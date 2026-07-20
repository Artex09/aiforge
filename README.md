# AIForge

**A modular framework for building autonomous multi-agent AI systems.**

AIForge provides a complete, production-oriented foundation for creating,
orchestrating, and monitoring AI agents that collaborate, reason, use tools,
manage memory, and execute complex workflows.

The **core framework runs on the Python standard library alone** — no external
dependencies are required. It ships with an offline mock LLM provider so every
feature (agents, tools, memory, workflows, the REST API, and the dashboard)
runs out of the box with zero API keys. Real providers (OpenAI-compatible,
Anthropic) are optional, lazily-imported adapters.

---

## Design principles

Modular · Extensible · Framework-first · Provider-agnostic · Tool-first ·
Memory-first · Event-driven · Production-ready · Developer-friendly.

## Architecture at a glance

```
                         ┌───────────────────────────┐
   CLI / SDK / REST API  │          Engine           │  ← composition root
                         │  (wires every subsystem)   │
                         └────────────┬──────────────┘
        ┌───────────────┬────────────┼─────────────┬───────────────┐
     Agents         Workflows      Memory        Tools          Providers
   (registry,      (steps, engine, (short/long/  (registry,     (mock, openai,
    roles, comms)   builder, ser.)  vector, mgr)  builtins,      anthropic,
        │               │            │            chaining)       fallback)
        └───────────────┴─────┬──────┴─────────────┴───────────────┘
                          Event Bus  ── Monitoring ── Storage (local/sqlite/vector)
                          State Manager · Security (secrets/permissions/limits/sandbox)
                          Plugin System · Config · Dashboard
```

## Repository layout

```
aiforge/
├── core/        # engine, types, errors, context, state, security, monitoring
├── agents/      # agent definition, registry, roles, templates, communication
├── workflows/   # steps, engine, builder, serialization
├── memory/      # short/long/working/session/vector stores + manager
├── tools/       # registry, base+decorator, context, chaining, builtin/
├── events/      # publish/subscribe event bus
├── providers/   # LLM provider contract, mock, openai, anthropic, registry
├── plugins/     # typed plugin interfaces + manager + examples/
├── dashboard/   # vanilla HTML/CSS/JS UI (no frontend framework)
├── api/         # REST API on the Python stdlib http.server
├── sdk/         # AIForge high-level SDK facade
├── cli/         # argparse-based command line interface
├── storage/     # local, sqlite, cache, vector store backends
└── config/      # layered configuration (defaults + file + env + runtime)
examples/  tests/  docs/  assets/
```

## Install

```bash
# from the repository root
pip install -e .            # core, zero required dependencies

# optional extras
pip install -e ".[openai]"      # OpenAI-compatible provider
pip install -e ".[anthropic]"   # Anthropic (Claude) provider
pip install -e ".[vector]"      # NumPy acceleration for vector memory
pip install -e ".[dev]"         # pytest for the test suite
```

## Quick start — serial agents (Crew)

The easiest way to build something useful: a **crew** of agents whose **tasks run
in sequence**, each receiving the previous results as context.

```python
from aiforge.sdk import AIForge

forge = AIForge()

forge.agent("researcher", role="researcher", allow_all_tools=True)
forge.agent("writer", role="assistant", allow_all_tools=True)

crew = forge.crew([
    forge.task("Research the impact of AI agents on software engineering", agent="researcher"),
    forge.task("Write a short report from the research", agent="writer"),
])

result = crew.kickoff()
print(result.output)          # final task output
for t in result.task_outputs: # every step, in order
    print(t["agent"], "→", t["output"][:80])
```

## Quick start (single agent)

