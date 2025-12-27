# Tasks for: 2025-12-27-split-choice-modules

🎯 目标：按小步骤安全地将 `choice/` 中的大文件拆分为单一职责模块并保持兼容性。

1. Discovery (small, non-invasive)
   - [x] 列出每个待拆分文件的函数/类/变量公共表（`grep` + `rg`）。
   - 验证点：生成一个 `CHANGELOG.md` 风格的映射（旧位置 → 新位置）。

2. Create new module scaffolding + tests (no behavioral change)
   - [x] 新建目标模块文件（空实现或者仅写 docstring 和 `__all__`）并添加导出占位符。
   - [x] 为每个即将移动的单元添加一个单元测试（或迁移现有测试）并确保测试在旧导出下仍能通过。
   - 验证点：CI 在不修改功能的前提下全部通过（现有测试不变）。

3. Move code in small commits
   - [x] 将 `models` 的验证逻辑移到 `validation.py`（保留 `models.parse_request` 代理一段时间以保证兼容性）。
   - [x] 将响应生成逻辑移动到 `response.py`（`normalize_response` 等）。
   - [x] 将 `web.py` 拆为 `web/server.py`、`web/session.py`、`web/templates.py`。每次移动后运行测试并确保导入兼容。 
   - [x] 将 `terminal.py` 拆为 `terminal/ui.py` 和 `terminal/runner.py`。
   - 验证点：每个提交都应包含对应测试，且 `pytest` 绿灯。

4. API & import surface hardening
   - [x] 在原文件中加入短期代理（`from .validation import parse_request as parse_request`）并标注 `# TODO: remove in vX.Y`。
   - [x] 更新 `__init__.py`（如需要）以保持外部使用方式不变。
   - 验证点：Tool binding（`server.py`、`orchestrator.py`）导入不变，`mypy`/类型检查通过。

5. Cleanup & docs
   - [x] 移除过时代理，执行一次全项目搜索确认没有引用旧位置。
   - [x] 更新 `README.md` / `AGENTS.md` 中的架构图与说明。
   - 验证点：最终提交包含变更说明、测试覆盖率未下降。

6. Validation & release
   - [ ] 运行 `openspec validate 2025-12-27-split-choice-modules --strict` 并修复问题。
   - [ ] 发布一个小版本并观察用户/CI 是否有回归。

---

时间线建议：把实现分成 6–10 个小 PR，每个 PR 只移动或修改 1–2 个小组件以便审查。
