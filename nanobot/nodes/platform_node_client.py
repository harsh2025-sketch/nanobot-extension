"""Cross-platform node client."""

import asyncio
import json
from typing import Optional, Callable, Any
from dataclasses import dataclass
from loguru import logger
from datetime import datetime


@dataclass
class NodeMessage:
    """Message structure for node communication."""
    type: str  # "event", "command", "response"
    node_id: str
    timestamp: str
    payload: dict[str, Any]
    message_id: Optional[str] = None


class PlatformNodeClient:
    """Client for communicating with platform nodes."""
    
    def __init__(self, node_id: str):
        self.node_id = node_id
        self.event_callbacks: dict[str, list[Callable]] = {}
        self.pending_responses: dict[str, asyncio.Future] = {}
        
    def on_event(self, event_type: str, callback: Callable):
        """Register event listener."""
        if event_type not in self.event_callbacks:
            self.event_callbacks[event_type] = []
        self.event_callbacks[event_type].append(callback)
    
    async def send_command(self, command: str, args: dict = None, timeout: int = 30) -> dict:
        """Send command to node and wait for response."""
        args = args or {}
        message_id = f"{self.node_id}_{datetime.now().timestamp()}"
        
        message = {
            "type": "command",
            "node_id": self.node_id,
            "message_id": message_id,
            "timestamp": datetime.now().isoformat(),
            "payload": {
                "command": command,
                "args": args
            }
        }
        
        future: asyncio.Future = asyncio.Future()
        self.pending_responses[message_id] = future
        
        try:
            # Send would happen via underlying transport (WebSocket, etc.)
            # This is a placeholder for the actual send mechanism
            logger.debug(f"[{self.node_id}] Sending command: {command}")
            
            # Wait for response with timeout
            result = await asyncio.wait_for(future, timeout=timeout)
            return result
        except asyncio.TimeoutError:
            logger.error(f"[{self.node_id}] Command timeout: {command}")
            return {"error": "Command timeout"}
        finally:
            self.pending_responses.pop(message_id, None)
    
    async def send_event(self, event_type: str, payload: dict) -> bool:
        """Send event from node."""
        message = {
            "type": "event",
            "node_id": self.node_id,
            "timestamp": datetime.now().isoformat(),
            "payload": {
                "event": event_type,
                **payload
            }
        }
        
        logger.debug(f"[{self.node_id}] Event: {event_type}")
        return True
    
    async def trigger_event(self, event_type: str, data: dict):
        """Trigger local event callbacks."""
        if event_type in self.event_callbacks:
            for callback in self.event_callbacks[event_type]:
                try:
                    result = callback(data)
                    if asyncio.iscoroutine(result):
                        await result
                except Exception as e:
                    logger.error(f"[{self.node_id}] Event callback error: {e}")
    
    def handle_response(self, message_id: str, result: dict):
        """Handle command response."""
        if message_id in self.pending_responses:
            future = self.pending_responses[message_id]
            if not future.done():
                future.set_result(result)


class RemoteNodeProxy:
    """Proxy to control a remote node."""
    
    def __init__(self, node_id: str, platform: str):
        self.node_id = node_id
        self.platform = platform
        self.client = PlatformNodeClient(node_id)
        self.last_status = {}
        
    async def snap_camera(self, camera: str = "rear") -> dict:
        """Take camera snapshot."""
        return await self.client.send_command("camera_snap", {"camera": camera})
    
    async def record_camera(self, duration: int = 5, camera: str = "rear") -> dict:
        """Record camera clip."""
        return await self.client.send_command("camera_clip", {
            "duration": duration,
            "camera": camera
        })
    
    async def record_screen(self, duration: int = 10, include_audio: bool = True) -> dict:
        """Record screen."""
        return await self.client.send_command("screen_record", {
            "duration": duration,
            "include_audio": include_audio
        })
    
    async def enable_talk_mode(self, enabled: bool = True, position: str = "bottom") -> dict:
        """Enable Talk Mode."""
        return await self.client.send_command("talk_mode", {
            "enabled": enabled,
            "position": position
        })
    
    async def enable_voice_wake(self, enabled: bool = True, wake_word: str = "hey") -> dict:
        """Enable Voice Wake."""
        return await self.client.send_command("voice_wake", {
            "enabled": enabled,
            "wake_word": wake_word
        })
    
    async def push_canvas(self, content: dict, layout: str = "default") -> dict:
        """Push content to canvas."""
        return await self.client.send_command("canvas_push", {
            "content": content,
            "layout": layout
        })
    
    async def get_location(self) -> dict:
        """Get device location."""
        return await self.client.send_command("location_get")
    
    async def send_notification(self, title: str, message: str) -> dict:
        """Send notification."""
        return await self.client.send_command("notify", {
            "title": title,
            "message": message
        })
    
    async def send_sms(self, phone_number: str, message: str) -> dict:
        """Send SMS (Android only)."""
        return await self.client.send_command("send_sms", {
            "phone_number": phone_number,
            "message": message
        })
    
    async def get_device_info(self) -> dict:
        """Get device information."""
        return await self.client.send_command("get_device_info")
    
    def on_event(self, event_type: str, callback: Callable):
        """Register event listener."""
        self.client.on_event(event_type, callback)
