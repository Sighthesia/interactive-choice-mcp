# Proposal: Add WebSocket and Timeout Synchronization

## Metadata
- **Change ID**: `add-websocket-timeout-sync`
- **Status**: Draft
- **Author**: GitHub Copilot
- **Date**: 2025-12-27

## Summary
Implement a WebSocket-based synchronization mechanism between the FastAPI server and the web portal. This will allow real-time updates of the remaining timeout duration, ensuring the client-side countdown is always in sync with the server-side expiration. It also enables the server to push status updates and potentially handle dynamic timeout adjustments from the UI. **Additionally, the proposal includes browser notifications for timeout alerts and a central dashboard to view and re-enter active interactions.**

## Motivation
Currently, the web portal uses a client-side timer that is initialized once. If the user changes the timeout in the UI, it only affects the client-side countdown, while the server-side `asyncio.wait_for` remains fixed. Furthermore, there is no real-time connection monitoring. WebSocket provides a more robust way to keep the client and server state consistent, especially for time-sensitive interactions like timeouts. **Users also need a way to be notified when a timeout is approaching even if the tab is not focused, and a way to recover active sessions if a tab is accidentally closed.**

## Why
Keeping the server-side deadline authoritative prevents mismatches that can lead to incorrect auto-submissions or silent cancellations. WebSocket enables low-latency two-way communication which is necessary for both pushing remaining-time updates and for allowing the UI to adjust server-side deadlines when users change timeout settings. The dashboard and notifications address user experience problems caused by background tabs or accidental tab closures.

## Scope
- **FastAPI Server**: Add a `/ws/{choice_id}` endpoint and a `/` dashboard endpoint.
- **Timeout Management**: Replace static `asyncio.wait_for` with a dynamic deadline-based approach that can be updated.
- **Web Portal (JS)**: Implement WebSocket client logic, Web Notifications API, and a dashboard UI.
- **Synchronization**: Periodically push or allow querying of the remaining time.
- **Session Recovery**: Maintain a registry of active choices to display on the dashboard.

## What Changes
- Add server WebSocket endpoint and deadline monitor in `choice/web.py`.
- Add dashboard template `choice/templates/dashboard.html` and integrate an active registry.
- Enhance client template `choice/templates/choice.html` with WebSocket client, sync logic and notifications.
- Add accompanying OpenSpec docs under `openspec/changes/add-websocket-timeout-sync/` (proposal, design, spec delta, tasks).

## Relationships
- Modifies `choice-orchestration` spec to formalize WebSocket usage for synchronization.
- Builds upon the existing Web Bridge Flow.
