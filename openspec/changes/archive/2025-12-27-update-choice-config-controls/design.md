## Context
User feedback asks for more control over how choices are captured: toggling single-click auto submission vs batch submission, enforcing min/max selection counts, attaching annotations (per-option and global), and providing default selections/placeholders from the AI. Cancel must remain available everywhere with no disable switch. These changes extend the existing configuration surfaces added in the pending `add-interaction-config-panels` change.

## Goals / Non-Goals
- Goals: expand the choice schema and UI to cover selection mode, default selections, min/max constraints, placeholder visibility, and annotation inputs; keep cancel always enabled; ensure both terminal and web flows apply the same rules and persist settings.
- Non-Goals: introducing new transports, redesigning the FastAPI lifecycle, or changing the result envelope beyond capturing the new annotation fields.

## Decisions
- Enforce cancel as always available: remove the toggle from configuration panels and treat any `allow_cancel` input as true to keep parity across transports.
- Extend the request/response schema with `default_selection_ids`, `min_selections`, `max_selections`, `placeholder_enabled`, `option_annotations` (per-option), and `additional_annotation`, plus a `single_submit_mode` flag to express auto-submit vs batch-submit flows.
- Validate selection counts against min/max before submission; clamp defaults to allowed options and reject payloads whose limits are inverted (min > max) or non-positive.
- Surface UI controls in both terminal and web panels for selection mode, default selections, min/max limits, placeholder visibility, and annotation capture; persist these settings alongside existing interface/timeout defaults for reuse.

## Risks / Trade-offs
- Additional UI controls could slow interaction; mitigate with sensible defaults (single submit on, placeholders derived from prompt) and concise labels.
- Persisted defaults from older versions may miss new fields; mitigate with safe fallbacks and migration that injects defaults when missing.
- Annotation capture could clutter terminal UI; mitigate with short prompts and optional entry.

## Open Questions
- How should defaults handle hybrid/text modes when both placeholder and annotations are present? (Plan: show placeholder toggle only for text-capable modes; annotations remain optional.)
- Should min/max constraints apply to hybrid custom-input flows? (Plan: apply only to option selections; custom input bypasses count limits.)
