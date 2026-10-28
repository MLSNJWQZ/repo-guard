# 仓库巡检看板

> 最后巡检：**2026-10-28 13:25 UTC**
> 巡检器自身：上次运行 —前，结论 `—`
> 模式：⚠️ **匿名模式**：仅覆盖公开仓库，未认证限额 60 次/小时
> 覆盖：**5** 个仓库 / **15** 个 workflow ｜ 本次请求 39 次

## 总览：🔴 有 4 项异常

🟢 正常 11 ｜ 🟡 留意 0 ｜ 🔴 异常 4

## 需要处理

| 级别 | 仓库 | 工作流 / 文件 | 最后运行 | 周期 | 说明 |
|---|---|---|---|---|---|
| 🔴 | `db-sync` | keepalive | — | 每月 1 次 | 没有任何运行记录 |
| 🔴 | `lxmusic` | Star History | — | 每天 | workflow 状态为 `disabled_fork`（已被禁用）；没有任何运行记录 |
| 🔴 | `cf-speed-dns` | Cloudflare IP 优选并自动更新DNS (域名2) | 07-11 11:50 | 每 5 分钟 | workflow 状态为 `disabled_manually`（已被禁用）；109.1 天 未触发（预期每 5 分钟，容忍 6h）→ 疑似被 GitHub 静默停用 |
| 🔴 | `tvbox-source-aggregator` | Build & Push Multi-Arch Docker Image | — | 无定时器 | 没有任何运行记录 |
| 🔴 | `db-sync` | `feeds.txt`（采集源清单） | 10-18 13:52 | — | 10.0 天 没更新（阈值 96h）→ 跑了但没产出 |

## 全部工作流

| | 仓库 | 工作流 | 周期 | 最后运行 | 距今 | 最近结论 |
|---|---|---|---|---|---|---|
| 🔴 | `cf-speed-dns` | Cloudflare IP 优选并自动更新DNS (域名2) | 每 5 分钟 | 07-11 11:50 | 109.1 天 | `success` |
| 🔴 | `db-sync` | keepalive | 每月 1 次 | — | — | `—` |
| 🔴 | `lxmusic` | Star History | 每天 | — | — | `—` |
| 🔴 | `tvbox-source-aggregator` | Build & Push Multi-Arch Docker Image | 无定时器 | — | — | `—` |
| 🟢 | `cf-speed-dns` | dns_both_push | 每 6 小时 | 10-28 13:03 | 22 分钟 | `success` |
| 🟢 | `cf-speed-dns` | Keep Repo Alive | 每月 1 次 | 10-01 09:42 | 27.2 天 | `success` |
| 🟢 | `db-sync` | Guard - 巡检各仓库 Actions 存活 | 每天 | 10-28 06:12 | 7 小时 | `success` |
| 🟢 | `db-sync` | sync-db | 每天 | 10-28 09:28 | 4 小时 | `success` |
| 🟢 | `dongguaTV` | Android Build & Release | 无定时器 | 10-18 16:07 | 9.9 天 | `success` |
| 🟢 | `dongguaTV` | Sync db.json (from db-sync) | 每天 | 10-28 10:03 | 3 小时 | `success` |
| 🟢 | `dongguaTV` | Docker Build & Publish | 无定时器 | 10-18 15:48 | 9.9 天 | `success` |
| 🟢 | `dongguaTV` | 上游更新提醒 | 每天 | 10-28 06:25 | 7 小时 | `success` |
| 🟢 | `lxmusic` | Auto Sync & Keep Alive | 每天 | 10-28 07:50 | 6 小时 | `success` |
| 🟢 | `lxmusic` | 音源可用性检查 | 每天 | 10-27 21:05 | 16 小时 | `success` |
| 🟢 | `lxmusic` | pages-build-deployment | 无定时器 | 10-28 07:51 | 6 小时 | `success` |

## 产物新鲜度

| | 仓库 | 文件 | 说明 | 最后提交 | 距今 |
|---|---|---|---|---|---|
| 🔴 | `db-sync` | `feeds.txt` | 采集源清单 | 10-18 13:52 | 10.0 天 |
| 🟢 | `dongguaTV` | `db.json` | 站点库 | 10-27 09:23 | 28 小时 |

---
判定口径：以 workflow 自身 cron 推算预期周期，超过 `max(2×周期, 周期+6h)` 未触发即判停摆；连续 2 次失败判异常。本文件由 `scripts/guard.py` 自动生成，勿手改。
