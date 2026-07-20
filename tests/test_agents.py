from aiforge.agents.agent import AgentConfig, AgentStatus
from aiforge.core.errors import ToolPermissionError


def test_agent_basic_run(engine):
    agent = engine.create_agent(AgentConfig(name="a1", system_prompt="Be helpful."))
    result = agent.run("Hello there")
    assert result.success
    assert result.output
    assert agent.status == AgentStatus.DONE


def test_agent_uses_tool(engine):
    agent = engine.create_agent(AgentConfig(name="calc", allow_all_tools=True))
    result = agent.run("What is 6 * 7?")
    # The calculator tool should have run and produced 42 somewhere in the trace.
    joined = " ".join(m.content for m in result.messages)
    assert "42" in joined


def test_agent_tool_scoping(engine):
    # Agent only granted the calculator; using anything else is blocked.
    agent = engine.create_agent(AgentConfig(name="scoped", tools=["calculator"]))
    schemas = agent._tool_schemas()
    names = [s["function"]["name"] for s in schemas]
    assert names == ["calculator"]


def test_agent_from_template(engine):
    agent = engine.agent_from_template("research_assistant")
    assert agent.config.role == "researcher"
    assert "web_search" in agent.config.tools


def test_permission_enforced(engine):
    from aiforge.tools.context import ToolContext
    from aiforge.core.security import Permissions

    ctx = ToolContext(permissions=Permissions(grants=set()))  # no grants
    # read_file requires the 'fs' permission
    import pytest

    with pytest.raises(ToolPermissionError):
        engine.tools._check_permissions(engine.tools.get("read_file"), None, ctx)
