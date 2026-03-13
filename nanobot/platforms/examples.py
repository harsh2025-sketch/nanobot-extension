"""Example: Platform Nodes Integration with nanobot.

This example demonstrates how to:
1. Create platform nodes (macOS, iOS, Android)
2. Connect to the gateway
3. Execute commands
4. Handle events
"""

import asyncio
from loguru import logger

from nanobot.platforms.macos import create_macos_menubar
from nanobot.platforms.ios import create_ios_node
from nanobot.platforms.android import create_android_node
from nanobot.platforms.manager import PlatformManager
from nanobot.bus.platform_gateway import PlatformGateway
from nanobot.bus.platform_integration import setup_platform_integration


async def example_basic_usage():
    """Example 1: Basic node creation and initialization."""
    print("\n=== Example 1: Basic Node Creation ===\n")
    
    # Create nodes
    macos = await create_macos_menubar(
        device_name="My MacBook Pro"
    )
    
    ios = await create_ios_node(
        device_id="iphone-15-pro"
    )
    
    android = await create_android_node(
        device_id="pixel-8-pro"
    )
    
    # Initialize
    for node in [macos, ios, android]:
        await node.initialize()
        print(f"âœ“ {node.config.device_name}")
        print(f"  Capabilities: {', '.join(node.config.capabilities)}\n")


async def example_command_execution():
    """Example 2: Execute commands on nodes."""
    print("\n=== Example 2: Command Execution ===\n")
    
    # Create iOS node
    ios = await create_ios_node(device_id="test-iphone")
    await ios.initialize()
    
    # Simulate command execution (without real WebSocket connection)
    result = await ios.execute_command("camera_snap", {"camera": "rear"})
    print(f"Camera Snap: {result.get('success')}")
    print(f"Format: {result.get('format')}")
    print(f"Timestamp: {result.get('timestamp')}\n")
    
    # Screen recording
    result = await ios.execute_command("screen_record", {"duration": 5})
    print(f"Screen Record: {result.get('success')}")
    print(f"Duration: {result.get('duration')}s\n")
    
    # Android SMS
    android = await create_android_node(device_id="test-android")
    await android.initialize()
    
    result = await android.execute_command("send_sms", {
        "phone_number": "+1234567890",
        "message": "Hello from nanobot!"
    })
    print(f"SMS Sent: {result.get('success')}\n")


async def example_event_handling():
    """Example 3: Handle events from nodes."""
    print("\n=== Example 3: Event Handling ===\n")
    
    # Create iOS node
    ios = await create_ios_node(device_id="event-test")
    await ios.initialize()
    
    # Register event listeners
    async def on_camera_active(data):
        print(f"ðŸ“· Camera Event: {data}")
    
    async def on_talk_mode(data):
        print(f"ðŸŽ¤ Talk Mode Event: {data}")
    
    ios.on("camera_active", on_camera_active)
    ios.on("talk_mode_changed", on_talk_mode)
    
    # Trigger events
    await ios.send_event("camera_active", {"status": "capturing"})
    await ios.send_event("talk_mode_changed", {
        "enabled": True,
        "position": "bottom"
    })


async def example_platform_manager():
    """Example 4: Using PlatformManager."""
    print("\n=== Example 4: Platform Manager ===\n")
    
    manager = PlatformManager()
    
    # Create and register multiple nodes
    nodes = []
    
    macos = await create_macos_menubar()
    await macos.initialize()
    manager.register_node(macos)
    nodes.append(macos)
    
    ios = await create_ios_node(device_id="iphone-1")
    await ios.initialize()
    manager.register_node(ios)
    nodes.append(ios)
    
    android = await create_android_node(device_id="android-1")
    await android.initialize()
    manager.register_node(android)
    nodes.append(android)
    
    # Get status
    status = await manager.get_node_status()
    print("Platform Manager Status:")
    for node_id, info in status.items():
        print(f"  {node_id}: {info['platform']} - {info['device_name']}")
        print(f"    Capabilities: {', '.join(info['capabilities'][:2])}...")
    
    print()


