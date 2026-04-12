"""Phone integration for call handling and SMS."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from vaultbot.utils.logging import get_logger

logger = get_logger(__name__)


class CallState(str, Enum):
    """Phone call state."""

    IDLE = "idle"
    RINGING = "ringing"
    ACTIVE = "active"
    ON_HOLD = "on_hold"
    ENDED = "ended"


@dataclass(frozen=True, slots=True)
class SMSMessage:
    """An SMS message."""

    to: str
    body: str
    from_number: str = ""
    message_id: str = ""


@dataclass(frozen=True, slots=True)
class PhoneCall:
    """A phone call."""

    call_id: str
    to: str
    from_number: str = ""
    state: CallState = CallState.IDLE
    duration_seconds: float = 0.0


class PhoneManager:
    """Phone integration manager for calls and SMS."""

    def __init__(self) -> None:
        self._active_calls: dict[str, PhoneCall] = {}
        self._sms_count = 0
        self._call_count = 0

    @property
    def active_call_count(self) -> int:
        return len(self._active_calls)

    @property
    def sms_count(self) -> int:
        return self._sms_count

    async def send_sms(self, message: SMSMessage) -> bool:
        """Send an SMS message."""
        self._sms_count += 1
        logger.info("sms_sent", to=message.to)
        return True

    async def initiate_call(self, to: str, from_number: str = "") -> PhoneCall:
        """Initiate an outbound phone call."""
        call_id = f"call_{self._call_count}"
        call = PhoneCall(
            call_id=call_id,
            to=to,
            from_number=from_number,
            state=CallState.RINGING,
        )
        self._active_calls[call_id] = call
        self._call_count += 1
        logger.info("call_initiated", to=to, call_id=call_id)
        return call

    async def end_call(self, call_id: str) -> bool:
        """End an active call."""
        if call_id in self._active_calls:
            del self._active_calls[call_id]
            logger.info("call_ended", call_id=call_id)
            return True
        return False

    def get_active_calls(self) -> list[PhoneCall]:
        return list(self._active_calls.values())
