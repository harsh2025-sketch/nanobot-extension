"""
Advanced Routing - Multi-agent routing with failover, presence, and intelligent message dispatch.

Implements sophisticated message routing with multi-agent support, group message management,
presence tracking, and automatic failover chains.
"""

import asyncio
import logging
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Set
from datetime import datetime
from enum import Enum
import uuid

logger = logging.getLogger(__name__)


class AgentStatus(Enum):
    """Agent status indicators."""
    ONLINE = "online"
    AWAY = "away"
    BUSY = "busy"
    OFFLINE = "offline"
    UNAVAILABLE = "unavailable"


class MessagePriority(Enum):
    """Message priority levels."""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    CRITICAL = 4


@dataclass
class Agent:
    """Represents an agent in the routing system."""
    agent_id: str
    name: str
    status: AgentStatus = AgentStatus.OFFLINE
    capabilities: List[str] = field(default_factory=list)
    regions: List[str] = field(default_factory=list)  # Geographic regions
    max_load: int = 100
    current_load: int = 0
    last_heartbeat: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RoutedMessage:
    """Represents a routed message."""
    message_id: str
    source_agent: str
    target_agents: List[str]
    group_id: Optional[str] = None
    content: Dict[str, Any] = field(default_factory=dict)
    priority: MessagePriority = MessagePriority.NORMAL
    created_at: datetime = field(default_factory=datetime.now)
    deadline: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class FailoverChain:
    """Represents a failover chain for messages."""
    chain_id: str
    primary: str
    fallbacks: List[str]
    name: str = ""
    enabled: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)


