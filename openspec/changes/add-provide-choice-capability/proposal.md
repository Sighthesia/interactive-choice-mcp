# Change: Provide structured choice tool with dual transports

## Why
- AI flows currently guess user intent when multiple paths exist, leading to incorrect actions.
- We need a schema-first `provide_choice` tool and transport strategy so MCP calls can defer branching decisions to users reliably.

## What Changes
- Define the `provide_choice` tool contract with strict input schema and deterministic `action_status` outputs.
- Add choice orchestration that prefers interactive terminal prompts and falls back to a transient web portal when needed.
- Enforce timeout and cancel handling plus ordered multi-select normalization so downstream agents can act deterministically.
- Document decision policies so AI callers include task context and avoid speculative defaults.

## Impact
- Affected specs: choice-orchestration (new)
- Affected code: server.py, main.py, new transport/orchestration modules for terminal and web portal, schema validation and timeout handling
