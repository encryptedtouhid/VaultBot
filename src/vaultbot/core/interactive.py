"""Interactive response formatting with buttons, selects, and text blocks."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class BlockType(str, Enum):
    TEXT = "text"
    BUTTON = "button"
    SELECT = "select"
    DIVIDER = "divider"


@dataclass(frozen=True, slots=True)
class Button:
    label: str
    action: str
    style: str = "default"
    url: str = ""


@dataclass(frozen=True, slots=True)
class SelectOption:
    label: str
    value: str
    description: str = ""


@dataclass(frozen=True, slots=True)
class InteractiveBlock:
    block_type: BlockType
    text: str = ""
    buttons: list[Button] = field(default_factory=list)
    options: list[SelectOption] = field(default_factory=list)
    placeholder: str = ""


class InteractivePayload:
    """Builds interactive response payloads."""

    def __init__(self) -> None:
        self._blocks: list[InteractiveBlock] = []

    def add_text(self, text: str) -> InteractivePayload:
        self._blocks.append(InteractiveBlock(block_type=BlockType.TEXT, text=text))
        return self

    def add_buttons(self, buttons: list[Button]) -> InteractivePayload:
        self._blocks.append(InteractiveBlock(block_type=BlockType.BUTTON, buttons=buttons))
        return self

    def add_select(
        self, options: list[SelectOption], placeholder: str = "Choose..."
    ) -> InteractivePayload:
        self._blocks.append(
            InteractiveBlock(block_type=BlockType.SELECT, options=options, placeholder=placeholder)
        )
        return self

    def add_divider(self) -> InteractivePayload:
        self._blocks.append(InteractiveBlock(block_type=BlockType.DIVIDER))
        return self

    @property
    def blocks(self) -> list[InteractiveBlock]:
        return list(self._blocks)

    @property
    def block_count(self) -> int:
        return len(self._blocks)

    def to_dict(self) -> list[dict[str, object]]:
        result: list[dict[str, object]] = []
        for block in self._blocks:
            entry: dict[str, object] = {"type": block.block_type.value}
            if block.text:
                entry["text"] = block.text
            if block.buttons:
                entry["buttons"] = [{"label": b.label, "action": b.action} for b in block.buttons]
            if block.options:
                entry["options"] = [{"label": o.label, "value": o.value} for o in block.options]
            result.append(entry)
        return result