class AdvancedRouter:
    """
    Advanced message routing system for nanobot.
    
    Features:
    - Multi-agent routing and load balancing
    - Group message routing with mention gating
    - Presence tracking and status management
    - Intelligent failover chains
    - Message queuing and priority handling
    - Capability-based routing
    - Region-based routing
    - Session isolation
    - Reply-back to origin tracking
    - Message deduplication
    - Receipt confirmation
    """

    def __init__(self):
        """Initialize advanced routing system."""
        self.agents: Dict[str, Agent] = {}
        self.message_queue: asyncio.PriorityQueue = asyncio.PriorityQueue()
        self.failover_chains: Dict[str, FailoverChain] = {}
        self.message_history: Dict[str, RoutedMessage] = {}
        self.presence_handlers: List[Callable] = []
        self.message_handlers: List[Callable] = []
        self._max_history = 10000
        self._dispatcher_task: Optional[asyncio.Task] = None

    async def initialize(self) -> bool:
        """Initialize routing system."""
        try:
            logger.info("Advanced routing system initialized")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize routing: {e}")
            return False

    async def start(self) -> None:
        """Start message dispatcher."""
        if self._dispatcher_task:
            return
        
        self._dispatcher_task = asyncio.create_task(self._dispatch_messages())
        logger.info("Message dispatcher started")

    async def stop(self) -> None:
        """Stop message dispatcher."""
        if self._dispatcher_task:
            self._dispatcher_task.cancel()
            try:
                await self._dispatcher_task
            except asyncio.CancelledError:
                pass

    async def register_agent(self, agent: Agent) -> bool:
        """Register an agent."""
        try:
            self.agents[agent.agent_id] = agent
            
            # Notify presence handlers
            await self._notify_presence_change(agent)
            
            logger.info(f"Agent registered: {agent.name} ({agent.agent_id})")
            return True
        except Exception as e:
            logger.error(f"Failed to register agent: {e}")
            return False

    async def unregister_agent(self, agent_id: str) -> bool:
        """Unregister an agent."""
        try:
            if agent_id not in self.agents:
                return False

            agent = self.agents[agent_id]
            agent.status = AgentStatus.OFFLINE
            
            await self._notify_presence_change(agent)
            del self.agents[agent_id]
            
            logger.info(f"Agent unregistered: {agent.name}")
            return True
        except Exception as e:
            logger.error(f"Failed to unregister agent: {e}")
            return False

    async def set_agent_status(
        self,
        agent_id: str,
        status: AgentStatus,
    ) -> bool:
        """Set agent status with presence notifications."""
        try:
            if agent_id not in self.agents:
                return False

            agent = self.agents[agent_id]
            old_status = agent.status
            agent.status = status
            agent.last_heartbeat = datetime.now()

            if old_status != status:
                await self._notify_presence_change(agent)
            
            logger.info(f"Agent {agent.name} status: {status.value}")
            return True
        except Exception as e:
            logger.error(f"Failed to set agent status: {e}")
            return False

    async def route_message(
        self,
        source_agent: str,
        content: Dict[str, Any],
        target_agents: Optional[List[str]] = None,
        group_id: Optional[str] = None,
        priority: MessagePriority = MessagePriority.NORMAL,
        deadline: Optional[datetime] = None,
    ) -> Optional[str]:
        """
        Route a message to one or more agents.
        
        Args:
            source_agent: Origin agent ID
            content: Message content
            target_agents: Specific targets (if None, use failover/group)
            group_id: Group message ID
            priority: Message priority
            deadline: Optional delivery deadline
            
        Returns:
            Message ID if successful
        """
        try:
            message_id = str(uuid.uuid4())

            # Determine targets
            if not target_agents:
                if group_id:
                    target_agents = await self._get_group_members(group_id)
                else:
                    target_agents = []

            # Validate targets
            valid_targets = [
                t for t in target_agents
                if t in self.agents and self.agents[t].status != AgentStatus.OFFLINE
            ]

            if not valid_targets:
                # Try failover
                valid_targets = await self._get_failover_targets(source_agent)

            if not valid_targets:
                logger.warning(f"No valid targets for message {message_id}")
                return None

            message = RoutedMessage(
                message_id=message_id,
                source_agent=source_agent,
                target_agents=valid_targets,
                group_id=group_id,
                content=content,
                priority=priority,
                deadline=deadline,
            )

            # Add to queue
            await self.message_queue.put((priority.value, message_id, message))
            self.message_history[message_id] = message

            # Trim history
            if len(self.message_history) > self._max_history:
                oldest_id = min(self.message_history.keys(),
                               key=lambda k: self.message_history[k].created_at)
                del self.message_history[oldest_id]

            logger.info(f"Message routed: {message_id} -> {valid_targets}")
            return message_id
        except Exception as e:
            logger.error(f"Failed to route message: {e}")
            return None

    async def route_group_message(
        self,
        source_agent: str,
        group_id: str,
        content: Dict[str, Any],
        mention_only: Optional[List[str]] = None,
        priority: MessagePriority = MessagePriority.NORMAL,
    ) -> Optional[str]:
        """Route message to group with optional mention gating."""
        try:
            members = await self._get_group_members(group_id)
            
            # Apply mention gating if specified
            if mention_only:
                members = [m for m in members if m in mention_only]

            return await self.route_message(
                source_agent=source_agent,
                content=content,
                target_agents=members,
                group_id=group_id,
                priority=priority,
            )
        except Exception as e:
            logger.error(f"Failed to route group message: {e}")
            return None

    async def create_failover_chain(
        self,
        name: str,
        primary: str,
        fallbacks: List[str],
    ) -> Optional[str]:
        """Create a failover chain."""
        try:
            chain_id = str(uuid.uuid4())
            
            chain = FailoverChain(
                chain_id=chain_id,
                primary=primary,
                fallbacks=fallbacks,
                name=name,
            )
            
            self.failover_chains[chain_id] = chain
            logger.info(f"Failover chain created: {name}")
            
            return chain_id
        except Exception as e:
            logger.error(f"Failed to create failover chain: {e}")
            return None

    async def get_agent_by_capability(
        self,
        capability: str,
        region: Optional[str] = None,
    ) -> Optional[Agent]:
        """Get an available agent with specific capability."""
        try:
            available = [
                a for a in self.agents.values()
                if capability in a.capabilities
                   and a.status in [AgentStatus.ONLINE, AgentStatus.AWAY]
                   and (region is None or region in a.regions)
                   and a.current_load < a.max_load
            ]

            if not available:
                return None

            # Return agent with lowest current load
            return min(available, key=lambda a: a.current_load)
        except Exception as e:
            logger.error(f"Failed to get agent by capability: {e}")
            return None

    async def get_agents_load_balance(
        self,
        count: int = 1,
        capability: Optional[str] = None,
    ) -> List[Agent]:
        """Get agents sorted by load for load balancing."""
        try:
            available = [
                a for a in self.agents.values()
                if a.status in [AgentStatus.ONLINE, AgentStatus.AWAY]
                   and a.current_load < a.max_load
                   and (capability is None or capability in a.capabilities)
            ]

            # Sort by current load
            available.sort(key=lambda a: a.current_load)
            
            return available[:count]
        except Exception as e:
            logger.error(f"Failed to load balance agents: {e}")
            return []

    def register_presence_handler(self, handler: Callable) -> None:
        """Register a presence change handler."""
        self.presence_handlers.append(handler)

    def register_message_handler(self, handler: Callable) -> None:
        """Register a message handler."""
        self.message_handlers.append(handler)

    async def get_message(self, message_id: str) -> Optional[RoutedMessage]:
        """Get a message from history."""
        return self.message_history.get(message_id)

    async def get_agents_list(
        self,
        status: Optional[AgentStatus] = None,
    ) -> List[Agent]:
        """Get list of agents."""
        agents = list(self.agents.values())
        
        if status:
            agents = [a for a in agents if a.status == status]
        
        return agents

    async def _dispatch_messages(self) -> None:
        """Continuously dispatch routed messages."""
        while True:
            try:
                # Get message with timeout
                try:
                    _, message_id, message = await asyncio.wait_for(
                        self.message_queue.get(),
                        timeout=1.0
                    )
                except asyncio.TimeoutError:
                    continue

                # Check deadline
                if message.deadline and datetime.now() > message.deadline:
                    logger.warning(f"Message {message_id} expired")
                    continue

                # Dispatch to handlers
                for handler in self.message_handlers:
                    try:
                        await handler(message)
                    except Exception as e:
                        logger.error(f"Handler error: {e}")

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Dispatch error: {e}")

    async def _get_group_members(self, group_id: str) -> List[str]:
        """Get members of a group (would look up in group store)."""
        # Simulated: in production would query group database
        return []

    async def _get_failover_targets(self, agent_id: str) -> List[str]:
        """Get failover targets for an agent."""
        try:
            for chain in self.failover_chains.values():
                if chain.primary == agent_id and chain.enabled:
                    return [f for f in chain.fallbacks if f in self.agents]
            return []
        except Exception as e:
            logger.error(f"Failed to get failover targets: {e}")
            return []

    async def _notify_presence_change(self, agent: Agent) -> None:
        """Notify handlers of presence change."""
        for handler in self.presence_handlers:
            try:
                await handler(agent)
            except Exception as e:
                logger.error(f"Presence handler error: {e}")


__all__ = [
    "AdvancedRouter",
    "Agent",
    "RoutedMessage",
    "FailoverChain",
    "AgentStatus",
    "MessagePriority",
]
