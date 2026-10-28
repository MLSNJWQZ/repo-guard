# repo-guard · 仓库哨兵

自动巡检**你名下所有仓库**的 GitHub Actions 健康度。不用维护监控名单——加新仓库、加新 workflow，下次巡检自动发现。

> 🚀 **最快用法**：仓库页右上角 **`Use this template` → `Create a new repository`**，建完就不用管了。不要用 Fork——见[为什么](#怎么用)。

> 中文名「仓库哨兵」：`repo` = repository（仓库），`guard` = 守卫。GitHub 不允许仓库名用中文，所以英文链接名固定为 `repo-guard`，中文标识放在这里和仓库简介里。

## 它能抓什么

| 检查项 | 说明 |
|---|---|
| **静默停摆** | 读每个 workflow 自己的 cron 表达式推算预期周期，超时未触发就报警。这是最难发现的一类故障：**workflow 状态仍显示 `active`，但 schedule 根本不跑**（fork 仓库尤其常见） |
| **连续失败** | 最近一次 failure，或连续 ≥2 次失败 |
| **workflow 被禁用** | `state != active` |
| **仓库归档/停用** | 整个仓库级异常 |
| **产物新鲜度** | 关键文件（如 `db.json`）最后一次提交距今过久 → 抓「workflow 成功了但没产出」 |

产出两样东西：`STATUS.md` 状态看板（自动提交），有异常时开 Issue 报警。

## 发现异常之后：自愈（可选）

默认**关着**。开启后，它能自动修一件事：**把被 GitHub 停掉/挂死的定时器重新挂上**。

| 故障 | 自愈做什么 | 需要档位 |
|---|---|---|
| workflow 被 GitHub 静默停用（`state=disabled_inactivity`，仓库长期无活动导致） | `PUT .../enable` 重新启用 | `safe` |
| 状态还是 `active`，但定时器已超期不再触发 | `disable → enable` 重置定时器 | `full` |

**它故意不碰的东西**：跑失败的 workflow、产物不新鲜的、仓库归档的、代码有 bug 的。这些的原因在代码或上游数据里，机器人乱改只会把小问题变成大问题。所以自愈只做「不执行对方代码」的动作——重新挂定时器，不跑任何脚本、不改任何文件。

### 三档 + 一个演练档

`Settings → Secrets and variables → Actions → **Variables** → New repository variable`，名字 `FIX_LEVEL`：

| 值 | 行为 |
|---|---|
| `off` | 默认。只报告，一个写请求都不发 |
| `dry-run` | **建议先跑这个**。算出「本该修什么」写进看板和日志，但不执行 |
| `safe` | 自动启用被静默停用的 workflow |
| `full` | safe + 重置「挂着却不触发」的定时器 |

不设这个变量就是 `off`，fork 的人什么都不用管。

### 四条护栏

1. **留痕**：每次实际动作追加进 `heal_log.md`，看板里有「自愈」一节，Issue 正文也会写。修了什么、什么时候修的，都能翻。
2. **限频**：单轮最多修 3 个目标（`FIX_MAX_PER_RUN`）；同一目标 7 天内最多试 3 次（`FIX_MAX_PER_TARGET`），超了不再修，标成「需人工」——防止和 GitHub 死磕。
3. **不自杀**：巡检器自己所在的仓库永远不自动修。它不运行就没人来修它，只能人工点。
4. **改错不生效**：`FIX_LEVEL` 拼错（比如 `saf`）一律降级成 `off`，不会因为手滑就乱动你的仓库。

修过的目标当轮仍记为异常（要等下一轮巡检复核它是否真的活了），只是会多一句「本轮已自愈，下次巡检复核」。

## 怎么用

**最快路径是「Use this template」，不是 Fork。** 差别只有一点，但很致命：GitHub 官方文档写明「public 仓库被 fork 时，**scheduled workflow 默认被禁用**」；用模板创建是文件拷贝，不受这条限制。

### 方式一（推荐）：Use this template —— 建完就完事

1. 仓库页右上角 **`Use this template` → `Create a new repository`**
2. 结束。不用改代码、不用配 secret、不用点任何按钮

第一次巡检会在建仓时的 push 事件里自动跑，之后每 6 小时一次，看板自动提交到 `STATUS.md`。
（万一 Actions 页仍提示要 enable——偶发——点一次就行。）

### 方式二：Fork

fork 同样零改代码，但**必须手动点一次**：

1. Fork
2. 到 Actions 页点 `I understand my workflows, go ahead and re-enable them` ← 不能省
3. 进 `Repo Guard - 全仓库巡检` → `Run workflow` 跑一次

> ⚠️ 为什么 fork 必须点这一步：GitHub 默认禁用 fork 仓库的定时任务，而且**状态栏仍然显示 active**，只有 Actions 页顶部有那条按钮。不点的话你会以为它在跑，其实一次都不会触发。这个坑我自己就踩过——一个 fork 来的仓库停摆了 7 天才被发现。

### 可选：覆盖私有仓库 / 提高额度

上面两种**不配任何东西就能跑**，代价是：只扫公开仓库 + 每小时 60 次请求（按出口 IP 算，共享网络可能被别人耗光）。想把私有仓库也纳入、额度提到 5000 次/小时：

1. 生成 token（两选一）
   - 经典 PAT：Settings → Developer settings → Personal access tokens → Tokens (classic)，勾 **`repo`** + **`workflow`**
   - 细粒度 PAT：只读即可 —— **Administration: Read**、**Actions: Read**、**Contents: Read**，Repository access 选 **All repositories**
2. 本仓库 Settings → Secrets and variables → Actions → New repository secret
3. 名字填 `GH_PAT`，值贴 token
4. 重跑一次，看板顶部会变成「🔓 PAT 模式」

### 为什么能做到「不用改」

账号名、仓库名、连它自己这个 workflow 文件叫什么，全都是自动识别的（`github.repository_owner` / `GITHUB_REPOSITORY` / `GITHUB_WORKFLOW_REF`）。仓库你想改名叫什么都行，代码一行不用动。

唯一残留的「个性化」是 `ARTIFACTS`（盯哪些关键文件不更新），键是**仓库名**。别人的仓库名对不上就是空操作——不报错、不误报，只是不做这一项。想用自己加一行。

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
# 想顺带看自愈会做什么（不发写请求）：
GH_PAT=<your_token> GH_OWNER=<your_name> FIX_LEVEL=dry-run python scripts/guard.py
```

Windows / 沙箱环境如果设了 `http_proxy`，urllib 可能被代理隧道卡死（curl 走同一代理却正常）。脚本默认忽略环境代理直连；确实需要走代理时加 `GH_USE_PROXY=1`。

## 已知限制

- **巡检器自己也可能被静默停用**。建议让另一个仓库的 workflow 反向盯这个仓库（取最近一次 run 的时间），形成互锁。自愈也修不了它自己——它不跑就没人来修它。
- **自愈只修定时器，不修代码**。workflow 连续失败说明脚本或上游真有问题，那得看日志，不是 re-enable 能解决的。
- 自愈需要 workflow 的 `actions: write` 权限（本仓库 `.github/workflows/guard.yml` 已声明）；用 PAT 模式时 token 还得有 `workflow` scope，否则会报 403。
- 匿名模式下仓库多会触及 60 次/小时限额，脚本会提前截断并在看板标注「请求预算用尽」。
- 只能检查 GitHub 侧状态，管不了代码逻辑对不对、产物内容是否正确。
- 公开仓库的 workflow 会被读 cron，如果你的仓库是私有的且没配 PAT，会读不到。

## License

[MIT](LICENSE) © 2026 MLSNJWQZ

可自由使用、修改、再分发、商用，只需保留版权声明；作者不对使用后果承担责任。
