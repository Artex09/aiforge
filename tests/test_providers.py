from aiforge.core.types import LLMResponse, Message
from aiforge.providers.mock import MockProvider
from aiforge.providers.registry import ProviderRegistry


def test_mock_chat_reflects():
    p = MockProvider()
    resp = p.chat([Message.user("hello world")])
    assert "hello world" in resp.content
    assert resp.usage.total_tokens > 0


def test_mock_embeddings_deterministic():
    p = MockProvider()
    a = p.embed(["same text"]).vectors[0]
    b = p.embed(["same text"]).vectors[0]
    assert a == b
    assert len(a) == 256


def test_mock_tool_call_heuristic():
    p = MockProvider()
    tools = [{"function": {"name": "calculator", "parameters": {"properties": {}}}}]
    resp = p.chat([Message.user("please compute 2 + 2")], tools=tools)
    assert resp.has_tool_calls
    assert resp.tool_calls[0].name == "calculator"


def test_registry_fallback():
    reg = ProviderRegistry()

    class Broken(MockProvider):
        name = "broken"

        def chat(self, *a, **k):
            raise RuntimeError("down")

    reg.register(Broken(), default=True)
    reg.register(MockProvider())
    reg.set_fallbacks(["mock"])
    resp = reg.chat_with_fallback([Message.user("hi")])
    assert isinstance(resp, LLMResponse)
