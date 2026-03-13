"""
BlueBubbles Channel - iMessage integration for nanobot.

BlueBubbles provides a bridge to Apple's iMessage service, enabling
agents to send and receive iMessage conversations on any platform.
"""

import asyncio
import logging
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional
from datetime import datetime
from enum import Enum

logger = logging.getLogger(__name__)


class iMessageReactionType(Enum):
    """Reaction types for iMessage."""
    THUMBS_UP = "thumbsup"
    THUMBS_DOWN = "thumbsdown"
    LAUGH = "laugh"
    EXCLAMATION = "exclamation"
    QUESTION = "question"
    HEART = "heart"


@dataclass
class BlueBubblesConfig:
    """Configuration for BlueBubbles channel."""
    server_url: str  # e.g., "http://localhost:1234"
    api_key: str
    mac_id: str  # Unique identifier for the Mac running BlueBubbles
    timeout: int = 30
    retry_attempts: int = 3
    enabled: bool = True
    allow_reactions: bool = True
    allow_typing: bool = True
    allow_read_receipts: bool = True
    handle_attachments: bool = True


@dataclass
class iMessage:
    """Represents an iMessage conversation message."""
    guid: str
    chat_guid: str
    handle_id: str
    text: str
    timestamp: datetime
    is_from_me: bool
    associated_message_type: Optional[int] = None
    associated_message_guid: Optional[str] = None
    attachments: List[str] = field(default_factory=list)
    message_summary: Optional[str] = None


