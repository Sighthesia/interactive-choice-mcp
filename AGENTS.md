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

# Interactive Choice MCP – Guide

- **Entry & scope**: MCP tools `provide_choice` and `poll_selection` live in [../src/mcp/tools.py](../src/mcp/tools.py); both delegate to [../src/core/orchestrator.py](../src/core/orchestrator.py) and return normalized envelopes from [../src/core/response.py](../src/core/response.py).
- **Request rules**: Validation in [../src/core/validation.py](../src/core/validation.py) enforces `selection_mode` ∈ {single,multi}, non-empty title/prompt, unique option ids, boolean `recommended`, at least one recommended option, positive `timeout_seconds`, single mode allows only one recommended.
- **Transport selection**: Orchestrator builds defaults from persisted config and chooses terminal hand-off when config.interface == "terminal" (returns `pending_terminal_launch`) or web otherwise; `session_id` short-circuits to poll existing terminal/web session.
- **Terminal hand-off**: Terminal sessions reuse the unified ChoiceSession via [../src/web/server.py](../src/web/server.py). Agent runs the returned command (`uv run python -m src.terminal.client --session <id> --url http://<host>:<port>`); terminal output emits markers `[SELECTION_COMPLETE]`, `[CANCELLED]`, `[SWITCH_TO_WEB]` for parsing (see [../src/terminal/client.py](../src/terminal/client.py)).
- **Terminal UI defaults**: questionary-based flows in [../src/terminal/runner.py](../src/terminal/runner.py) and [../src/terminal/ui.py](../src/terminal/ui.py) support annotations, defaulting recommended options when `use_default_option` is true; settings prompt supports language, interface (if allowed), timeout, timeout defaults/actions.
- **Web flow**: FastAPI server in [../src/web/server.py](../src/web/server.py) creates ChoiceSessions, opens the browser, streams status via `/ws/{id}` and `/ws/interactions`, and persists results; switching from terminal sets interface `terminal-web` and reuses same session.
- **Web assets**: Bundled CSS/JS are assembled from [../src/web/frontend/manifest.json](../src/web/frontend/manifest.json) by [../src/web/bundler.py](../src/web/bundler.py) with content hashes and inline/default serving via [../src/web/templates.py](../src/web/templates.py); restart server after asset edits to refresh the cached bundle.
- **Timeout semantics**: Timeout actions (`submit|cancel|reinvoke`) and optional default selection are applied via [../src/core/response.py](../src/core/response.py) and honored in both web and terminal flows; timeout monitoring runs in session monitors ([../src/web/session.py](../src/web/session.py)).
- **Configuration persistence**: User settings stored at `.mcp-data/config.json` (or `MCP_DATA_DIR`) through [../src/infra/storage.py](../src/infra/storage.py); env `CHOICE_TIMEOUT_SECONDS` can override request timeout; `ConfigStore.save(..., exclude_transport=True)` preserves interface during terminal→web switch.
- **Interaction history**: Completed sessions persisted under `.mcp-data/sessions` with index + per-session files via [../src/store/interaction_store.py](../src/store/interaction_store.py); retention/max limits enforced (defaults 3 days/100 sessions) and surfaced in the interaction list.
- **Paths & data dir**: [../src/infra/paths.py](../src/infra/paths.py) resolves `.mcp-data` (respects `MCP_DATA_DIR`) and ensures directories for config, sessions, logs.
- **Logging & language**: Configure logging through env `CHOICE_LOG_LEVEL|FILE|FORMAT` ([../src/infra/logging.py](../src/infra/logging.py)); language from `CHOICE_LANG` or persisted config feeds i18n texts in [../src/infra/i18n.py](../src/infra/i18n.py).
- **Env for web host/port**: `CHOICE_WEB_HOST`/`CHOICE_WEB_PORT` resolved in [../src/web/server.py](../src/web/server.py); server finds a free port if the requested one is taken.
- **Result envelopes**: Normalized responses carry option ids (not indices), annotations, and action_status variants (`selected`, `cancelled`, `cancel_with_annotation`, timeout variants, `pending_terminal_launch`, `interrupted`).
- **Testing**: `uv run pytest` (or scoped suites) per [../tests/README.md](../tests/README.md); coverage via `uv run pytest --cov=src --cov-report=html`.
- **Run/dev workflow**: `uv sync` to install; `uv run server.py` to start MCP server (or `uv run mcp dev server.py` for inspector); config persists between calls.
- **Spec workflow**: For new capabilities or architecture shifts, consult [../openspec/AGENTS.md](../openspec/AGENTS.md) and follow change-proposal flow before implementation; feature work should align with specs under [../openspec/specs](../openspec/specs) and active changes under [../openspec/changes](../openspec/changes).
- **Safety defaults**: If validation fails, orchestrator returns a cancelled response with `validation_error:*`; unexpected exceptions fall back to timeout responses while preserving request context (see `safe_handle` in [../src/core/orchestrator.py](../src/core/orchestrator.py)).
