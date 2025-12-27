# Proposal: Split large `choice/` modules into smaller, single-purpose modules

**Change-id:** 2025-12-27-split-choice-modules

## Summary
当前 `choice/` 目录下部分源文件（尤其 `web.py`, `models.py`, `terminal.py`）体积较大，职责交叉，给维护、测试与扩展带来负担。提议按职责对现有代码进行模块化拆分（不改变外部公共 API 的语义），提升可维护性、测试覆盖与审阅速度。

## Goals
- 将大文件拆分为更小的、单一职责模块（每个模块尽量保持在 200 行左右） ✅
- 保持对外行为（工具契约、函数签名）兼容，逐步迁移测试以验证等价性 ✅
- 制定可回滚、分步骤的迁移计划，便于小批量提交和代码审查 ✅

## Non-Goals
- 在 proposal 阶段不做代码修改；实现细节将放在 `tasks.md` 和 `design.md` 中。 ❌

## High-level Module Map (建议)
- `choice/models.py` → 保留仅数据类（dataclasses）和常量
- `choice/validation.py` → 校验/parse_request、option 验证、选择模式转换等
- `choice/response.py` → normalize_response、cancelled_response、timeout_response
- `choice/storage.py` → 保留不动（小且职责单一）
- `choice/terminal/` (包)
  - `terminal/ui.py` → questionary UI 构建与提示函数
  - `terminal/runner.py` → timeout wrapper、`run_terminal_choice`、`prompt_configuration`
- `choice/web/` (包)
  - `web/templates.py` → HTML 渲染、模板加载、dashboard 渲染
  - `web/session.py` → `ChoiceSession` 类及其方法（广播/监控/close 等）
  - `web/server.py` → `WebChoiceServer`、路由注册及 lifecycle
  - `web/api.py` → 路由处理器（`submit_choice`、websocket handlers）可选的分离项
- `choice/orchestrator.py` → 保留为协调层，只依赖小模块的稳定接口

## Risks & Mitigations
- 风险：大型重命名/移动导致回归或测试过多失败。缓解：分小步实施，每步配套回归测试并保留兼容导出。
- 风险：导入循环。缓解：在设计阶段识别依赖方向，优先提取纯数据和工具函数（models/validation/response）以打破环路。

## Next step
参照 `tasks.md` 中的分步任务实现并运行 `openspec validate --strict` 与测试套件（`pytest`）。
