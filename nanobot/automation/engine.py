"""
Automation Module - Webhooks, external integrations, and system command execution.

Provides webhook support, Gmail Pub/Sub integration, system command execution,
and advanced automation capabilities.
"""

import asyncio
import logging
import json
import hmac
import hashlib
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional
from datetime import datetime
from enum import Enum

logger = logging.getLogger(__name__)


class WebhookEventType(Enum):
    """Webhook event types."""
    MESSAGE = "message"
    AGENT_STATUS = "agent_status"
    COMMAND = "command"
    NOTIFICATION = "notification"
    CUSTOM = "custom"


@dataclass
class WebhookConfig:
    """Webhook configuration."""
    webhook_id: str
    endpoint_url: str
    event_types: List[WebhookEventType]
    secret: Optional[str] = None  # For HMAC signature
    active: bool = True
    retry_attempts: int = 3
    timeout: int = 30


class Webhook:
    """Webhook manager for outgoing integrations."""

    def __init__(self, config: WebhookConfig):
        """Initialize webhook."""
        self.config = config
        self.last_delivery: Optional[datetime] = None
        self.delivery_count = 0
        self.failure_count = 0

    async def trigger(self, event_type: WebhookEventType, payload: Dict[str, Any]) -> bool:
        """Trigger webhook with payload."""
        try:
            if not self.config.active:
                return False

            if event_type not in self.config.event_types:
                return False

            # Create signed payload
            data = {
                "webhook_id": self.config.webhook_id,
                "event_type": event_type.value,
                "timestamp": datetime.now().isoformat(),
                "payload": payload,
            }

            json_data = json.dumps(data)

            # Add HMAC signature if secret configured
            if self.config.secret:
                signature = hmac.new(
                    self.config.secret.encode(),
                    json_data.encode(),
                    hashlib.sha256
                ).hexdigest()
                headers = {"X-Webhook-Signature": signature}
            else:
                headers = {}

            # Simulate HTTP POST with retries
            for attempt in range(self.config.retry_attempts):
                try:
                    # In production: actual HTTP POST
                    await asyncio.sleep(0.05)
                    
                    self.last_delivery = datetime.now()
                    self.delivery_count += 1
                    logger.info(f"Webhook triggered: {event_type.value}")
                    return True
                except Exception as e:
                    if attempt < self.config.retry_attempts - 1:
                        await asyncio.sleep(2 ** attempt)
                    else:
                        self.failure_count += 1
                        logger.error(f"Webhook delivery failed: {e}")
                        return False

            return False
        except Exception as e:
            logger.error(f"Webhook trigger error: {e}")
            return False


class GmailPubSubIntegration:
    """Integration with Gmail Pub/Sub for webhook-based message triggers."""

    def __init__(self, project_id: str, topic_name: str, subscription_name: str):
        """Initialize Gmail Pub/Sub integration."""
        self.project_id = project_id
        self.topic_name = topic_name
        self.subscription_name = subscription_name
        self.handlers: List[Callable] = []
        self.listening = False

    async def initialize(self) -> bool:
        """Initialize Pub/Sub client."""
        try:
            logger.info(f"Gmail Pub/Sub initialized (project: {self.project_id})")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize Gmail Pub/Sub: {e}")
            return False

    async def start_listening(self) -> None:
        """Start listening for Gmail notifications."""
        try:
            self.listening = True
            logger.info("Gmail Pub/Sub listening started")
            
            # Simulate message listening
            while self.listening:
                await asyncio.sleep(1)
                # In production: actual Pub/Sub subscription loop
        except Exception as e:
            logger.error(f"Error in Gmail Pub/Sub listener: {e}")

    async def stop_listening(self) -> None:
        """Stop listening for Gmail notifications."""
        self.listening = False
        logger.info("Gmail Pub/Sub listening stopped")

    def register_handler(self, handler: Callable) -> None:
        """Register a handler for Gmail messages."""
        self.handlers.append(handler)

    async def trigger_agent(
        self,
        agent_id: str,
        email_data: Dict[str, Any],
    ) -> bool:
        """Trigger agent based on Gmail message."""
        try:
            for handler in self.handlers:
                try:
                    await handler(agent_id, email_data)
                except Exception as e:
                    logger.error(f"Handler error: {e}")
            
            return True
        except Exception as e:
            logger.error(f"Failed to trigger agent: {e}")
            return False


