"""
Generic Webhook Channel Implementation

Sends notifications to any HTTP endpoint.
Useful for custom integrations, Slack incoming webhooks, etc.
"""
import httpx
from datetime import datetime
from typing import Dict, Any, Optional

from .base import (
    BaseChannel,
    ChannelType,
    ChannelCapabilities,
    OutboundMessage,
    DeliveryResult,
)


class WebhookChannel(BaseChannel):
    """
    Generic webhook notification channel.

    Configuration:
        url: Webhook URL
        method: HTTP method (default: POST)
        headers: Custom headers (optional)
        template: Payload template (optional)
            - Use {text}, {to}, {timestamp} as placeholders
            - Or provide a callable for custom formatting

    Usage:
        # Simple webhook
        channel = WebhookChannel({
            "url": "https://example.com/webhook",
            "headers": {"Authorization": "Bearer xxx"}
        })

        # Slack-style webhook
        channel = WebhookChannel({
            "url": "https://hooks.slack.com/services/...",
            "template": {"text": "{text}"}
        })

        # Custom template
        channel = WebhookChannel({
            "url": "https://api.example.com/notify",
            "template": {
                "message": "{text}",
                "recipient": "{to}",
                "source": "ai-assistant"
            }
        })
    """

    channel_type = ChannelType.WEBHOOK
    capabilities = ChannelCapabilities(
        direct_message=True,
        group_message=False,
        media=False,
        markdown=False,
        html=False,
        threading=False,
        reactions=False,
        text_chunk_limit=10000,
    )

    def __init__(self, config: Dict[str, Any]):
        self.url: str = ""
        self.method: str = "POST"
        self.headers: Dict[str, str] = {}
        self.template: Optional[Dict[str, Any]] = None
        self.timeout: float = 30.0
        super().__init__(config)

    def _validate_config(self) -> None:
        """Validate webhook configuration"""
        if "url" not in self.config:
            raise ValueError("Webhook requires 'url' in config")

        self.url = self.config["url"]
        self.method = self.config.get("method", "POST").upper()
        self.headers = self.config.get("headers", {})
        self.template = self.config.get("template")
        self.timeout = self.config.get("timeout", 30.0)

        # Add default content-type if not specified
        if "Content-Type" not in self.headers:
            self.headers["Content-Type"] = "application/json"

    def _build_payload(self, message: OutboundMessage) -> Dict[str, Any]:
        """Build webhook payload from message"""
        timestamp = datetime.now().isoformat()

        if self.template:
            # Use template with placeholders
            payload = {}
            for key, value in self.template.items():
                if isinstance(value, str):
                    payload[key] = value.format(
                        text=message.text,
                        to=message.to,
                        timestamp=timestamp,
                        **message.meta
                    )
                else:
                    payload[key] = value
            return payload

        # Default payload structure
        return {
            "text": message.text,
            "to": message.to,
            "timestamp": timestamp,
            "meta": message.meta,
        }

    async def send_text(self, message: OutboundMessage) -> DeliveryResult:
        """Send message via webhook"""
        payload = self._build_payload(message)

        try:
            async with httpx.AsyncClient() as client:
                if self.method == "POST":
                    response = await client.post(
                        self.url,
                        json=payload,
                        headers=self.headers,
                        timeout=self.timeout,
                    )
                elif self.method == "PUT":
                    response = await client.put(
                        self.url,
                        json=payload,
                        headers=self.headers,
                        timeout=self.timeout,
                    )
                else:
                    return DeliveryResult(
                        success=False,
                        channel=self.channel_type,
                        error=f"Unsupported method: {self.method}"
                    )

                success = response.status_code in range(200, 300)

                return DeliveryResult(
                    success=success,
                    channel=self.channel_type,
                    message_id=None,
                    timestamp=datetime.now(),
                    error=None if success else f"HTTP {response.status_code}",
                    meta={
                        "status_code": response.status_code,
                        "response": response.text[:500] if response.text else None,
                    }
                )

        except httpx.TimeoutException:
            return DeliveryResult(
                success=False,
                channel=self.channel_type,
                error="Webhook timeout"
            )
        except Exception as e:
            return DeliveryResult(
                success=False,
                channel=self.channel_type,
                error=str(e)
            )


class SlackWebhookChannel(WebhookChannel):
    """
    Slack Incoming Webhook channel.

    Configuration:
        webhook_url: Slack webhook URL
        username: Bot username (optional)
        icon_emoji: Bot emoji (optional)
        channel: Override channel (optional)

    Usage:
        channel = SlackWebhookChannel({
            "webhook_url": "https://hooks.slack.com/services/T.../B.../xxx",
            "username": "AI Assistant",
            "icon_emoji": ":robot_face:"
        })
    """

    def __init__(self, config: Dict[str, Any]):
        self.username: Optional[str] = None
        self.icon_emoji: Optional[str] = None
        self.channel_override: Optional[str] = None
        super().__init__(config)

    def _validate_config(self) -> None:
        """Validate Slack webhook configuration"""
        if "webhook_url" not in self.config:
            raise ValueError("Slack requires 'webhook_url' in config")

        self.url = self.config["webhook_url"]
        self.method = "POST"
        self.headers = {"Content-Type": "application/json"}
        self.username = self.config.get("username")
        self.icon_emoji = self.config.get("icon_emoji")
        self.channel_override = self.config.get("channel")
        self.timeout = self.config.get("timeout", 30.0)

    def _build_payload(self, message: OutboundMessage) -> Dict[str, Any]:
        """Build Slack webhook payload"""
        payload: Dict[str, Any] = {
            "text": message.text,
        }

        if self.username:
            payload["username"] = self.username
        if self.icon_emoji:
            payload["icon_emoji"] = self.icon_emoji
        if self.channel_override:
            payload["channel"] = self.channel_override

        # Support Slack blocks for rich formatting
        if "blocks" in message.meta:
            payload["blocks"] = message.meta["blocks"]

        # Support attachments
        if "attachments" in message.meta:
            payload["attachments"] = message.meta["attachments"]

        return payload
