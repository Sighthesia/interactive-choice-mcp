# Change: Add interaction configuration surfaces for terminal and web flows

## Why
Current prompts assume defaults and hide configuration such as transport selection, visible options, and timeout tuning; users want an explicit settings surface in both terminal and web flows to control how choices are presented.

## What Changes
- Add a configuration surface to terminal flows so users can set transport, filter available options, and adjust timeout before answering.
- Add a configuration panel to the web portal with the same controls, keeping defaults sane but explicit.
- Plumb the chosen configuration through orchestrator so the tool contract and result payload honor user-selected transport, option set, and timeout.
- Persist last-used settings so subsequent invocations can prefill transport, option visibility, and timeout defaults.

## Impact
- Affected specs: choice-orchestration
- Affected code: orchestrator, terminal renderer, web portal
