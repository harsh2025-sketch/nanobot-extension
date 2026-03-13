# UltraBot Safe Full Rename Migration Plan

This plan performs a **full brand/package migration** with strict runtime compatibility and rollback safety.

## Safety Principles

- Keep `nanobot.*` imports working until final cutover is validated.
- Introduce `ultrabot.*` compatibility shims first.
- Move in small, testable stages with explicit breakage checks.
- Keep all stage transitions reversible via git commits.

## Stage 0 (Completed): Compatibility Baseline

Changes applied:
- Added `ultrabot` package wrappers forwarding to `nanobot` runtime.
- Added `python -m ultrabot` support via `ultrabot/__main__.py`.
- Added `ultrabot.cli.commands:app` wrapper.
- Packaging now includes both `nanobot` and `ultrabot` packages.
- Added channel setup/readiness parity for Discord.
- Added safer `--allow-from` parsing (`all` -> `*`) in channel setup.

Breakage checks:
- `python -m py_compile nanobot\cli\commands.py ultrabot\__init__.py ultrabot\__main__.py ultrabot\cli\commands.py`
- `python -m nanobot.cli.commands --help`
- `python -m ultrabot --help`
- `python -m nanobot.cli.commands channels status`

Rollback:
- Revert Stage 0 commit only.

## Stage 1 (Completed): User-Facing Identity Finalization (Low Risk)

Goal:
- Replace remaining user-facing "nanobot" wording with "UltraBot" where not part of compatibility notes, package paths, or repo URLs.

Changes applied:
- Replaced remaining user-facing CLI setup error text that hardcoded `~/.nanobot/config.json` with neutral config wording.
- Kept compatibility-sensitive names/paths untouched (`nanobot` import paths, `NANOBOT_CONFIG_PATH`, repo URLs).

Breakage checks:
- `python -m py_compile nanobot\cli\commands.py`
- `python -m ultrabot --help`
- `python -m nanobot.cli.commands status`

Rollback:
- Revert Stage 1 commit.

## Stage 2 (Completed): Import Alias Expansion (Medium Risk)

Goal:
- Add explicit forwarders for high-traffic modules under `ultrabot.*` (agent, config, channels, web) while preserving `nanobot.*` imports.

Approach:
- For each migrated namespace, add thin wrappers in `ultrabot/` that import and re-export from `nanobot/`.
- Do not remove original `nanobot` modules.

Changes applied:
- Added forwarder packages and modules:
  - `ultrabot.agent` (`__init__.py`, `loop.py`)
  - `ultrabot.config` (`__init__.py`, `loader.py`, `schema.py`, `paths.py`)
  - `ultrabot.channels` (`__init__.py`, `base.py`, `manager.py`, `registry.py`, `telegram.py`, `discord.py`)
  - `ultrabot.web` (`__init__.py`, `control_ui.py`)

Validation executed:
- Compile check on all Stage 2 wrappers and key runtime files passed.
- Runtime import check passed:
  - `import nanobot, ultrabot`
  - `import ultrabot.cli.commands, ultrabot.agent.loop, ultrabot.config.loader, ultrabot.channels.manager, ultrabot.web.control_ui`
- `python -m ultrabot selftest` passed.

Breakage checks:
- `python -m py_compile nanobot\**\*.py ultrabot\**\*.py` (or selected modules)
- `python -c "import nanobot, ultrabot; import ultrabot.cli.commands"`
- `python -m ultrabot selftest`

Rollback:
- Revert Stage 2 commit.

## Stage 3: Internal Reference Migration (High Risk)

Goal:
- Switch internal references gradually from `nanobot.*` to `ultrabot.*` where wrappers exist.

Approach:
- Batch-by-batch replacements (config, cli, agent, channels).
- Keep wrappers to avoid immediate hard breaks.

Progress:
- Batch 1 completed (CLI import migration to wrapper modules where available).
- Updated `nanobot/cli/commands.py` imports from `nanobot.*` to `ultrabot.*` for:
  - `config.loader`, `config.paths`, `config.schema`
  - `agent.loop`
  - `channels.manager`, `channels.registry`
  - `web.control_ui`
- Non-wrapper imports intentionally left unchanged.
- Batch 2 completed (core module import migration to wrapper modules where available).
- Updated:
  - `nanobot/config/loader.py`: `config.schema` -> `ultrabot.config.schema`
  - `nanobot/channels/manager.py`: `channels.base`, `config.schema`, `channels.registry` -> `ultrabot.*`
  - `nanobot/web/control_ui.py`: `agent.loop` -> `ultrabot.agent.loop`
