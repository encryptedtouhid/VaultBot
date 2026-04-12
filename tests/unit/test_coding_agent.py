"""Unit tests for coding agent."""

from __future__ import annotations

import pytest

from vaultbot.agents.coding_agent import (
    CodeExecutionRequest,
    CodeLanguage,
    CodingAgent,
)


class TestCodingAgent:
    def test_sandbox_dir_exists(self) -> None:
        agent = CodingAgent()
        assert agent.sandbox_dir.exists()

    def test_review_clean_code(self) -> None:
        agent = CodingAgent()
        result = agent.review_code("x = 1\nprint(x)")
        assert result.score > 0.5
        assert len(result.issues) == 0

    def test_review_empty_code(self) -> None:
        agent = CodingAgent()
        result = agent.review_code("")
        assert "empty" in result.issues[0].lower()

    def test_review_long_lines(self) -> None:
        agent = CodingAgent()
        result = agent.review_code("x = " + "a" * 200)
        assert any("120" in issue for issue in result.issues)

    @pytest.mark.asyncio
    async def test_execute_python(self) -> None:
        agent = CodingAgent()
        req = CodeExecutionRequest(code="print('hello')", language=CodeLanguage.PYTHON)
        result = await agent.execute(req)
        assert result.success is True
        assert "hello" in result.stdout
        assert agent.execution_count == 1

    @pytest.mark.asyncio
    async def test_execute_python_error(self) -> None:
        agent = CodingAgent()
        req = CodeExecutionRequest(code="raise ValueError('oops')", language=CodeLanguage.PYTHON)
        result = await agent.execute(req)
        assert result.success is False
        assert result.exit_code != 0

    @pytest.mark.asyncio
    async def test_execute_timeout(self) -> None:
        agent = CodingAgent()
        req = CodeExecutionRequest(
            code="import time; time.sleep(10)",
            language=CodeLanguage.PYTHON,
            timeout_seconds=1,
        )
        result = await agent.execute(req)
        assert result.success is False
        assert "timed out" in result.stderr.lower()
