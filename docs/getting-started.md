# Getting Started

## Install

```bash
pip install -e .            # core only (no third-party deps required)
pip install -e ".[all]"     # with optional providers, numpy, yaml
```

## Your first agent

```python
from aiforge.sdk import AIForge

forge = AIForge()
agent = forge.agent("assistant", system_prompt="You are concise.", allow_all_tools=True)
result = forge.run(agent, "What is 12 * 12?")
print(result.output)
```

Because the default provider is the offline **mock** provider, this runs with no
API keys. The agent will detect the arithmetic, call the built-in `calculator`
tool, and answer.

## Switching to a real provider

Set a key and point the default provider at it:

```python
import os
forge = AIForge(overrides={"provider": {"default": "anthropic", "anthropic_model": "claude-fable-5"}})
forge.set_secret("ANTHROPIC_API_KEY", os.environ["ANTHROPIC_API_KEY"])
```

Install the matching extra first (`pip install -e ".[anthropic]"` or `".[openai]"`).

## Configuration

Configuration is layered: **defaults → file → environment → runtime overrides**.

```python
from aiforge.config.settings import Config
config = Config.load(path="aiforge.config.json", overrides={"provider": {"temperature": 0.2}})
forge = AIForge(config=config)
```

Environment variables use the `AIFORGE_` prefix with `__` for nesting:

```bash
export AIFORGE_PROVIDER__DEFAULT=openai
export AIFORGE_SECURITY__ALLOW_SHELL=false
```

## The CLI

```bash
python -m aiforge.cli version
python -m aiforge.cli list tools
python -m aiforge.cli run-template research_assistant "Summarise AIForge"
python -m aiforge.cli serve            # REST API + dashboard on :8787
python -m aiforge.cli init ./project   # scaffold a project
```

## Next steps

- [Architecture](architecture.md) — how the pieces fit together
- [Agents](agents.md), [Workflows](workflows.md), [Tools](tools.md), [Memory](memory.md)
- [Examples](examples.md) — ten runnable projects
