# UltraBot Final Setup Guide

This guide is the final, stable setup path for this project. Follow it exactly for a clean first run.

## 1. Prerequisites

- Python 3.11 or newer
- Git
- Internet access for package installation and optional API/channels

Optional:

- Node.js for WhatsApp bridge workflows

## 2. Fresh Install

### Windows (recommended for this workspace)

```powershell
cd d:\sem6_mini_project\nanobot
py -3.11 -m venv venv311
.\venv311\Scripts\activate
python -m pip install --upgrade pip
python -m pip install -e .
```

### Linux/macOS

```bash
cd /path/to/nanobot
python3 -m venv venv311
source venv311/bin/activate
python -m pip install --upgrade pip
python -m pip install -e .
```

## 3. Use Project Local Config

### Windows

```powershell
$env:NANOBOT_CONFIG_PATH = "d:\sem6_mini_project\nanobot\config.json"
$env:PYTHONUTF8 = "1"
```

### Linux/macOS

```bash
export NANOBOT_CONFIG_PATH="$(pwd)/config.json"
export PYTHONUTF8=1
```

## 4. One-Time Initialization

```bash
ultrabot quickstart --no-open-ui
```

Alternative:

```bash
ultrabot onboard
```

## 5. Start Gateway + Control UI

```bash
ultrabot gateway --verbose --ui --ui-host 127.0.0.1 --ui-port 18792 --port 18790
```

Expected behavior:

- Gateway port: 18790
- Control UI WebSocket server: 18792
- Control UI HTTP page: 18793

Open browser:

- http://127.0.0.1:18793

Health check:

```bash
curl http://127.0.0.1:18793/api/health
```

## 6. Runtime Mode Selection (New UI)

In the sidebar Runtime Control panel, choose one mode:

- hybrid: default, current safe behavior
- local-llm: direct local model path
- neurosymbolic: local symbolic fallback path
- api: external OpenAI-compatible API path

For api mode, fill:

- API Base
- Model
- API Key

Then click Save Config, then Test API Config.

## 7. Smoke Test Commands

Run these from the Web UI chat box:

- /help
- memory usage
- cpu info
- public ip
- check port: 18790
- service status: Spooler

## 8. Channel Setup (Optional)

Telegram:

```bash
ultrabot channels telegram-setup --token "<BOT_TOKEN>" --allow-from all --enable
ultrabot channels telegram-check
```

Discord:

```bash
ultrabot channels discord-setup --token "<BOT_TOKEN>" --allow-from all --enable
ultrabot channels discord-check
```

Important: do not leave allowFrom empty on enabled channels.

## 9. Troubleshooting

- ultrabot command not found:
  - run python -m pip install -e .
- UI page does not load:
  - verify gateway process is running
  - verify http://127.0.0.1:18793/api/health
- API mode fails:
  - check API Base and Model
  - verify API key is valid
  - click Test API Config in Runtime Control

## 10. Project Freeze (Final)

This project is now considered final for setup and runtime flow.

Freeze policy:

- Keep command/port defaults documented above unchanged
- Treat Runtime Control behavior as stable contract
- Only allow critical bug fixes and security fixes
- Do not introduce breaking CLI/UI changes without versioned migration notes

Recommended final baseline check:

```bash
python -m py_compile nanobot\web\control_ui.py nanobot\agent\loop.py nanobot\agent\memory.py
python -m pytest tests\test_loop_quick_responses.py tests\test_loop_recent_file_followup.py -q
```
