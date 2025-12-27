# Proposal: Tighten Terminal UX & Hand-off Guidance

## Problem Statement
- Agents often receive `pending_terminal_launch` but fail to run the terminal command, leading to stalled interactions.
- Terminal hand-off response mixes `summary`/URL; agents must parse text instead of consuming structured fields.
- Terminal UI lacks cues (invocation time, timeout), navigation ergonomics (j/k, Tab to annotations), and a settings entry to switch transports or adjust preferences mid-flow.
- Annotation flow is inconsistent: optional by default, cancel path lacks global annotation prompt.
- Unclear whether the terminal hand-off URL is required for clients; need a clarified contract.

## Goals
- Make terminal hand-off unambiguous: structured fields (`terminal_command`, `session_id`, optional `url`), clear agent instructions, and default blocking poll to reduce missed execution.
- Upgrade terminal UI ergonomics: show invocation + timeout, support j/k navigation, Tab to annotations, always-available annotations (empty = no note), cancel triggers global annotation prompt.
- Provide an in-terminal settings entry to adjust global/terminal UI settings and switch the current session to web transport when desired.
- Clarify URL semantics: keep for client connectivity but make it optional/auxiliary so agents need only `terminal_command` + `session_id`.

## Non-Goals
- Do not redesign the web UI; only enable switching from terminal to web.
- Do not change core selection/validation schema beyond hand-off field semantics and annotation defaults.

## Constraints / Considerations
- Must remain compatible with existing web bridge and terminal client storage; sessions are still single-use.
- Keep changes aligned with `choice-orchestration` spec; introduce spec deltas rather than ad-hoc behavior.

## Acceptance Criteria
- Updated specs validated via `openspec validate tighten-terminal-ux-hand-off --strict`.
- Terminal hand-off contract explicitly requires `terminal_command` + `session_id`; URL clarified as optional/aux.
- Terminal UI behavior (timestamps, timeout display, j/k, Tab to annotations, always-on annotations, cancel→global annotation, settings entry, web switch) captured in requirements.
- Tasks enumerated for implementation and testing.