- Batch 3 completed (session wrapper introduction and UI/gateway session-path migration).
- Added:
  - `ultrabot/session/__init__.py`
  - `ultrabot/session/manager.py`
- Updated:
  - `nanobot/web/control_ui.py`: `session.manager` -> `ultrabot.session.manager`
  - `nanobot/cli/commands.py`: gateway `SessionManager` import -> `ultrabot.session.manager`
  - `nanobot/bridge/acp.py`: `agent.loop` and `session.manager` -> `ultrabot.*`
- Batch 4 completed (remaining agent/session runtime callers migrated to the session wrapper).
- Updated:
  - `nanobot/agent/loop.py`: `session.manager` -> `ultrabot.session.manager`
  - `nanobot/agent/memory.py`: TYPE_CHECKING `session.manager` -> `ultrabot.session.manager`
  - `nanobot/session/__init__.py`: re-export via `ultrabot.session.manager`
- Batch 5 completed (broad safe core-runtime migration across wrapper-backed namespaces).
- Added wrapper namespaces and modules for:
  - `ultrabot.agent.context`, `ultrabot.agent.memory`, `ultrabot.agent.skills`, `ultrabot.agent.subagent`
  - `ultrabot.agent.tools.*`
  - `ultrabot.bus.*`
  - `ultrabot.bridge.*`
  - `ultrabot.cron.*`
  - `ultrabot.heartbeat.*`
  - `ultrabot.providers.*`
  - `ultrabot.utils.*`
  - `ultrabot.channels.webhook_server`
- Updated broad internal imports in main runtime modules under:
  - `nanobot/agent`
  - `nanobot/bus`
  - `nanobot/bridge`
  - `nanobot/channels`
  - `nanobot/config`
  - `nanobot/cron`
  - `nanobot/heartbeat`
  - `nanobot/providers`
  - `nanobot/session`
  - `nanobot/utils`
  - `nanobot/web`
- Remaining direct `nanobot.*` imports in the main runtime are intentionally limited to compatibility-sensitive or currently out-of-scope surfaces:
  - `nanobot.__main__`
  - `i18n`
  - platform examples/commands
  - `nodes`

Batch 6 completed (final pass — zero remaining nanobot.* imports in main runtime).
- Added wrapper namespaces and modules for:
  - `ultrabot.i18n` (`__init__.py`, `detector.py`, `languages.py`)
  - `ultrabot.platforms` (`__init__.py`, `base.py`, `manager.py`)
  - `ultrabot.platforms.macos` (`__init__.py`)
  - `ultrabot.platforms.ios` (`__init__.py`)
  - `ultrabot.platforms.android` (`__init__.py`)
  - `ultrabot.nodes` (`__init__.py`, `node_manager.py`, `platform_node_client.py`)
- Migrated remaining imports in:
  - `nanobot/__main__.py`: `nanobot.cli.commands` -> `ultrabot.cli.commands`
  - `nanobot/i18n/__init__.py`: `nanobot.i18n.detector`, `nanobot.i18n.languages` -> `ultrabot.*`
  - `nanobot/cli/platform_commands.py`: all `nanobot.platforms.*` and `nanobot.nodes` -> `ultrabot.*`
  - `nanobot/platforms/examples.py`: all `nanobot.platforms.*` and `nanobot.bus.*` -> `ultrabot.*`
- Fixed pre-existing import bug in `nanobot/platforms/macos/__init__.py`, `ios/__init__.py`, `android/__init__.py`:
  - `from ..platforms.base import ...` was resolving to non-existent `nanobot.platforms.platforms.base`
  - Corrected to `from ..base import ...`
- **Stage 3 is now 100% complete: zero `nanobot.*` imports remain in main runtime.**

Batch 1 validation:
- `python -m py_compile nanobot\cli\commands.py` passed.
- `python -m ultrabot --help` passed.
- `python -m ultrabot selftest` passed.

Batch 2 validation:
- `python -m py_compile nanobot\config\loader.py nanobot\channels\manager.py nanobot\web\control_ui.py nanobot\cli\commands.py` passed.
- Runtime import check passed:
  - `import ultrabot.config.loader, ultrabot.channels.manager, ultrabot.web.control_ui`
- `python -m ultrabot selftest` passed.
- `python -m nanobot.cli.commands status` passed.

Batch 3 validation:
- `python -m py_compile nanobot\web\control_ui.py nanobot\cli\commands.py nanobot\bridge\acp.py ultrabot\session\__init__.py ultrabot\session\manager.py` passed.
- Runtime import check passed:
  - `import ultrabot.session.manager, ultrabot.web.control_ui, ultrabot.cli.commands, nanobot.bridge.acp`
- `python -m nanobot.cli.commands selftest` passed.
- `python -m nanobot.cli.commands status` passed.

