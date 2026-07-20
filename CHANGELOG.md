# Changelog

All notable changes to AIForge are documented here. This project follows
[Semantic Versioning](https://semver.org/).

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
