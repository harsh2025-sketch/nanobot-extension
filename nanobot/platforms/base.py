"""Base classes for platform node support."""

import asyncio
import json
from abc import ABC, abstractmethod
from datetime import datetime
from enum import Enum
from typing import Any, Optional
from dataclasses import dataclass, asdict
from loguru import logger
import websockets
from websockets.server import WebSocketServerProtocol


class PlatformType(str, Enum):
    """Platform types."""
    MACOS = "macos"
    IOS = "ios"
    ANDROID = "android"
    WINDOWS = "windows"
    LINUX = "linux"


class NodeCapability(str, Enum):
    """Node capabilities."""
    CAMERA = "camera"
    SCREEN_RECORD = "screen_record"
    VOICE_WAKE = "voice_wake"
    TALK_MODE = "talk_mode"
    CANVAS = "canvas"
    NOTIFICATIONS = "notifications"
    LOCATION = "location"
    SYSTEM_RUN = "system_run"
    SMS = "sms"


@dataclass
class PlatformConfig:
    """Platform configuration."""
    platform_type: str
    node_id: str
    gateway_url: str = "ws://127.0.0.1:18789"
    device_name: str = ""
    capabilities: list[str] = None
    auto_reconnect: bool = True
    reconnect_interval: int = 5
    max_reconnect_attempts: int = 10
    
    def __post_init__(self):
        if self.capabilities is None:
            self.capabilities = []


@dataclass
class PlatformMessage:
    """Message from/to platform node."""
    type: str  # "command", "response", "event"
    node_id: str
    timestamp: str
    payload: dict[str, Any]
    message_id: Optional[str] = None
    
    def to_dict(self) -> dict:
        return asdict(self)
    
    def to_json(self) -> str:
        return json.dumps(self.to_dict())
    
    @classmethod
    def from_dict(cls, data: dict) -> "PlatformMessage":
        """Create from dict."""
        return cls(**data)


class PlatformNode(ABC):
    """Base class for platform nodes (macOS, iOS, Android)."""
    
    def __init__(self, config: PlatformConfig):
        self.config = config
        self.is_connected = False
        self.ws: Optional[WebSocketServerProtocol] = None
        self.message_queue: asyncio.Queue = asyncio.Queue()
        self.reconnect_attempts = 0
        self.listeners: dict[str, list[callable]] = {}
        
    @abstractmethod
    async def initialize(self) -> bool:
        """Initialize platform-specific setup."""
        pass
    
    @abstractmethod
    async def get_capabilities(self) -> list[str]:
        """Get available capabilities on this node."""
        pass
    
    @abstractmethod
    async def execute_command(self, command: str, args: dict) -> dict:
        """Execute platform-specific command."""
        pass
    
    async def connect(self) -> bool:
        """Connect to gateway."""
        attempts = 0
        while attempts < self.config.max_reconnect_attempts:
            try:
                logger.info(f"[{self.config.platform_type}] Connecting to gateway {self.config.gateway_url}")
                async with websockets.connect(self.config.gateway_url) as ws:
                    self.ws = ws
                    self.is_connected = True
                    self.reconnect_attempts = 0
                    logger.info(f"[{self.config.platform_type}] Connected to gateway")
                    
                    # Send handshake
                    handshake = PlatformMessage(
                        type="handshake",
                        node_id=self.config.node_id,
                        timestamp=datetime.now().isoformat(),
                        payload={
                            "platform": self.config.platform_type,
                            "device_name": self.config.device_name,
                            "capabilities": self.config.capabilities,
                            "version": "1.0"
                        }
                    )
                    await ws.send(handshake.to_json())
                    
                    # Listen for messages
                    await self._listen()
                    
            except Exception as e:
                logger.error(f"[{self.config.platform_type}] Connection failed: {e}")
                self.is_connected = False
                attempts += 1
                
                if self.config.auto_reconnect and attempts < self.config.max_reconnect_attempts:
                    logger.info(f"[{self.config.platform_type}] Reconnecting in {self.config.reconnect_interval}s...")
                    await asyncio.sleep(self.config.reconnect_interval)
                else:
                    break
        
        return self.is_connected
    
    async def _listen(self):
        """Listen for messages from gateway."""
        try:
            async for message in self.ws:
                try:
                    data = json.loads(message)
                    msg = PlatformMessage.from_dict(data)
                    await self.message_queue.put(msg)
                    await self._handle_message(msg)
                except json.JSONDecodeError:
                    logger.error(f"[{self.config.platform_type}] Invalid JSON: {message}")
        except Exception as e:
            logger.error(f"[{self.config.platform_type}] Listen error: {e}")
            self.is_connected = False
    
    async def _handle_message(self, message: PlatformMessage):
        """Handle incoming message."""
        if message.type == "command":
            response = await self.execute_command(
                message.payload.get("command", ""),
                message.payload.get("args", {})
            )
            await self.send_response(message.message_id or "", response)
        
        # Trigger listeners
        if message.type in self.listeners:
            for listener in self.listeners[message.type]:
                try:
                    await listener(message)
                except Exception as e:
                    logger.error(f"[{self.config.platform_type}] Listener error: {e}")
    
    async def send_message(self, message: PlatformMessage) -> bool:
        """Send message to gateway."""
        if not self.is_connected or not self.ws:
            logger.warning(f"[{self.config.platform_type}] Not connected to gateway")
            return False
        
        try:
            await self.ws.send(message.to_json())
            return True
        except Exception as e:
            logger.error(f"[{self.config.platform_type}] Send error: {e}")
            return False
    
    async def send_event(self, event_type: str, payload: dict) -> bool:
        """Send event to gateway."""
        message = PlatformMessage(
            type="event",
            node_id=self.config.node_id,
            timestamp=datetime.now().isoformat(),
            payload={"event": event_type, **payload}
        )
        return await self.send_message(message)
    
    async def send_response(self, message_id: str, result: dict) -> bool:
        """Send response to gateway."""
        message = PlatformMessage(
            type="response",
            message_id=message_id,
            node_id=self.config.node_id,
            timestamp=datetime.now().isoformat(),
            payload=result
        )
        return await self.send_message(message)
    
    def on(self, message_type: str, callback: callable):
        """Register listener for message type."""
        if message_type not in self.listeners:
            self.listeners[message_type] = []
        self.listeners[message_type].append(callback)
    
    def off(self, message_type: str, callback: callable):
        """Unregister listener."""
        if message_type in self.listeners:
            try:
                self.listeners[message_type].remove(callback)
            except ValueError:
                pass
