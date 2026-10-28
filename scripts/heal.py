#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
仓库哨兵 · 自愈（heal）
======================
被 `scripts/guard.py` 在巡检结束后调用。**只做一件事**：把被外力打断的定时器重新挂上。

设计原则
--------
1. **只修「被外力打断」，不修「代码本身坏了」**
   GitHub 会在两种情况下让定时任务失灵：仓库长期无活动导致 workflow 被静默停用
   （`state=disabled_inactivity`），或者状态还是 active 但调度器不再触发。
   这两种的修法都是「把定时器重新挂上」，**不会执行对方仓库里的任何代码**。
   跑失败的 workflow、产物不新鲜、仓库归档、代码 bug —— 只报告，一律不碰。
2. **留痕**：每次动作写进 `heal_log.md`（追加），并在 `STATUS.md` 开「自愈」一节。
3. **限频防死磕**：单轮最多 `FIX_MAX_PER_RUN` 次；同一目标 7 天内最多
   `FIX_MAX_PER_TARGET` 次，超了不再修，标记「转人工」。
4. **先看后动**：默认 `off`，什么都不做；`dry-run` 只输出「本该修什么」，
   一个写请求都不发。

档位（环境变量 FIX_LEVEL）
--------------------------
off       默认。完全不动作（连计划都不算）。
dry-run   算出计划、写日志，但不发写请求。用来观察一段时间。
safe      自动 `enable` 被 GitHub 停用的 workflow。
full      safe + 对「定时器挂着却不触发」执行 `disable → enable` 重置定时器。

