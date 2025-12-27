<!-- OPENSPEC:START -->
# OpenSpec Instructions

These instructions are for AI assistants working in this project.

Always open `@/openspec/AGENTS.md` when the request:
- Mentions planning or proposals (words like proposal, spec, change, plan)
- Introduces new capabilities, breaking changes, architecture shifts, or big performance/security work
- Sounds ambiguous and you need the authoritative spec before coding

Use `@/openspec/AGENTS.md` to learn:
- How to create and apply change proposals
- Spec format and conventions
- Project structure and guidelines

Keep this managed block so 'openspec update' can refresh the instructions.

<!-- OPENSPEC:END -->

# Instructions

## 🏗️ 架构概览 (Big Picture)
本项目是一个 MCP 服务器，核心功能是通过 `provide_choice` 工具收集用户决策。

- **核心调度 (Orchestration)**: [choice/orchestrator.py](choice/orchestrator.py) 中的 `ChoiceOrchestrator` 是大脑，负责验证请求、选择传输方式（终端或 Web）以及持久化用户配置。
- **传输层 (Transports)**:
  - **Terminal**: [choice/terminal/runner.py](choice/terminal/runner.py) + [choice/terminal/ui.py](choice/terminal/ui.py) 使用 `questionary` 实现 ANSI 交互。
  - **Web**: [choice/web/server.py](choice/web/server.py) + [choice/web/session.py](choice/web/session.py) + [choice/web/templates.py](choice/web/templates.py) 使用 `FastAPI` 启动临时服务器。
- **数据模型**: [choice/models.py](choice/models.py) 定义核心数据结构；验证与配置应用在 [choice/validation.py](choice/validation.py)，响应归一化在 [choice/response.py](choice/response.py)。
- **持久化**: [choice/storage.py](choice/storage.py) 将用户偏好保存至 `~/.interactive_choice_config.json`。
- **日志系统**: [choice/logging.py](choice/logging.py) 提供统一的日志配置与工具。

## 🛠️ 关键工作流 (Workflows)
- **环境同步**: `uv sync`
- **运行服务器**: `uv run server.py`
- **运行测试**: `uv run pytest`
- **规范管理**: 使用 `openspec` 工具管理项目提案和任务（见 [openspec/](openspec/)）。

## 🐛 调试指南 (Debugging)

### 日志配置
服务器使用 [choice/logging.py](choice/logging.py) 模块提供统一的日志功能。

**环境变量配置：**
```bash
# 日志级别 (DEBUG, INFO, WARNING, ERROR)
export CHOICE_LOG_LEVEL=DEBUG

# 日志文件路径（可选）
export CHOICE_LOG_FILE=~/.local/share/interactive-choice-mcp/server.log
```

**在代码中使用日志：**
```python
from choice.logging import get_logger, get_session_logger

# 获取模块级 logger
logger = get_logger(__name__)
logger.info("Processing request")
logger.debug("Detailed info: %s", data)

# 获取带 session ID 前缀的 logger（用于追踪特定会话）
session_logger = get_session_logger(__name__, session_id)
session_logger.info("User submitted selection")  # 输出: [abc123de] User submitted selection
```

**日志记录位置：**
- `choice.orchestrator`: 请求处理、传输选择、完成状态
- `choice.server`: Web 服务器启动、session 创建/提交/超时
- `choice.session`: 超时监控、WebSocket 广播

**调试技巧：**
1. 设置 `CHOICE_LOG_LEVEL=DEBUG` 查看详细流程
2. 设置 `CHOICE_LOG_FILE` 持久化日志用于事后分析
3. 日志文件支持自动轮转（10MB，保留 5 份）

### MCP Inspector
使用 MCP Inspector 进行交互式调试：
```bash
uv run mcp dev server.py
```

## 📏 编码约定 (Conventions)
- **逻辑分段**: 使用 `// Section: Section Name` 注释来分隔文件中的逻辑块。
- **模型定义**: 必须在 [choice/models.py](choice/models.py) 中使用 `@dataclass` 定义新模型。
- **类型提示**: 强制使用严格的类型提示（Type Hints）。
- **错误处理**: 
  - 工具入口应使用 `safe_handle` 包装，确保始终返回有效的 MCP 响应。
  - 优先返回 `cancelled_response` 或 `timeout_response` 而非抛出未捕获异常。
- **ID 语义**: `ProvideChoiceOption.id` 既是唯一标识也是显示标签。`selected_indices` 存储的是这些 ID 字符串，而非数字索引。
- **日志记录**: 在关键操作点使用 `choice.logging` 模块记录日志，便于问题排查。

## 🔗 集成要点 (Integration)
- **FastMCP**: 使用 `@mcp.tool()` 注册工具。
- **Web Bridge**: Web 模式是短寿命的，任务完成后应确保服务器关闭。
- **OpenSpec**: 修改架构或引入重大变更前，必须参考或更新 [openspec/](openspec/) 中的提案。

## 📂 关键文件参考
- [server.py](server.py): MCP 入口与工具定义。
- [choice/orchestrator.py](choice/orchestrator.py): 核心调度逻辑。
- [choice/models.py](choice/models.py): 协议数据模型。
- [choice/validation.py](choice/validation.py): 请求校验与配置应用。
- [choice/response.py](choice/response.py): 响应归一化与超时处理。
- [choice/storage.py](choice/storage.py): 配置持久化实现。
- [choice/logging.py](choice/logging.py): 日志配置与工具。
