"""Multi-mode gateway authentication."""

from __future__ import annotations

import hashlib
import hmac
import time
from dataclasses import dataclass, field
from enum import Enum

from vaultbot.utils.logging import get_logger

logger = get_logger(__name__)


class AuthMode(str, Enum):
    NONE = "none"
    TOKEN = "token"
    PASSWORD = "password"
    DEVICE_PAIR = "device_pair"


class Role(str, Enum):
    ADMIN = "admin"
    READ = "read"
    WRITE = "write"
    APPROVALS = "approvals"
    PAIRING = "pairing"


@dataclass(frozen=True, slots=True)
class AuthResult:
    authenticated: bool
    mode: AuthMode = AuthMode.NONE
    role: Role = Role.READ
    device_id: str = ""
    error: str = ""


@dataclass(slots=True)
class DeviceToken:
    device_id: str
    token_hash: str
    role: Role = Role.WRITE
    created_at: float = field(default_factory=time.time)
    last_used: float = 0.0
    approved: bool = False


class GatewayAuth:
    """Multi-mode authentication for gateway connections."""

    def __init__(
        self,
        token: str = "",
        password: str = "",
    ) -> None:
        self._token = token
        self._password_hash = hashlib.sha256(password.encode()).hexdigest() if password else ""
        self._device_tokens: dict[str, DeviceToken] = {}
        self._rate_limits: dict[str, list[float]] = {}

    def authenticate(self, mode: AuthMode, credential: str, device_id: str = "") -> AuthResult:
        if mode == AuthMode.NONE:
            return AuthResult(authenticated=True, mode=mode)

        if mode == AuthMode.TOKEN:
            if not self._token:
                return AuthResult(authenticated=True, mode=mode, role=Role.ADMIN)
            if hmac.compare_digest(credential, self._token):
                return AuthResult(authenticated=True, mode=mode, role=Role.ADMIN)
            return AuthResult(authenticated=False, error="invalid token")

        if mode == AuthMode.PASSWORD:
            cred_hash = hashlib.sha256(credential.encode()).hexdigest()
            if hmac.compare_digest(cred_hash, self._password_hash):
                return AuthResult(authenticated=True, mode=mode, role=Role.WRITE)
            return AuthResult(authenticated=False, error="invalid password")

        if mode == AuthMode.DEVICE_PAIR:
            device = self._device_tokens.get(device_id)
            if not device or not device.approved:
                return AuthResult(authenticated=False, error="device not approved")
            token_hash = hashlib.sha256(credential.encode()).hexdigest()
            if hmac.compare_digest(token_hash, device.token_hash):
                device.last_used = time.time()
                return AuthResult(
                    authenticated=True, mode=mode, role=device.role, device_id=device_id
                )
            return AuthResult(authenticated=False, error="invalid device token")

        return AuthResult(authenticated=False, error="unknown auth mode")

    def register_device(self, device_id: str, token: str, role: Role = Role.WRITE) -> DeviceToken:
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        device = DeviceToken(device_id=device_id, token_hash=token_hash, role=role)
        self._device_tokens[device_id] = device
        return device

    def approve_device(self, device_id: str) -> bool:
        device = self._device_tokens.get(device_id)
        if not device:
            return False
        device.approved = True
        return True

    def revoke_device(self, device_id: str) -> bool:
        if device_id in self._device_tokens:
            del self._device_tokens[device_id]
            return True
        return False

    def check_rate_limit(self, client_id: str, max_per_minute: int = 60) -> bool:
        now = time.time()
        window = self._rate_limits.setdefault(client_id, [])
        window[:] = [t for t in window if now - t < 60]
        if len(window) >= max_per_minute:
            return False
        window.append(now)
        return True

    def check_method_access(self, role: Role, method: str) -> bool:
        """Check if a role has access to a gateway method."""
        admin_methods = {"config.write", "device.approve", "device.revoke", "system.shutdown"}
        write_methods = {"chat.send", "session.create", "agent.run"}
        if role == Role.ADMIN:
            return True
        if role == Role.WRITE:
            return method not in admin_methods
        if role == Role.READ:
            return method not in admin_methods and method not in write_methods
        return False
