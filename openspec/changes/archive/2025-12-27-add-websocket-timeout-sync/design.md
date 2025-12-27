# Design: WebSocket and Timeout Synchronization

## Architecture Overview
The synchronization mechanism relies on a WebSocket connection established as soon as the web portal loads. The server maintains the "source of truth" for the expiration time (deadline).

### 1. Server-side Timeout Management
Instead of a single `asyncio.wait_for` call, the `run_web_choice` function will:
- Maintain a `deadline` (timestamp).
- Use an `asyncio.Event` or a loop with a short sleep to check if the deadline has passed or if a result has been submitted.
- Provide a way to update the `deadline` if the user changes the timeout value in the UI (via POST or WS).

### 2. WebSocket Protocol
- **Endpoint**: `/ws/{choice_id}`
- **Server -> Client Messages**:
  - `{"type": "sync", "remaining_seconds": float}`: Sent periodically (e.g., every 5 seconds) or upon connection.
  - `{"type": "status", "status": "connected" | "timeout" | "submitted"}`: General status updates.
- **Client -> Server Messages**:
  - `{"type": "ping"}`: Keep-alive.
  - `{"type": "update_timeout", "seconds": int}`: (Optional) Update the server-side deadline.

### 3. Client-side Countdown Logic
- The client maintains its own local countdown for smooth UI updates (1fps).
- When a `sync` message is received via WebSocket, the client adjusts its local `_timeoutRemaining` to match the server's `remaining_seconds`.
- If the WebSocket disconnects, the client can attempt to reconnect or fallback to the local timer.

### 4. Browser Notifications
- The web portal will request notification permissions upon first load.
- A notification will be triggered when:
  - The timeout is less than 10 seconds (and the tab is not focused).
  - The interaction has timed out.

### 5. Active Interaction Dashboard
- A global `ACTIVE_CHOICES` registry will be maintained in `web.py`.
- The FastAPI app will include a `/` route that renders a simple list of all currently active `choice_id`s with their titles and remaining time.
- This allows users to re-enter an interaction if they accidentally close the tab.

## Data Flow
1. `run_web_choice` starts, sets `deadline = now + timeout_seconds`, and registers the choice in `ACTIVE_CHOICES`.
2. Browser opens `/choice/{id}`, JS connects to `/ws/{id}`.
3. Server sends initial `sync` message with `remaining_seconds`.
4. JS starts local countdown and requests notification permissions.
5. Every 5 seconds, server pushes a `sync` message.
6. If user changes timeout in UI, JS sends `update_timeout` to server (or via existing POST config update).
7. Server updates `deadline`.
8. If `now > deadline`, server sets `result_future` to `timeout_response`, notifies client via WS, and triggers a browser notification.
9. Upon completion (submit/cancel/timeout), the choice is removed from `ACTIVE_CHOICES`.

## Trade-offs
- **Complexity**: Adding WebSocket increases the complexity of the `web.py` module.
- **Resource Usage**: Keeping a WS connection open uses slightly more resources than pure REST, but for a single-user local tool, this is negligible.
- **Robustness**: WebSocket provides better "liveness" detection than polling.

## Alternatives Considered
- **Polling**: Client could call a GET `/remaining` endpoint every few seconds. This is simpler to implement but less efficient and less "real-time" than WebSocket.
- **Server-Sent Events (SSE)**: Good for one-way server-to-client updates. WebSocket was chosen because it allows two-way communication (e.g., updating timeout from client).
