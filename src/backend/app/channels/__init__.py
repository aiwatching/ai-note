"""
Notification Channels

Multi-platform notification system inspired by OpenClaw's channel architecture.

Supported channels:
- Telegram (bot API)
- Discord (webhook or bot)
- Slack (webhook)
- Generic Webhook

Quick start:
    from app.channels import notification_service, Notification

    # Configure from environment
    notification_service.configure_from_env()

    # Or configure manually
    notification_service.configure_telegram(
        bot_token="123:ABC...",
        default_chat_id="12345678"
    )

    # Send notification
    result = await notification_service.notify(Notification(
        title="Reminder",
        message="Don't forget the meeting!",
    ))
"""

from .base import (
    ChannelType,
    ChannelCapabilities,
    BaseChannel,
    ChannelRegistry,
    OutboundMessage,
    DeliveryResult,
    registry,
)
from .telegram import TelegramChannel
from .discord import DiscordChannel
from .webhook import WebhookChannel, SlackWebhookChannel
from .notification import (
    NotificationService,
    NotificationPriority,
    Notification,
    NotificationResult,
    notification_service,
)

__all__ = [
    # Base
    "ChannelType",
    "ChannelCapabilities",
    "BaseChannel",
    "ChannelRegistry",
    "OutboundMessage",
    "DeliveryResult",
    "registry",
    # Channels
    "TelegramChannel",
    "DiscordChannel",
    "WebhookChannel",
    "SlackWebhookChannel",
    # Notification Service
    "NotificationService",
    "NotificationPriority",
    "Notification",
    "NotificationResult",
    "notification_service",
]
