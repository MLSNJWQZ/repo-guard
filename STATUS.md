# 仓库巡检看板

> 最后巡检：**2026-10-30 22:23 UTC**
> 巡检器自身：上次运行 9 小时前，结论 `success`
> 模式：🔓 **PAT 模式**：覆盖全部仓库（含私有）
> 覆盖：**6** 个仓库 / **15** 个 workflow ｜ 本次请求 35 次

## 总览：🟡 1 项需留意

🟢 正常 11 ｜ 🟡 留意 1 ｜ 🔴 异常 0 ｜ ⚪ 跳过 3

> ⚪ 跳过＝按预期不运行，不算故障：手动禁用的、fork 仓库默认禁用的、纯手动触发从未跑过的、以及刚建还没到首个触发周期的。

## 自愈

> 🧪 **dry-run 演练**（只决策，不发写请求） ｜ 命中 0 项 ｜ 可自动修 0 ｜ 需人工 0 ｜ 顺延 0

> 本轮没有需要自愈的目标。

## 需要处理

| 级别 | 仓库 | 工作流 / 文件 | 最后定时触发 | 周期 | 说明 |
|---|---|---|---|---|---|
| 🟡 | `lxmusic` | Auto Sync & Keep Alive | 10-30 07:58 | 每天 | 最近 30 次里失败 3 次 |

## 全部工作流

| | 仓库 | 工作流 | 周期 | 最后定时触发 | 距今 | 最近结论 |
|---|---|---|---|---|---|---|
| 🟡 | `lxmusic` | Auto Sync & Keep Alive | 每天 | 10-30 07:58 | 14 小时 | `success` |
| 🟢 | `cf-speed-dns` | dns_both_push | 每 6 小时 | 10-30 22:00 | 23 分钟 | `success` |
| 🟢 | `cf-speed-dns` | Keep Repo Alive | 每月 1 次 | 10-01 09:42 | 29.5 天 | `success` |
| ⚪ | `cf-speed-dns` | Cloudflare IP 优选并自动更新DNS (域名2) | — | — | — | `—` |
| 🟢 | `db-sync` | Guard - 巡检定时任务存活（互锁） | 每天 | 10-30 06:20 | 16 小时 | `success` |
| ⚪ | `db-sync` | keepalive | 每月 1 次 | — | — | `—` |
| 🟢 | `db-sync` | sync-db | 每天 | 10-30 09:47 | 13 小时 | `success` |
| 🟢 | `dongguaTV` | Android Build & Release | 无定时器 | 10-28 16:37 | 2.2 天 | `success` |
| 🟢 | `dongguaTV` | Sync db.json (from db-sync) | 每天 | 10-30 10:29 | 12 小时 | `success` |
| 🟢 | `dongguaTV` | Docker Build & Publish | 无定时器 | 10-29 16:07 | 30 小时 | `success` |
| 🟢 | `dongguaTV` | 上游更新提醒 | 每天 | 10-30 06:36 | 16 小时 | `success` |
| 🟢 | `lxmusic` | 音源可用性检查 | 每天 | 10-30 21:18 | 1 小时 | `success` |
| 🟢 | `lxmusic` | Star History | 每天 | 10-30 07:13 | 15 小时 | `success` |
| 🟢 | `lxmusic` | pages-build-deployment | 无定时器 | 10-29 10:09 | 36 小时 | `success` |
| ⚪ | `tvbox-source-aggregator` | Build & Push Multi-Arch Docker Image | — | — | — | `—` |

## 产物新鲜度

| | 仓库 | 文件 | 说明 | 最后提交 | 距今 |
|---|---|---|---|---|---|
| 🟢 | `dongguaTV` | `db.json` | 站点库 | 10-30 10:29 | 12 小时 |
| 🟢 | `db-sync` | `db.json` | 站点库 | 10-30 09:48 | 13 小时 |

---
判定口径：以 workflow 自身 cron 推算预期周期，超过 `max(2×周期, 周期+6h)` 未触发即判停摆；连续 2 次失败判异常。本文件由 `scripts/guard.py` 自动生成，勿手改。
