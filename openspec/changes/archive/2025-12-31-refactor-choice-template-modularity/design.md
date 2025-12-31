## Context
`src/templates/choice.html` currently embeds CSS, markup, JS, config persistence, WebSocket handling, timeout logic, interaction list rendering, and i18n helpers in one 2.5k-line file. There is no asset manifest or static delivery path, so any UX tweak requires navigating unrelated logic and risks regressions. We need modular source files while still emitting a single deliverable page for the web portal.

## Goals / Non-Goals
- Goals: separate front-end sources by concern (styles, config/i18n, rendering, sockets/timeout, interaction list), centralize settings/i18n wiring, and introduce a simple assembly pipeline that keeps runtime delivery intact.
- Non-Goals: redesign the UI, change selection semantics, or introduce a new JS bundler/toolchain.

## Decisions
- **Source layout**: introduce `src/web/frontend/` with `styles/` (e.g., `base.css`, `layout.css`, `components.css`, `responsive.css`) and `scripts/` (e.g., `bootstrap.js` for bootstrapping data, `i18n.js`, `config.js`, `render.js`, `websocket.js`, `interaction_list.js`, `timeout.js`, `submission.js`). Keep the HTML shell in `src/web/templates/choice_base.html` with placeholders for CSS/JS and data blocks.
- **Assembly strategy**: add a lightweight template builder in `templates.py` that reads a manifest (ordered list of CSS and JS sources), concatenates them, and injects them into the shell at render time. Cache the concatenated strings in memory to avoid repeated disk I/O per request; compute a version hash (e.g., sha1 of concatenated content) for cache busting.
- **Delivery strategy**: expose a FastAPI static route serving the hashed bundle (CSS and JS) with cache headers. The shell references versioned URLs by default, with an inline fallback path for environments where static serving is disabled.
- **Data injection**: keep server-provided payloads (`defaults_json`, `options_json`, `session_state_json`, `i18n_json`) as dedicated `<script type="application/json">` blocks. `bootstrap.js` will read these blocks into a namespaced object (e.g., `window.mcpData`) consumed by other modules to avoid scattered DOM queries.
- **i18n/config centralization**: `i18n.js` exposes `t(key)` using the injected JSON, and `config.js` owns language/theme/notification/interface persistence plus debounce logic. Other modules consume these helpers instead of touching DOM or storage directly.
- **Interaction wiring**: `render.js` handles option rendering and annotations; `websocket.js` covers session sync and reconnection; `timeout.js` manages countdowns; `interaction_list.js` manages the sidebar feed and fallback polling; `submission.js` orchestrates payload building and status rendering. Each module exports functions consumed by a small entrypoint (in `bootstrap.js`).
- **Compatibility**: final HTML delivered to the browser remains functional even if static serving fails, via the inline fallback. The assembly preserves existing placeholders and request parameters so server behavior and tests stay compatible.

## Risks / Trade-offs
- Multiple source files increase build-time complexity; mitigated by a simple manifest and in-memory cache.
- Module ordering errors could break runtime initialization; mitigated by an explicit manifest and a shared bootstrap entrypoint.
- Inline bundling keeps payload size similar to today; no minification is planned to preserve readability, accepting slightly larger responses than separate cached assets.

## Migration Plan
1. Create the asset manifest and shell template with placeholders for styles, scripts, data payloads, and versioned URLs.
2. Move CSS into grouped files and JS into modules following the manifest order; adapt code to consume `bootstrap.js` data instead of scattered globals.
3. Implement builder in `templates.py` that concatenates manifest assets, caches content, injects into the shell, and emits the hashed bundle for the static route while keeping an inline fallback.
4. Wire the FastAPI static route, set cache headers, and inject the hashed URLs into the shell.
5. Add smoke tests that load the static bundle route (200 OK, hash match, manifest order) and verify the bootstrap wiring remains intact.
6. Update tests to validate assembled HTML includes expected payload blocks, i18n keys, and entrypoint wiring; run full test suite.

## Open Questions
- Do we need additional cache-busting controls (e.g., short TTL) for environments that cannot invalidate static assets promptly?
