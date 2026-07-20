# SDK Reference

`aiforge.sdk.AIForge` is the high-level facade over the `Engine`.

## Construction

```python
AIForge(config=None, config_path=None, overrides=None)
```

- `config` — a prebuilt `Config`.
- `config_path` — path to a JSON/YAML config file.
- `overrides` — a dict merged on top with highest precedence.

## Agents

```python
forge.agent(name, *, role="assistant", system_prompt="", tools=None,
            provider=None, template=None, **kwargs) -> Agent
forge.run(agent, user_input, **kwargs) -> RunResult
```

- `tools=None` + `allow_all_tools=True` grants every registered tool; a list
  scopes to those tool names.
- `template=...` builds from a named template (see [Agents](agents.md)).

## Tools

```python
forge.tool(func_or_tool=None, **kwargs)   # register (also usable as a decorator)
forge.call_tool(name, **arguments) -> ToolResult
```

## Memory

```python
forge.remember(content, semantic=False, **metadata) -> str
forge.recall(query, top_k=5) -> list[str]
```

## Workflows

```python
forge.workflow(name, description="") -> WorkflowBuilder
forge.run_workflow(workflow, inputs=None) -> RunResult
```

## Providers & secrets

```python
forge.register_provider(provider, default=False)
forge.set_secret("OPENAI_API_KEY", "...")
```

## Server & introspection

```python
forge.serve(host=None, port=None)     # REST API + dashboard
forge.status() -> dict                # providers, tools, agents, memory, plugins
forge.load_plugins(path) -> list[str]
```

## Escaping to the Engine

Everything the SDK wraps is available on `forge.engine` — `providers`, `tools`,
`agents`, `memory`, `state`, `events`, `monitor`, `workflow_engine`,
`coordinator`, `plugins`, `secrets`, `sandbox`, and `config`.

## Return types

- `RunResult` — `output`, `success`, `error`, `steps`, `usage`, `messages`,
  `duration`, `to_dict()`.
- `ToolResult` — `ok`, `output`, `error`, `metadata`, `to_dict()`.
