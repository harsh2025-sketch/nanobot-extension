from __future__ import annotations

import json
import os
import platform
import re
import shutil
import socket
import subprocess
import hashlib
import base64
import csv
import random
import uuid
import zipfile
import ast
import operator
import webbrowser
import mimetypes
import tempfile
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Callable
from urllib.request import Request, urlopen
import xml.etree.ElementTree as ET


def sys_python() -> str:
    """Return the path to the currently running Python interpreter."""
    import sys as _sys
    return _sys.executable or "python"


@dataclass
class BrainConfig:
    workspace: Path
    allow_write: bool = False
    max_file_preview: int = 5
    enable_experience_learning: bool = True
    max_experiences: int = 2000


@dataclass
class BrainResponse:
    category: str
    output: str
    actions: list[str] = field(default_factory=list)


class NeuroSymbolicBrain:
    """Rule-based + symbolic local engine for offline testing prompts."""

    def __init__(self, config: BrainConfig):
        self.config = config
        self.workspace = config.workspace
        self._experience_path = self.workspace / "memory" / "brain_experience.jsonl"
        self._experience_index: dict[str, str] = {}
        self.state = {
            "thinking": "medium",
            "verbose": False,
            "usage": "tokens",
            "session_started": datetime.now().isoformat(),
            "messages": 0,
        }
        self._load_experiences()

    @staticmethod
    def _normalize_prompt(prompt: str) -> str:
        return " ".join(prompt.strip().lower().split())

    def _load_experiences(self) -> None:
        if not self.config.enable_experience_learning:
            return
        if not self._experience_path.exists():
            return
        try:
            for line in self._experience_path.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if not line:
                    continue
                rec = json.loads(line)
                key = str(rec.get("prompt", "")).strip()
                output = str(rec.get("output", "")).strip()
                if key and output:
                    self._experience_index[key] = output
        except Exception:
            return

    def _recall_experience(self, prompt: str) -> str | None:
        if not self.config.enable_experience_learning:
            return None
        key = self._normalize_prompt(prompt)
        return self._experience_index.get(key)

    def _store_experience(self, prompt: str, response: BrainResponse) -> None:
        if not self.config.enable_experience_learning:
            return
        key = self._normalize_prompt(prompt)
        output = (response.output or "").strip()
        if len(key) < 8 or not output:
            return
        if len(output) > 1500:
            output = output[:1500] + "..."
        if self._experience_index.get(key) == output:
            return

        self._experience_index[key] = output
        if len(self._experience_index) > self.config.max_experiences:
            oldest_key = next(iter(self._experience_index.keys()))
            self._experience_index.pop(oldest_key, None)

        try:
            self._experience_path.parent.mkdir(parents=True, exist_ok=True)
            with self._experience_path.open("a", encoding="utf-8") as fh:
                fh.write(json.dumps({
                    "prompt": key,
                    "output": output,
                    "category": response.category,
                    "ts": datetime.now().isoformat(),
                }) + "\n")
        except Exception:
            return

    def _finalize_response(self, prompt: str, response: BrainResponse) -> BrainResponse:
        self._store_experience(prompt, response)
        return response

    def handle(self, prompt: str) -> BrainResponse:
        self.state["messages"] += 1
        p = prompt.strip()
        low = p.lower()

        remembered = self._recall_experience(p)
        if remembered:
            return BrainResponse(
                category="memory",
                output="[Learned from experience]\n" + remembered,
            )

        if low.startswith("/"):
            return self._finalize_response(p, self._handle_command(low))

        if any(marker in low for marker in ["api not available", "api unavailable", "offline mode", "no api key", "fallback mode"]):
            return self._finalize_response(p, self._task_api_fallback(p))

        handlers: list[tuple[str, Callable[[str], BrainResponse]]] = [
            ("list files", self._task_list_files),
            ("show files", self._task_list_files),
            ("list workspace files", self._task_list_files),
            ("list files in current workspace", self._task_list_files),
            ("find all references to 'openrouter'", self._task_find_openrouter),
            ("create test_plan.md", self._task_create_test_plan),
            ("update how_to_use.md", self._task_update_how_to_use),
            ("search for todo/fixme", self._task_find_todo_fixme),
            ("show system info", self._task_system_info),
            ("show disk usage", self._task_disk_usage),
            ("show running processes", self._task_processes),
            ("show environment variables", self._task_env_vars),
            ("show network info", self._task_network_info),
            ("current date and time", self._task_datetime_now),
            ("list largest files", self._task_largest_files),
            ("count lines in project", self._task_count_lines),
            ("find duplicate filenames", self._task_duplicate_names),
            ("search text in files", self._task_search_text),
            ("read file", self._task_read_file),
            ("create note", self._task_create_note),
            ("append note", self._task_append_note),
            ("generate password", self._task_generate_password),
            ("hash text sha256", self._task_hash_sha256),
            ("base64 encode", self._task_base64_encode),
            ("base64 decode", self._task_base64_decode),
            ("json pretty", self._task_json_pretty),
            ("calculate", self._task_calculate),
            ("generate uuid", self._task_generate_uuid),
            ("random number", self._task_random_number),
            ("word count", self._task_word_count),
            ("sort lines", self._task_sort_lines),
            ("unique lines", self._task_unique_lines),
            ("count files by extension", self._task_count_files_by_ext),
            ("show directory tree", self._task_directory_tree),
            ("find empty directories", self._task_find_empty_dirs),
            ("find recent files", self._task_recent_files),
            ("checksum file sha256", self._task_checksum_file),
            ("compare files", self._task_compare_files),
            ("csv summary", self._task_csv_summary),
            ("create folder", self._task_create_folder),
            ("copy file", self._task_copy_file),
            ("move file", self._task_move_file),
            ("delete file", self._task_delete_file),
            ("zip folder", self._task_zip_folder),
            ("unzip file", self._task_unzip_file),
            ("run command", self._task_run_command),
            ("find today’s top 5 ai news", self._task_ai_news),
            ("find today's top 5 ai news", self._task_ai_news),
            ("compare openrouter free models", self._task_compare_free_models),
            ("fetch openrouter privacy settings", self._task_openrouter_privacy),
            ("best practices for telegram bot security", self._task_telegram_security),
            ("python logging and asyncio docs", self._task_python_docs),
            ("introduce yourself in 3 lines", self._task_intro),
            ("explain async vs sync", self._task_async_sync),
            ("summarize this text in 5 bullets", self._task_summarize),
            ("rewrite this in professional tone", self._task_rewrite_professional),
            ("translate this to hindi", self._task_translate_hindi),
            ("make a 7-day plan to learn python", self._task_python_7_day_plan),
            ("create a daily timetable", self._task_daily_timetable),
            ("give me pomodoro plan", self._task_pomodoro),
            ("turn this syllabus into a revision checklist", self._task_revision_checklist),
            ("generate 20 interview questions on oop", self._task_oop_questions),
            ("write python code for binary search", self._task_binary_search),
            ("refactor this code", self._task_refactor),
            ("find bugs in this snippet", self._task_find_bugs),
            ("create a fastapi crud app", self._task_fastapi_crud),
            ("generate a regex for email", self._task_regex_email_phone),
            ("i got this error", self._task_error_root_cause),
            ("why is this code slow", self._task_perf_debug),
            ("add logging and exception handling", self._task_add_logging),
            ("convert this blocking code to async", self._task_blocking_to_async),
            ("write unit tests for this function", self._task_unit_tests),
            ("read this readme and create a quick-start", self._task_quickstart),
            ("draft release notes", self._task_release_notes),
            ("write a contributing.md", self._task_contributing),
            ("create a troubleshooting section", self._task_troubleshooting),
            ("generate a deployment checklist", self._task_deploy_checklist),
            # ── System automation ──────────────────────────────────────────
            ("launch app", self._task_launch_app),
            ("open app", self._task_launch_app),
            ("start app", self._task_launch_app),
            ("run app", self._task_launch_app),
            ("open program", self._task_launch_app),
            ("start program", self._task_launch_app),
            ("launch program", self._task_launch_app),
            ("open notepad", self._task_launch_app),
            ("open calculator", self._task_launch_app),
            ("open chrome", self._task_launch_app),
            ("open firefox", self._task_launch_app),
            ("open vscode", self._task_launch_app),
            ("open code", self._task_launch_app),
            ("open explorer", self._task_launch_app),
            ("open terminal", self._task_launch_app),
            ("open powershell", self._task_launch_app),
            ("open paint", self._task_launch_app),
            ("open word", self._task_launch_app),
            ("open excel", self._task_launch_app),
            ("run file", self._task_run_file),
            ("execute file", self._task_run_file),
            ("run script", self._task_run_file),
            ("run python", self._task_run_file),
            ("execute script", self._task_run_file),
            ("open url", self._task_open_url),
            ("open website", self._task_open_url),
            ("open browser", self._task_open_url),
            ("visit website", self._task_open_url),
            ("go to http", self._task_open_url),
            ("go to www", self._task_open_url),
            ("browse to", self._task_open_url),
            ("clipboard read", self._task_clipboard_read),
            ("read clipboard", self._task_clipboard_read),
            ("get clipboard", self._task_clipboard_read),
            ("what is in clipboard", self._task_clipboard_read),
            ("clipboard write", self._task_clipboard_write),
            ("copy to clipboard", self._task_clipboard_write),
            ("write to clipboard", self._task_clipboard_write),
            ("set clipboard", self._task_clipboard_write),
            ("list windows", self._task_list_windows),
            ("show windows", self._task_list_windows),
            ("list open windows", self._task_list_windows),
            ("what windows are open", self._task_list_windows),
            ("kill process", self._task_kill_process),
            ("stop process", self._task_kill_process),
            ("end process", self._task_kill_process),
            ("terminate process", self._task_kill_process),
            ("kill app", self._task_kill_process),
            ("take screenshot", self._task_screenshot),
            ("capture screen", self._task_screenshot),
            ("screenshot", self._task_screenshot),
            ("print screen", self._task_screenshot),
            ("show memory usage", self._task_memory_usage),
            ("memory usage", self._task_memory_usage),
            ("ram usage", self._task_memory_usage),
            ("check memory", self._task_memory_usage),
            ("rename file", self._task_rename_file),
            ("open file with", self._task_open_file_with_default),
            ("open this file", self._task_open_file_with_default),
            ("show file in explorer", self._task_open_file_with_default),
            ("cpu usage", self._task_cpu_info),
            ("cpu info", self._task_cpu_info),
            ("processor info", self._task_cpu_info),
            ("show cpu", self._task_cpu_info),
            ("list installed apps", self._task_list_installed_apps),
            ("installed programs", self._task_list_installed_apps),
            ("installed software", self._task_list_installed_apps),
            ("set volume", self._task_set_volume),
            ("volume up", self._task_set_volume),
            ("volume down", self._task_set_volume),
            ("mute volume", self._task_set_volume),
            ("get active window", self._task_get_active_window),
            ("current window", self._task_get_active_window),
            ("active window", self._task_get_active_window),
            ("what is open", self._task_get_active_window),
            ("sleep", self._task_sleep_system),
            ("hibernate", self._task_sleep_system),
            ("shutdown", self._task_sleep_system),
            ("restart pc", self._task_sleep_system),
            ("lock screen", self._task_lock_screen),
            ("lock pc", self._task_lock_screen),
            ("empty recycle bin", self._task_empty_recycle),
            ("clear recycle", self._task_empty_recycle),
            ("ping", self._task_ping_host),
            ("check internet", self._task_ping_host),
            ("is internet working", self._task_ping_host),
            ("uptime", self._task_system_uptime),
            ("system uptime", self._task_system_uptime),
            ("public ip", self._task_public_ip),
            ("my ip", self._task_public_ip),
            ("external ip", self._task_public_ip),
            ("open ports", self._task_open_ports),
            ("list ports", self._task_open_ports),
            ("list listening ports", self._task_open_ports),
            ("check port", self._task_check_port),
            ("port status", self._task_check_port),
            ("process details", self._task_process_details),
            ("task details", self._task_process_details),
            ("wifi profiles", self._task_wifi_profiles),
            ("saved wifi", self._task_wifi_profiles),
            ("service status", self._task_service_status),
            ("windows service", self._task_service_status),
            ("list startup apps", self._task_startup_apps),
            ("startup programs", self._task_startup_apps),
        ]

        for marker, fn in handlers:
            if marker in low:
                return self._finalize_response(p, fn(p))

        # ── Scored semantic dispatch ──────────────────────────────────────
        scored = self._score_dispatch(p)
        if scored is not None:
            return self._finalize_response(p, scored)

        chat = self._task_general_chat(p)
        if chat is not None:
            return self._finalize_response(p, chat)

        return self._finalize_response(p, BrainResponse(
            category="fallback",
            output=(
                "🔥 UltraBot local brain active (offline / no API key).\n\n"
                "I can handle:\n"
                "• System: launch app, run file, open url, clipboard read/write, screenshot\n"
                "• Process: kill process, list windows, active window, cpu/memory usage\n"
                "• Network: ping host, public IP, open ports, check port, wifi profiles\n"
                "• Health: system uptime, process details, service status, startup apps\n"
                "• Files: list, read, create, search, copy, move, rename, zip, compare\n"
                "• Utils: calculate, hash, uuid, base64, json pretty, password generate\n"
                "• Info: system info, disk usage, processes, network info, recent files\n"
                "• Study: 7-day plan, daily timetable, pomodoro, revision checklist\n"
                "• Code: binary search, fastapi CRUD, unit tests, refactor tips, bug checklist\n\n"
                "Examples:\n"
                "  launch app: notepad\n"
                "  run file: scripts/hello.py\n"
                "  open url: https://google.com\n"
                "  clipboard read\n"
                "  take screenshot\n"
                "  kill process: chrome.exe\n"
                "  check port: 5432\n"
                "  service status: Spooler\n"
                "  calculate: (100 * 3.14) / 2"
            ),
        ))

    def _handle_command(self, cmd: str) -> BrainResponse:
        if cmd.startswith("/status"):
            return BrainResponse("command", json.dumps(self.state, indent=2))
        if cmd.startswith("/usage"):
            return BrainResponse("command", "Local mode: no remote token billing. Usage tracking = symbolic only.")
        if cmd.startswith("/think"):
            parts = cmd.split(maxsplit=1)
            self.state["thinking"] = parts[1] if len(parts) > 1 else "medium"
            return BrainResponse("command", f"Thinking level set to: {self.state['thinking']}")
        if cmd.startswith("/verbose"):
            self.state["verbose"] = "on" in cmd
            return BrainResponse("command", f"Verbose set to: {self.state['verbose']}")
        if cmd.startswith("/new") or cmd.startswith("/reset"):
            self.state["messages"] = 0
            self.state["session_started"] = datetime.now().isoformat()
            return BrainResponse("command", "New local session started.")
        if cmd.startswith("/help"):
            return BrainResponse("command", (
                "🔥 UltraBot commands:\n"
                "/status     — show session state\n"
                "/usage      — show token/usage info\n"
                "/think      — set thinking level (low/medium/high)\n"
                "/verbose on — enable verbose output\n"
                "/new        — start new session\n"
                "/help       — show this help\n\n"
                "Local tasks (no API needed):\n"
                "  launch app: notepad  |  run file: script.py\n"
                "  open url: <url>      |  clipboard read\n"
                "  take screenshot      |  kill process: <name>\n"
                "  show system info     |  memory usage\n"
                "  calculate: <expr>    |  show disk usage"
            ))
        return BrainResponse("command", "Unknown command. Use /help for available commands.")

    def _extract_after_colon(self, prompt: str) -> str:
        parts = prompt.split(":", 1)
        return parts[1].strip() if len(parts) > 1 else ""

    def _task_intro(self, _: str) -> BrainResponse:
        return BrainResponse("basic_chat", "🔥 I am UltraBot — a local neurosymbolic brain.\nI run without API keys and use symbolic rules + system tools.\nI can launch apps, run files, open URLs, take screenshots, manage clipboard, generate plans, code templates, and execute workspace actions offline.")

    def _task_async_sync(self, _: str) -> BrainResponse:
        out = (
            "Sync: tasks run one-by-one; each task waits for previous to finish.\n"
            "Async: tasks can pause while waiting (I/O) so others continue.\n"
            "Use sync for simple CPU logic, async for network/file/chat workloads."
        )
        return BrainResponse("basic_chat", out)

    def _task_summarize(self, prompt: str) -> BrainResponse:
        text = self._extract_after_colon(prompt)
        if not text:
            return BrainResponse("basic_chat", "Provide text after ':' to summarize.")
        sentences = re.split(r"(?<=[.!?])\s+", text)
        bullets = [f"- {s.strip()}" for s in sentences[:5] if s.strip()]
        return BrainResponse("basic_chat", "\n".join(bullets) if bullets else "- No clear sentences found.")

    def _task_rewrite_professional(self, prompt: str) -> BrainResponse:
        text = self._extract_after_colon(prompt)
        if not text:
            return BrainResponse("basic_chat", "Provide text after ':' to rewrite.")
        cleaned = re.sub(r"\b(gonna|wanna|kinda|sorta)\b", "", text, flags=re.I)
        cleaned = re.sub(r"\s+", " ", cleaned).strip()
        return BrainResponse("basic_chat", f"Professional rewrite:\n{cleaned}")

    def _task_translate_hindi(self, prompt: str) -> BrainResponse:
        text = self._extract_after_colon(prompt)
        if not text:
            return BrainResponse("basic_chat", "Provide text after ':' to translate.")
        return BrainResponse("basic_chat", f"[Hindi draft]\n{text}\n\nNote: local mode uses template translation; for perfect Hindi, use a translation model.")

    def _task_python_7_day_plan(self, _: str) -> BrainResponse:
        plan = [
            "Day 1: Python syntax, variables, data types (2h)",
            "Day 2: Conditions + loops + functions (2h)",
            "Day 3: Lists/dicts/sets/tuples + exercises (2h)",
            "Day 4: OOP basics + classes (2h)",
            "Day 5: Files, exceptions, modules (2h)",
            "Day 6: Mini project (CLI todo or calculator) (2h)",
            "Day 7: Revision + coding quiz + improvements (2h)",
        ]
        return BrainResponse("study", "\n".join(f"- {p}" for p in plan))

    def _task_daily_timetable(self, _: str) -> BrainResponse:
        return BrainResponse("study", "- 07:00-08:00: Review\n- 10:00-12:00: Project work\n- 14:00-15:00: Exam prep\n- 18:00-19:00: Revision\n- 21:00-21:30: Plan next day")

    def _task_pomodoro(self, _: str) -> BrainResponse:
        return BrainResponse("study", "8 Pomodoros: [25m focus + 5m break] x4, 20m long break, then repeat x4.")

    def _task_revision_checklist(self, prompt: str) -> BrainResponse:
        text = self._extract_after_colon(prompt)
        topics = [t.strip(" -") for t in re.split(r"[\n,;]", text) if t.strip()]
        if not topics:
            return BrainResponse("study", "Provide syllabus text after ':'.")
        return BrainResponse("study", "\n".join(f"- [ ] {t}" for t in topics[:30]))

    def _task_oop_questions(self, _: str) -> BrainResponse:
        qs = [
            "What is encapsulation?", "What is inheritance?", "Difference between abstraction and encapsulation?",
            "What is polymorphism?", "What is method overriding?", "What is method overloading?",
            "Class vs object?", "What is constructor?", "What is composition?", "What is association?",
            "What is SOLID?", "What is interface?", "Abstract class vs interface?", "What is dependency injection?",
            "What is immutability?", "What is static method?", "What is final class?", "What is aggregation?",
            "What is multiple inheritance issue?", "What are access modifiers?",
        ]
        return BrainResponse("study", "\n".join(f"{i+1}. {q} — Short answer: <fill>" for i, q in enumerate(qs)))

    def _task_binary_search(self, _: str) -> BrainResponse:
        code = '''def binary_search(arr, target):
    left, right = 0, len(arr) - 1
    while left <= right:
        mid = (left + right) // 2
        if arr[mid] == target:
            return mid
        if arr[mid] < target:
            left = mid + 1
        else:
            right = mid - 1
    return -1


def test_binary_search():
    assert binary_search([], 1) == -1
    assert binary_search([1], 1) == 0
    assert binary_search([1, 3, 5, 7], 5) == 2
    assert binary_search([1, 3, 5, 7], 6) == -1
'''
        return BrainResponse("coding", code)

    def _task_refactor(self, prompt: str) -> BrainResponse:
        return BrainResponse("coding", "Refactor suggestions:\n- Extract small pure functions\n- Rename unclear variables\n- Remove duplicated branches\n- Add guard clauses\n- Add type hints and unit tests")

    def _task_find_bugs(self, prompt: str) -> BrainResponse:
        return BrainResponse("coding", "Bug checklist:\n- Null/None checks\n- Off-by-one loops\n- Mutable default args\n- Blocking I/O in async funcs\n- Unhandled exceptions\n- Resource leaks")

    def _task_fastapi_crud(self, _: str) -> BrainResponse:
        return BrainResponse("coding", "FastAPI CRUD template:\n- Define Pydantic models\n- SQLAlchemy engine + SessionLocal\n- Endpoints: POST/GET/PUT/DELETE\n- Return proper status codes\n- Add tests with TestClient")

    def _task_regex_email_phone(self, _: str) -> BrainResponse:
        return BrainResponse("coding", r"Email: ^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$\nPhone: ^\+?[1-9]\d{7,14}$")

    def _task_error_root_cause(self, prompt: str) -> BrainResponse:
        return BrainResponse("debug", "Root-cause workflow:\n1) Read last traceback frame\n2) Reproduce with minimal input\n3) Inspect variable assumptions\n4) Patch + add regression test")

    def _task_perf_debug(self, _: str) -> BrainResponse:
        return BrainResponse("debug", "Performance steps:\n- profile with cProfile\n- identify hot path\n- reduce nested loops\n- cache repeated I/O\n- batch network calls")

    def _task_add_logging(self, _: str) -> BrainResponse:
        return BrainResponse("debug", "Add `logger.info` at entry/exit, `logger.debug` for key vars, `try/except` with structured error context.")

    def _task_blocking_to_async(self, _: str) -> BrainResponse:
        return BrainResponse("debug", "Convert plan:\n- replace blocking libs with async equivalents\n- mark call chain as async\n- use `await` for I/O\n- keep CPU-heavy work in executor")

    def _task_unit_tests(self, _: str) -> BrainResponse:
        return BrainResponse("debug", "Unit test template:\n- happy path\n- edge cases\n- invalid input\n- exception path\n- idempotency")

    def _task_quickstart(self, _: str) -> BrainResponse:
        return BrainResponse("docs", "Quick-start in 8 steps:\n1. Install Python\n2. Create venv\n3. Install deps\n4. Configure API/model\n5. Run gateway\n6. Run agent prompt\n7. Enable channels\n8. Verify with /status")

    def _task_release_notes(self, prompt: str) -> BrainResponse:
        text = self._extract_after_colon(prompt)
        items = [i.strip(" -") for i in re.split(r"[\n;]", text) if i.strip()]
        if not items:
            return BrainResponse("docs", "Provide bullet changes after ':'.")
        return BrainResponse("docs", "Release notes:\n" + "\n".join(f"- {i}" for i in items))

    def _task_contributing(self, _: str) -> BrainResponse:
        return BrainResponse("docs", "CONTRIBUTING.md sections:\n- setup\n- branch naming\n- commit style\n- test requirements\n- PR checklist\n- code review rules")

    def _task_troubleshooting(self, _: str) -> BrainResponse:
        return BrainResponse("docs", "Troubleshooting:\n- command not found\n- wrong venv active\n- API key missing\n- model not found\n- channel token invalid")

    def _task_deploy_checklist(self, _: str) -> BrainResponse:
        return BrainResponse("docs", "Windows deploy checklist:\n- Python 3.11\n- venv active\n- config path set\n- gateway starts\n- logs monitored\n- firewall ports checked")

    def _task_list_files(self, _: str) -> BrainResponse:
        files = []
        for p in sorted(self.workspace.iterdir()):
            files.append(("[D] " if p.is_dir() else "[F] ") + p.name)
        return BrainResponse("file_tools", "\n".join(files[:200]))

    def _task_find_openrouter(self, _: str) -> BrainResponse:
        matches = []
        for path in self.workspace.rglob("*"):
            if not path.is_file() or path.suffix.lower() in {".png", ".jpg", ".jpeg", ".gif", ".exe", ".dll", ".pyc"}:
                continue
            try:
                text = path.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                continue
            if "openrouter" in text.lower():
                rel = path.relative_to(self.workspace)
                matches.append(str(rel))
        return BrainResponse("file_tools", "OpenRouter references:\n" + ("\n".join(f"- {m}" for m in matches[:200]) or "- none"))

    def _task_create_test_plan(self, _: str) -> BrainResponse:
        target = self.workspace / "TEST_PLAN.md"
        content = "# Terminal Test Plan\n\n- [ ] onboard\n- [ ] gateway start\n- [ ] agent prompt\n- [ ] /status\n- [ ] channel smoke test\n"
        if self.config.allow_write:
            target.write_text(content, encoding="utf-8")
            return BrainResponse("file_tools", f"Created {target}", actions=["write:TEST_PLAN.md"])
        return BrainResponse("file_tools", "Write blocked (allow_write=False). Would create TEST_PLAN.md.")

    def _task_update_how_to_use(self, _: str) -> BrainResponse:
        target = self.workspace / "HOW_TO_USE.md"
        if not target.exists():
            return BrainResponse("file_tools", "HOW_TO_USE.md not found.")
        marker = "## 6) Telegram setup (optional)"
        note = "\nTip: verify bot token + keep gateway running in a dedicated terminal.\n"
        text = target.read_text(encoding="utf-8", errors="ignore")
        if note.strip() in text:
            return BrainResponse("file_tools", "HOW_TO_USE.md already contains Telegram tip.")
        if self.config.allow_write:
            text = text.replace(marker, marker + note)
            target.write_text(text, encoding="utf-8")
            return BrainResponse("file_tools", "Updated HOW_TO_USE.md Telegram section.", actions=["write:HOW_TO_USE.md"])
        return BrainResponse("file_tools", "Write blocked (allow_write=False). Would update HOW_TO_USE.md.")

    def _task_find_todo_fixme(self, _: str) -> BrainResponse:
        rows = []
        for path in self.workspace.rglob("*"):
            if not path.is_file() or path.suffix.lower() in {".png", ".jpg", ".jpeg", ".gif", ".exe", ".dll", ".pyc"}:
                continue
            try:
                lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
            except Exception:
                continue
            for i, line in enumerate(lines, 1):
                ll = line.lower()
                if "todo" in ll or "fixme" in ll:
                    rows.append(f"- {path.relative_to(self.workspace)}:{i} -> {line.strip()[:120]}")
        return BrainResponse("file_tools", "TODO/FIXME:\n" + ("\n".join(rows[:300]) or "- none"))

    def _task_ai_news(self, _: str) -> BrainResponse:
        try:
            req = Request("https://news.google.com/rss/search?q=AI&hl=en-US&gl=US&ceid=US:en", headers={"User-Agent": "Mozilla/5.0"})
            with urlopen(req, timeout=12) as r:
                xml = r.read()
            root = ET.fromstring(xml)
            titles = [item.findtext("title") for item in root.findall("./channel/item")[:5]]
            lines = [f"- {t}" for t in titles if t]
            return BrainResponse("web", "Top AI news:\n" + ("\n".join(lines) or "- no headlines"))
        except Exception as e:
            return BrainResponse("web", f"Could not fetch live news (network issue): {e}")

    def _task_compare_free_models(self, _: str) -> BrainResponse:
        return BrainResponse("web", "OpenRouter free-model notes:\n- gpt-oss free: good general reasoning\n- free models can be rate limited\n- privacy settings may block endpoints\n- keep a paid fallback model configured")

    def _task_openrouter_privacy(self, _: str) -> BrainResponse:
        return BrainResponse("web", "If you see 'No endpoints found matching your data policy', open https://openrouter.ai/settings/privacy and enable policy needed for free models.")

    def _task_telegram_security(self, _: str) -> BrainResponse:
        return BrainResponse("web", "Telegram bot security:\n- rotate bot token\n- restrict allowFrom users\n- avoid logging secrets\n- validate webhook source (if used)\n- run with least privileges")

    def _task_python_docs(self, _: str) -> BrainResponse:
        return BrainResponse("web", "Docs:\n- https://docs.python.org/3/library/logging.html\n- https://docs.python.org/3/library/asyncio.html\nSummary: logging = structured diagnostics; asyncio = cooperative concurrency for I/O workloads.")

    def _task_api_fallback(self, _: str) -> BrainResponse:
        return BrainResponse(
            "fallback",
            "API fallback active: using local neurosymbolic tools only.\n"
            "Available now: general chat, study planner, coding templates, debug checklists, docs helpers, system info, disk/process/file tools, text/hash/base64/json utilities.",
        )

    def _task_general_chat(self, prompt: str) -> BrainResponse | None:
        low = prompt.lower().strip()
        if any(g in low for g in ["hello", "hi ", "hey", "good morning", "good evening", "hi!"]):
            return BrainResponse("general_chat", "🔥 Hi! I am UltraBot — your local offline assistant. I can chat normally and also run local PC tasks like launching apps, running files, taking screenshots, and much more.")
        if "how are you" in low:
            return BrainResponse("general_chat", "Running perfectly in offline mode! Tell me what you want to do — I can launch apps, run scripts, read your clipboard, or help with planning.")
        if any(g in low for g in ["thank you", "thanks"]):
            return BrainResponse("general_chat", "You're welcome! I can continue with more local tasks if you want.")
        if any(g in low for g in ["who are you", "what can you do", "what are you"]):
            return BrainResponse(
                "general_chat",
                "🔥 I am UltraBot — a superior local AI assistant.\n\n"
                "I can:\n"
                "• Launch apps (notepad, calculator, chrome, vscode, etc.)\n"
                "• Run files and scripts (.py, .bat, .exe, .html)\n"
                "• Open URLs in browser\n"
                "• Read/write clipboard\n"
                "• Take screenshots\n"
                "• Kill or list processes\n"
                "• Show system/disk/memory info\n"
                "• File operations (read, create, copy, move, zip, search)\n"
                "• Study plans, code templates, debugging checklists\n"
                "• Math calculations, UUID, hash, base64, JSON utilities\n\n"
                "All offline — no API key needed.",
            )
        if "joke" in low:
            jokes = [
                "Why do programmers prefer dark mode? Because light attracts bugs.",
                "How many programmers does it take to change a light bulb? None — that's a hardware problem.",
                "I told my computer I needed a break. Now it won't stop sending me Kit-Kat ads.",
                "A SQL query walks into a bar, walks up to two tables and asks... 'Can I join you?'",
            ]
            return BrainResponse("general_chat", random.choice(jokes))
        if "motivate" in low or "motivation" in low:
            return BrainResponse("general_chat", "💪 Small progress every day beats perfect plans that never start. Pick one 25-minute task and begin now. UltraBot is here to help you execute.")
        if "what time" in low or "what is the time" in low:
            return BrainResponse("general_chat", f"Current time: {datetime.now().strftime('%H:%M:%S')} on {datetime.now().strftime('%Y-%m-%d')}")
        if "your name" in low or "what are you called" in low:
            return BrainResponse("general_chat", "I am UltraBot 🔥 — your superior local AI assistant.")
        if "version" in low and ("your" in low or "bot" in low or "ultra" in low):
            return BrainResponse("general_chat", "UltraBot v0.2.0 — local neurosymbolic brain, offline-first, zero API dependency.")
        return None

    def _task_datetime_now(self, _: str) -> BrainResponse:
        return BrainResponse("local_pc", f"Local date/time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    def _task_system_info(self, _: str) -> BrainResponse:
        uname = platform.uname()
        out = [
            f"System: {uname.system}",
            f"Node: {uname.node}",
            f"Release: {uname.release}",
            f"Version: {uname.version}",
            f"Machine: {uname.machine}",
            f"Processor: {uname.processor or 'N/A'}",
            f"Python: {platform.python_version()}",
            f"CPU cores (logical): {os.cpu_count()}",
            f"Workspace: {self.workspace}",
        ]
        return BrainResponse("local_pc", "\n".join(f"- {x}" for x in out))

    def _task_disk_usage(self, _: str) -> BrainResponse:
        usage = shutil.disk_usage(self.workspace)
        gb = 1024 ** 3
        out = (
            f"Disk usage for {self.workspace}:\n"
            f"- Total: {usage.total / gb:.2f} GB\n"
            f"- Used: {usage.used / gb:.2f} GB\n"
            f"- Free: {usage.free / gb:.2f} GB"
        )
        return BrainResponse("local_pc", out)

    def _task_processes(self, _: str) -> BrainResponse:
        try:
            if os.name == "nt":
                proc = subprocess.run(["tasklist"], capture_output=True, text=True, timeout=15)
                lines = proc.stdout.splitlines()[:40]
                return BrainResponse("local_pc", "Running processes (top 40 lines):\n" + "\n".join(lines))
            proc = subprocess.run(["ps", "-eo", "pid,comm,%cpu,%mem"], capture_output=True, text=True, timeout=15)
            lines = proc.stdout.splitlines()[:40]
            return BrainResponse("local_pc", "Running processes (top 40 lines):\n" + "\n".join(lines))
        except Exception as e:
            return BrainResponse("local_pc", f"Could not get process list: {e}")

    def _task_env_vars(self, _: str) -> BrainResponse:
        keys = ["USERNAME", "COMPUTERNAME", "OS", "PROCESSOR_ARCHITECTURE", "PYTHONPATH", "VIRTUAL_ENV", "PATH"]
        rows = []
        for key in keys:
            val = os.environ.get(key)
            if not val:
                continue
            if key == "PATH":
                val = ";".join(val.split(";")[:6]) + ("; ..." if len(val.split(";")) > 6 else "")
            rows.append(f"- {key}={val}")
        return BrainResponse("local_pc", "Environment snapshot:\n" + ("\n".join(rows) or "- no values"))

    def _task_network_info(self, _: str) -> BrainResponse:
        try:
            host = socket.gethostname()
            ip = socket.gethostbyname(host)
            return BrainResponse("local_pc", f"Network info:\n- Hostname: {host}\n- Local IP: {ip}")
        except Exception as e:
            return BrainResponse("local_pc", f"Could not get network info: {e}")

    def _task_largest_files(self, _: str) -> BrainResponse:
        items = []
        for path in self.workspace.rglob("*"):
            if path.is_file():
                try:
                    items.append((path.stat().st_size, path.relative_to(self.workspace)))
                except Exception:
                    continue
        items.sort(reverse=True)
        top = items[:20]
        if not top:
            return BrainResponse("local_pc", "No files found.")
        out = [f"- {p} ({size / 1024:.1f} KB)" for size, p in top]
        return BrainResponse("local_pc", "Largest files:\n" + "\n".join(out))

    def _task_count_lines(self, _: str) -> BrainResponse:
        total = 0
        files = 0
        for path in self.workspace.rglob("*"):
            if not path.is_file() or path.suffix.lower() in {".png", ".jpg", ".jpeg", ".gif", ".exe", ".dll", ".pyc"}:
                continue
            try:
                lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
            except Exception:
                continue
            total += len(lines)
            files += 1
        return BrainResponse("local_pc", f"Project line count: {total} lines across {files} text files.")

    def _task_duplicate_names(self, _: str) -> BrainResponse:
        bucket: dict[str, list[Path]] = {}
        for path in self.workspace.rglob("*"):
            if path.is_file():
                bucket.setdefault(path.name.lower(), []).append(path.relative_to(self.workspace))
        dups = {name: paths for name, paths in bucket.items() if len(paths) > 1}
        if not dups:
            return BrainResponse("local_pc", "No duplicate filenames found.")
        rows = []
        for name, paths in list(dups.items())[:30]:
            rows.append(f"- {name}: {len(paths)} copies")
        return BrainResponse("local_pc", "Duplicate filenames:\n" + "\n".join(rows))

    def _task_search_text(self, prompt: str) -> BrainResponse:
        query = self._extract_after_colon(prompt).strip()
        if not query:
            query = "todo"
        matches = []
        for path in self.workspace.rglob("*"):
            if not path.is_file() or path.suffix.lower() in {".png", ".jpg", ".jpeg", ".gif", ".exe", ".dll", ".pyc"}:
                continue
            try:
                lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
            except Exception:
                continue
            for i, line in enumerate(lines, 1):
                if query.lower() in line.lower():
                    matches.append(f"- {path.relative_to(self.workspace)}:{i} -> {line.strip()[:120]}")
                    if len(matches) >= 200:
                        break
            if len(matches) >= 200:
                break
        return BrainResponse("local_pc", f"Search results for '{query}':\n" + ("\n".join(matches) if matches else "- no matches"))

    def _task_read_file(self, prompt: str) -> BrainResponse:
        path_text = self._extract_after_colon(prompt)
        if not path_text:
            return BrainResponse("local_pc", "Use: read file: relative/path.ext")
        target = (self.workspace / path_text).resolve()
        if not target.exists() or not target.is_file():
            return BrainResponse("local_pc", f"File not found: {path_text}")
        try:
            text = target.read_text(encoding="utf-8", errors="ignore")
        except Exception as e:
            return BrainResponse("local_pc", f"Could not read file: {e}")
        lines = text.splitlines()[: max(10, self.config.max_file_preview * 20)]
        return BrainResponse("local_pc", f"Preview of {target.relative_to(self.workspace)}:\n" + "\n".join(lines))

    def _task_create_note(self, prompt: str) -> BrainResponse:
        payload = self._extract_after_colon(prompt)
        if "|" not in payload:
            return BrainResponse("local_pc", "Use: create note: notes/today.txt | your content")
        rel, content = [x.strip() for x in payload.split("|", 1)]
        if not rel:
            return BrainResponse("local_pc", "Missing note file path.")
        target = (self.workspace / rel)
        if not self.config.allow_write:
            return BrainResponse("local_pc", f"Write blocked (allow_write=False). Would create {rel}.")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content + "\n", encoding="utf-8")
        return BrainResponse("local_pc", f"Created note: {target.relative_to(self.workspace)}", actions=[f"write:{rel}"])

    def _task_append_note(self, prompt: str) -> BrainResponse:
        payload = self._extract_after_colon(prompt)
        if "|" not in payload:
            return BrainResponse("local_pc", "Use: append note: notes/today.txt | extra line")
        rel, content = [x.strip() for x in payload.split("|", 1)]
        target = (self.workspace / rel)
        if not self.config.allow_write:
            return BrainResponse("local_pc", f"Write blocked (allow_write=False). Would append to {rel}.")
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("a", encoding="utf-8") as f:
            f.write(content + "\n")
        return BrainResponse("local_pc", f"Appended note: {target.relative_to(self.workspace)}", actions=[f"append:{rel}"])

    def _task_generate_password(self, _: str) -> BrainResponse:
        token = base64.urlsafe_b64encode(os.urandom(18)).decode("utf-8").rstrip("=")
        return BrainResponse("local_pc", f"Generated password/token:\n{token}")

    def _task_hash_sha256(self, prompt: str) -> BrainResponse:
        text = self._extract_after_colon(prompt)
        if not text:
            return BrainResponse("local_pc", "Use: hash text sha256: your text")
        digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
        return BrainResponse("local_pc", f"SHA256: {digest}")

    def _task_base64_encode(self, prompt: str) -> BrainResponse:
        text = self._extract_after_colon(prompt)
        if not text:
            return BrainResponse("local_pc", "Use: base64 encode: your text")
        encoded = base64.b64encode(text.encode("utf-8")).decode("utf-8")
        return BrainResponse("local_pc", encoded)

    def _task_base64_decode(self, prompt: str) -> BrainResponse:
        text = self._extract_after_colon(prompt)
        if not text:
            return BrainResponse("local_pc", "Use: base64 decode: SGVsbG8=")
        try:
            decoded = base64.b64decode(text).decode("utf-8")
            return BrainResponse("local_pc", decoded)
        except Exception as e:
            return BrainResponse("local_pc", f"Invalid base64 input: {e}")

    def _task_json_pretty(self, prompt: str) -> BrainResponse:
        text = self._extract_after_colon(prompt)
        if not text:
            return BrainResponse("local_pc", "Use: json pretty: {\"a\":1,\"b\":2}")
        try:
            obj = json.loads(text)
            return BrainResponse("local_pc", json.dumps(obj, indent=2, ensure_ascii=False))
        except Exception as e:
            return BrainResponse("local_pc", f"Invalid JSON: {e}")

    def _task_calculate(self, prompt: str) -> BrainResponse:
        expr = self._extract_after_colon(prompt)
        if not expr:
            return BrainResponse("local_pc", "Use: calculate: (12+5)*3/2")

        allowed_bin = {
            ast.Add: operator.add,
            ast.Sub: operator.sub,
            ast.Mult: operator.mul,
            ast.Div: operator.truediv,
            ast.FloorDiv: operator.floordiv,
            ast.Mod: operator.mod,
            ast.Pow: operator.pow,
        }
        allowed_unary = {ast.UAdd: operator.pos, ast.USub: operator.neg}

        def _eval(node):
            if isinstance(node, ast.Expression):
                return _eval(node.body)
            if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
                return node.value
            if isinstance(node, ast.BinOp) and type(node.op) in allowed_bin:
                return allowed_bin[type(node.op)](_eval(node.left), _eval(node.right))
            if isinstance(node, ast.UnaryOp) and type(node.op) in allowed_unary:
                return allowed_unary[type(node.op)](_eval(node.operand))
            raise ValueError("Unsupported expression")

        try:
            tree = ast.parse(expr, mode="eval")
            result = _eval(tree)
            return BrainResponse("local_pc", f"Result: {result}")
        except Exception as e:
            return BrainResponse("local_pc", f"Invalid expression: {e}")

    def _task_generate_uuid(self, _: str) -> BrainResponse:
        return BrainResponse("local_pc", f"UUID: {uuid.uuid4()}")

    def _task_random_number(self, prompt: str) -> BrainResponse:
        text = self._extract_after_colon(prompt)
        if not text:
            return BrainResponse("local_pc", f"Random number (1-100): {random.randint(1, 100)}")
        nums = re.findall(r"-?\d+", text)
        if len(nums) >= 2:
            a, b = int(nums[0]), int(nums[1])
            lo, hi = (a, b) if a <= b else (b, a)
            return BrainResponse("local_pc", f"Random number ({lo}-{hi}): {random.randint(lo, hi)}")
        return BrainResponse("local_pc", "Use: random number: 10 50")

    def _task_word_count(self, prompt: str) -> BrainResponse:
        text = self._extract_after_colon(prompt)
        if not text:
            return BrainResponse("local_pc", "Use: word count: your sentence")
        words = re.findall(r"\S+", text)
        chars = len(text)
        return BrainResponse("local_pc", f"Words: {len(words)}\nCharacters: {chars}")

    def _task_sort_lines(self, prompt: str) -> BrainResponse:
        text = self._extract_after_colon(prompt)
        if not text:
            return BrainResponse("local_pc", "Use: sort lines: c,b,a")
        lines = [x.strip() for x in re.split(r"\n|,", text) if x.strip()]
        return BrainResponse("local_pc", "\n".join(sorted(lines, key=str.lower)))

    def _task_unique_lines(self, prompt: str) -> BrainResponse:
        text = self._extract_after_colon(prompt)
        if not text:
            return BrainResponse("local_pc", "Use: unique lines: a,a,b")
        lines = [x.strip() for x in re.split(r"\n|,", text) if x.strip()]
        seen = set()
        out = []
        for line in lines:
            if line.lower() in seen:
                continue
            seen.add(line.lower())
            out.append(line)
        return BrainResponse("local_pc", "\n".join(out) if out else "No unique lines.")

    def _task_count_files_by_ext(self, _: str) -> BrainResponse:
        counts: dict[str, int] = {}
        for path in self.workspace.rglob("*"):
            if not path.is_file():
                continue
            ext = path.suffix.lower() or "[no_ext]"
            counts[ext] = counts.get(ext, 0) + 1
        rows = sorted(counts.items(), key=lambda x: x[1], reverse=True)[:40]
        return BrainResponse("local_pc", "Files by extension:\n" + "\n".join(f"- {ext}: {n}" for ext, n in rows))

    def _task_directory_tree(self, prompt: str) -> BrainResponse:
        depth = 2
        text = self._extract_after_colon(prompt)
        if text:
            nums = re.findall(r"\d+", text)
            if nums:
                depth = max(1, min(6, int(nums[0])))

        lines: list[str] = []
        root_depth = len(self.workspace.parts)
        for path in sorted(self.workspace.rglob("*")):
            rel = path.relative_to(self.workspace)
            lvl = len(path.parts) - root_depth
            if lvl > depth:
                continue
            indent = "  " * (lvl - 1)
            name = rel.name + ("/" if path.is_dir() else "")
            lines.append(f"{indent}- {name}")
            if len(lines) >= 250:
                break
        return BrainResponse("local_pc", "Directory tree:\n" + ("\n".join(lines) or "- empty"))

    def _task_find_empty_dirs(self, _: str) -> BrainResponse:
        empties = []
        for path in self.workspace.rglob("*"):
            if path.is_dir():
                try:
                    next(path.iterdir())
                except StopIteration:
                    empties.append(str(path.relative_to(self.workspace)))
                except Exception:
                    continue
        return BrainResponse("local_pc", "Empty directories:\n" + ("\n".join(f"- {x}" for x in empties[:200]) or "- none"))

    def _task_recent_files(self, prompt: str) -> BrainResponse:
        count = 20
        text = self._extract_after_colon(prompt)
        if text:
            nums = re.findall(r"\d+", text)
            if nums:
                count = max(1, min(100, int(nums[0])))
        items = []
        for path in self.workspace.rglob("*"):
            if not path.is_file():
                continue
            try:
                items.append((path.stat().st_mtime, path.relative_to(self.workspace)))
            except Exception:
                continue
        items.sort(reverse=True)
        rows = [f"- {datetime.fromtimestamp(ts).strftime('%Y-%m-%d %H:%M:%S')}  {p}" for ts, p in items[:count]]
        return BrainResponse("local_pc", "Recent files:\n" + ("\n".join(rows) if rows else "- none"))

    def _task_checksum_file(self, prompt: str) -> BrainResponse:
        rel = self._extract_after_colon(prompt)
        if not rel:
            return BrainResponse("local_pc", "Use: checksum file sha256: path/to/file")
        target = (self.workspace / rel).resolve()
        if not target.exists() or not target.is_file():
            return BrainResponse("local_pc", f"File not found: {rel}")
        h = hashlib.sha256()
        try:
            with target.open("rb") as f:
                while chunk := f.read(1024 * 1024):
                    h.update(chunk)
            return BrainResponse("local_pc", f"SHA256({target.relative_to(self.workspace)}): {h.hexdigest()}")
        except Exception as e:
            return BrainResponse("local_pc", f"Checksum failed: {e}")

    def _task_compare_files(self, prompt: str) -> BrainResponse:
        text = self._extract_after_colon(prompt)
        if "|" not in text:
            return BrainResponse("local_pc", "Use: compare files: file1 | file2")
        rel1, rel2 = [x.strip() for x in text.split("|", 1)]
        p1 = (self.workspace / rel1).resolve()
        p2 = (self.workspace / rel2).resolve()
        if not p1.exists() or not p2.exists() or not p1.is_file() or not p2.is_file():
            return BrainResponse("local_pc", "Both files must exist.")
        try:
            h1 = hashlib.sha256(p1.read_bytes()).hexdigest()
            h2 = hashlib.sha256(p2.read_bytes()).hexdigest()
            same = h1 == h2
            return BrainResponse("local_pc", f"Files equal: {same}\n- {rel1}: {h1}\n- {rel2}: {h2}")
        except Exception as e:
            return BrainResponse("local_pc", f"Compare failed: {e}")

    def _task_csv_summary(self, prompt: str) -> BrainResponse:
        rel = self._extract_after_colon(prompt)
        if not rel:
            return BrainResponse("local_pc", "Use: csv summary: data/file.csv")
        target = (self.workspace / rel).resolve()
        if not target.exists() or not target.is_file():
            return BrainResponse("local_pc", f"CSV file not found: {rel}")
        try:
            with target.open("r", encoding="utf-8", errors="ignore", newline="") as f:
                reader = csv.DictReader(f)
                headers = reader.fieldnames or []
                rows = list(reader)
            return BrainResponse(
                "local_pc",
                "CSV summary:\n"
                f"- File: {target.relative_to(self.workspace)}\n"
                f"- Rows: {len(rows)}\n"
                f"- Columns: {len(headers)}\n"
                f"- Headers: {', '.join(headers[:30]) if headers else 'none'}",
            )
        except Exception as e:
            return BrainResponse("local_pc", f"CSV summary failed: {e}")

    def _task_create_folder(self, prompt: str) -> BrainResponse:
        rel = self._extract_after_colon(prompt)
        if not rel:
            return BrainResponse("local_pc", "Use: create folder: notes/archive")
        target = (self.workspace / rel)
        if not self.config.allow_write:
            return BrainResponse("local_pc", f"Write blocked (allow_write=False). Would create folder {rel}.")
        try:
            target.mkdir(parents=True, exist_ok=True)
            return BrainResponse("local_pc", f"Folder ready: {target.relative_to(self.workspace)}", actions=[f"mkdir:{rel}"])
        except Exception as e:
            return BrainResponse("local_pc", f"Create folder failed: {e}")

    def _task_copy_file(self, prompt: str) -> BrainResponse:
        text = self._extract_after_colon(prompt)
        if "|" not in text:
            return BrainResponse("local_pc", "Use: copy file: src.txt | backup/src.txt")
        src_rel, dst_rel = [x.strip() for x in text.split("|", 1)]
        src = (self.workspace / src_rel)
        dst = (self.workspace / dst_rel)
        if not self.config.allow_write:
            return BrainResponse("local_pc", f"Write blocked (allow_write=False). Would copy {src_rel} -> {dst_rel}.")
        if not src.exists() or not src.is_file():
            return BrainResponse("local_pc", f"Source file not found: {src_rel}")
        try:
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
            return BrainResponse("local_pc", f"Copied: {src_rel} -> {dst_rel}", actions=[f"copy:{src_rel}->{dst_rel}"])
        except Exception as e:
            return BrainResponse("local_pc", f"Copy failed: {e}")

    def _task_move_file(self, prompt: str) -> BrainResponse:
        text = self._extract_after_colon(prompt)
        if "|" not in text:
            return BrainResponse("local_pc", "Use: move file: src.txt | archive/src.txt")
        src_rel, dst_rel = [x.strip() for x in text.split("|", 1)]
        src = (self.workspace / src_rel)
        dst = (self.workspace / dst_rel)
        if not self.config.allow_write:
            return BrainResponse("local_pc", f"Write blocked (allow_write=False). Would move {src_rel} -> {dst_rel}.")
        if not src.exists() or not src.is_file():
            return BrainResponse("local_pc", f"Source file not found: {src_rel}")
        try:
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(src), str(dst))
            return BrainResponse("local_pc", f"Moved: {src_rel} -> {dst_rel}", actions=[f"move:{src_rel}->{dst_rel}"])
        except Exception as e:
            return BrainResponse("local_pc", f"Move failed: {e}")

    def _task_delete_file(self, prompt: str) -> BrainResponse:
        rel = self._extract_after_colon(prompt)
        if not rel:
            return BrainResponse("local_pc", "Use: delete file: temp.txt")
        target = (self.workspace / rel)
        if not self.config.allow_write:
            return BrainResponse("local_pc", f"Write blocked (allow_write=False). Would delete {rel}.")
        if not target.exists() or not target.is_file():
            return BrainResponse("local_pc", f"File not found: {rel}")
        try:
            target.unlink()
            return BrainResponse("local_pc", f"Deleted file: {rel}", actions=[f"delete:{rel}"])
        except Exception as e:
            return BrainResponse("local_pc", f"Delete failed: {e}")

    def _task_zip_folder(self, prompt: str) -> BrainResponse:
        text = self._extract_after_colon(prompt)
        if "|" not in text:
            return BrainResponse("local_pc", "Use: zip folder: folder_path | archive.zip")
        folder_rel, zip_rel = [x.strip() for x in text.split("|", 1)]
        folder = (self.workspace / folder_rel)
        target_zip = (self.workspace / zip_rel)
        if not self.config.allow_write:
            return BrainResponse("local_pc", f"Write blocked (allow_write=False). Would zip {folder_rel} -> {zip_rel}.")
        if not folder.exists() or not folder.is_dir():
            return BrainResponse("local_pc", f"Folder not found: {folder_rel}")
        try:
            target_zip.parent.mkdir(parents=True, exist_ok=True)
            with zipfile.ZipFile(target_zip, "w", zipfile.ZIP_DEFLATED) as zf:
                for p in folder.rglob("*"):
                    if p.is_file():
                        zf.write(p, p.relative_to(folder.parent))
            return BrainResponse("local_pc", f"Created zip: {zip_rel}", actions=[f"zip:{folder_rel}->{zip_rel}"])
        except Exception as e:
            return BrainResponse("local_pc", f"Zip failed: {e}")

    def _task_unzip_file(self, prompt: str) -> BrainResponse:
        text = self._extract_after_colon(prompt)
        if "|" not in text:
            return BrainResponse("local_pc", "Use: unzip file: archive.zip | output_folder")
        zip_rel, out_rel = [x.strip() for x in text.split("|", 1)]
        zip_path = (self.workspace / zip_rel)
        out_dir = (self.workspace / out_rel)
        if not self.config.allow_write:
            return BrainResponse("local_pc", f"Write blocked (allow_write=False). Would unzip {zip_rel} -> {out_rel}.")
        if not zip_path.exists() or not zip_path.is_file():
            return BrainResponse("local_pc", f"Zip file not found: {zip_rel}")
        try:
            out_dir.mkdir(parents=True, exist_ok=True)
            with zipfile.ZipFile(zip_path, "r") as zf:
                zf.extractall(out_dir)
            return BrainResponse("local_pc", f"Extracted to: {out_rel}", actions=[f"unzip:{zip_rel}->{out_rel}"])
        except Exception as e:
            return BrainResponse("local_pc", f"Unzip failed: {e}")

    def _task_run_command(self, prompt: str) -> BrainResponse:
        cmd = self._extract_after_colon(prompt)
        if not cmd:
            return BrainResponse("local_pc", "Use: run command: where python")
        try:
            proc = subprocess.run(
                cmd,
                shell=True,
                capture_output=True,
                text=True,
                timeout=20,
                cwd=str(self.workspace),
            )
            out = (proc.stdout or "").strip()
            err = (proc.stderr or "").strip()
            text = [f"Exit code: {proc.returncode}"]
            if out:
                text.append("STDOUT:\n" + out[:4000])
            if err:
                text.append("STDERR:\n" + err[:2000])
            return BrainResponse("local_pc", "\n\n".join(text))
        except Exception as e:
            return BrainResponse("local_pc", f"Command failed: {e}")

    # ══════════════════════════════════════════════════════════════════════
    # Scoring / NLP helpers
    # ══════════════════════════════════════════════════════════════════════

    def _extract_entities(self, prompt: str) -> dict:
        """Extract structured entities from natural language prompt."""
        low = prompt.lower()
        entities: dict = {}
        # URLs
        urls = re.findall(r"https?://\S+|www\.\S+", prompt)
        if urls:
            entities["urls"] = urls
        # File paths (Windows + POSIX)
        paths = re.findall(r"[A-Za-z]:\\[\w\\.\-]+|/[\w/.\-]+\.[\w]{1,10}", prompt)
        if paths:
            entities["paths"] = paths
        # Numbers
        nums = re.findall(r"-?\d+(?:\.\d+)?", prompt)
        if nums:
            entities["numbers"] = [float(n) if "." in n else int(n) for n in nums]
        # App names (after keywords like "launch/open/start/kill")
        app_match = re.search(
            r"(?:launch|open|start|run|kill|stop|close|end)\s+(?:app|program|process|application)?\s*[:\-]?\s*([a-zA-Z][\w.\-\s]{0,30})",
            low,
        )
        if app_match:
            entities["app_name"] = app_match.group(1).strip().rstrip(".")
        # File after "run file:" or "execute:"
        file_match = re.search(
            r"(?:run file|execute file|run script|run python|execute)[\s:\-]+([^\s,]+(?:\.[a-zA-Z]{1,8}))",
            low,
        )
        if file_match:
            entities["file_path"] = file_match.group(1).strip()
        # URL after "open url" / "go to" / "visit"
        url_match = re.search(
            r"(?:open url|open website|visit|go to|browse to|open browser)[\s:\-]+(https?://\S+|www\.\S+|[\w\-]+\.\w{2,6}(?:/\S*)?)",
            low,
        )
        if url_match:
            entities["target_url"] = url_match.group(1).strip()
        return entities

    def _score_dispatch(self, prompt: str) -> "BrainResponse | None":
        """Scored multi-keyword intent matching for natural-language queries."""
        low = prompt.lower()
        entities = self._extract_entities(prompt)

        # Each entry: (min_score, score_fn, handler_fn)
        scored_rules: list[tuple[int, Callable[[], int], Callable[[str], BrainResponse]]] = [
            # ── App launching ──────────────────────────────────────────────
            (2, lambda: sum([
                any(k in low for k in ["launch", "open", "start", "run", "execute"]),
                any(k in low for k in ["app", "application", "program", "software", "exe"]),
                "app_name" in entities,
            ]), self._task_launch_app),
            # ── File execution ─────────────────────────────────────────────
            (2, lambda: sum([
                any(k in low for k in ["run", "execute", "play", "launch"]),
                any(k in low for k in ["file", "script", "python", "batch"]),
                "file_path" in entities,
                bool(re.search(r"\.(py|bat|sh|exe|js|html?|ps1|rb|php)\b", low)),
            ]), self._task_run_file),
            # ── URL navigation ─────────────────────────────────────────────
            (2, lambda: sum([
                any(k in low for k in ["open", "go", "visit", "browse", "navigate"]),
                any(k in low for k in ["url", "website", "site", "link", "browser", "internet"]),
                "target_url" in entities or bool(entities.get("urls")),
                bool(re.search(r"https?://|www\.", low)),
            ]), self._task_open_url),
            # ── Clipboard ──────────────────────────────────────────────────
            (2, lambda: sum([
                "clipboard" in low,
                any(k in low for k in ["copy", "paste", "read", "write", "get", "set"]),
                any(k in low for k in ["clipboard", "clip board", "copy buffer"]),
            ]) + (2 if "clipboard" in low and any(k in low for k in ["read", "get", "what", "show"]) else 0),
            self._task_clipboard_read),
            # ── Screenshot ─────────────────────────────────────────────────
            (2, lambda: sum([
                any(k in low for k in ["screen", "screenshot", "capture", "snap", "print screen"]),
                any(k in low for k in ["take", "grab", "save", "make", "create"]),
            ]), self._task_screenshot),
            # ── Process kill ───────────────────────────────────────────────
            (2, lambda: sum([
                any(k in low for k in ["kill", "stop", "close", "end", "terminate", "force close"]),
                any(k in low for k in ["process", "app", "program", "application", "exe", "task"]),
                "app_name" in entities,
            ]), self._task_kill_process),
            # ── Memory usage ───────────────────────────────────────────────
            (2, lambda: sum([
                any(k in low for k in ["memory", "ram", "heap"]),
                any(k in low for k in ["usage", "info", "status", "check", "show", "free", "available"]),
            ]), self._task_memory_usage),
            # ── Port check ─────────────────────────────────────────────────
            (2, lambda: sum([
                "port" in low,
                any(k in low for k in ["check", "status", "open", "listening", "listen"]),
                bool(re.search(r"\b\d{2,5}\b", low)),
            ]), self._task_check_port),
            # ── Service status ─────────────────────────────────────────────
            (2, lambda: sum([
                "service" in low,
                any(k in low for k in ["status", "running", "stopped", "check", "query"]),
            ]), self._task_service_status),
        ]

        best_score = 0
        best_fn = None
        for min_score, score_fn, handler_fn in scored_rules:
            try:
                score = score_fn()
            except Exception:
                score = 0
            if score >= min_score and score > best_score:
                best_score = score
                best_fn = handler_fn

        if best_fn is not None:
            return best_fn(prompt)
        return None

    # ══════════════════════════════════════════════════════════════════════
    # App / process automation handlers
    # ══════════════════════════════════════════════════════════════════════

    # Map of common app names to executable commands
    _APP_MAP: dict[str, str] = {
        "notepad": "notepad.exe",
        "calculator": "calc.exe",
        "calc": "calc.exe",
        "paint": "mspaint.exe",
        "mspaint": "mspaint.exe",
        "chrome": "chrome.exe",
        "google chrome": "chrome.exe",
        "firefox": "firefox.exe",
        "edge": "msedge.exe",
        "microsoft edge": "msedge.exe",
        "brave": "brave.exe",
        "opera": "opera.exe",
        "vscode": "code",
        "visual studio code": "code",
        "code": "code",
        "explorer": "explorer.exe",
        "file explorer": "explorer.exe",
        "task manager": "taskmgr.exe",
        "taskmgr": "taskmgr.exe",
        "cmd": "cmd.exe",
        "command prompt": "cmd.exe",
        "terminal": "wt.exe",
        "windows terminal": "wt.exe",
        "powershell": "powershell.exe",
        "wordpad": "wordpad.exe",
        "word": "winword.exe",
        "excel": "excel.exe",
        "powerpoint": "powerpnt.exe",
        "outlook": "outlook.exe",
        "teams": "teams.exe",
        "discord": "discord.exe",
        "spotify": "spotify.exe",
        "vlc": "vlc.exe",
        "obs": "obs64.exe",
        "steam": "steam.exe",
        "winamp": "winamp.exe",
        "snipping tool": "snippingtool.exe",
        "snip": "snippingtool.exe",
        "regedit": "regedit.exe",
        "control panel": "control.exe",
        "settings": "ms-settings:",
        "device manager": "devmgmt.msc",
        "event viewer": "eventvwr.msc",
        "services": "services.msc",
        "disk management": "diskmgmt.msc",
        "python": "python",
        "git": "git",
        "node": "node",
        "npm": "npm",
    }

    def _task_launch_app(self, prompt: str) -> BrainResponse:
        """Launch a named application."""
        low = prompt.lower()
        entities = self._extract_entities(prompt)
        app_name = entities.get("app_name", "")

        if not app_name:
            # Try extracting from after colon
            colon_val = self._extract_after_colon(prompt).strip().rstrip(".")
            if colon_val:
                app_name = colon_val.lower()

        if not app_name:
            # Try stripping action words to get app name
            cleaned = re.sub(r"\b(launch|open|start|run|execute|app|application|program|software|please|can you|could you)\b", "", low)
            app_name = cleaned.strip().rstrip(".,!").strip()

        if not app_name:
            return BrainResponse("automation", "Please specify the app name. Example: launch app: notepad")

        # Look up in map
        app_name_lower = app_name.lower().strip()
        executable = self._APP_MAP.get(app_name_lower)

        if not executable:
            # Try partial match
            for key, exe in self._APP_MAP.items():
                if key in app_name_lower or app_name_lower in key:
                    executable = exe
                    break

        if not executable:
            # Use raw app name as executable (user knows what they want)
            executable = app_name_lower
            # Add .exe if on Windows and no extension
            if os.name == "nt" and "." not in executable and "/" not in executable and "\\" not in executable:
                executable_with_ext = executable + ".exe"
            else:
                executable_with_ext = executable
        else:
            executable_with_ext = executable

        try:
            if os.name == "nt" and executable_with_ext.startswith("ms-"):
                # Windows settings URI
                os.startfile(executable_with_ext)
                return BrainResponse("automation", f"✅ Opened: {app_name} (Windows URI)", actions=[f"launch:{app_name}"])
            if os.name == "nt" and executable_with_ext.endswith(".msc"):
                subprocess.Popen(["mmc", executable_with_ext], creationflags=subprocess.DETACHED_PROCESS)
                return BrainResponse("automation", f"✅ Opened: {app_name}", actions=[f"launch:{app_name}"])
            if os.name == "nt":
                subprocess.Popen(
                    executable_with_ext,
                    creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP,
                    close_fds=True,
                    shell=True,
                )
            else:
                subprocess.Popen(
                    executable_with_ext,
                    start_new_session=True,
                    shell=True,
                )
            return BrainResponse("automation", f"✅ Launched: {app_name} ({executable_with_ext})", actions=[f"launch:{app_name}"])
        except FileNotFoundError:
            return BrainResponse("automation", f"❌ App not found: {executable_with_ext}\nMake sure it is installed and in your PATH.")
        except Exception as e:
            return BrainResponse("automation", f"❌ Failed to launch {app_name}: {e}")

    def _task_run_file(self, prompt: str) -> BrainResponse:
        """Execute a file with the appropriate runner."""
        entities = self._extract_entities(prompt)
        rel = entities.get("file_path") or self._extract_after_colon(prompt).strip()
        if not rel:
            return BrainResponse("automation", "Use: run file: path/to/script.py\nSupported: .py .bat .sh .exe .js .html .ps1")

        target = (self.workspace / rel).resolve()
        if not target.exists():
            # Try absolute path
            abs_target = Path(rel)
            if abs_target.exists():
                target = abs_target
            else:
                return BrainResponse("automation", f"File not found: {rel}")

        ext = target.suffix.lower()
        runner_map = {
            ".py": [sys_python(), str(target)],
            ".pyw": [sys_python(), str(target)],
            ".bat": ["cmd", "/c", str(target)],
            ".cmd": ["cmd", "/c", str(target)],
            ".sh": ["bash", str(target)],
            ".ps1": ["powershell", "-ExecutionPolicy", "Bypass", "-File", str(target)],
            ".js": ["node", str(target)],
            ".rb": ["ruby", str(target)],
            ".php": ["php", str(target)],
        }
        gui_extensions = {".exe", ".html", ".htm", ".pdf", ".docx", ".xlsx", ".pptx", ".png", ".jpg", ".jpeg", ".gif", ".mp4", ".mp3"}

        if ext in gui_extensions:
            try:
                if os.name == "nt":
                    os.startfile(str(target))
                else:
                    subprocess.Popen(["xdg-open", str(target)])
                return BrainResponse("automation", f"✅ Opened with default app: {target.name}", actions=[f"open:{rel}"])
            except Exception as e:
                return BrainResponse("automation", f"❌ Could not open {target.name}: {e}")

        cmd = runner_map.get(ext)
        if not cmd:
            return BrainResponse("automation", f"Unknown file type: {ext}\nSupported: {', '.join(runner_map)}")

        try:
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=30, cwd=str(target.parent))
            out = (proc.stdout or "").strip()
            err = (proc.stderr or "").strip()
            parts = [f"✅ Ran: {target.name} (exit {proc.returncode})"]
            if out:
                parts.append("Output:\n" + out[:3000])
            if err:
                parts.append("Stderr:\n" + err[:1000])
            return BrainResponse("automation", "\n\n".join(parts), actions=[f"run:{rel}"])
        except FileNotFoundError:
            runner_name = cmd[0]
            return BrainResponse("automation", f"❌ Runner not found: '{runner_name}'. Make sure it is installed and in PATH.")
        except subprocess.TimeoutExpired:
            return BrainResponse("automation", f"⏱ Timeout: {target.name} took too long (>30s). Try running it manually.")
        except Exception as e:
            return BrainResponse("automation", f"❌ Run failed: {e}")

    def _task_open_url(self, prompt: str) -> BrainResponse:
        """Open a URL in the default browser."""
        entities = self._extract_entities(prompt)
        url = entities.get("target_url") or (entities.get("urls", [None])[0] if entities.get("urls") else None)

        if not url:
            colon_val = self._extract_after_colon(prompt).strip()
            if colon_val:
                url = colon_val

        if not url:
            return BrainResponse("automation", "Use: open url: https://example.com")

        # Normalize URL
        if not url.startswith(("http://", "https://", "file://")):
            url = "https://" + url

        try:
            webbrowser.open(url)
            return BrainResponse("automation", f"✅ Opened in browser: {url}", actions=[f"open_url:{url}"])
        except Exception as e:
            return BrainResponse("automation", f"❌ Could not open browser: {e}")

    # ──────────────────────────────────────────────────────────────────────
    # Clipboard
    # ──────────────────────────────────────────────────────────────────────

    def _clipboard_get_windows(self) -> str:
        """Read clipboard text on Windows using ctypes."""
        import ctypes
        CF_UNICODETEXT = 13
        if not ctypes.windll.user32.OpenClipboard(0):
            raise RuntimeError("Cannot open clipboard")
        try:
            data = ctypes.windll.user32.GetClipboardData(CF_UNICODETEXT)
            if not data:
                return ""
            ptr = ctypes.cast(data, ctypes.c_wchar_p)
            return ptr.value or ""
        finally:
            ctypes.windll.user32.CloseClipboard()

    def _clipboard_set_windows(self, text: str) -> None:
        """Write clipboard text on Windows using ctypes."""
        import ctypes
        CF_UNICODETEXT = 13
        GMEM_MOVEABLE = 0x0002
        encoded = text.encode("utf-16-le") + b"\x00\x00"
        h_mem = ctypes.windll.kernel32.GlobalAlloc(GMEM_MOVEABLE, len(encoded))
        if not h_mem:
            raise RuntimeError("GlobalAlloc failed")
        ptr = ctypes.windll.kernel32.GlobalLock(h_mem)
        ctypes.memmove(ptr, encoded, len(encoded))
        ctypes.windll.kernel32.GlobalUnlock(h_mem)
        if not ctypes.windll.user32.OpenClipboard(0):
            raise RuntimeError("Cannot open clipboard")
        try:
            ctypes.windll.user32.EmptyClipboard()
            ctypes.windll.user32.SetClipboardData(CF_UNICODETEXT, h_mem)
        finally:
            ctypes.windll.user32.CloseClipboard()

    def _task_clipboard_read(self, _: str = "") -> BrainResponse:
        """Read the current clipboard contents."""
        try:
            if os.name == "nt":
                content = self._clipboard_get_windows()
            else:
                proc = subprocess.run(["xclip", "-selection", "clipboard", "-o"], capture_output=True, text=True, timeout=5)
                content = proc.stdout
        except Exception as e:
            return BrainResponse("automation", f"❌ Could not read clipboard: {e}")

        if not content:
            return BrainResponse("automation", "📋 Clipboard is empty.")
        preview = content[:2000]
        suffix = f"\n... [{len(content) - 2000} more chars]" if len(content) > 2000 else ""
        return BrainResponse("automation", f"📋 Clipboard content:\n{preview}{suffix}")

    def _task_clipboard_write(self, prompt: str) -> BrainResponse:
        """Write text to the clipboard."""
        text = self._extract_after_colon(prompt).strip()
        if not text:
            return BrainResponse("automation", "Use: clipboard write: your text to copy")
        try:
            if os.name == "nt":
                self._clipboard_set_windows(text)
            else:
                proc = subprocess.run(["xclip", "-selection", "clipboard"], input=text, text=True, timeout=5)
                if proc.returncode != 0:
                    raise RuntimeError("xclip failed")
        except Exception as e:
            return BrainResponse("automation", f"❌ Could not write clipboard: {e}")
        return BrainResponse("automation", f"✅ Copied to clipboard ({len(text)} chars)", actions=["clipboard:write"])

    # ──────────────────────────────────────────────────────────────────────
    # Window & screen management
    # ──────────────────────────────────────────────────────────────────────

    def _task_list_windows(self, _: str = "") -> BrainResponse:
        """List open windows / processes with visible titles."""
        try:
            if os.name == "nt":
                proc = subprocess.run(
                    ["powershell", "-NoProfile", "-Command",
                     "Get-Process | Where-Object {$_.MainWindowTitle -ne ''} | Select-Object Name, Id, MainWindowTitle | Format-Table -AutoSize"],
                    capture_output=True, text=True, timeout=15,
                )
                out = proc.stdout.strip()
                if not out:
                    return BrainResponse("automation", "No windows with titles found.")
                return BrainResponse("automation", "🪟 Open windows:\n" + out[:3000])
            else:
                proc = subprocess.run(["wmctrl", "-l"], capture_output=True, text=True, timeout=10)
                return BrainResponse("automation", "🪟 Open windows:\n" + (proc.stdout.strip() or "none"))
        except Exception as e:
            return BrainResponse("automation", f"❌ Could not list windows: {e}")

    def _task_get_active_window(self, _: str = "") -> BrainResponse:
        """Get the currently active window title."""
        try:
            if os.name == "nt":
                import ctypes
                buf = ctypes.create_unicode_buffer(512)
                hwnd = ctypes.windll.user32.GetForegroundWindow()
                ctypes.windll.user32.GetWindowTextW(hwnd, buf, 512)
                title = buf.value
                return BrainResponse("automation", f"🔲 Active window: {title or '(no title)'}")
            else:
                proc = subprocess.run(
                    ["xdotool", "getactivewindow", "getwindowname"],
                    capture_output=True, text=True, timeout=5,
                )
                return BrainResponse("automation", f"🔲 Active window: {proc.stdout.strip()}")
        except Exception as e:
            return BrainResponse("automation", f"❌ Could not get active window: {e}")

    def _task_kill_process(self, prompt: str) -> BrainResponse:
        """Kill a process by name."""
        entities = self._extract_entities(prompt)
        name = entities.get("app_name") or self._extract_after_colon(prompt).strip()

        if not name:
            # Extract after kill/stop/end/terminate
            m = re.search(r"(?:kill|stop|close|end|terminate)\s+(?:process\s+)?([a-zA-Z][\w.\-]{1,40})", prompt.lower())
            if m:
                name = m.group(1).strip()

        if not name:
            return BrainResponse("automation", "Use: kill process: chrome.exe\nOr: stop process: notepad")

        # Auto-add .exe on Windows if missing
        if os.name == "nt" and "." not in name:
            name_exe = name + ".exe"
        else:
            name_exe = name

        try:
            if os.name == "nt":
                proc = subprocess.run(
                    ["taskkill", "/IM", name_exe, "/F"],
                    capture_output=True, text=True, timeout=10,
                )
                if proc.returncode == 0:
                    return BrainResponse("automation", f"✅ Killed: {name_exe}\n{proc.stdout.strip()}", actions=[f"kill:{name_exe}"])
                else:
                    # Try without .exe
                    proc2 = subprocess.run(
                        ["taskkill", "/IM", name, "/F"],
                        capture_output=True, text=True, timeout=10,
                    )
                    if proc2.returncode == 0:
                        return BrainResponse("automation", f"✅ Killed: {name}\n{proc2.stdout.strip()}", actions=[f"kill:{name}"])
                    return BrainResponse("automation", f"❌ Could not kill '{name}': {proc.stderr.strip()}")
            else:
                proc = subprocess.run(["pkill", "-f", name], capture_output=True, text=True, timeout=10)
                if proc.returncode == 0:
                    return BrainResponse("automation", f"✅ Killed: {name}", actions=[f"kill:{name}"])
                return BrainResponse("automation", f"❌ No process found matching '{name}'")
        except Exception as e:
            return BrainResponse("automation", f"❌ Kill process failed: {e}")

    def _task_screenshot(self, _: str = "") -> BrainResponse:
        """Take a screenshot and save to workspace."""
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"screenshot_{ts}.png"
        target = self.workspace / filename

        # Method 1: PIL/Pillow
        try:
            from PIL import ImageGrab  # type: ignore
            img = ImageGrab.grab()
            img.save(str(target))
            return BrainResponse("automation", f"✅ Screenshot saved: {filename} ({img.size[0]}x{img.size[1]})", actions=[f"screenshot:{filename}"])
        except ImportError:
            pass
        except Exception as e:
            pass

        # Method 2: Windows PowerShell fallback
        if os.name == "nt":
            try:
                ps_cmd = (
                    f"Add-Type -AssemblyName System.Windows.Forms; "
                    f"$bmp = [System.Drawing.Bitmap]::new([System.Windows.Forms.Screen]::PrimaryScreen.Bounds.Width, "
                    f"[System.Windows.Forms.Screen]::PrimaryScreen.Bounds.Height); "
                    f"$g = [System.Drawing.Graphics]::FromImage($bmp); "
                    f"$g.CopyFromScreen(0, 0, 0, 0, $bmp.Size); "
                    f"$bmp.Save('{str(target).replace(chr(92), '/')}'); "
                    f"$g.Dispose(); $bmp.Dispose()"
                )
                proc = subprocess.run(["powershell", "-NoProfile", "-Command", ps_cmd], capture_output=True, text=True, timeout=20)
                if target.exists():
                    return BrainResponse("automation", f"✅ Screenshot saved: {filename}", actions=[f"screenshot:{filename}"])
                return BrainResponse("automation", f"❌ PowerShell screenshot failed: {proc.stderr.strip()[:500]}")
            except Exception as e:
                return BrainResponse("automation", f"❌ Screenshot failed: {e}")

        return BrainResponse("automation", "❌ Screenshot requires Pillow (pip install pillow) or Windows PowerShell.")

    def _task_memory_usage(self, _: str = "") -> BrainResponse:
        """Show system RAM / memory usage."""
        try:
            if os.name == "nt":
                proc = subprocess.run(
                    ["powershell", "-NoProfile", "-Command",
                     "Get-CimInstance Win32_OperatingSystem | Select-Object TotalVisibleMemorySize, FreePhysicalMemory | Format-List"],
                    capture_output=True, text=True, timeout=10,
                )
                out = proc.stdout.strip()
                if not out:
                    raise RuntimeError("No output from WMI")
                # Parse values
                total_m = re.search(r"TotalVisibleMemorySize\s*:\s*(\d+)", out)
                free_m = re.search(r"FreePhysicalMemory\s*:\s*(\d+)", out)
                if total_m and free_m:
                    total_kb = int(total_m.group(1))
                    free_kb = int(free_m.group(1))
                    used_kb = total_kb - free_kb
                    total_gb = total_kb / 1024 / 1024
                    used_gb = used_kb / 1024 / 1024
                    free_gb = free_kb / 1024 / 1024
                    pct = used_kb / total_kb * 100
                    return BrainResponse(
                        "local_pc",
                        f"💾 Memory usage:\n"
                        f"- Total RAM: {total_gb:.2f} GB\n"
                        f"- Used: {used_gb:.2f} GB ({pct:.1f}%)\n"
                        f"- Free: {free_gb:.2f} GB",
                    )
                return BrainResponse("local_pc", out[:1000])
            else:
                proc = subprocess.run(["free", "-h"], capture_output=True, text=True, timeout=5)
                return BrainResponse("local_pc", "💾 Memory usage:\n" + proc.stdout.strip())
        except Exception as e:
            return BrainResponse("local_pc", f"❌ Could not get memory info: {e}")

    def _task_cpu_info(self, _: str = "") -> BrainResponse:
        """Show CPU info and current usage."""
        try:
            uname = platform.uname()
            info = [
                f"Processor: {uname.processor or uname.machine}",
                f"Cores (logical): {os.cpu_count()}",
                f"System: {uname.system} {uname.release}",
            ]
            if os.name == "nt":
                proc = subprocess.run(
                    ["powershell", "-NoProfile", "-Command",
                     "Get-CimInstance Win32_Processor | Select-Object Name, NumberOfCores, MaxClockSpeed | Format-List"],
                    capture_output=True, text=True, timeout=10,
                )
                if proc.returncode == 0 and proc.stdout.strip():
                    info.append("\n" + proc.stdout.strip()[:800])
            return BrainResponse("local_pc", "🖥 CPU info:\n" + "\n".join(f"- {x}" for x in info))
        except Exception as e:
            return BrainResponse("local_pc", f"❌ CPU info failed: {e}")

    def _task_rename_file(self, prompt: str) -> BrainResponse:
        """Rename a file."""
        text = self._extract_after_colon(prompt)
        if "|" not in text:
            return BrainResponse("local_pc", "Use: rename file: oldname.txt | newname.txt")
        src_rel, dst_rel = [x.strip() for x in text.split("|", 1)]
        src = (self.workspace / src_rel)
        dst = (self.workspace / dst_rel)
        if not self.config.allow_write:
            return BrainResponse("local_pc", f"Write blocked (allow_write=False). Would rename {src_rel} -> {dst_rel}.")
        if not src.exists():
            return BrainResponse("local_pc", f"Source not found: {src_rel}")
        try:
            dst.parent.mkdir(parents=True, exist_ok=True)
            src.rename(dst)
            return BrainResponse("local_pc", f"✅ Renamed: {src_rel} → {dst_rel}", actions=[f"rename:{src_rel}->{dst_rel}"])
        except Exception as e:
            return BrainResponse("local_pc", f"❌ Rename failed: {e}")

    def _task_open_file_with_default(self, prompt: str) -> BrainResponse:
        """Open a file with the OS default application."""
        rel = self._extract_after_colon(prompt).strip()
        if not rel:
            return BrainResponse("automation", "Use: open file with: relative/path.ext")
        target = (self.workspace / rel).resolve()
        if not target.exists():
            rel_abs = Path(rel)
            if rel_abs.exists():
                target = rel_abs
            else:
                return BrainResponse("automation", f"File not found: {rel}")
        try:
            if os.name == "nt":
                os.startfile(str(target))
            elif platform.system() == "Darwin":
                subprocess.Popen(["open", str(target)])
            else:
                subprocess.Popen(["xdg-open", str(target)])
            return BrainResponse("automation", f"✅ Opened with default app: {target.name}", actions=[f"open_file:{rel}"])
        except Exception as e:
            return BrainResponse("automation", f"❌ Could not open file: {e}")

    def _task_list_installed_apps(self, _: str = "") -> BrainResponse:
        """List installed applications (Windows only)."""
        if os.name != "nt":
            return BrainResponse("automation", "List installed apps is only supported on Windows.")
        try:
            proc = subprocess.run(
                ["powershell", "-NoProfile", "-Command",
                 "Get-ItemProperty HKLM:\\Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\* | "
                 "Select-Object DisplayName, DisplayVersion | Where-Object DisplayName -ne $null | "
                 "Sort-Object DisplayName | Select-Object -First 50 | Format-Table -AutoSize"],
                capture_output=True, text=True, timeout=20,
            )
            out = proc.stdout.strip()
            return BrainResponse("automation", "📦 Installed programs (top 50):\n" + (out[:4000] if out else "No data found."))
        except Exception as e:
            return BrainResponse("automation", f"❌ Could not list installed apps: {e}")

    def _task_set_volume(self, prompt: str) -> BrainResponse:
        """Adjust system volume on Windows."""
        if os.name != "nt":
            return BrainResponse("automation", "Volume control is only supported on Windows.")
        low = prompt.lower()
        mute = "mute" in low
        if mute:
            # Toggle mute via PowerShell
            cmd = (
                "$wshell = New-Object -ComObject wscript.shell; "
                "$wshell.SendKeys([char]0xAD)"  # 0xAD = VK_VOLUME_MUTE
            )
            try:
                subprocess.run(["powershell", "-NoProfile", "-Command", cmd], timeout=5)
                return BrainResponse("automation", "🔇 Mute toggled.")
            except Exception as e:
                return BrainResponse("automation", f"❌ Mute failed: {e}")
        # Try to parse a volume % from prompt
        nums = re.findall(r"\d+", prompt)
        if nums:
            vol = max(0, min(100, int(nums[0])))
            # Use nircmd if available, else PowerShell audio
            nircmd = shutil.which("nircmd")
            if nircmd:
                try:
                    subprocess.run([nircmd, "setsysvolume", str(int(vol * 655.35))], timeout=5)
                    return BrainResponse("automation", f"🔊 Volume set to {vol}%")
                except Exception:
                    pass
            return BrainResponse(
                "automation",
                f"Volume change to {vol}% requested.\n"
                "Tip: install nircmd (https://www.nirsoft.net/utils/nircmd.html) for precise volume control.",
            )
        if "up" in low:
            return BrainResponse("automation", "Volume up requested. (Install nircmd for programmatic control)")
        if "down" in low:
            return BrainResponse("automation", "Volume down requested. (Install nircmd for programmatic control)")
        return BrainResponse("automation", "Use: set volume: 50  OR  mute volume  OR  volume up/down")

    def _task_sleep_system(self, prompt: str) -> BrainResponse:
        """Sleep, hibernate, restart, or shutdown the system."""
        if not self.config.allow_write:
            return BrainResponse("automation", "⚠️ Power actions are blocked (allow_write=False). Enable allow_write to proceed.")
        low = prompt.lower()
        if "shutdown" in low:
            if os.name == "nt":
                subprocess.run(["shutdown", "/s", "/t", "30"], capture_output=True)
            else:
                subprocess.run(["sudo", "shutdown", "-h", "+1"], capture_output=True)
            return BrainResponse("automation", "⚠️ Shutdown scheduled in 30 seconds. Run 'shutdown /a' to cancel.")
        if "restart" in low or "reboot" in low:
            if os.name == "nt":
                subprocess.run(["shutdown", "/r", "/t", "30"], capture_output=True)
            else:
                subprocess.run(["sudo", "reboot"], capture_output=True)
            return BrainResponse("automation", "⚠️ Restart scheduled in 30 seconds. Run 'shutdown /a' to cancel.")
        if "hibernate" in low:
            if os.name == "nt":
                subprocess.run(["shutdown", "/h"], capture_output=True)
            return BrainResponse("automation", "💤 Hibernate initiated.")
        if "sleep" in low:
            if os.name == "nt":
                subprocess.run(["rundll32.exe", "powrprof.dll,SetSuspendState", "0,1,0"], capture_output=True)
                return BrainResponse("automation", "💤 Sleep initiated.")
            return BrainResponse("automation", "Sleep is Windows-only in this mode.")
        return BrainResponse("automation", "Options: sleep / hibernate / shutdown / restart pc")

    def _task_lock_screen(self, _: str = "") -> BrainResponse:
        """Lock the screen / workstation."""
        try:
            if os.name == "nt":
                import ctypes
                ctypes.windll.user32.LockWorkStation()
                return BrainResponse("automation", "🔒 Screen locked.")
            elif platform.system() == "Darwin":
                subprocess.run(["/System/Library/CoreServices/Menu\\ Extras/User.menu/Contents/Resources/CGSession", "-suspend"])
                return BrainResponse("automation", "🔒 Screen locked.")
            else:
                subprocess.run(["gnome-screensaver-command", "-l"])
                return BrainResponse("automation", "🔒 Screen locked.")
        except Exception as e:
            return BrainResponse("automation", f"❌ Lock screen failed: {e}")

    def _task_empty_recycle(self, _: str = "") -> BrainResponse:
        """Empty the recycle bin (Windows)."""
        if not self.config.allow_write:
            return BrainResponse("automation", "⚠️ Blocked (allow_write=False). Enable to allow deleting recycle bin contents.")
        if os.name != "nt":
            return BrainResponse("automation", "Recycle bin operations are Windows-only.")
        try:
            proc = subprocess.run(
                ["powershell", "-NoProfile", "-Command", "Clear-RecycleBin -Force -ErrorAction SilentlyContinue"],
                capture_output=True, text=True, timeout=15,
            )
            return BrainResponse("automation", "✅ Recycle bin emptied.", actions=["recycle_bin:empty"])
        except Exception as e:
            return BrainResponse("automation", f"❌ Could not empty recycle bin: {e}")

    def _task_ping_host(self, prompt: str) -> BrainResponse:
        """Ping a host or check internet connectivity."""
        host = self._extract_after_colon(prompt).strip()
        if not host:
            m = re.search(r"(?:ping|check internet|internet status)\s+([a-zA-Z0-9_.\-]+)", prompt.lower())
            if m:
                host = m.group(1)
        if not host:
            host = "8.8.8.8"  # Google DNS as default connectivity check

        try:
            if os.name == "nt":
                proc = subprocess.run(["ping", "-n", "4", host], capture_output=True, text=True, timeout=20)
            else:
                proc = subprocess.run(["ping", "-c", "4", host], capture_output=True, text=True, timeout=20)
            success = proc.returncode == 0
            icon = "✅" if success else "❌"
            return BrainResponse(
                "local_pc",
                f"{icon} Ping {host}:\n{proc.stdout.strip()[:2000]}",
            )
        except Exception as e:
            return BrainResponse("local_pc", f"❌ Ping failed: {e}")

    def _task_system_uptime(self, _: str = "") -> BrainResponse:
        """Report system uptime."""
        try:
            if os.name == "nt":
                proc = subprocess.run(
                    ["powershell", "-NoProfile", "-Command", "(Get-CimInstance Win32_OperatingSystem).LastBootUpTime"],
                    capture_output=True, text=True, timeout=10,
                )
                boot = proc.stdout.strip()
                if not boot:
                    return BrainResponse("local_pc", "Could not determine boot time.")
                return BrainResponse("local_pc", f"⏱ System uptime info:\n- Last boot: {boot}")
            proc = subprocess.run(["uptime"], capture_output=True, text=True, timeout=8)
            return BrainResponse("local_pc", f"⏱ {proc.stdout.strip()}")
        except Exception as e:
            return BrainResponse("local_pc", f"❌ Uptime check failed: {e}")

    def _task_public_ip(self, _: str = "") -> BrainResponse:
        """Fetch public IP via simple HTTP endpoint."""
        try:
            req = Request("https://api.ipify.org", headers={"User-Agent": "UltraBot"})
            with urlopen(req, timeout=8) as resp:
                ip = resp.read().decode("utf-8", errors="replace").strip()
            if ip:
                return BrainResponse("network", f"🌐 Public IP: {ip}")
            return BrainResponse("network", "Could not fetch public IP.")
        except Exception as e:
            return BrainResponse("network", f"❌ Public IP check failed: {e}")

    def _task_open_ports(self, _: str = "") -> BrainResponse:
        """List listening/open ports."""
        try:
            if os.name == "nt":
                proc = subprocess.run(
                    ["powershell", "-NoProfile", "-Command", "Get-NetTCPConnection -State Listen | Select-Object LocalAddress,LocalPort,OwningProcess | Sort-Object LocalPort | Format-Table -AutoSize"],
                    capture_output=True, text=True, timeout=15,
                )
                out = proc.stdout.strip() or proc.stderr.strip()
                return BrainResponse("network", "🔌 Listening ports:\n" + (out[:3500] if out else "No data."))
            proc = subprocess.run(["sh", "-c", "ss -lntp || netstat -lntp"], capture_output=True, text=True, timeout=12)
            return BrainResponse("network", "🔌 Listening ports:\n" + (proc.stdout.strip()[:3500] or "No data."))
        except Exception as e:
            return BrainResponse("network", f"❌ Open-port listing failed: {e}")

    def _task_check_port(self, prompt: str) -> BrainResponse:
        """Check if a local port is listening."""
        nums = re.findall(r"\b\d{2,5}\b", prompt)
        if not nums:
            return BrainResponse("network", "Use: check port: 5432")
        port = int(nums[0])
        if port < 1 or port > 65535:
            return BrainResponse("network", "Port must be in range 1-65535.")
        try:
            if os.name == "nt":
                proc = subprocess.run(
                    ["powershell", "-NoProfile", "-Command", f"Get-NetTCPConnection -LocalPort {port} -ErrorAction SilentlyContinue | Select-Object State,OwningProcess,LocalAddress,LocalPort | Format-Table -AutoSize"],
                    capture_output=True, text=True, timeout=10,
                )
                out = (proc.stdout or "").strip()
                if out:
                    return BrainResponse("network", f"✅ Port {port} appears active:\n{out[:1200]}")
                return BrainResponse("network", f"ℹ Port {port} is not listening.")
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(0.8)
            ok = s.connect_ex(("127.0.0.1", port)) == 0
            s.close()
            return BrainResponse("network", f"{'✅' if ok else 'ℹ'} Port {port} {'is open' if ok else 'is closed'} on localhost.")
        except Exception as e:
            return BrainResponse("network", f"❌ Port check failed: {e}")

    def _task_process_details(self, prompt: str) -> BrainResponse:
        """Show details for a process name or PID."""
        arg = self._extract_after_colon(prompt).strip()
        if not arg:
            m = re.search(r"(?:process details|task details)\s+([\w.\-]+)", prompt.lower())
            if m:
                arg = m.group(1)
        if not arg:
            return BrainResponse("local_pc", "Use: process details: chrome  or  process details: 1234")
        try:
            if os.name == "nt":
                if arg.isdigit():
                    cmd = f"Get-Process -Id {arg} | Select-Object Name,Id,CPU,WorkingSet,StartTime,Path | Format-List"
                else:
                    safe_arg = arg.replace("'", "")
                    cmd = f"Get-Process -Name '{safe_arg}' -ErrorAction SilentlyContinue | Select-Object Name,Id,CPU,WorkingSet,StartTime,Path | Format-Table -AutoSize"
                proc = subprocess.run(["powershell", "-NoProfile", "-Command", cmd], capture_output=True, text=True, timeout=12)
                out = (proc.stdout or "").strip()
                return BrainResponse("local_pc", out[:2500] if out else f"No process details found for: {arg}")
            proc = subprocess.run(["sh", "-c", f"ps aux | grep -i '{arg}' | grep -v grep"], capture_output=True, text=True, timeout=10)
            out = (proc.stdout or "").strip()
            return BrainResponse("local_pc", out[:2500] if out else f"No process details found for: {arg}")
        except Exception as e:
            return BrainResponse("local_pc", f"❌ Process details failed: {e}")

    def _task_wifi_profiles(self, _: str = "") -> BrainResponse:
        """List saved Wi-Fi profiles on Windows."""
        if os.name != "nt":
            return BrainResponse("network", "Wi-Fi profile listing is currently Windows-only.")
        try:
            proc = subprocess.run(["netsh", "wlan", "show", "profiles"], capture_output=True, text=True, timeout=10)
            out = (proc.stdout or "").strip()
            lines = [ln.strip() for ln in out.splitlines() if "All User Profile" in ln]
            if not lines:
                return BrainResponse("network", "No saved Wi-Fi profiles found.")
            pretty = "\n".join(lines[:80])
            return BrainResponse("network", "📶 Saved Wi-Fi profiles:\n" + pretty)
        except Exception as e:
            return BrainResponse("network", f"❌ Could not list Wi-Fi profiles: {e}")

    def _task_service_status(self, prompt: str) -> BrainResponse:
        """Check service status by name."""
        name = self._extract_after_colon(prompt).strip()
        if not name:
            m = re.search(r"service status\s+([\w.\-]+)", prompt.lower())
            if m:
                name = m.group(1)
        if not name:
            return BrainResponse("local_pc", "Use: service status: Spooler")
        try:
            if os.name == "nt":
                safe_name = name.replace("'", "")
                cmd = f"Get-Service -Name '{safe_name}' -ErrorAction SilentlyContinue | Select-Object Name,DisplayName,Status,StartType | Format-List"
                proc = subprocess.run(["powershell", "-NoProfile", "-Command", cmd], capture_output=True, text=True, timeout=10)
                out = (proc.stdout or "").strip()
                return BrainResponse("local_pc", out if out else f"Service not found: {name}")
            proc = subprocess.run(["systemctl", "status", name, "--no-pager"], capture_output=True, text=True, timeout=10)
            out = (proc.stdout or proc.stderr or "").strip()
            return BrainResponse("local_pc", out[:2500])
        except Exception as e:
            return BrainResponse("local_pc", f"❌ Service check failed: {e}")

    def _task_startup_apps(self, _: str = "") -> BrainResponse:
        """List startup programs."""
        try:
            if os.name == "nt":
                cmd = (
                    "Get-CimInstance Win32_StartupCommand | "
                    "Select-Object Name, Command, Location, User | "
                    "Format-Table -AutoSize"
                )
                proc = subprocess.run(["powershell", "-NoProfile", "-Command", cmd], capture_output=True, text=True, timeout=15)
                out = (proc.stdout or "").strip()
                return BrainResponse("local_pc", "🚀 Startup programs:\n" + (out[:3500] if out else "No entries found."))
            proc = subprocess.run(["sh", "-c", "ls -la ~/.config/autostart 2>/dev/null"], capture_output=True, text=True, timeout=8)
            out = (proc.stdout or "").strip()
            return BrainResponse("local_pc", "🚀 Startup programs:\n" + (out if out else "No autostart entries found."))
        except Exception as e:
            return BrainResponse("local_pc", f"❌ Startup app listing failed: {e}")
