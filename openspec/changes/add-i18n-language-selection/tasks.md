# Tasks: Add i18n language selection

## Phase 1: Configuration & Resources
- [ ] 1.1 为 `ProvideChoiceConfig` 增加语言字段（en/zh），在校验与默认值中支持回退英文。
- [ ] 1.2 读取 MCP 环境变量 `CHOICE_LANG` 作为默认语言优先级，记录无效值警告并回退。
- [ ] 1.3 引入共享文案资源（en/zh），覆盖终端与 Web 的提示、按钮、设置项文本。

## Phase 2: Orchestration & Persistence
- [ ] 2.1 在 orchestrator 初始化/启动时加载语言默认值（env -> 持久化配置 -> 默认 en），并传递到 session。
- [ ] 2.2 更新配置存储与交互列表持久化，保存/恢复语言偏好，确保缺失字段时平滑回退。

## Phase 3: Terminal/Web Integration
- [ ] 3.1 终端 UI：设置界面支持语言切换，渲染文案根据当前语言切换且在会话内即时生效。
- [ ] 3.2 Web UI：设置面板支持语言切换，模板与交互列表文案使用 i18n 资源并随选择更新。

## Phase 4: Validation & Docs
- [ ] 4.1 添加覆盖 env 回退、配置持久化、终端/Web 文案切换的测试。
- [ ] 4.2 更新 AGENTS/README 等文档并运行 `openspec validate add-i18n-language-selection --strict`。
