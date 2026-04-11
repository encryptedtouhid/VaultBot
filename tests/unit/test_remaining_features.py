"""Tests for canvas, polls, auto-reply, music gen, 2FA, and observability."""

from __future__ import annotations

import pytest

# ======================================================================
# Canvas (#29)
# ======================================================================

class TestCanvas:
    def test_create(self) -> None:
        from vaultbot.tools.canvas import CanvasManager, CanvasType
        mgr = CanvasManager()
        c = mgr.create("Test Doc", CanvasType.MARKDOWN)
        assert c.title == "Test Doc"
        assert mgr.count == 1

    def test_update_content(self) -> None:
        from vaultbot.tools.canvas import CanvasManager
        mgr = CanvasManager()
        c = mgr.create("Doc")
        rev = c.update("Hello world", "user1")
        assert c.content == "Hello world"
        assert rev.revision_id == 1

    def test_undo(self) -> None:
        from vaultbot.tools.canvas import CanvasManager
        mgr = CanvasManager()
        c = mgr.create("Doc")
        c.update("v1", "user")
        c.update("v2", "user")
        result = c.undo()
        assert result == "v1"

    def test_undo_single_revision(self) -> None:
        from vaultbot.tools.canvas import CanvasManager
        mgr = CanvasManager()
        c = mgr.create("Doc")
        c.update("v1", "user")
        assert c.undo() is None

    def test_delete(self) -> None:
        from vaultbot.tools.canvas import CanvasManager
        mgr = CanvasManager()
        c = mgr.create("Doc")
        assert mgr.delete(c.id) is True
        assert mgr.count == 0

    def test_list(self) -> None:
        from vaultbot.tools.canvas import CanvasManager
        mgr = CanvasManager()
        mgr.create("A")
        mgr.create("B")
        assert len(mgr.list_canvases()) == 2


# ======================================================================
# Polls (#30)
# ======================================================================

class TestPolls:
    def test_create_poll(self) -> None:
        from vaultbot.tools.polls import PollManager
        mgr = PollManager()
        poll = mgr.create("Best language?", ["Python", "Rust", "Go"])
        assert poll.question == "Best language?"
        assert len(poll.options) == 3

    def test_vote(self) -> None:
        from vaultbot.tools.polls import PollManager
        mgr = PollManager()
        poll = mgr.create("Pick one", ["A", "B", "C"])
        assert poll.vote("user1", [0]) is True
        assert poll.total_votes == 1

    def test_vote_closed_fails(self) -> None:
        from vaultbot.tools.polls import PollManager
        mgr = PollManager()
        poll = mgr.create("Q", ["A", "B"])
        poll.close()
        assert poll.vote("user1", [0]) is False

    def test_results(self) -> None:
        from vaultbot.tools.polls import PollManager
        mgr = PollManager()
        poll = mgr.create("Q", ["A", "B"])
        poll.vote("u1", [0])
        poll.vote("u2", [0])
        poll.vote("u3", [1])
        results = poll.get_results()
        assert results["A"] == 2
        assert results["B"] == 1

    def test_invalid_vote_option(self) -> None:
        from vaultbot.tools.polls import PollManager
        mgr = PollManager()
        poll = mgr.create("Q", ["A", "B"])
        assert poll.vote("u1", [99]) is False

    def test_list_active(self) -> None:
        from vaultbot.tools.polls import PollManager
        mgr = PollManager()
        p1 = mgr.create("Q1", ["A"])
        p2 = mgr.create("Q2", ["B"])
        p1.close()
        assert len(mgr.list_polls(active_only=True)) == 1


# ======================================================================
# Auto-reply (#31)
# ======================================================================

class TestAutoReply:
    def test_auto_reply_match(self) -> None:
        from vaultbot.core.auto_reply import AutoReplyEngine, AutoReplyRule
        engine = AutoReplyEngine()
        engine.add_reply_rule(AutoReplyRule(name="greeting", pattern=r"^(hi|hello)", response="Hello! How can I help?"))
        assert engine.check_auto_reply("hi there") == "Hello! How can I help?"

    def test_auto_reply_no_match(self) -> None:
        from vaultbot.core.auto_reply import AutoReplyEngine, AutoReplyRule
        engine = AutoReplyEngine()
        engine.add_reply_rule(AutoReplyRule(name="greeting", pattern=r"^hello", response="Hi!"))
        assert engine.check_auto_reply("what is python?") is None

    def test_routing_rule(self) -> None:
        from vaultbot.core.auto_reply import AutoReplyEngine, RoutingRule
        engine = AutoReplyEngine()
        engine.add_routing_rule(RoutingRule(name="code", pattern=r"(code|function|bug)", target_model="deepseek-coder"))
        assert engine.get_model_for_message("fix this bug") == "deepseek-coder"

    def test_routing_no_match(self) -> None:
        from vaultbot.core.auto_reply import AutoReplyEngine
        engine = AutoReplyEngine()
        assert engine.get_model_for_message("hello") is None

    def test_remove_rule(self) -> None:
        from vaultbot.core.auto_reply import AutoReplyEngine, AutoReplyRule
        engine = AutoReplyEngine()
        engine.add_reply_rule(AutoReplyRule(name="r1", pattern="hi", response="hello"))
        assert engine.remove_reply_rule("r1") is True
        assert len(engine.list_reply_rules()) == 0

    def test_disabled_rule_skipped(self) -> None:
        from vaultbot.core.auto_reply import AutoReplyEngine, AutoReplyRule
        engine = AutoReplyEngine()
        engine.add_reply_rule(AutoReplyRule(name="r1", pattern="hi", response="hello", enabled=False))
        assert engine.check_auto_reply("hi") is None


