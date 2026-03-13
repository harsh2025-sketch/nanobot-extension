---
name: telegram-ops
description: Configure and validate Telegram channel operations.
---

# Telegram Ops

Use this skill when user wants Telegram setup, diagnostics, or safe rollout.

## Setup Checklist

1. Enable Telegram and set bot token in config.
2. Optionally set `allow_from` allowlist for private access.
3. Start gateway and verify Telegram appears in enabled channels.
4. Send `/start` to bot and confirm message routing.

## Quick Validation

- Check config has `channels.telegram.enabled=true`.
- Check token is non-empty.
- Confirm gateway logs mention Telegram channel started.
- Send a short prompt and confirm agent reply reaches Telegram.

## Safety

- Prefer allowlist for production bots.
- Rotate token if it was exposed.
- Use least-privilege bot permissions.
