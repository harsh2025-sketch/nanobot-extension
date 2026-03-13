# NeuroSymbolic Lab (Offline, No API Key)

This is a **separate local testing module**.
It does **not** use OpenRouter, OpenAI, or any remote LLM APIs.

## What it is

- Rule-based prompt router
- Symbolic utilities for file/search/docs tasks
- Deterministic template outputs for coding/study/debug requests
- Optional local file write mode for specific actions
- API-down fallback mode for local execution
- General conversation support for normal user interaction

## What it is not

- Not a replacement for full LLM reasoning
- Not connected to existing ultrabot channels/agent loop
- Not meant for production autonomous execution

## Run

From `ultrabot` folder:

```powershell
# one-shot
python -m neurosymbolic_lab.cli "introduce yourself in 3 lines"

# interactive
python -m neurosymbolic_lab.cli --interactive

# allow file writing for file-tool actions
python -m neurosymbolic_lab.cli --interactive --allow-write
```

## Commands in interactive mode

- `/status`
- `/usage`
- `/think low|medium|high`
- `/verbose on|off`
- `/new` or `/reset`

## Supported prompt buckets (examples)

### Basic Chat
- `introduce yourself in 3 lines`
- `explain async vs sync with examples`
- `summarize this text in 5 bullets: ...`
- `rewrite this in professional tone: ...`
- `translate this to Hindi: ...`
- `hello` / `how are you` / `what can you do`
- `tell me a joke` / `motivate me`

### API Fallback Trigger
- `api not available, continue in local mode`
- `no api key, switch to fallback mode`

### Study / Productivity
- `make a 7-day plan to learn Python`
- `create a daily timetable for exam prep`
- `give me pomodoro plan for 4 hours deep work`
- `turn this syllabus into a revision checklist: ...`
- `generate 20 interview questions on OOP with short answers`

### Coding Assistant
- `write Python code for binary search + tests`
- `refactor this code: ...`
- `find bugs in this snippet: ...`
- `create a FastAPI CRUD app scaffold`
- `generate a regex for email and phone validation`

### Debug / Dev Support
- `i got this error: ModuleNotFoundError... help root cause`
- `why is this code slow?`
- `add logging and exception handling pattern`
- `convert this blocking code to async`
- `write unit tests for this function`

### Docs / Project Assistant
- `read this README and create a quick-start`
- `draft release notes from these commits: ...`
- `write a CONTRIBUTING.md template`
- `create a troubleshooting section for setup errors`
- `generate a deployment checklist for Windows`

### File / Workspace Tools
- `list files in current workspace`
- `find all references to 'openrouter'`
- `create TEST_PLAN.md with terminal tests`
- `update HOW_TO_USE.md to add Telegram setup tip`
- `search for TODO/FIXME across project`

### Local PC Tasks (Offline)
- `show system info`
- `show disk usage`
- `show running processes`
- `show environment variables`
- `show network info`
- `current date and time`
- `list largest files`
- `count lines in project`
- `count files by extension`
- `show directory tree: depth 2`
- `find empty directories`
- `find recent files: 25`
- `find duplicate filenames`
- `search text in files: openrouter`
- `read file: README.md`
- `create note: notes/today.txt | hello`
- `append note: notes/today.txt | next line`
- `create folder: notes/archive`
- `copy file: README.md | backup/README.md`
- `move file: temp/a.txt | temp/archive/a.txt`
- `delete file: temp/a.txt`
- `zip folder: docs | backup/docs.zip`
- `unzip file: backup/docs.zip | extracted/docs`
- `run command: where python`
- `generate password`
- `generate uuid`
- `random number: 10 50`
- `calculate: (12+5)*3/2`
- `word count: this is sample text`
- `sort lines: c,b,a`
- `unique lines: a,a,b,b,c`
- `hash text sha256: your text`
- `checksum file sha256: README.md`
- `compare files: README.md | HOW_TO_USE.md`
- `base64 encode: hello world`
- `base64 decode: aGVsbG8gd29ybGQ=`
- `json pretty: {"a":1,"b":[2,3]}`
- `csv summary: data/report.csv`

### Web / Research (lightweight)
- `find today's top 5 AI news`
- `compare OpenRouter free models`
- `fetch OpenRouter privacy settings help`
- `best practices for Telegram bot security`
- `python logging and asyncio docs summary`

## Notes

- Web tasks use simple public fetches; if network is blocked, the response explains fallback.
- File-write tasks require `--allow-write` (`create note`, `append note`, `create TEST_PLAN.md`, `update HOW_TO_USE.md`).
- Everything runs locally for testing purpose only.