# ======================================================================
# Music generation (#32)
# ======================================================================

class TestMusicGeneration:
    def test_engine_init(self) -> None:
        from vaultbot.media.music_generation import MusicGenerationEngine
        engine = MusicGenerationEngine()
        assert engine.generation_count == 0

    @pytest.mark.asyncio
    async def test_generate_unknown_raises(self) -> None:
        from vaultbot.media.music_generation import MusicGenerationEngine
        engine = MusicGenerationEngine()
        with pytest.raises(ValueError, match="Unknown music provider"):
            await engine.generate("happy song")

    def test_genre_enum(self) -> None:
        from vaultbot.media.music_generation import MusicGenre
        assert MusicGenre.JAZZ.value == "jazz"


# ======================================================================
# 2FA (#36)
# ======================================================================

class TestTwoFactor:
    def test_generate_secret(self) -> None:
        from vaultbot.security.two_factor import generate_totp_secret
        secret = generate_totp_secret()
        assert len(secret) == 40  # 20 bytes hex

    def test_compute_and_verify(self) -> None:
        from vaultbot.security.two_factor import compute_totp, verify_totp
        secret = "0" * 40
        code = compute_totp(secret, timestamp=1000000000)
        assert verify_totp(secret, code, timestamp=1000000000) is True

    def test_wrong_code_fails(self) -> None:
        from vaultbot.security.two_factor import verify_totp
        assert verify_totp("0" * 40, "000000", timestamp=1000000000) is False

    def test_provisioning_uri(self) -> None:
        from vaultbot.security.two_factor import get_provisioning_uri
        uri = get_provisioning_uri("0" * 40, account="test")
        assert uri.startswith("otpauth://totp/")
        assert "test" in uri

    def test_manager_setup(self) -> None:
        from vaultbot.security.two_factor import TwoFactorManager
        mgr = TwoFactorManager()
        setup = mgr.setup("user1")
        assert setup.secret_hex
        assert mgr.is_enabled("user1") is True

    def test_manager_verify(self) -> None:
        from vaultbot.security.two_factor import TwoFactorManager, compute_totp
        mgr = TwoFactorManager()
        setup = mgr.setup("user1")
        code = compute_totp(setup.secret_hex)
        assert mgr.verify("user1", code) is True

    def test_manager_remove(self) -> None:
        from vaultbot.security.two_factor import TwoFactorManager
        mgr = TwoFactorManager()
        mgr.setup("user1")
        assert mgr.remove("user1") is True
        assert mgr.is_enabled("user1") is False

    def test_verify_unknown_user(self) -> None:
        from vaultbot.security.two_factor import TwoFactorManager
        mgr = TwoFactorManager()
        assert mgr.verify("unknown", "123456") is False


# ======================================================================
# Observability (#39)
# ======================================================================

class TestObservability:
    def test_counter(self) -> None:
        from vaultbot.observability import MetricsExporter
        exp = MetricsExporter()
        exp.increment("requests", 5)
        assert exp.get_counter("requests") == 5

    def test_gauge(self) -> None:
        from vaultbot.observability import MetricsExporter
        exp = MetricsExporter()
        exp.gauge("temperature", 0.7)
        assert exp.get_gauge("temperature") == 0.7

    def test_histogram(self) -> None:
        from vaultbot.observability import MetricsExporter
        exp = MetricsExporter()
        exp.histogram("latency", 100)
        exp.histogram("latency", 200)
        assert exp.get_histogram_avg("latency") == 150.0

    def test_span(self) -> None:
        from vaultbot.observability import MetricsExporter
        exp = MetricsExporter()
        span = exp.start_span("llm_call", provider="claude")
        assert span.duration_ms >= 0
        span.end()
        assert span.status == "ok"

    def test_export_metrics(self) -> None:
        from vaultbot.observability import MetricsExporter
        exp = MetricsExporter()
        exp.increment("req", 10)
        exp.gauge("mem", 512)
        data = exp.export_metrics()
        assert "counters" in data
        assert "gauges" in data

    def test_export_spans(self) -> None:
        from vaultbot.observability import MetricsExporter
        exp = MetricsExporter()
        s = exp.start_span("test")
        s.end()
        spans = exp.export_spans()
        assert len(spans) == 1
        assert spans[0]["name"] == "test"

    def test_labels(self) -> None:
        from vaultbot.observability import MetricsExporter
        exp = MetricsExporter()
        exp.increment("requests", 1, provider="claude")
        assert exp.get_counter("requests{provider=claude}") == 1

    def test_reset(self) -> None:
        from vaultbot.observability import MetricsExporter
        exp = MetricsExporter()
        exp.increment("x", 10)
        exp.reset()
        assert exp.get_counter("x") == 0
