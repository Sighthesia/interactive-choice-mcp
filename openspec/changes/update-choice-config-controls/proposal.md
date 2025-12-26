# Change: Update choice configuration controls for annotations and selection limits

## Why
- Users need richer control over how choices are captured (auto-submit vs batch submit, annotations, enforced min/max) to avoid AI guesswork.
- Cancel must remain available across transports, and callers want defaults (selection, placeholder) applied consistently.

## What Changes
- Extend the `provide_choice` schema with defaults (preselected options, placeholder toggle), selection bounds, and annotation fields (per-option and global) while keeping cancel always enabled.
- Add single-select mode toggle that either auto-submits on click or enables multi-select with explicit submit; surface min/max constraints and default selections in both terminal and web flows.
- Capture optional freeform annotations: inline with options and as a global note when none of the options fit.

## Impact
- Affected specs: choice-orchestration
- Affected code: orchestrator, models/validation, terminal renderer, web portal, persisted configuration handling
