"""Node manager for coordinating multiple platform nodes."""

from typing import Optional, Dict, List
from loguru import logger
from .platform_node_client import RemoteNodeProxy


class NodeManager:
    """Manages all connected platform nodes."""
    
    def __init__(self):
        self.nodes: Dict[str, RemoteNodeProxy] = {}
        
    def register_node(self, node_id: str, platform: str) -> RemoteNodeProxy:
        """Register a node."""
        if node_id in self.nodes:
            logger.warning(f"Node {node_id} already registered")
            return self.nodes[node_id]
        
        node = RemoteNodeProxy(node_id, platform)
        self.nodes[node_id] = node
        logger.info(f"Registered node: {node_id} ({platform})")
        return node
    
    def unregister_node(self, node_id: str) -> bool:
        """Unregister a node."""
        if node_id not in self.nodes:
            return False
        
        del self.nodes[node_id]
        logger.info(f"Unregistered node: {node_id}")
        return True
    
    def get_node(self, node_id: str) -> Optional[RemoteNodeProxy]:
        """Get node by ID."""
        return self.nodes.get(node_id)
    
    def get_nodes_by_platform(self, platform: str) -> List[RemoteNodeProxy]:
        """Get all nodes of specific platform."""
        return [n for n in self.nodes.values() if n.platform == platform]
    
    def get_all_nodes(self) -> List[RemoteNodeProxy]:
        """Get all registered nodes."""
        return list(self.nodes.values())
    
    async def broadcast_command(self, command: str, args: dict) -> Dict[str, dict]:
        """Send command to all nodes."""
        results = {}
        for node_id, node in self.nodes.items():
            try:
                # Use generic command execution on client
                result = await node.client.send_command(command, args)
                results[node_id] = result
            except Exception as e:
                results[node_id] = {"error": str(e)}
        
        return results
    
    def list_nodes(self) -> List[Dict]:
        """List all nodes with info."""
        return [
            {
                "node_id": node.node_id,
                "platform": node.platform
            }
            for node in self.nodes.values()
        ]
