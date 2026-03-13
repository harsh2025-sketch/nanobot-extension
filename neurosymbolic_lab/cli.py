from __future__ import annotations

import argparse
import json
from pathlib import Path

from .brain import BrainConfig, NeuroSymbolicBrain


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Offline NeuroSymbolic test brain (no API key)")
    parser.add_argument("prompt", nargs="*", help="Prompt to process")
    parser.add_argument("--workspace", default=".", help="Workspace root path")
    parser.add_argument("--allow-write", action="store_true", help="Allow file writes for file tool tasks")
    parser.add_argument("--interactive", action="store_true", help="Start interactive shell")
    parser.add_argument("--json", action="store_true", help="Print result as JSON")
    return parser


def run_once(brain: NeuroSymbolicBrain, prompt: str, as_json: bool) -> int:
    res = brain.handle(prompt)
    if as_json:
        print(json.dumps({"category": res.category, "output": res.output, "actions": res.actions}, indent=2))
    else:
        print(f"[{res.category}]\n{res.output}")
        if res.actions:
            print("\nActions:")
            for action in res.actions:
                print(f"- {action}")
    return 0


def interactive_loop(brain: NeuroSymbolicBrain, as_json: bool) -> int:
    print("NeuroSymbolic Lab interactive mode. Type 'exit' to quit.")
    while True:
        try:
            prompt = input("lab> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return 0
        if not prompt:
            continue
        if prompt.lower() in {"exit", "quit"}:
            return 0
        run_once(brain, prompt, as_json)


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    workspace = Path(args.workspace).resolve()
    cfg = BrainConfig(workspace=workspace, allow_write=args.allow_write)
    brain = NeuroSymbolicBrain(cfg)

    if args.interactive:
        return interactive_loop(brain, args.json)

    if not args.prompt:
        parser.print_help()
        return 2

    prompt = " ".join(args.prompt)
    return run_once(brain, prompt, args.json)


if __name__ == "__main__":
    raise SystemExit(main())
