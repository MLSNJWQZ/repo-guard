# 仓库巡检看板

> 最后巡检：**2026-10-28 22:37 UTC**
> 巡检器自身：上次运行 6 小时前，结论 `failure`
> 模式：🔓 **PAT 模式**：覆盖全部仓库（含私有）
> 覆盖：**6** 个仓库 / **15** 个 workflow ｜ 本次请求 37 次

## 总览：🔴 有 1 项异常

🟢 正常 11 ｜ 🟡 留意 1 ｜ 🔴 异常 1 ｜ ⚪ 跳过 2

> ⚪ 跳过＝按预期不运行，不算故障：手动禁用的、fork 仓库默认禁用的、纯手动触发从未跑过的、以及刚建还没到首个触发周期的。

## 自愈

> 🧪 **dry-run 演练**（只决策，不发写请求） ｜ 命中 0 项 ｜ 可自动修 0 ｜ 需人工 0 ｜ 顺延 0

> 本轮没有需要自愈的目标。

## 需要处理

| 级别 | 仓库 | 工作流 / 文件 | 最后定时触发 | 周期 | 说明 |
|---|---|---|---|---|---|
| 🔴 | `lxmusic` | Star History | — | 每天 | 配置了定时器但从未运行过 |
| 🟡 | `tvbox-source-aggregator` | Build & Push Multi-Arch Docker Image | 10-28 16:51 | 无定时器 | 最近一次运行失败 |

## 全部工作流

| | 仓库 | 工作流 | 周期 | 最后定时触发 | 距今 | 最近结论 |
|---|---|---|---|---|---|---|
| 🔴 | `lxmusic` | Star History | 每天 | — | — | `—` |
| 🟡 | `tvbox-source-aggregator` | Build & Push Multi-Arch Docker Image | 无定时器 | 10-28 16:51 | 6 小时 | `failure` |
| 🟢 | `cf-speed-dns` | dns_both_push | 每 6 小时 | 10-28 22:18 | 19 分钟 | `success` |
| 🟢 | `cf-speed-dns` | Keep Repo Alive | 每月 1 次 | 10-01 09:42 | 27.5 天 | `success` |
| ⚪ | `cf-speed-dns` | Cloudflare IP 优选并自动更新DNS (域名2) | — | — | — | `—` |
| 🟢 | `db-sync` | Guard - 巡检定时任务存活（互锁） | 每天 | 10-28 06:12 | 16 小时 | `success` |
| ⚪ | `db-sync` | keepalive | 每月 1 次 | — | — | `—` |
| 🟢 | `db-sync` | sync-db | 每天 | 10-28 09:28 | 13 小时 | `success` |
| 🟢 | `dongguaTV` | Android Build & Release | 无定时器 | 10-28 16:37 | 6 小时 | `success` |
| 🟢 | `dongguaTV` | Sync db.json (from db-sync) | 每天 | 10-28 10:03 | 13 小时 | `success` |
| 🟢 | `dongguaTV` | Docker Build & Publish | 无定时器 | 10-18 15:48 | 10.3 天 | `success` |
| 🟢 | `dongguaTV` | 上游更新提醒 | 每天 | 10-28 06:25 | 16 小时 | `success` |
| 🟢 | `lxmusic` | Auto Sync & Keep Alive | 每天 | 10-28 07:50 | 15 小时 | `success` |
| 🟢 | `lxmusic` | 音源可用性检查 | 每天 | 10-28 21:28 | 1 小时 | `success` |
| 🟢 | `lxmusic` | pages-build-deployment | 无定时器 | 10-28 21:29 | 1 小时 | `success` |

## 产物新鲜度

| | 仓库 | 文件 | 说明 | 最后提交 | 距今 |
|---|---|---|---|---|---|
| 🟢 | `dongguaTV` | `db.json` | 站点库 | 10-27 09:23 | 37 小时 |
| 🟢 | `db-sync` | `db.json` | 站点库 | 10-28 09:30 | 13 小时 |

---
判定口径：以 workflow 自身 cron 推算预期周期，超过 `max(2×周期, 周期+6h)` 未触发即判停摆；连续 2 次失败判异常。本文件由 `scripts/guard.py` 自动生成，勿手改。
