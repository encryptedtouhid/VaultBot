"""Tests for the calculator example plugin."""

import sys
from pathlib import Path

import pytest

# Add examples to path for importing
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "examples" / "plugins" / "calculator"))

from plugin import CalculatorPlugin  # noqa: E402

from vaultbot.plugins.base import PluginContext, PluginResultStatus  # noqa: E402


@pytest.fixture
def calc() -> CalculatorPlugin:
    return CalculatorPlugin()


@pytest.fixture
def ctx() -> PluginContext:
    return PluginContext(
        user_input="", chat_id="test", user_id="test", platform="test"
    )


def _ctx_with_input(expr: str) -> PluginContext:
    return PluginContext(
        user_input=expr, chat_id="test", user_id="test", platform="test"
    )


@pytest.mark.asyncio
async def test_basic_addition(calc: CalculatorPlugin) -> None:
    result = await calc.handle(_ctx_with_input("2 + 3"))
    assert result.status == PluginResultStatus.SUCCESS
    assert result.data["result"] == 5


@pytest.mark.asyncio
async def test_multiplication(calc: CalculatorPlugin) -> None:
    result = await calc.handle(_ctx_with_input("7 * 8"))
    assert result.status == PluginResultStatus.SUCCESS
    assert result.data["result"] == 56


@pytest.mark.asyncio
async def test_division(calc: CalculatorPlugin) -> None:
    result = await calc.handle(_ctx_with_input("10 / 4"))
    assert result.status == PluginResultStatus.SUCCESS
    assert result.data["result"] == 2.5


@pytest.mark.asyncio
async def test_complex_expression(calc: CalculatorPlugin) -> None:
    result = await calc.handle(_ctx_with_input("(2 + 3) * 4 - 1"))
    assert result.status == PluginResultStatus.SUCCESS
    assert result.data["result"] == 19


@pytest.mark.asyncio
async def test_negative_numbers(calc: CalculatorPlugin) -> None:
    result = await calc.handle(_ctx_with_input("-5 + 3"))
    assert result.status == PluginResultStatus.SUCCESS
    assert result.data["result"] == -2


@pytest.mark.asyncio
async def test_power(calc: CalculatorPlugin) -> None:
    result = await calc.handle(_ctx_with_input("2 ** 10"))
    assert result.status == PluginResultStatus.SUCCESS
    assert result.data["result"] == 1024


@pytest.mark.asyncio
async def test_division_by_zero(calc: CalculatorPlugin) -> None:
    result = await calc.handle(_ctx_with_input("1 / 0"))
    assert result.status == PluginResultStatus.ERROR


@pytest.mark.asyncio
async def test_invalid_expression(calc: CalculatorPlugin) -> None:
    result = await calc.handle(_ctx_with_input("hello world"))
    assert result.status == PluginResultStatus.ERROR


@pytest.mark.asyncio
async def test_blocks_dangerous_power(calc: CalculatorPlugin) -> None:
    result = await calc.handle(_ctx_with_input("10 ** 100000"))
    assert result.status == PluginResultStatus.ERROR
    assert "too large" in result.error.lower()


@pytest.mark.asyncio
async def test_manifest(calc: CalculatorPlugin) -> None:
    m = calc.manifest()
    assert m.name == "calculator"
    assert m.network_domains == []
