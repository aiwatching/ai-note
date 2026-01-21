"""Base Agent class for the Agent system."""

import asyncio
from abc import ABC, abstractmethod
from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional, TYPE_CHECKING

from loguru import logger

if TYPE_CHECKING:
    from .event_bus import EventBus


class AgentStatus(Enum):
    """Agent status enumeration."""
    IDLE = "idle"
    RUNNING = "running"
    PAUSED = "paused"
    STOPPED = "stopped"
    ERROR = "error"


class BaseAgent(ABC):
    """
    Base class for all agents in the system.

    Each agent runs as an async task and can:
    - Subscribe to events from the event bus
    - Publish events to the event bus
    - Execute periodic tasks
    - Handle specific tasks assigned by the scheduler
    """

    def __init__(
        self,
        name: str,
        event_bus: Optional["EventBus"] = None,
        interval_seconds: int = 60,
    ):
        """
        Initialize the agent.

        Args:
            name: Unique name for the agent
            event_bus: Event bus for inter-agent communication
            interval_seconds: Default interval for periodic tasks
        """
        self.name = name
        self.event_bus = event_bus
        self.interval_seconds = interval_seconds
        self.status = AgentStatus.IDLE
        self._task: Optional[asyncio.Task] = None
        self._stop_event = asyncio.Event()
        self._last_run: Optional[datetime] = None
        self._run_count = 0
        self._error_count = 0
        self._metadata: Dict[str, Any] = {}

    @property
    def is_running(self) -> bool:
        """Check if agent is running."""
        return self.status == AgentStatus.RUNNING

    @abstractmethod
    async def setup(self) -> None:
        """
        Setup the agent before running.

        Override this method to initialize resources, subscribe to events, etc.
        """
        pass

    @abstractmethod
    async def run_cycle(self) -> None:
        """
        Execute one cycle of the agent's main task.

        This method is called periodically based on interval_seconds.
        Override this method to implement the agent's core logic.
        """
        pass

    @abstractmethod
    async def cleanup(self) -> None:
        """
        Cleanup resources when the agent stops.

        Override this method to release resources, unsubscribe from events, etc.
        """
        pass

    async def start(self) -> None:
        """Start the agent."""
        if self.status == AgentStatus.RUNNING:
            logger.warning(f"Agent {self.name} is already running")
            return

        logger.info(f"Starting agent: {self.name}")
        self._stop_event.clear()
        self.status = AgentStatus.RUNNING

        try:
            await self.setup()
            self._task = asyncio.create_task(self._run_loop())
            logger.info(f"Agent {self.name} started successfully")
        except Exception as e:
            logger.error(f"Failed to start agent {self.name}: {e}")
            self.status = AgentStatus.ERROR
            raise

    async def stop(self) -> None:
        """Stop the agent gracefully."""
        if self.status == AgentStatus.STOPPED:
            logger.warning(f"Agent {self.name} is already stopped")
            return

        logger.info(f"Stopping agent: {self.name}")
        self._stop_event.set()
        self.status = AgentStatus.STOPPED

        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

        try:
            await self.cleanup()
            logger.info(f"Agent {self.name} stopped successfully")
        except Exception as e:
            logger.error(f"Error during cleanup of agent {self.name}: {e}")

    async def pause(self) -> None:
        """Pause the agent."""
        if self.status == AgentStatus.RUNNING:
            self.status = AgentStatus.PAUSED
            logger.info(f"Agent {self.name} paused")

    async def resume(self) -> None:
        """Resume the agent."""
        if self.status == AgentStatus.PAUSED:
            self.status = AgentStatus.RUNNING
            logger.info(f"Agent {self.name} resumed")

    async def _run_loop(self) -> None:
        """Main run loop for the agent."""
        while not self._stop_event.is_set():
            if self.status == AgentStatus.PAUSED:
                await asyncio.sleep(1)
                continue

            try:
                self._last_run = datetime.now()
                await self.run_cycle()
                self._run_count += 1
            except Exception as e:
                self._error_count += 1
                logger.error(f"Error in agent {self.name} run cycle: {e}")
                if self._error_count > 10:
                    logger.error(f"Agent {self.name} exceeded error threshold, stopping")
                    self.status = AgentStatus.ERROR
                    break

            # Wait for next cycle
            try:
                await asyncio.wait_for(
                    self._stop_event.wait(),
                    timeout=self.interval_seconds
                )
            except asyncio.TimeoutError:
                # Normal timeout, continue to next cycle
                pass

    def get_status(self) -> Dict[str, Any]:
        """Get agent status information."""
        return {
            "name": self.name,
            "status": self.status.value,
            "last_run": self._last_run.isoformat() if self._last_run else None,
            "run_count": self._run_count,
            "error_count": self._error_count,
            "interval_seconds": self.interval_seconds,
            "metadata": self._metadata,
        }

    def set_metadata(self, key: str, value: Any) -> None:
        """Set metadata for the agent."""
        self._metadata[key] = value

    def get_metadata(self, key: str, default: Any = None) -> Any:
        """Get metadata for the agent."""
        return self._metadata.get(key, default)
