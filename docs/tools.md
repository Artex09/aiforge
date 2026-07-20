# Tools

Tools are AIForge's unit of action. A tool declares a JSON schema, required
permissions, and a `run` implementation. Arguments are validated (and coerced)
against the schema before execution.

## Defining a tool

The `@tool` decorator derives a schema from your function signature:

```python
from aiforge.tools.base import tool, ToolResult

@tool(description="Add two numbers")
def add(a: int, b: int = 0) -> int:
    return a + b

engine.tools.register(add)
```

Return a plain value or a `ToolResult`. Class-based tools subclass `Tool` and set
`name`, `description`, `parameters`, `permissions`, and optionally
`wants_context = True` to receive a `ToolContext`.

## Built-in tools

`calculator`, `read_file`, `write_file`, `list_dir`, `http_request`,
`web_search`, `current_datetime`, `json_parse`, `json_query`, `summarize_text`,
`word_count`, and a guarded `shell` (disabled unless `security.allow_shell`).

```python
engine.call_tool("calculator", {"expression": "2 * (3 + 4)"})
```

## Permissions & isolation

- Tools declare `permissions` (e.g. `fs`, `network`, `shell`). Callers must hold
  the grant or a `ToolPermissionError` is raised.
- File tools resolve paths **inside the sandbox root**; traversal outside is
  rejected. Direct SDK/API calls run with full grants scoped to the sandbox.
- The `calculator` uses an AST allow-list (no `eval`); `shell` is off by default.

## Tool context

Tools with `wants_context = True` (or a `context` parameter) receive a
`ToolContext` exposing `state`, `memory`, `events`, `config`, `secrets`,
`sandbox_root`, and `permissions` — no globals required.

## Discovery

```python
engine.tools.discover("my_package.tools")   # import + auto-register Tools
```

## Chaining

```python
from aiforge.tools.chaining import ToolChain
chain = ToolChain(engine.tools)
chain.add("current_datetime", {"fmt": "iso"})
chain.add("word_count", map_input=lambda out: {"text": str(out)})
chain.run()
```
