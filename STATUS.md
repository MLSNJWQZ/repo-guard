# 仓库巡检看板

> 最后巡检：**2026-11-05 06:50 UTC**
> 巡检器自身：上次运行 11 小时前，结论 `success`
> 模式：🔓 **PAT 模式**：覆盖全部仓库（含私有）
> 覆盖：**8** 个仓库 / **15** 个 workflow ｜ 本次请求 37 次

## 总览：🟡 3 项需留意

🟢 正常 10 ｜ 🟡 留意 3 ｜ 🔴 异常 0 ｜ ⚪ 跳过 2

> ⚪ 跳过＝按预期不运行，不算故障：手动禁用的、fork 仓库默认禁用的、纯手动触发从未跑过的、以及刚建还没到首个触发周期的。

## 自愈

> 🧪 **dry-run 演练**（只决策，不发写请求） ｜ 命中 0 项 ｜ 可自动修 0 ｜ 需人工 0 ｜ 顺延 0

> 本轮没有需要自愈的目标。

## 需要处理

| 级别 | 仓库 | 工作流 / 文件 | 最后定时触发 | 周期 | 说明 |
|---|---|---|---|---|---|
| 🟡 | `lxmusic` | Auto Sync & Keep Alive | 11-04 08:29 | 每天 | 最近 30 次里失败 3 次 |
| 🟡 | `dongguaTV` | 上游更新提醒 | 11-04 07:03 | 每天 | 最近 24 次里失败 4 次 |
| 🟡 | `db-sync` | sync-db | 11-04 10:41 | 每天 | 最近一次运行失败 |

## 全部工作流

| | 仓库 | 工作流 | 周期 | 最后定时触发 | 距今 | 最近结论 |
|---|---|---|---|---|---|---|
| 🟡 | `db-sync` | sync-db | 每天 | 11-04 10:41 | 20 小时 | `failure` |
| 🟡 | `dongguaTV` | 上游更新提醒 | 每天 | 11-04 07:03 | 24 小时 | `success` |
| 🟡 | `lxmusic` | Auto Sync & Keep Alive | 每天 | 11-04 08:29 | 22 小时 | `success` |
| 🟢 | `cf-speed-dns` | dns_both_push | 每 6 小时 | 11-05 05:37 | 1 小时 | `success` |
| 🟢 | `cf-speed-dns` | Keep Repo Alive | 每月 1 次 | 11-01 10:03 | 3.9 天 | `success` |
| ⚪ | `cf-speed-dns` | Cloudflare IP 优选并自动更新DNS (域名2) | — | — | — | `—` |
| 🟢 | `db-sync` | Guard - 巡检定时任务存活（互锁） | 每天 | 11-04 06:55 | 24 小时 | `success` |
| 🟢 | `db-sync` | keepalive | 每月 1 次 | 11-01 11:09 | 3.8 天 | `success` |
| 🟢 | `dongguaTV` | Android Build & Release | 无定时器 | 11-04 17:10 | 14 小时 | `success` |
| 🟢 | `dongguaTV` | Docker Build & Publish | 无定时器 | 10-29 16:07 | 6.6 天 | `success` |
| 🟢 | `lxmusic` | 音源可用性检查 | 每天 | 11-04 22:21 | 8 小时 | `success` |
| 🟢 | `lxmusic` | Star History | 每天 | 11-04 07:31 | 23 小时 | `success` |
| 🟢 | `lxmusic` | pages-build-deployment | 无定时器 | 11-01 09:57 | 3.9 天 | `success` |
| 🟢 | `pano-landing` | pages-build-deployment | 无定时器 | 11-01 07:32 | 4.0 天 | `success` |
| ⚪ | `tvbox-source-aggregator` | Build & Push Multi-Arch Docker Image | — | — | — | `—` |

## 产物新鲜度

| | 仓库 | 文件 | 说明 | 最后提交 | 距今 |
|---|---|---|---|---|---|
| 🟢 | `dongguaTV` | `db.json` | 站点库 | 11-04 16:48 | 14 小时 |
| 🟢 | `db-sync` | `db.json` | 站点库 | 11-03 10:40 | 44 小时 |

## 未纳入巡检

- `dsh-purge`：没有配置任何 workflow

---
判定口径：以 workflow 自身 cron 推算预期周期，超过 `max(2×周期, 周期+6h)` 未触发即判停摆；连续 2 次失败判异常。本文件由 `scripts/guard.py` 自动生成，勿手改。
