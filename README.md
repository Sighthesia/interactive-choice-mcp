# Interactive Choice MCP

<div align="left">
  <p>
    <a href="README.zh.md">中文</a> | 
    <a href="README.md">English</a>
  </p>
</div>

An MCP Server that enables AI to provide options and launch an interactive interface for user selection when facing choice problems, then return the results. Inspired by [mcp-feedback-enhanced](https://github.com/astral-sh/mcp-feedback-enhanced), built with [FastMCP](https://github.com/jlowin/fastmcp).

- Showcase:
  ![Showcase](<Showcase.png>)

## 📋 Table of Contents

- [✨ Key Features](#-key-features)
- [📦 Installation](#-installation)
- [🤝 Contributing](#-contributing)
- [📍 Local Development Environment Setup](#-local-development-environment-setup)
- [💖 Acknowledgments](#-acknowledgments)

## ✨ Key Features

### 🎯 Core Capabilities
- **Interactive Choice Interface**: AI presents options, users make selections through intuitive interfaces
- **Dual Interface Support**: Web-based UI and Terminal UI (experimental)
- **Selection Modes**: Single-select and multi-select modes
- **Option Annotations**: Users can add annotations to options to provide correct feedback to AI
- **Automation Ready**: AI can mark recommended options with timeout auto-submit


## 📦 Installation

### Prerequisites
- Python 3.12 or higher
- [uv](https://github.com/astral-sh/uv) package manager (recommended) or pip

### 🚀 Quick Start

Add the following configuration:

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

- This will automatically clone the project repository and install dependencies.

- For best results, it is recommended to add the following content to your global prompt (still being adjusted, currently focusing on optimization for pay-per-use AI assistants, suggestions are welcome):

  ```markdown
  Strictly follow the rules of the `provide_choice` tool.
  ```

#### Environment Variables (Optional)

You can override saved configurations by adding the following environment variables to the `env` section in your MCP configuration:

| Environment Variable  | Description        | Possible Values                     | Default                          |
| --------------------- | ------------------ | ----------------------------------- | -------------------------------- |
| `CHOICE_WEB_HOST`     | Web server host    | Any valid IP or hostname            | `127.0.0.1`                      |
| `CHOICE_WEB_PORT`     | Web server port    | Any available port number           | `9999`                           |
| `CHOICE_LANG`         | Interface language | `en`, `zh`                          | Auto-detected by system language |
| `CHOICE_LOG_LEVEL`    | Log level          | `DEBUG`, `INFO`, `WARNING`, `ERROR` | `INFO`                           |
| `CHOICE_LOG_FILE`     | Log file path      | Any valid file path                 | Optional                         |
| `CHOICE_MCP_DATA_DIR` | Data storage dir   | Any valid directory path            | `.mcp-data/`                     |

##### Configuration Example

Here is a complete MCP configuration example with environment variables:

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

## 🤝 Contributing

Contributions are welcome! Whether it's reporting issues, requesting features, or submitting PRs, it's all greatly appreciated!

For AI-driven development, refer to [AGENTS.md](AGENTS.md) and [openspec](openspec).

### 📍 Local Development Environment Setup

```bash
# Clone the repository
git clone https://github.com/Sighthesia/interactive-choice-mcp.git
cd interactive-choice-mcp

# Install dependencies
uv sync

# Verify installation
uv run pytest
```

- You can configure to use a local development environment to run the MCP Server:

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

  **Tip**: Replace `/path/to/interactive-choice-mcp` with the actual path, such as `~/interactive-choice-mcp`.

### 🧪 Testing

For detailed testing information, please refer to [tests/README.md](tests/README.md).

The following are common test commands for development and debugging:

#### Running Interactive Tests

Temporarily run the Web server for interactive testing to verify user-side interaction effects:

1. Open Web interaction interface and test the default single-select mode

  ```bash
  uv run pytest tests/integration/test_interaction_web.py::TestWebInteractionManual::test_web_e2e_manual_interaction --interactive -v -s
  ```

2. Open terminal interaction interface and test the default single-select mode

  ```bash
  uv run pytest tests/integration/test_interaction_terminal.py::TestTerminalInteractionManual::test_terminal_e2e_manual_interaction --interactive -v -s
  ```

#### Running MCP Server Debugging

Run MCP Inspector to verify MCP Server tool input/output effects:

```bash
uv run mcp dev server.py
```

### 🏗️ Project Architecture

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

### Future Considerations
- Since various AI IDEs and CLIs tend to silently run AI commands, the terminal mode interaction experience may be limited and requires further consideration for feasibility

## 💖 Acknowledgments

- [Minidoracat](https://github.com/Minidoracat) - [mcp-feedback-enhanced](https://github.com/Minidoracat/mcp-feedback-enhanced) - Project reference and inspiration source. If you like this project, consider supporting them!

## 📄 License

[MIT License](LICENSE).