```python
from aiforge.sdk import AIForge

forge = AIForge()

# Build an agent with access to all built-in tools
agent = forge.agent("assistant", system_prompt="You are helpful.", allow_all_tools=True)
print(forge.run(agent, "What is 21 * 2?").output)

# Semantic memory
forge.remember("AIForge is provider-agnostic", semantic=True)
print(forge.recall("what is aiforge?"))

# A workflow
wf = (forge.workflow("demo")
        .tool("calculator", {"expression": "10 + 5"}, output_var="sum")
        .agent("assistant", "Explain the number {sum}")
        .build())
print(forge.run_workflow(wf, {"input": "start"}).output)
```

## Quick start (CLI)

```bash
python -m aiforge.cli version
python -m aiforge.cli list tools
python -m aiforge.cli run-template research_assistant "Summarise AIForge"
python -m aiforge.cli serve --port 8787        # REST API + dashboard
python -m aiforge.cli init ./my-project        # scaffold a new project
```

## Studio — the visual workflow builder (Node UI)

AIForge ships a **Node.js flow-based Studio**: a React + React Flow canvas where
you drag **Agent**, **Task**, and **Trigger** nodes, wire them into a sequential
crew, describe what you want in the **Studio Chat** (which plans a specialised
crew for your brief — software, data, content, or research), and hit **Run** —
with per-task results streamed live into the Run tab. It lives in
[`aiforge/frontend/`](aiforge/frontend/).

Beyond the canvas, every page is functional:

- **Automations** — name a crew, hit *Save*, reopen or delete it later.
- **Agents Repository** — real agent templates you can add to the canvas in one click.
- **Tools & Integrations** — the sandboxed builtin tool catalog.
- **Traces** — every run recorded: status, tasks, tokens, cost, model, duration.
- **LLM Connections** — connect OpenAI/Anthropic from the UI (see below).
- **Usage** — live metrics plus run/cost totals. **Settings** — live workspace config.

```bash
# 1) build the UI once (outputs aiforge/frontend/dist)
cd aiforge/frontend
npm install
npm run build

# 2) serve it (the stdlib API server hosts the built SPA)
cd ../..
python -m aiforge.cli studio          # http://127.0.0.1:8787
```

For UI development with hot reload, run the API on :8787 and Vite on :5173
(Vite proxies `/api` to the engine):

```bash
python -m aiforge.cli serve                 # terminal 1 (engine + API)
cd aiforge/frontend && npm run dev          # terminal 2 (http://127.0.0.1:5173)
```

If the UI hasn't been built, `serve` falls back to the zero-dependency
vanilla-JS dashboard (live execution, tools, memory, timeline, analytics).

## Using a real provider

The quickest way: open the Studio's **LLM Connections** page, paste your API
key, pick a model, and press *Connect* — it becomes the default provider
immediately. The key is held in the engine's in-memory vault only (never
written to disk, never returned by the API).

From the environment instead (`pip install openai` or `anthropic` first):

```powershell
$env:OPENAI_API_KEY = "sk-…"                 # or ANTHROPIC_API_KEY
$env:AIFORGE_PROVIDER__DEFAULT = "openai"    # or "anthropic"
python -m aiforge.cli studio
```

Or from code:

```python
import os
from aiforge.sdk import AIForge

forge = AIForge(overrides={"provider": {"default": "openai"}})
forge.set_secret("OPENAI_API_KEY", os.environ["OPENAI_API_KEY"])
# or ANTHROPIC_API_KEY with provider.default = "anthropic"
```

## Examples

Ten runnable example projects live in [`examples/`](examples/), one per catalog
use case: research assistant, browser agent, coding agent, file assistant,
document analyst, customer support, meeting assistant, cybersecurity (defensive),
data analysis, and automation. All run offline.

```bash
python examples/01_research_assistant.py
```

## Tests

```bash
pip install -e ".[dev]"
pytest
```

## Documentation

See [`docs/`](docs/): Getting Started, Architecture, Agents, Workflows, Tools,
Memory, Plugins, Examples, API Reference, and SDK Reference.

## Roadmap

Distributed agents · remote workers · multi-machine execution · voice agents ·
computer use · MCP support · agent marketplace · visual workflow builder ·
cloud deployment · team collaboration.

## License

MIT.
