# Workflows

A **workflow** is an ordered set of **steps** executed against a shared
`ExecutionContext`. The engine emits events, persists execution history, and
enforces validation.

## Building a workflow

```python
from aiforge.workflows.builder import WorkflowBuilder
from aiforge.workflows.steps import ToolStep, AgentStep

wf = (WorkflowBuilder("report", "Compute then explain")
        .set({"topic": "growth"})
        .tool("calculator", {"expression": "40 + 2"}, output_var="answer")
        .agent("assistant", "Explain {answer} about {topic}", output_var="text")
        .parallel([
            AgentStep("critic", "Critique: {text}", name="review"),
            ToolStep("word_count", {"text": "{text}"}, name="count"),
        ])
        .build())

result = engine.run_workflow(wf, {"input": "start"})
```

## Step types

| Step | Purpose |
|------|---------|
| `SetVariableStep` | Assign context variables |
| `ToolStep` | Invoke a registered tool |
| `AgentStep` | Invoke a registered agent (prompt supports `{var}` templating) |
| `SequenceStep` | Run children in order |
| `ConditionalStep` | Branch on a condition (`then`/`else`) |
| `BranchStep` | Multi-way switch with a default |
| `ParallelStep` | Run children concurrently (threads) |
| `LoopStep` | Iterate over a variable or `while` a condition holds |
| `RetryStep` | Retry a wrapped step on failure |
| `TimeoutStep` | Fail a wrapped step after N seconds |
| `FallbackStep` | Try candidates until one succeeds |
| `NestedWorkflowStep` | Run another workflow as one step |
| `FunctionStep` | Run arbitrary `fn(context)` |

## Input resolution

Step arguments resolve special forms against the context:
`"$var"` or `{"$var": "name"}` reads a context variable, `{"$last": true}` reads
the previous step's output, and `AgentStep` prompts also expand `{var}` tokens.

## Conditions

Conditions are either a callable `fn(context) -> bool` or a **string expression**
evaluated in a sandbox (no builtins) against the context variables, e.g.
`"n > 5 and status == 'ok'"`.

## Validation

`workflow.validate()` returns a list of problems; `ensure_valid()` raises. The
engine validates before running (unique step names, non-empty, per-step checks).

## Serialization

Declarative workflows round-trip to/from JSON:

```python
from aiforge.workflows.serialization import workflow_to_json, workflow_from_json
text = workflow_to_json(wf)
restored = workflow_from_json(text)
```

Steps backed by Python callables (`FunctionStep`, callable conditions) cannot be
reconstructed from data and raise on load.
