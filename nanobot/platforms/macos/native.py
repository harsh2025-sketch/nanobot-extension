"""macOS menu bar app implementation details."""

# This module contains PyObjC-based implementations for:
# - NSStatusBar menu bar integration
# - NSUserNotification/UserNotifications framework
# - AppleScript support
# - System event handling

# Install: pip install pyobjc-framework-Cocoa pyobjc-framework-CoreServices

try:
    from AppKit import NSApp, NSApplication, NSStatusBar, NSStatusItem
    from Cocoa import *
    PYOBJC_AVAILABLE = True
except ImportError:
    PYOBJC_AVAILABLE = False
    NSApp = None
    NSApplication = None
    NSStatusBar = None


def is_macos_available() -> bool:
    """Check if PyObjC is available for macOS."""
    return PYOBJC_AVAILABLE
