#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GitHub 全仓库巡检器（通用版，任何人 fork 后开箱即用）
====================================================
不硬编码任何账号名或仓库名：owner 自动取当前仓库的归属者。

两种运行模式（自动选择）
------------------------
- **PAT 模式**：仓库 Secrets 配了 `GH_PAT` → 覆盖名下**全部**仓库（含私有）
- **匿名模式**：没配 → 降级为只巡检**公开**仓库，无需任何配置，fork 就能跑
  （未认证 API 限额 60 次/小时，脚本会自动控制请求量并在看板标注）

检查维度
--------
1. 静默停摆：按 workflow 自身 cron 推算预期周期，超时未触发即报警
2. 运行失败：最近一次 failure，或连续失败 >= 2 次
3. 状态异常：workflow 被禁用、仓库归档/停用
4. 产物新鲜度：关键文件最后提交距今过久 —— 抓「跑了但没产出」
5. 自监控：把巡检器自身运行时间写进看板，供其他仓库反向盯

输出
----
- STATUS.md        状态看板（workflow 自动提交）
- guard_report.md  存在异常时生成，供 workflow 开 Issue
- 退出码 1 = 有 FAIL 级异常

环境变量
--------
GH_OWNER    必填，账号名（workflow 里传 ${{ github.repository_owner }}）
GH_PAT      可选，跨仓库读取权限的 token
GITHUB_REPOSITORY  自动注入，用于识别巡检器自身仓库名
GH_OUT_DIR  可选，输出目录
"""

import base64
import json
import os
import re
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from urllib import parse, request, error

API = "https://api.github.com"

# 自愈模块与巡检器同目录。加载失败不影响巡检（只是没有自愈能力）。
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
try:
    import heal  # noqa: E402
except Exception as _heal_err:  # noqa: BLE001
    heal = None
    print(f"[heal] 无法加载自愈模块：{_heal_err}", file=sys.stderr)

TOKEN = (os.environ.get("GH_PAT") or "").strip()
OWNER = (os.environ.get("GH_OWNER") or "").strip()
REPO_ENV = os.environ.get("GITHUB_REPOSITORY") or ""
SELF_REPO = REPO_ENV.split("/")[-1] if REPO_ENV else "repo-guard"
OUT_DIR = os.environ.get("GH_OUT_DIR") or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

MODE = "pat" if TOKEN else "anon"
ANON_BUDGET = 55  # 未认证每小时 60 次，留 5 次余量

# 关键产物新鲜度：仓库 -> [(路径, 最大陈旧小时, 说明)]
# 这是唯一的「个性化」配置项，fork 的人可自行增删。
# 选「每天都会变的文件」，不要选配置类文件（那种几十天不变是正常的）
ARTIFACTS = {
    "db-sync": [("db.json", 96, "站点库")],
    "dongguaTV": [("db.json", 96, "站点库")],
}

# 这些 workflow state 属于「按预期不运行」，不算故障
BENIGN_STATES = {
    "disabled_manually": "手动禁用",
    "disabled_fork": "fork 默认禁用",
    "deleted": "已删除",
}

# 特例覆盖：实际周期与 cron 不符时按小时强行指定，键为 "仓库名/工作流名"
PERIOD_OVERRIDE = {}

SKIPPED = []
REQ_COUNT = 0
_REQ_LOCK = threading.Lock()

# 默认忽略 http_proxy / https_proxy 环境变量直连 GitHub。
# 原因：某些沙箱/公司代理会让 urllib 的 CONNECT 隧道卡死，而 curl 走同一代理却正常。
# 确实需要走代理时，设 GH_USE_PROXY=1。
if os.environ.get("GH_USE_PROXY") == "1":
    OPENER = request.build_opener()
else:
    OPENER = request.build_opener(request.ProxyHandler({}))


# ---------------------------------------------------------------- HTTP
def api(path, method="GET", payload=None):
    global REQ_COUNT
    url = path if path.startswith("http") else API + path
    data = json.dumps(payload).encode() if payload is not None else None
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "repo-guard",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    if TOKEN:
        headers["Authorization"] = f"Bearer {TOKEN}"

    req = request.Request(url, data=data, method=method, headers=headers)
    for attempt in range(3):
        with _REQ_LOCK:
            REQ_COUNT += 1
        try:
            with OPENER.open(req, timeout=30) as r:
                raw = r.read()
                return json.loads(raw) if raw else {}
        except error.HTTPError as e:
            if e.code in (403, 429) and attempt < 2:
                time.sleep(3 * (attempt + 1))
                continue
            detail = ""
            try:
                detail = e.read().decode()[:200]
            except Exception:  # noqa: BLE001
                pass
            return {"_error": f"HTTP {e.code} {e.reason} {detail}".strip(), "_code": e.code, "_path": path}
        except Exception as e:  # noqa: BLE001
            if attempt < 2:
                time.sleep(2)
                continue
            return {"_error": f"{type(e).__name__}: {e}", "_path": path}
    return {"_error": "unreachable", "_path": path}


def ok(resp):
    if isinstance(resp, list):
        return True
    return isinstance(resp, dict) and not resp.get("_error")


# ---------------------------------------------------------------- 工具
def now_utc():
    return datetime.now(timezone.utc)


def parse_dt(s):
    if not s:
        return None
    try:
        return datetime.strptime(s, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    except ValueError:
        try:
            return datetime.fromisoformat(s.replace("Z", "+00:00"))
        except ValueError:
            return None


def human_age(hours):
    if hours is None:
        return "—"
    if hours < 1:
        return f"{hours * 60:.0f} 分钟"
    if hours < 48:
        return f"{hours:.0f} 小时"
    return f"{hours / 24:.1f} 天"


def cron_period_hours(cron):
    """从 cron 推算平均触发间隔，返回 (小时, 人话)。"""
    f = cron.split()
    if len(f) != 5:
        return 24.0, "cron 格式异常，按每天"
    mi, hr, dom, mon, dow = f
    try:
        if mi.startswith("*/") and hr == "*":
            n = int(mi[2:])
            return max(n, 1) / 60, f"每 {n} 分钟"
        if hr.startswith("*/"):
            n = int(hr[2:])
            return max(n, 1), f"每 {n} 小时"
        if hr == "*" and mi == "*":
            return 1 / 60, "每分钟"
        if hr == "*":
            return 1.0, "每小时"
        if dom == "*" and mon == "*" and dow == "*":
            return 24.0, "每天"
        if dow != "*":
            n = len([x for x in dow.split(",") if x.strip()])
            return 168.0 / max(n, 1), f"每周 {n} 天"
        if dom != "*":
            n = len([x for x in dom.split(",") if x.strip()])
            return 720.0 / max(n, 1), f"每月 {n} 次"
    except (ValueError, IndexError):
        pass
    return 24.0, "无法解析，按每天"


def extract_cron(text):
    m = re.search(r"cron:\s*['\"]?([^'\"\n]+)", text or "")
    return m.group(1).strip() if m else None


# ---------------------------------------------------------------- 巡检
def list_repos():
    """PAT 模式取名下全部；匿名模式只能取公开仓库。"""
    repos, page = [], 1
    while True:
        if MODE == "pat":
            path = f"/user/repos?affiliation=owner&per_page=100&page={page}&sort=pushed"
        else:
            path = f"/users/{OWNER}/repos?per_page=100&page={page}&sort=pushed"
        chunk = api(path)
        if not ok(chunk):
            raise SystemExit(f"列出仓库失败：{chunk.get('_error') if isinstance(chunk, dict) else chunk}")
        if not chunk:
            break
        repos.extend(chunk)
        if len(chunk) < 100:
            break
        page += 1
    return repos


def check_workflow(repo, wf):
    name = wf.get("name") or wf.get("path") or f"id{wf.get('id')}"
    state = wf.get("state") or "unknown"
    wf_id = wf.get("id")
    path = wf.get("path") or ""
    if os.environ.get("GH_VERBOSE") == "1":
        print(f"[req {REQ_COUNT}] {repo} / {name} (state={state})", file=sys.stderr, flush=True)

    # 手动禁用 / fork 默认禁用 / 已删除：按预期不运行，直接跳过，不消耗请求
    if state in BENIGN_STATES:
        return {
            "repo": repo, "workflow": name, "status": "SKIP", "cron": None,
            "period": "—", "last": None, "age_h": None, "conclusion": None,
            "notes": [f"workflow 状态 `{state}`（{BENIGN_STATES[state]}）"],
        }

    cron = None
    if path:
        body = api(f"/repos/{OWNER}/{repo}/contents/{parse.quote(path)}")
        if ok(body) and body.get("content"):
            try:
                cron = extract_cron(base64.b64decode(body["content"]).decode("utf-8", "replace"))
            except Exception:  # noqa: BLE001
                cron = None

    runs = api(f"/repos/{OWNER}/{repo}/actions/workflows/{wf_id}/runs?per_page=30")
    if not ok(runs):
        return {
            "repo": repo, "workflow": name, "status": "WARN", "cron": cron,
            "period": None, "last": None, "age_h": None, "conclusion": None,
            "notes": [f"读取运行记录失败：{runs.get('_error')}"],
        }

    run_list = list(runs.get("workflow_runs") or [])
    notes = []
    level = "OK"
    stalled = False  # 定时器挂着却不触发：自愈模块据此决定是否重置

    period, period_desc = None, "无定时器"
    if cron:
        period, period_desc = cron_period_hours(cron)
        ov = PERIOD_OVERRIDE.get(f"{repo}/{name}")
        if ov:
            period, period_desc = float(ov), f"每 {ov} 小时（指定）"

    if state != "active":
        level = "FAIL"
        notes.append(f"workflow 状态为 `{state}`（非 active，需人工确认）")

    if not run_list:
        # 无定时器 = 纯手动/推送触发，从未运行是正常的
        if not period:
            return {
                "repo": repo, "workflow": name, "status": "SKIP", "cron": cron,
                "period": period_desc, "last": None, "age_h": None, "conclusion": None,
                "notes": ["无定时器且从未运行（纯手动触发）"],
            }
        # 有定时器但没记录：可能刚建，还没到第一次触发时间
        tolerance = max(2 * period, period + 6)
        created = parse_dt(wf.get("created_at"))
        if created:
            since_create = (now_utc() - created).total_seconds() / 3600
            if since_create <= tolerance:
                return {
                    "repo": repo, "workflow": name, "status": "SKIP", "cron": cron,
                    "period": period_desc, "last": None, "age_h": None, "conclusion": None,
                    "notes": [f"新建 {human_age(since_create)}，尚未到首个触发周期（容忍 {tolerance:.0f}h）"],
                }
        notes.append("配置了定时器但从未运行过")
        return {
            "repo": repo, "workflow": name, "status": "FAIL", "cron": cron,
            "period": period_desc, "last": None, "age_h": None, "conclusion": None,
            "wf_id": wf_id, "state": state, "stalled": False,
            "notes": notes,
        }

    latest = run_list[0]
    last_dt = parse_dt(latest.get("created_at"))
    age_h = (now_utc() - last_dt).total_seconds() / 3600 if last_dt else None

    # 停摆判定只看 schedule 触发的运行。
    # 手动触发（workflow_dispatch）不能算数——否则每周手点一次就能掩盖定时任务已死。
    sched_runs = [r for r in run_list if (r.get("event") or "") == "schedule"]
    last_sched_dt = parse_dt(sched_runs[0].get("created_at")) if sched_runs else None
    sched_age_h = (
        (now_utc() - last_sched_dt).total_seconds() / 3600 if last_sched_dt else None
    )

    if period:
        tolerance = max(2 * period, period + 6)
        if not sched_runs:
            level = "FAIL"
            stalled = True
            notes.append(
                f"有{period_desc}的定时器，但最近 {len(run_list)} 次运行中**没有一次由 schedule 触发**"
                "（只有手动/推送触发）→ 定时任务没在工作"
            )
        elif sched_age_h is not None and sched_age_h > tolerance:
            level = "FAIL"
            stalled = True
            notes.append(
                f"上次定时触发是 {human_age(sched_age_h)}前（预期{period_desc}，容忍 {tolerance:.0f}h）"
                "→ 疑似被 GitHub 静默停用"
            )

    consec = 0
    for r in run_list:
        if (r.get("conclusion") or "") == "failure":
            consec += 1
        else:
            break
    fails = sum(1 for r in run_list if (r.get("conclusion") or "") == "failure")

    if consec >= 2:
        level = "FAIL"
        notes.append(f"连续 {consec} 次运行失败")
    elif consec == 1:
        if level == "OK":
            level = "WARN"
        notes.append("最近一次运行失败")
    if fails >= 3 and consec < 2:
        if level == "OK":
            level = "WARN"
        notes.append(f"最近 {len(run_list)} 次里失败 {fails} 次")

    return {
        "repo": repo, "workflow": name, "status": level, "cron": cron,
        "period": period_desc, "last": last_dt, "age_h": age_h,
        "last_sched": last_sched_dt, "sched_age_h": sched_age_h,
        # 结论优先取最近一次定时触发的结果，避免手动成功掩盖定时失败
        "conclusion": (sched_runs[0].get("conclusion") if sched_runs else latest.get("conclusion")),
        "event": latest.get("event"),
        "wf_id": wf_id, "state": state, "stalled": stalled,
        "notes": notes,
    }


def check_artifact(repo, path, max_age_h, label):
    commits = api(f"/repos/{OWNER}/{repo}/commits?path={parse.quote(path)}&per_page=1")
    if not ok(commits):
        return {"repo": repo, "path": path, "label": label, "status": "WARN",
                "age_h": None, "notes": [f"读取提交失败：{commits.get('_error')}"]}
    if not commits:
        return {"repo": repo, "path": path, "label": label, "status": "FAIL",
                "age_h": None, "notes": [f"文件 `{path}` 不存在"]}
    dt = parse_dt(commits[0]["commit"]["author"]["date"])
    age_h = (now_utc() - dt).total_seconds() / 3600 if dt else None
    level = "OK"
    notes = []
    if age_h is not None and age_h > max_age_h:
        level = "FAIL"
        notes.append(f"{human_age(age_h)} 没更新（阈值 {max_age_h}h）→ 跑了但没产出")
    return {"repo": repo, "path": path, "label": label, "status": level,
            "age_h": age_h, "last": dt, "notes": notes}


def self_check():
    runs = api(f"/repos/{OWNER}/{SELF_REPO}/actions/workflows/guard.yml/runs?per_page=5")
    if not ok(runs) or not runs.get("workflow_runs"):
        return {"status": "WARN", "age_h": None, "notes": ["读不到自身运行记录"]}
    # 只取已完成的，否则会读到「正在跑的这一轮」，结论永远是空的
    done = [r for r in runs["workflow_runs"] if (r.get("status") or "") == "completed"]
    if not done:
        return {"status": "WARN", "age_h": None, "conclusion": None, "notes": ["没有已完成的运行"]}
    r = done[0]
    dt = parse_dt(r.get("created_at"))
    age_h = (now_utc() - dt).total_seconds() / 3600 if dt else None
    return {"status": "OK", "age_h": age_h, "last": dt, "conclusion": r.get("conclusion")}


# ---------------------------------------------------------------- 输出
def build_status(results, artifacts, selfinfo, repo_count, wf_count, heal_summary=None):
    t = now_utc()
    L = []
    L.append("# 仓库巡检看板\n")
    L.append(f"> 最后巡检：**{t.strftime('%Y-%m-%d %H:%M')} UTC**")
    self_age = human_age(selfinfo.get("age_h"))
    L.append(f"> 巡检器自身：上次运行 {self_age}前，结论 `{selfinfo.get('conclusion') or '—'}`")
    mode_desc = (
        "🔓 **PAT 模式**：覆盖全部仓库（含私有）"
        if MODE == "pat"
        else "⚠️ **匿名模式**：仅覆盖公开仓库，未认证限额 60 次/小时"
    )
    L.append(f"> 模式：{mode_desc}")
    L.append(f"> 覆盖：**{repo_count}** 个仓库 / **{wf_count}** 个 workflow ｜ 本次请求 {REQ_COUNT} 次\n")

    n_fail = sum(1 for x in results if x["status"] == "FAIL")
    n_warn = sum(1 for x in results if x["status"] == "WARN")
    n_ok = sum(1 for x in results if x["status"] == "OK")
    n_skip = sum(1 for x in results if x["status"] == "SKIP")
    badge = f"🔴 有 {n_fail} 项异常" if n_fail else (f"🟡 {n_warn} 项需留意" if n_warn else "🟢 全部正常")
    L.append(f"## 总览：{badge}\n")
    L.append(f"🟢 正常 {n_ok} ｜ 🟡 留意 {n_warn} ｜ 🔴 异常 {n_fail} ｜ ⚪ 跳过 {n_skip}\n")
    if n_skip:
        L.append(
            "> ⚪ 跳过＝按预期不运行，不算故障：手动禁用的、fork 仓库默认禁用的、"
            "纯手动触发从未跑过的、以及刚建还没到首个触发周期的。\n"
        )

    icon = {"OK": "🟢", "WARN": "🟡", "FAIL": "🔴", "SKIP": "⚪"}

    if heal_summary is not None and heal is not None:
        L.extend(heal.render_status(heal_summary))

    if n_fail or n_warn:
        L.append("## 需要处理\n")
        L.append("| 级别 | 仓库 | 工作流 / 文件 | 最后定时触发 | 周期 | 说明 |")
        L.append("|---|---|---|---|---|---|")
        for x in results:
            if x["status"] in ("FAIL", "WARN"):
                lt = x.get("last_sched") or x.get("last")
                last = lt.strftime("%m-%d %H:%M") if lt else "—"
                L.append(
                    f"| {icon[x['status']]} | `{x['repo']}` | {x['workflow']} | {last} "
                    f"| {x.get('period') or '—'} | {'；'.join(x['notes'])} |"
                )
        for a in artifacts:
            if a["status"] in ("FAIL", "WARN"):
                last = a["last"].strftime("%m-%d %H:%M") if a.get("last") else "—"
                L.append(
                    f"| {icon[a['status']]} | `{a['repo']}` | `{a['path']}`（{a['label']}） | {last} "
                    f"| — | {'；'.join(a['notes'])} |"
                )
        L.append("")

    L.append("## 全部工作流\n")
    L.append("| | 仓库 | 工作流 | 周期 | 最后定时触发 | 距今 | 最近结论 |")
    L.append("|---|---|---|---|---|---|---|")
    for x in sorted(results, key=lambda r: (r["status"] != "FAIL", r["status"] != "WARN", r["repo"])):
        lt = x.get("last_sched") or x.get("last")
        last = lt.strftime("%m-%d %H:%M") if lt else "—"
        age = x.get("sched_age_h") if x.get("last_sched") else x.get("age_h")
        L.append(
            f"| {icon[x['status']]} | `{x['repo']}` | {x['workflow']} | {x.get('period') or '—'} "
            f"| {last} | {human_age(age)} | `{x.get('conclusion') or '—'}` |"
        )
    L.append("")

    if artifacts:
        L.append("## 产物新鲜度\n")
        L.append("| | 仓库 | 文件 | 说明 | 最后提交 | 距今 |")
        L.append("|---|---|---|---|---|---|")
        for a in artifacts:
            last = a["last"].strftime("%m-%d %H:%M") if a.get("last") else "—"
            L.append(
                f"| {icon[a['status']]} | `{a['repo']}` | `{a['path']}` | {a['label']} "
                f"| {last} | {human_age(a.get('age_h'))} |"
            )
        L.append("")

    if SKIPPED:
        L.append("## 未纳入巡检\n")
        for s in SKIPPED:
            L.append(f"- `{s['repo']}`：{s['why']}")
        L.append("")

    L.append("---")
    L.append(
        "判定口径：以 workflow 自身 cron 推算预期周期，超过 `max(2×周期, 周期+6h)` 未触发即判停摆；"
        "连续 2 次失败判异常。本文件由 `scripts/guard.py` 自动生成，勿手改。"
    )
    return "\n".join(L) + "\n"


def build_report(results, artifacts, heal_summary=None):
    blocks = []
    if heal_summary and heal is not None:
        seg = heal.render_report(heal_summary)
        if seg:
            blocks.append(seg)
    for x in results:
        if x["status"] in ("FAIL", "WARN"):
            lt = x.get("last_sched") or x.get("last")
            last = lt.strftime("%Y-%m-%d %H:%M UTC") if lt else "从未运行"
            age = x.get("sched_age_h") if x.get("last_sched") else x.get("age_h")
            blocks.append(
                f"### {x['repo']} / {x['workflow']}\n"
                f"- 级别：{'🔴 异常' if x['status'] == 'FAIL' else '🟡 留意'}\n"
                f"- 最后定时触发：{last}（{human_age(age)}前）\n"
                f"- 预期周期：{x.get('period') or '—'}\n"
                f"- 问题：{'；'.join(x['notes'])}\n"
            )
    for a in artifacts:
        if a["status"] in ("FAIL", "WARN"):
            blocks.append(
                f"### {a['repo']} / `{a['path']}`\n"
                f"- 级别：{'🔴 异常' if a['status'] == 'FAIL' else '🟡 留意'}\n"
                f"- 说明：{a['label']}\n"
                f"- 距今：{human_age(a.get('age_h'))}\n"
                f"- 问题：{'；'.join(a['notes'])}\n"
            )
    return "\n".join(blocks)


# ---------------------------------------------------------------- main
def main():
    if not OWNER:
        raise SystemExit("缺少 GH_OWNER 环境变量")

    repos = list_repos()
    results, artifacts = [], []
    wf_total = 0
    wf_jobs, art_jobs = [], []

    # 第一遍：串行列出每个仓库的 workflow（请求少，且要先知道有哪些）
    for repo in repos:
        rname = repo.get("name")
        if rname == SELF_REPO:
            continue
        if repo.get("archived") or repo.get("disabled"):
            results.append({
                "repo": rname, "workflow": "（仓库级）", "status": "FAIL", "last": None,
                "age_h": None, "period": "—", "conclusion": None,
                "notes": [f"仓库已{'归档' if repo.get('archived') else '停用'}"],
            })
            continue

        if MODE == "anon" and REQ_COUNT >= ANON_BUDGET:
            SKIPPED.append({"repo": rname, "why": "匿名模式请求预算用尽，已跳过"})
            continue

        wfs = api(f"/repos/{OWNER}/{rname}/actions/workflows?per_page=100")
        if not ok(wfs):
            SKIPPED.append({"repo": rname, "why": f"读取 workflow 失败：{wfs.get('_error')}"})
            continue
        wf_list = wfs.get("workflows") or []
        if not wf_list:
            SKIPPED.append({"repo": rname, "why": "没有配置任何 workflow"})
            continue

        for wf in wf_list:
            wf_total += 1
            wf_jobs.append((rname, wf))
        for path_, max_h, label in ARTIFACTS.get(rname, []):
            art_jobs.append((rname, path_, max_h, label))

    # 第二遍：并发检查。串行时 35 个请求 × 2-3 秒会超过 2 分钟，并发后十几秒完成。
    workers = min(8, max(len(wf_jobs) + len(art_jobs), 1))
    with ThreadPoolExecutor(max_workers=workers) as ex:
        results.extend(ex.map(lambda j: check_workflow(*j), wf_jobs))
        artifacts.extend(ex.map(lambda a: check_artifact(*a), art_jobs))

    selfinfo = self_check()

    # ---- 自愈（默认 off，不动作）----
    # 放在生成看板之前，这样看板里能直接看到「本轮修了什么」。
    # 任何异常都只警告，绝不影响巡检本身。
    heal_summary = None
    if heal is None:
        heal_summary = {"level": "error", "note": "自愈模块未加载（scripts/heal.py 缺失或被改动）"}
    else:
        try:
            heal_summary = heal.run(
                results,
                api=api,
                owner=OWNER,
                self_repo=SELF_REPO,
                out_dir=OUT_DIR,
            )
            # 修过的目标加个标注：本次仍算异常（要等下一轮复核），但说明已处理
            for x in results:
                if f"{x.get('repo')}#{x.get('wf_id')}" in heal_summary["healed_keys"]:
                    x["notes"].append("**本轮已自愈，下次巡检复核**")
        except Exception as e:  # noqa: BLE001
            print(f"[heal] 自愈模块异常，已跳过：{type(e).__name__}: {e}", file=sys.stderr)
            heal_summary = {"level": "error", "note": f"{type(e).__name__}: {e}"}

    status_md = build_status(results, artifacts, selfinfo, len(repos), wf_total, heal_summary)

    os.makedirs(OUT_DIR, exist_ok=True)
    with open(os.path.join(OUT_DIR, "STATUS.md"), "w", encoding="utf-8") as f:
        f.write(status_md)
    print(status_md)

    bad = [x for x in results if x["status"] in ("FAIL", "WARN")] + [
        a for a in artifacts if a["status"] in ("FAIL", "WARN")
    ]
    hard = [x for x in results if x["status"] == "FAIL"] + [a for a in artifacts if a["status"] == "FAIL"]

    report_path = os.path.join(OUT_DIR, "guard_report.md")
    if bad:
        report = (
            f"自动巡检发现 **{len(bad)}** 项需要处理（其中 🔴 异常 {len(hard)} 项）。\n\n"
            + build_report(results, artifacts, heal_summary)
            + "\n**处理提示**\n"
            "- **静默停摆**：`schedule` 在 fork 仓库上会被 GitHub 周期性停用（状态仍显示 active，极隐蔽）。"
            "到该仓库 Actions 页面确认，或改用外部定时器调 `workflow_dispatch`。\n"
            "- **连续失败**：点进最近一次失败的 run 看日志。\n"
            "- **产物不更新**：workflow 可能成功了但内容无变化（例如 CDN 缓存滞后），核对上游数据源。\n"
            "- 修复后本 Issue 会在下次巡检时自动关闭。\n"
        )
        with open(report_path, "w", encoding="utf-8") as f:
            f.write(report)
        print("\n--- 已生成 guard_report.md ---")
    elif os.path.exists(report_path):
        os.remove(report_path)

    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a", encoding="utf-8") as f:
            f.write(status_md)

    return 1 if hard else 0


if __name__ == "__main__":
    sys.exit(main())
