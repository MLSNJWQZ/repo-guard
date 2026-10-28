# repo-guard

自动巡检**你名下所有仓库**的 GitHub Actions 健康度。不用维护监控名单——加新仓库、加新 workflow，下次巡检自动发现。

## 它能抓什么

| 检查项 | 说明 |
|---|---|
| **静默停摆** | 读每个 workflow 自己的 cron 表达式推算预期周期，超时未触发就报警。这是最难发现的一类故障：**workflow 状态仍显示 `active`，但 schedule 根本不跑**（fork 仓库尤其常见） |
| **连续失败** | 最近一次 failure，或连续 ≥2 次失败 |
| **workflow 被禁用** | `state != active` |
| **仓库归档/停用** | 整个仓库级异常 |
| **产物新鲜度** | 关键文件（如 `db.json`）最后一次提交距今过久 → 抓「workflow 成功了但没产出」 |

产出两样东西：`STATUS.md` 状态看板（自动提交），有异常时开 Issue 报警。

## 怎么用

### 方式一：fork 后直接用（覆盖公开仓库，零配置）

1. Fork 这个仓库
2. **到 Actions 页面点 `I understand my workflows, go ahead and re-enable them`** ← 这步不能省，见下方警告
3. 进 `Repo Guard - 全仓库巡检` → `Run workflow` 手动跑一次

账号名会自动从 `github.repository_owner` 取，**不需要改任何代码**。

> ⚠️ **fork 后必做第 2 步**：GitHub 默认禁用 fork 仓库的定时任务，而且**状态栏仍然显示 active**，只有 Actions 页面顶部有那条按钮。不点的话你会以为它在跑，其实一次都不会触发。这个坑我自己就踩过——一个 fork 来的仓库停摆了 7 天才被发现。

### 方式二：覆盖私有仓库（需要 PAT）

匿名 API 每小时只有 60 次额度，且读不到私有仓库。想全量覆盖：

1. 生成 token（两选一）
   - 经典 PAT：Settings → Developer settings → Personal access tokens → Tokens (classic)，勾选 **`repo`** + **`workflow`**
   - 细粒度 PAT：只读权限即可 —— **Administration: Read**、**Actions: Read**、**Contents: Read**，Repository access 选 **All repositories**
2. 本仓库 Settings → Secrets and variables → Actions → New repository secret
3. 名字填 `GH_PAT`，值贴 token
4. 重跑 workflow，看板顶部会变成「🔓 PAT 模式」

## 看板长什么样

```markdown
## 总览：🔴 有 1 项异常

🟢 正常 8 ｜ 🟡 留意 0 ｜ 🔴 异常 1

## 需要处理

| 级别 | 仓库 | 工作流 / 文件 | 最后运行 | 周期 | 说明 |
|---|---|---|---|---|---|
| 🔴 | `some-repo` | dns_push | 10-14 21:02 | 每 6 小时 | 14 天 未触发 → 疑似被 GitHub 静默停用 |
```

## 自定义

编辑 `scripts/guard.py` 顶部两个常量：

```python
# 想盯哪些关键产物不更新（仓库名 -> [(路径, 最大允许陈旧小时, 说明)]）
ARTIFACTS = {
    "your-repo": [("data.json", 96, "数据快照")],
}

# 实际周期与 cron 不符时强行覆盖，键为 "仓库名/工作流名"
PERIOD_OVERRIDE = {
    "your-repo/some-workflow": 12,
}
```

巡检频率改 `.github/workflows/guard.yml` 里的 cron。

## 判定口径

- **停摆只看 `schedule` 触发的运行**。手动跑（`workflow_dispatch`）不算数——否则每周手点一次就能掩盖定时任务已死，这是最容易自欺的地方。
- **停摆阈值** = `max(2 × 预期周期, 预期周期 + 6h)`。周期从 cron 推算：`*/N * * * *` → N 小时；`0 H * * *` → 24 小时；带星期/日期字段按周/月折算。
- **宽限期**：workflow 创建不满 2 天且尚未定时触发过的，跳过不报（刚建好还没轮到第一次 cron 是正常的）。
- **不算故障的状态**：`disabled_manually`（你自己关的）、`disabled_fork`（fork 默认禁用）、从未运行且无定时器（纯手动工作流）——统统归为 ⚪ 跳过。
- 连续 2 次 `failure` 判 🔴；最近 1 次失败或 10 次内失败 ≥3 次判 🟡。
- 退出码 1 表示有 🔴 异常。**workflow 显示红色叉是告警信号，不是脚本坏了**——它会先提交看板、开 Issue，最后才定结论。

## 架构：为什么要互锁

巡检器自己也依赖 GitHub 的 schedule，同样会被静默停用。所以需要两个仓库互相盯：

```
repo-guard        →  每 6 小时巡检所有仓库（含 db-sync 的 Guard）
db-sync / Guard   →  每天盯一次 repo-guard 是否还活着
```

任一方停摆，另一方都能发现。建议 fork 后照这个模式，在你最活跃的那个仓库里放一个只负责「检查本仓库最近一次运行时间」的小 workflow 当守门人。

## 本地运行（可选）

```bash
GH_PAT=<your_token> GH_OWNER=<your_name> python scripts/guard.py
```

Windows / 沙箱环境如果设了 `http_proxy`，urllib 可能被代理隧道卡死（curl 走同一代理却正常）。脚本默认忽略环境代理直连；确实需要走代理时加 `GH_USE_PROXY=1`。

## 已知限制

- **巡检器自己也可能被静默停用**。建议让另一个仓库的 workflow 反向盯这个仓库（取最近一次 run 的时间），形成互锁。
- 匿名模式下仓库多会触及 60 次/小时限额，脚本会提前截断并在看板标注「请求预算用尽」。
- 只能检查 GitHub 侧状态，管不了代码逻辑对不对、产物内容是否正确。
- 公开仓库的 workflow 会被读 cron，如果你的仓库是私有的且没配 PAT，会读不到。

## License

[MIT](LICENSE) © 2026 MLSNJWQZ

可自由使用、修改、再分发、商用，只需保留版权声明；作者不对使用后果承担责任。