async def example_gateway_integration():
    """Example 5: Gateway integration."""
    print("\n=== Example 5: Gateway Integration ===\n")
    
    # Create gateway
    gateway = PlatformGateway(host="127.0.0.1", port=18789)
    
    # Register handlers
    async def handle_notify(node_id: str, args: dict) -> dict:
        print(f"ðŸ“¬ Notification from {node_id}: {args.get('title')}")
        return {"success": True}
    
    async def handle_system_run(node_id: str, args: dict) -> dict:
        print(f"âš™ï¸  System command from {node_id}: {args.get('command')}")
        return {"success": True}
    
    async def on_node_connected(data: dict):
        print(f"âœ… Node connected: {data.get('node_id')} ({data.get('platform')})")
    
    async def on_node_disconnected(data: dict):
        print(f"âŒ Node disconnected: {data.get('node_id')}")
    
    gateway.register_command_handler("notify", handle_notify)
    gateway.register_command_handler("system_run", handle_system_run)
    gateway.register_event_handler("on_node_connected", on_node_connected)
    gateway.register_event_handler("on_node_disconnected", on_node_disconnected)
    
    print("âœ“ Gateway configured")
    print("  - notify handler registered")
    print("  - system_run handler registered")
    print("  - Node connection handlers ready\n")


async def example_macos_specific():
    """Example 6: macOS-specific features."""
    print("\n=== Example 6: macOS Features ===\n")
    
    app = await create_macos_menubar(
        menu_title="nanobot",
        start_at_login=True
    )
    await app.initialize()
    
    print(f"âœ“ macOS Menu Bar App: {app.config.device_name}")
    
    # Simulate menu operations
    await app.add_menu_item("quick_search", "Quick Search", None)
    await app.update_status("listening")
    
    # Simulate commands
    result = await app.execute_command("toggle_visibility", {})
    print(f"  Toggle visibility: {result.get('visible')}")
    
    result = await app.execute_command("talk_mode", {"enabled": True})
    print(f"  Talk Mode: {result.get('features')}")
    
    result = await app.execute_command("screen_capture", {})
    print(f"  Screen capture: {result.get('format')} @ {result.get('width')}x{result.get('height')}")
    
    # Auto-start
    if await app.add_to_login_items():
        print("  âœ“ Added to login items\n")


async def example_ios_specific():
    """Example 7: iOS-specific features."""
    print("\n=== Example 7: iOS Features ===\n")
    
    node = await create_ios_node(device_id="iphone-15")
    await node.initialize()
    
    print(f"âœ“ iOS Node: {node.config.device_name}")
    print(f"  Screen: {node.config.screen_width}x{node.config.screen_height}")
    
    # Camera operations
    result = await node.execute_command("camera_snap", {})
    print(f"  Camera snap: {result.get('format')}")
    
    # Voice Wake
    result = await node.execute_command("voice_wake", {"enabled": True})
    print(f"  Voice Wake: {result.get('enabled')}")
    
    # Location
    result = await node.execute_command("location_get", {})
    if result.get('success'):
        print(f"  Location: ({result.get('latitude')}, {result.get('longitude')})")
    
    # Device info
    result = await node.execute_command("get_device_info", {})
    print(f"  Device ID: {result.get('device_id')}")
    print(f"  OS: {result.get('model')} iOS {result.get('os_version')}\n")


async def example_android_specific():
    """Example 8: Android-specific features."""
    print("\n=== Example 8: Android Features ===\n")
    
    node = await create_android_node(device_id="pixel-8")
    await node.initialize()
    
    print(f"âœ“ Android Node: {node.config.device_name}")
    print(f"  API Level: {node.config.api_level}")
    
    # Camera with front and rear
    for camera in ["rear", "front"]:
        result = await node.execute_command("camera_snap", {"camera": camera})
        print(f"  Camera ({camera}): {result.get('format')}")
    
    # Screen recording with audio
    result = await node.execute_command("screen_record", {
        "duration": 10,
        "include_audio": True
    })
    print(f"  Screen recording: {result.get('resolution')} with audio")
    
    # SMS
    result = await node.execute_command("send_sms", {
        "phone_number": "+1234567890",
        "message": "Test message"
    })
    print(f"  SMS sent: {result.get('success')}")
    
    # Device info
    result = await node.execute_command("get_device_info", {})
    print(f"  Device ID: {result.get('device_id')}")
    print(f"  Platform: {result.get('platform')} API {result.get('api_level')}\n")


async def main():
    """Run all examples."""
    logger.info("Platform Nodes Examples")
    
    await example_basic_usage()
    await example_command_execution()
    await example_event_handling()
    await example_platform_manager()
    await example_gateway_integration()
    await example_macos_specific()
    await example_ios_specific()
    await example_android_specific()
    
    print("\nâœ… All examples completed!")


if __name__ == "__main__":
    asyncio.run(main())
