# 仓库巡检看板

> 最后尝试：**2026-11-28 20:07 UTC**
> 模式：🔓 PAT 模式

## 总览：⚫ 本轮未完成

原因：`列出仓库失败：HTTP 401 Unauthorized {
  "message": "Bad credentials",
  "documentation_url": "https://docs.github.com/rest",
  "status": "401"
}`

PAT 模式仍失败，通常是 **token 过期 / 权限不足 / GitHub 临时故障**。

检查：PAT 是否勾了 `repo`（或细粒度 token 的 Administration/Actions/Contents 只读）、是否已过期、`GH_PAT` secret 是否写错。


---
> 这一轮**不算任何仓库的故障**——是巡检自己的请求被拦下了，下一轮会自动重试。本文件由 `scripts/guard.py` 自动生成，勿手改。
