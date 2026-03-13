"""
Routing Module - Advanced message routing system for nanobot.

Implements multi-agent routing with failover, presence tracking, and group messaging.
"""

from .advanced_router import (
    AdvancedRouter,
    Agent,
    RoutedMessage,
    FailoverChain,
    AgentStatus,
    MessagePriority,
)

__all__ = [
    "AdvancedRouter",
    "Agent",
    "RoutedMessage",
    "FailoverChain",
    "AgentStatus",
    "MessagePriority",
]
