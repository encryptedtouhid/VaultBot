"""Unit tests for advanced session management."""

from __future__ import annotations

from vaultbot.core.send_policy import (
    ModelOverride,
    ModelOverrideManager,
    SendPolicy,
    SendPolicyConfig,
)
from vaultbot.core.session_events import SessionEvent, SessionEventEmitter, SessionEventType


class TestSessionEventEmitter:
    def test_emit_and_listen(self) -> None:
        emitter = SessionEventEmitter()
        received: list[str] = []
        emitter.on(SessionEventType.CREATED, lambda e: received.append(e.session_id))
        emitter.emit(SessionEvent(event_type=SessionEventType.CREATED, session_id="s1"))
        assert received == ["s1"]

    def test_off(self) -> None:
        emitter = SessionEventEmitter()
        cb = lambda e: None  # noqa: E731
        emitter.on(SessionEventType.CREATED, cb)
        assert emitter.off(SessionEventType.CREATED, cb) is True

    def test_get_log(self) -> None:
        emitter = SessionEventEmitter()
        emitter.emit(SessionEvent(event_type=SessionEventType.CREATED, session_id="s1"))
        emitter.emit(SessionEvent(event_type=SessionEventType.DELETED, session_id="s1"))
        assert len(emitter.get_log("s1")) == 2
        assert emitter.total_events == 2

    def test_get_log_filtered(self) -> None:
        emitter = SessionEventEmitter()
        emitter.emit(SessionEvent(event_type=SessionEventType.CREATED, session_id="s1"))
        emitter.emit(SessionEvent(event_type=SessionEventType.CREATED, session_id="s2"))
        assert len(emitter.get_log("s1")) == 1


class TestSendPolicy:
    def test_rate_within_limit(self) -> None:
        policy = SendPolicy(SendPolicyConfig(max_messages_per_minute=5))
        for _ in range(5):
            assert policy.check_rate() is True
            policy.record_send()
        assert policy.check_rate() is False

    def test_check_size(self) -> None:
        policy = SendPolicy(SendPolicyConfig(max_response_bytes=10))
        assert policy.check_size("short") is True
        assert policy.check_size("a" * 100) is False

    def test_check_tokens(self) -> None:
        policy = SendPolicy(SendPolicyConfig(max_response_tokens=100))
        assert policy.check_tokens(50) is True
        assert policy.check_tokens(200) is False


class TestModelOverrideManager:
    def test_set_and_get(self) -> None:
        mgr = ModelOverrideManager()
        mgr.set_override("s1", ModelOverride(model="gpt-4o", temperature=0.5))
        override = mgr.get_override("s1")
        assert override is not None
        assert override.model == "gpt-4o"

    def test_has_override(self) -> None:
        mgr = ModelOverrideManager()
        assert mgr.has_override("s1") is False
        mgr.set_override("s1", ModelOverride(model="gpt-4o"))
        assert mgr.has_override("s1") is True

    def test_clear_override(self) -> None:
        mgr = ModelOverrideManager()
        mgr.set_override("s1", ModelOverride(model="gpt-4o"))
        assert mgr.clear_override("s1") is True
        assert mgr.has_override("s1") is False

    def test_empty_override_not_set(self) -> None:
        override = ModelOverride()
        assert override.is_set is False
