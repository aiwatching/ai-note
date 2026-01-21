"""Master Scheduler Agent for managing all other agents."""

import asyncio
from datetime import datetime
from typing import Any, Dict, List, Optional, Type

from loguru import logger

from .base import AgentStatus, BaseAgent
from .event_bus import Event, EventBus, EventType, get_event_bus


class MasterScheduler:
    """
    Master Scheduler Agent that manages all other agents.

    Responsibilities:
    - Start/stop agents
    - Monitor agent health
    - Distribute tasks to appropriate agents
    - Handle system-wide events
    """

    def __init__(self, event_bus: Optional[EventBus] = None):
        """
        Initialize the master scheduler.

        Args:
            event_bus: Event bus for communication (uses global if not provided)
        """
        self.event_bus = event_bus or get_event_bus()
        self._agents: Dict[str, BaseAgent] = {}
        self._running = False
        self._monitor_task: Optional[asyncio.Task] = None
        self._started_at: Optional[datetime] = None

    @property
    def is_running(self) -> bool:
        """Check if scheduler is running."""
        return self._running

    def register_agent(self, agent: BaseAgent) -> None:
        """
        Register an agent with the scheduler.

        Args:
            agent: Agent instance to register
        """
        if agent.name in self._agents:
            logger.warning(f"Agent {agent.name} already registered, replacing")

        self._agents[agent.name] = agent
        agent.event_bus = self.event_bus
        logger.info(f"Registered agent: {agent.name}")

    def unregister_agent(self, name: str) -> Optional[BaseAgent]:
        """
        Unregister an agent from the scheduler.

        Args:
            name: Name of the agent to unregister

        Returns:
            The unregistered agent or None
        """
        agent = self._agents.pop(name, None)
        if agent:
            logger.info(f"Unregistered agent: {name}")
        return agent

    def get_agent(self, name: str) -> Optional[BaseAgent]:
        """Get an agent by name."""
        return self._agents.get(name)

    def list_agents(self) -> List[str]:
        """List all registered agent names."""
        return list(self._agents.keys())

    async def start(self) -> None:
        """Start the master scheduler and all registered agents."""
        if self._running:
            logger.warning("Master scheduler is already running")
            return

        logger.info("Starting Master Scheduler")
        self._running = True
        self._started_at = datetime.now()

        # Emit system startup event
        await self.event_bus.emit(
            EventType.SYSTEM_STARTUP,
            {"timestamp": self._started_at.isoformat()},
            source="master_scheduler",
        )

        # Start all registered agents
        for name, agent in self._agents.items():
            try:
                await agent.start()
                await self.event_bus.emit(
                    EventType.AGENT_STARTED,
                    {"agent_name": name},
                    source="master_scheduler",
                )
            except Exception as e:
                logger.error(f"Failed to start agent {name}: {e}")
                await self.event_bus.emit(
                    EventType.AGENT_ERROR,
                    {"agent_name": name, "error": str(e)},
                    source="master_scheduler",
                )

        # Start the monitor task
        self._monitor_task = asyncio.create_task(self._monitor_agents())

        logger.info(f"Master Scheduler started with {len(self._agents)} agents")

    async def stop(self) -> None:
        """Stop the master scheduler and all agents."""
        if not self._running:
            logger.warning("Master scheduler is not running")
            return

        logger.info("Stopping Master Scheduler")

        # Stop monitor task
        if self._monitor_task:
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass

        # Stop all agents
        for name, agent in self._agents.items():
            try:
                await agent.stop()
                await self.event_bus.emit(
                    EventType.AGENT_STOPPED,
                    {"agent_name": name},
                    source="master_scheduler",
                )
            except Exception as e:
                logger.error(f"Error stopping agent {name}: {e}")

        # Emit system shutdown event
        await self.event_bus.emit(
            EventType.SYSTEM_SHUTDOWN,
            {"timestamp": datetime.now().isoformat()},
            source="master_scheduler",
        )

        self._running = False
        logger.info("Master Scheduler stopped")

    async def start_agent(self, name: str) -> bool:
        """
        Start a specific agent.

        Args:
            name: Name of the agent to start

        Returns:
            True if started successfully
        """
        agent = self._agents.get(name)
        if not agent:
            logger.error(f"Agent {name} not found")
            return False

        try:
            await agent.start()
            await self.event_bus.emit(
                EventType.AGENT_STARTED,
                {"agent_name": name},
                source="master_scheduler",
            )
            return True
        except Exception as e:
            logger.error(f"Failed to start agent {name}: {e}")
            return False

    async def stop_agent(self, name: str) -> bool:
        """
        Stop a specific agent.

        Args:
            name: Name of the agent to stop

        Returns:
            True if stopped successfully
        """
        agent = self._agents.get(name)
        if not agent:
            logger.error(f"Agent {name} not found")
            return False

        try:
            await agent.stop()
            await self.event_bus.emit(
                EventType.AGENT_STOPPED,
                {"agent_name": name},
                source="master_scheduler",
            )
            return True
        except Exception as e:
            logger.error(f"Failed to stop agent {name}: {e}")
            return False

    async def _monitor_agents(self) -> None:
        """Monitor agent health and restart failed agents."""
        while self._running:
            for name, agent in self._agents.items():
                if agent.status == AgentStatus.ERROR:
                    logger.warning(f"Agent {name} is in error state, attempting restart")
                    try:
                        await agent.stop()
                        await asyncio.sleep(5)  # Wait before restart
                        await agent.start()
                        logger.info(f"Agent {name} restarted successfully")
                    except Exception as e:
                        logger.error(f"Failed to restart agent {name}: {e}")

            await asyncio.sleep(30)  # Check every 30 seconds

    def get_status(self) -> Dict[str, Any]:
        """Get scheduler and all agents status."""
        return {
            "running": self._running,
            "started_at": self._started_at.isoformat() if self._started_at else None,
            "agent_count": len(self._agents),
            "agents": {
                name: agent.get_status()
                for name, agent in self._agents.items()
            },
        }


# Global scheduler instance
_scheduler: Optional[MasterScheduler] = None


def get_scheduler() -> MasterScheduler:
    """Get or create the global scheduler instance."""
    global _scheduler
    if _scheduler is None:
        _scheduler = MasterScheduler()
    return _scheduler
