## 1. Implementation
- [ ] 1.1 Model the terminal hand-off session (session id, launch address/command, persistence of pending state, and result envelope mapping to `ProvideChoiceResponse`).
- [ ] 1.2 Extend the response/action-status contract to support the pending terminal launch, including surfacing the launch address in `selection.url`/`selection.summary` and validating the new status.
- [ ] 1.3 Build the terminal hand-off flow: spawn session, return immediately, attach a terminal client that renders questionary, posts results back, and enforces timeout/cancel.
- [ ] 1.4 Wire orchestrator/config store with the hand-off flow, ensure configuration defaults carry through, and add/adjust unit tests for the new terminal path.
- [ ] 1.5 Update CLI/docs/smoke instructions for launching the terminal UI via the returned command and document timeout/cancel expectations.
