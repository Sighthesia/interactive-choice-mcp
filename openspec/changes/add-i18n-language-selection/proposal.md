# Change: Add i18n language selection

## Why
- 目前终端与 Web 文本仅英文，无法满足中文用户的可用性。
- 需要统一入口让用户在交互前选择界面语言，并能持久化偏好。
- MCP 环境变量需要能够预设交互语言，方便代理层统一配置。

## What Changes
- 提供中英文文案资源并让终端/Web 共用，保持提示、按钮、设置等文本一致。
- 在交互设置中暴露语言选择并立即应用到当前会话，同时持久化到配置。
- 支持通过 MCP 环境变量 `CHOICE_LANG` 设定默认语言（en/zh），无效值回退英文并记录警告。
- 将语言偏好透传到交互流程（orchestrator、terminal/web UI、存储），确保 session 重启后仍可复用。

## Impact
- Affected specs: choice-orchestration
- Affected code: choice/models.py, choice/validation.py, choice/storage.py, choice/orchestrator.py, choice/terminal/*, choice/web/*, templates
- Breaking changes: None (新增能力)
