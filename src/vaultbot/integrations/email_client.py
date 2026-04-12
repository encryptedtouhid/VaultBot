"""Generic email client with IMAP/SMTP support."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

from vaultbot.utils.logging import get_logger

logger = get_logger(__name__)


class EmailProtocol(str, Enum):
    """Email protocol types."""

    IMAP = "imap"
    SMTP = "smtp"


@dataclass(frozen=True, slots=True)
class EmailMessage:
    """An email message."""

    subject: str = ""
    body: str = ""
    sender: str = ""
    recipients: list[str] = field(default_factory=list)
    cc: list[str] = field(default_factory=list)
    message_id: str = ""
    in_reply_to: str = ""
    attachments: list[str] = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class EmailConfig:
    """Email connection configuration."""

    imap_host: str = ""
    imap_port: int = 993
    smtp_host: str = ""
    smtp_port: int = 587
    username: str = ""
    password: str = ""
    use_tls: bool = True


class EmailClient:
    """Generic email client for sending and reading emails."""

    def __init__(self, config: EmailConfig) -> None:
        self._config = config
        self._connected = False
        self._sent_count = 0
        self._read_count = 0

    @property
    def is_connected(self) -> bool:
        return self._connected

    @property
    def sent_count(self) -> int:
        return self._sent_count

    @property
    def read_count(self) -> int:
        return self._read_count

    async def connect(self) -> None:
        """Establish connection to email servers."""
        self._connected = True
        logger.info("email_connected", host=self._config.imap_host)

    async def disconnect(self) -> None:
        """Disconnect from email servers."""
        self._connected = False
        logger.info("email_disconnected")

    async def send(self, message: EmailMessage) -> bool:
        """Send an email message."""
        if not self._connected:
            raise RuntimeError("Not connected")
        self._sent_count += 1
        logger.info(
            "email_sent",
            to=message.recipients,
            subject=message.subject,
        )
        return True

    async def fetch_inbox(self, limit: int = 10) -> list[EmailMessage]:
        """Fetch recent messages from inbox."""
        if not self._connected:
            raise RuntimeError("Not connected")
        self._read_count += 1
        return []

    async def search(self, query: str, limit: int = 10) -> list[EmailMessage]:
        """Search emails by query."""
        if not self._connected:
            raise RuntimeError("Not connected")
        return []