class BlueBubblesChannel:
    """
    BlueBubbles iMessage channel for nanobot.
    
    Features:
    - Send and receive iMessages
    - Group chat support
    - Message reactions (emoji)
    - Typing indicators
    - Read receipts
    - Attachment handling
    - Chat list management
    - Contact information
    - Message reactions to existing messages
    """

    def __init__(self, config: BlueBubblesConfig):
        """Initialize BlueBubbles channel."""
        self.config = config
        self.message_handlers: List[Callable] = []
        self.running = False
        self.chats_cache: Dict[str, dict] = {}
        self.handles_cache: Dict[str, str] = {}
        self._polling_task = None
        self._session = None

    async def initialize(self) -> bool:
        """Initialize BlueBubbles connection."""
        try:
            # Test connection to BlueBubbles server
            if not await self._verify_connection():
                logger.error("BlueBubbles server not accessible")
                return False
            
            # Load chats and handles
            await self._load_chats()
            await self._load_handles()
            
            logger.info(f"BlueBubbles channel initialized (Mac: {self.config.mac_id})")
            self.running = True
            return True
        except Exception as e:
            logger.error(f"Failed to initialize BlueBubbles: {e}")
            return False

    async def start(self) -> None:
        """Start polling for messages."""
        if self._polling_task:
            return
        
        self._polling_task = asyncio.create_task(self._poll_messages())
        logger.info("BlueBubbles polling started")

    async def stop(self) -> None:
        """Stop polling for messages."""
        self.running = False
        if self._polling_task:
            self._polling_task.cancel()
            try:
                await self._polling_task
            except asyncio.CancelledError:
                pass
        logger.info("BlueBubbles stopped")

    async def send_message(
        self,
        chat_guid: str,
        text: str,
        attachments: Optional[List[str]] = None,
    ) -> Optional[str]:
        """
        Send an iMessage.
        
        Args:
            chat_guid: GUID of the chat/conversation
            text: Message text
            attachments: List of file paths to attach
            
        Returns:
            Message GUID if successful, None otherwise
        """
        try:
            payload = {
                "text": text,
                "chat_guid": chat_guid,
                "method": "send",
            }
            
            if attachments and self.config.handle_attachments:
                payload["attachments"] = attachments

            result = await self._api_call("messages", payload)
            
            if result and "guid" in result:
                logger.info(f"iMessage sent to {chat_guid}")
                return result["guid"]
            
            return None
        except Exception as e:
            logger.error(f"Failed to send iMessage: {e}")
            return None

    async def react_to_message(
        self,
        message_guid: str,
        chat_guid: str,
        reaction: iMessageReactionType,
    ) -> bool:
        """React to a message with an emoji."""
        if not self.config.allow_reactions:
            return False
        
        try:
            payload = {
                "message_guid": message_guid,
                "chat_guid": chat_guid,
                "reaction": reaction.value,
                "method": "react",
            }
            
            result = await self._api_call("reactions", payload)
            return result is not None
        except Exception as e:
            logger.error(f"Failed to send reaction: {e}")
            return False

    async def remove_reaction(
        self,
        message_guid: str,
        chat_guid: str,
    ) -> bool:
        """Remove a reaction from a message."""
        if not self.config.allow_reactions:
            return False
        
        try:
            payload = {
                "message_guid": message_guid,
                "chat_guid": chat_guid,
                "method": "remove_reaction",
            }
            
            result = await self._api_call("reactions", payload)
            return result is not None
        except Exception as e:
            logger.error(f"Failed to remove reaction: {e}")
            return False

    async def set_typing_indicator(
        self,
        chat_guid: str,
        typing: bool,
    ) -> bool:
        """Set typing indicator for a chat."""
        if not self.config.allow_typing:
            return False
        
        try:
            payload = {
                "chat_guid": chat_guid,
                "typing": typing,
            }
            
            return await self._api_call("typing", payload)
        except Exception as e:
            logger.error(f"Failed to set typing indicator: {e}")
            return False

    async def send_read_receipt(
        self,
        message_guid: str,
        chat_guid: str,
    ) -> bool:
        """Send read receipt for a message."""
        if not self.config.allow_read_receipts:
            return False
        
        try:
            payload = {
                "message_guid": message_guid,
                "chat_guid": chat_guid,
            }
            
            return await self._api_call("read_receipts", payload)
        except Exception as e:
            logger.error(f"Failed to send read receipt: {e}")
            return False

    async def get_chats(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get list of iMessage conversations."""
        try:
            payload = {"limit": limit}
            chats = await self._api_call("chats", payload)
            
            if chats:
                self.chats_cache = {c["guid"]: c for c in chats}
            
            return chats or []
        except Exception as e:
            logger.error(f"Failed to get chats: {e}")
            return []

    async def get_chat_messages(
        self,
        chat_guid: str,
        limit: int = 25,
        offset: int = 0,
    ) -> List[iMessage]:
        """Get messages from a specific chat."""
        try:
            payload = {
                "chat_guid": chat_guid,
                "limit": limit,
                "offset": offset,
            }
            
            messages_data = await self._api_call("messages", payload)
            
            messages = []
            for msg in (messages_data or []):
                messages.append(iMessage(
                    guid=msg.get("guid", ""),
                    chat_guid=msg.get("chat_guid", ""),
                    handle_id=msg.get("handle_id", ""),
                    text=msg.get("text", ""),
                    timestamp=datetime.fromisoformat(msg.get("timestamp", "")),
                    is_from_me=msg.get("is_from_me", False),
                    associated_message_type=msg.get("associated_message_type"),
                    associated_message_guid=msg.get("associated_message_guid"),
                    attachments=msg.get("attachments", []),
                    message_summary=msg.get("message_summary"),
                ))
            
            return messages
        except Exception as e:
            logger.error(f"Failed to get chat messages: {e}")
            return []

    async def get_handles(self) -> Dict[str, str]:
        """Get list of iMessage handles (contact info)."""
        try:
            handles = await self._api_call("handles", {})
            
            if handles:
                self.handles_cache = {h["id"]: h["address"] for h in handles}
            
            return self.handles_cache
        except Exception as e:
            logger.error(f"Failed to get handles: {e}")
            return {}

    def register_handler(self, handler: Callable) -> None:
        """Register a message handler callback."""
        self.message_handlers.append(handler)

    async def _poll_messages(self) -> None:
        """Poll BlueBubbles API for new messages."""
        last_timestamp = datetime.now()
        
        while self.running:
            try:
                payload = {"since": last_timestamp.isoformat()}
                messages_data = await self._api_call("messages/new", payload)
                
                if messages_data:
                    for msg_data in messages_data:
                        msg = iMessage(
                            guid=msg_data.get("guid", ""),
                            chat_guid=msg_data.get("chat_guid", ""),
                            handle_id=msg_data.get("handle_id", ""),
                            text=msg_data.get("text", ""),
                            timestamp=datetime.fromisoformat(msg_data.get("timestamp", "")),
                            is_from_me=msg_data.get("is_from_me", False),
                            attachments=msg_data.get("attachments", []),
                        )
                        
                        last_timestamp = msg.timestamp
                        
                        # Call handlers
                        for handler in self.message_handlers:
                            try:
                                await handler(msg)
                            except Exception as e:
                                logger.error(f"Handler error: {e}")
                
                await asyncio.sleep(2)  # Poll interval
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error polling messages: {e}")
                await asyncio.sleep(5)

    async def _verify_connection(self) -> bool:
        """Verify BlueBubbles server is accessible."""
        try:
            result = await self._api_call("health", {})
            return result is not None
        except Exception:
            return False

    async def _load_chats(self) -> None:
        """Load and cache all chats."""
        try:
            self.chats_cache = {c["guid"]: c for c in (await self.get_chats()) or []}
        except Exception as e:
            logger.warning(f"Failed to load chats: {e}")

    async def _load_handles(self) -> None:
        """Load and cache all handles."""
        try:
            self.handles_cache = await self.get_handles()
        except Exception as e:
            logger.warning(f"Failed to load handles: {e}")

    async def _api_call(self, endpoint: str, payload: Dict[str, Any]) -> Any:
        """Make API call to BlueBubbles server."""
        # Simulated API call - in production, would use actual HTTP client
        # with persistent session and API key authentication
        await asyncio.sleep(0.01)  # Simulate network delay
        return payload  # Echo payload for testing


__all__ = [
    "BlueBubblesChannel",
    "BlueBubblesConfig",
    "iMessage",
    "iMessageReactionType",
]
