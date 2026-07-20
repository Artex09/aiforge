"""Tests for the 'make it real' additions: retries, structured validation,
cost accounting, RRF fusion, and graph->code."""
import pytest

from aiforge.core.errors import ProviderError, ValidationError
from aiforge.core.pricing import estimate_cost, price_for
from aiforge.core.retry import with_retries
from aiforge.core.schema import validate_against_schema
from aiforge.providers.mock import MockProvider
from aiforge.core.types import Message


def test_retry_succeeds_after_failures():
    calls = {"n": 0}

    def flaky():
        calls["n"] += 1
        if calls["n"] < 3:
            raise ConnectionError("transient")
        return "ok"

    result = with_retries(flaky, attempts=5, base_delay=0, sleep=lambda _s: None)
    assert result == "ok" and calls["n"] == 3


def test_retry_exhausts_and_raises():
    with pytest.raises(ValueError):
        with_retries(lambda: (_ for _ in ()).throw(ValueError("x")), attempts=2, base_delay=0, sleep=lambda _s: None)


def test_schema_validation_catches_problems():
    schema = {"type": "object", "required": ["name"], "properties": {"name": {"type": "string"}, "age": {"type": "integer"}}}
    assert validate_against_schema({"name": "a", "age": 3}, schema) == []
    assert validate_against_schema({"age": "no"}, schema)  # missing name + wrong type


def test_structured_output_validates_and_returns(monkeypatch):
    schema = {"type": "object", "required": ["title"], "properties": {"title": {"type": "string"}}}
    p = MockProvider()
    out = p.structured([Message.user("give me a title")], schema)
    assert "title" in out


def test_structured_output_validates_and_retries():
    # A bare provider (base structured: parse -> validate -> retry) that always
    # returns non-JSON must fail after exhausting attempts.
    from aiforge.core.types import LLMResponse
    from aiforge.providers.base import LLMProvider, ProviderCapabilities

    class Bare(LLMProvider):
        name = "bare"
        capabilities = ProviderCapabilities()

        def chat(self, messages, **kwargs):
            return LLMResponse(content="not json at all", model="x")

    with pytest.raises(ProviderError):
        Bare().structured(
            [Message.user("x")],
            {"type": "object", "required": ["a"], "properties": {"a": {"type": "string"}}},
            max_attempts=2,
        )


def test_pricing():
    assert price_for("aiforge-mock-1") == (0.0, 0.0)
    assert estimate_cost("gpt-4o-mini", 1_000_000, 0) == pytest.approx(0.15)
    assert estimate_cost("claude-fable-5", 0, 1_000_000) == pytest.approx(15.0)


def test_rrf_recall_prefers_relevant(tmp_path):
    from aiforge.memory.manager import MemoryManager
    from aiforge.storage.local import LocalStorage

    mgr = MemoryManager(backend=LocalStorage(str(tmp_path)))
    mgr.remember_semantic("AIForge is an open framework for multi-agent systems")
    for i in range(5):
        mgr.remember(f"unrelated chatter about the weather number {i}")
    hits = mgr.recall("what is aiforge?", top_k=3)
    assert any("AIForge" in h.content for h in hits)


def test_graph_to_code(engine):
    graph = {
        "nodes": [
            {"id": "a1", "type": "agent", "data": {"name": "Writer", "role": "assistant", "tools": ["calculator"]}},
            {"id": "t1", "type": "task", "data": {"label": "Do", "description": "Write something", "agent": "Writer"}},
        ],
        "edges": [],
    }
    code = engine.graph_to_code(graph)
    assert "forge.agent(\"Writer\"" in code
    assert "forge.crew([" in code
    assert "crew.kickoff()" in code
    compile(code, "<generated>", "exec")  # must be syntactically valid Python
