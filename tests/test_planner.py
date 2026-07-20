"""The Studio Chat planner must assemble a *specialised* crew per intent —
not a fixed researcher/writer pair for every brief."""
from aiforge.agents.planner import plan_crew
from aiforge.core.engine import Engine


def _agents(plan):
    return [n["data"]["name"] for n in plan["graph"]["nodes"] if n["type"] == "agent"]


def _tasks(plan):
    return [n["data"]["label"] for n in plan["graph"]["nodes"] if n["type"] == "task"]


def test_software_brief_builds_engineering_crew():
    plan = plan_crew("Build a backend with Rust language")
    assert plan["domain"] == "software"
    agents = _agents(plan)
    assert "Lead Software Architect" in agents
    assert "Rust Backend Developer" in agents
    assert any("QA" in a for a in agents)
    # It must NOT fall back to the generic research pair.
    assert "Report Writer" not in agents


def test_software_tasks_are_actionable_not_reports():
    tasks = " ".join(_tasks(plan_crew("Build a REST API in Go with Postgres"))).lower()
    assert "implement" in tasks
    assert "test" in tasks
    assert "write report" not in tasks


def test_fullstack_with_deploy_adds_frontend_and_devops():
    agents = _agents(plan_crew(
        "Create a full-stack website in TypeScript with React and deploy with Docker"
    ))
    assert "Frontend Developer" in agents
    assert "DevOps Engineer" in agents


def test_data_brief_builds_data_crew():
    agents = _agents(plan_crew("analyse this sales dataset and find trends"))
    assert agents == ["Data Engineer", "Data Analyst", "Insights Specialist"]


def test_content_brief_builds_writing_crew():
    plan = plan_crew("write a launch blog post about our new app")
    assert plan["domain"] == "content"
    assert "Content Writer" in _agents(plan)


def test_research_is_the_default_and_still_action_oriented():
    plan = plan_crew("research the best vector databases for RAG")
    assert plan["domain"] == "research"
    assert "Research Specialist" in _agents(plan)


def test_build_does_not_trigger_frontend_via_substring():
    # "build" contains "ui" — must not spawn a Frontend Developer.
    agents = _agents(plan_crew("Build a backend with Rust language"))
    assert "Frontend Developer" not in agents


def test_planned_graph_runs_end_to_end_in_order():
    plan = plan_crew("Build a backend with Rust language")
    result = Engine().run_graph(plan["graph"])
    assert result["success"] is True
    outs = result["task_outputs"]
    assert len(outs) == 3  # architecture -> implement -> test
