# Project Context

## Purpose
Build an MCP server that exposes a single `provide_choice` tool to collect structured user decisions. The server must support both interactive terminal selection and a transient web bridge so AI agents can defer branching decisions to the user instead of guessing.

## Tech Stack
- Python 3.12+
- FastAPI + Uvicorn for the temporary web portal and callback channel
- fastmcp for MCP server scaffolding
- questionary for ANSI-based terminal prompts

## Project Conventions

### Code Style
- PEP 8 with type hints; prefer dataclasses or TypedDict for request/response envelopes
- Keep modules small and single-purpose; avoid global state beyond configuration wiring
- User-facing text is concise and action-oriented; avoid ambiguous phrasing in prompts

### Architecture Patterns
- CLI-first interaction with optional web bridge fallback; both share a common `provide_choice` schema
- Tool contract is schema-first: `title`, `prompt`, `type (single_select|multi_select|text_input|hybrid)`, `options[id,label,description]`, `allow_cancel`, `placeholder`
- Result contract is deterministic: `action_status (selected|custom_input|cancelled|timeout)` plus normalized selection payload
- Separation of concerns: input transport (terminal/web) separated from choice orchestration and MCP binding

### Testing Strategy
- Unit tests with pytest for choice normalization and timeout/cancel handling
- Manual smoke tests for both terminal (questionary navigation) and web portal flows until e2e harness is added
- Validate schemas with strict parsing to prevent malformed tool payloads

### Git Workflow
- Default branch: `main`; feature branches per change-id when following OpenSpec proposals
- Conventional Commit messages where practical; keep commits small and scoped to one behavior change
- Run `openspec validate --strict` before requesting reviews when specs are touched

## Domain Context
- `provide_choice` is the sole user-facing tool; AI must call it whenever there are multiple paths, destructive actions, or missing config instead of guessing
- Terminal mode: render ANSI list with arrow/space/enter; clear screen after completion and print summary only
- Web bridge mode: spawn short-lived FastAPI server, open `http://localhost:<port>/choice/<id>` in browser, collect via WebSocket/long-poll, then shut down after returning result
- Multi-select returns ordered option ids; hybrid/text modes capture freeform input with optional placeholder guidance

## Important Constraints
- Enforce a timeout (e.g., ~5 minutes) for waiting on user input; return `timeout` status and prompt re-invocation
- Respect `cancel` as a hard stop; AI should halt the current subtask when received
- Avoid speculative defaults; always surface the current task context in the `prompt` so users know why a choice is needed

## External Dependencies
- Local browser invocation for the web portal; assume localhost networking only
- fastmcp runtime expectations for tool registration and execution lifecycle
- questionary behavior for terminal keybindings and rendering capabilities
