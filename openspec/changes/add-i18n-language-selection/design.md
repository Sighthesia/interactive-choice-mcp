# Design: i18n language selection

## Context
当前终端与 Web 界面只提供英文文案，用户无法在交互前切换语言，也没有集中管理的文案资源。需求是为交互界面增加中英文切换，并允许通过 MCP 环境变量预设默认语言。

## Goals / Non-Goals
- Goals:
  - 支持 en/zh 文案资源，终端与 Web 共用一致的 key 集。
  - 在交互配置面板/终端设置中可切换语言，立即影响当前会话且持久化。
  - 允许通过环境变量 `CHOICE_LANG` 预置默认语言，优先级高于已保存配置。
- Non-Goals:
  - 不引入其他语言或自动检测系统 locale。
  - 不翻译用户提供的内容（选项描述、prompt 等保持原文）。

## Decisions
- Decision: 新增 `language` 字段到 `ProvideChoiceConfig`，允许值 `en`/`zh`，缺失或非法值回退 `en`。
- Decision: 语言优先级为环境变量 `CHOICE_LANG` > 存储配置 > 代码默认值；无效 env 记录 warning 后使用英文。
- Decision: 文案存储使用共享资源模块（如 `choice/i18n.py`）返回 dict，终端与 Web 通过 key 查找，避免分散硬编码。
- Decision: 配置存储与 interaction store 在序列化/反序列化时保存语言字段，旧数据缺失时回退 `en`。

## Risks / Trade-offs
- 资源覆盖不全导致混合语言 → 通过单一资源模块和测试覆盖主要 UI 文案缓解。
- 新增字段影响旧配置加载 → 通过回退默认和迁移逻辑保证兼容。

## Migration Plan
- 配置加载时若无语言字段则默认 `en`。
- 首次启动读取 `CHOICE_LANG` 作为初始值并写入配置；若无 env，则继续使用存储值或默认。

## Open Questions
- 是否需要允许每次请求级别覆盖语言？（暂不支持，仍遵循全局/环境优先级。）
