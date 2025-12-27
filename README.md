# Interactive Choice MCP

这是一个 MCP (Model Context Protocol) 服务器，提供了一个 `provide_choice` 工具，允许 AI 代理向用户请求结构化的决策输入。

它旨在解决 AI 在面临多个分支、破坏性操作或配置缺失时“猜测”用户意图的问题，通过提供明确的选项让用户通过终端或浏览器进行选择。

## ✨ 特性

- **双模式交互**：
  - **终端模式 (Terminal)**：使用 ANSI 交互式菜单（基于 `questionary`），支持键盘导航。
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

**基础配置：**
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

**启用调试日志的配置：**
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

### 工具定义：`provide_choice`

AI 代理可以调用此工具来请求用户输入。

**参数：**

- `title` (string): 选择界面的标题。
- `prompt` (string): 向用户展示的提示信息，应包含上下文。
- `selection_mode` (string): 选择模式 (`single`, `multi`)。
- `options` (array): 选项列表，每个选项包含 `id`、`description`、`recommended` (至少一个需要为 `true`)。
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
### 运行测试
使用 pytest 运行测试套件，请先确保安装了 pytest ：

```bash
uv run pytest
```

### 调试服务器

运行此命令进入 MCP Inspector 进行调试：

```bash
uv run mcp dev server.py
```

### 日志配置

服务器支持通过环境变量配置日志输出，便于调试和问题排查。

**环境变量：**

| 变量名              | 说明                                           | 默认值 |
| ------------------- | ---------------------------------------------- | ------ |
| `CHOICE_LOG_LEVEL`  | 日志级别 (`DEBUG`, `INFO`, `WARNING`, `ERROR`) | `INFO` |
| `CHOICE_LOG_FILE`   | 日志文件路径（不设置则只输出到 stderr）        | 无     |
| `CHOICE_LOG_FORMAT` | 自定义日志格式                                 | 见下方 |

**默认日志格式：**
```
%(asctime)s | %(levelname)-8s | %(name)-20s | %(message)s
```

**示例配置：**

```bash
# 启用详细调试日志并保存到文件
export CHOICE_LOG_LEVEL=DEBUG
export CHOICE_LOG_FILE=~/.local/share/interactive-choice-mcp/server.log
```

**日志输出示例：**
```
2024-12-27 22:00:00 | INFO     | choice.orchestrator  | Handling choice request: title='选择框架', mode=single, options=3
2024-12-27 22:00:00 | INFO     | choice.server        | Starting web server on http://127.0.0.1:17863
2024-12-27 22:00:00 | INFO     | choice.server        | Created session abc12345: title='选择框架', timeout=600s
2024-12-27 22:00:30 | INFO     | choice.server        | Session abc12345 submitted: selected=['react']
2024-12-27 22:00:30 | INFO     | choice.orchestrator  | Choice completed via web: action=selected
```

**调试技巧：**

1. **查看请求处理流程**：设置 `CHOICE_LOG_LEVEL=DEBUG` 可以看到详细的请求解析、配置应用等信息。
2. **排查超时问题**：日志会记录 session 创建时间、超时设置和超时触发事件。
3. **追踪 WebSocket 连接**：DEBUG 级别会记录 WebSocket 连接和断开事件。
4. **持久化日志**：设置 `CHOICE_LOG_FILE` 可以保存日志到文件，支持自动轮转（最大 10MB，保留 5 个备份）。

## 📄 许可证

[MIT License](LICENSE)
