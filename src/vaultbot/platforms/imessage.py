"""iMessage platform adapter for macOS.

Uses the `pypush` library or AppleScript bridge to send/receive iMessages
on macOS. This adapter only works on macOS with a signed-in Apple ID.

Note: iMessage has no official bot API. This adapter uses local macOS
integrations and is intended for personal use only.
"""

from __future__ import annotations

import asyncio
import json
import subprocess
from collections.abc import AsyncIterator
from datetime import UTC, datetime
from pathlib import Path

from vaultbot.core.message import InboundMessage, OutboundMessage
from vaultbot.utils.logging import get_logger

logger = get_logger(__name__)

# AppleScript to send an iMessage
_SEND_SCRIPT = """\
tell application "Messages"
    set targetService to 1st account whose service type = iMessage
    set targetBuddy to participant "{recipient}" of targetService
    send "{message}" to targetBuddy
end tell
"""

# AppleScript to check for new messages from the Messages database
_CHECK_MESSAGES_SCRIPT = """\
use framework "Foundation"
use scripting additions

set dbPath to (POSIX path of (path to home folder)) & \
    "Library/Messages/chat.db"
set shellCmd to "sqlite3 '" & dbPath & \
    "' \"SELECT m.rowid, m.text, h.id, m.date/1000000000 + 978307200 " & \
    "FROM message m JOIN handle h ON m.handle_id = h.rowid " & \
    "WHERE m.is_from_me = 0 AND m.rowid > {last_rowid} " & \
    "ORDER BY m.rowid ASC LIMIT 50\" -json 2>/dev/null"
return do shell script shellCmd
"""


class IMessageAdapter:
    """iMessage adapter for macOS using AppleScript bridge.

    Requirements:
        - macOS only
        - Messages.app signed in with Apple ID
        - Full Disk Access permission for the terminal/process
    """

    def __init__(self) -> None:
        import sys

        if sys.platform != "darwin":
            raise RuntimeError("iMessage adapter is only available on macOS.")
        self._message_queue: asyncio.Queue[InboundMessage] = asyncio.Queue()
        self._polling = False
        self._poll_task: asyncio.Task[None] | None = None
        self._last_rowid = 0
        self._load_last_rowid()

    @property
    def platform_name(self) -> str:
        return "imessage"

    def _load_last_rowid(self) -> None:
        """Load the last processed message rowid to avoid replaying old messages."""
        state_file = Path.home() / ".vaultbot" / "imessage_state.json"
        if state_file.exists():
            try:
                data = json.loads(state_file.read_text())
                self._last_rowid = data.get("last_rowid", 0)
            except (json.JSONDecodeError, OSError):
                pass

    def _save_last_rowid(self) -> None:
        """Persist the last processed rowid."""
        state_dir = Path.home() / ".vaultbot"
        state_dir.mkdir(parents=True, exist_ok=True)
        state_file = state_dir / "imessage_state.json"
        state_file.write_text(json.dumps({"last_rowid": self._last_rowid}))

    async def connect(self) -> None:
        """Start polling for new iMessages."""
        self._polling = True
        self._poll_task = asyncio.create_task(self._poll_messages())
        logger.info("imessage_connected")

    async def disconnect(self) -> None:
        """Stop polling."""
        self._polling = False
        if self._poll_task and not self._poll_task.done():
            self._poll_task.cancel()
            try:
                await self._poll_task
            except asyncio.CancelledError:
                pass
        self._save_last_rowid()
        logger.info("imessage_disconnected")

    async def _poll_messages(self) -> None:
        """Poll the Messages database for new messages."""
        while self._polling:
            try:
                script = _CHECK_MESSAGES_SCRIPT.replace("{last_rowid}", str(self._last_rowid))
                result = await asyncio.to_thread(
                    subprocess.run,
                    ["osascript", "-e", script],
                    capture_output=True,
                    text=True,
                    timeout=10,
                )

                if result.returncode == 0 and result.stdout.strip():
                    try:
                        rows = json.loads(result.stdout)
                    except json.JSONDecodeError:
                        rows = []

                    for row in rows:
                        if not isinstance(row, dict):
                            continue
                        rowid = row.get("rowid", 0)
                        text = row.get("text", "")
                        sender = row.get("id", "unknown")
                        timestamp_unix = row.get("date/1000000000 + 978307200", 0)

                        if not text:
                            continue

                        try:
                            timestamp = datetime.fromtimestamp(float(timestamp_unix), tz=UTC)
                        except (ValueError, OSError):
                            timestamp = datetime.now(UTC)

                        inbound = InboundMessage(
                            id=str(rowid),
                            platform="imessage",
                            sender_id=sender,
                            chat_id=sender,
                            text=text,
                            timestamp=timestamp,
                        )
                        await self._message_queue.put(inbound)
                        self._last_rowid = max(self._last_rowid, rowid)

            except Exception as e:
                logger.error("imessage_poll_error", error=str(e))

            await asyncio.sleep(2.0)

    async def listen(self) -> AsyncIterator[InboundMessage]:
        """Yield messages as they arrive from iMessage."""
        while True:
            message = await self._message_queue.get()
            yield message

    async def send(self, message: OutboundMessage) -> None:
        """Send an iMessage via AppleScript."""
        # Sanitize inputs to prevent AppleScript injection
        recipient = message.chat_id.replace('"', '\\"').replace("\\", "\\\\")
        text = message.text.replace('"', '\\"').replace("\\", "\\\\")

        script = _SEND_SCRIPT.format(recipient=recipient, message=text)

        try:
            result = await asyncio.to_thread(
                subprocess.run,
                ["osascript", "-e", script],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode != 0:
                logger.error(
                    "imessage_send_error",
                    stderr=result.stderr[:200],
                    recipient=message.chat_id,
                )
        except subprocess.TimeoutExpired:
            logger.error("imessage_send_timeout", recipient=message.chat_id)

    async def healthcheck(self) -> bool:
        """Check if Messages.app is available."""
        try:
            result = await asyncio.to_thread(
                subprocess.run,
                ["osascript", "-e", 'tell application "Messages" to get name'],
                capture_output=True,
                text=True,
                timeout=5,
            )
            return result.returncode == 0
        except Exception:
            return False
