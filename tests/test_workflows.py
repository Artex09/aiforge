from aiforge.agents.agent import AgentConfig
from aiforge.workflows.builder import WorkflowBuilder
from aiforge.workflows.serialization import workflow_from_json, workflow_to_json
from aiforge.workflows.steps import (
    AgentStep,
    ConditionalStep,
    FallbackStep,
    RetryStep,
    SetVariableStep,
    ToolStep,
)


def test_sequential_workflow(engine):
    wf = (
        WorkflowBuilder("seq")
        .tool("calculator", {"expression": "2 + 2"}, output_var="sum")
        .tool("word_count", {"text": "$sum"}, output_var="wc")
        .build()
    )
    result = engine.run_workflow(wf, {"input": "go"})
    assert result.success
    assert result.steps == 2


def test_conditional_branch(engine):
    wf = (
        WorkflowBuilder("cond")
        .set({"n": 10})
        .condition(
            "n > 5",
            ToolStep("calculator", {"expression": "100"}, name="big"),
            ToolStep("calculator", {"expression": "1"}, name="small"),
            name="branch",
        )
        .build()
    )
    result = engine.run_workflow(wf)
    assert result.success


def test_parallel_and_retry(engine):
    engine.create_agent(AgentConfig(name="w", allow_all_tools=True))
    wf = (
        WorkflowBuilder("par")
        .parallel(
            [
                ToolStep("calculator", {"expression": "1+1"}, name="p1"),
                ToolStep("word_count", {"text": "hello world"}, name="p2"),
            ]
        )
        .retry(ToolStep("calculator", {"expression": "9*9"}, name="r"), max_retries=1)
        .build()
    )
    result = engine.run_workflow(wf)
    assert result.success


def test_fallback(engine):
    wf = (
        WorkflowBuilder("fb")
        .fallback(
            [
                ToolStep("does_not_exist", name="bad"),
                ToolStep("calculator", {"expression": "5"}, name="good"),
            ]
        )
        .build()
    )
    result = engine.run_workflow(wf)
    assert result.success
    assert result.output == 5


def test_serialization_roundtrip():
    wf = (
        WorkflowBuilder("ser")
        .set({"x": 1})
        .tool("calculator", {"expression": "$x"}, output_var="y")
        .build()
    )
    text = workflow_to_json(wf)
    wf2 = workflow_from_json(text)
    assert wf2.name == "ser"
    assert [s.type for s in wf2.steps] == ["set_variable", "tool"]


def test_validation_rejects_empty():
    import pytest
    from aiforge.core.errors import WorkflowError
    from aiforge.workflows.base import Workflow

    with pytest.raises(WorkflowError):
        Workflow("empty").ensure_valid()
