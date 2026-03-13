"""
Session & Presence Management - Advanced session handling with typing indicators and usage tracking.

Features:
- Session activation modes (mention/always for groups)
- Typing indicators (send/receive)
- Usage tracking with cost calculation
- Session history and transcript logging
- Presence tracking
"""

import asyncio
import logging
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional
from datetime import datetime
from enum import Enum
import json

logger = logging.getLogger(__name__)


class ActivationMode(Enum):
    """Session activation modes for group conversations."""
    MENTION = "mention"      # Only respond when mentioned
    ALWAYS = "always"        # Respond to all messages


class PresenceStatus(Enum):
    """Presence status for multi-agent systems."""
    ACTIVE = "active"
    IDLE = "idle"
    AWAY = "away"
    OFFLINE = "offline"
    DO_NOT_DISTURB = "do_not_disturb"


@dataclass
class TypingIndicator:
    """Represents a typing indicator event."""
    sender: str
    channel: str
    session_id: str
    is_typing: bool
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class UsageMetrics:
    """Usage metrics for a response."""
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    cost: float = 0.0
    model: str = ""
    timestamp: datetime = field(default_factory=datetime.now)
    response_time_ms: float = 0.0


@dataclass
class SessionTranscript:
    """Session conversation history."""
    session_id: str
    created_at: datetime
    messages: List[Dict[str, Any]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


class TypingIndicatorManager:
    """Manages typing indicators across channels."""

    def __init__(self):
        """Initialize typing indicator manager."""
        self.active_typists: Dict[str, List[TypingIndicator]] = {}
        self.callbacks: List[Callable] = []
        logger.info("TypingIndicatorManager initialized")

    async def send_typing(self, session_id: str, channel: str, is_typing: bool) -> None:
        """Send typing indicator."""
        indicator = TypingIndicator(
            sender="agent",
            channel=channel,
            session_id=session_id,
            is_typing=is_typing
        )
        
        key = f"{channel}:{session_id}"
        if is_typing:
            if key not in self.active_typists:
                self.active_typists[key] = []
            self.active_typists[key].append(indicator)
            logger.debug(f"Typing indicator sent on {channel}")
        else:
            if key in self.active_typists:
                self.active_typists[key] = []
            logger.debug(f"Typing stopped on {channel}")
        
        # Trigger callbacks
        for callback in self.callbacks:
            await callback(indicator)

    async def on_typing(self, callback: Callable) -> None:
        """Register callback for typing events."""
        self.callbacks.append(callback)
        logger.debug("Typing indicator callback registered")

    async def get_typing_status(self, session_id: str, channel: str) -> bool:
        """Get current typing status for a session."""
        key = f"{channel}:{session_id}"
        return len(self.active_typists.get(key, [])) > 0


class UsageTracker:
    """Track token usage and costs."""

    def __init__(self):
        """Initialize usage tracker."""
        self.usage_history: List[UsageMetrics] = []
        self.model_costs = {
            "gpt-4": {"input": 0.03, "output": 0.06},
            "gpt-3.5-turbo": {"input": 0.0005, "output": 0.0015},
            "claude-3-opus": {"input": 0.015, "output": 0.075},
            "claude-3-sonnet": {"input": 0.003, "output": 0.015},
            "claude-3-haiku": {"input": 0.00025, "output": 0.00125},
        }
        logger.info("UsageTracker initialized")

    async def log_usage(
        self,
        input_tokens: int,
        output_tokens: int,
        model: str,
        response_time_ms: float = 0.0
    ) -> UsageMetrics:
        """Log token usage and calculate cost."""
        total_tokens = input_tokens + output_tokens
        
        # Calculate cost
        cost = 0.0
        if model in self.model_costs:
            costs = self.model_costs[model]
            cost = (input_tokens / 1000 * costs["input"]) + \
                   (output_tokens / 1000 * costs["output"])
        
        metrics = UsageMetrics(
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=total_tokens,
            cost=cost,
            model=model,
            response_time_ms=response_time_ms
        )
        
        self.usage_history.append(metrics)
        logger.info(f"Usage logged: {total_tokens} tokens, cost: ${cost:.4f}")
        return metrics

    async def get_usage_stats(self) -> Dict[str, Any]:
        """Get usage statistics."""
        if not self.usage_history:
            return {"total_tokens": 0, "total_cost": 0.0, "responses": 0}
        
        total_tokens = sum(m.total_tokens for m in self.usage_history)
        total_cost = sum(m.cost for m in self.usage_history)
        
        return {
            "total_tokens": total_tokens,
            "total_cost": total_cost,
            "responses": len(self.usage_history),
            "average_tokens_per_response": total_tokens / len(self.usage_history),
            "average_cost_per_response": total_cost / len(self.usage_history),
        }

    async def get_usage_footer(self, metrics: UsageMetrics) -> str:
        """Generate a usage footer for a response."""
        return f"_Tokens: {metrics.total_tokens} | Cost: ${metrics.cost:.4f} | {metrics.response_time_ms:.0f}ms_"


class SessionManager:
    """Manage session state, activation modes, and history."""

    def __init__(self):
        """Initialize session manager."""
        self.sessions: Dict[str, Dict[str, Any]] = {}
        self.transcripts: Dict[str, SessionTranscript] = {}
        self.activation_modes: Dict[str, ActivationMode] = {}
        logger.info("SessionManager initialized")

    async def create_session(
        self,
        session_id: str,
        channel: str,
        activation_mode: ActivationMode = ActivationMode.MENTION
    ) -> bool:
        """Create a new session."""
        self.sessions[session_id] = {
            "channel": channel,
            "created_at": datetime.now(),
            "last_activity": datetime.now(),
            "message_count": 0,
        }
        self.activation_modes[session_id] = activation_mode
        self.transcripts[session_id] = SessionTranscript(
            session_id=session_id,
            created_at=datetime.now()
        )
        logger.info(f"Session created: {session_id} with mode {activation_mode.value}")
        return True

    async def reset_session(self, session_id: str) -> bool:
        """Reset session (clear history)."""
        if session_id in self.sessions:
            self.transcripts[session_id] = SessionTranscript(
                session_id=session_id,
                created_at=datetime.now()
            )
            self.sessions[session_id]["last_activity"] = datetime.now()
            self.sessions[session_id]["message_count"] = 0
            logger.info(f"Session reset: {session_id}")
            return True
        return False

    async def add_message(
        self,
        session_id: str,
        role: str,
        content: str,
        metadata: Dict[str, Any] = None
    ) -> bool:
        """Add message to session transcript."""
        if session_id not in self.transcripts:
            return False
        
        message = {
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat(),
            **(metadata or {})
        }
        self.transcripts[session_id].messages.append(message)
        
        if session_id in self.sessions:
            self.sessions[session_id]["message_count"] += 1
            self.sessions[session_id]["last_activity"] = datetime.now()
        
        return True

    async def get_session_history(self, session_id: str) -> List[Dict[str, Any]]:
        """Get session conversation history."""
        if session_id not in self.transcripts:
            return []
        return self.transcripts[session_id].messages

    async def set_activation_mode(
        self,
        session_id: str,
        mode: ActivationMode
    ) -> bool:
        """Set session activation mode."""
        if session_id in self.sessions:
            self.activation_modes[session_id] = mode
            logger.info(f"Activation mode set to {mode.value} for {session_id}")
            return True
        return False

    async def should_respond(self, session_id: str, is_mentioned: bool) -> bool:
        """Check if agent should respond based on activation mode."""
        mode = self.activation_modes.get(session_id, ActivationMode.MENTION)
        
        if mode == ActivationMode.ALWAYS:
            return True
        elif mode == ActivationMode.MENTION:
            return is_mentioned
        
        return False

    async def get_session_status(self, session_id: str) -> Dict[str, Any]:
        """Get session status information."""
        if session_id not in self.sessions:
            return {}
        
        session = self.sessions[session_id]
        transcript = self.transcripts.get(session_id)
        
        return {
            "session_id": session_id,
            "channel": session["channel"],
            "created_at": session["created_at"].isoformat(),
            "last_activity": session["last_activity"].isoformat(),
            "message_count": session["message_count"],
            "activation_mode": self.activation_modes.get(session_id, ActivationMode.MENTION).value,
            "transcript_length": len(transcript.messages) if transcript else 0,
        }


class PresenceManager:
    """Manage agent presence across channels."""

    def __init__(self):
        """Initialize presence manager."""
        self.presence_status: Dict[str, PresenceStatus] = {}
        self.callbacks: List[Callable] = []
        logger.info("PresenceManager initialized")

    async def set_presence(
        self,
        agent_id: str,
        status: PresenceStatus
    ) -> None:
        """Set agent presence status."""
        old_status = self.presence_status.get(agent_id)
        self.presence_status[agent_id] = status
        
        if old_status != status:
            logger.info(f"Presence changed: {agent_id} is now {status.value}")
            
            # Trigger callbacks
            for callback in self.callbacks:
                await callback(agent_id, status)

    async def get_presence(self, agent_id: str) -> PresenceStatus:
        """Get agent presence status."""
        return self.presence_status.get(agent_id, PresenceStatus.OFFLINE)

    async def on_presence_change(self, callback: Callable) -> None:
        """Register callback for presence changes."""
        self.callbacks.append(callback)
        logger.debug("Presence change callback registered")

    async def get_all_presence(self) -> Dict[str, str]:
        """Get all agent presence statuses."""
        return {
            agent_id: status.value
            for agent_id, status in self.presence_status.items()
        }
