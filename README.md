# Interactive Choice MCP
一个让 AI 在遇到选择问题时，能让 AI 提供选项并开启交互界面以进行选择并反馈的 MCP Sever，灵感来源于 [mcp-feedback-enhanced](https://github.com/astral-sh/mcp-feedback-enhanced)。

## ✨ 功能
- 支持 Web 和终端（试验性）两种交互界面。
- 选项支持备注，以快速修改 AI 提供的选项。
- AI 可提供推荐选项，支持超时自动提交，满足自动化需求。
- 支持单选和多选模式。

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

## 🤝 贡献

欢迎任何贡献！无论是报告问题、提出功能请求，还是提交代码改进，都非常感谢。

## 🧪 测试

有关测试的详细帮助信息，请参阅 [tests/README.md](tests/README.md)。

1. 快速运行 Web 交互界面交互式测试
```bash
uv run pytest tests/integration/test_interaction_web.py::TestWebInteractionManual::test_web_e2e_manual_interaction --interactive -v -s
```

1. 快速运行终端交互界面交互式测试
```bash
uv run pytest tests/integration/test_interaction_terminal.py::TestTerminalInteractionManual::test_terminal_e2e_manual_interaction --interactive -v -s
```


## 💖 感谢

- [mcp-feedback-enhanced](https://github.com/Minidoracat/mcp-feedback-enhanced) - 项目参考和灵感来源

## 📄 许可证

[MIT License](LICENSE)。