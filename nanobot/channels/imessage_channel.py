"""Legacy iMessage channel (macOS Messages app integration)."""

from __future__ import annotations

import asyncio
import json
import logging
import platform
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

from nanobot.bus.events import OutboundMessage
from nanobot.bus.queue import MessageBus
from nanobot.channels.base import BaseChannel

logger = logging.getLogger(__name__)


@dataclass
class IMessageConfig:
    """Configuration for legacy iMessage channel."""
    enabled: bool = False
    inbox_path: str = ""  # Optional JSONL inbox file to simulate inbound messages
    poll_interval_seconds: int = 5
    send_via_osascript: bool = True
    allow_from: list[str] = field(default_factory=list)


class IMessageChannel(BaseChannel):
    """Legacy iMessage channel using local macOS Messages automation."""

    name = "imessage"

    def __init__(self, config: IMessageConfig, bus: MessageBus):
        super().__init__(config, bus)
        self.config: IMessageConfig = config
        self._poll_task: asyncio.Task | None = None
        self._inbox_offset = 0

    async def start(self) -> None:
        if self._running:
            return
        self._running = True
        if self.config.inbox_path:
            self._poll_task = asyncio.create_task(self._poll_inbox())
        while self._running:
            await asyncio.sleep(1)

    async def stop(self) -> None:
        self._running = False
        if self._poll_task:
            self._poll_task.cancel()
            try:
                await self._poll_task
            except asyncio.CancelledError:
                pass
            self._poll_task = None

    async def send(self, msg: OutboundMessage) -> None:
        if not self.config.send_via_osascript:
            logger.warning("iMessage send disabled (send_via_osascript=false)")
            return

        if platform.system().lower() != "darwin":
            logger.warning("iMessage send only supported on macOS")
            return

        escaped_content = msg.content.replace('"', '\\"')
        script = (
            "tell application \"Messages\"\n"
            "set targetService to 1st service whose service type = iMessage\n"
            f"set targetBuddy to buddy \"{msg.chat_id}\" of targetService\n"
            f"send \"{escaped_content}\" to targetBuddy\n"
            "end tell\n"
        )

        try:
            subprocess.run(["osascript", "-e", script], check=True, capture_output=True)
        except subprocess.CalledProcessError as exc:
            logger.error("Failed to send iMessage: %s", exc)

    async def _poll_inbox(self) -> None:
        inbox_path = Path(self.config.inbox_path).expanduser()
        if not inbox_path.exists():
            logger.warning("iMessage inbox_path not found: %s", inbox_path)
            return

        while self._running:
            try:
                with inbox_path.open("r", encoding="utf-8") as handle:
                    lines = handle.readlines()

                new_lines = lines[self._inbox_offset :]
                self._inbox_offset = len(lines)

                for line in new_lines:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        payload = json.loads(line)
                    except json.JSONDecodeError:
                        continue

                    sender_id = payload.get("sender_id") or payload.get("from") or "unknown"
                    chat_id = payload.get("chat_id") or sender_id
                    content = payload.get("content") or payload.get("text") or ""
                    if content:
                        await self._handle_message(sender_id, chat_id, content, metadata=payload)
            except Exception as exc:
                logger.error("Failed polling iMessage inbox: %s", exc)

            await asyncio.sleep(self.config.poll_interval_seconds)
