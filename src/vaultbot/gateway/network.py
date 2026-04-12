"""Network utilities — interface detection, IP validation."""

from __future__ import annotations

import ipaddress
import socket


def get_local_ip() -> str:
    """Get the local LAN IP address."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("8.8.8.8", 80))
            return s.getsockname()[0]
    except OSError:
        return "127.0.0.1"


def is_private_ip(ip: str) -> bool:
    """Check if an IP address is private/internal."""
    try:
        return ipaddress.ip_address(ip).is_private
    except ValueError:
        return False


def is_loopback(ip: str) -> bool:
    """Check if an IP is loopback."""
    try:
        return ipaddress.ip_address(ip).is_loopback
    except ValueError:
        return False


def ip_in_cidr(ip: str, cidr: str) -> bool:
    """Check if an IP is within a CIDR range."""
    try:
        return ipaddress.ip_address(ip) in ipaddress.ip_network(cidr, strict=False)
    except ValueError:
        return False


def validate_origin(origin: str, allowed_origins: list[str]) -> bool:
    """Validate a browser origin against allowed list."""
    if not allowed_origins or "*" in allowed_origins:
        return True
    return origin in allowed_origins
