# 仓库巡检看板

> 最后巡检：**2026-10-28 14:46 UTC**
> 巡检器自身：上次运行 13 分钟前，结论 `failure`
> 模式：🔓 **PAT 模式**：覆盖全部仓库（含私有）
> 覆盖：**6** 个仓库 / **15** 个 workflow ｜ 本次请求 35 次

## 总览：🔴 有 1 项异常

🟢 正常 10 ｜ 🟡 留意 0 ｜ 🔴 异常 1 ｜ ⚪ 跳过 4

> ⚪ 跳过＝按预期不运行，不算故障：手动禁用的、fork 仓库默认禁用的、纯手动触发从未跑过的、以及刚建还没到首个触发周期的。

## 自愈

> 🧪 **dry-run 演练**（只决策，不发写请求） ｜ 命中 1 项 ｜ 可自动修 0 ｜ 需人工 1 ｜ 顺延 0

| | 仓库 | 工作流 | 动作 | 说明 |
|---|---|---|---|---|
| ⛔ | `cf-speed-dns` | dns_both_push | `manual` | 定时器挂着却不触发；重置需 FIX_LEVEL=full，当前档位不动它 |

> 口径：自愈只做「让 GitHub 重新挂上定时器」（`enable` / `disable→enable`），**不执行**对方仓库的代码，也不改任何文件。跑失败、产物不新鲜、代码 bug 一律只报告。同一目标 7 天内最多试 3 次，超了转人工。详见 `heal_log.md`。

## 需要处理

| 级别 | 仓库 | 工作流 / 文件 | 最后定时触发 | 周期 | 说明 |
|---|---|---|---|---|---|
| 🔴 | `cf-speed-dns` | dns_both_push | 10-14 21:02 | 每 6 小时 | 上次定时触发是 13.7 天前（预期每 6 小时，容忍 12h）→ 疑似被 GitHub 静默停用 |

## 全部工作流

| | 仓库 | 工作流 | 周期 | 最后定时触发 | 距今 | 最近结论 |
|---|---|---|---|---|---|---|
| 🔴 | `cf-speed-dns` | dns_both_push | 每 6 小时 | 10-14 21:02 | 13.7 天 | `success` |
| 🟢 | `cf-speed-dns` | Keep Repo Alive | 每月 1 次 | 10-01 09:42 | 27.2 天 | `success` |
| ⚪ | `cf-speed-dns` | Cloudflare IP 优选并自动更新DNS (域名2) | — | — | — | `—` |
| 🟢 | `db-sync` | Guard - 巡检定时任务存活（互锁） | 每天 | 10-28 06:12 | 9 小时 | `success` |
| ⚪ | `db-sync` | keepalive | 每月 1 次 | — | — | `—` |
| 🟢 | `db-sync` | sync-db | 每天 | 10-28 09:28 | 5 小时 | `success` |
| 🟢 | `dongguaTV` | Android Build & Release | 无定时器 | 10-18 16:07 | 9.9 天 | `success` |
| 🟢 | `dongguaTV` | Sync db.json (from db-sync) | 每天 | 10-28 10:03 | 5 小时 | `success` |
| 🟢 | `dongguaTV` | Docker Build & Publish | 无定时器 | 10-18 15:48 | 10.0 天 | `success` |
| 🟢 | `dongguaTV` | 上游更新提醒 | 每天 | 10-28 06:25 | 8 小时 | `success` |
| 🟢 | `lxmusic` | Auto Sync & Keep Alive | 每天 | 10-28 07:50 | 7 小时 | `success` |
| 🟢 | `lxmusic` | 音源可用性检查 | 每天 | 10-27 21:05 | 18 小时 | `success` |
| ⚪ | `lxmusic` | Star History | — | — | — | `—` |
| 🟢 | `lxmusic` | pages-build-deployment | 无定时器 | 10-28 07:51 | 7 小时 | `success` |
| ⚪ | `tvbox-source-aggregator` | Build & Push Multi-Arch Docker Image | 无定时器 | — | — | `—` |

## 产物新鲜度

| | 仓库 | 文件 | 说明 | 最后提交 | 距今 |
|---|---|---|---|---|---|
| 🟢 | `db-sync` | `db.json` | 站点库 | 10-28 09:30 | 5 小时 |
| 🟢 | `dongguaTV` | `db.json` | 站点库 | 10-27 09:23 | 29 小时 |

---
判定口径：以 workflow 自身 cron 推算预期周期，超过 `max(2×周期, 周期+6h)` 未触发即判停摆；连续 2 次失败判异常。本文件由 `scripts/guard.py` 自动生成，勿手改。
