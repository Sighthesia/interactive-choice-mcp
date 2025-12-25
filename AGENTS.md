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

- Scope: This repo builds an MCP server whose only tool is `provide_choice`, gathering structured user decisions instead of AI guesses. Two fronts: terminal (ANSI via questionary) and a transient web bridge (FastAPI+Uvicorn) that returns a local URL.
- Key references: read [openspec/project.md](../openspec/project.md) for stack/conventions and [openspec/AGENTS.md](../openspec/AGENTS.md) when work involves proposals/spec changes. Root [AGENTS.md](../AGENTS.md) points to OpenSpec flow. README is currently empty.
- Stack: Python 3.12+, fastmcp for MCP glue, FastAPI+Uvicorn for the web portal, questionary for CLI prompts.
- Tool contract: schema-first `provide_choice` with `title`, `prompt`, `type (single_select|multi_select|text_input|hybrid)`, `options[id,label,description]`, `allow_cancel`, `placeholder`. Output must include `action_status (selected|custom_input|cancelled|timeout)` and normalized selections.
- Interaction design: CLI is default—render list, arrow/space/enter, then clear UI and print a concise summary. Web bridge is fallback—spawn short-lived server, open `http://localhost:<port>/choice/<id>`, collect via WebSocket/long-poll, then shut down.
- Behavioral rules: invoke the tool whenever choices/branches >2, destructive actions, or config is missing. Never guess defaults; always explain why the choice is needed in the prompt. `cancel` halts the subtask; enforce a ~5 min timeout returning `timeout` status.
- Code style: PEP 8 with type hints; keep modules small and single-purpose; prefer dataclasses/TypedDict for payloads; keep user-facing text concise and action-oriented.
- Architecture: separate transport (terminal/web) from choice orchestration and MCP binding. Normalize selection ordering for multi-select; support hybrid/text input with placeholder guidance.
- Testing: target pytest unit tests for choice normalization, timeout, and cancel handling; manual smoke for both terminal and web until e2e exists.
- Git/flow: default branch `main`; feature branches keyed to change-id when following OpenSpec; Conventional Commit style encouraged; run `openspec validate --strict` when specs are touched.
- External touchpoints: local browser for the web flow (assume localhost only); fastmcp lifecycle expectations; questionary keybindings/render limits.
- Current code: [server.py](../server.py) only initializes `FastMCP("Interactive Choice")`; [main.py](../main.py) is a stub. Expect to add FastAPI app, tool registration, and web portal handlers.
