"""RPC method router with role-based scoping."""

from __future__ import annotations

from collections.abc import Callable, Coroutine
from dataclasses import dataclass, field
from typing import Any

from vaultbot.gateway.auth import Role
from vaultbot.utils.logging import get_logger

logger = get_logger(__name__)

RPCHandler = Callable[..., Coroutine[Any, Any, dict[str, object]]]


@dataclass(frozen=True, slots=True)
class RPCMethod:
    name: str
    handler: RPCHandler
    required_role: Role = Role.READ
    description: str = ""


@dataclass(frozen=True, slots=True)
class RPCRequest:
    method: str
    params: dict[str, object] = field(default_factory=dict)
    request_id: str = ""
    caller_role: Role = Role.READ


@dataclass(frozen=True, slots=True)
class RPCResponse:
    result: dict[str, object] = field(default_factory=dict)
    error: str = ""
    request_id: str = ""
    success: bool = True


class RPCRouter:
    """Routes RPC method calls with role-based access control."""

    def __init__(self) -> None:
        self._methods: dict[str, RPCMethod] = {}

    def register(self, method: RPCMethod) -> None:
        self._methods[method.name] = method
        logger.info("rpc_method_registered", method=method.name)

    def unregister(self, name: str) -> bool:
        if name in self._methods:
            del self._methods[name]
            return True
        return False

    async def dispatch(self, request: RPCRequest) -> RPCResponse:
        method = self._methods.get(request.method)
        if not method:
            return RPCResponse(
                error=f"Unknown method: {request.method}",
                request_id=request.request_id,
                success=False,
            )

        # Role check
        role_order = [Role.READ, Role.WRITE, Role.APPROVALS, Role.PAIRING, Role.ADMIN]
        caller_idx = (
            role_order.index(request.caller_role) if request.caller_role in role_order else 0
        )
        required_idx = (
            role_order.index(method.required_role) if method.required_role in role_order else 0
        )
        if caller_idx < required_idx:
            return RPCResponse(
                error=f"Insufficient role for {request.method}",
                request_id=request.request_id,
                success=False,
            )

        try:
            result = await method.handler(**request.params)
            return RPCResponse(
                result=result,
                request_id=request.request_id,
            )
        except Exception as exc:
            return RPCResponse(
                error=str(exc),
                request_id=request.request_id,
                success=False,
            )

    def list_methods(self, role: Role | None = None) -> list[RPCMethod]:
        if role is None:
            return list(self._methods.values())
        role_order = [Role.READ, Role.WRITE, Role.APPROVALS, Role.PAIRING, Role.ADMIN]
        caller_idx = role_order.index(role) if role in role_order else 0
        return [
            m
            for m in self._methods.values()
            if role_order.index(m.required_role) <= caller_idx
            if m.required_role in role_order
        ]

    @property
    def method_count(self) -> int:
        return len(self._methods)
