import json
from pathlib import Path


def main() -> int:
    cfg_path = Path.home() / ".nanobot" / "config.json"
    if not cfg_path.exists():
        print(f"ERROR: config not found at {cfg_path}")
        return 1

    cfg = json.loads(cfg_path.read_text(encoding="utf-8"))

    agents = cfg.setdefault("agents", {})
    defaults = agents.setdefault("defaults", {})
    defaults["providerTimeoutSeconds"] = 2

    providers = cfg.get("providers", {})
    has_api_key = any(
        isinstance(v, dict) and str(v.get("apiKey", "")).strip()
        for v in providers.values()
    )

    if not has_api_key:
        try:
            import httpx

            resp = httpx.get("http://127.0.0.1:11434/api/tags", timeout=2)
            if resp.status_code == 200:
                payload = resp.json() if resp.content else {}
                models = payload.get("models") or []
                if models:
                    model_name = str(models[0].get("name", "")).strip()
                    if model_name:
                        defaults["model"] = model_name
        except Exception:
            # Keep config usable even when Ollama is unavailable.
            pass

    cfg_path.write_text(json.dumps(cfg, indent=2), encoding="utf-8")
    print(
        "OK model={} providerTimeoutSeconds={}".format(
            defaults.get("model"), defaults.get("providerTimeoutSeconds")
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