Batch 4 validation:
- `python -m py_compile nanobot\agent\loop.py nanobot\agent\memory.py nanobot\session\__init__.py` passed.
- Runtime import check passed:
  - `import nanobot.agent.loop, nanobot.agent.memory, nanobot.session, ultrabot.session.manager`
- `python -m nanobot.cli.commands selftest` passed.
- `python -m nanobot.cli.commands status` passed.
- Fresh gateway smoke test passed after clearing any stale `18791` listener:
  - `python -m nanobot.cli.commands gateway --verbose` started successfully
  - listeners observed on `127.0.0.1:18791` and `127.0.0.1:18792`
  - `http://127.0.0.1:18792` returned `200`

Batch 5 validation:
- Broad syntax validation passed across touched runtime directories and `ultrabot` wrappers when excluding one unrelated pre-existing syntax error in `nanobot/channels/imessage_channel.py`.
- Runtime import check passed:
  - `import nanobot.agent.loop, nanobot.agent.subagent, nanobot.channels.telegram, nanobot.channels.discord, nanobot.providers.litellm_provider, nanobot.session.manager, ultrabot.bus.queue, ultrabot.providers.registry, ultrabot.agent.tools.message`
- `python -m nanobot.cli.commands selftest` passed.
- `python -m nanobot.cli.commands status` passed.
- Final gateway smoke test passed:
  - listeners observed on `127.0.0.1:18791` and `127.0.0.1:18792`
  - `http://127.0.0.1:18792` returned `200`
- Remaining direct `nanobot.*` imports were re-audited and reduced to a small compatibility-sensitive set.

Batch 6 validation (2026-03-12):
- Zero `nanobot.*` imports remain in any main runtime file (confirmed by full scan).
- Compile check passed for all nanobot/ and ultrabot/ files (excluding pre-existing imessage_channel.py bug).
- Runtime import check passed:
  - `import ultrabot.i18n, ultrabot.i18n.detector, ultrabot.i18n.languages, ultrabot.platforms, ultrabot.platforms.macos, ultrabot.platforms.ios, ultrabot.platforms.android, ultrabot.platforms.manager, ultrabot.nodes, nanobot.i18n, nanobot.cli.platform_commands, nanobot.platforms.examples`
- `python -m nanobot.cli.commands selftest` passed (5/5 prompts).
- `python -m nanobot.cli.commands status` passed.

Gateway smoke test:
- Initial failure traced to `OSError: [Errno 10048]` on `127.0.0.1:18791` (Control UI WebSocket port already in use), not an import/runtime regression.
- After terminating the stale listener, `python -m nanobot.cli.commands gateway --verbose` started successfully.
- Verified active listener PID and HTTP reachability on `http://127.0.0.1:18792` with status `200`.

Breakage checks per batch:
- `python -m py_compile` on touched files
- `python -m ultrabot selftest`
- `python -m ultrabot gateway --verbose`
- Web UI smoke test (`http://127.0.0.1:18792`)

Rollback:
- Revert current batch commit.

## Stage 4: Optional Hard Cutover (Very High Risk, Optional)

Goal:
- Make `ultrabot` the canonical runtime package and deprecate `nanobot` imports.

Only proceed if:
- All tests and channel validations pass for at least one full release cycle.
- Consumers have migrated to `ultrabot` imports.

Approach:
- Keep `nanobot` as a compatibility shim package for one deprecation window.
- Emit deprecation warnings on `nanobot` imports.

Breakage checks:
- Full test suite
- CLI + gateway + Web UI + channel e2e checks
- Install wheel and test entry points on clean env

Rollback:
- Restore previous release tags and compatibility package layout.

## Channel E2E Validation (Token Deferred)

You can safely postpone tokens and still prepare config now.

Telegram prepare-now commands:
- `python -m nanobot.cli.commands channels telegram-setup --allow-from all --disable`
- `python -m nanobot.cli.commands channels telegram-check`

Discord prepare-now commands:
- `python -m nanobot.cli.commands channels discord-setup --allow-from all --disable`
- `python -m nanobot.cli.commands channels discord-check`

When token is available, enable and validate:
- Telegram:
  - `python -m nanobot.cli.commands channels telegram-setup --token "<BOT_TOKEN>" --allow-from "<USER_ID or *>" --enable`
  - `python -m nanobot.cli.commands channels telegram-check`
- Discord:
  - `python -m nanobot.cli.commands channels discord-setup --token "<BOT_TOKEN>" --allow-from "<USER_ID or *>" --enable`
  - `python -m nanobot.cli.commands channels discord-check`

Then run gateway and do live `/help` roundtrip from allowed sender.
