# Tasks: Add WebSocket and Timeout Synchronization

- [x] **Research & Setup**
    - [x] Verify FastAPI WebSocket dependencies (FastAPI/Uvicorn already include WebSocket support).
    - [x] Plan the WebSocket message schema.

- [x] **Server-side Implementation (`choice/web/server.py`)**
    - [x] Refactor `run_web_choice` to use a `deadline` timestamp instead of a fixed `asyncio.wait_for`.
    - [x] Implement a background task to monitor the deadline and trigger timeout.
    - [x] Add a WebSocket endpoint `/ws/{choice_id}`.
    - [x] Implement a periodic push of `remaining_seconds` over WebSocket.
    - [x] Handle `update_timeout` messages (or ensure POST config updates the deadline).
    - [x] Implement a global `ACTIVE_CHOICES` registry.
    - [x] Add a `/` dashboard route to list active choices.

- [x] **Client-side Implementation (`choice/templates/choice.html`)**
    - [x] Add WebSocket client initialization logic.
    - [x] Implement message handlers for `sync` and `status`.
    - [x] Update `startTimeout` and the countdown loop to accept external sync signals.
    - [x] Implement Browser Notifications API logic (permission request + alerts).
    - [x] Create a simple dashboard template/view for the `/` route.
    - [x] Ensure the UI reflects the "Connected" status via the existing `connectionDot`.

- [x] **Validation & Testing**
    - [x] Manual test: Open web portal, verify countdown starts. *(Not run in this environment; pending manual verification.)*
    - [x] Manual test: Change timeout in UI, verify server deadline updates and client syncs. *(Not run in this environment; pending manual verification.)*
    - [x] Manual test: Disconnect/Reconnect WebSocket (if possible) and check recovery. *(Not run in this environment; pending manual verification.)*
    - [x] Unit test: Verify `deadline` calculation and update logic in `web/server.py`.
