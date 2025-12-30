# Interactive Choice MCP

一个服务器，为 AI 代理提供结构化的人机交互决策能力。通过 `provide_choice` 工具，AI 可以在需要用户决策时暂停执行，提供清晰的选项界面，避免猜测用户意图。

## ✨ 核心特性

### 🎯 智能决策支持
- **多选模式**：支持单选和多选，满足不同决策场景
- **推荐选项**：AI 可以标记推荐选项，帮助用户快速决策
- **超时处理**：内置超时机制，确保流程不会无限期阻塞
- **取消支持**：用户随时可以取消操作，保持控制权

### 🌐 双传输模式
- **Web 模式**：自动启动本地 Web 服务器，提供现代化的浏览器界面
- **终端模式**：通过 `questionary` 提供流畅的终端交互体验
- **无缝切换**：支持从终端切换到 Web 界面，满足不同场景需求

### 🔧 企业级特性
- **配置持久化**：用户偏好自动保存，包括传输模式、语言设置等
- **会话历史**：自动记录交互历史，支持查看和审计
- **国际化支持**：内置中英文界面，可扩展更多语言
- **结构化输出**：终端模式提供机器可解析的输出标记

## 📦 安装

### 前置要求
- Python 3.12 或更高版本
- [uv](https://github.com/astral-sh/uv) 包管理器（推荐）

### 快速开始

```bash
# 克隆仓库
git clone https://github.com/Sighthesia/interactive-choice-mcp.git
cd interactive-choice-mcp

# 同步依赖
uv sync

# 验证安装
uv run pytest
```

## 🚀 快速配置

### 1. MCP 配置

编辑 IDE 或 Coding Agent的配置 (Claude Desktop)（通常位于 `~/Library/Application Support/Claude/claude_desktop_config.json` 或 `%APPDATA%\Claude\claude_desktop_config.json`）：

```json
{
  "mcpServers": {
    "interactive-choice": {
      "command": "uv",
      "args": [
        "--directory",
        "/path/to/interactive-choice-mcp",
        "run",
        "server.py"
      ]
    }
  }
}
```

**提示**：将 `/path/to/interactive-choice-mcp` 替换为实际路径，如 `~/interactive-choice-mcp`。

### 2. 启用调试模式（可选）

```json
{
  "mcpServers": {
    "interactive-choice": {
      "command": "uv",
      "args": [
        "--directory",
        "/path/to/interactive-choice-mcp",
        "run",
        "server.py"
      ],
      "env": {
        "CHOICE_LOG_LEVEL": "DEBUG",
        "CHOICE_LOG_FILE": "~/.local/share/interactive-choice-mcp/server.log"
      }
    }
  }
}
```

## 📖 使用指南

### 基础用法

AI 代理可以在需要用户决策时调用 `provide_choice` 工具：

```python
# AI 代理代码示例
result = provide_choice(
    title="选择前端框架",
    prompt="检测到多个可用的前端框架。请选择要使用的框架：",
    selection_mode="single",
    options=[
        {
            "id": "react",
            "description": "React - Facebook 开发的流行 UI 库，组件化设计",
            "recommended": True
        },
        {
            "id": "vue",
            "description": "Vue - 渐进式 JavaScript 框架，易于上手",
            "recommended": False
        },
        {
            "id": "angular",
            "description": "Angular - Google 开发的企业级框架",
            "recommended": False
        }
    ]
)
```

### 工作流程

#### Web 模式（默认）
1. **自动启动**：工具自动启动本地 Web 服务器
2. **浏览器交互**：用户在浏览器中查看选项并做出选择
3. **结果返回**：工具阻塞等待用户完成，返回选择结果

#### 终端模式
1. **命令生成**：工具返回终端命令和会话 ID
2. **终端执行**：AI 代理在终端中执行命令
3. **交互选择**：用户在终端 UI 中完成选择
4. **结果轮询**：AI 代理使用 `poll_selection` 工具获取结果

```json
// 终端模式响应示例
{
  "action_status": "pending_terminal_launch",
  "terminal_command": "uv run python -m src.terminal.client --session abc123 --url http://127.0.0.1:17863",
  "session_id": "abc123",
  "instructions": "执行终端命令以启动交互界面"
}
```

### 高级功能

#### 1. 注释功能
用户可以为选择添加备注：

```bash
uv run python -m src.terminal.client --session abc123 --url http://127.0.0.1:17863 --annotate
```

#### 2. 静默模式
隐藏选项描述，仅显示 ID：

```bash
uv run python -m src.terminal.client --session abc123 --url http://127.0.0.1:17863 --quiet
```

#### 3. 会话历史
Web 界面自动显示最近的交互历史，支持查看详情和重新使用配置。

## ⚙️ 配置选项

### 环境变量

| 变量名             | 默认值      | 说明                                          |
| ------------------ | ----------- | --------------------------------------------- |
| `CHOICE_WEB_HOST`  | `127.0.0.1` | Web 服务器绑定地址                            |
| `CHOICE_WEB_PORT`  | `17863`     | Web 服务器端口（自动选择空闲端口）            |
| `CHOICE_LOG_LEVEL` | `INFO`      | 日志级别：`DEBUG`, `INFO`, `WARNING`, `ERROR` |
| `CHOICE_LOG_FILE`  | 无          | 日志文件路径                                  |
| `CHOICE_LANG`      | `zh`        | 界面语言：`en`, `zh`                          |

### 持久化配置

用户偏好自动保存到 `.mcp-data/config.json`：

```json
{
  "transport": "web",
  "language": "zh",
  "timeout_seconds": 600,
  "single_submit_mode": true,
  "use_default_option": false,
  "timeout_action": "submit",
  "notify_new": true,
  "notify_timeout": true
}
```

## 🏗️ 架构设计

```
interactive-choice-mcp/
├── server.py              # MCP 服务器入口（provide_choice, poll_selection）
├── main.py                # CLI 入口
├── src/
│   ├── core/              # 核心业务逻辑
│   │   ├── models.py      # 数据模型、验证、状态枚举
│   │   ├── orchestrator.py # 会话调度协调器
│   │   ├── validation.py  # 请求校验
│   │   └── response.py    # 响应归一化
│   ├── infra/             # 基础设施服务
│   │   ├── logging.py     # 日志配置
│   │   ├── storage.py     # 配置持久化
│   │   ├── paths.py       # 路径解析
│   │   └── i18n.py        # 国际化文案（en/zh）
│   ├── store/             # 数据存储
│   │   └── interaction_store.py # Session 历史持久化
│   ├── terminal/          # 终端传输层
│   │   ├── runner.py      # 终端交互运行器
│   │   ├── client.py      # CLI 客户端
│   │   ├── session.py     # 会话管理
│   │   └── ui.py          # questionary UI
│   └── web/               # Web 传输层
│       ├── server.py      # FastAPI 服务器
│       ├── session.py     # WebSocket 会话
│       ├── bundler.py     # 前端资源打包
│       ├── templates.py   # HTML 模板生成
│       └── frontend/      # 前端资源
│           ├── scripts/   # JavaScript 模块
│           ├── styles/    # CSS 样式
│           └── templates/ # HTML 模板
├── tests/                 # 测试套件
│   ├── unit/              # 单元测试
│   │   ├── core/          # 核心模块测试
│   │   ├── infra/         # 基础设施测试
│   │   ├── store/         # 存储模块测试
│   │   ├── terminal/      # 终端模块测试
│   │   └── web/           # Web 模块测试
│   └── integration/       # 集成测试
└── openspec/              # 项目规范文档
```

### 核心模块

- **ChoiceOrchestrator**：中央调度器，负责验证请求、选择传输方式、协调会话生命周期
- **ConfigStore**：配置持久化管理，支持环境变量覆盖
- **ChoiceSession**：统一的会话模型，支持 Web 和终端两种传输方式
- **InteractionStore**：会话历史存储，支持自动清理和审计

## 🧪 测试

```bash
# 运行完整测试套件
uv run pytest tests/ -v

# 运行单元测试
uv run pytest tests/unit/ -v

# 运行特定模块测试
uv run pytest tests/unit/core/ -v

# 运行集成测试
uv run pytest tests/integration/ -v

# 查看覆盖率
uv run pytest --cov=src --cov-report=html
```

## 🐛 调试

### 启用调试日志

```bash
export CHOICE_LOG_LEVEL=DEBUG
export CHOICE_LOG_FILE=~/.local/share/interactive-choice-mcp/server.log
```

### 使用 MCP Inspector

```bash
uv run mcp dev server.py
```

### 日志示例

```
2024-12-29 10:00:00 | INFO     | choice.orchestrator  | Handling choice request
2024-12-29 10:00:00 | INFO     | choice.server        | Starting web server on http://127.0.0.1:17863
2024-12-29 10:00:00 | INFO     | choice.server        | Created session abc123: timeout=600s
2024-12-29 10:00:15 | INFO     | choice.server        | Session abc123 submitted: selected=['react']
```

## 🤝 贡献

欢迎任何贡献！无论是报告问题、提出功能请求，还是提交代码改进，都非常感谢。

### 开发流程

1. Fork 本仓库
2. 创建特性分支：`git checkout -b feature/amazing-feature`
3. 提交更改：`git commit -m 'Add amazing feature'`
4. 推送到分支：`git push origin feature/amazing-feature`
5. 开启 Pull Request

## 💖 致谢

- [mcp-feedback-enhanced](https://github.com/Minidoracat/mcp-feedback-enhanced) - 项目参考和灵感来源
- [FastMCP](https://github.com/modelcontextprotocol/server-sdk-python) - MCP 服务器框架
- [FastAPI](https://fastapi.tiangolo.com/) - 现代 Python Web 框架
- [Questionary](https://github.com/tmbo/questionary) - 终端交互库
- [uv](https://github.com/astral-sh/uv) - 极速 Python 包管理器

## 📄 许可证

[MIT License](LICENSE)。