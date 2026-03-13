"""CLI commands for nanobot."""

import asyncio
import json
import os
import shutil
import signal
from pathlib import Path
import select
import subprocess
import sys

import typer
from rich.console import Console
from rich.markdown import Markdown
from rich.table import Table
from rich.text import Text

from prompt_toolkit import PromptSession
from prompt_toolkit.formatted_text import HTML
from prompt_toolkit.history import FileHistory
from prompt_toolkit.patch_stdout import patch_stdout

from nanobot import __version__, __logo__
from nanobot.config.schema import Config

app = typer.Typer(
    name="nanobot",
    help=f"{__logo__} nanobot - Personal AI Assistant",
    no_args_is_help=True,
)

console = Console()
EXIT_COMMANDS = {"exit", "quit", "/exit", "/quit", ":q"}

# ---------------------------------------------------------------------------
# CLI input: prompt_toolkit for editing, paste, history, and display
# ---------------------------------------------------------------------------

_PROMPT_SESSION: PromptSession | None = None
_SAVED_TERM_ATTRS = None  # original termios settings, restored on exit


def _flush_pending_tty_input() -> None:
    """Drop unread keypresses typed while the model was generating output."""
    try:
        fd = sys.stdin.fileno()
        if not os.isatty(fd):
            return
    except Exception:
        return

    try:
        import termios
        termios.tcflush(fd, termios.TCIFLUSH)
        return
    except Exception:
        pass

    try:
        while True:
            ready, _, _ = select.select([fd], [], [], 0)
            if not ready:
                break
            if not os.read(fd, 4096):
                break
    except Exception:
        return


def _restore_terminal() -> None:
    """Restore terminal to its original state (echo, line buffering, etc.)."""
    if _SAVED_TERM_ATTRS is None:
        return
    try:
        import termios
        termios.tcsetattr(sys.stdin.fileno(), termios.TCSADRAIN, _SAVED_TERM_ATTRS)
    except Exception:
        pass


def _init_prompt_session() -> None:
    """Create the prompt_toolkit session with persistent file history."""
    global _PROMPT_SESSION, _SAVED_TERM_ATTRS

    # Save terminal state so we can restore it on exit
    try:
        import termios
        _SAVED_TERM_ATTRS = termios.tcgetattr(sys.stdin.fileno())
    except Exception:
        pass

    history_file = Path.home() / ".nanobot" / "history" / "cli_history"
    history_file.parent.mkdir(parents=True, exist_ok=True)

    _PROMPT_SESSION = PromptSession(
        history=FileHistory(str(history_file)),
        enable_open_in_editor=False,
        multiline=False,   # Enter submits (single line mode)
    )


def _print_agent_response(response: str, render_markdown: bool) -> None:
    """Render assistant response with consistent terminal styling."""
    content = response or ""
    body = Markdown(content) if render_markdown else Text(content)
    console.print()
    console.print(f"[cyan]{__logo__} nanobot[/cyan]")
    console.print(body)
    console.print()


def _is_exit_command(command: str) -> bool:
    """Return True when input should end interactive chat."""
    return command.lower() in EXIT_COMMANDS


async def _read_interactive_input_async() -> str:
    """Read user input using prompt_toolkit (handles paste, history, display).

    prompt_toolkit natively handles:
    - Multiline paste (bracketed paste mode)
    - History navigation (up/down arrows)
    - Clean display (no ghost characters or artifacts)
    """
    if _PROMPT_SESSION is None:
        raise RuntimeError("Call _init_prompt_session() first")
    try:
        with patch_stdout():
            return await _PROMPT_SESSION.prompt_async(
                HTML("<b fg='ansiblue'>You:</b> "),
            )
    except EOFError as exc:
        raise KeyboardInterrupt from exc



def version_callback(value: bool):
    if value:
        console.print(f"{__logo__} nanobot v{__version__}")
        raise typer.Exit()


@app.callback()
def main(
    version: bool = typer.Option(
        None, "--version", "-v", callback=version_callback, is_eager=True
    ),
):
    """nanobot - Personal AI Assistant."""
    pass


# ============================================================================
# Onboard / Setup
# ============================================================================


@app.command()
def onboard(
    non_interactive: bool = typer.Option(False, "--non-interactive", help="Skip setup wizard and create/refresh config only"),
    config_path: str | None = typer.Option(None, "--config-path", help="Custom config path to use and save"),
):
    """Initialize nanobot configuration and run terminal setup wizard."""
    from nanobot.config.loader import get_config_path, load_config, save_config
    from nanobot.config.schema import Config
    from nanobot.utils.helpers import get_workspace_path

    resolved_path = _resolve_onboard_config_path(config_path, non_interactive)

    if resolved_path.exists():
        console.print(f"[yellow]Config already exists at {resolved_path}[/yellow]")
        console.print("  [bold]y[/bold] = overwrite with defaults (existing values will be lost)")
        console.print("  [bold]N[/bold] = refresh config, keeping existing values and adding new fields")
        if typer.confirm("Overwrite?"):
            config = Config()
            save_config(config, config_path=resolved_path)
            console.print(f"[green]✓[/green] Config reset to defaults at {resolved_path}")
        else:
            config = load_config(resolved_path)
            save_config(config, config_path=resolved_path)
            console.print(f"[green]✓[/green] Config refreshed at {resolved_path} (existing values preserved)")
    else:
        config = Config()
        save_config(config, config_path=resolved_path)
        console.print(f"[green]✓[/green] Created config at {resolved_path}")

    if not non_interactive:
        config = load_config(resolved_path)
        _run_setup_wizard(config)
        save_config(config, config_path=resolved_path)
        console.print(f"[green]✓[/green] Setup wizard completed and saved to {resolved_path}")

    # Create workspace
    workspace = get_workspace_path()

    if not workspace.exists():
        workspace.mkdir(parents=True, exist_ok=True)
        console.print(f"[green]✓[/green] Created workspace at {workspace}")

    # Create default bootstrap files
    _create_workspace_templates(workspace)

    console.print(f"\n{__logo__} nanobot is ready!")
    console.print("\nNext steps:")
    console.print(f"  1. Config path: [cyan]{resolved_path}[/cyan]")
    if str(resolved_path) != str(get_config_path()):
        console.print("  2. To keep using this custom path, set env var:")
        console.print(f"     [cyan]$env:NANOBOT_CONFIG_PATH = \"{resolved_path}\"[/cyan]")
        console.print("  3. Chat: [cyan]nanobot agent -m \"Hello!\"[/cyan]")
    else:
        console.print("  2. Provider already configured via wizard (or edit config manually if needed)")
        console.print("  3. Chat: [cyan]nanobot agent -m \"Hello!\"[/cyan]")
    console.print("\n[dim]Terminal usage works without channels: nanobot agent -m \"Hello!\"[/dim]")
    console.print("[dim]Enable channels in config.json if you want Telegram/WhatsApp/Discord, etc.[/dim]")


