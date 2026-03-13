"""
ultrabot Platforms: Native Apps for macOS, iOS, and Android

This module adds native companion apps for ultrabot, enabling:
- macOS menu bar app for quick access and notifications
- iOS app with Voice Wake, Talk Mode, Canvas, and camera support
- Android app with screen recording, SMS, and more

## Architecture

Each platform consists of:

1. **Platform Node** (`base.py`): Base class for all platform nodes
   - WebSocket connection to gateway
   - Command execution framework
   - Event handling system
   - Cross-platform messaging

2. **Platform-Specific Implementations**:
   - **macOS** (`macos/`): Menu bar app with notifications and system integration
   - **iOS** (`ios/`): iPhone app with voice and camera features
   - **Android** (`android/`): Android phone app with SMS and screen recording

3. **Gateway Integration** (`gateway.py`): WebSocket server for managing connections
4. **Platform Manager** (`manager.py`): Coordinates multiple nodes

## Quick Start

### macOS Menu Bar App

```python
from ultrabot.platforms.macos import create_macos_menubar

app = await create_macos_menubar()
await app.initialize()
await app.connect()
```

### iOS Node

```python
from ultrabot.platforms.ios import create_ios_node

node = await create_ios_node(device_id="iphone-1")
await node.initialize()
await node.connect()
```

### Android Node

```python
from ultrabot.platforms.android import create_android_node

node = await create_android_node(device_id="android-1")
await node.initialize()
await node.connect()
```

## Features

### macOS Menu Bar App
- Quick status indicator
- Notifications
- System command execution
- Talk Mode overlay
- Voice Wake support
- Canvas rendering
- Auto-start on login

### iOS Node
- Camera snap/video recording
- Voice Wake (always-on listening)
- Talk Mode overlay
- Canvas support
- Location tracking
- App-level notifications
- Bonjour pairing

### Android Node
- Rear/front camera
- Screen recording
- Talk Mode overlay
- Canvas support
- Location tracking
- SMS messaging
- System notifications
- Screen recording with audio

## Commands

```bash
# List all connected nodes
ultrabot platform list

# Start macOS menu bar app
ultrabot platform start-macos

# Start iOS node
ultrabot platform start-ios --device-id iphone-1

# Start Android node
ultrabot platform start-android --device-id android-1

# Run demo with all platforms
ultrabot platform demo
```

## Gateway Configuration

The platform gateway runs on `ws://127.0.0.1:18789` by default.

To use custom port:
```bash
ultrabot gateway --port 18789
```

## Development

### Adding a New Platform

1. Create subdirectory: `platforms/<platform_name>/`
2. Implement `PlatformNode` subclass
3. Register with `PlatformManager`
4. Add CLI commands in `cli/platform_commands.py`

### Platform Node Interface

```python
class YourPlatformNode(PlatformNode):
    async def initialize(self) -> bool:
        # Setup platform-specific features
        pass
    
    async def get_capabilities(self) -> list[str]:
        # Return available capabilities
        pass
    
    async def execute_command(self, command: str, args: dict) -> dict:
        # Handle incoming commands
        pass
```

## WebSocket Protocol

### Handshake

```json
{
  "type": "handshake",
  "node_id": "macos-menubar",
  "timestamp": "2026-02-19T...",
  "payload": {
    "platform": "macos",
    "device_name": "MacBook Pro",
    "capabilities": ["notifications", "system_run", "canvas"],
    "version": "1.0"
  }
}
```

### Command

```json
{
  "type": "command",
  "node_id": "ios-node-1",
  "message_id": "msg_123",
  "timestamp": "2026-02-19T...",
  "payload": {
    "command": "camera_snap",
    "args": {"camera": "rear"}
  }
}
```

### Response

```json
{
  "type": "response",
  "message_id": "msg_123",
  "node_id": "ios-node-1",
  "timestamp": "2026-02-19T...",
  "payload": {
    "success": true,
    "image_data": "...",
    "format": "jpeg"
  }
}
```

### Event

```json
{
  "type": "event",
  "node_id": "ios-node-1",
  "timestamp": "2026-02-19T...",
  "payload": {
    "event": "camera_active",
    "status": "recording"
  }
}
```

## Capabilities Reference

- `CAMERA`: Take snapshots and record video
- `SCREEN_RECORD`: Record screen activity
- `VOICE_WAKE`: Always-on listening
- `TALK_MODE`: Interactive overlay mode
- `CANVAS`: Render UI on device
- `NOTIFICATIONS`: Send notifications
- `LOCATION`: Get device location
- `SYSTEM_RUN`: Execute system commands
- `SMS`: Send SMS messages (Android only)

## Troubleshooting

### Node not connecting
- Check gateway is running: `ultrabot gateway`
- Verify WebSocket URL in config
- Check network connectivity

### Commands timing out
- Increase timeout in `PlatformConfig`
- Check node is properly initialized
- Review gateway logs

### Missing capabilities
- Not all features available on all platforms
- Check `get_capabilities()` response
- Some features require permissions

## Future Enhancements

- [ ] Plugin system for extending platforms
- [ ] Persistent state management
- [ ] Media streaming optimization
- [ ] Advanced gesture recognition
- [ ] Cross-platform synchronization
- [ ] Hardware acceleration support
- [ ] Advanced authentication (biometric, etc.)
- [ ] Native app stores integration


