# Architecture

AIForge is organised around a central **Engine** that composes independent
subsystems. Each subsystem has a narrow contract and can be replaced or extended
via plugins.

## The Engine (composition root)

`aiforge.core.engine.Engine` constructs and wires:

| Subsystem | Module | Responsibility |
|-----------|--------|----------------|
| Config | `config/` | Layered settings (defaults + file + env + runtime) |
| Events | `events/` | Framework-wide publish/subscribe bus + lifecycle hooks |
| Storage | `storage/` | Local/SQLite key-value + collections, cache, vector store |
| Providers | `providers/` | LLM adapters with capabilities + fallback |
| Tools | `tools/` | Registry, schema validation, permissions, chaining |
| State | `core/state.py` | Global/local/shared state, versioning, persistence |
| Memory | `memory/` | Short/long/working/session/vector stores + manager |
| Agents | `agents/` | Definition, registry, roles, templates, communication |
| Workflows | `workflows/` | Steps, engine, builder, serialization |
| Security | `core/security.py` | Secrets, permissions, limits, sandbox, auth |
| Monitoring | `core/monitoring.py` | Metrics, timeline, error tracking |
| Plugins | `plugins/` | Typed extension points + manager |
| API | `api/` | REST endpoints on the stdlib http.server |
| Dashboard | `dashboard/` | Vanilla HTML/CSS/JS UI |

## Data flow of an agent run

1. `Agent.run(input)` assembles a message list: system prompt (role + custom) +
   relevant **memory** + history + the user input.
2. It enters a bounded loop (`max_steps`). Each iteration calls the **provider**
   with the agent's allowed **tool** schemas.
3. If the model returns tool calls, each is validated and executed through the
   **tool registry** (permissions + limits enforced), and results are appended.
4. Otherwise the loop ends with a final answer. Interactions are written to
   **memory**; **events** are emitted throughout for **monitoring**.

## Event-driven core

Every subsystem emits typed events (`EventType`) — agent/workflow/tool/memory/
LLM/error lifecycle. The `Monitor` subscribes to all of them to build metrics
and an execution timeline; plugins and user code can subscribe too. Handlers are
isolated: a failing subscriber never breaks the emitter.

## Provider-agnostic LLM layer

Providers implement a single contract (`chat`, `stream`, `structured`, `embed`)
and declare `ProviderCapabilities`. The `ProviderRegistry` supports an ordered
fallback chain so a failing primary rolls over automatically. The **mock**
provider implements the full surface offline and deterministically.

## Zero-dependency by default

The entire core — including vector similarity, embeddings (hash-based fallback),
the REST API, and the dashboard — is implemented with the standard library.
Third-party packages (`openai`, `anthropic`, `numpy`, `PyYAML`) are optional and
imported lazily only when used.
