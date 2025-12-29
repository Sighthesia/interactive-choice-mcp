## 1. Preparation
- [x] 1.1 Define frontend asset layout (CSS/JS fragments, markup partials) and manifest ordering
- [x] 1.2 Add template-builder scaffolding (Python) to assemble assets for rendering and cache/etag handling

## 2. Asset extraction
- [x] 2.1 Extract CSS from `src/templates/choice.html` into concern-based files (layout/components, typography, responsive)
- [x] 2.2 Extract JS into modules (config+i18n, rendering, websocket/timeout, interaction list, submission) wired via manifest entrypoint
- [x] 2.3 Create minimal HTML shell that references assembled assets or inlined bundle while preserving current data placeholders

## 3. Server integration
- [x] 3.1 Update `templates.py` to load assembled assets (inline or static URLs) and keep current substitution variables intact
- [x] 3.2 Update `web/server.py` to serve static bundle if needed and ensure timeout/i18n/config payloads flow unchanged
- [x] 3.3 Add a FastAPI static route (hashed bundle path) plus cache headers; inject versioned URLs into the shell when not inlined

## 4. Validation
- [x] 4.1 Add/adjust tests to cover asset assembly, i18n payload availability, and backwards-compatible rendering
- [x] 4.2 Add a smoke test for the static asset route (200 OK, correct content hash/order) and manifest ordering
- [x] 4.3 Run `uv run pytest` and `openspec validate refactor-choice-template-modularity --strict`
