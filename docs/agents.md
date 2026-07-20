# Agents

An **agent** is a configured reasoning unit: a provider, a system prompt, a
scoped set of tools, a memory manager, and permission/limits.

## Defining an agent

```python
from aiforge.agents.agent import AgentConfig

config = AgentConfig(
    name="analyst",
    role="analyst",                 # built-in archetype (see Roles)
    system_prompt="Quantify everything.",
    tools=["calculator", "json_query"],   # allow-list; [] = no tools
    permissions=["fs"],             # None = allow all; list = grants
    max_steps=8,
    use_memory=True,
)
agent = engine.create_agent(config)
```

Or use the SDK:

```python
agent = forge.agent("analyst", role="analyst", tools=["calculator"])
```

## Roles

Built-in roles (`aiforge.agents.roles.AgentRole`): `assistant`, `researcher`,
`coder`, `analyst`, `planner`, `critic`, `router`, `executor`. Each role bundles
a system-prompt fragment and default permissions. Register custom roles:

```python
from aiforge.agents.roles import ROLES, RoleDefinition
ROLES.register(RoleDefinition("legal", "You are a careful legal analyst.", []))
```

## Templates & profiles

Ready-made configs map to the catalog's example projects:

```python
agent = engine.agent_from_template("research_assistant")
# research_assistant, browser_agent, coding_agent, file_assistant,
# document_analyst, customer_support_agent, meeting_assistant,
# cybersecurity_agent, data_analysis_agent, automation_agent
```

## Lifecycle

Agents transition through `AgentStatus`: `CREATED → READY → RUNNING → DONE/ERROR`.
Lifecycle events (`AGENT_CREATED/START/STEP/END/ERROR`) are emitted on the bus.

## Permissions & limits

- **Tool scoping**: `tools=[...]` restricts which tools the agent may call;
  `allow_all_tools=True` grants everything registered.
- **Permissions**: `permissions=[...]` grants capabilities (`fs`, `network`,
  `shell`, …) that tools may require. `None` means allow-all.
- **Execution limits**: `max_steps`, plus engine-wide token and tool-call caps
  from `ExecutionLimits`, prevent runaway loops.

## Communication & coordination

```python
from aiforge.agents.communication import Coordinator

coord = engine.coordinator
chosen = coord.route("analyse quarterly revenue")     # pick best agent
result = coord.pipeline("draft a report", ["planner", "executor"])  # chain
engine.messages.send(AgentMessage(sender="a", recipient="b", content="hi"))
```
