"""Google Chat channel (webhook-based) for nanobot."""

from __future__ import annotations

import asyncio
import json
import logging
from dataclasses import dataclass, field
from typing import Any
from urllib.request import Request, urlopen

from nanobot.bus.events import OutboundMessage
from nanobot.bus.queue import MessageBus
from nanobot.channels.base import BaseChannel
from nanobot.channels.webhook_server import WebhookServer

logger = logging.getLogger(__name__)


@dataclass
class GoogleChatConfig:
    """Google Chat channel configuration."""
    enabled: bool = False
    webhook_url: str = ""  # Incoming webhook URL for outbound messages
    listen_host: str = "127.0.0.1"
    listen_port: int = 8090
    listen_path: str = "/googlechat"
    verify_token: str = ""  # Optional shared token for inbound verification
    allow_from: list[str] = field(default_factory=list)


class GoogleChatChannel(BaseChannel):
    """Google Chat channel using a simple webhook receiver."""

    name = "googlechat"

    def __init__(self, config: GoogleChatConfig, bus: MessageBus):
        super().__init__(config, bus)
        self.config: GoogleChatConfig = config
        self._server: WebhookServer | None = None
        self._loop: asyncio.AbstractEventLoop | None = None

    async def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._loop = asyncio.get_running_loop()

        self._server = WebhookServer(
            host=self.config.listen_host,
            port=self.config.listen_port,
            path=self.config.listen_path,
            on_event=self._handle_webhook_event,
            verify_token=self.config.verify_token or None,
            loop=self._loop,
        )
        self._server.start()
        logger.info(
            "Google Chat webhook listening on http://%s:%s%s",
            self.config.listen_host,
            self.config.listen_port,
            self.config.listen_path,
        )

        while self._running:
            await asyncio.sleep(1)

    async def stop(self) -> None:
        self._running = False
        if self._server:
            self._server.stop()
            self._server = None

    async def send(self, msg: OutboundMessage) -> None:
        if not self.config.webhook_url:
            logger.warning("Google Chat webhook_url not configured")
            return

        payload = {
            "text": msg.content,
        }

        try:
            data = json.dumps(payload).encode("utf-8")
            req = Request(self.config.webhook_url, data=data, headers={"Content-Type": "application/json"})
            with urlopen(req, timeout=10) as resp:
                resp.read()
        except Exception as exc:
            logger.error("Failed to send Google Chat message: %s", exc)

    async def _handle_webhook_event(self, payload: dict[str, Any]) -> None:
        try:
            message = payload.get("message") or {}
            sender = payload.get("user") or payload.get("sender") or {}
            space = payload.get("space") or {}

            sender_id = sender.get("name") or sender.get("displayName") or "unknown"
            chat_id = space.get("name") or "space:unknown"
            content = message.get("text") or ""

            if not content:
                return

            await self._handle_message(sender_id=sender_id, chat_id=chat_id, content=content, metadata=payload)
        except Exception as exc:
            logger.error("Failed to process Google Chat webhook: %s", exc)
