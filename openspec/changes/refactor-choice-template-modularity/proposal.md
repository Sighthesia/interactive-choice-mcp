# Change: Refactor choice web template into modular assets

## Why
The current `src/templates/choice.html` inlines style, markup, script, configuration persistence, and i18n handling in a single 2.5k-line file. This makes UX changes risky, duplicates configuration wiring across sections, and scatters i18n updates inside logic-heavy code. Developers need a maintainable layout where web assets are grouped by concern and centrally managed.

## What Changes
- Split the web portal into modular assets (CSS, JS, markup fragments) grouped by concern (layout, interaction list, timeout, config/i18n, interface state) with a lightweight assembly step.
- Introduce a manifest-driven template builder so `templates.py` composes the final page from reusable fragments or a hashed static bundle instead of a monolithic inline file, with a FastAPI static route for cache-friendly delivery.
- Centralize i18n payload injection and configuration defaults in dedicated modules to avoid scattered text/setting mutations.
- Keep the delivered page footprint stable (single HTML response or versioned static bundle) while making source maintenance focused.

## Impact
- Affected specs: `choice-orchestration` (web template modularity and maintainability)
- Affected code: `src/templates/choice.html`, `src/web/templates.py`, `src/web/server.py`, potential new `src/web/frontend/*` asset sources
