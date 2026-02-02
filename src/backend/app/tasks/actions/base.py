"""
Base Action and Action Registry

Actions are executable units that tasks run. Each action type
has its own implementation with specific logic and configuration.
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, Type, List
from dataclasses import dataclass, field
import logging

from ..models import Task, ActionType


logger = logging.getLogger(__name__)


@dataclass
class ActionResult:
    """Result of an action execution"""
    success: bool
    data: Dict[str, Any] = field(default_factory=dict)
    message: str = ""
    should_notify: bool = False
    notification_title: str = ""
    notification_message: str = ""
    notification_priority: str = "normal"  # low, normal, high, urgent


class BaseAction(ABC):
    """Base class for all actions"""

    action_type: ActionType = None
    description: str = ""

    def __init__(
        self,
        stock_service=None,
        notification_service=None,
        memory_index=None,
    ):
        self.stock_service = stock_service
        self.notification_service = notification_service
        self.memory_index = memory_index

    @abstractmethod
    async def execute(self, task: Task) -> ActionResult:
        """
        Execute the action.

        Args:
            task: The task to execute

        Returns:
            ActionResult with execution result
        """
        pass

    @abstractmethod
    def validate_config(self, config: Dict[str, Any]) -> List[str]:
        """
        Validate action configuration.

        Args:
            config: The action configuration dict

        Returns:
            List of validation error messages (empty if valid)
        """
        pass

    async def send_notification(
        self,
        task: Task,
        result: ActionResult,
        channels: List[str] = None,
    ):
        """Send notification if configured"""
        if not result.should_notify or not self.notification_service:
            return

        # Get channels from task config or use provided ones
        config = task.action_config
        notify_channels = channels or config.get("notify_channels", [])

        if not notify_channels:
            return

        from ...channels import Notification, NotificationPriority, ChannelType

        # Map priority
        priority_map = {
            "low": NotificationPriority.LOW,
            "normal": NotificationPriority.NORMAL,
            "high": NotificationPriority.HIGH,
            "urgent": NotificationPriority.URGENT,
        }
        priority = priority_map.get(result.notification_priority, NotificationPriority.NORMAL)

        # Map channel names to ChannelType
        channel_map = {
            "telegram": ChannelType.TELEGRAM,
            "discord": ChannelType.DISCORD,
            "slack": ChannelType.SLACK,
            "webhook": ChannelType.WEBHOOK,
        }
        channel_types = [
            channel_map[c] for c in notify_channels
            if c in channel_map
        ]

        notification = Notification(
            title=result.notification_title or f"Task: {task.name}",
            message=result.notification_message or result.message,
            priority=priority,
            channels=channel_types if channel_types else None,
        )

        try:
            await self.notification_service.notify(notification)
            logger.info(f"Notification sent for task {task.id}")
        except Exception as e:
            logger.error(f"Failed to send notification: {e}")

    async def index_to_memory(
        self,
        task: Task,
        result: ActionResult,
    ) -> List[str]:
        """Index result to memory for later retrieval"""
        if not self.memory_index:
            return []

        # Build text for indexing
        text_parts = [
            f"Task: {task.name}",
            f"Type: {task.action_type.value}",
            f"Result: {result.message}",
        ]

        # Add relevant data
        if result.data:
            for key, value in result.data.items():
                if isinstance(value, (str, int, float)):
                    text_parts.append(f"{key}: {value}")

        text = "\n".join(text_parts)

        try:
            chunk_ids = await self.memory_index.add(
                text=text,
                source="task_execution",
                source_id=task.id,
                metadata={
                    "task_id": task.id,
                    "task_name": task.name,
                    "action_type": task.action_type.value,
                },
            )
            logger.info(f"Indexed task result to memory: {chunk_ids}")
            return chunk_ids
        except Exception as e:
            logger.error(f"Failed to index to memory: {e}")
            return []


class ActionRegistry:
    """Registry for action implementations"""

    _actions: Dict[ActionType, Type[BaseAction]] = {}

    @classmethod
    def register(cls, action_type: ActionType):
        """Decorator to register an action class"""
        def decorator(action_class: Type[BaseAction]):
            action_class.action_type = action_type
            cls._actions[action_type] = action_class
            return action_class
        return decorator

    @classmethod
    def get(cls, action_type: ActionType) -> Optional[Type[BaseAction]]:
        """Get action class by type"""
        return cls._actions.get(action_type)

    @classmethod
    def create(
        cls,
        action_type: ActionType,
        stock_service=None,
        notification_service=None,
        memory_index=None,
    ) -> Optional[BaseAction]:
        """Create an action instance"""
        action_class = cls.get(action_type)
        if not action_class:
            return None

        return action_class(
            stock_service=stock_service,
            notification_service=notification_service,
            memory_index=memory_index,
        )

    @classmethod
    def list_types(cls) -> List[ActionType]:
        """List all registered action types"""
        return list(cls._actions.keys())
