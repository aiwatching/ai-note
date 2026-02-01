"""
Discord Channel Implementation

Sends notifications via Discord Webhook or Bot API.
"""
import httpx
from datetime import datetime
from typing import Dict, Any, Optional, List

from .base import (
    BaseChannel,
    ChannelType,
    ChannelCapabilities,
    OutboundMessage,
    DeliveryResult,
)


class DiscordChannel(BaseChannel):
    """
    Discord notification channel.

    Supports two modes:
    1. Webhook mode (simpler, no bot needed)
    2. Bot mode (more features, requires bot token)

    Configuration (webhook mode):
        webhook_url: Discord webhook URL

    Configuration (bot mode):
        bot_token: Discord bot token
        default_channel_id: Default channel ID

    Usage:
        # Webhook mode
        channel = DiscordChannel({
            "webhook_url": "https://discord.com/api/webhooks/..."
        })

        # Bot mode
        channel = DiscordChannel({
            "bot_token": "MTIz...",
            "default_channel_id": "123456789"
        })
    """

    channel_type = ChannelType.DISCORD
    capabilities = ChannelCapabilities(
        direct_message=True,
        group_message=True,
        media=True,
        markdown=True,
        html=False,
        threading=True,
        reactions=True,
        text_chunk_limit=2000,  # Discord limit
    )

    BOT_API_URL = "https://discord.com/api/v10"

    def __init__(self, config: Dict[str, Any]):
        self.webhook_url: Optional[str] = None
        self.bot_token: Optional[str] = None
        self.default_channel_id: Optional[str] = None
        self.username: str = "AI Assistant"
        self.avatar_url: Optional[str] = None
        super().__init__(config)

    def _validate_config(self) -> None:
        """Validate Discord configuration"""
        self.webhook_url = self.config.get("webhook_url")
        self.bot_token = self.config.get("bot_token")
        self.default_channel_id = self.config.get("default_channel_id")
        self.username = self.config.get("username", "AI Assistant")
        self.avatar_url = self.config.get("avatar_url")

        if not self.webhook_url and not self.bot_token:
            raise ValueError(
                "Discord requires either 'webhook_url' or 'bot_token' in config"
            )

        if self.bot_token and not self.default_channel_id:
            raise ValueError(
                "Bot mode requires 'default_channel_id' in config"
            )

    @property
    def is_webhook_mode(self) -> bool:
        return bool(self.webhook_url)

    def _get_channel_id(self, to: str) -> str:
        """Resolve channel ID from recipient"""
        if to:
            return to
        if self.default_channel_id:
            return self.default_channel_id
        raise ValueError("No recipient and no default_channel_id")

    async def send_text(self, message: OutboundMessage) -> DeliveryResult:
        """Send text message via Discord"""
        if self.is_webhook_mode:
            return await self._send_webhook(message)
        else:
            return await self._send_bot(message)

    async def _send_webhook(self, message: OutboundMessage) -> DeliveryResult:
        """Send via webhook"""
        payload: Dict[str, Any] = {
            "content": message.text,
            "username": self.username,
        }

        if self.avatar_url:
            payload["avatar_url"] = self.avatar_url

        # Embeds for richer content
        if message.meta.get("embed"):
            payload["embeds"] = [message.meta["embed"]]

        # Thread support
        if message.thread_id:
            # Webhook thread requires ?thread_id=xxx in URL
            url = f"{self.webhook_url}?thread_id={message.thread_id}"
        else:
            url = self.webhook_url

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    url,
                    json=payload,
                    timeout=30.0,
                )

                # Discord webhooks return 204 No Content on success
                # or 200 with wait=true
                if response.status_code in (200, 204):
                    data = response.json() if response.text else {}
                    return DeliveryResult(
                        success=True,
                        channel=self.channel_type,
                        message_id=data.get("id"),
                        chat_id=data.get("channel_id"),
                        timestamp=datetime.now(),
                        meta={"webhook": True}
                    )
                else:
                    return DeliveryResult(
                        success=False,
                        channel=self.channel_type,
                        error=f"Discord returned {response.status_code}: {response.text}",
                    )

        except Exception as e:
            return DeliveryResult(
                success=False,
                channel=self.channel_type,
                error=str(e)
            )

    async def _send_bot(self, message: OutboundMessage) -> DeliveryResult:
        """Send via bot API"""
        channel_id = self._get_channel_id(message.to)

        payload: Dict[str, Any] = {
            "content": message.text,
        }

        # Reply reference
        if message.reply_to:
            payload["message_reference"] = {
                "message_id": message.reply_to
            }

        headers = {
            "Authorization": f"Bot {self.bot_token}",
            "Content-Type": "application/json",
        }

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.BOT_API_URL}/channels/{channel_id}/messages",
                    json=payload,
                    headers=headers,
                    timeout=30.0,
                )

                if response.status_code == 200:
                    data = response.json()
                    return DeliveryResult(
                        success=True,
                        channel=self.channel_type,
                        message_id=data["id"],
                        chat_id=data["channel_id"],
                        timestamp=datetime.fromisoformat(
                            data["timestamp"].replace("Z", "+00:00")
                        ),
                        meta={"author": data.get("author", {})}
                    )
                else:
                    return DeliveryResult(
                        success=False,
                        channel=self.channel_type,
                        error=f"Discord API error: {response.status_code}",
                        meta={"response": response.text}
                    )

        except Exception as e:
            return DeliveryResult(
                success=False,
                channel=self.channel_type,
                error=str(e)
            )

    async def send_media(self, message: OutboundMessage) -> DeliveryResult:
        """Send media via Discord (as embed or attachment)"""
        if not message.media_url:
            return await self.send_text(message)

        # For webhooks, use embeds for media
        if self.is_webhook_mode:
            embed_message = OutboundMessage(
                to=message.to,
                text=message.text,
                thread_id=message.thread_id,
                meta={
                    "embed": {
                        "description": message.text,
                        "image": {"url": message.media_url}
                    }
                }
            )
            return await self._send_webhook(embed_message)

        # For bot mode, include URL in content
        text_with_media = message.text
        if message.media_url:
            text_with_media += f"\n{message.media_url}"

        media_message = OutboundMessage(
            to=message.to,
            text=text_with_media,
            reply_to=message.reply_to,
            thread_id=message.thread_id,
        )
        return await self._send_bot(media_message)

    def create_embed(
        self,
        title: Optional[str] = None,
        description: Optional[str] = None,
        color: int = 0x5865F2,  # Discord blurple
        fields: Optional[List[Dict[str, Any]]] = None,
        footer: Optional[str] = None,
        image_url: Optional[str] = None,
        thumbnail_url: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Helper to create Discord embed object"""
        embed: Dict[str, Any] = {"color": color}

        if title:
            embed["title"] = title
        if description:
            embed["description"] = description
        if fields:
            embed["fields"] = fields
        if footer:
            embed["footer"] = {"text": footer}
        if image_url:
            embed["image"] = {"url": image_url}
        if thumbnail_url:
            embed["thumbnail"] = {"url": thumbnail_url}

        return embed
