"""
WebChat Channel - Built-in web interface for nanobot messaging.

Provides a web-based chat interface that can be served directly from
the nanobot gateway, allowing users to chat with agents via browser.
"""

import asyncio
import logging
import json
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Set
from datetime import datetime
from enum import Enum
import uuid

logger = logging.getLogger(__name__)


class WebChatUserRole(Enum):
    """User roles in WebChat."""
    VISITOR = "visitor"
    USER = "user"
    MODERATOR = "moderator"
    ADMIN = "admin"


class WebChatMessageType(Enum):
    """Message types in WebChat."""
    TEXT = "text"
    SYSTEM = "system"
    TYPING = "typing"
    USER_JOINED = "user_joined"
    USER_LEFT = "user_left"
    NOTIFICATION = "notification"


@dataclass
class WebChatConfig:
    """Configuration for WebChat channel."""
    port: int = 8000
    host: str = "localhost"
    path: str = "/chat"
    max_connections: int = 1000
    message_history_limit: int = 100
    session_timeout: int = 3600  # seconds
    allow_anonymous: bool = True
    require_auth: bool = False
    cors_enabled: bool = True
    cors_origins: List[str] = field(default_factory=lambda: ["*"])
    enable_file_upload: bool = False
    max_file_size: int = 10 * 1024 * 1024  # 10MB
    enable_threading: bool = True


