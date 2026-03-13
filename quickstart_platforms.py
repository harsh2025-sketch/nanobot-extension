#!/usr/bin/env python3
"""
Quick Start: Platform Nodes for nanobot

This script demonstrates how to get started with platform nodes in nanobot.
"""

import asyncio
from loguru import logger

# Configure logging
logger.enable("nanobot")


async def main():
    """Quick start guide for platform nodes."""
    
    print("\n" + "="*60)
    print("  nanobot Platform Nodes - Quick Start")
    print("="*60 + "\n")
    
    print("📱 Platform Support in nanobot")
    print("-" * 60)
    print("This version of nanobot includes native apps for:")
    print("  • macOS Menu Bar App")
    print("  • iOS Node (iPhone app)")
    print("  • Android Node (Android app)")
    print()
    
    # Example 1: Create nodes
    print("1️⃣  Creating Nodes")
    print("-" * 60)
    
    from nanobot.platforms.macos import create_macos_menubar
    from nanobot.platforms.ios import create_ios_node
    from nanobot.platforms.android import create_android_node
    
    macos = await create_macos_menubar()
    ios = await create_ios_node(device_id="test-iphone")
    android = await create_android_node(device_id="test-android")
    
    print(f"✓ Created macOS app: {macos.config.device_name}")
    print(f"✓ Created iOS node: {ios.config.device_name}")
    print(f"✓ Created Android node: {android.config.device_name}\n")
    
    # Example 2: Initialize nodes
    print("2️⃣  Initializing Nodes")
    print("-" * 60)
    
    for node in [macos, ios, android]:
        await node.initialize()
        caps = len(node.config.capabilities)
        print(f"✓ {node.config.device_name}")
        print(f"  Capabilities: {caps} features available")
    print()
    
    # Example 3: Execute commands
    print("3️⃣  Executing Commands")
    print("-" * 60)
    
    result = await ios.execute_command("camera_snap", {"camera": "rear"})
    print(f"✓ iOS Camera Snap: {result.get('success')}")
    
    result = await android.execute_command("send_sms", {
        "phone_number": "+1234567890",
        "message": "Hello from nanobot!"
    })
    print(f"✓ Android SMS: {result.get('success')}")
    
    result = await macos.execute_command("notify", {
        "title": "Hello",
        "message": "Platform nodes are working!"
    })
    print(f"✓ macOS Notification: {result.get('success')}\n")
    
    # Example 4: Using Platform Manager
    print("4️⃣  Platform Manager")
    print("-" * 60)
    
    from nanobot.platforms.manager import PlatformManager
    
    manager = PlatformManager()
    manager.register_node(macos)
    manager.register_node(ios)
    manager.register_node(android)
    
    status = await manager.get_node_status()
    print(f"✓ Registered {len(status)} nodes")
    
    # Get iOS nodes
    ios_nodes = manager.get_nodes_by_platform("ios")
    print(f"✓ iOS nodes: {len(ios_nodes)}")
    
    # Get nodes with camera capability
    camera_nodes = manager.get_nodes_with_capability("camera")
    print(f"✓ Nodes with camera: {len(camera_nodes)}\n")
    
    # Example 5: Gateway Setup
    print("5️⃣  Gateway Integration")
    print("-" * 60)
    print("To use platform nodes with nanobot gateway:")
    print()
    print("  Terminal 1:")
    print("    $ nanobot gateway --port 18789")
    print()
    print("  Terminal 2:")
    print("    $ nanobot platform demo")
    print()
    print("This starts all platform nodes and connects them to gateway\n")
    
    # Example 6: CLI Commands
    print("6️⃣  Available CLI Commands")
    print("-" * 60)
    print("  nanobot platform list          - List connected nodes")
    print("  nanobot platform start-macos   - Start macOS app")
    print("  nanobot platform start-ios     - Start iOS node")
    print("  nanobot platform start-android - Start Android node")
    print("  nanobot platform demo          - Start all platforms\n")
    
    # Example 7: What's Next
    print("7️⃣  What's Next?")
    print("-" * 60)
    print("✓ Run examples:")
    print("    python -m nanobot.platforms.examples")
    print()
    print("✓ Start the gateway:")
    print("    nanobot gateway")
    print()
    print("✓ Launch a platform node:")
    print("    nanobot platform start-ios --device-id my-iphone")
    print()
    print("✓ Integrate with your agent:")
    print("    from nanobot.nodes import NodeManager")
    print("    manager = NodeManager()")
    print("    node = manager.get_node('my-iphone')")
    print("    await node.snap_camera()")
    print()
    
    # Summary
    print("=" * 60)
    print("✅ Platform Nodes Setup Complete!")
    print("=" * 60)
    print()
    print("📚 Documentation:")
    print("  - nanobot/platforms/README.md")
    print("  - PLATFORMS_IMPLEMENTATION.md")
    print("  - nanobot/platforms/examples.py")
    print()


if __name__ == "__main__":
    asyncio.run(main())
