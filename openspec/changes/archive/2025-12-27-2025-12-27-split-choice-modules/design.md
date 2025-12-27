# Design Notes: Module split for `choice/`

## What
将 `choice/` 中体积较大的文件拆分为更细粒度的模块，按职责隔离数据模型、验证、响应、web runtime、web route handlers、terminal UI 与 runner、以及持久化。该设计不改变对外 contract，仅重构内部实现。

## How (关键数据流与依赖方向)
- 依赖方向应保持从上层到下层：
  - `orchestrator` → `web` / `terminal` / `storage`
  - `web` / `terminal` → `models` / `validation` / `response`
- 抽象点：`models` 提供纯数据结构；`validation` 和 `response` 提供无副作用的函数，便于单元测试。

## Why (权衡与动机)
- 可维护性：较小文件更易审查与贡献；每次 PR 变更范围小。
- 测试性：将逻辑拆分后可以更容易建立边界测试（validation、serialization、session lifecycle）。
- 扩展性：例如将来添加 websocket 超时同步或仪表盘功能可以仅修改 `web/session.py`。

权衡：更多文件意味着更多导入点与轻微的导航成本。我们通过稳定的导出/兼容代理（短期）来降低迁移风险。

## Analysis (风险、边界条件、未来扩展)
- 导入循环：在拆分初期优先提取不依赖于其它模块的纯函数（`validation`、`response`）。
- 向后兼容：保留原有函数签名与在旧位置的代理导出，增加 deprecation 注释，计划在下一个主版本移除代理。

## Migration policy
- 分阶段：先创建新文件并添加代理；随后分批移动实现并迁移测试；最后删除代理并清理。
- 每一步必须保证 CI 绿灯并通过 `pytest`。
