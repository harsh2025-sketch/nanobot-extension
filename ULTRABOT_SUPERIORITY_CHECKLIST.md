# UltraBot Superiority Checklist

This checklist defines what UltraBot must contain to be at least equal to original nanobot and clearly superior.

## A) Nanobot Parity Baseline (Must Have)

- [x] Core agent loop, tools, sessions, memory, providers present
- [x] CLI supports onboard, agent, gateway, status, channels
- [x] Web + chat channel architecture preserved
- [x] Original channel modules retained or restored
- [x] Config schema supports legacy channel sections
- [x] Backward-compatible launcher remains available (`nanobot`)
- [x] Runtime templates (SOUL/TOOLS/USER/HEARTBEAT) still generated

Parity audit snapshot:
- Original package Python files: 64
- UltraBot package Python files: 112
- Missing original Python files in UltraBot: 0
- Added Python files in UltraBot: 48

## B) UltraBot Superiority Features (Must Exceed)

- [x] Local neurosymbolic brain integrated for offline operation
- [x] Local-brain-first routing in direct user message path
- [x] Modern Web UI with session sidebar and markdown rendering
- [x] Rich local automation tasks (apps/files/process/screenshot/clipboard)
- [x] Network and diagnostics tasks (ping/public ip/ports/services)
- [x] Expanded platform/channel support beyond baseline
- [x] i18n language detection subsystem included
- [x] Extra modules for routing, plugins, automation, browser, nodes

## C) Identity and Branding Separation (User-facing)

- [x] Help text uses UltraBot branding
- [x] Gateway startup text uses UltraBot branding
- [x] Status command uses UltraBot branding
- [x] Telegram /start and /help responses use UltraBot branding
- [x] SOUL identity set to UltraBot in template and workspace

Notes:
- Internal Python package/import path remains `nanobot` for compatibility.
- CLI entry points support both `ultrabot` and `nanobot`.

## D) Runtime Validation Checklist

### D1. Syntax and Build
- [x] Key runtime files compile successfully (`py_compile`)

### D2. CLI
- [x] `status` command runs and reports configuration
- [x] `agent` command responds to local queries
- [x] `quickstart` command initializes config/workspace via CLI
- [x] `selftest` command validates local critical paths

### D3. Web UI
- [x] WebSocket endpoint listens on configured control UI port
- [x] HTTP control UI serves successfully
- [x] `/help` response returns UltraBot command list

### D4. Local Brain Task Validation
- [x] `cpu info`
- [x] `memory usage`
- [x] `take screenshot`
- [x] `public ip`
- [x] `check port: <port>`
- [x] `service status: <name>`
- [x] `launch app: notepad`

### D5. Channel Validation
- [x] Telegram CLI setup command available (`channels telegram-setup`)
- [x] Telegram readiness validator available (`channels telegram-check`)
- [x] Discord CLI setup command available (`channels discord-setup`)
- [x] Discord readiness validator available (`channels discord-check`)
- [ ] Telegram live E2E message exchange validated with real bot token
- [ ] Discord live E2E message exchange validated with real bot token

## E) Multi-Platform Setup Coverage (Any Device)

- [x] Windows setup documented
- [x] Linux setup documented
- [x] macOS setup documented
- [x] Web UI runbook included
- [x] CLI runbook included
- [x] Channel enablement checklist included

## F) Recommended Ongoing Quality Gate (Keep Superior)

- [ ] Add automated regression tests for local brain commands
- [ ] Add end-to-end tests for at least Telegram + Discord channels
- [ ] Add CI smoke test for gateway startup + control UI ports
- [ ] Add release checklist for branding and compatibility checks

---

## Fast Verification Commands

Windows PowerShell:

```powershell
cd d:\sem6_mini_project\nanobot
$env:NANOBOT_CONFIG_PATH = "d:\sem6_mini_project\nanobot\config.json"
.\venv311\Scripts\python.exe -m py_compile nanobot\agent\loop.py nanobot\cli\commands.py neurosymbolic_lab\brain.py
.\venv311\Scripts\python.exe -m nanobot.cli.commands quickstart --no-open-ui
.\venv311\Scripts\python.exe -m nanobot.cli.commands status
.\venv311\Scripts\python.exe -m nanobot.cli.commands selftest
.\venv311\Scripts\python.exe -m nanobot.cli.commands gateway --verbose
```

Telegram enable + check:

```powershell
.\venv311\Scripts\python.exe -m nanobot.cli.commands channels telegram-setup --token "<BOT_TOKEN>" --allow-from all --enable
.\venv311\Scripts\python.exe -m nanobot.cli.commands channels telegram-check
```

Discord enable + check:

```powershell
.\venv311\Scripts\python.exe -m nanobot.cli.commands channels discord-setup --token "<BOT_TOKEN>" --allow-from all --enable
.\venv311\Scripts\python.exe -m nanobot.cli.commands channels discord-check
```
