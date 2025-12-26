# Interactive Choice MCP

这是一个 MCP (Model Context Protocol) 服务器，提供了一个 `provide_choice` 工具，允许 AI 代理向用户请求结构化的决策输入。

它旨在解决 AI 在面临多个分支、破坏性操作或配置缺失时“猜测”用户意图的问题，通过提供明确的选项让用户通过终端或浏览器进行选择。

## ✨ 特性

- **双模式交互**：
    - **终端模式 (Terminal)**：使用 ANSI 交互式菜单（基于 `questionary`），支持键盘导航。
    - **Web 模式 (Web Bridge)**：自动启动临时本地 Web 服务器，允许用户在浏览器中进行选择（适用于不支持终端交互的环境）。
- **多种选择类型**：
    - `single_select`: 单选。
    - `multi_select`: 多选。
    - `text_input`: 自由文本输入。
    - `hybrid`: 预定义选项 + 自定义输入。
- **健壮性设计**：
    - 支持超时（Timeout）处理。
    - 支持取消（Cancel）操作。
    - 严格的输入验证。

## 📦 安装

本项目使用 `uv` 进行依赖管理。

1. 克隆仓库：

```bash
git clone https://github.com/Sighthesia/interactive-choice-mcp.git
```
2. 进入项目目录：

```bash
cd interactive-choice-mcp
```

3. 安装依赖

```bash
uv sync
```

## 🚀 使用方法

### 配置 MCP 客户端

将此服务器添加到你的 MCP 客户端配置文件中（例如 Claude Desktop 的 `claude_desktop_config.json`）。

- 其中 `/path/to/interactive-choice-mcp` 应改为克隆仓库的实际位置（如 `~/interactive-choice-mcp`）。

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

### 工具定义：`provide_choice`

AI 代理可以调用此工具来请求用户输入。

**参数：**

- `title` (string): 选择界面的标题。
- `prompt` (string): 向用户展示的提示信息，应包含上下文。
- `type` (string): 选择类型 (`single_select`, `multi_select`, `text_input`, `hybrid`)。
- `options` (array): 选项列表，每个选项包含 `id`, `label`, `description`。
- `allow_cancel` (boolean): 是否允许用户取消。
- `placeholder` (string, optional): 输入框的占位符。
- `transport` (string, optional): 强制指定传输方式 (`terminal` 或 `web`)。
- `timeout_seconds` (integer, optional): 超时时间（秒）。

## 🛠️ 开发

### 项目结构

```
interactive-choice-mcp/
├── server.py              # MCP 服务器入口
├── choice/
│   ├── orchestrator.py    # 调度器：决定使用终端还是 Web
│   ├── models.py          # 数据模型与验证
│   ├── terminal.py        # 终端交互实现 (questionary)
│   └── web.py             # Web 交互实现 (FastAPI)
└── openspec/              # 项目规范文档
```

### 运行开发服务器

运行此命令进入 MCP Instpector 进行调试：

```bash
uv run mcp dev server.py
```

## 📄 许可证

[MIT License](LICENSE)
