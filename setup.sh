#!/bin/bash

# UltraBot one-go setup for macOS & Linux (offline-first)
# Usage:
#   ./setup.sh         -> setup + config alignment
#   ./setup.sh --run   -> setup + config alignment + start gateway

set -euo pipefail

echo
echo "============================================================"
echo "   >>> ULTRABOT ONE-GO SETUP FOR macOS & LINUX <<<"
echo "============================================================"
echo

echo "[1/7] Checking Python..."
if ! command -v python3 >/dev/null 2>&1; then
  echo "ERROR: python3 not found. Install Python 3.11+"
  exit 1
fi
python3 --version
echo

VENV_DIR="venv311"
PY_EXE="$VENV_DIR/bin/python"
ULTRA_EXE="$VENV_DIR/bin/ultrabot"

echo "[2/7] Creating or reusing ${VENV_DIR}..."
if [ ! -x "$PY_EXE" ]; then
  python3 -m venv "$VENV_DIR"
fi
echo "OK venv ready at ${VENV_DIR}"
echo

echo "[3/7] Activating ${VENV_DIR}..."
# shellcheck disable=SC1091
source "$VENV_DIR/bin/activate"
echo "OK venv activated"
echo

echo "[4/7] Installing UltraBot in editable mode..."
"$PY_EXE" -m pip install -U pip >/dev/null 2>&1 || true
"$PY_EXE" -m pip install -e .
echo "OK installation complete"
echo

CFG_FILE="$HOME/.nanobot/config.json"
echo "[5/7] Ensuring global config exists..."
if [ ! -f "$CFG_FILE" ]; then
  "$ULTRA_EXE" onboard
fi
echo "OK config path: $CFG_FILE"
echo

echo "[6/7] Aligning config for offline-first startup..."
"$PY_EXE" - <<'PY'
import json
from pathlib import Path

cfg_path = Path.home() / ".nanobot" / "config.json"
cfg = json.loads(cfg_path.read_text(encoding="utf-8"))

agents = cfg.setdefault("agents", {})
defaults = agents.setdefault("defaults", {})
defaults["providerTimeoutSeconds"] = 2

providers = cfg.get("providers", {})

def has_api_key(data: dict) -> bool:
    for _, v in data.items():
        if isinstance(v, dict) and str(v.get("apiKey", "")).strip():
            return True
    return False

if not has_api_key(providers):
    try:
        import httpx
        resp = httpx.get("http://127.0.0.1:11434/api/tags", timeout=1.5)
        if resp.status_code == 200:
            payload = resp.json() if resp.content else {}
            models = payload.get("models") or []
            if models:
                first = str(models[0].get("name", "")).strip()
                if first:
                    defaults["model"] = first
    except Exception:
        pass

cfg_path.write_text(json.dumps(cfg, indent=2), encoding="utf-8")
print(f"OK model={defaults.get('model')} providerTimeoutSeconds={defaults.get('providerTimeoutSeconds')}")
PY
echo

echo "[7/7] Verifying CLI health..."
export NANOBOT_CONFIG_PATH="$CFG_FILE"
"$ULTRA_EXE" status
echo

echo "============================================================"
echo "   SETUP COMPLETE"
echo "============================================================"
echo "Config: $CFG_FILE"
echo
echo "Run now:"
echo "  export NANOBOT_CONFIG_PATH=$CFG_FILE"
echo "  ultrabot gateway --verbose"
echo
echo "Quick checks:"
echo "  ultrabot channels status"
echo "  ultrabot channels telegram-check"
echo "  ultrabot channels discord-check"
echo

if [ "${1:-}" = "--run" ]; then
  echo "Starting gateway now..."
  for p in 18790 18791 18792; do
    lsof -ti tcp:"$p" 2>/dev/null | xargs -r kill -9 || true
  done
  "$ULTRA_EXE" gateway --verbose
fi
