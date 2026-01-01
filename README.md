# Interactive Choice MCP

一个让 AI 在遇到选择问题时，能让 AI 提供选项并开启交互界面以进行选择，并反馈的 MCP Server。灵感来源于 [mcp-feedback-enhanced](https://github.com/astral-sh/mcp-feedback-enhanced)。

## ✨ 主要功能

- **交互**：支持 Web 和终端（实验性）两种交互界面
- **选择模式**：支持单选（single）和多选（multi）模式
- **选项备注**：选项支持备注，便于修改 AI 提供的选项以提供正确反馈
- **自动化**：AI 可提供推荐选项，支持超时自动提交以适应自动化场景
- **会话持久化**：支持交互历史记录持久化，默认保留 3 天

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

### 1. 基本配置

在 MCP 配置文件中添加 `"interactive-choice"`：

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

### 2. 环境变量（可选）

可以通过向 MCP 配置中的 `env` 添加以下环境变量自定义配置：

- `CHOICE_WEB_HOST`：Web 服务器主机（默认：`127.0.0.1`）
- `CHOICE_WEB_PORT`：Web 服务器端口（默认：`9999`）
- `CHOICE_LANG`：界面语言（`en` 或 `zh`，默认根据系统语言自动选择）
- `CHOICE_LOG_LEVEL`：日志级别（`DEBUG`、`INFO`、`WARNING`、`ERROR`，默认：`INFO`）
- `CHOICE_LOG_FILE`：日志文件路径（可选）
- `CHOICE_MCP_DATA_DIR`：数据存储目录（默认：`.mcp-data/`）

## 🤝 贡献

欢迎任何的贡献！无论是报告问题、提出功能请求，还是提交 PR，都非常感谢！

AI 驱动开发可参考 [AGENTS.md](AGENTS.md) 与 [openspec](openspec) 。

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

### 计划
由于各类 AI IDE 与 Cli 倾向于将 AI 运行的终端命令静默化，终端模式的交互体验可能受限，还需要考虑可行性。

## 💖 感谢

- [mcp-feedback-enhanced](https://github.com/Minidoracat/mcp-feedback-enhanced) - 项目参考和灵感来源

## 📄 许可证

[MIT License](LICENSE)。