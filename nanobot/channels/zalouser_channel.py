"""Zalo Personal (Zalo User) channel for nanobot."""

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
class ZaloUserConfig:
    """Configuration for Zalo Personal channel."""
    enabled: bool = False
    access_token: str = ""  # Zalo user access token
    listen_host: str = "127.0.0.1"
    listen_port: int = 8091
    listen_path: str = "/zalouser"
    verify_token: str = ""  # Optional token for webhook verification
    allow_from: list[str] = field(default_factory=list)


class ZaloUserChannel(BaseChannel):
    """Zalo Personal channel using webhook-style inbound payloads."""

    name = "zalouser"

    def __init__(self, config: ZaloUserConfig, bus: MessageBus):
        super().__init__(config, bus)
        self.config: ZaloUserConfig = config
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
            "Zalo Personal webhook listening on http://%s:%s%s",
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
        if not self.config.access_token:
            logger.warning("Zalo access_token not configured")
            return

        payload = {
            "recipient": {"user_id": msg.chat_id},
            "message": {"text": msg.content},
        }

        try:
            data = json.dumps(payload).encode("utf-8")
            req = Request(
                "https://openapi.zalo.me/v2.0/oa/message",
                data=data,
                headers={
                    "Content-Type": "application/json",
                    "access_token": self.config.access_token,
                },
            )
            with urlopen(req, timeout=10) as resp:
                resp.read()
        except Exception as exc:
            logger.error("Failed to send Zalo message: %s", exc)

    async def _handle_webhook_event(self, payload: dict[str, Any]) -> None:
        try:
            sender = payload.get("sender", {})
            message = payload.get("message", {})

            sender_id = sender.get("id") or "unknown"
            chat_id = payload.get("thread_id") or sender_id
            content = message.get("text") or ""

            if not content:
                return

            await self._handle_message(sender_id=sender_id, chat_id=chat_id, content=content, metadata=payload)
        except Exception as exc:
            logger.error("Failed to process Zalo webhook: %s", exc)
