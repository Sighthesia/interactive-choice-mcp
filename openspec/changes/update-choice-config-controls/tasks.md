## 1. Proposal Validation
- [x] 1.1 Validate change with `openspec validate update-choice-config-controls --strict`.

## 2. Spec and Schema
- [x] 2.1 Update choice-orchestration spec with extended schema fields (defaults, min/max limits, annotation knobs, single-submit flag, placeholder toggle) and cancel-always-on behavior.
- [x] 2.2 Align with pending `add-interaction-config-panels` change to avoid conflicting requirements.

## 3. Orchestration and Persistence
- [x] 3.1 Extend orchestration models/validation to honor new fields and force cancel enabled; migrate persisted config defaults safely.
- [x] 3.2 Normalize responses to include annotations and enforce min/max selection counts before submission.

## 4. Terminal Flow
- [x] 4.1 Add UI controls for selection mode toggle, default selections, min/max bounds, annotation inputs, and placeholder visibility; keep cancel available without a toggle.
- [x] 4.2 Ensure summary output reflects annotations and selection count validation results.

## 5. Web Flow
- [x] 5.1 Mirror new controls (selection mode, defaults, min/max, annotations, placeholder toggle) in the web panel; maintain cancel visibility.
- [x] 5.2 Enforce min/max constraints on submit and surface errors to the user.

## 6. Testing
- [x] 6.1 Add/extend pytest coverage for schema validation, min/max enforcement, annotation capture, and cancel-always-on behavior across transports.
- [ ] 6.2 Manual smoke: terminal and web flows show new controls, enforce limits, and return expected payloads.
