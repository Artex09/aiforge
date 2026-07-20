# Changelog

All notable changes to AIForge are documented here. This project follows
[Semantic Versioning](https://semver.org/).

## [0.3.0]

### Added — every Studio page is now real
- **LLM Connections page:** connect OpenAI or Anthropic from the UI — paste a
  key, pick a model (or a custom OpenAI-compatible base URL), and it becomes
  the default provider. Keys live in the engine's in-memory vault only: never
  written to disk, never echoed back by the API.
  (`POST /api/providers/connect|default|disconnect`, richer `GET /api/providers`.)
- **Traces page:** every crew run is recorded (status, tasks, tokens, cost,
  model, duration) and browsable with per-task detail. (`GET /api/runs`;
  runs persist via the storage backend.)
- **Automations page:** save the current canvas as a named crew, reopen or
  delete it later. (`GET/POST /api/crews`, `DELETE /api/crews/{name}`.)
- **Settings page:** live workspace configuration (provider, security limits,
  storage, API) served by `GET /api/config` — auth token always redacted —
  plus a browser-side API bearer-token field and a canvas reset.
- **Agents Repository:** template cards now show the real role, description,
  and tool set (`GET /api/templates` returns full detail) with one-click
  "Add to Studio".
- **Studio:** editable crew name in the top bar (used when saving/running),
  a Save button, and example-prompt chips in a fresh chat.
- **Hash routing:** every page has a URL (`#/traces`, `#/connections`, …) so
  views are bookmarkable and the browser back button works.
- Usage page adds crew-run and total-cost stats.

### Changed
- Sidebar: removed the placeholder "Skills Repository" entry; the footer now
  shows the *default* provider rather than the first registered one.
- Topbar: removed the redundant Share button (Download covers export);
  Studio Chat's dead History button is now a working "New chat".
- The generic placeholder page (fake "Module · 1/2/3" tiles) is gone —
  every sidebar destination renders a functional page.

### Fixed
- **`Config.set` mutated the module-level `DEFAULTS`** because `_deep_merge`
  shallow-copied nested dicts — e.g. setting `api.auth_token` on one engine
  silently enabled auth for every engine created afterwards in the same
  process. Merges now deep-copy both sides.

## [0.2.0]

### Added — "make it real" (beyond the mock)
- **Live run streaming (SSE):** `POST /api/runs/stream` streams every run event
  (task/tool/LLM/token) as it happens; the Studio renders a live trace.
- **Retries with backoff + jitter** around every LLM call (`core/retry.py`),
  configurable via `provider.retries` / `provider.retry_base_delay`.
- **Structured-output validation:** `provider.structured()` now validates the
  result against a JSON schema (`core/schema.py`) and re-asks the model on
  mismatch, up to `max_attempts`.
- **Per-run token + cost accounting** (`core/pricing.py`); cost surfaces in
  `CrewResult`, the monitor, and the Studio run summary.
- **Reciprocal Rank Fusion (RRF)** for memory recall — principled fusion of
  vector + keyword + recency signals across stores.
- **Graph ⇄ code round-tripping:** `engine.graph_to_code()` and
  `POST /api/graph/code` render a visual crew as runnable Python (SDK calls).

### Added — Studio (Node UI)
- Click-to-edit **node inspector** (name, role, model, instructions, tools).
- **Right-click node context menu** (Edit / Duplicate / Delete).
- Working toolbar: **Variables**, **Share** (copy JSON), **Download** (JSON),
  **Export code** (Python), and a streaming **Run**.
- Auto-save to the browser; prominent, grabbable connection handles.

### Fixed
- **Studio Chat now plans a specialised crew per intent.** It previously
  answered every brief with the same "Research Specialist + Report Writer"
  pair, so "build a backend in Rust" came out as *research*. A new intent-aware
  planner (`agents/planner.py`) assembles domain-appropriate crews with
  action-oriented tasks: software → Architect + language-specific Developer(s)
  + QA (+ DevOps when deployment is requested); data → Data Engineer + Analyst
  + Insights; content → Strategist + Writer + Editor; research stays the
  default. Task ordering (`Engine._order_by_edges`) is hardened so a
  `trigger → task` edge never disturbs sequencing.
- Nodes could not be linked — connection handles were clipped by the node's
  `overflow: hidden`. Handles now render outside the card and connect reliably.
- Right-click showed the browser menu instead of node actions.
- "Run" produced no visible result — it now streams a live trace and results.
- Non-functional toolbar buttons are now all wired to real actions.

### Credibility
- Typed public API (`py.typed`), `CHANGELOG.md`, and a `SECURITY.md` policy.
- Built Studio (`frontend/dist`) is packaged for `pip install`.

## [0.1.0]

### Added
- Core framework: agents, sequential crews, workflow engine, memory (short/long/
  working/session/vector), tools + registry, event bus, provider layer (mock/
  OpenAI/Anthropic), storage (local/sqlite/vector), plugins, monitoring, config.
- REST API on the Python standard library; vanilla dashboard; SDK; CLI.
- Ten example projects; documentation; test suite.

### Security (0.1.x hardening)
- Removed `eval()` from workflow conditions in favor of an AST-allowlist
  evaluator (`core/safe_eval.py`).
- Dropped wildcard CORS; opt-in `api.cors_origins` only.
- Sandbox uses `realpath` (blocks symlink escape); `http_request` blocks
  non-HTTP schemes and private/loopback/metadata addresses.
- Agents deny-by-default on permissions; bounded calculator exponent; proper
  4xx API errors.
