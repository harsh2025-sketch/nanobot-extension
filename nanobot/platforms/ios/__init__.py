"""iOS node support for nanobot."""

import asyncio
from typing import Optional
from dataclasses import dataclass
from loguru import logger
from ..base import PlatformNode, PlatformConfig, NodeCapability, PlatformMessage
from datetime import datetime


@dataclass
class iOSNodeConfig(PlatformConfig):
    """iOS-specific configuration."""
    device_id: str = ""
    is_simulator: bool = False
    screen_width: int = 1170  # iPhone 15 Pro
    screen_height: int = 2532
    supports_face_recognition: bool = True
    supports_lidar: bool = False


class iOSNode(PlatformNode):
    """iOS node for nanobot."""
    
    def __init__(self, config: Optional[iOSNodeConfig] = None):
        if config is None:
            config = iOSNodeConfig(
                platform_type="ios",
                node_id="ios-node-1",
                device_name="iPhone"
            )
        
        super().__init__(config)
        self.config: iOSNodeConfig = config
        self.camera_active = False
        self.screen_recording = False
        self.voice_wake_enabled = False
        self.talk_mode_enabled = False
        
    async def initialize(self) -> bool:
        """Initialize iOS node."""
        logger.info("[iOS] Initializing iOS node")
        
        self.config.capabilities = [
            NodeCapability.CAMERA.value,
            NodeCapability.VOICE_WAKE.value,
            NodeCapability.TALK_MODE.value,
            NodeCapability.CANVAS.value,
            NodeCapability.NOTIFICATIONS.value,
            NodeCapability.LOCATION.value,
        ]
        
        if not self.config.is_simulator:
            self.config.capabilities.append(NodeCapability.SCREEN_RECORD.value)
        
        return True
    
    async def get_capabilities(self) -> list[str]:
        """Get available capabilities."""
        return self.config.capabilities
    
    async def execute_command(self, command: str, args: dict) -> dict:
        """Execute iOS-specific command."""
        handlers = {
            "camera_snap": self._handle_camera_snap,
            "camera_clip": self._handle_camera_clip,
            "screen_record": self._handle_screen_record,
            "voice_wake": self._handle_voice_wake,
            "talk_mode": self._handle_talk_mode,
            "canvas_push": self._handle_canvas_push,
            "location_get": self._handle_location_get,
            "notify": self._handle_notify,
            "get_device_info": self._handle_get_device_info,
        }
        
        handler = handlers.get(command)
        if not handler:
            return {"error": f"Unknown command: {command}"}
        
        try:
            return await handler(args)
        except Exception as e:
            logger.error(f"[iOS] Command error: {e}")
            return {"error": str(e)}
    
    async def _handle_camera_snap(self, args: dict) -> dict:
        """Capture camera snapshot."""
        logger.info("[iOS] Capturing camera snapshot")
        
        self.camera_active = True
        await self.send_event("camera_active", {"status": "capturing"})
        
        # Simulate capture
        await asyncio.sleep(0.5)
        
        result = {
            "success": True,
            "image_data": "base64_encoded_image_data",
            "timestamp": datetime.now().isoformat(),
            "width": self.config.screen_width,
            "height": self.config.screen_height,
            "format": "jpeg",
            "camera": "rear"
        }
        
        self.camera_active = False
        return result
    
    async def _handle_camera_clip(self, args: dict) -> dict:
        """Record camera video clip."""
        duration = args.get("duration", 5)
        
        logger.info(f"[iOS] Recording camera clip for {duration}s")
        
        self.camera_active = True
        await self.send_event("camera_active", {"status": "recording"})
        
        # Simulate recording
        await asyncio.sleep(min(duration, 5))
        
        result = {
            "success": True,
            "video_data": "base64_encoded_video_data",
            "duration": duration,
            "timestamp": datetime.now().isoformat(),
            "format": "mp4",
            "camera": "rear"
        }
        
        self.camera_active = False
        return result
    
    async def _handle_screen_record(self, args: dict) -> dict:
        """Record screen."""
        if self.config.is_simulator:
            return {"success": False, "error": "Screen recording not available on simulator"}
        
        duration = args.get("duration", 10)
        
        logger.info(f"[iOS] Recording screen for {duration}s")
        
        self.screen_recording = True
        await self.send_event("screen_recording", {"status": "recording"})
        
        # Simulate recording
        await asyncio.sleep(min(duration, 5))
        
        result = {
            "success": True,
            "video_data": "base64_encoded_screen_data",
            "duration": duration,
            "timestamp": datetime.now().isoformat(),
            "format": "mp4"
        }
        
        self.screen_recording = False
        return result
    
    async def _handle_voice_wake(self, args: dict) -> dict:
        """Enable/disable Voice Wake."""
        enabled = args.get("enabled", True)
        wake_word = args.get("wake_word", "hey siri")
        
        logger.info(f"[iOS] Voice Wake: {enabled}")
        
        self.voice_wake_enabled = enabled
        
        await self.send_event("voice_wake_changed", {
            "enabled": enabled,
            "wake_word": wake_word,
            "timestamp": datetime.now().isoformat()
        })
        
        return {
            "success": True,
            "enabled": enabled,
            "wake_word": wake_word,
            "listening": enabled
        }
    
    async def _handle_talk_mode(self, args: dict) -> dict:
        """Enable Talk Mode overlay."""
        enabled = args.get("enabled", True)
        position = args.get("position", "bottom")
        
        logger.info(f"[iOS] Talk Mode: {enabled}")
        
        self.talk_mode_enabled = enabled
        
        await self.send_event("talk_mode_changed", {
            "enabled": enabled,
            "position": position,
            "timestamp": datetime.now().isoformat()
        })
        
        return {
            "success": True,
            "enabled": enabled,
            "position": position,
            "features": [
                "voice_input",
                "voice_output",
                "realtime_transcription",
                "interruption_aware"
            ]
        }
    
    async def _handle_canvas_push(self, args: dict) -> dict:
        """Push content to canvas."""
        content = args.get("content", {})
        layout = args.get("layout", "default")
        
        logger.info(f"[iOS] Canvas push: {layout}")
        
        await self.send_event("canvas_updated", {
            "layout": layout,
            "screen_size": f"{self.config.screen_width}x{self.config.screen_height}",
            "has_content": bool(content),
            "timestamp": datetime.now().isoformat()
        })
        
        return {
            "success": True,
            "canvas_id": f"canvas_{datetime.now().timestamp()}",
            "layout": layout,
            "screen_size": f"{self.config.screen_width}x{self.config.screen_height}"
        }
    
    async def _handle_location_get(self, args: dict) -> dict:
        """Get current location."""
        logger.info("[iOS] Getting location")
        
        # Simulate location data
        return {
            "success": True,
            "latitude": 37.7749,
            "longitude": -122.4194,
            "accuracy": 10.0,
            "altitude": 0.0,
            "timestamp": datetime.now().isoformat()
        }
    
    async def _handle_notify(self, args: dict) -> dict:
        """Send notification."""
        title = args.get("title", "nanobot")
        message = args.get("message", "")
        badge = args.get("badge", 1)
        
        logger.info(f"[iOS] Notification: {title}")
        
        await self.send_event("notification_sent", {
            "title": title,
            "message": message,
            "badge": badge,
            "timestamp": datetime.now().isoformat()
        })
        
        return {"success": True, "id": f"notify_{datetime.now().timestamp()}"}
    
    async def _handle_get_device_info(self, args: dict) -> dict:
        """Get device information."""
        return {
            "success": True,
            "device_id": self.config.device_id,
            "model": "iPhone" if not self.config.is_simulator else "iPhone Simulator",
            "os_version": "17.0",
            "screen_width": self.config.screen_width,
            "screen_height": self.config.screen_height,
            "locale": "en_US",
            "timezone": "America/Los_Angeles",
            "device_capabilities": self.config.capabilities
        }
    
    async def start(self):
        """Start iOS node."""
        logger.info("[iOS] Starting iOS node")
        await self.initialize()
        await self.connect()


async def create_ios_node(
    device_id: str = "ios-device",
    gateway_url: str = "ws://127.0.0.1:18789"
) -> iOSNode:
    """Create iOS node."""
    config = iOSNodeConfig(
        platform_type="ios",
        node_id=device_id,
        device_id=device_id,
        device_name=f"iPhone ({device_id})",
        gateway_url=gateway_url
    )
    
    return iOSNode(config)
