import pytest

from aiforge.core.errors import ToolValidationError
from aiforge.tools.base import FunctionTool, ToolResult, tool
from aiforge.tools.builtin import register_builtins
from aiforge.tools.registry import ToolRegistry


def test_decorator_derives_schema():
    @tool(description="add")
    def add(a: int, b: int = 1) -> int:
        return a + b

    assert add.parameters["properties"]["a"]["type"] == "integer"
    assert "b" not in add.parameters.get("required", [])
    assert add.run(a=2, b=3).output == 5


def test_registry_execute_and_validate():
    reg = ToolRegistry()
    register_builtins(reg)
    result = reg.execute("calculator", {"expression": "3 * 7"})
    assert result.ok and result.output == 21


def test_validation_missing_required():
    reg = ToolRegistry()

    @tool()
    def needs(x: int) -> int:
        return x

    reg.register(needs)
    with pytest.raises(ToolValidationError):
        needs.validate({})


def test_calculator_rejects_unsafe():
    from aiforge.tools.builtin.calculator import calculator

    result = calculator.run(expression="__import__('os').system('echo hi')")
    assert not result.ok


def test_tool_chaining():
    from aiforge.tools.chaining import ToolChain

    reg = ToolRegistry()
    register_builtins(reg)
    chain = ToolChain(reg)
    chain.add("current_datetime", {"fmt": "iso"})
    chain.add("word_count", map_input=lambda out: {"text": str(out)})
    result = chain.run()
    assert result.ok
    assert result.output["words"] >= 1
