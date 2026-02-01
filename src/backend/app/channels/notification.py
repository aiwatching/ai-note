"""
Notification Service

High-level API for sending notifications across channels.
Supports scheduling, templates, and priority-based delivery.
"""
import os
from datetime import datetime
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from enum import Enum

from .base import (
    ChannelType,
    ChannelRegistry,
    OutboundMessage,
    DeliveryResult,
    registry,
)
from .telegram import TelegramChannel
from .discord import DiscordChannel
from .webhook import WebhookChannel, SlackWebhookChannel


class NotificationPriority(str, Enum):
    """Notification priority levels"""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


@dataclass
class Notification:
    """A notification to send"""
    title: Optional[str] = None
    message: str = ""
    priority: NotificationPriority = NotificationPriority.NORMAL
    channels: Optional[List[ChannelType]] = None  # None = all configured
    recipient: Optional[str] = None               # Override default recipient
    data: Dict[str, Any] = field(default_factory=dict)


@dataclass
class NotificationResult:
    """Result of sending a notification"""
    success: bool
    results: Dict[ChannelType, DeliveryResult]
    errors: List[str] = field(default_factory=list)

    @property
    def any_success(self) -> bool:
        return any(r.success for r in self.results.values())


class NotificationService:
    """
    Unified notification service.

    Manages channel configuration and provides high-level API
    for sending notifications.

    Usage:
        # Initialize
        service = NotificationService()

        # Configure from environment
        service.configure_from_env()

        # Or configure manually
        service.configure_telegram(bot_token="...", chat_id="...")

        # Send notification
        result = await service.notify(Notification(
            title="Reminder",
            message="Meeting in 10 minutes!",
            priority=NotificationPriority.HIGH
        ))
    """

    def __init__(self, channel_registry: Optional[ChannelRegistry] = None):
        self.registry = channel_registry or registry
        self._default_recipients: Dict[ChannelType, str] = {}
        self._templates: Dict[str, str] = {}

    def configure_from_env(self) -> List[ChannelType]:
        """
        Configure channels from environment variables.

        Supported environment variables:
            TELEGRAM_BOT_TOKEN - Telegram bot token
            TELEGRAM_CHAT_ID - Default Telegram chat ID
            DISCORD_WEBHOOK_URL - Discord webhook URL
            DISCORD_BOT_TOKEN - Discord bot token
            DISCORD_CHANNEL_ID - Default Discord channel ID
            SLACK_WEBHOOK_URL - Slack webhook URL
            NOTIFICATION_WEBHOOK_URL - Generic webhook URL

        Returns:
            List of successfully configured channel types
        """
        configured = []

        # Telegram
        telegram_token = os.environ.get("TELEGRAM_BOT_TOKEN")
        telegram_chat = os.environ.get("TELEGRAM_CHAT_ID")
        if telegram_token:
            if self.configure_telegram(telegram_token, telegram_chat):
                configured.append(ChannelType.TELEGRAM)

        # Discord (webhook mode)
        discord_webhook = os.environ.get("DISCORD_WEBHOOK_URL")
        if discord_webhook:
            if self.configure_discord_webhook(discord_webhook):
                configured.append(ChannelType.DISCORD)
        else:
            # Discord (bot mode)
            discord_token = os.environ.get("DISCORD_BOT_TOKEN")
            discord_channel = os.environ.get("DISCORD_CHANNEL_ID")
            if discord_token and discord_channel:
                if self.configure_discord_bot(discord_token, discord_channel):
                    configured.append(ChannelType.DISCORD)

        # Slack
        slack_webhook = os.environ.get("SLACK_WEBHOOK_URL")
        if slack_webhook:
            if self.configure_slack(slack_webhook):
                configured.append(ChannelType.SLACK)

        # Generic webhook
        webhook_url = os.environ.get("NOTIFICATION_WEBHOOK_URL")
        if webhook_url:
            if self.configure_webhook(webhook_url):
                configured.append(ChannelType.WEBHOOK)

        print(f"[Notifications] Configured channels: {[c.value for c in configured]}")
        return configured

    def configure_telegram(
        self,
        bot_token: str,
        default_chat_id: Optional[str] = None
    ) -> bool:
        """Configure Telegram channel"""
        config = {"bot_token": bot_token}
        if default_chat_id:
            config["default_chat_id"] = default_chat_id
            self._default_recipients[ChannelType.TELEGRAM] = default_chat_id

        self.registry.register_factory(ChannelType.TELEGRAM, TelegramChannel)
        return self.registry.configure(ChannelType.TELEGRAM, config)

    def configure_discord_webhook(
        self,
        webhook_url: str,
        username: str = "AI Assistant"
    ) -> bool:
        """Configure Discord webhook"""
        config = {
            "webhook_url": webhook_url,
            "username": username,
        }
        self.registry.register_factory(ChannelType.DISCORD, DiscordChannel)
        return self.registry.configure(ChannelType.DISCORD, config)

    def configure_discord_bot(
        self,
        bot_token: str,
        default_channel_id: str
    ) -> bool:
        """Configure Discord bot"""
        config = {
            "bot_token": bot_token,
            "default_channel_id": default_channel_id,
        }
        self._default_recipients[ChannelType.DISCORD] = default_channel_id
        self.registry.register_factory(ChannelType.DISCORD, DiscordChannel)
        return self.registry.configure(ChannelType.DISCORD, config)

    def configure_slack(
        self,
        webhook_url: str,
        username: str = "AI Assistant",
        icon_emoji: str = ":robot_face:"
    ) -> bool:
        """Configure Slack webhook"""
        config = {
            "webhook_url": webhook_url,
            "username": username,
            "icon_emoji": icon_emoji,
        }
        self.registry.register_factory(ChannelType.SLACK, SlackWebhookChannel)
        return self.registry.configure(ChannelType.SLACK, config)

    def configure_webhook(
        self,
        url: str,
        headers: Optional[Dict[str, str]] = None,
        template: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Configure generic webhook"""
        config = {
            "url": url,
            "headers": headers or {},
        }
        if template:
            config["template"] = template
        self.registry.register_factory(ChannelType.WEBHOOK, WebhookChannel)
        return self.registry.configure(ChannelType.WEBHOOK, config)

    def _format_message(self, notification: Notification) -> str:
        """Format notification into message text"""
        parts = []

        # Priority emoji
        priority_emoji = {
            NotificationPriority.LOW: "📝",
            NotificationPriority.NORMAL: "📬",
            NotificationPriority.HIGH: "⚠️",
            NotificationPriority.URGENT: "🚨",
        }
        emoji = priority_emoji.get(notification.priority, "")

        if notification.title:
            parts.append(f"{emoji} **{notification.title}**")
        elif emoji:
            parts.append(emoji)

        parts.append(notification.message)

        return "\n\n".join(parts)

    async def notify(self, notification: Notification) -> NotificationResult:
        """
        Send a notification to configured channels.

        Args:
            notification: The notification to send

        Returns:
            NotificationResult with delivery status for each channel
        """
        message_text = self._format_message(notification)

        # Determine target channels
        if notification.channels:
            target_channels = notification.channels
        else:
            target_channels = self.registry.list_available()

        if not target_channels:
            return NotificationResult(
                success=False,
                results={},
                errors=["No channels configured"]
            )

        results: Dict[ChannelType, DeliveryResult] = {}
        errors: List[str] = []

        for channel_type in target_channels:
            # Determine recipient
            recipient = notification.recipient or self._default_recipients.get(
                channel_type, ""
            )

            message = OutboundMessage(
                to=recipient,
                text=message_text,
                parse_mode="markdown",
                meta=notification.data,
            )

            try:
                result = await self.registry.send(channel_type, message)
                results[channel_type] = result
                if not result.success:
                    errors.append(f"{channel_type.value}: {result.error}")
            except Exception as e:
                errors.append(f"{channel_type.value}: {str(e)}")
                results[channel_type] = DeliveryResult(
                    success=False,
                    channel=channel_type,
                    error=str(e)
                )

        return NotificationResult(
            success=all(r.success for r in results.values()),
            results=results,
            errors=errors,
        )

    async def send_reminder(
        self,
        message: str,
        title: str = "Reminder",
        channels: Optional[List[ChannelType]] = None
    ) -> NotificationResult:
        """Convenience method to send a reminder"""
        return await self.notify(Notification(
            title=title,
            message=message,
            priority=NotificationPriority.NORMAL,
            channels=channels,
        ))

    async def send_alert(
        self,
        message: str,
        title: str = "Alert",
        channels: Optional[List[ChannelType]] = None
    ) -> NotificationResult:
        """Convenience method to send an alert"""
        return await self.notify(Notification(
            title=title,
            message=message,
            priority=NotificationPriority.HIGH,
            channels=channels,
        ))

    async def send_urgent(
        self,
        message: str,
        title: str = "URGENT",
        channels: Optional[List[ChannelType]] = None
    ) -> NotificationResult:
        """Convenience method to send urgent notification"""
        return await self.notify(Notification(
            title=title,
            message=message,
            priority=NotificationPriority.URGENT,
            channels=channels,
        ))

    def list_channels(self) -> List[Dict[str, Any]]:
        """List configured channels with their status"""
        channels = []
        for channel_type in ChannelType:
            channel = self.registry.get(channel_type)
            channels.append({
                "type": channel_type.value,
                "configured": channel is not None,
                "default_recipient": self._default_recipients.get(channel_type),
            })
        return channels


# Global notification service instance
notification_service = NotificationService()
