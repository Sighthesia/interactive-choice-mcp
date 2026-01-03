# Interactive Choice MCP

<div align="left">
  <p>
    <a href="README.zh.md">中文</a> | 
    <a href="README.md">English</a>
  </p>
</div>

一个让 AI 在遇到选择问题时，能让 AI 提供选项并开启交互界面以进行选择，并反馈的 MCP Server。灵感来源于 [mcp-feedback-enhanced](https://github.com/astral-sh/mcp-feedback-enhanced), 使用 [FastMCP](https://github.com/jlowin/fastmcp) 开发。

- 效果展示：
  ![Showcase](<Showcase.png>)

# 相似项目

- **imhuso/[cunzhi](https://github.com/imhuso/cunzhi)** - 基于 Rust + Tauri 的桌面应用，专门用于**拦截** AI 过早结束对话。包含项目级记忆管理和代码搜索功能。功能更全面完善。

- **paulp-o/[ask-user-questions-mcp](https://github.com/paulp-o/ask-user-questions-mcp)** - 基于 TypeScript + Node.js 的轻量级 MCP 服务器，专注于 **CLI 交互**。专为多 Agent 并行编码工作流设计，支持问题队列和 SSH。更轻量，专注终端界面。

- **fhyfhy17/[panel-feedback](https://github.com/fhyfhy17/panel-feedback)** - Panel Feedback 将 AI 交互直接嵌入 IDE 侧边栏 - 无缝集成，随时可用，永不打扰。

**差异**：本项目提供 **双界面支持**（Web + Terminal），在复杂度上保持平衡，专注于交互式选择场景。

*（实际上我写完本项目才发现了这些项目，希望这些好项目能够让更多人发现）*

## 📋 目录

- [✨ 主要功能](#-主要功能)
- [📦 安装](#-安装)
- [🤝 贡献](#-贡献)
- [📍 本地开发环境设置](#-本地开发环境设置)
- [💖 感谢](#-感谢)

## ✨ 主要功能

### 🎯 核心能力
- **交互式选择界面**：AI 提供选项，用户通过直观界面进行选择
- **双界面支持**：Web 界面和终端界面（实验性）
- **选择模式**：单选和多选模式
- **选项备注**：可以为选项添加备注以提供正确反馈给 AI
- **自动化支持**：AI 可以标记推荐选项并支持超时自动提交

## 📦 安装

### 前置要求
- Python 3.12 或更高版本
- [uv](https://github.com/astral-sh/uv) 包管理器

### 🚀 快速配置

在 MCP 配置文件中添加：

```json
{
  "mcpServers": {
    "interactive-choice": {
      "command": "uvx",
      "args": [
        "--from",
        "git+https://github.com/Sighthesia/interactive-choice-mcp",
        "interactive-choice-mcp"
      ]
    }
  }
}
```
- 这会自动 Clone 项目仓库并安装依赖。
  
- 为确保效果，建议在全局提示词中增加以下内容（仍然在调整中， 提示词来自`寸止`，目前针对按次数计费的 AI 助手优化 ，欢迎给出建议）：

  ```markdown
  - 需求不明确时使用 `provide_choice` 询问澄清，提供预定义选项
  - 在有多个方案的时候，需要使用 `provide_choice` 询问，而不是自作主张
  - 在有方案/策略需要更新时，需要使用 `provide_choice` 询问，而不是自作主张
  - 即将完成请求前必须调用 `provide_choice` 请求反馈
  - 在没有明确通过使用 `provide_choice` 询问并得到可以完成任务/结束时，禁止主动结束对话/请求。
  ```

#### 环境变量（可选）

可以通过向 MCP 配置中的 `env` 添加以下环境变量以覆盖保存的配置：

| 环境变量              | 说明           | 可选值                              | 默认值               |
| --------------------- | -------------- | ----------------------------------- | -------------------- |
| `CHOICE_WEB_HOST`     | Web 服务器主机 | 任意有效 IP 或主机名                | `127.0.0.1`          |
| `CHOICE_WEB_PORT`     | Web 服务器端口 | 任意可用端口号                      | `9999`               |
| `CHOICE_LANG`         | 界面语言       | `en`, `zh`                          | 根据系统语言自动选择 |
| `CHOICE_LOG_LEVEL`    | 日志级别       | `DEBUG`, `INFO`, `WARNING`, `ERROR` | `INFO`               |
| `CHOICE_LOG_FILE`     | 日志文件路径   | 任意有效文件路径                    | 可选                 |
| `CHOICE_MCP_DATA_DIR` | 数据存储目录   | 任意有效目录路径                    | `.mcp-data/`         |

##### 配置示例

以下是一个包含环境变量的完整 MCP 配置示例：

```json
{
  "mcpServers": {
    "interactive-choice": {
      "command": "uvx",
      "args": [
        "--from",
        "git+https://github.com/Sighthesia/interactive-choice-mcp",
        "interactive-choice-mcp"
      ],
      "env": {
        "CHOICE_WEB_HOST": "127.0.0.1",
        "CHOICE_WEB_PORT": "8080",
        "CHOICE_LANG": "en",
        "CHOICE_LOG_LEVEL": "DEBUG",
        "CHOICE_LOG_FILE": "~/.mcp-data/interactive-choice.log",
        "CHOICE_MCP_DATA_DIR": "~/.mcp-data/interactive-choice"
      }
    }
  }
}
```

## 🤝 贡献

欢迎任何的贡献！无论是报告问题、提出功能请求，还是提交 PR，都非常感谢！

AI 驱动开发可参考 [AGENTS.md](AGENTS.md) 与 [openspec](openspec) 。

### 📍 本地开发环境设置

```bash
# 克隆仓库
git clone https://github.com/Sighthesia/interactive-choice-mcp.git
cd interactive-choice-mcp

# 同步依赖
uv sync

# 验证安装
uv run pytest
```

- 可配置使用本地开发环境运行 MCP Server：


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

### 🧪 测试

有关测试的详细帮助信息，请参阅 [tests/README.md](tests/README.md)。

以下为开发调试常用的测试命令：

#### 运行交互式测试

临时运行 Web 服务器进行交互式测试，检验用户端交互效果：

1. 打开 Web 交互界面并测试默认的单选模式

  ```bash
  uv run pytest tests/integration/test_interaction_web.py::TestWebInteractionManual::test_web_e2e_manual_interaction --interactive -v -s
  ```

2. 打开终端交互界面并测试默认的单选模式

  ```bash
  uv run pytest tests/integration/test_interaction_terminal.py::TestTerminalInteractionManual::test_terminal_e2e_manual_interaction --interactive -v -s
  ```

#### 运行 MCP Server 调试

运行 MCP Inspector 检验 MCP Sever 工具输入输出效果：

```bash
uv run mcp dev server.py
```

### 🏗️ 项目结构

```
src/
├── core/                    # Core orchestration and business logic
│   ├── models.py           # Data models and schemas
│   ├── orchestrator.py     # Main orchestration logic
│   ├── validation.py       # Input validation
│   └── response.py         # Response generation
├── mcp/                    # MCP tool bindings
│   ├── tools.py           # MCP tool definitions
│   └── response_formatter.py
├── web/                    # Web interface
│   ├── server.py          # FastAPI web server
│   ├── bundler.py         # Asset bundling
│   └── templates.py       # HTML templates
├── terminal/               # Terminal interface
│   ├── ui.py              # Questionary-based UI
│   └── session.py         # Terminal session management
├── store/                  # Data persistence
│   └── interaction_store.py
└── infra/                  # Infrastructure
    ├── logging.py         # Logging configuration
    ├── i18n.py            # Internationalization
    └── storage.py         # File system operations
```

### 未来考虑
- 由于各类 AI IDE 与 Cli 倾向于将 AI 运行的终端命令静默化，终端模式的交互体验可能受限，还需要考虑可行性

## 💖 感谢

- [Minidoracat](https://github.com/Minidoracat) - [mcp-feedback-enhanced](https://github.com/Minidoracat/mcp-feedback-enhanced) - 项目参考和灵感来源。如果你喜欢本项目，也可考虑支持他们！

## 📄 许可证

[MIT License](LICENSE)。