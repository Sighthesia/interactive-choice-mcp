## 1. Proposal Validation
- [x] 1.1 Validate change with `openspec validate add-interaction-config-panels --strict`.

## 2. Schema and Orchestration
- [x] 2.1 Extend orchestrator config model to accept explicit transport selection, option visibility filters, and timeout overrides.
- [x] 2.2 Ensure normalized result payload respects user-selected transport and timeout.
- [x] 2.3 Persist and reload last-used configuration so defaults prefill transport, option visibility, and timeout across invocations.

## 3. Terminal Flow
- [x] 3.1 Add a pre-prompt configuration surface in terminal to choose transport, adjust visible options, and set timeout with defaults.
- [x] 3.2 Preserve concise summary and clear-screen behavior after submission.

## 4. Web Flow
- [x] 4.1 Add configuration panel to the web portal mirroring terminal controls (transport choice, option visibility, timeout) before presenting choices.
- [x] 4.2 Ensure server shutdown and result payload include the configured values.

## 5. Testing
- [x] 5.1 Add/extend pytest coverage for configuration parsing, timeout overrides, and normalized outputs across transports.
- [ ] 5.2 Manual smoke: terminal config surface renders and applies; web config panel renders, applies, and shuts down cleanly.
