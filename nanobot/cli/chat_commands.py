"""
Chat Commands - Built-in chat commands for session and agent control.

Supported commands:
- /status - Show session status
- /new or /reset - Reset session
- /think - Set thinking level
- /verbose - Toggle verbose mode
- /usage - Toggle usage display
- /restart - Restart gateway
- /activation - Toggle group activation mode
- /compact - Compact session context
"""

import asyncio
import logging
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional
from enum import Enum
import re

logger = logging.getLogger(__name__)


class ThinkingLevel(Enum):
    """Extended thinking levels."""
    OFF = "off"
    MINIMAL = "minimal"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    XHIGH = "xhigh"


class VerboseLevel(Enum):
    """Verbosity levels for responses."""
    OFF = "off"
    NORMAL = "normal"
    HIGH = "high"
    DEBUG = "debug"


class UsageDisplayMode(Enum):
    """Usage display modes."""
    OFF = "off"
    TOKENS = "tokens"
    FULL = "full"


@dataclass
class ChatCommand:
    """Represents a parsed chat command."""
    command: str
    args: List[str]
    raw: str


class ChatCommandProcessor:
    """Process and execute chat commands."""

    def __init__(self):
        """Initialize command processor."""
        self.commands: Dict[str, Callable] = {}
        self.session_configs: Dict[str, Dict[str, Any]] = {}
        self._register_default_commands()
        logger.info("ChatCommandProcessor initialized")

    def _register_default_commands(self) -> None:
        """Register default commands."""
        self.commands = {
            "status": self.cmd_status,
            "new": self.cmd_reset,
            "reset": self.cmd_reset,
            "think": self.cmd_think,
            "verbose": self.cmd_verbose,
            "usage": self.cmd_usage,
            "restart": self.cmd_restart,
            "activation": self.cmd_activation,
            "compact": self.cmd_compact,
        }

    async def parse_command(self, text: str) -> Optional[ChatCommand]:
        """Parse a potential command from text."""
        if not text.startswith("/"):
            return None
        
        # Extract command and args
        parts = text.split(maxsplit=1)
        command = parts[0][1:].lower()  # Remove /
        args = parts[1].split() if len(parts) > 1 else []
        
        return ChatCommand(command=command, args=args, raw=text)

    async def execute_command(
        self,
        command: ChatCommand,
        session_id: str,
        **kwargs
    ) -> Dict[str, Any]:
        """Execute a chat command."""
        if command.command not in self.commands:
            return {
                "success": False,
                "error": f"Unknown command: /{command.command}",
                "is_command": True
            }
        
        try:
            handler = self.commands[command.command]
            result = await handler(session_id, command.args, **kwargs)
            result["is_command"] = True
            return result
        except Exception as e:
            logger.error(f"Command execution failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "is_command": True
            }

    async def cmd_status(
        self,
        session_id: str,
        args: List[str],
        **kwargs
    ) -> Dict[str, Any]:
        """Handle /status command."""
        status = kwargs.get("session_manager", {}).sessions.get(session_id, {})
        config = self.session_configs.get(session_id, {})
        
        return {
            "success": True,
            "message": f"**Session Status**\n"
                      f"- Model: {config.get('model', 'unknown')}\n"
                      f"- Thinking: {config.get('thinking_level', 'medium')}\n"
                      f"- Verbose: {config.get('verbose', 'off')}\n"
                      f"- Messages: {status.get('message_count', 0)}",
        }

    async def cmd_reset(
        self,
        session_id: str,
        args: List[str],
        **kwargs
    ) -> Dict[str, Any]:
        """Handle /new and /reset commands."""
        session_manager = kwargs.get("session_manager")
        if session_manager:
            await session_manager.reset_session(session_id)
        
        return {
            "success": True,
            "message": "Session reset. Starting fresh conversation.",
        }

    async def cmd_think(
        self,
        session_id: str,
        args: List[str],
        **kwargs
    ) -> Dict[str, Any]:
        """Handle /think command."""
        if not args:
            return {
                "success": False,
                "error": "Usage: /think <level> (off|minimal|low|medium|high|xhigh)",
            }
        
        level = args[0].lower()
        valid_levels = [e.value for e in ThinkingLevel]
        
        if level not in valid_levels:
            return {
                "success": False,
                "error": f"Invalid level. Valid: {', '.join(valid_levels)}",
            }
        
        if session_id not in self.session_configs:
            self.session_configs[session_id] = {}
        
        self.session_configs[session_id]["thinking_level"] = level
        logger.info(f"Thinking level set to {level} for {session_id}")
        
        return {
            "success": True,
            "message": f"Thinking level set to **{level}**.",
        }

    async def cmd_verbose(
        self,
        session_id: str,
        args: List[str],
        **kwargs
    ) -> Dict[str, Any]:
        """Handle /verbose command."""
        if not args:
            return {
                "success": False,
                "error": "Usage: /verbose <on|off>",
            }
        
        mode = args[0].lower()
        if mode not in ["on", "off"]:
            return {
                "success": False,
                "error": "Valid modes: on, off",
            }
        
        if session_id not in self.session_configs:
            self.session_configs[session_id] = {}
        
        self.session_configs[session_id]["verbose"] = mode
        logger.info(f"Verbose mode set to {mode} for {session_id}")
        
        return {
            "success": True,
            "message": f"Verbose mode turned **{mode}**.",
        }

    async def cmd_usage(
        self,
        session_id: str,
        args: List[str],
        **kwargs
    ) -> Dict[str, Any]:
        """Handle /usage command."""
        if not args:
            return {
                "success": False,
                "error": "Usage: /usage <off|tokens|full>",
            }
        
        mode = args[0].lower()
        valid_modes = ["off", "tokens", "full"]
        
        if mode not in valid_modes:
            return {
                "success": False,
                "error": f"Valid modes: {', '.join(valid_modes)}",
            }
        
        if session_id not in self.session_configs:
            self.session_configs[session_id] = {}
        
        self.session_configs[session_id]["usage_mode"] = mode
        logger.info(f"Usage display set to {mode} for {session_id}")
        
        return {
            "success": True,
            "message": f"Usage display set to **{mode}**.",
        }

    async def cmd_activation(
        self,
        session_id: str,
        args: List[str],
        **kwargs
    ) -> Dict[str, Any]:
        """Handle /activation command (groups only)."""
        if not args:
            return {
                "success": False,
                "error": "Usage: /activation <mention|always>",
            }
        
        mode = args[0].lower()
        if mode not in ["mention", "always"]:
            return {
                "success": False,
                "error": "Valid modes: mention, always",
            }
        
        if session_id not in self.session_configs:
            self.session_configs[session_id] = {}
        
        self.session_configs[session_id]["activation_mode"] = mode
        logger.info(f"Activation mode set to {mode} for {session_id}")
        
        return {
            "success": True,
            "message": f"Group activation mode set to **{mode}**.",
        }

    async def cmd_restart(
        self,
        session_id: str,
        args: List[str],
        **kwargs
    ) -> Dict[str, Any]:
        """Handle /restart command (owner-only)."""
        is_owner = kwargs.get("is_owner", False)
        
        if not is_owner:
            return {
                "success": False,
                "error": "Only session owner can restart.",
            }
        
        logger.warning(f"Gateway restart initiated by {session_id}")
        
        return {
            "success": True,
            "message": "Gateway is restarting...",
        }

    async def cmd_compact(
        self,
        session_id: str,
        args: List[str],
        **kwargs
    ) -> Dict[str, Any]:
        """Handle /compact command."""
        session_manager = kwargs.get("session_manager")
        
        if not session_manager:
            return {
                "success": False,
                "error": "Session manager not available",
            }
        
        history = await session_manager.get_session_history(session_id)
        
        return {
            "success": True,
            "message": f"Session context compacted. Kept {len(history)} messages for context.",
            "action": "compact_context",
        }


