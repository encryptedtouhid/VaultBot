"""Tests for conversation context management."""

from zenbot.core.context import ContextManager, ConversationContext
from zenbot.core.message import ChatMessage


def test_sliding_window_trims_old_messages() -> None:
    ctx = ConversationContext(chat_id="test", max_history=3)
    for i in range(5):
        ctx.add_message(ChatMessage(role="user", content=f"msg{i}"))
    assert ctx.message_count == 3
    messages = ctx.get_messages()
    assert messages[0].content == "msg2"


def test_system_prompt_prepended() -> None:
    ctx = ConversationContext(chat_id="test", system_prompt="Be helpful.")
    ctx.add_message(ChatMessage(role="user", content="Hello"))
    messages = ctx.get_messages()
    assert messages[0].role == "system"
    assert messages[0].content == "Be helpful."
    assert messages[1].role == "user"


def test_clear_resets_history() -> None:
    ctx = ConversationContext(chat_id="test")
    ctx.add_message(ChatMessage(role="user", content="Hello"))
    assert ctx.message_count == 1
    ctx.clear()
    assert ctx.message_count == 0


def test_context_manager_per_chat_isolation() -> None:
    mgr = ContextManager(system_prompt="Test")
    ctx1 = mgr.get("chat1")
    ctx2 = mgr.get("chat2")
    ctx1.add_message(ChatMessage(role="user", content="Hello"))
    assert ctx1.message_count == 1
    assert ctx2.message_count == 0


def test_context_manager_clear_specific_chat() -> None:
    mgr = ContextManager()
    ctx = mgr.get("chat1")
    ctx.add_message(ChatMessage(role="user", content="Hello"))
    mgr.clear("chat1")
    assert mgr.get("chat1").message_count == 0
