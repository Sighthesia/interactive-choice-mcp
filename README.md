# Interactive Choice MCP

这是一个 MCP (Model Context Protocol) 服务器，提供了一个 `provide_choice` 工具，允许 AI 代理向用户请求结构化的决策输入。

它旨在解决 AI 在面临多个分支、破坏性操作或配置缺失时“猜测”用户意图的问题，通过提供明确的选项让用户通过终端或浏览器进行选择。

## ✨ 特性

- **双模式交互**：
  - **终端模式 (Terminal Hand-off)**：工具返回一个启动命令，AI 代理在终端中执行该命令以打开交互式 UI（基于 `questionary`）。
  - **Web 模式 (Web Bridge)**：自动启动临时本地 Web 服务器，允许用户在浏览器中进行选择（适用于不支持终端交互的环境）。
- **多种选择类型**：
  - `single`: 单选。
  - `multi`: 多选。
- **健壮性设计**:
  - 支持超时（Timeout）处理。
  - 取消（Cancel）始终可用。
  - 严格的输入验证。

## 📦 安装

本项目由 FastMCP 构建，推荐使用 [uv](https://github.com/astral-sh/uv) 进行依赖管理。

1. **克隆并同步环境**：
   ```bash
   git clone https://github.com/Sighthesia/interactive-choice-mcp.git
   ```

    ```bash
   cd interactive-choice-mcp
   ```

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
- `selection_mode` (string): 选择模式 (`single`, `multi`)。
- `options` (array): 选项列表，每个选项包含 `id`、`description`、`recommended` (至少一个需要为 `true`)。
- `session_id` (string, optional): 用于轮询已创建的终端会话的结果。

### Terminal Hand-off 流程

当工具返回 `action_status: pending_terminal_launch` 时：

1. 响应中的 `summary` 字段包含一个 CLI 命令
2. AI 代理应在终端中执行该命令以打开交互式 UI
3. 用户在终端 UI 中完成选择
4. AI 代理使用 `session_id` 再次调用 `provide_choice` 来获取最终结果

示例响应：
```json
{
  "action_status": "pending_terminal_launch",
  "summary": "uv run python -m choice.terminal.client --session abc123 --url http://127.0.0.1:17863",
  "session_id": "abc123",
  "url": "http://127.0.0.1:17863/terminal/abc123"
}
```

## 🛠️ 开发

### 项目结构

```
interactive-choice-mcp/
├── server.py                  # MCP 服务器入口
├── choice/
│   ├── orchestrator.py        # 调度器：决定使用终端还是 Web
│   ├── models.py              # 数据模型与验证
│   ├── response.py            # 响应归一化
│   ├── storage.py             # 配置持久化
│   ├── validation.py          # 请求验证
│   ├── terminal/
│   │   ├── runner.py          # 终端交互实现
│   │   ├── session.py         # 终端会话管理
│   │   ├── client.py          # 终端客户端 CLI
│   │   └── ui.py              # 终端 UI 构建
│   └── web/
│       ├── server.py          # Web 服务器实现
│       ├── session.py         # Web 会话管理
│       └── templates.py       # HTML 模板
└── openspec/                  # 项目规范文档
```
### 运行测试
使用 pytest 运行测试套件，请先确保安装了 pytest ：

```bash
uv run pytest
```

### 调试服务器

运行此命令进入 MCP Instpector 进行调试：

```bash
uv run mcp dev server.py
```

## 📄 许可证

[MIT License](LICENSE)
