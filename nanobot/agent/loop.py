"""Agent loop: the core processing engine."""

import asyncio
from contextlib import AsyncExitStack
import json
import json_repair
from pathlib import Path
import re
from typing import Any, Awaitable, Callable

from loguru import logger

from nanobot.bus.events import InboundMessage, OutboundMessage
from nanobot.bus.queue import MessageBus
from nanobot.providers.base import LLMProvider
from nanobot.agent.context import ContextBuilder
from nanobot.agent.tools.registry import ToolRegistry
from nanobot.agent.tools.filesystem import ReadFileTool, WriteFileTool, EditFileTool, ListDirTool
from nanobot.agent.tools.shell import ExecTool
from nanobot.agent.tools.web import WebSearchTool, WebFetchTool
from nanobot.agent.tools.message import MessageTool
from nanobot.agent.tools.spawn import SpawnTool
from nanobot.agent.tools.cron import CronTool
from nanobot.agent.memory import MemoryStore
from nanobot.agent.subagent import SubagentManager
from nanobot.session.manager import Session, SessionManager


class AgentLoop:
    """
    The agent loop is the core processing engine.

    It:
    1. Receives messages from the bus
    2. Builds context with history, memory, skills
    3. Calls the LLM
    4. Executes tool calls
    5. Sends responses back
    """

    def __init__(
        self,
        bus: MessageBus,
        provider: LLMProvider,
        workspace: Path,
        model: str | None = None,
        max_iterations: int = 20,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        memory_window: int = 50,
        brave_api_key: str | None = None,
        exec_config: "ExecToolConfig | None" = None,
        cron_service: "CronService | None" = None,
        restrict_to_workspace: bool = False,
        session_manager: SessionManager | None = None,
        mcp_servers: dict | None = None,
    ):
        from nanobot.config.schema import ExecToolConfig
        from nanobot.cron.service import CronService
        self.bus = bus
        self.provider = provider
        self.workspace = workspace
        self.model = model or provider.get_default_model()
        self.max_iterations = max_iterations
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.memory_window = memory_window if memory_window is not None else 50
        self.brave_api_key = brave_api_key
        self.exec_config = exec_config or ExecToolConfig()
        self.cron_service = cron_service
        self.restrict_to_workspace = restrict_to_workspace

        self.context = ContextBuilder(workspace)
        self.sessions = session_manager or SessionManager(workspace)
        self.tools = ToolRegistry()
        self.subagents = SubagentManager(
            provider=provider,
            workspace=workspace,
            bus=bus,
            model=self.model,
            brave_api_key=brave_api_key,
            exec_config=self.exec_config,
            restrict_to_workspace=restrict_to_workspace,
        )
        
        self._running = False
        self._mcp_servers = mcp_servers or {}
        self._mcp_stack: AsyncExitStack | None = None
        self._mcp_connected = False
        self._register_default_tools()
    
    def _register_default_tools(self) -> None:
        """Register the default set of tools."""
        # File tools (restrict to workspace if configured)
        allowed_dir = self.workspace if self.restrict_to_workspace else None
        self.tools.register(ReadFileTool(workspace=self.workspace, allowed_dir=allowed_dir))
        self.tools.register(WriteFileTool(workspace=self.workspace, allowed_dir=allowed_dir))
        self.tools.register(EditFileTool(workspace=self.workspace, allowed_dir=allowed_dir))
        self.tools.register(ListDirTool(workspace=self.workspace, allowed_dir=allowed_dir))
        
        # Shell tool
        self.tools.register(ExecTool(
            working_dir=str(self.workspace),
            timeout=self.exec_config.timeout,
            restrict_to_workspace=self.restrict_to_workspace,
        ))
        
        # Web tools
        self.tools.register(WebSearchTool(api_key=self.brave_api_key))
        self.tools.register(WebFetchTool())
        
        # Message tool
        message_tool = MessageTool(send_callback=self.bus.publish_outbound)
        self.tools.register(message_tool)
        
        # Spawn tool (for subagents)
        spawn_tool = SpawnTool(manager=self.subagents)
        self.tools.register(spawn_tool)
        
        # Cron tool (for scheduling)
        if self.cron_service:
            self.tools.register(CronTool(self.cron_service))
    
    async def _connect_mcp(self) -> None:
        """Connect to configured MCP servers (one-time, lazy)."""
        if self._mcp_connected or not self._mcp_servers:
            return
        self._mcp_connected = True
        from nanobot.agent.tools.mcp import connect_mcp_servers
        self._mcp_stack = AsyncExitStack()
        await self._mcp_stack.__aenter__()
        await connect_mcp_servers(self._mcp_servers, self.tools, self._mcp_stack)

    def _set_tool_context(self, channel: str, chat_id: str) -> None:
        """Update context for all tools that need routing info."""
        if message_tool := self.tools.get("message"):
            if isinstance(message_tool, MessageTool):
                message_tool.set_context(channel, chat_id)

        if spawn_tool := self.tools.get("spawn"):
            if isinstance(spawn_tool, SpawnTool):
                spawn_tool.set_context(channel, chat_id)

        if cron_tool := self.tools.get("cron"):
            if isinstance(cron_tool, CronTool):
                cron_tool.set_context(channel, chat_id)

    @staticmethod
    def _strip_think(text: str | None) -> str | None:
        """Remove <think>…</think> blocks that some models embed in content."""
        if not text:
            return None
        return re.sub(r"<think>[\s\S]*?</think>", "", text).strip() or None

    @staticmethod
    def _tool_hint(tool_calls: list) -> str:
        """Format tool calls as concise hint, e.g. 'web_search("query")'."""
        def _fmt(tc):
            val = next(iter(tc.arguments.values()), None) if tc.arguments else None
            if not isinstance(val, str):
                return tc.name
            return f'{tc.name}("{val[:40]}…")' if len(val) > 40 else f'{tc.name}("{val}")'
        return ", ".join(_fmt(tc) for tc in tool_calls)

    @staticmethod
    def _provider_failed(response_content: str | None, finish_reason: str) -> bool:
        """Detect provider/API failures that should trigger local fallback."""
        if finish_reason == "error":
            return True
        text = (response_content or "").strip().lower()
        if text.startswith("error calling llm"):
            return True
        if "no endpoints found matching your data policy" in text:
            return True
        if "api key" in text and "invalid" in text:
            return True
        return False

    @staticmethod
    def _looks_like_literal_tool_call(text: str | None) -> bool:
        """Detect accidental raw tool-call strings like read_file("...") from weaker models."""
        if not text:
            return False
        s = text.strip()
        if not s:
            return False
        return bool(re.match(r"^[a-zA-Z_][a-zA-Z0-9_]*\s*\([\s\S]*\)\s*$", s))

    @staticmethod
    def _looks_like_tool_schema_dump(text: str | None) -> bool:
        """Detect leaked tool/schema payloads rendered as plain text to users."""
        if not text:
            return False
        s = text.strip()
        low = s.lower()
        if low.startswith("{function <nil>"):
            return True
        if low.startswith("{function "):
            return True
        if '"name"' in low and '"parameters"' in low and ('read_file' in low or 'web_search' in low or 'write_file' in low):
            return True
        if '"name"' in low and '"parameters"' in low and 'translate_text' in low:
            return True
        if "tool call" in low and ("web_search" in low or "read_file" in low):
            return True
        if "{\"name\":" in low and "\"parameters\":" in low:
            return True
        if re.search(r'\{\s*"name"\s*:\s*"[a-zA-Z0-9_:-]+"\s*,\s*"parameters"\s*:', s, re.DOTALL):
            return True
        return False

    @staticmethod
    def _looks_like_execution_snippet_dump(text: str | None) -> bool:
        """Detect leaked python/action snippets that should never be a chat reply."""
        if not text:
            return False
        low = text.strip().lower()
        if "<|python_tag|>" in low:
            return True
        if "webbrowser.open(" in low:
            return True
        if low.startswith("import ") and "\n" in low:
            return True
        return False

    @staticmethod
    def _extract_last_user_prompt(messages: list[dict]) -> str:
        for item in reversed(messages):
            if item.get("role") == "user":
                return item.get("content", "")
        return ""

    @staticmethod
    def _has_placeholder_tool_args(args: Any) -> bool:
        """Detect placeholder argument values like 'path'/'object' from weak tool-calling outputs."""
        placeholders = {
            "path", "object", "string", "number", "boolean", "null",
            "file", "file_path", "filepath", "<path>", "<file>", "value",
        }

        def _walk(v: Any) -> bool:
            if isinstance(v, str):
                t = v.strip().lower()
                return t in placeholders
            if isinstance(v, dict):
                return any(_walk(x) for x in v.values())
            if isinstance(v, list):
                return any(_walk(x) for x in v)
            return False

        return _walk(args)

    @staticmethod
    def _quick_direct_response(user_text: str) -> str | None:
        """Return deterministic responses for common chat intents to avoid unnecessary tool churn."""
        low = user_text.strip().lower()
        if low in {"hi", "hello", "hey", "/start", "start"}:
            return "Hello! I am online and ready. Ask me anything or give me a task."
        if any(phrase in low for phrase in ("what can you do", "your capabilities", "tell ur capabilities", "tell your capabilities", "what are your capabilities")):
            return (
                "I can help with local tasks and coding assistance. Current reliable capabilities are: "
                "answering questions, summarizing text, basic code generation, file reading and writing, showing exact file paths, opening file contents in chat, simple status/time responses, and limited short translation help for common words or phrases. "
                "I should not claim broad translation or external-web capabilities unless those tools are actually configured."
            )
        if any(phrase in low for phrase in (
            "how u can claim", "how can you claim", "so how can you claim", "why do you claim", "how can u say that",
        )) and "translate" in low:
            return (
                "That claim was too broad. The correct behavior is: I can only offer limited built-in translation help for some short words or phrases unless a proper translation tool or model is configured. "
                "I should not advertise full translation capability when it is not reliably available."
            )
        if "news" in low:
            return (
                "I can help with news, but web search is not configured right now. "
                "Share a topic and I will provide a concise background summary from built-in knowledge."
            )
        if ("today" in low or "todays" in low) and ("news" in low or "highlight" in low or "headline" in low):
            return (
                "I can fetch today's highlights. Please specify scope, for example: "
                "'today highlights in india tech' or 'today world headlines'."
            )
        return None

    @staticmethod
    def _quick_translation_response(user_text: str) -> str | None:
        text = user_text.strip()
        low = text.lower()
        match = re.match(r"translate\s+(.+?)\s+to\s+([a-zA-Z]+)\s*$", low)
        if not match:
            return None

        phrase = match.group(1).strip(" \t\n\r\"'")
        target = match.group(2).strip().lower()

        direct = AgentLoop._known_translation_lookup(phrase, target)
        if direct:
            return direct

        if target in {"spanish", "english", "hindi", "french", "german"}:
            return (
                f"I can only give limited built-in translation help right now, and I do not have a reliable offline translation result for '{phrase}' to {target}. "
                "If you want, I can still try a best-effort explanation, but I should not pretend it is exact."
            )

        return "Translation is not configured for that language pair right now."

    @staticmethod
    def _known_translation_lookup(phrase: str, target: str) -> str | None:
        translations: dict[tuple[str, str], str] = {
            ("harsh", "spanish"): "'harsh' in Spanish depends on context: 'duro', 'severo', or 'áspero'. If 'Harsh' is a person's name, it usually stays 'Harsh'.",
            ("hello", "spanish"): "'hello' in Spanish is 'hola'.",
            ("thanks", "spanish"): "'thanks' in Spanish is 'gracias'.",
            ("thank you", "spanish"): "'thank you' in Spanish is 'gracias'.",
            ("good morning", "spanish"): "'good morning' in Spanish is 'buenos días'.",
        }
        return translations.get((phrase.strip().lower(), target.strip().lower()))

    @staticmethod
    def _parse_translation_request(user_text: str) -> tuple[str, str | None, str] | None:
        text = user_text.strip()
        if not text:
            return None

        m = re.match(r"translate\s+(.+?)\s+from\s+([a-zA-Z]+)\s+to\s+([a-zA-Z]+)\s*$", text, flags=re.IGNORECASE)
        if m:
            phrase = m.group(1).strip(" \t\n\r\"'")
            source = m.group(2).strip().lower()
            target = m.group(3).strip().lower()
            if phrase and target:
                return phrase, source, target

        m = re.match(r"translate\s+(.+?)\s+to\s+([a-zA-Z]+)\s*$", text, flags=re.IGNORECASE)
        if m:
            phrase = m.group(1).strip(" \t\n\r\"'")
            target = m.group(2).strip().lower()
            if phrase and target:
                return phrase, None, target
        return None

    async def _handle_translation_request(self, user_text: str) -> str | None:
        req = self._parse_translation_request(user_text)
        if not req:
            return None

        phrase, source, target = req

        # Keep short/common cases deterministic and fast.
        known = self._known_translation_lookup(phrase, target)
        if known is not None:
            return known

        source_label = source or "auto-detect"
        prompt = (
            f"Translate from {source_label} to {target}. Return only the translated text, no explanation.\n"
            f"Text: {phrase}"
        )

        try:
            response = await self.provider.chat(
                messages=[
                    {
                        "role": "system",
                        "content": "You are a translation engine. Output only translated text.",
                    },
                    {"role": "user", "content": prompt},
                ],
                tools=[],
                model=self.model,
                temperature=0.0,
                max_tokens=min(self.max_tokens, 200),
            )
            content = self._strip_think(response.content)
        except Exception:
            content = None

        if (
            not content
            or self._looks_like_literal_tool_call(content)
            or self._looks_like_tool_schema_dump(content)
            or self._looks_like_execution_snippet_dump(content)
        ):
            return (
                f"I can only give limited built-in translation help right now, and I do not have a reliable translation result for '{phrase}' to {target}. "
                "If you want, I can still provide a best-effort explanation."
            )

        return content.strip()

    @staticmethod
    def _looks_like_internal_context_dump(text: str | None) -> bool:
        """Detect leaked internal prompt/runtime context text that should never be user-facing."""
        if not text:
            return False
        low = text.lower()
        leak_markers = [
            "[runtime context",
            "your long-term memory is:",
            "your history log is:",
            "do not assume gnu tools",
            "you have a powerful offline local brain",
        ]
        return any(marker in low for marker in leak_markers)

    def _resolve_workspace_path(self, path: str | None) -> Path | None:
        if not path:
            return None
        candidate = Path(path).expanduser()
        if not candidate.is_absolute():
            candidate = self.workspace / candidate
        try:
            return candidate.resolve()
        except Exception:
            return candidate

    @staticmethod
    def _extract_file_name_hint(text: str) -> str | None:
        match = re.search(r"([A-Za-z0-9_.-]+\.[A-Za-z0-9]+)", text)
        return match.group(1).lower() if match else None

    @staticmethod
    def _extract_path_from_tool_result(result: str) -> str | None:
        match = re.search(r"\bto\s+([A-Za-z]:\\[^\r\n]+)$", result.strip())
        if match:
            return match.group(1).strip()
        match = re.search(r"\bedited\s+([A-Za-z]:\\[^\r\n]+)$", result.strip())
        if match:
            return match.group(1).strip()
        return None

    def _remember_file_from_tool(
        self,
        turn_state: dict[str, str],
        tool_name: str,
        tool_args: dict[str, Any],
        tool_result: str,
    ) -> None:
        if tool_name not in {"write_file", "edit_file", "read_file"}:
            return
        if isinstance(tool_result, str) and tool_result.startswith("Error"):
            return

        resolved = self._resolve_workspace_path(tool_args.get("path"))
        result_path = self._extract_path_from_tool_result(tool_result) if isinstance(tool_result, str) else None
        remembered = self._resolve_workspace_path(result_path) or resolved
        if remembered is None:
            return

        turn_state["last_file_path"] = str(remembered)
        turn_state["last_file_name"] = remembered.name.lower()

    def _resolve_followup_file_target(
        self,
        remembered_path: Path,
        hinted_name: str | None,
    ) -> tuple[Path | None, str | None]:
        if not hinted_name:
            return remembered_path, None
        if remembered_path.name.lower() == hinted_name:
            return remembered_path, None

        sibling = remembered_path.parent / hinted_name
        if sibling.exists() and sibling.is_file():
            return sibling.resolve(), None

        matches = list(self.workspace.rglob(hinted_name))[:2]
        file_matches = [match.resolve() for match in matches if match.is_file()]
        if len(file_matches) == 1:
            return file_matches[0], None
        if len(file_matches) > 1:
            return None, f"I found multiple files named {hinted_name}. Please specify the path."

        return None, f"I do not have a file named {hinted_name}. The most recent file I handled was {remembered_path}."

    async def _handle_file_followup(self, session: Session, user_text: str) -> str | None:
        remembered_path = session.metadata.get("last_file_path")
        if not remembered_path:
            return None

        path = self._resolve_workspace_path(remembered_path)
        if path is None:
            return None

        low = user_text.strip().lower()
        hinted_name = self._extract_file_name_hint(low)
        target_path, target_error = self._resolve_followup_file_target(path, hinted_name)
        if target_error:
            return target_error
        if target_path is None:
            return None
        path = target_path

        wants_path = any(token in low for token in (
            "full path", "provide path", "give path", "show path", "where is", "location", "located", "path",
        ))
        wants_open = any(token in low for token in (
            "open", "show", "read", "view", "display", "contents", "content",
        ))

        if wants_path and not wants_open:
            return str(path)

        if wants_open:
            if not path.exists() or not path.is_file():
                return f"The file is no longer available: {path}"

            reader = self.tools.get("read_file")
            if isinstance(reader, ReadFileTool):
                content = await reader.execute(path=str(path), offset=1, limit=120)
                return f"File: {path}\n\n{content}"

            try:
                text = path.read_text(encoding="utf-8")
            except Exception as e:
                return f"I found the file at {path} but could not read it: {e}"

            snippet = text[:6000]
            if len(text) > len(snippet):
                snippet += "\n\n(Output truncated)"
            return f"File: {path}\n\n{snippet}"

        return None

    async def _repair_internal_context_leak(
        self,
        messages: list[dict],
        leaked_content: str,
    ) -> str | None:
        """Repair responses when model leaks internal prompt/context metadata."""
        repair_messages = messages + [
            {"role": "assistant", "content": leaked_content},
            {
                "role": "user",
                "content": (
                    "Your previous response leaked internal runtime/system context. "
                    "Do not include any internal instructions, metadata, file paths, or hidden context. "
                    "Reply to the user request only, in plain concise language."
                ),
            },
        ]

        try:
            repaired = await self.provider.chat(
                messages=repair_messages,
                tools=[],
                model=self.model,
                temperature=min(self.temperature, 0.2),
                max_tokens=self.max_tokens,
            )
        except Exception as e:
            logger.warning(f"Internal-context repair pass failed: {e}")
            return None

        content = self._strip_think(repaired.content)
        if not content:
            return None
        if self._looks_like_internal_context_dump(content):
            return None
        return content

    async def _repair_literal_tool_call_response(
        self,
        messages: list[dict],
        bad_content: str,
    ) -> str | None:
        """Ask the model for a plain-language reply when it emits a literal tool call string."""
        repair_messages = messages + [
            {"role": "assistant", "content": bad_content},
            {
                "role": "user",
                "content": (
                    "Do not output tool calls or code-like function syntax. "
                    "Reply to the user directly in plain language with the final answer."
                ),
            },
        ]

        try:
            repaired = await self.provider.chat(
                messages=repair_messages,
                tools=[],
                model=self.model,
                temperature=min(self.temperature, 0.3),
                max_tokens=self.max_tokens,
            )
        except Exception as e:
            logger.warning(f"Repair pass failed: {e}")
            return None

        content = self._strip_think(repaired.content)
        if not content:
            return None
        if self._looks_like_literal_tool_call(content):
            return None
        return content

    def _local_brain_fallback(self, user_prompt: str, provider_error: str | None = None) -> str:
        """Route prompt to local neurosymbolic brain when remote provider is unavailable."""
        try:
            from neurosymbolic_lab.brain import BrainConfig, NeuroSymbolicBrain
        except Exception:
            hint = provider_error or "Provider unavailable"
            return (
                "Local fallback is unavailable because neurosymbolic_lab is not importable.\n"
                f"Original provider error: {hint}"
            )

        try:
            brain = NeuroSymbolicBrain(
                BrainConfig(workspace=self.workspace, allow_write=False)
            )
            local = brain.handle(user_prompt)
            prefix = "[Local Fallback Mode]\n"
            if provider_error:
                prefix += f"Provider error: {provider_error}\n\n"
            return prefix + (local.output or "Local fallback completed with no output.")
        except Exception as e:
            hint = provider_error or "Provider unavailable"
            return (
                "Provider failed and local fallback also failed.\n"
                f"Provider error: {hint}\n"
                f"Fallback error: {e}"
            )

    async def _run_agent_loop(
        self,
        initial_messages: list[dict],
        on_progress: Callable[[str], Awaitable[None]] | None = None,
    ) -> tuple[str | None, list[str], dict[str, str]]:
        """
        Run the agent iteration loop.

        Args:
            initial_messages: Starting messages for the LLM conversation.
            on_progress: Optional callback to push intermediate content to the user.

        Returns:
            Tuple of (final_content, list_of_tools_used).
        """
        messages = initial_messages
        iteration = 0
        final_content = None
        tools_used: list[str] = []
        turn_state: dict[str, str] = {}

        while iteration < self.max_iterations:
            iteration += 1

            response = await self.provider.chat(
                messages=messages,
                tools=self.tools.get_definitions(),
                model=self.model,
                temperature=self.temperature,
                max_tokens=self.max_tokens,
            )

            if self._provider_failed(response.content, response.finish_reason):
                logger.warning("Provider failure detected; switching to local neurosymbolic fallback")
                last_user_prompt = ""
                for item in reversed(messages):
                    if item.get("role") == "user":
                        last_user_prompt = item.get("content", "")
                        break
                final_content = self._local_brain_fallback(last_user_prompt, response.content)
                break

            if response.has_tool_calls:
                if on_progress:
                    await on_progress(self._tool_hint(response.tool_calls))

                tool_call_dicts = [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.name,
                            "arguments": json.dumps(tc.arguments)
                        }
                    }
                    for tc in response.tool_calls
                ]
                messages = self.context.add_assistant_message(
                    messages, response.content, tool_call_dicts,
                    reasoning_content=response.reasoning_content,
                )

                for tool_call in response.tool_calls:
                    tools_used.append(tool_call.name)
                    args_str = json.dumps(tool_call.arguments, ensure_ascii=False)
                    logger.info(f"Tool call: {tool_call.name}({args_str[:200]})")
                    if self._has_placeholder_tool_args(tool_call.arguments):
                        result = (
                            "Error: Invalid tool arguments (placeholder values). "
                            "Use concrete values or answer directly without tool call."
                        )
                    else:
                        result = await self.tools.execute(tool_call.name, tool_call.arguments)
                        self._remember_file_from_tool(turn_state, tool_call.name, tool_call.arguments, result)
                    messages = self.context.add_tool_result(
                        messages, tool_call.id, tool_call.name, result
                    )
            else:
                final_content = self._strip_think(response.content)
                if (
                    self._looks_like_literal_tool_call(final_content)
                    or self._looks_like_tool_schema_dump(final_content)
                    or self._looks_like_execution_snippet_dump(final_content)
                ):
                    logger.warning("Model returned literal tool-call text; running plain-language repair pass")
                    repaired = await self._repair_literal_tool_call_response(messages, final_content)
                    if repaired:
                        final_content = repaired
                    else:
                        quick = self._quick_direct_response(self._extract_last_user_prompt(messages))
                        final_content = quick or "I am ready to help. Please tell me the exact result you want."
                if self._looks_like_internal_context_dump(final_content):
                    logger.warning("Model leaked internal runtime context; running repair pass")
                    repaired = await self._repair_internal_context_leak(messages, final_content)
                    if repaired:
                        final_content = repaired
                    else:
                        final_content = "I am ready to help. Please tell me the specific task you want me to do."
                if final_content and "Error: File not found: memory/" in final_content:
                    quick = self._quick_direct_response(self._extract_last_user_prompt(messages))
                    final_content = quick or "I hit an internal file-state issue. Please retry your request once."
                break

        return final_content, tools_used, turn_state

    async def run(self) -> None:
        """Run the agent loop, processing messages from the bus."""
        self._running = True
        await self._connect_mcp()
        logger.info("Agent loop started")

        while self._running:
            try:
                msg = await asyncio.wait_for(
                    self.bus.consume_inbound(),
                    timeout=1.0
                )
                try:
                    response = await self._process_message(msg)
                    if response:
                        await self.bus.publish_outbound(response)
                except Exception as e:
                    logger.error(f"Error processing message: {e}")
                    await self.bus.publish_outbound(OutboundMessage(
                        channel=msg.channel,
                        chat_id=msg.chat_id,
                        content=f"Sorry, I encountered an error: {str(e)}"
                    ))
            except asyncio.TimeoutError:
                continue
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Agent loop error: {e}")
                await asyncio.sleep(1)
                continue
    
    async def close_mcp(self) -> None:
        """Close MCP connections."""
        if self._mcp_stack:
            try:
                await self._mcp_stack.aclose()
            except (RuntimeError, BaseExceptionGroup):
                pass  # MCP SDK cancel scope cleanup is noisy but harmless
            self._mcp_stack = None

    def stop(self) -> None:
        """Stop the agent loop."""
        self._running = False
        logger.info("Agent loop stopping")
    
    async def _process_message(
        self,
        msg: InboundMessage,
        session_key: str | None = None,
        on_progress: Callable[[str], Awaitable[None]] | None = None,
    ) -> OutboundMessage | None:
        """
        Process a single inbound message.
        
        Args:
            msg: The inbound message to process.
            session_key: Override session key (used by process_direct).
            on_progress: Optional callback for intermediate output (defaults to bus publish).
        
        Returns:
            The response message, or None if no response needed.
        """
        # System messages route back via chat_id ("channel:chat_id")
        if msg.channel == "system":
            return await self._process_system_message(msg)
        
        preview = msg.content[:80] + "..." if len(msg.content) > 80 else msg.content
        logger.info(f"Processing message from {msg.channel}:{msg.sender_id}: {preview}")
        
        key = session_key or msg.session_key
        session = self.sessions.get_or_create(key)

        file_followup = await self._handle_file_followup(session, msg.content)
        if file_followup is not None:
            session.add_message("user", msg.content)
            session.add_message("assistant", file_followup)
            self.sessions.save(session)
            return OutboundMessage(channel=msg.channel, chat_id=msg.chat_id, content=file_followup)

        translated = await self._handle_translation_request(msg.content)
        if translated is not None:
            session.add_message("user", msg.content)
            session.add_message("assistant", translated)
            self.sessions.save(session)
            return OutboundMessage(channel=msg.channel, chat_id=msg.chat_id, content=translated)
        
        # Handle slash commands
        cmd = msg.content.strip().lower()
        quick = self._quick_direct_response(msg.content)
        if quick is not None:
            return OutboundMessage(channel=msg.channel, chat_id=msg.chat_id, content=quick)

        if cmd == "/new":
            # Capture messages before clearing (avoid race condition with background task)
            messages_to_archive = session.messages.copy()
            session.clear()
            self.sessions.save(session)
            self.sessions.invalidate(session.key)

            async def _consolidate_and_cleanup():
                temp_session = Session(key=session.key)
                temp_session.messages = messages_to_archive
                await self._consolidate_memory(temp_session, archive_all=True)

            asyncio.create_task(_consolidate_and_cleanup())
            return OutboundMessage(channel=msg.channel, chat_id=msg.chat_id,
                                  content="New session started. Memory consolidation in progress.")
        if cmd == "/help":
            return OutboundMessage(channel=msg.channel, chat_id=msg.chat_id,
                                  content="🐈 nanobot commands:\n/new — Start a new conversation\n/help — Show available commands")
        
        if len(session.messages) > self.memory_window:
            asyncio.create_task(self._consolidate_memory(session))

        self._set_tool_context(msg.channel, msg.chat_id)
        initial_messages = self.context.build_messages(
            history=session.get_history(max_messages=self.memory_window),
            current_message=msg.content,
            media=msg.media if msg.media else None,
            channel=msg.channel,
            chat_id=msg.chat_id,
        )

        async def _bus_progress(content: str) -> None:
            # Keep progress/tool-hint chatter out of chat channels like Telegram/Web UI.
            if msg.channel != "cli":
                return
            await self.bus.publish_outbound(OutboundMessage(
                channel=msg.channel, chat_id=msg.chat_id, content=content,
                metadata=msg.metadata or {},
            ))

        progress_cb = on_progress
        if progress_cb is None and msg.channel == "cli":
            progress_cb = _bus_progress

        final_content, tools_used, turn_state = await self._run_agent_loop(
            initial_messages, on_progress=progress_cb,
        )

        if final_content is None:
            final_content = "I've completed processing but have no response to give."
        
        preview = final_content[:120] + "..." if len(final_content) > 120 else final_content
        logger.info(f"Response to {msg.channel}:{msg.sender_id}: {preview}")
        
        session.add_message("user", msg.content)
        if turn_state:
            session.metadata.update(turn_state)
        session.add_message("assistant", final_content,
                            tools_used=tools_used if tools_used else None)
        self.sessions.save(session)
        
        return OutboundMessage(
            channel=msg.channel,
            chat_id=msg.chat_id,
            content=final_content,
            metadata=msg.metadata or {},  # Pass through for channel-specific needs (e.g. Slack thread_ts)
        )
    
    async def _process_system_message(self, msg: InboundMessage) -> OutboundMessage | None:
        """
        Process a system message (e.g., subagent announce).
        
        The chat_id field contains "original_channel:original_chat_id" to route
        the response back to the correct destination.
        """
        logger.info(f"Processing system message from {msg.sender_id}")
        
        # Parse origin from chat_id (format: "channel:chat_id")
        if ":" in msg.chat_id:
            parts = msg.chat_id.split(":", 1)
            origin_channel = parts[0]
            origin_chat_id = parts[1]
        else:
            # Fallback
            origin_channel = "cli"
            origin_chat_id = msg.chat_id
        
        session_key = f"{origin_channel}:{origin_chat_id}"
        session = self.sessions.get_or_create(session_key)
        self._set_tool_context(origin_channel, origin_chat_id)
        initial_messages = self.context.build_messages(
            history=session.get_history(max_messages=self.memory_window),
            current_message=msg.content,
            channel=origin_channel,
            chat_id=origin_chat_id,
        )
        final_content, _, turn_state = await self._run_agent_loop(initial_messages)

        if final_content is None:
            final_content = "Background task completed."
        
        session.add_message("user", f"[System: {msg.sender_id}] {msg.content}")
        if turn_state:
            session.metadata.update(turn_state)
        session.add_message("assistant", final_content)
        self.sessions.save(session)
        
        return OutboundMessage(
            channel=origin_channel,
            chat_id=origin_chat_id,
            content=final_content
        )
    
    async def _consolidate_memory(self, session, archive_all: bool = False) -> None:
        """Consolidate old messages into MEMORY.md + HISTORY.md.

        Args:
            archive_all: If True, clear all messages and reset session (for /new command).
                       If False, only write to files without modifying session.
        """
        memory = MemoryStore(self.workspace)

        if archive_all:
            old_messages = session.messages
            keep_count = 0
            logger.info(f"Memory consolidation (archive_all): {len(session.messages)} total messages archived")
        else:
            keep_count = self.memory_window // 2
            if len(session.messages) <= keep_count:
                logger.debug(f"Session {session.key}: No consolidation needed (messages={len(session.messages)}, keep={keep_count})")
                return

            messages_to_process = len(session.messages) - session.last_consolidated
            if messages_to_process <= 0:
                logger.debug(f"Session {session.key}: No new messages to consolidate (last_consolidated={session.last_consolidated}, total={len(session.messages)})")
                return

            old_messages = session.messages[session.last_consolidated:-keep_count]
            if not old_messages:
                return
            logger.info(f"Memory consolidation started: {len(session.messages)} total, {len(old_messages)} new to consolidate, {keep_count} keep")

        lines = []
        for m in old_messages:
            if not m.get("content"):
                continue
            tools = f" [tools: {', '.join(m['tools_used'])}]" if m.get("tools_used") else ""
            lines.append(f"[{m.get('timestamp', '?')[:16]}] {m['role'].upper()}{tools}: {m['content']}")
        conversation = "\n".join(lines)
        current_memory = memory.read_long_term()

        prompt = f"""You are a memory consolidation agent. Process this conversation and return a JSON object with exactly two keys:

1. "history_entry": A paragraph (2-5 sentences) summarizing the key events/decisions/topics. Start with a timestamp like [YYYY-MM-DD HH:MM]. Include enough detail to be useful when found by grep search later.

2. "memory_update": The updated long-term memory content. Add any new facts: user location, preferences, personal info, habits, project context, technical decisions, tools/services used. If nothing new, return the existing content unchanged.

## Current Long-term Memory
{current_memory or "(empty)"}

## Conversation to Process
{conversation}

Respond with ONLY valid JSON, no markdown fences."""

        try:
            response = await self.provider.chat(
                messages=[
                    {"role": "system", "content": "You are a memory consolidation agent. Respond only with valid JSON."},
                    {"role": "user", "content": prompt},
                ],
                model=self.model,
            )
            text = (response.content or "").strip()
            if not text:
                logger.warning("Memory consolidation: LLM returned empty response, skipping")
                return
            if text.startswith("```"):
                text = text.split("\n", 1)[-1].rsplit("```", 1)[0].strip()
            result = json_repair.loads(text)
            if not isinstance(result, dict):
                logger.warning(f"Memory consolidation: unexpected response type, skipping. Response: {text[:200]}")
                return

            if entry := result.get("history_entry"):
                memory.append_history(entry)
            if update := result.get("memory_update"):
                if update != current_memory:
                    memory.write_long_term(update)

            if archive_all:
                session.last_consolidated = 0
            else:
                session.last_consolidated = len(session.messages) - keep_count
            logger.info(f"Memory consolidation done: {len(session.messages)} messages, last_consolidated={session.last_consolidated}")
        except Exception as e:
            logger.error(f"Memory consolidation failed: {e}")

    async def process_direct(
        self,
        content: str,
        session_key: str = "cli:direct",
        channel: str = "cli",
        chat_id: str = "direct",
        on_progress: Callable[[str], Awaitable[None]] | None = None,
    ) -> str:
        """
        Process a message directly (for CLI or cron usage).
        
        Args:
            content: The message content.
            session_key: Session identifier (overrides channel:chat_id for session lookup).
            channel: Source channel (for tool context routing).
            chat_id: Source chat ID (for tool context routing).
            on_progress: Optional callback for intermediate output.
        
        Returns:
            The agent's response.
        """
        await self._connect_mcp()
        msg = InboundMessage(
            channel=channel,
            sender_id="user",
            chat_id=chat_id,
            content=content
        )
        
        response = await self._process_message(msg, session_key=session_key, on_progress=on_progress)
        return response.content if response else ""
