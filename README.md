# nanobot Extension

UltraBot Extension is a local-first AI assistant project that works through CLI, Web UI, and chat platforms.

## What You Get

- Local neurosymbolic brain for offline tasks (no API key required)
- Web UI at `http://127.0.0.1:18792`
- CLI commands via `ultrabot` and `nanobot` (backward compatibility)
- Multi-channel support: Telegram, Discord, Slack, WhatsApp, Matrix, Email, Teams, Signal, iMessage, and more

## Quick Start (Any Device)

1. Install Python 3.11+
2. Create and activate a virtual environment
3. Install project in editable mode
4. Run onboarding once
5. Start gateway (Web UI + channels)

## Windows

```powershell
cd d:\sem6_mini_project\nanobot
py -3.11 -m venv venv311
.\venv311\Scripts\activate
python -m pip install -U pip
python -m pip install -e .
$env:NANOBOT_CONFIG_PATH = "d:\sem6_mini_project\nanobot\config.json"
ultrabot onboard
ultrabot gateway --verbose
```

Open: `http://127.0.0.1:18792`

## Linux / macOS

```bash
cd /path/to/nanobot
python3 -m venv venv311
source venv311/bin/activate
python -m pip install -U pip
python -m pip install -e .
export NANOBOT_CONFIG_PATH="$(pwd)/config.json"
ultrabot onboard
ultrabot gateway --verbose
```

Open: `http://127.0.0.1:18792`

## CLI Usage

```bash
ultrabot --help
ultrabot status
ultrabot agent -m "who are you"
ultrabot agent
```

## Web UI Usage

1. Start gateway: `ultrabot gateway --verbose`
2. Open browser: `http://127.0.0.1:18792`
3. Type commands in chat input

Useful test commands:

- `/help`
- `launch app: notepad`
- `take screenshot`
- `memory usage`
- `check port: 5432`
- `service status: Spooler`

## Chat Platforms (Gateway Mode)

1. Enable channel in `config.json` under `channels`
2. Fill required token/credentials
3. Set `allowFrom` properly (`["*"]` for open testing or explicit IDs)
4. Run: `ultrabot gateway`

Example checklist per platform:

- Telegram: `channels.telegram.enabled = true`, set `token`, set `allowFrom`
- Discord: `channels.discord.enabled = true`, set `token`, set `allowFrom`
- Slack: set bot/app tokens and mode
- WhatsApp: run `ultrabot channels login` if bridge setup is needed

## Local Brain Tasks

UltraBot local brain supports system, file, process, and network operations, including:

- App launch and file execution
- Clipboard read/write
- Screenshot capture
- CPU/RAM/system info
- Process control (kill/details)
- Port and service checks
- Wi-Fi profile listing
- Public IP and network ping
- File utilities (search/compare/zip/checksum)

## Troubleshooting

- If Web UI not opening:
  - Ensure gateway is running and shows `Control UI: http://127.0.0.1:18792`
  - Check local firewall for ports `18791` and `18792`
- If channels fail:
  - Verify token values in `config.json`
  - Ensure `allowFrom` is not empty for enabled channels
- If command not found:
  - Re-run `python -m pip install -e .`

## Notes

- Internal Python package name remains `nanobot` for compatibility.
- CLI brand is UltraBot, and both `ultrabot` and `nanobot` launchers are supported.
