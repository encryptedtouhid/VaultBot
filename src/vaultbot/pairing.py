"""Device pairing for mobile companion apps.

Provides secure pairing via random codes with expiry, device
management (list, revoke), and paired device registry.
"""

from __future__ import annotations

import secrets
import time
from dataclasses import dataclass, field
from datetime import UTC, datetime

from vaultbot.utils.logging import get_logger

logger = get_logger(__name__)

_CODE_LENGTH = 6
_CODE_EXPIRY_SECONDS = 300  # 5 minutes


@dataclass
class PairedDevice:
    """A paired device."""

    id: str
    name: str
    device_type: str  # "ios", "android", "desktop", "web"
    paired_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    last_seen: datetime = field(default_factory=lambda: datetime.now(UTC))
    active: bool = True


@dataclass
class PairingCode:
    """A temporary pairing code."""

    code: str
    created_at: float = field(default_factory=time.monotonic)
    expiry_seconds: float = _CODE_EXPIRY_SECONDS

    @property
    def is_expired(self) -> bool:
        return (time.monotonic() - self.created_at) > self.expiry_seconds


class DevicePairingManager:
    """Manages device pairing and paired device registry."""

    def __init__(self) -> None:
        self._devices: dict[str, PairedDevice] = {}
        self._pending_codes: dict[str, PairingCode] = {}
        self._device_counter: int = 0

    def generate_pairing_code(self) -> str:
        """Generate a random pairing code."""
        code = "".join(str(secrets.randbelow(10)) for _ in range(_CODE_LENGTH))
        self._pending_codes[code] = PairingCode(code=code)
        logger.info("pairing_code_generated")
        return code

    def complete_pairing(
        self, code: str, device_name: str, device_type: str = "mobile"
    ) -> PairedDevice | None:
        """Complete pairing with a valid code.

        Returns the paired device if successful, None if code invalid/expired.
        """
        pending = self._pending_codes.pop(code, None)
        if pending is None or pending.is_expired:
            logger.warning("pairing_failed", reason="invalid or expired code")
            return None

        self._device_counter += 1
        device_id = f"device_{self._device_counter}"
        device = PairedDevice(
            id=device_id,
            name=device_name,
            device_type=device_type,
        )
        self._devices[device_id] = device
        logger.info("device_paired", device_id=device_id, name=device_name)
        return device

    def revoke_device(self, device_id: str) -> bool:
        """Revoke a paired device."""
        device = self._devices.get(device_id)
        if device:
            device.active = False
            logger.info("device_revoked", device_id=device_id)
            return True
        return False

    def remove_device(self, device_id: str) -> bool:
        """Remove a device entirely."""
        if device_id in self._devices:
            del self._devices[device_id]
            return True
        return False

    def list_devices(self, *, active_only: bool = False) -> list[PairedDevice]:
        """List paired devices."""
        devices = list(self._devices.values())
        if active_only:
            devices = [d for d in devices if d.active]
        return devices

    def get_device(self, device_id: str) -> PairedDevice | None:
        return self._devices.get(device_id)

    def update_last_seen(self, device_id: str) -> None:
        """Update the last_seen timestamp for a device."""
        device = self._devices.get(device_id)
        if device:
            device.last_seen = datetime.now(UTC)

    def cleanup_expired_codes(self) -> int:
        """Remove expired pairing codes."""
        expired = [c for c, pc in self._pending_codes.items() if pc.is_expired]
        for c in expired:
            del self._pending_codes[c]
        return len(expired)

    @property
    def device_count(self) -> int:
        return len(self._devices)

    @property
    def active_device_count(self) -> int:
        return sum(1 for d in self._devices.values() if d.active)

    @property
    def pending_codes_count(self) -> int:
        return len(self._pending_codes)
