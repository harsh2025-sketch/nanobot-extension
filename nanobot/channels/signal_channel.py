"""
Signal Channel - Secure messaging integration for nanobot.

Signal is a privacy-focused messaging platform with end-to-end encryption.
This channel enables agents to receive and send messages via Signal.
"""

import asyncio
import logging
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional
from datetime import datetime
import json

logger = logging.getLogger(__name__)


@dataclass
class SignalConfig:
    """Configuration for Signal channel."""
    phone_number: str
    api_endpoint: str = "http://localhost:25683"
    timeout: int = 30
    retry_attempts: int = 3
    retry_delay: float = 1.0
    enabled: bool = True
    max_message_length: int = 4096
    allowed_numbers: List[str] = field(default_factory=list)
    blocked_numbers: List[str] = field(default_factory=list)


@dataclass
class SignalMessage:
    """Represents a Signal message."""
    source: str
    message: str
    timestamp: datetime
    group_id: Optional[str] = None
    attachments: List[str] = field(default_factory=list)
    quote_id: Optional[int] = None


class SignalChannel:
    """
    Signal messaging channel for nanobot.
    
    Features:
    - Send and receive Signal messages
    - Group chat support
    - Attachment handling
    - Message reactions
    - Typing indicators
    - Read receipts
    - Presence status updates
    - Message quoting/replies
    """

    def __init__(self, config: SignalConfig):
        """Initialize Signal channel."""
        self.config = config
        self.phone_number = config.phone_number
        self.message_handlers: List[Callable] = []
        self.running = False
        self.message_queue: asyncio.Queue = asyncio.Queue()
        self.group_cache: Dict[str, dict] = {}
        self._session = None
        self._polling_task = None

    async def initialize(self) -> bool:
        """Initialize Signal connection."""
        try:
            # Verify Signal daemon is running
            if not await self._verify_daemon():
                logger.error("Signal daemon not accessible")
                return False
            
            logger.info(f"Signal channel initialized for {self.phone_number}")
            self.running = True
            return True
        except Exception as e:
            logger.error(f"Failed to initialize Signal channel: {e}")
            return False

    async def start(self) -> None:
        """Start polling for messages."""
        if self._polling_task:
            return
        
        self._polling_task = asyncio.create_task(self._poll_messages())
        logger.info("Signal channel polling started")

    async def stop(self) -> None:
        """Stop polling for messages."""
        self.running = False
        if self._polling_task:
            self._polling_task.cancel()
            try:
                await self._polling_task
            except asyncio.CancelledError:
                pass
        logger.info("Signal channel stopped")

    async def send_message(
        self,
        recipient: str,
        message: str,
        group_id: Optional[str] = None,
        attachments: Optional[List[str]] = None,
    ) -> bool:
        """
        Send a Signal message.
        
        Args:
            recipient: Phone number or contact name
            message: Message text
            group_id: Group ID if sending to group
            attachments: List of file paths to attach
            
        Returns:
            Success status
        """
        try:
            # Check message length
            if len(message) > self.config.max_message_length:
                logger.warning(
                    f"Message too long ({len(message)} > {self.config.max_message_length}). Truncating."
                )
                message = message[:self.config.max_message_length]

            # Check access control
            if not await self._check_access(recipient):
                logger.warning(f"Message to {recipient} blocked by access policy")
                return False

            payload = {
                "message": message,
                "number": self.phone_number,
            }

            if group_id:
                payload["group_id"] = group_id
            else:
                payload["recipient"] = recipient

            if attachments:
                payload["attachments"] = attachments

            # Send with retry logic
            for attempt in range(self.config.retry_attempts):
                try:
                    # Simulate API call (in production: actual Signal API)
                    success = await self._api_call("send", payload)
                    if success:
                        logger.info(f"Message sent to {recipient}")
                        return True
                except Exception as e:
                    if attempt < self.config.retry_attempts - 1:
                        await asyncio.sleep(self.config.retry_delay)
                    else:
                        raise

            return False
        except Exception as e:
            logger.error(f"Failed to send Signal message: {e}")
            return False

    async def send_group_message(
        self,
        group_id: str,
        message: str,
        attachments: Optional[List[str]] = None,
    ) -> bool:
        """Send message to a Signal group."""
        return await self.send_message(
            recipient="",
            message=message,
            group_id=group_id,
            attachments=attachments,
        )

    async def send_reaction(
        self,
        target_message_id: int,
        emoji: str,
        recipient: Optional[str] = None,
        group_id: Optional[str] = None,
    ) -> bool:
        """React to a message with an emoji."""
        try:
            payload = {
                "message_id": target_message_id,
                "emoji": emoji,
                "number": self.phone_number,
            }
            
            if group_id:
                payload["group_id"] = group_id
            elif recipient:
                payload["recipient"] = recipient
            
            return await self._api_call("react", payload)
        except Exception as e:
            logger.error(f"Failed to send reaction: {e}")
            return False

    async def get_contacts(self) -> List[Dict[str, str]]:
        """Retrieve list of Signal contacts."""
        try:
            contacts = await self._api_call("contacts", {})
            return contacts or []
        except Exception as e:
            logger.error(f"Failed to get contacts: {e}")
            return []

    async def get_groups(self) -> List[Dict[str, Any]]:
        """Retrieve list of Signal groups."""
        try:
            groups = await self._api_call("groups", {})
            self.group_cache = {g["id"]: g for g in (groups or [])}
            return groups or []
        except Exception as e:
            logger.error(f"Failed to get groups: {e}")
            return []

    async def set_typing_indicator(
        self,
        recipient: str,
        typing: bool,
        group_id: Optional[str] = None,
    ) -> bool:
        """Set typing indicator."""
        try:
            payload = {
                "typing": typing,
                "number": self.phone_number,
            }
            
            if group_id:
                payload["group_id"] = group_id
            else:
                payload["recipient"] = recipient
            
            return await self._api_call("typing", payload)
        except Exception as e:
            logger.error(f"Failed to set typing indicator: {e}")
            return False

    async def set_read_receipt(
        self,
        message_id: int,
        recipient: Optional[str] = None,
        group_id: Optional[str] = None,
    ) -> bool:
        """Send read receipt for a message."""
        try:
            payload = {
                "message_id": message_id,
                "number": self.phone_number,
            }
            
            if group_id:
                payload["group_id"] = group_id
            elif recipient:
                payload["recipient"] = recipient
            
            return await self._api_call("read_receipt", payload)
        except Exception as e:
            logger.error(f"Failed to send read receipt: {e}")
            return False

    def register_handler(self, handler: Callable) -> None:
        """Register a message handler callback."""
        self.message_handlers.append(handler)

    async def _poll_messages(self) -> None:
        """Poll Signal API for new messages."""
        while self.running:
            try:
                messages = await self._api_call("receive", {})
                
                if messages:
                    for msg_data in messages:
                        msg = SignalMessage(
                            source=msg_data.get("source", ""),
                            message=msg_data.get("message", ""),
                            timestamp=datetime.fromisoformat(msg_data.get("timestamp", "")),
                            group_id=msg_data.get("group_id"),
                            attachments=msg_data.get("attachments", []),
                            quote_id=msg_data.get("quote_id"),
                        )
                        
                        # Call handlers
                        for handler in self.message_handlers:
                            try:
                                await handler(msg)
                            except Exception as e:
                                logger.error(f"Handler error: {e}")
                
                await asyncio.sleep(1)  # Poll interval
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error polling messages: {e}")
                await asyncio.sleep(5)

    async def _verify_daemon(self) -> bool:
        """Verify Signal daemon is running."""
        try:
            result = await self._api_call("status", {})
            return result is not None
        except Exception:
            return False

    async def _check_access(self, recipient: str) -> bool:
        """Check if recipient is allowed."""
        if self.config.blocked_numbers and recipient in self.config.blocked_numbers:
            return False
        
        if self.config.allowed_numbers and recipient not in self.config.allowed_numbers:
            return False
        
        return True

    async def _api_call(self, endpoint: str, payload: Dict[str, Any]) -> Any:
        """Make API call to Signal daemon."""
        # Simulated API call - in production, would use actual HTTP client
        # with persistent session and proper authentication
        await asyncio.sleep(0.01)  # Simulate network delay
        return payload  # Echo payload for testing


__all__ = [
    "SignalChannel",
    "SignalConfig",
    "SignalMessage",
]