class ChatCommandInterpreter:
    """Interpret and execute chat commands intelligently."""

    def __init__(self):
        """Initialize interpreter."""
        self.processor = ChatCommandProcessor()
        logger.info("ChatCommandInterpreter initialized")

    async def process_message(
        self,
        text: str,
        session_id: str,
        **context
    ) -> tuple[bool, Dict[str, Any]]:
        """
        Process a message, checking for commands.
        
        Returns:
            (is_command, result_dict)
        """
        command = await self.processor.parse_command(text)
        
        if not command:
            return False, {}
        
        result = await self.processor.execute_command(command, session_id, **context)
        return True, result

    async def get_available_commands(self) -> List[Dict[str, str]]:
        """Get list of available commands."""
        return [
            {"command": "/status", "description": "Show current session status"},
            {"command": "/new", "description": "Start a new session (reset)"},
            {"command": "/reset", "description": "Alias for /new"},
            {"command": "/think <level>", "description": "Set thinking level: off|minimal|low|medium|high|xhigh"},
            {"command": "/verbose <on|off>", "description": "Toggle verbose output"},
            {"command": "/usage <off|tokens|full>", "description": "Set usage display: off|tokens|full"},
            {"command": "/activation <mention|always>", "description": "Set group activation (groups only)"},
            {"command": "/compact", "description": "Compact session context"},
            {"command": "/restart", "description": "Restart gateway (owner only)"},
        ]
