# REST API Reference

The API is served by the Python standard library (`http.server`) — no external
web framework. Start it with `python -m aiforge.cli serve` (default
`http://127.0.0.1:8787`). It also serves the dashboard from `/`.

## Authentication

If `api.auth_token` is set, requests to `/api/*` must send
`Authorization: Bearer <token>`. When unset, the API is open (local dev).

## Endpoints

| Method | Path | Body / Query | Returns |
|--------|------|--------------|---------|
| GET | `/api/health` | — | `{status}` |
| GET | `/api/status` | — | engine status snapshot |
| GET | `/api/providers` | — | `{providers}` |
| GET | `/api/tools` | — | OpenAI-style tool schemas |
| POST | `/api/tools/{name}/run` | `{arguments}` | tool result |
| GET | `/api/agents` | — | agent configs |
| POST | `/api/agents` | `{template}` or agent config | `{created}` |
| POST | `/api/agents/{name}/run` | `{input}` | run result |
| GET | `/api/memory` | `?query=&top_k=` | ranked records |
| POST | `/api/memory` | `{content}` | `{id}` |
| GET | `/api/memory/stats` | — | per-store counts |
| POST | `/api/workflows/run` | `{workflow, inputs}` | run result |
| GET | `/api/metrics` | — | metrics + tool usage + errors |
| GET | `/api/timeline` | `?limit=` | recent events (timeline) |
| GET | `/api/events` | `?limit=` | raw event history |
| GET | `/api/executions` | — | execution history |
| GET | `/api/logs` | — | persisted event log |
| GET | `/api/plugins` | — | loaded plugins |
| GET | `/api/templates` | — | available agent templates |

## Examples

```bash
curl http://127.0.0.1:8787/api/health

curl -X POST http://127.0.0.1:8787/api/agents \
  -H 'Content-Type: application/json' \
  -d '{"template": "research_assistant"}'

curl -X POST http://127.0.0.1:8787/api/agents/research_assistant/run \
  -H 'Content-Type: application/json' \
  -d '{"input": "Summarise AIForge"}'

curl -X POST http://127.0.0.1:8787/api/tools/calculator/run \
  -H 'Content-Type: application/json' \
  -d '{"arguments": {"expression": "6 * 7"}}'
```

## Embedding the server

```python
from aiforge.api.server import serve, serve_in_thread
serve(engine)                       # blocking
server = serve_in_thread(engine)    # background thread (tests); server.shutdown()
```
