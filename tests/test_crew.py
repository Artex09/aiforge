from aiforge.agents.agent import AgentConfig
from aiforge.agents.crew import Crew, Task


def _team(engine):
    engine.create_agent(AgentConfig(name="researcher", role="researcher", allow_all_tools=True))
    engine.create_agent(AgentConfig(name="writer", role="assistant", allow_all_tools=True))


def test_crew_sequential(engine):
    _team(engine)
    crew = Crew(
        engine,
        tasks=[
            Task("Research the topic", agent="researcher"),
            Task("Write a report", agent="writer"),
        ],
        name="test-crew",
    )
    result = crew.kickoff({"input": "AI agents"})
    assert result.success
    assert len(result.task_outputs) == 2
    assert result.output is not None


def test_crew_via_sdk(forge):
    forge.agent("researcher", role="researcher", allow_all_tools=True)
    forge.agent("writer", allow_all_tools=True)
    crew = forge.crew(
        [
            forge.task("Research X", agent="researcher"),
            forge.task("Summarize the research", agent="writer"),
        ]
    )
    result = crew.kickoff()
    assert result.success
    assert result.task_outputs[0]["agent"] == "researcher"


def test_run_graph(engine):
    graph = {
        "process": "sequential",
        "nodes": [
            {"id": "ag1", "type": "agent", "data": {"name": "R", "role": "researcher", "tools": []}},
            {"id": "t1", "type": "task", "data": {"label": "Research", "description": "Research the market", "agent": "R"}},
            {"id": "t2", "type": "task", "data": {"label": "Report", "description": "Write the report", "agent": "R"}},
        ],
        "edges": [{"source": "t1", "target": "t2"}],
    }
    out = engine.run_graph(graph)
    assert out["success"]
    assert [t["task"] for t in out["task_outputs"]] == ["Research", "Report"]


def test_run_graph_orders_by_edges(engine):
    # Tasks provided out of order; edges dictate the sequence.
    graph = {
        "nodes": [
            {"id": "a", "type": "agent", "data": {"name": "A", "tools": []}},
            {"id": "t2", "type": "task", "data": {"label": "second", "description": "b", "agent": "A"}},
            {"id": "t1", "type": "task", "data": {"label": "first", "description": "a", "agent": "A"}},
        ],
        "edges": [{"source": "t1", "target": "t2"}],
    }
    out = engine.run_graph(graph)
    assert [t["task"] for t in out["task_outputs"]] == ["first", "second"]
