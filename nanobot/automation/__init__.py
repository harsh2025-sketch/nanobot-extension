"""
Automation Module - Advanced automation for nanobot.

Provides webhooks, Gmail Pub/Sub integration, system command execution,
and automation rule engine.
"""

from .engine import (
    AutomationEngine,
    Webhook,
    WebhookConfig,
    GmailPubSubIntegration,
    SystemCommandExecutor,
    WebhookEventType,
)

__all__ = [
    "AutomationEngine",
    "Webhook",
    "WebhookConfig",
    "GmailPubSubIntegration",
    "SystemCommandExecutor",
    "WebhookEventType",
]
