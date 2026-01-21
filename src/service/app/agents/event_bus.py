"""Event Bus for inter-agent communication."""

import asyncio
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Coroutine, Dict, List, Optional, Set
from uuid import uuid4

from loguru import logger


class EventType(Enum):
    """Event types for the agent system."""

    # System events
    SYSTEM_STARTUP = "system.startup"
    SYSTEM_SHUTDOWN = "system.shutdown"
    AGENT_STARTED = "agent.started"
    AGENT_STOPPED = "agent.stopped"
    AGENT_ERROR = "agent.error"

    # Note events
    NOTE_CREATED = "note.created"
    NOTE_UPDATED = "note.updated"
    NOTE_DELETED = "note.deleted"

    # Schedule events
    SCHEDULE_CREATED = "schedule.created"
    SCHEDULE_UPDATED = "schedule.updated"
    SCHEDULE_DELETED = "schedule.deleted"
    SCHEDULE_REMINDER = "schedule.reminder"
    SCHEDULE_CONFLICT = "schedule.conflict"

    # Content events
    CONTENT_ANALYZED = "content.analyzed"
    CONTENT_LINKED = "content.linked"
    TAGS_OPTIMIZED = "tags.optimized"

    # Todo events
    TODO_CREATED = "todo.created"
    TODO_COMPLETED = "todo.completed"
    TODO_OVERDUE = "todo.overdue"

    # Custom events
    CUSTOM = "custom"


@dataclass
class Event:
    """Event object for the event bus."""

    type: EventType
    data: Dict[str, Any] = field(default_factory=dict)
    source: str = "unknown"
    timestamp: datetime = field(default_factory=datetime.now)
    id: str = field(default_factory=lambda: str(uuid4()))

    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary."""
        return {
            "id": self.id,
            "type": self.type.value,
            "data": self.data,
            "source": self.source,
            "timestamp": self.timestamp.isoformat(),
        }


# Type alias for event handlers
EventHandler = Callable[[Event], Coroutine[Any, Any, None]]


class EventBus:
    """
    Event Bus for publish-subscribe communication between agents.

    Supports:
    - Async event handling
    - Multiple subscribers per event type
    - Event history tracking
    - Wildcard subscriptions
    """

    def __init__(self, max_history: int = 100):
        """
        Initialize the event bus.

        Args:
            max_history: Maximum number of events to keep in history
        """
        self._subscribers: Dict[EventType, Set[EventHandler]] = {}
        self._history: List[Event] = []
        self._max_history = max_history
        self._lock = asyncio.Lock()

    def subscribe(self, event_type: EventType, handler: EventHandler) -> None:
        """
        Subscribe to an event type.

        Args:
            event_type: Type of event to subscribe to
            handler: Async function to handle the event
        """
        if event_type not in self._subscribers:
            self._subscribers[event_type] = set()
        self._subscribers[event_type].add(handler)
        logger.debug(f"Handler subscribed to {event_type.value}")

    def unsubscribe(self, event_type: EventType, handler: EventHandler) -> None:
        """
        Unsubscribe from an event type.

        Args:
            event_type: Type of event to unsubscribe from
            handler: Handler to remove
        """
        if event_type in self._subscribers:
            self._subscribers[event_type].discard(handler)
            logger.debug(f"Handler unsubscribed from {event_type.value}")

    async def publish(self, event: Event) -> None:
        """
        Publish an event to all subscribers.

        Args:
            event: Event to publish
        """
        async with self._lock:
            # Add to history
            self._history.append(event)
            if len(self._history) > self._max_history:
                self._history = self._history[-self._max_history:]

        logger.debug(f"Publishing event: {event.type.value} from {event.source}")

        # Get handlers for this event type
        handlers = self._subscribers.get(event.type, set())

        # Execute all handlers concurrently
        if handlers:
            tasks = [self._safe_handle(handler, event) for handler in handlers]
            await asyncio.gather(*tasks)

    async def _safe_handle(self, handler: EventHandler, event: Event) -> None:
        """Safely execute a handler, catching any exceptions."""
        try:
            await handler(event)
        except Exception as e:
            logger.error(f"Error in event handler for {event.type.value}: {e}")

    async def emit(
        self,
        event_type: EventType,
        data: Optional[Dict[str, Any]] = None,
        source: str = "unknown",
    ) -> Event:
        """
        Convenience method to create and publish an event.

        Args:
            event_type: Type of event
            data: Event data
            source: Source of the event

        Returns:
            The created event
        """
        event = Event(
            type=event_type,
            data=data or {},
            source=source,
        )
        await self.publish(event)
        return event

    def get_history(
        self,
        event_type: Optional[EventType] = None,
        limit: int = 50,
    ) -> List[Event]:
        """
        Get event history.

        Args:
            event_type: Filter by event type (optional)
            limit: Maximum number of events to return

        Returns:
            List of events
        """
        events = self._history
        if event_type:
            events = [e for e in events if e.type == event_type]
        return events[-limit:]

    def get_subscriber_count(self, event_type: EventType) -> int:
        """Get number of subscribers for an event type."""
        return len(self._subscribers.get(event_type, set()))

    def clear_history(self) -> None:
        """Clear event history."""
        self._history.clear()


# Global event bus instance
_event_bus: Optional[EventBus] = None


def get_event_bus() -> EventBus:
    """Get or create the global event bus instance."""
    global _event_bus
    if _event_bus is None:
        _event_bus = EventBus()
    return _event_bus
