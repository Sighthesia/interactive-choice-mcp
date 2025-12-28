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

### 环境变量

| 变量名 | 默认值 | 说明 |
|--------|--------|------|
| `CHOICE_WEB_HOST` | `127.0.0.1` | Web 服务器绑定地址。设置为 `0.0.0.0` 可允许外部访问 |
| `CHOICE_WEB_PORT` | `17863` | Web 服务器端口。如果端口被占用会自动选择空闲端口 |
| `CHOICE_LOG_LEVEL` | `INFO` | 日志级别：`DEBUG`, `INFO`, `WARNING`, `ERROR` |
| `CHOICE_LOG_FILE` | (无) | 日志文件路径。不设置则只输出到 stderr |

**完整环境变量配置示例：**
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
        "CHOICE_WEB_HOST": "0.0.0.0",
        "CHOICE_WEB_PORT": "18000",
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
- `session_id` (string, optional): 用于轮询已创建的终端会话的结果。

### Terminal Hand-off 流程

当工具返回 `action_status: pending_terminal_launch` 时：

1. 从响应的 `terminal_command` 字段获取 CLI 命令
2. AI 代理在终端中执行该命令以打开交互式 UI
3. 用户在终端 UI 中完成选择
4. AI 代理使用 `session_id` 再次调用 `provide_choice` 来获取最终结果
   - **注意**：轮询会阻塞等待最多 30 秒，减少频繁轮询的需要

示例响应：
```json
{
  "action_status": "pending_terminal_launch",
  "terminal_command": "uv run python -m choice.terminal.client --session abc123 --url http://127.0.0.1:17863",
  "session_id": "abc123",
  "url": "http://127.0.0.1:17863/terminal/abc123",
  "instructions": "1. Run the terminal_command in a terminal\n2. Wait for user to complete the interaction\n3. Call provide_choice again with session_id='abc123' to get the result"
}
```

### 终端客户端选项

```bash
# 基本用法
uv run python -m choice.terminal.client --session <id> --url <url>

# 启用注释功能（允许用户为选择添加备注）
uv run python -m choice.terminal.client --session <id> --url <url> --annotate

# 静默模式（不显示选项描述预览）
uv run python -m choice.terminal.client --session <id> --url <url> --quiet
```

终端 UI 特性：
- 清晰的标题、提示和超时显示
- 选项描述预览
- 键盘导航提示（↑/↓ 导航，Enter 确认，Space 多选切换，Ctrl+C 取消）
- 默认跳过注释步骤（使用 `--annotate` 启用）

注意：终端会话为**单次使用**（完成后会清理），如果没有客户端在 `timeout_seconds` 时间内附着并提交结果，会话将自动过期并在轮询时返回 `timeout` 响应。
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
