"""macOS menu bar app for nanobot."""

import asyncio
import json
from typing import Optional, Dict
from dataclasses import dataclass
from loguru import logger
from ..base import PlatformNode, PlatformConfig, NodeCapability, PlatformMessage
from datetime import datetime


@dataclass
class MenuBarAppConfig(PlatformConfig):
    """macOS-specific configuration."""
    menu_title: str = "nanobot"
    icon_path: str = ""
    show_dock_icon: bool = False
    start_at_login: bool = True
    hide_on_launch: bool = True


class MacOSMenuBar(PlatformNode):
    """macOS menu bar application node."""
    
    def __init__(self, config: Optional[MenuBarAppConfig] = None):
        if config is None:
            config = MenuBarAppConfig(
                platform_type="macos",
                node_id="macos-menubar",
                device_name="macOS Menu Bar"
            )
        
        super().__init__(config)
        self.config: MenuBarAppConfig = config
        self.menu_items: dict[str, callable] = {}
        self.is_visible = not config.hide_on_launch
        self.status = "idle"
        
    async def initialize(self) -> bool:
        """Initialize macOS app."""
        logger.info("[macOS] Initializing menu bar app")
        self.config.capabilities = [
            NodeCapability.NOTIFICATIONS.value,
            NodeCapability.SYSTEM_RUN.value,
            NodeCapability.TALK_MODE.value,
            NodeCapability.VOICE_WAKE.value,
            NodeCapability.CANVAS.value,
        ]
        return True
    
    async def get_capabilities(self) -> list[str]:
        """Get available capabilities."""
        return self.config.capabilities
    
    async def execute_command(self, command: str, args: dict) -> dict:
        """Execute macOS-specific command."""
        handlers = {
            "notify": self._handle_notify,
            "system_run": self._handle_system_run,
            "toggle_visibility": self._handle_toggle_visibility,
            "talk_mode": self._handle_talk_mode,
            "canvas_push": self._handle_canvas_push,
            "screen_capture": self._handle_screen_capture,
            "get_menu_items": self._handle_get_menu_items,
        }
        
        handler = handlers.get(command)
        if not handler:
            return {"error": f"Unknown command: {command}"}
        
        try:
            return await handler(args)
        except Exception as e:
            logger.error(f"[macOS] Command error: {e}")
            return {"error": str(e)}
    
    async def _handle_notify(self, args: dict) -> dict:
        """Send notification to user."""
        title = args.get("title", "nanobot")
        message = args.get("message", "")
        sound = args.get("sound", False)
        
        logger.info(f"[macOS] Notification: {title} - {message}")
        
        # In real implementation, would use NSUserNotification or UserNotifications
        await self.send_event("notification_shown", {
            "title": title,
            "message": message,
            "timestamp": datetime.now().isoformat()
        })
        
        return {"success": True, "id": f"notify_{datetime.now().timestamp()}"}
    
    async def _handle_system_run(self, args: dict) -> dict:
        """Run system command."""
        command = args.get("command", "")
        timeout = args.get("timeout", 10)
        
        logger.info(f"[macOS] Running command: {command}")
        
        try:
            # In real implementation, would use subprocess
            import subprocess
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=timeout
            )
            
            return {
                "success": True,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "returncode": result.returncode
            }
        except asyncio.TimeoutError:
            return {"success": False, "error": "Command timeout"}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _handle_toggle_visibility(self, args: dict) -> dict:
        """Toggle app visibility."""
        self.is_visible = not self.is_visible
        logger.info(f"[macOS] Visibility toggled: {self.is_visible}")
        
        await self.send_event("visibility_changed", {
            "visible": self.is_visible
        })
        
        return {"success": True, "visible": self.is_visible}
    
    async def _handle_talk_mode(self, args: dict) -> dict:
        """Enable Talk Mode overlay."""
        enabled = args.get("enabled", True)
        position = args.get("position", "bottom-right")
        
        logger.info(f"[macOS] Talk Mode: {enabled}")
        
        await self.send_event("talk_mode_changed", {
            "enabled": enabled,
            "position": position,
            "timestamp": datetime.now().isoformat()
        })
        
        return {
            "success": True,
            "enabled": enabled,
            "position": position,
            "features": ["voice_input", "voice_output", "realtime_transcription"]
        }
    
    async def _handle_canvas_push(self, args: dict) -> dict:
        """Push content to canvas."""
        content = args.get("content", {})
        layout = args.get("layout", "default")
        
        logger.info(f"[macOS] Canvas push: {layout}")
        
        await self.send_event("canvas_updated", {
            "layout": layout,
            "has_content": bool(content),
            "timestamp": datetime.now().isoformat()
        })
        
        return {
            "success": True,
            "canvas_id": f"canvas_{datetime.now().timestamp()}",
            "layout": layout
        }
    
    async def _handle_screen_capture(self, args: dict) -> dict:
        """Capture screen area."""
        area = args.get("area")  # Optional: specific area
        format_type = args.get("format", "png")
        
        logger.info(f"[macOS] Screen capture: {format_type}")
        
        # In real implementation, would use CGDisplayCreateImage or similar
        return {
            "success": True,
            "image_data": "base64_encoded_image_data",
            "format": format_type,
            "width": 1440,
            "height": 900,
            "timestamp": datetime.now().isoformat()
        }
    
    async def _handle_get_menu_items(self, args: dict) -> dict:
        """Get menu items."""
        return {
            "success": True,
            "menu_items": [
                {"id": "status", "label": "Status", "enabled": True},
                {"id": "settings", "label": "Settings", "enabled": True},
                {"id": "show_canvas", "label": "Show Canvas", "enabled": True},
                {"id": "voice_wake", "label": "Voice Wake", "enabled": True},
                {"id": "quit", "label": "Quit", "enabled": True},
            ]
        }
    
    async def update_status(self, status: str):
        """Update app status."""
        self.status = status
        await self.send_event("status_updated", {
            "status": status,
            "timestamp": datetime.now().isoformat()
        })
    
    async def add_menu_item(self, item_id: str, label: str, callback: callable):
        """Add menu item dynamically."""
        self.menu_items[item_id] = callback
        await self.send_event("menu_updated", {
            "item_id": item_id,
            "label": label,
            "action": "added"
        })
    
    async def add_to_login_items(self) -> bool:
        """Add app to login items (auto-start)."""
        logger.info("[macOS] Adding to login items")
        # In real implementation, would modify LaunchAgents
        return True
    
    async def remove_from_login_items(self) -> bool:
        """Remove app from login items."""
        logger.info("[macOS] Removing from login items")
        return True
    
    async def start(self):
        """Start menu bar app."""
        logger.info("[macOS] Starting menu bar app")
        await self.initialize()
        await self.connect()


# Convenience functions for setup

async def create_macos_menubar(
    gateway_url: str = "ws://127.0.0.1:18789",
    device_name: str = "macOS Menu Bar",
    auto_start_login: bool = True
) -> MacOSMenuBar:
    """Create and configure macOS menu bar app."""
    config = MenuBarAppConfig(
        platform_type="macos",
        node_id="macos-menubar",
        device_name=device_name,
        gateway_url=gateway_url,
        start_at_login=auto_start_login
    )
    
    app = MacOSMenuBar(config)
    return app