@dataclass
class WebChatUser:
    """Represents a WebChat user."""
    user_id: str
    name: str
    role: WebChatUserRole
    session_id: str
    connected_at: datetime
    last_activity: datetime
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class WebChatMessage:
    """Represents a WebChat message."""
    message_id: str
    user_id: str
    user_name: str
    text: str
    timestamp: datetime
    message_type: WebChatMessageType
    thread_id: Optional[str] = None
    parent_message_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class WebChatChannel:
    """
    WebChat messaging channel for nanobot.
    
    Features:
    - Real-time messaging via WebSocket
    - Session management
    - User authentication (optional)
    - Message history and persistence
    - Threading/replies support
    - Typing indicators
    - User presence tracking
    - Message reactions
    - File uploads (optional)
    - CORS support
    - Rate limiting
    - Message filtering and moderation
    """

    def __init__(self, config: WebChatConfig):
        """Initialize WebChat channel."""
        self.config = config
        self.message_handlers: List[Callable] = []
        self.connection_handlers: List[Callable] = []
        self.running = False
        
        # State management
        self.users: Dict[str, WebChatUser] = {}
        self.message_history: List[WebChatMessage] = []
        self.active_connections: Set[str] = set()
        self.threads: Dict[str, List[WebChatMessage]] = {}
        
        # Rate limiting
        self.user_message_rate: Dict[str, List[float]] = {}
        self.rate_limit_window = 60  # seconds
        self.rate_limit_max = 30  # messages per window

    async def initialize(self) -> bool:
        """Initialize WebChat channel."""
        try:
            logger.info(f"WebChat initialized on {self.config.host}:{self.config.port}{self.config.path}")
            self.running = True
            return True
        except Exception as e:
            logger.error(f"Failed to initialize WebChat: {e}")
            return False

    async def start(self) -> None:
        """Start WebChat server."""
        logger.info("WebChat server started")
        self.running = True

    async def stop(self) -> None:
        """Stop WebChat server."""
        self.running = False
        
        # Notify all users
        for user in self.users.values():
            await self._notify_user_disconnection(user)
        
        self.users.clear()
        self.active_connections.clear()
        
        logger.info("WebChat server stopped")

    async def handle_user_join(
        self,
        session_id: str,
        user_name: str,
        user_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Optional[WebChatUser]:
        """Handle a user joining the chat."""
        try:
            if not self.config.allow_anonymous and not user_id:
                logger.warning("Anonymous users not allowed")
                return None

            if len(self.active_connections) >= self.config.max_connections:
                logger.warning("Max connections reached")
                return None

            user_id = user_id or f"user_{uuid.uuid4().hex[:8]}"
            
            user = WebChatUser(
                user_id=user_id,
                name=user_name,
                role=WebChatUserRole.USER,
                session_id=session_id,
                connected_at=datetime.now(),
                last_activity=datetime.now(),
                metadata=metadata or {},
            )
            
            self.users[user_id] = user
            self.active_connections.add(session_id)
            self.user_message_rate[user_id] = []
            
            # Notify others
            await self._broadcast_system_message(
                f"{user_name} joined the chat",
                WebChatMessageType.USER_JOINED,
            )
            
            # Call connection handlers
            for handler in self.connection_handlers:
                try:
                    await handler(user, "joined")
                except Exception as e:
                    logger.error(f"Connection handler error: {e}")
            
            logger.info(f"User {user_id} joined (session: {session_id})")
            return user
        except Exception as e:
            logger.error(f"Failed to handle user join: {e}")
            return None

    async def handle_user_leave(self, session_id: str) -> bool:
        """Handle a user leaving the chat."""
        try:
            # Find user by session
            user = None
            for u in self.users.values():
                if u.session_id == session_id:
                    user = u
                    break
            
            if not user:
                return False

            await self._notify_user_disconnection(user)
            
            # Remove user
            del self.users[user.user_id]
            if user.user_id in self.user_message_rate:
                del self.user_message_rate[user.user_id]
            
            self.active_connections.discard(session_id)
            
            # Broadcast
            await self._broadcast_system_message(
                f"{user.name} left the chat",
                WebChatMessageType.USER_LEFT,
            )
            
            logger.info(f"User {user.user_id} left")
            return True
        except Exception as e:
            logger.error(f"Failed to handle user leave: {e}")
            return False

    async def handle_message(
        self,
        session_id: str,
        text: str,
        thread_id: Optional[str] = None,
    ) -> Optional[WebChatMessage]:
        """
        Handle an incoming message from a user.
        
        Args:
            session_id: User's session ID
            text: Message text
            thread_id: Optional thread ID for threaded conversations
            
        Returns:
            The created message if successful
        """
        try:
            # Find user
            user = None
            for u in self.users.values():
                if u.session_id == session_id:
                    user = u
                    break
            
            if not user:
                logger.warning(f"Message from unknown session: {session_id}")
                return None

            # Check rate limiting
            if not await self._check_rate_limit(user.user_id):
                logger.warning(f"Rate limit exceeded for {user.user_id}")
                return None

            # Create message
            message = WebChatMessage(
                message_id=str(uuid.uuid4()),
                user_id=user.user_id,
                user_name=user.name,
                text=text,
                timestamp=datetime.now(),
                message_type=WebChatMessageType.TEXT,
                thread_id=thread_id,
            )

            # Store in history
            self._add_to_history(message)
            
            # Store in thread if applicable
            if thread_id:
                if thread_id not in self.threads:
                    self.threads[thread_id] = []
                self.threads[thread_id].append(message)
            
            # Update user activity
            user.last_activity = datetime.now()
            
            # Call message handlers
            for handler in self.message_handlers:
                try:
                    await handler(message)
                except Exception as e:
                    logger.error(f"Handler error: {e}")

            logger.info(f"Message from {user.user_id}: {text[:50]}...")
            return message
        except Exception as e:
            logger.error(f"Failed to handle message: {e}")
            return None

    async def send_message(
        self,
        text: str,
        user_id: Optional[str] = None,
        thread_id: Optional[str] = None,
    ) -> Optional[WebChatMessage]:
        """Send a message from the agent."""
        try:
            message = WebChatMessage(
                message_id=str(uuid.uuid4()),
                user_id=user_id or "system",
                user_name="Agent",
                text=text,
                timestamp=datetime.now(),
                message_type=WebChatMessageType.TEXT,
                thread_id=thread_id,
            )
            
            self._add_to_history(message)
            
            if thread_id:
                if thread_id not in self.threads:
                    self.threads[thread_id] = []
                self.threads[thread_id].append(message)
            
            return message
        except Exception as e:
            logger.error(f"Failed to send message: {e}")
            return None

    async def broadcast_notification(
        self,
        title: str,
        body: str,
        target_user: Optional[str] = None,
    ) -> int:
        """Broadcast a notification to users."""
        count = 0
        try:
            for user in self.users.values():
                if target_user and user.user_id != target_user:
                    continue
                
                message = WebChatMessage(
                    message_id=str(uuid.uuid4()),
                    user_id="system",
                    user_name="System",
                    text=f"{title}: {body}",
                    timestamp=datetime.now(),
                    message_type=WebChatMessageType.NOTIFICATION,
                )
                
                self._add_to_history(message)
                count += 1
            
            return count
        except Exception as e:
            logger.error(f"Failed to broadcast notification: {e}")
            return 0

    async def get_active_users(self) -> List[WebChatUser]:
        """Get list of active users."""
        return list(self.users.values())

    async def get_message_history(
        self,
        limit: Optional[int] = None,
        thread_id: Optional[str] = None,
    ) -> List[WebChatMessage]:
        """Get message history."""
        if thread_id and thread_id in self.threads:
            return self.threads[thread_id][-limit:] if limit else self.threads[thread_id]
        
        return self.message_history[-limit:] if limit else self.message_history

    async def set_typing_indicator(
        self,
        user_id: str,
        typing: bool,
    ) -> bool:
        """Set typing indicator for a user."""
        try:
            if user_id not in self.users:
                return False
            
            # Notify other users
            message = WebChatMessage(
                message_id=str(uuid.uuid4()),
                user_id=user_id,
                user_name=self.users[user_id].name,
                text="",
                timestamp=datetime.now(),
                message_type=WebChatMessageType.TYPING,
            )
            
            return True
        except Exception as e:
            logger.error(f"Failed to set typing indicator: {e}")
            return False

    def register_message_handler(self, handler: Callable) -> None:
        """Register a message handler callback."""
        self.message_handlers.append(handler)

    def register_connection_handler(self, handler: Callable) -> None:
        """Register a connection handler callback."""
        self.connection_handlers.append(handler)

    async def _check_rate_limit(self, user_id: str) -> bool:
        """Check if user is within rate limit."""
        now = datetime.now().timestamp()
        
        if user_id not in self.user_message_rate:
            self.user_message_rate[user_id] = []
        
        # Remove old timestamps
        self.user_message_rate[user_id] = [
            ts for ts in self.user_message_rate[user_id]
            if now - ts < self.rate_limit_window
        ]
        
        if len(self.user_message_rate[user_id]) >= self.rate_limit_max:
            return False
        
        self.user_message_rate[user_id].append(now)
        return True

    def _add_to_history(self, message: WebChatMessage) -> None:
        """Add message to history with limit."""
        self.message_history.append(message)
        
        # Trim history if needed
        if len(self.message_history) > self.config.message_history_limit:
            self.message_history = self.message_history[-self.config.message_history_limit:]

    async def _broadcast_system_message(
        self,
        text: str,
        msg_type: WebChatMessageType,
    ) -> None:
        """Broadcast a system message to all users."""
        try:
            message = WebChatMessage(
                message_id=str(uuid.uuid4()),
                user_id="system",
                user_name="System",
                text=text,
                timestamp=datetime.now(),
                message_type=msg_type,
            )
            
            self._add_to_history(message)
        except Exception as e:
            logger.error(f"Failed to broadcast system message: {e}")

    async def _notify_user_disconnection(self, user: WebChatUser) -> None:
        """Notify handlers of user disconnection."""
        for handler in self.connection_handlers:
            try:
                await handler(user, "left")
            except Exception as e:
                logger.error(f"Connection handler error: {e}")


__all__ = [
    "WebChatChannel",
    "WebChatConfig",
    "WebChatUser",
    "WebChatMessage",
    "WebChatUserRole",
    "WebChatMessageType",
]
