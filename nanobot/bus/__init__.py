"""Message bus module for decoupled channel-agent communication."""

from nanobot.bus.events import InboundMessage, OutboundMessage
from nanobot.bus.queue import MessageBus

# Optional platform support - gracefully skip if not available
try:
    from nanobot.bus.platform_gateway import PlatformGateway
    from nanobot.bus.platform_integration import setup_platform_integration
    __all__ = ["MessageBus", "InboundMessage", "OutboundMessage", "PlatformGateway", "setup_platform_integration"]
except ImportError:
    # Platform support not available
    __all__ = ["MessageBus", "InboundMessage", "OutboundMessage"]
