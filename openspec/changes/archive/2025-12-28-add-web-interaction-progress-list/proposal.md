# Change: Add web interaction progress list

## Why
- Users cannot see the status or interface type of active/recent interactions in the web portal, making it hard to pick the right session after multiple agent-triggered prompts.
- Concurrent tool invocations can spawn multiple web interactions that overlap; without a clear list and status badges, users risk interacting with the wrong session or missing timeouts.

## What Changes
- Add a left-side interaction list in the web UI showing active interactions plus the five most recent completed ones with their status (submitted, auto-submitted, timeout, pending, cancelled) and interface type (web, terminal), including terminal sessions in the list.
- Surface per-interaction metadata (started time, session id) with filters (e.g., active vs completed) and ensure status updates when submissions, auto-submits, cancellations, or timeouts occur.
- Handle concurrent interactions from multiple agents by isolating session state, keeping the list stable, and letting users re-enter the correct session safely while temporarily replacing the separate dashboard view with the sidebar list.

## Impact
- Affected specs: choice-orchestration
- Affected code: choice/web/templates.py, choice/web/templates/*.html, choice/web/session.py, choice/orchestrator.py, choice/response.py, tests under tests/test_web_timeout.py and related web/session coverage