其他环境变量
------------
FIX_MAX_PER_RUN     单轮最多修几个目标，默认 3
FIX_MAX_PER_TARGET  同一目标 7 天内最多尝试几次，默认 3
"""

import json
import os
import sys
import time
from datetime import datetime, timedelta, timezone

VALID_LEVELS = ("off", "dry-run", "safe", "full")
WINDOW_DAYS = 7      # 同目标计数窗口
KEEP_DAYS = 45       # 状态里超过这么久没动静的条目直接清掉
LOG_MAX_LINES = 240  # heal_log.md 最多保留多少行

I = {"OK": "🟢", "FIX": "✅", "FAIL": "❌", "MANUAL": "⛔", "HOLD": "⏸"}


# ---------------------------------------------------------------- 小工具
def now_utc():
    return datetime.now(timezone.utc)


def iso(dt):
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def parse_dt(s):
    if not s:
        return None
    try:
        return datetime.strptime(s, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    except (ValueError, TypeError):
        return None


def resolve_level(level=None):
    """档位容错：写错了一律降级成 off，绝不因为拼错就乱改东西。"""
    raw = (level or os.environ.get("FIX_LEVEL") or "off").strip().lower()
    if raw in ("", "none", "no", "0", "false", "close", "shut"):
        raw = "off"
    if raw not in VALID_LEVELS:
        print(
            f"[heal] 未知 FIX_LEVEL={raw!r}，按 off 处理（可选：{', '.join(VALID_LEVELS)}）",
            file=sys.stderr,
        )
        return "off"
    return raw


def _int_env(name, default):
    try:
        return max(int(str(os.environ.get(name, default)).strip()), 0)
    except (TypeError, ValueError):
        return default


# ---------------------------------------------------------------- 决策
def plan(results, self_repo, level):
    """把巡检结果翻译成「该修什么」。纯函数，不发任何请求。"""
    items = []
    if level == "off":
        return items

    for x in results:
        if (x.get("status") or "") != "FAIL":
            continue
        repo = x.get("repo") or ""
        wf_id = x.get("wf_id")
        if not wf_id:
            continue
        state = (x.get("state") or "").strip()
        name = x.get("workflow") or "—"
        base = {
            "key": f"{repo}#{wf_id}",
            "repo": repo,
            "workflow": name,
            "wf_id": wf_id,
            "state": state,
        }

        # 巡检器自己：它不跑就没人来修它，只能人工
        if repo == self_repo:
            if state == "disabled_inactivity":
                items.append(dict(
                    base, action="manual",
                    why="巡检器自身被停用；它不运行就没人来修它，请在 Actions 页面手动 re-enable",
                ))
            continue

        if state == "disabled_inactivity":
            items.append(dict(
                base, action="enable",
                why="GitHub 因仓库长期无活动，静默停用了定时任务",
            ))
        elif state == "active" and x.get("stalled"):
            if level == "full":
                items.append(dict(
                    base, action="toggle",
                    why="状态仍是 active，但已超期未触发 → 重置定时器",
                ))
            else:
                items.append(dict(
                    base, action="manual",
                    why="定时器挂着却不触发；重置需 FIX_LEVEL=full，当前档位不动它",
                ))
        elif state and state != "active":
            items.append(dict(
                base, action="manual",
                why=f"workflow 状态为 `{state}`，不是静默停用，需人工判断",
            ))
    return items


# ---------------------------------------------------------------- 执行
def _execute(api, owner, it):
    """真正发写请求。返回 (是否成功, 人话说明)。"""
    repo, wf_id = it["repo"], it["wf_id"]
    try:
        if it["action"] == "enable":
            r = api(f"/repos/{owner}/{repo}/actions/workflows/{wf_id}/enable", method="PUT")
            if isinstance(r, dict) and r.get("_error"):
                return False, f"enable 失败：{r['_error']}"
            return True, "已重新启用，定时器恢复"

        if it["action"] == "toggle":
            r1 = api(f"/repos/{owner}/{repo}/actions/workflows/{wf_id}/disable", method="PUT")
            if isinstance(r1, dict) and r1.get("_error"):
                return False, f"disable 失败：{r1['_error']}"
            time.sleep(1)
            r2 = api(f"/repos/{owner}/{repo}/actions/workflows/{wf_id}/enable", method="PUT")
            if isinstance(r2, dict) and r2.get("_error"):
                return False, f"已 disable 但 enable 失败，请人工恢复：{r2['_error']}"
            return True, "已 disable→enable 重置定时器"

        return False, f"未知动作 `{it['action']}`"
    except Exception as e:  # noqa: BLE001
        return False, f"{type(e).__name__}: {e}"


def _load_state(path):
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict) and isinstance(data.get("targets"), dict):
            return data
    except (OSError, ValueError):
        pass
    return {"targets": {}}


def _prune(state):
    cut = now_utc() - timedelta(days=KEEP_DAYS)
    for k in list(state["targets"]):
        last = parse_dt((state["targets"].get(k) or {}).get("last"))
        if last is None or last < cut:
            state["targets"].pop(k, None)
    return state


def run(results, api, owner, self_repo, out_dir, level=None):
    """入口。任何异常都不该影响巡检主体，所以内部尽量自己兜住。"""
    lv = resolve_level(level)
    summary = {
        "level": lv,
        "planned": [],
        "fixed": [],
        "failed": [],
        "escalated": [],
        "skipped": [],
        "note": "",
        "healed_keys": set(),
    }
    if lv == "off":
        return summary

    max_run = _int_env("FIX_MAX_PER_RUN", 3)
    max_target = _int_env("FIX_MAX_PER_TARGET", 3)

    items = plan(results, self_repo, lv)
    summary["planned"] = items
    if not items:
        return summary

    spath = os.path.join(out_dir, "heal_state.json")
    state = _prune(_load_state(spath))
    window_start = now_utc() - timedelta(days=WINDOW_DAYS)
    acted = 0
    touched = False

    for it in items:
        if it["action"] == "manual":
            summary["escalated"].append(it)
            continue

        rec = state["targets"].get(it["key"]) or {}
        tries = [t for t in (parse_dt(s) for s in rec.get("times") or []) if t and t >= window_start]
        if len(tries) >= max_target:
            it = dict(it, why=f"{WINDOW_DAYS} 天内已尝试 {len(tries)} 次仍未恢复，转人工")
            summary["escalated"].append(it)
            continue

        # dry-run 不做限频截断：它是演练，要看全量计划
        if lv != "dry-run" and acted >= max_run:
            it = dict(it, why=f"本轮已达上限 {max_run} 次，留到下一轮")
            summary["skipped"].append(it)
            continue

        if lv == "dry-run":
            # 不写 state：演练不该消耗真实配额
            summary["fixed"].append(dict(it, result="演练，未实际执行"))
            continue

        acted += 1
        okd, msg = _execute(api, owner, it)
        stamp = iso(now_utc())
        state["targets"][it["key"]] = {
            "times": [iso(t) for t in tries] + [stamp],
            "last": stamp,
            "last_state": it["state"],
            "last_result": ("ok" if okd else msg)[:160],
        }
        touched = True
        if okd:
            summary["fixed"].append(dict(it, result=msg))
            summary["healed_keys"].add(it["key"])
        else:
            summary["failed"].append(dict(it, result=msg))

    if touched:
        try:
            os.makedirs(out_dir, exist_ok=True)
            with open(spath, "w", encoding="utf-8") as f:
                json.dump(state, f, ensure_ascii=False, indent=2, sort_keys=True)
                f.write("\n")
        except OSError as e:
            print(f"[heal] 状态写入失败：{e}", file=sys.stderr)

    _append_log(out_dir, summary)
    return summary


# ---------------------------------------------------------------- 留痕
def _append_log(out_dir, s):
    lv = s.get("level")
    if lv in ("off", "error") or not (s.get("fixed") or s.get("failed")):
        return
    head = (
        "# 自愈日志\n\n"
        "> 由 `scripts/heal.py` 自动追加，勿手改。只记录**实际执行过**的动作。\n\n"
    )
    lines = [f"## {now_utc().strftime('%Y-%m-%d %H:%M')} UTC · `{lv}`"]
    for it in s.get("fixed") or []:
        lines.append(f"- ✅ `{it['repo']}` / {it['workflow']}：`{it['action']}` → {it.get('result') or ''}")
    for it in s.get("failed") or []:
        lines.append(f"- ❌ `{it['repo']}` / {it['workflow']}：`{it['action']}` → {it.get('result') or ''}")
    lines.append("")

    path = os.path.join(out_dir, "heal_log.md")
    old = ""
    try:
        with open(path, encoding="utf-8") as f:
            old = f.read()
    except OSError:
        old = head
    body = (old if old.strip() else head).rstrip("\n")
    body += "\n\n" + "\n".join(lines) + "\n"
    kept = body.splitlines()
    if len(kept) > LOG_MAX_LINES:
        # 保住文件头，从尾部保留
        body = "\n".join(head.splitlines() + ["", f"<!-- 更早记录已截断 -->", ""] + kept[-LOG_MAX_LINES:]) + "\n"
    try:
        os.makedirs(out_dir, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(body)
    except OSError as e:
        print(f"[heal] 日志写入失败：{e}", file=sys.stderr)


def render_status(s):
    """STATUS.md 里的「自愈」一节。"""
    L = ["## 自愈\n"]
    lv = (s or {}).get("level") or "off"
    if lv == "off":
        L.append("> 未开启（`FIX_LEVEL=off`）：巡检只报告，不改动任何东西。\n")
        return L
    if lv == "error":
        L.append(f"> ⚠️ 自愈模块异常，本轮未执行任何修复：`{s.get('note')}`\n")
        return L

    tag = {
        "dry-run": "🧪 **dry-run 演练**（只决策，不发写请求）",
        "safe": "🩹 **安全档**：只重新启用被静默停用的 workflow",
        "full": "🛠 **完整档**：含重置「挂着却不触发」的定时器",
    }.get(lv, lv)
    fixed = s.get("fixed") or []
    failed = s.get("failed") or []
    esc = s.get("escalated") or []
    hold = s.get("skipped") or []
    act_label = "可自动修" if lv == "dry-run" else "已修"
    tail = "" if lv == "dry-run" else f" ｜ 失败 {len(failed)}"
    L.append(
        f"> {tag} ｜ 命中 {len(s.get('planned') or [])} 项 ｜ "
        f"{act_label} {len(fixed)}{tail} ｜ 需人工 {len(esc)} ｜ 顺延 {len(hold)}\n"
    )
    rows = (
        [(I["FIX"], x, x.get("result")) for x in fixed]
        + [(I["FAIL"], x, x.get("result")) for x in failed]
        + [(I["MANUAL"], x, x.get("why")) for x in esc]
        + [(I["HOLD"], x, x.get("why")) for x in hold]
    )
    if not rows:
        L.append("> 本轮没有需要自愈的目标。\n")
        return L

    L.append("| | 仓库 | 工作流 | 动作 | 说明 |")
    L.append("|---|---|---|---|---|")
    for icon, x, note in rows:
        L.append(f"| {icon} | `{x['repo']}` | {x['workflow']} | `{x['action']}` | {note or x.get('why') or '—'} |")
    L.append("")
    L.append(
        "> 口径：自愈只做「让 GitHub 重新挂上定时器」（`enable` / `disable→enable`），"
        "**不执行**对方仓库的代码，也不改任何文件。跑失败、产物不新鲜、代码 bug 一律只报告。"
        "同一目标 7 天内最多试 3 次，超了转人工。详见 `heal_log.md`。\n"
    )
    return L


def render_report(s):
    """Issue 正文里的自愈段落。"""
    if not s or (s.get("level") or "off") in ("off", "error"):
        return ""
    fixed = s.get("fixed") or []
    failed = s.get("failed") or []
    esc = s.get("escalated") or []
    if not (fixed or failed or esc):
        return ""
    out = ["### 自愈动作\n"]
    for it in fixed:
        out.append(f"- ✅ `{it['repo']}` / {it['workflow']}：`{it['action']}` — {it.get('result') or ''}")
    for it in failed:
        out.append(f"- ❌ `{it['repo']}` / {it['workflow']}：`{it['action']}` — {it.get('result') or ''}")
    for it in esc:
        out.append(f"- ⛔ `{it['repo']}` / {it['workflow']}：需人工 — {it.get('why') or ''}")
    out.append("")
    return "\n".join(out)
