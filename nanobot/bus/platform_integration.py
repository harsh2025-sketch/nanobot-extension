"""Integration helpers for platform nodes."""

import asyncio
from loguru import logger
from ..platforms.macos import MacOSMenuBar, create_macos_menubar
from ..platforms.ios import iOSNode, create_ios_node
from ..platforms.android import AndroidNode, create_android_node
from .platform_gateway import PlatformGateway


async def setup_platform_integration(gateway: PlatformGateway, agent_loop=None):
    """Setup platform node integration with gateway and agent."""
    
    logger.info("[Platforms] Setting up platform integration")
    
    # Register command handlers
    
    async def handle_notify(node_id: str, args: dict) -> dict:
        """Handle notification from node."""
        logger.info(f"[Platforms] Notification from {node_id}: {args.get('title')}")
        return {"success": True}
    
    async def handle_canvas_update(node_id: str, args: dict) -> dict:
        """Handle canvas update from node."""
        logger.info(f"[Platforms] Canvas update from {node_id}")
        return {"success": True}
    
    async def handle_system_run(node_id: str, args: dict) -> dict:
        """Handle system command from node."""
        logger.info(f"[Platforms] System command from {node_id}: {args.get('command')}")
        return {"success": True}
    
    gateway.register_command_handler("notify", handle_notify)
    gateway.register_command_handler("system_run", handle_system_run)
    gateway.register_command_handler("canvas_push", handle_canvas_update)
    
    # Register event handlers
    
    async def on_node_connected(data: dict):
        """Handle node connection."""
        node_id = data.get("node_id")
        platform = data.get("platform")
        logger.info(f"[Platforms] Node connected: {node_id} ({platform})")
    
    async def on_node_disconnected(data: dict):
        """Handle node disconnection."""
        node_id = data.get("node_id")
        logger.info(f"[Platforms] Node disconnected: {node_id}")
    
    async def on_camera_active(data: dict):
        """Handle camera activation."""
        node_id = data.get("node_id")
        status = data.get("status")
        logger.debug(f"[Platforms] {node_id} camera: {status}")
    
    async def on_talk_mode_changed(data: dict):
        """Handle Talk Mode change."""
        node_id = data.get("node_id")
        enabled = data.get("enabled")
        logger.info(f"[Platforms] {node_id} Talk Mode: {enabled}")
    
    gateway.register_event_handler("on_node_connected", on_node_connected)
    gateway.register_event_handler("on_node_disconnected", on_node_disconnected)
    gateway.register_event_handler("camera_active", on_camera_active)
    gateway.register_event_handler("talk_mode_changed", on_talk_mode_changed)
    
    logger.info("[Platforms] Platform integration ready")


def create_platform_demo_nodes(gateway_url: str = "ws://127.0.0.1:18789"):
    """Create demo platform nodes for testing."""
    
    nodes = []
    
    # Create macOS menu bar app
    macos_app = MacOSMenuBar(gateway_url=gateway_url)
    nodes.append(macos_app)
    
    # Create iOS node
    ios_node = iOSNode(gateway_url=gateway_url)
    nodes.append(ios_node)
    
    # Create Android node
    android_node = AndroidNode(gateway_url=gateway_url)
    nodes.append(android_node)
    
    return nodes
