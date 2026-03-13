"""Gateway platform integration for nanobot.

Handles WebSocket connections from platform nodes (macOS, iOS, Android).
"""

import asyncio
import json
from typing import Optional, Dict, Callable
from loguru import logger
from datetime import datetime
import websockets
from websockets.server import WebSocketServerProtocol, serve


class PlatformGateway:
    """WebSocket gateway for platform nodes."""
    
    def __init__(self, host: str = "127.0.0.1", port: int = 18789):
        self.host = host
        self.port = port
        self.connected_nodes: Dict[str, WebSocketServerProtocol] = {}
        self.node_metadata: Dict[str, dict] = {}
        self.command_handlers: Dict[str, Callable] = {}
        self.event_handlers: Dict[str, Callable] = {}
        self.server = None
        
    async def start(self):
        """Start the platform gateway."""
        logger.info(f"[Gateway] Starting platform gateway on {self.host}:{self.port}")
        
        async with serve(self._handle_connection, self.host, self.port):
            logger.info(f"[Gateway] Platform gateway listening on ws://{self.host}:{self.port}")
            await asyncio.Future()  # run forever
    
    async def _handle_connection(self, ws: WebSocketServerProtocol, path: str):
        """Handle new node connection."""
        node_id = None
        
        try:
            # Wait for handshake
            handshake = await asyncio.wait_for(ws.recv(), timeout=5)
            handshake_data = json.loads(handshake)
            
            node_id = handshake_data.get("payload", {}).get("node_id", "unknown")
            platform = handshake_data.get("payload", {}).get("platform", "unknown")
            
            logger.info(f"[Gateway] Node connected: {node_id} ({platform})")
            
            self.connected_nodes[node_id] = ws
            self.node_metadata[node_id] = handshake_data.get("payload", {})
            
            # Notify about new node
            if "on_node_connected" in self.event_handlers:
                await self.event_handlers["on_node_connected"]({
                    "node_id": node_id,
                    "platform": platform,
                    "metadata": self.node_metadata[node_id]
                })
            
            # Listen for messages
            await self._listen_node(node_id, ws)
            
        except asyncio.TimeoutError:
            logger.warning("[Gateway] Handshake timeout")
        except json.JSONDecodeError:
            logger.warning("[Gateway] Invalid handshake JSON")
        except Exception as e:
            logger.error(f"[Gateway] Connection error: {e}")
        finally:
            if node_id and node_id in self.connected_nodes:
                del self.connected_nodes[node_id]
                del self.node_metadata[node_id]
                logger.info(f"[Gateway] Node disconnected: {node_id}")
                
                if "on_node_disconnected" in self.event_handlers:
                    await self.event_handlers["on_node_disconnected"]({"node_id": node_id})
    
    async def _listen_node(self, node_id: str, ws: WebSocketServerProtocol):
        """Listen for messages from a node."""
        try:
            async for message in ws:
                try:
                    data = json.loads(message)
                    message_type = data.get("type")
                    
                    if message_type == "command":
                        await self._handle_command(node_id, data)
                    elif message_type == "event":
                        await self._handle_event(node_id, data)
                    elif message_type == "response":
                        await self._handle_response(node_id, data)
                    
                except json.JSONDecodeError:
                    logger.warning(f"[Gateway] Invalid JSON from {node_id}")
        except Exception as e:
            logger.error(f"[Gateway] Listen error for {node_id}: {e}")
    
    async def _handle_command(self, node_id: str, data: dict):
        """Handle command from node."""
        message_id = data.get("message_id")
        payload = data.get("payload", {})
        command = payload.get("command")
        args = payload.get("args", {})
        
        logger.debug(f"[Gateway] Command from {node_id}: {command}")
        
        if command in self.command_handlers:
            try:
                result = await self.command_handlers[command](node_id, args)
                await self.send_response(node_id, message_id, result)
            except Exception as e:
                await self.send_response(node_id, message_id, {
                    "error": str(e)
                })
    
    async def _handle_event(self, node_id: str, data: dict):
        """Handle event from node."""
        payload = data.get("payload", {})
        event_type = payload.get("event")
        
        logger.debug(f"[Gateway] Event from {node_id}: {event_type}")
        
        if event_type in self.event_handlers:
            try:
                await self.event_handlers[event_type]({
                    "node_id": node_id,
                    **{k: v for k, v in payload.items() if k != "event"}
                })
            except Exception as e:
                logger.error(f"[Gateway] Event handler error: {e}")
    
    async def _handle_response(self, node_id: str, data: dict):
        """Handle response from node."""
        message_id = data.get("message_id")
        payload = data.get("payload", {})
        
        logger.debug(f"[Gateway] Response from {node_id}: {message_id}")
        
        # Store response or call waiting handler
        # This would integrate with command request system
    
    async def send_command(self, node_id: str, command: str, args: dict = None) -> bool:
        """Send command to a node."""
        args = args or {}
        
        if node_id not in self.connected_nodes:
            logger.warning(f"[Gateway] Node not connected: {node_id}")
            return False
        
        message = {
            "type": "command",
            "node_id": node_id,
            "timestamp": datetime.now().isoformat(),
            "payload": {
                "command": command,
                "args": args
            }
        }
        
        try:
            await self.connected_nodes[node_id].send(json.dumps(message))
            return True
        except Exception as e:
            logger.error(f"[Gateway] Send error to {node_id}: {e}")
            return False
    
    async def broadcast_command(self, command: str, args: dict = None) -> Dict[str, bool]:
        """Send command to all nodes."""
        args = args or {}
        results = {}
        
        for node_id in self.connected_nodes.keys():
            results[node_id] = await self.send_command(node_id, command, args)
        
        return results
    
    async def send_response(self, node_id: str, message_id: str, result: dict) -> bool:
        """Send response to a node."""
        if node_id not in self.connected_nodes:
            return False
        
        message = {
            "type": "response",
            "message_id": message_id,
            "node_id": node_id,
            "timestamp": datetime.now().isoformat(),
            "payload": result
        }
        
        try:
            await self.connected_nodes[node_id].send(json.dumps(message))
            return True
        except Exception as e:
            logger.error(f"[Gateway] Send error to {node_id}: {e}")
            return False
    
    def register_command_handler(self, command: str, handler: Callable):
        """Register command handler."""
        self.command_handlers[command] = handler
        logger.debug(f"[Gateway] Registered command handler: {command}")
    
    def register_event_handler(self, event_type: str, handler: Callable):
        """Register event handler."""
        self.event_handlers[event_type] = handler
        logger.debug(f"[Gateway] Registered event handler: {event_type}")
    
    async def get_node_status(self, node_id: str) -> Optional[dict]:
        """Get status of a node."""
        if node_id not in self.node_metadata:
            return None
        
        return {
            "node_id": node_id,
            "connected": node_id in self.connected_nodes,
            "metadata": self.node_metadata[node_id]
        }
    
    async def get_all_nodes(self) -> Dict[str, dict]:
        """Get all connected nodes."""
        result = {}
        for node_id in self.node_metadata.keys():
            status = await self.get_node_status(node_id)
            if status:
                result[node_id] = status
        
        return result
