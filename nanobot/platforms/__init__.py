"""
Platform support for nanobot.

Provides native app integration for:
- macOS (menu bar app)
- iOS (node with Voice Wake, Talk Mode, Canvas)
- Android (node with Talk Mode, Canvas, Camera)
"""

from .base import PlatformNode, PlatformConfig
from .manager import PlatformManager

__all__ = ["PlatformNode", "PlatformConfig", "PlatformManager"]
