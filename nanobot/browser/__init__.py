"""
Browser Module - Comprehensive browser automation for nanobot.

Provides full Chrome/Chromium control with screenshot capabilities,
persistent sessions, and complete DOM interaction.
"""

from .automation import (
    BrowserAutomation,
    BrowserSession,
    BrowserConfig,
    BrowserAction,
    Screenshot,
    BrowserTargetType,
    NavigationWaitCondition,
)
from .profile_manager import (
    BrowserProfileManager,
    BrowserProfile,
    BrowserCookie,
    LocalStorageEntry,
)

__all__ = [
    "BrowserAutomation",
    "BrowserSession",
    "BrowserConfig",
    "BrowserAction",
    "Screenshot",
    "BrowserTargetType",
    "NavigationWaitCondition",
    "BrowserProfileManager",
    "BrowserProfile",
    "BrowserCookie",
    "LocalStorageEntry",
]
