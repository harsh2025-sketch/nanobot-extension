"""Platform manager for handling multiple connected nodes."""

from typing import Optional, Dict
from loguru import logger
from .base import PlatformNode, PlatformConfig, PlatformType, PlatformMessage
import asyncio


class PlatformManager:
    """Manages all connected platform nodes."""
    
    def __init__(self):
        self.nodes: Dict[str, PlatformNode] = {}
        self.event_listeners: dict[str, list[callable]] = {}
        
    def register_node(self, node: PlatformNode) -> bool:
        """Register a platform node."""
        node_id = node.config.node_id
        if node_id in self.nodes:
            logger.warning(f"Node {node_id} already registered")
            return False
        
        self.nodes[node_id] = node
        logger.info(f"Registered node: {node_id} ({node.config.platform_type})")
        return True
    
    def unregister_node(self, node_id: str) -> bool:
        """Unregister a platform node."""
        if node_id not in self.nodes:
            return False
        
        del self.nodes[node_id]
        logger.info(f"Unregistered node: {node_id}")
        return True
    
    def get_node(self, node_id: str) -> Optional[PlatformNode]:
        """Get a node by ID."""
        return self.nodes.get(node_id)
    
    def get_nodes_by_platform(self, platform_type: str) -> list[PlatformNode]:
        """Get all nodes of a specific platform type."""
        return [
            node for node in self.nodes.values()
            if node.config.platform_type == platform_type
        ]
    
    def get_nodes_with_capability(self, capability: str) -> list[PlatformNode]:
        """Get all nodes with a specific capability."""
        return [
            node for node in self.nodes.values()
            if capability in node.config.capabilities
        ]
    
    async def broadcast_command(self, command: str, args: dict, exclude_node: Optional[str] = None) -> dict[str, dict]:
        """Broadcast a command to all connected nodes."""
        results = {}
        tasks = []
        
        for node_id, node in self.nodes.items():
            if exclude_node and node_id == exclude_node:
                continue
            
            async def execute_on_node(nid: str, n: PlatformNode):
                try:
                    result = await n.execute_command(command, args)
                    results[nid] = {"success": True, "result": result}
                except Exception as e:
                    results[nid] = {"success": False, "error": str(e)}
            
            tasks.append(execute_on_node(node_id, node))
        
        if tasks:
            await asyncio.gather(*tasks)
        
        return results
    
    async def broadcast_message(self, message: PlatformMessage, exclude_node: Optional[str] = None) -> dict[str, bool]:
        """Broadcast a message to all connected nodes."""
        results = {}
        
        for node_id, node in self.nodes.items():
            if exclude_node and node_id == exclude_node:
                continue
            
            message.node_id = node_id
            results[node_id] = await node.send_message(message)
        
        return results
    
    async def get_node_status(self) -> dict[str, dict]:
        """Get status of all nodes."""
        status = {}
        for node_id, node in self.nodes.items():
            status[node_id] = {
                "platform": node.config.platform_type,
                "connected": node.is_connected,
                "device_name": node.config.device_name,
                "capabilities": node.config.capabilities
            }
        return status
    
    def on_event(self, event_type: str, callback: callable):
        """Register listener for event type."""
        if event_type not in self.event_listeners:
            self.event_listeners[event_type] = []
        self.event_listeners[event_type].append(callback)
    
    async def trigger_event(self, event_type: str, data: dict):
        """Trigger event listeners."""
        if event_type in self.event_listeners:
            for callback in self.event_listeners[event_type]:
                try:
                    await callback(data)
                except Exception as e:
                    logger.error(f"Event listener error: {e}")