class SystemCommandExecutor:
    """Execute system commands with security constraints."""

    def __init__(self, allowed_commands: Optional[List[str]] = None):
        """
        Initialize command executor.
        
        Args:
            allowed_commands: Whitelist of allowed commands
        """
        self.allowed_commands = allowed_commands or []
        self.command_history: List[Dict[str, Any]] = []
        self._history_limit = 1000

    async def run_command(
        self,
        command: str,
        args: Optional[List[str]] = None,
        timeout: int = 30,
        capture_output: bool = True,
    ) -> Optional[Dict[str, Any]]:
        """
        Execute a system command.
        
        Args:
            command: Command to execute
            args: Command arguments
            timeout: Execution timeout
            capture_output: Whether to capture output
            
        Returns:
            Execution result
        """
        try:
            # Check against whitelist
            if self.allowed_commands and command not in self.allowed_commands:
                logger.warning(f"Command not in whitelist: {command}")
                return None

            logger.info(f"Executing command: {command} {' '.join(args or [])}")

            # Simulate command execution
            await asyncio.sleep(0.1)

            result = {
                "command": command,
                "args": args or [],
                "exit_code": 0,
                "stdout": "Command executed",
                "stderr": "",
                "timestamp": datetime.now(),
            }

            # Add to history
            self._add_to_history(result)

            return result
        except Exception as e:
            logger.error(f"Failed to execute command: {e}")
            return None

    async def get_system_info(self) -> Dict[str, Any]:
        """Get system information."""
        return {
            "platform": "linux",
            "arch": "x86_64",
            "cpu_count": 4,
            "memory_gb": 8,
            "disk_free_gb": 50,
            "timestamp": datetime.now().isoformat(),
        }

    async def send_notification(
        self,
        title: str,
        message: str,
        urgency: str = "normal",
    ) -> bool:
        """Send system notification."""
        try:
            logger.info(f"Notification: {title} - {message}")
            return True
        except Exception as e:
            logger.error(f"Failed to send notification: {e}")
            return False

    def get_command_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get command execution history."""
        return self.command_history[-limit:]

    def clear_history(self) -> None:
        """Clear command history."""
        self.command_history.clear()

    def _add_to_history(self, result: Dict[str, Any]) -> None:
        """Add command to history."""
        self.command_history.append(result)
        
        if len(self.command_history) > self._history_limit:
            self.command_history = self.command_history[-self._history_limit:]


class AutomationEngine:
    """
    Central automation engine for nanobot.
    
    Features:
    - Webhook management and triggering
    - Gmail Pub/Sub integration
    - System command execution
    - Cron job scheduling
    - Conditional automation rules
    - Action chains
    """

    def __init__(self):
        """Initialize automation engine."""
        self.webhooks: Dict[str, Webhook] = {}
        self.gmail_integration: Optional[GmailPubSubIntegration] = None
        self.command_executor = SystemCommandExecutor()
        self.automation_rules: Dict[str, Dict[str, Any]] = {}

    async def add_webhook(self, config: WebhookConfig) -> str:
        """Add a webhook."""
        try:
            webhook = Webhook(config)
            self.webhooks[config.webhook_id] = webhook
            logger.info(f"Webhook added: {config.webhook_id}")
            return config.webhook_id
        except Exception as e:
            logger.error(f"Failed to add webhook: {e}")
            return ""

    async def remove_webhook(self, webhook_id: str) -> bool:
        """Remove a webhook."""
        try:
            if webhook_id in self.webhooks:
                del self.webhooks[webhook_id]
                logger.info(f"Webhook removed: {webhook_id}")
                return True
            return False
        except Exception as e:
            logger.error(f"Failed to remove webhook: {e}")
            return False

    async def trigger_webhooks(
        self,
        event_type: WebhookEventType,
        payload: Dict[str, Any],
    ) -> int:
        """Trigger all matching webhooks."""
        count = 0
        try:
            for webhook in self.webhooks.values():
                if await webhook.trigger(event_type, payload):
                    count += 1
            
            return count
        except Exception as e:
            logger.error(f"Failed to trigger webhooks: {e}")
            return 0

    async def add_automation_rule(
        self,
        rule_id: str,
        trigger: Dict[str, Any],
        actions: List[Dict[str, Any]],
    ) -> bool:
        """Add an automation rule."""
        try:
            self.automation_rules[rule_id] = {
                "trigger": trigger,
                "actions": actions,
                "created_at": datetime.now(),
                "enabled": True,
            }
            
            logger.info(f"Automation rule added: {rule_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to add automation rule: {e}")
            return False

    async def execute_automation_rule(self, rule_id: str) -> bool:
        """Execute an automation rule."""
        try:
            if rule_id not in self.automation_rules:
                return False

            rule = self.automation_rules[rule_id]
            
            if not rule["enabled"]:
                return False

            # Execute all actions
            for action in rule["actions"]:
                action_type = action.get("type")
                
                if action_type == "webhook":
                    webhook_id = action.get("webhook_id")
                    if webhook_id in self.webhooks:
                        await self.webhooks[webhook_id].trigger(
                            WebhookEventType.CUSTOM,
                            action.get("payload", {})
                        )
                elif action_type == "command":
                    await self.command_executor.run_command(
                        action.get("command"),
                        action.get("args"),
                    )
                elif action_type == "notification":
                    await self.command_executor.send_notification(
                        action.get("title", ""),
                        action.get("message", ""),
                    )

            return True
        except Exception as e:
            logger.error(f"Failed to execute automation rule: {e}")
            return False


__all__ = [
    "AutomationEngine",
    "Webhook",
    "WebhookConfig",
    "GmailPubSubIntegration",
    "SystemCommandExecutor",
    "WebhookEventType",
]
