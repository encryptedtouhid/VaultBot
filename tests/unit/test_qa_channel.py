"""Unit tests for QA channel and lab."""

from __future__ import annotations

from vaultbot.qa.channel import QAChannel
from vaultbot.qa.lab import QALab, ScenarioStatus


class TestQAChannel:
    def test_create_conversation(self) -> None:
        ch = QAChannel()
        conv = ch.create_conversation()
        assert conv.conversation_id.startswith("qa_")
        assert ch.conversation_count == 1

    def test_send_message(self) -> None:
        ch = QAChannel()
        conv = ch.create_conversation()
        msg = ch.send_message(conv.conversation_id, "hello")
        assert msg is not None
        assert msg.role == "user"

    def test_add_response(self) -> None:
        ch = QAChannel()
        conv = ch.create_conversation()
        ch.send_message(conv.conversation_id, "hi")
        resp = ch.add_response(conv.conversation_id, "hello!")
        assert resp is not None
        assert resp.role == "assistant"

    def test_get_history(self) -> None:
        ch = QAChannel()
        conv = ch.create_conversation()
        ch.send_message(conv.conversation_id, "hi")
        ch.add_response(conv.conversation_id, "hello")
        history = ch.get_history(conv.conversation_id)
        assert len(history) == 2

    def test_clear_conversation(self) -> None:
        ch = QAChannel()
        conv = ch.create_conversation()
        ch.send_message(conv.conversation_id, "hi")
        assert ch.clear_conversation(conv.conversation_id) is True
        assert len(ch.get_history(conv.conversation_id)) == 0

    def test_missing_conversation(self) -> None:
        ch = QAChannel()
        assert ch.send_message("nope", "hi") is None
        assert ch.get_history("nope") == []


class TestQALab:
    def test_add_scenario(self) -> None:
        lab = QALab()
        lab.add_scenario("greeting", ["hello"], ["hi|hello"])
        assert lab.scenario_count == 1

    def test_run_scenario_pass(self) -> None:
        lab = QALab()
        s = lab.add_scenario("greeting", ["hello"], ["hello"])
        result = lab.run_scenario(s, ["hello world"])
        assert result is True
        assert s.status == ScenarioStatus.PASSED

    def test_run_scenario_fail(self) -> None:
        lab = QALab()
        s = lab.add_scenario("test", ["x"], ["expected_pattern"])
        result = lab.run_scenario(s, ["wrong"])
        assert result is False
        assert s.status == ScenarioStatus.FAILED

    def test_get_results(self) -> None:
        lab = QALab()
        s1 = lab.add_scenario("a", ["x"], ["x"])
        s2 = lab.add_scenario("b", ["y"], ["z"])
        lab.run_scenario(s1, ["x"])
        lab.run_scenario(s2, ["y"])
        results = lab.get_results()
        assert results.total == 2
        assert results.passed == 1
        assert results.failed == 1
