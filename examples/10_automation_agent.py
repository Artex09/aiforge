"""Automation Agent — chains tools and coordinates multiple agents.

Demonstrates the Coordinator routing a task and a multi-agent pipeline.
Run: python examples/10_automation_agent.py
"""
from aiforge.sdk import AIForge


def main() -> None:
    forge = AIForge()
    engine = forge.engine

    forge.agent("planner", role="planner", allow_all_tools=True)
    forge.agent("executor", template="automation_agent")

    # Route a task to the best agent, then run a 2-stage pipeline.
    chosen = engine.coordinator.route("plan and execute a daily report")
    print("Router chose:", chosen)

    result = engine.coordinator.pipeline(
        "Create a daily status report", ["planner", "executor"]
    )
    print("PIPELINE RESULT:", result.output)

    # Tool chaining: datetime -> word_count on the timestamp string.
    from aiforge.tools.chaining import ToolChain

    chain = ToolChain(engine.tools)
    chain.add("current_datetime", {"fmt": "iso"})
    chain.add("word_count", map_input=lambda out: {"text": str(out)})
    print("CHAIN:", chain.run().output)


if __name__ == "__main__":
    main()
