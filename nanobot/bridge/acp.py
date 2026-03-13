"""ACP bridge for nanobot (stdio NDJSON)."""

from __future__ import annotations

import asyncio
import json
import sys
import uuid
from dataclasses import dataclass
from typing import Any

from nanobot.agent.loop import AgentLoop
from nanobot.session.manager import SessionManager


@dataclass
class ACPConfig:
    """Configuration for ACP bridge."""
    default_session: str = "acp:default"


class ACPBridge:
    """Minimal ACP-compatible bridge over stdio (NDJSON)."""

    def __init__(self, agent: AgentLoop, sessions: SessionManager, config: ACPConfig | None = None):
        self.agent = agent
        self.sessions = sessions
        self.config = config or ACPConfig()
        self._session_map: dict[str, str] = {}
        self._running = True

    async def run(self) -> None:
        while self._running:
            line = await asyncio.to_thread(sys.stdin.readline)
            if not line:
                break
            line = line.strip()
            if not line:
                continue
            try:
                payload = json.loads(line)
            except json.JSONDecodeError:
                self._emit({"type": "error", "message": "Invalid JSON"})
                continue

            await self._handle_message(payload)

        await self.agent.close_mcp()

    async def _handle_message(self, payload: dict[str, Any]) -> None:
        msg_type = payload.get("type") or payload.get("method")

        if msg_type == "initialize":
            self._emit({
                "type": "initialize",
                "capabilities": {
                    "listSessions": True,
                    "newSession": True,
                    "loadSession": True,
                    "prompt": True,
                    "cancel": True,
                },
            })
            return

        if msg_type == "newSession":
            session_id = payload.get("sessionId") or f"acp:{uuid.uuid4().hex}"
            self._session_map[session_id] = session_id
            self._emit({"type": "newSession", "sessionId": session_id})
            return

        if msg_type == "loadSession":
            session_id = payload.get("sessionId") or self.config.default_session
            self._session_map.setdefault(session_id, session_id)
            self._emit({"type": "loadSession", "sessionId": session_id})
            return

        if msg_type == "listSessions":
            sessions = self.sessions.list_sessions()
            self._emit({"type": "listSessions", "sessions": sessions})
            return

        if msg_type == "cancel":
            self._emit({"type": "done", "status": "cancel"})
            return

        if msg_type == "prompt":
            session_id = payload.get("sessionId") or self.config.default_session
            session_key = self._session_map.get(session_id, session_id)
            prompt = payload.get("prompt") or payload.get("message") or ""
            if not prompt:
                self._emit({"type": "error", "message": "Missing prompt"})
                return

            response = await self.agent.process_direct(
                prompt,
                session_key=session_key,
                channel="acp",
                chat_id=session_id,
            )
            self._emit({
                "type": "message",
                "sessionId": session_id,
                "role": "assistant",
                "content": response,
            })
            self._emit({"type": "done", "sessionId": session_id, "status": "stop"})
            return

        self._emit({"type": "error", "message": f"Unknown message type: {msg_type}"})

    @staticmethod
    def _emit(payload: dict[str, Any]) -> None:
        sys.stdout.write(json.dumps(payload) + "\n")
        sys.stdout.flush()