@app.command("setup")
def setup(
    non_interactive: bool = typer.Option(False, "--non-interactive", help="Skip setup wizard and create/refresh config only"),
    config_path: str | None = typer.Option(None, "--config-path", help="Custom config path to use and save"),
):
    """Alias for onboard (terminal setup wizard)."""
    onboard(non_interactive=non_interactive, config_path=config_path)


@app.command("quickstart")
def quickstart(
    model: str = typer.Option("llama3.2:1b", "--model", help="Default model to use"),
    ollama: bool = typer.Option(True, "--ollama/--no-ollama", help="Configure local Ollama endpoint"),
    telegram_token: str | None = typer.Option(None, "--telegram-token", help="Telegram bot token to enable Telegram channel"),
    telegram_allow_from: list[str] = typer.Option([], "--telegram-allow-from", help="Allowed Telegram user IDs/usernames (repeatable)"),
    wizard: bool = typer.Option(False, "--wizard/--no-wizard", help="Run interactive setup wizard before quickstart"),
    start: bool = typer.Option(True, "--start/--no-start", help="Start gateway after applying config"),
    port: int = typer.Option(18790, "--port", "-p", help="Gateway port"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Verbose output"),
    ui: bool = typer.Option(True, "--ui/--no-ui", help="Enable Control UI"),
):
    """One-command setup + optional Telegram + start gateway."""
    from nanobot.config.loader import load_config, save_config, get_config_path
    from nanobot.utils.helpers import get_workspace_path

    config_path = get_config_path()
    config = load_config()

    if wizard:
        _run_setup_wizard(config)

    if ollama:
        config.providers.custom.api_base = "http://127.0.0.1:11434/v1"
        config.providers.custom.api_key = "ollama"

    if model:
        config.agents.defaults.model = model

    if telegram_token:
        config.channels.telegram.enabled = True
        config.channels.telegram.token = telegram_token.strip()
        if telegram_allow_from:
            config.channels.telegram.allow_from = [x.strip() for x in telegram_allow_from if x.strip()]

    save_config(config, config_path=config_path)

    workspace = get_workspace_path()
    workspace.mkdir(parents=True, exist_ok=True)
    _create_workspace_templates(workspace)

    console.print("[green]✓[/green] Quickstart configuration saved")
    console.print(f"  Config: [cyan]{config_path}[/cyan]")
    console.print(f"  Model: [cyan]{config.agents.defaults.model}[/cyan]")
    console.print(f"  Telegram: [cyan]{'enabled' if config.channels.telegram.enabled else 'disabled'}[/cyan]")

    if not start:
        console.print("[green]✓[/green] Setup complete (gateway not started; use --start to launch)")
        return

    gateway(port=port, verbose=verbose, ui=ui)


def _resolve_onboard_config_path(config_path: str | None, non_interactive: bool) -> Path:
    """Resolve config path for onboarding, optionally prompting user for custom location."""
    from nanobot.config.loader import get_config_path

    if config_path:
        return Path(config_path).expanduser()

    default_path = get_config_path()
    if non_interactive:
        return default_path

    if os.getenv("NANOBOT_CONFIG_PATH", "").strip():
        return default_path

    if typer.confirm("Store config in a custom path?", default=False):
        proposed = str(Path.cwd() / "config.json")
        custom = typer.prompt("Config file path", default=proposed).strip()
        if custom:
            return Path(custom).expanduser()
    return default_path


def _run_setup_wizard(config: "Config") -> None:
    """Interactive setup wizard for providers, local LLM, channels, and platforms."""
    console.print("\n[bold cyan]Terminal Setup Wizard[/bold cyan]")
    console.print("Configure API/local LLM, channels, and platform commands from terminal.\n")

    use_local = typer.confirm("Prefer local LLM (Ollama) setup?", default=False)
    configured = False

    if use_local:
        configured = _setup_ollama_provider(config)

    if not configured:
        _setup_remote_or_custom_provider(config)

    _setup_channels_wizard(config)
    _setup_platform_wizard()


def _setup_ollama_provider(config: "Config") -> bool:
    """Configure Ollama (if available) through custom OpenAI-compatible endpoint."""
    ollama_bin = shutil.which("ollama")
    if not ollama_bin:
        console.print("[yellow]Ollama not found in PATH.[/yellow]")
        console.print("Install from: https://ollama.com/download")
        return False

    console.print(f"[green]✓[/green] Ollama detected: {ollama_bin}")
    model = typer.prompt("Ollama model name to use", default="llama3.2:3b").strip()

    if typer.confirm(f"Pull model '{model}' now?", default=True):
        try:
            console.print(f"Pulling [cyan]{model}[/cyan]...")
            subprocess.run([ollama_bin, "pull", model], check=True)
            console.print(f"[green]✓[/green] Pulled {model}")
        except Exception as e:
            console.print(f"[yellow]Could not pull model automatically: {e}[/yellow]")

    config.providers.custom.api_base = "http://127.0.0.1:11434/v1"
    config.providers.custom.api_key = "ollama"
    config.agents.defaults.model = model
    console.print("[green]✓[/green] Configured local Ollama via custom provider")
    return True


def _setup_remote_or_custom_provider(config: "Config") -> None:
    """Configure cloud provider API or generic OpenAI-compatible endpoint."""
    from nanobot.providers.registry import PROVIDERS

    specs = [s for s in PROVIDERS if s.name != "vllm"]
    choices = [s.name.replace("_", "-") for s in specs]
    console.print("[bold]Supported provider types:[/bold]")
    console.print("  " + ", ".join(choices))
    console.print("  any other OpenAI-compatible API endpoint can use: custom")

    default_provider = "openrouter"
    provider = typer.prompt("Choose provider", default=default_provider).strip().lower().replace("-", "_")

    spec = next((s for s in specs if s.name == provider), None)
    if spec is None:
        console.print("[yellow]Unknown provider; using custom provider flow.[/yellow]")
        provider = "custom"

    model_default = "openrouter/openai/gpt-oss-120b:free" if provider == "openrouter" else "gpt-4o-mini"
    model = typer.prompt("Default model", default=model_default).strip()
    config.agents.defaults.model = model

    if provider == "custom":
        api_base = typer.prompt("Custom API base URL", default="http://127.0.0.1:8000/v1").strip()
        api_key = typer.prompt("Custom API key (or any placeholder)", default="no-key", hide_input=True)
        config.providers.custom.api_base = api_base
        config.providers.custom.api_key = api_key
        console.print("[green]✓[/green] Custom provider configured")
        return

    if spec and spec.is_oauth:
        console.print(f"[yellow]{spec.label} uses OAuth login.[/yellow]")
        console.print(f"Run: [cyan]nanobot provider login {provider.replace('_', '-')}[/cyan]")
        return

    api_key = typer.prompt(f"{provider.replace('_', '-')} API key", hide_input=True).strip()
    provider_cfg = getattr(config.providers, provider)
    provider_cfg.api_key = api_key

    if spec and (spec.is_gateway or spec.default_api_base):
        api_base_default = spec.default_api_base or (provider_cfg.api_base or "")
        if typer.confirm("Set/override API base URL?", default=bool(api_base_default)):
            provider_cfg.api_base = typer.prompt("API base URL", default=api_base_default).strip()

    console.print(f"[green]✓[/green] Configured provider: {provider.replace('_', '-')}")


def _setup_channels_wizard(config: "Config") -> None:
    """Optional channel setup from terminal prompts."""
    console.print("\n[bold]Channel setup (optional)[/bold]")
    if typer.confirm("Enable Telegram channel now?", default=False):
        token = typer.prompt("Telegram bot token", hide_input=True).strip()
        config.channels.telegram.enabled = True
        config.channels.telegram.token = token
        console.print("[green]✓[/green] Telegram enabled")

    if typer.confirm("Enable Discord channel now?", default=False):
        token = typer.prompt("Discord bot token", hide_input=True).strip()
        config.channels.discord.enabled = True
        config.channels.discord.token = token
        console.print("[green]✓[/green] Discord enabled")

    if typer.confirm("Enable Slack channel now?", default=False):
        bot = typer.prompt("Slack bot token (xoxb-...)", hide_input=True).strip()
        app_token = typer.prompt("Slack app token (xapp-...)", hide_input=True).strip()
        config.channels.slack.enabled = True
        config.channels.slack.bot_token = bot
        config.channels.slack.app_token = app_token
        console.print("[green]✓[/green] Slack enabled")


def _setup_platform_wizard() -> None:
    """Optional platform command guidance from terminal."""
    console.print("\n[bold]Platform setup (optional)[/bold]")
    if not typer.confirm("Configure a platform command now?", default=False):
        return

    choice = typer.prompt(
        "Choose platform",
        default="android",
    ).strip().lower()

    if choice == "macos":
        console.print("Run: [cyan]nanobot platform start-macos[/cyan]")
    elif choice == "ios":
        device = typer.prompt("iOS device id", default="ios-device-1")
        console.print(f"Run: [cyan]nanobot platform start-ios --device-id {device}[/cyan]")
    elif choice == "android":
        device = typer.prompt("Android device id", default="android-device-1")
        console.print(f"Run: [cyan]nanobot platform start-android --device-id {device}[/cyan]")
    else:
        console.print("Run: [cyan]nanobot platform demo[/cyan]")




def _create_workspace_templates(workspace: Path):
    """Create default workspace template files."""
    templates = {
        "AGENTS.md": """# Agent Instructions

You are a helpful AI assistant. Be concise, accurate, and friendly.

## Guidelines

- Always explain what you're doing before taking actions
- Ask for clarification when the request is ambiguous
- Use tools to help accomplish tasks
- Remember important information in memory/MEMORY.md; past events are logged in memory/HISTORY.md
""",
        "SOUL.md": """# Soul

I am nanobot, a lightweight AI assistant.

## Personality

- Helpful and friendly
- Concise and to the point
- Curious and eager to learn

## Values

- Accuracy over speed
- User privacy and safety
- Transparency in actions
""",
        "USER.md": """# User

Information about the user goes here.

## Preferences

- Communication style: (casual/formal)
- Timezone: (your timezone)
- Language: (your preferred language)
""",
    }
    
    for filename, content in templates.items():
        file_path = workspace / filename
        if not file_path.exists():
            file_path.write_text(content)
            console.print(f"  [dim]Created {filename}[/dim]")
    
    # Create memory directory and MEMORY.md
    memory_dir = workspace / "memory"
    memory_dir.mkdir(exist_ok=True)
    memory_file = memory_dir / "MEMORY.md"
    if not memory_file.exists():
        memory_file.write_text("""# Long-term Memory

This file stores important information that should persist across sessions.

## User Information

(Important facts about the user)

## Preferences

(User preferences learned over time)

## Important Notes

(Things to remember)
""")
        console.print("  [dim]Created memory/MEMORY.md[/dim]")
    
    history_file = memory_dir / "HISTORY.md"
    if not history_file.exists():
        history_file.write_text("")
        console.print("  [dim]Created memory/HISTORY.md[/dim]")

    # Create skills directory for custom user skills
    skills_dir = workspace / "skills"
    skills_dir.mkdir(exist_ok=True)


def _make_provider(config: Config):
    """Create the appropriate LLM provider from config."""
    from nanobot.providers.litellm_provider import LiteLLMProvider
    from nanobot.providers.openai_codex_provider import OpenAICodexProvider
    from nanobot.providers.custom_provider import CustomProvider

    model = config.agents.defaults.model
    provider_name = config.get_provider_name(model)
    p = config.get_provider(model)

    # OpenAI Codex (OAuth)
    if provider_name == "openai_codex" or model.startswith("openai-codex/"):
        return OpenAICodexProvider(default_model=model)

    # Custom: direct OpenAI-compatible endpoint, bypasses LiteLLM
    if provider_name == "custom":
        return CustomProvider(
            api_key=p.api_key if p else "no-key",
            api_base=config.get_api_base(model) or "http://localhost:8000/v1",
            default_model=model,
        )

    from nanobot.providers.registry import find_by_name
    spec = find_by_name(provider_name)
    if (
        not model.startswith("bedrock/")
        and not (p and p.api_key)
        and not (spec and (spec.is_oauth or spec.is_local))
    ):
        console.print("[red]Error: No API key configured.[/red]")
        console.print("Set one in ~/.nanobot/config.json under providers section")
        raise typer.Exit(1)

    return LiteLLMProvider(
        api_key=p.api_key if p else None,
        api_base=config.get_api_base(model),
        default_model=model,
        extra_headers=p.extra_headers if p else None,
        provider_name=provider_name,
    )


# ============================================================================
# Gateway / Server
# ============================================================================


@app.command()
def gateway(
    port: int = typer.Option(18790, "--port", "-p", help="Gateway port"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Verbose output"),
    ui: bool = typer.Option(True, "--ui/--no-ui", help="Enable Control UI"),
    ui_host: str | None = typer.Option(None, "--ui-host", help="Control UI host"),
    ui_port: int | None = typer.Option(None, "--ui-port", help="Control UI port"),
):
    """Start the nanobot gateway."""
    from nanobot.config.loader import load_config, get_data_dir
    from nanobot.bus.queue import MessageBus
    from nanobot.agent.loop import AgentLoop
    from nanobot.channels.manager import ChannelManager
    from nanobot.session.manager import SessionManager
    from nanobot.cron.service import CronService
    from nanobot.cron.types import CronJob
    from nanobot.heartbeat.service import HeartbeatService
    
    if verbose:
        import logging
        logging.basicConfig(level=logging.DEBUG)
    
    console.print(f"{__logo__} Starting nanobot gateway on port {port}...")
    
    config = load_config()
    bus = MessageBus()
    provider = _make_provider(config)
    session_manager = SessionManager(config.workspace_path)
    
    # Create cron service first (callback set after agent creation)
    cron_store_path = get_data_dir() / "cron" / "jobs.json"
    cron = CronService(cron_store_path)
    
    # Create agent with cron service
    agent = AgentLoop(
        bus=bus,
        provider=provider,
        workspace=config.workspace_path,
        model=config.agents.defaults.model,
        temperature=config.agents.defaults.temperature,
        max_tokens=config.agents.defaults.max_tokens,
        max_iterations=config.agents.defaults.max_tool_iterations,
        memory_window=config.agents.defaults.memory_window,
        brave_api_key=config.tools.web.search.api_key or None,
        exec_config=config.tools.exec,
        cron_service=cron,
        restrict_to_workspace=config.tools.restrict_to_workspace,
        session_manager=session_manager,
        mcp_servers=config.tools.mcp_servers,
    )
    
    # Set cron callback (needs agent)
    async def on_cron_job(job: CronJob) -> str | None:
        """Execute a cron job through the agent."""
        response = await agent.process_direct(
            job.payload.message,
            session_key=f"cron:{job.id}",
            channel=job.payload.channel or "cli",
            chat_id=job.payload.to or "direct",
        )
        if job.payload.deliver and job.payload.to:
            from nanobot.bus.events import OutboundMessage
            await bus.publish_outbound(OutboundMessage(
                channel=job.payload.channel or "cli",
                chat_id=job.payload.to,
                content=response or ""
            ))
        return response
    cron.on_job = on_cron_job
    
    # Create channel manager
    channels = ChannelManager(config, bus)

    def _pick_heartbeat_target() -> tuple[str, str]:
        """Pick a routable channel/chat target for heartbeat-triggered messages."""
        enabled = set(channels.enabled_channels)
        for item in session_manager.list_sessions():
            key = item.get("key") or ""
            if ":" not in key:
                continue
            channel, chat_id = key.split(":", 1)
            if channel in {"cli", "system"}:
                continue
            if channel in enabled and chat_id:
                return channel, chat_id
        return "cli", "direct"

    # Create heartbeat service
    async def on_heartbeat_execute(tasks: str) -> str:
        """Execute heartbeat tasks through the full agent loop."""
        channel, chat_id = _pick_heartbeat_target()

        async def _silent(*_args, **_kwargs):
            return None

        return await agent.process_direct(
            tasks,
            session_key="heartbeat",
            channel=channel,
            chat_id=chat_id,
            on_progress=_silent,
        )

    async def on_heartbeat_notify(response: str) -> None:
        """Deliver heartbeat output to an external channel when available."""
        from nanobot.bus.events import OutboundMessage

        channel, chat_id = _pick_heartbeat_target()
        if channel == "cli":
            return
        await bus.publish_outbound(
            OutboundMessage(channel=channel, chat_id=chat_id, content=response)
        )

    hb_cfg = config.gateway.heartbeat
    heartbeat = HeartbeatService(
        workspace=config.workspace_path,
        provider=provider,
        model=agent.model,
        on_execute=on_heartbeat_execute,
        on_notify=on_heartbeat_notify,
        interval_s=hb_cfg.interval_s,
        enabled=hb_cfg.enabled,
    )
    
    if channels.enabled_channels:
        console.print(f"[green]✓[/green] Channels enabled: {', '.join(channels.enabled_channels)}")
    else:
        console.print("[yellow]No channels enabled[/yellow] (this is fine for terminal-only usage)")
        console.print("[dim]Use: nanobot agent --message \"Hello\" in another terminal[/dim]")
    
    cron_status = cron.status()
    if cron_status["jobs"] > 0:
        console.print(f"[green]✓[/green] Cron: {cron_status['jobs']} scheduled jobs")
    
    console.print(f"[green]✓[/green] Heartbeat: every {hb_cfg.interval_s}s")
    
    async def run():
        control_ui = None
        try:
            if ui and config.gateway.control_ui_enabled:
                from nanobot.web.control_ui import ControlUIServer
                control_ui = ControlUIServer(
                    host=ui_host or config.gateway.control_ui_host,
                    port=ui_port or config.gateway.control_ui_port,
                    agent=agent,
                    sessions=session_manager,
                )
                await control_ui.start()
                console.print(
                    f"[green]✓[/green] Control UI: http://{control_ui.host}:{control_ui.port + 1}"
                )

            await cron.start()
            await heartbeat.start()
            await asyncio.gather(
                agent.run(),
                channels.start_all(),
            )
        except KeyboardInterrupt:
            console.print("\nShutting down...")
        finally:
            await agent.close_mcp()
            if control_ui:
                await control_ui.stop()
            heartbeat.stop()
            cron.stop()
            agent.stop()
            await channels.stop_all()
    
    asyncio.run(run())




# ============================================================================
# Agent Commands
# ============================================================================


@app.command()
def agent(
    message: str = typer.Option(None, "--message", "-m", help="Message to send to the agent"),
    session_id: str = typer.Option("cli:direct", "--session", "-s", help="Session ID"),
    markdown: bool = typer.Option(True, "--markdown/--no-markdown", help="Render assistant output as Markdown"),
    logs: bool = typer.Option(False, "--logs/--no-logs", help="Show nanobot runtime logs during chat"),
):
    """Interact with the agent directly."""
    from nanobot.config.loader import load_config, get_data_dir
    from nanobot.bus.queue import MessageBus
    from nanobot.agent.loop import AgentLoop
    from nanobot.cron.service import CronService
    from loguru import logger
    
    config = load_config()
    
    bus = MessageBus()
    provider = _make_provider(config)

    # Create cron service for tool usage (no callback needed for CLI unless running)
    cron_store_path = get_data_dir() / "cron" / "jobs.json"
    cron = CronService(cron_store_path)

    if logs:
        logger.enable("nanobot")
    else:
        logger.disable("nanobot")
    
    agent_loop = AgentLoop(
        bus=bus,
        provider=provider,
        workspace=config.workspace_path,
        model=config.agents.defaults.model,
        temperature=config.agents.defaults.temperature,
        max_tokens=config.agents.defaults.max_tokens,
        max_iterations=config.agents.defaults.max_tool_iterations,
        memory_window=config.agents.defaults.memory_window,
        brave_api_key=config.tools.web.search.api_key or None,
        exec_config=config.tools.exec,
        cron_service=cron,
        restrict_to_workspace=config.tools.restrict_to_workspace,
        mcp_servers=config.tools.mcp_servers,
    )
    
    # Show spinner when logs are off (no output to miss); skip when logs are on
    def _thinking_ctx():
        if logs:
            from contextlib import nullcontext
            return nullcontext()
        # Animated spinner is safe to use with prompt_toolkit input handling
        return console.status("[dim]nanobot is thinking...[/dim]", spinner="dots")

    async def _cli_progress(content: str) -> None:
        console.print(f"  [dim]↳ {content}[/dim]")

    if message:
        # Single message mode
        async def run_once():
            with _thinking_ctx():
                response = await agent_loop.process_direct(message, session_id, on_progress=_cli_progress)
            _print_agent_response(response, render_markdown=markdown)
            await agent_loop.close_mcp()
        
        asyncio.run(run_once())
    else:
        # Interactive mode
        _init_prompt_session()
        console.print(f"{__logo__} Interactive mode (type [bold]exit[/bold] or [bold]Ctrl+C[/bold] to quit)\n")

        def _exit_on_sigint(signum, frame):
            _restore_terminal()
            console.print("\nGoodbye!")
            os._exit(0)

        signal.signal(signal.SIGINT, _exit_on_sigint)


# ============================================================================
# Diagnostics
# ============================================================================


@app.command()
def doctor(
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Verbose output"),
):
    """Run diagnostics and configuration checks."""
    from nanobot.advanced.systems import DiagnosticsDoctor

    async def run_checks():
        doctor = DiagnosticsDoctor()
        result = await doctor.run_diagnostics()
        return result

    if verbose:
        console.print("Running nanobot diagnostics...")

    result = asyncio.run(run_checks())
    console.print(Markdown(f"```json\n{json.dumps(result, indent=2)}\n```"))


# ============================================================================
# ACP Bridge
# ============================================================================


@app.command()
def acp(
    session: str = typer.Option("acp:default", "--session", help="Default ACP session key"),
):
    """Run ACP bridge over stdio (NDJSON)."""
    from nanobot.config.loader import load_config, get_data_dir
    from nanobot.bus.queue import MessageBus
    from nanobot.agent.loop import AgentLoop
    from nanobot.cron.service import CronService
    from nanobot.bridge.acp import ACPBridge, ACPConfig
    from nanobot.session.manager import SessionManager

    config = load_config()
    bus = MessageBus()
    provider = _make_provider(config)

    cron_store_path = get_data_dir() / "cron" / "jobs.json"
    cron = CronService(cron_store_path)

    agent_loop = AgentLoop(
        bus=bus,
        provider=provider,
        workspace=config.workspace_path,
        model=config.agents.defaults.model,
        temperature=config.agents.defaults.temperature,
        max_tokens=config.agents.defaults.max_tokens,
        max_iterations=config.agents.defaults.max_tool_iterations,
        memory_window=config.agents.defaults.memory_window,
        brave_api_key=config.tools.web.search.api_key or None,
        exec_config=config.tools.exec,
        cron_service=cron,
        restrict_to_workspace=config.tools.restrict_to_workspace,
        session_manager=SessionManager(config.workspace_path),
        mcp_servers=config.tools.mcp_servers,
    )

    bridge = ACPBridge(agent_loop, agent_loop.sessions, ACPConfig(default_session=session))
    asyncio.run(bridge.run())


# ============================================================================
# Channel Commands
# ============================================================================


channels_app = typer.Typer(help="Manage channels")
app.add_typer(channels_app, name="channels")


@channels_app.command("status")
def channels_status():
    """Show channel status."""
    from nanobot.config.loader import load_config

    config = load_config()

    table = Table(title="Channel Status")
    table.add_column("Channel", style="cyan")
    table.add_column("Enabled", style="green")
    table.add_column("Configuration", style="yellow")

    # WhatsApp
    wa = config.channels.whatsapp
    table.add_row(
        "WhatsApp",
        "✓" if wa.enabled else "✗",
        wa.bridge_url
    )

    dc = config.channels.discord
    table.add_row(
        "Discord",
        "✓" if dc.enabled else "✗",
        dc.gateway_url
    )

    # Feishu
    fs = config.channels.feishu
    fs_config = f"app_id: {fs.app_id[:10]}..." if fs.app_id else "[dim]not configured[/dim]"
    table.add_row(
        "Feishu",
        "✓" if fs.enabled else "✗",
        fs_config
    )

    # Mochat
    mc = config.channels.mochat
    mc_base = mc.base_url or "[dim]not configured[/dim]"
    table.add_row(
        "Mochat",
        "✓" if mc.enabled else "✗",
        mc_base
    )
    
    # Telegram
    tg = config.channels.telegram
    tg_config = f"token: {tg.token[:10]}..." if tg.token else "[dim]not configured[/dim]"
    table.add_row(
        "Telegram",
        "✓" if tg.enabled else "✗",
        tg_config
    )

    # Slack
    slack = config.channels.slack
    slack_config = "socket" if slack.app_token and slack.bot_token else "[dim]not configured[/dim]"
    table.add_row(
        "Slack",
        "✓" if slack.enabled else "✗",
        slack_config
    )

    console.print(table)


def _get_bridge_dir() -> Path:
    """Get the bridge directory, setting it up if needed."""
    import shutil
    import subprocess
    
    # User's bridge location
    user_bridge = Path.home() / ".nanobot" / "bridge"
    
    # Check if already built
    if (user_bridge / "dist" / "index.js").exists():
        return user_bridge
    
    # Check for npm
    if not shutil.which("npm"):
        console.print("[red]npm not found. Please install Node.js >= 18.[/red]")
        raise typer.Exit(1)
    
    # Find source bridge: first check package data, then source dir
    pkg_bridge = Path(__file__).parent.parent / "bridge"  # nanobot/bridge (installed)
    src_bridge = Path(__file__).parent.parent.parent / "bridge"  # repo root/bridge (dev)
    
    source = None
    if (pkg_bridge / "package.json").exists():
        source = pkg_bridge
    elif (src_bridge / "package.json").exists():
        source = src_bridge
    
    if not source:
        console.print("[red]Bridge source not found.[/red]")
        console.print("Try reinstalling: pip install --force-reinstall nanobot")
        raise typer.Exit(1)
    
    console.print(f"{__logo__} Setting up bridge...")
    
    # Copy to user directory
    user_bridge.parent.mkdir(parents=True, exist_ok=True)
    if user_bridge.exists():
        shutil.rmtree(user_bridge)
    shutil.copytree(source, user_bridge, ignore=shutil.ignore_patterns("node_modules", "dist"))
    
    # Install and build
    try:
        console.print("  Installing dependencies...")
        subprocess.run(["npm", "install"], cwd=user_bridge, check=True, capture_output=True)
        
        console.print("  Building...")
        subprocess.run(["npm", "run", "build"], cwd=user_bridge, check=True, capture_output=True)
        
        console.print("[green]✓[/green] Bridge ready\n")
    except subprocess.CalledProcessError as e:
        console.print(f"[red]Build failed: {e}[/red]")
        if e.stderr:
            console.print(f"[dim]{e.stderr.decode()[:500]}[/dim]")
        raise typer.Exit(1)
    
    return user_bridge


@channels_app.command("login")
def channels_login():
    """Link device via QR code."""
    import subprocess
    from nanobot.config.loader import load_config
    
    config = load_config()
    bridge_dir = _get_bridge_dir()
    
    console.print(f"{__logo__} Starting bridge...")
    console.print("Scan the QR code to connect.\n")
    
    env = {**os.environ}
    if config.channels.whatsapp.bridge_token:
        env["BRIDGE_TOKEN"] = config.channels.whatsapp.bridge_token
    
    try:
        subprocess.run(["npm", "start"], cwd=bridge_dir, check=True, env=env)
    except subprocess.CalledProcessError as e:
        console.print(f"[red]Bridge failed: {e}[/red]")
    except FileNotFoundError:
        console.print("[red]npm not found. Please install Node.js.[/red]")


# ============================================================================
# Cron Commands
# ============================================================================

cron_app = typer.Typer(help="Manage scheduled tasks")
app.add_typer(cron_app, name="cron")


@cron_app.command("list")
def cron_list(
    all: bool = typer.Option(False, "--all", "-a", help="Include disabled jobs"),
):
    """List scheduled jobs."""
    from nanobot.config.loader import get_data_dir
    from nanobot.cron.service import CronService
    
    store_path = get_data_dir() / "cron" / "jobs.json"
    service = CronService(store_path)
    
    jobs = service.list_jobs(include_disabled=all)
    
    if not jobs:
        console.print("No scheduled jobs.")
        return
    
    table = Table(title="Scheduled Jobs")
    table.add_column("ID", style="cyan")
    table.add_column("Name")
    table.add_column("Schedule")
    table.add_column("Status")
    table.add_column("Next Run")
    
    import time
    from datetime import datetime as _dt
    from zoneinfo import ZoneInfo
    for job in jobs:
        # Format schedule
        if job.schedule.kind == "every":
            sched = f"every {(job.schedule.every_ms or 0) // 1000}s"
        elif job.schedule.kind == "cron":
            sched = f"{job.schedule.expr or ''} ({job.schedule.tz})" if job.schedule.tz else (job.schedule.expr or "")
        else:
            sched = "one-time"
        
        # Format next run
        next_run = ""
        if job.state.next_run_at_ms:
            ts = job.state.next_run_at_ms / 1000
            try:
                tz = ZoneInfo(job.schedule.tz) if job.schedule.tz else None
                next_run = _dt.fromtimestamp(ts, tz).strftime("%Y-%m-%d %H:%M")
            except Exception:
                next_run = time.strftime("%Y-%m-%d %H:%M", time.localtime(ts))
        
        status = "[green]enabled[/green]" if job.enabled else "[dim]disabled[/dim]"
        
        table.add_row(job.id, job.name, sched, status, next_run)
    
    console.print(table)


@cron_app.command("add")
def cron_add(
    name: str = typer.Option(..., "--name", "-n", help="Job name"),
    message: str = typer.Option(..., "--message", "-m", help="Message for agent"),
    every: int = typer.Option(None, "--every", "-e", help="Run every N seconds"),
    cron_expr: str = typer.Option(None, "--cron", "-c", help="Cron expression (e.g. '0 9 * * *')"),
    tz: str | None = typer.Option(None, "--tz", help="IANA timezone for cron (e.g. 'America/Vancouver')"),
    at: str = typer.Option(None, "--at", help="Run once at time (ISO format)"),
    deliver: bool = typer.Option(False, "--deliver", "-d", help="Deliver response to channel"),
    to: str = typer.Option(None, "--to", help="Recipient for delivery"),
    channel: str = typer.Option(None, "--channel", help="Channel for delivery (e.g. 'telegram', 'whatsapp')"),
):
    """Add a scheduled job."""
    from nanobot.config.loader import get_data_dir
    from nanobot.cron.service import CronService
    from nanobot.cron.types import CronSchedule
    
    if tz and not cron_expr:
        console.print("[red]Error: --tz can only be used with --cron[/red]")
        raise typer.Exit(1)

    # Determine schedule type
    if every:
        schedule = CronSchedule(kind="every", every_ms=every * 1000)
    elif cron_expr:
        schedule = CronSchedule(kind="cron", expr=cron_expr, tz=tz)
    elif at:
        import datetime
        dt = datetime.datetime.fromisoformat(at)
        schedule = CronSchedule(kind="at", at_ms=int(dt.timestamp() * 1000))
    else:
        console.print("[red]Error: Must specify --every, --cron, or --at[/red]")
        raise typer.Exit(1)
    
    store_path = get_data_dir() / "cron" / "jobs.json"
    service = CronService(store_path)
    
    job = service.add_job(
        name=name,
        schedule=schedule,
        message=message,
        deliver=deliver,
        to=to,
        channel=channel,
    )
    
    console.print(f"[green]✓[/green] Added job '{job.name}' ({job.id})")


@cron_app.command("remove")
def cron_remove(
    job_id: str = typer.Argument(..., help="Job ID to remove"),
):
    """Remove a scheduled job."""
    from nanobot.config.loader import get_data_dir
    from nanobot.cron.service import CronService
    
    store_path = get_data_dir() / "cron" / "jobs.json"
    service = CronService(store_path)
    
    if service.remove_job(job_id):
        console.print(f"[green]✓[/green] Removed job {job_id}")
    else:
        console.print(f"[red]Job {job_id} not found[/red]")


@cron_app.command("enable")
def cron_enable(
    job_id: str = typer.Argument(..., help="Job ID"),
    disable: bool = typer.Option(False, "--disable", help="Disable instead of enable"),
):
    """Enable or disable a job."""
    from nanobot.config.loader import get_data_dir
    from nanobot.cron.service import CronService
    
    store_path = get_data_dir() / "cron" / "jobs.json"
    service = CronService(store_path)
    
    job = service.enable_job(job_id, enabled=not disable)
    if job:
        status = "disabled" if disable else "enabled"
        console.print(f"[green]✓[/green] Job '{job.name}' {status}")
    else:
        console.print(f"[red]Job {job_id} not found[/red]")


@cron_app.command("run")
def cron_run(
    job_id: str = typer.Argument(..., help="Job ID to run"),
    force: bool = typer.Option(False, "--force", "-f", help="Run even if disabled"),
):
    """Manually run a job."""
    from nanobot.config.loader import get_data_dir
    from nanobot.cron.service import CronService
    
    store_path = get_data_dir() / "cron" / "jobs.json"
    service = CronService(store_path)
    
    async def run():
        return await service.run_job(job_id, force=force)
    
    if asyncio.run(run()):
        console.print(f"[green]✓[/green] Job executed")
    else:
        console.print(f"[red]Failed to run job {job_id}[/red]")


# ============================================================================
# Status Commands
# ============================================================================


@app.command()
def status():
    """Show nanobot status."""
    from nanobot.config.loader import load_config, get_config_path

    config_path = get_config_path()
    config = load_config()
    workspace = config.workspace_path

    console.print(f"{__logo__} nanobot Status\n")

    console.print(f"Config: {config_path} {'[green]✓[/green]' if config_path.exists() else '[red]✗[/red]'}")
    console.print(f"Workspace: {workspace} {'[green]✓[/green]' if workspace.exists() else '[red]✗[/red]'}")

    if config_path.exists():
        from nanobot.providers.registry import PROVIDERS

        console.print(f"Model: {config.agents.defaults.model}")
        
        # Check API keys from registry
        for spec in PROVIDERS:
            p = getattr(config.providers, spec.name, None)
            if p is None:
                continue
            if spec.is_oauth:
                console.print(f"{spec.label}: [green]✓ (OAuth)[/green]")
            elif spec.is_local:
                # Local deployments show api_base instead of api_key
                if p.api_base:
                    console.print(f"{spec.label}: [green]✓ {p.api_base}[/green]")
                else:
                    console.print(f"{spec.label}: [dim]not set[/dim]")
            else:
                has_key = bool(p.api_key)
                console.print(f"{spec.label}: {'[green]✓[/green]' if has_key else '[dim]not set[/dim]'}")


# ============================================================================
# OAuth Login
# ============================================================================

provider_app = typer.Typer(help="Manage providers")
app.add_typer(provider_app, name="provider")


_LOGIN_HANDLERS: dict[str, callable] = {}


def _register_login(name: str):
    def decorator(fn):
        _LOGIN_HANDLERS[name] = fn
        return fn
    return decorator


@provider_app.command("login")
def provider_login(
    provider: str = typer.Argument(..., help="OAuth provider (e.g. 'openai-codex', 'github-copilot')"),
):
    """Authenticate with an OAuth provider."""
    from nanobot.providers.registry import PROVIDERS

    key = provider.replace("-", "_")
    spec = next((s for s in PROVIDERS if s.name == key and s.is_oauth), None)
    if not spec:
        names = ", ".join(s.name.replace("_", "-") for s in PROVIDERS if s.is_oauth)
        console.print(f"[red]Unknown OAuth provider: {provider}[/red]  Supported: {names}")
        raise typer.Exit(1)

    handler = _LOGIN_HANDLERS.get(spec.name)
    if not handler:
        console.print(f"[red]Login not implemented for {spec.label}[/red]")
        raise typer.Exit(1)

    console.print(f"{__logo__} OAuth Login - {spec.label}\n")
    handler()


@_register_login("openai_codex")
def _login_openai_codex() -> None:
    try:
        from oauth_cli_kit import get_token, login_oauth_interactive
        token = None
        try:
            token = get_token()
        except Exception:
            pass
        if not (token and token.access):
            console.print("[cyan]Starting interactive OAuth login...[/cyan]\n")
            token = login_oauth_interactive(
                print_fn=lambda s: console.print(s),
                prompt_fn=lambda s: typer.prompt(s),
            )
        if not (token and token.access):
            console.print("[red]✗ Authentication failed[/red]")
            raise typer.Exit(1)
        console.print(f"[green]✓ Authenticated with OpenAI Codex[/green]  [dim]{token.account_id}[/dim]")
    except ImportError:
        console.print("[red]oauth_cli_kit not installed. Run: pip install oauth-cli-kit[/red]")
        raise typer.Exit(1)


@_register_login("github_copilot")
def _login_github_copilot() -> None:
    import asyncio

    console.print("[cyan]Starting GitHub Copilot device flow...[/cyan]\n")

    async def _trigger():
        from litellm import acompletion
        await acompletion(model="github_copilot/gpt-4o", messages=[{"role": "user", "content": "hi"}], max_tokens=1)

    try:
        asyncio.run(_trigger())
        console.print("[green]✓ Authenticated with GitHub Copilot[/green]")
    except Exception as e:
        console.print(f"[red]Authentication error: {e}[/red]")
        raise typer.Exit(1)


# ============================================================================
# Platform Nodes (Optional)
# ============================================================================
# Optional platform support - only added if nanobot.platforms is available
# This keeps the core codebase unchanged while enabling platform features

try:
    from nanobot.cli.platform_commands import platform_app
    app.add_typer(platform_app, name="platform")
except ImportError:
    # Platform support not available - continue without it
    pass


if __name__ == "__main__":
    app()
