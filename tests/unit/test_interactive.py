"""Unit tests for interactive responses."""

from __future__ import annotations

from vaultbot.core.interactive import (
    BlockType,
    Button,
    InteractivePayload,
    SelectOption,
)


class TestInteractivePayload:
    def test_add_text(self) -> None:
        payload = InteractivePayload()
        payload.add_text("Hello")
        assert payload.block_count == 1
        assert payload.blocks[0].block_type == BlockType.TEXT

    def test_add_buttons(self) -> None:
        payload = InteractivePayload()
        payload.add_buttons(
            [
                Button(label="Yes", action="confirm"),
                Button(label="No", action="cancel"),
            ]
        )
        assert payload.blocks[0].block_type == BlockType.BUTTON
        assert len(payload.blocks[0].buttons) == 2

    def test_add_select(self) -> None:
        payload = InteractivePayload()
        payload.add_select(
            [
                SelectOption(label="Option A", value="a"),
                SelectOption(label="Option B", value="b"),
            ]
        )
        assert payload.blocks[0].block_type == BlockType.SELECT

    def test_add_divider(self) -> None:
        payload = InteractivePayload()
        payload.add_divider()
        assert payload.blocks[0].block_type == BlockType.DIVIDER

    def test_chaining(self) -> None:
        payload = (
            InteractivePayload()
            .add_text("Choose:")
            .add_buttons([Button(label="OK", action="ok")])
            .add_divider()
        )
        assert payload.block_count == 3

    def test_to_dict(self) -> None:
        payload = InteractivePayload()
        payload.add_text("Hello")
        payload.add_buttons([Button(label="OK", action="ok")])
        result = payload.to_dict()
        assert len(result) == 2
        assert result[0]["type"] == "text"
        assert result[1]["type"] == "button"
