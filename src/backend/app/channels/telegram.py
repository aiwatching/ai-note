"""
Telegram Channel Implementation

Sends notifications via Telegram Bot API.
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


class TelegramChannel(BaseChannel):
    """
    Telegram notification channel.

    Configuration:
        bot_token: Telegram bot token (from @BotFather)
        default_chat_id: Default chat ID to send to (optional)

    Usage:
        channel = TelegramChannel({
            "bot_token": "123456:ABC-DEF...",
            "default_chat_id": "123456789"
        })
        result = await channel.send(OutboundMessage(
            to="123456789",  # or use default
            text="Hello from AI Assistant!"
        ))
    """

    channel_type = ChannelType.TELEGRAM
    capabilities = ChannelCapabilities(
        direct_message=True,
        group_message=True,
        media=True,
        markdown=True,
        html=True,
        threading=True,
        reactions=True,
        text_chunk_limit=4096,
    )

    BASE_URL = "https://api.telegram.org/bot"

    def __init__(self, config: Dict[str, Any]):
        self.bot_token: str = ""
        self.default_chat_id: Optional[str] = None
        super().__init__(config)

    def _validate_config(self) -> None:
        """Validate Telegram configuration"""
        if "bot_token" not in self.config:
            raise ValueError("Telegram requires 'bot_token' in config")

        self.bot_token = self.config["bot_token"]
        self.default_chat_id = self.config.get("default_chat_id")

    def _get_chat_id(self, to: str) -> str:
        """Resolve chat ID from recipient"""
        if to:
            return to
        if self.default_chat_id:
            return self.default_chat_id
        raise ValueError("No recipient specified and no default_chat_id configured")

    async def send_text(self, message: OutboundMessage) -> DeliveryResult:
        """Send text message via Telegram"""
        chat_id = self._get_chat_id(message.to)

        # Build request payload
        payload: Dict[str, Any] = {
            "chat_id": chat_id,
            "text": message.text,
        }

        # Set parse mode
        if message.parse_mode == "markdown":
            payload["parse_mode"] = "MarkdownV2"
        elif message.parse_mode == "html":
            payload["parse_mode"] = "HTML"

        # Threading support
        if message.reply_to:
            payload["reply_to_message_id"] = int(message.reply_to)
        if message.thread_id:
            payload["message_thread_id"] = int(message.thread_id)

        # Disable link preview for cleaner messages (optional)
        payload["disable_web_page_preview"] = message.meta.get(
            "disable_preview", False
        )

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.BASE_URL}{self.bot_token}/sendMessage",
                    json=payload,
                    timeout=30.0,
                )
                data = response.json()

                if data.get("ok"):
                    result = data["result"]
                    return DeliveryResult(
                        success=True,
                        channel=self.channel_type,
                        message_id=str(result["message_id"]),
                        chat_id=str(result["chat"]["id"]),
                        timestamp=datetime.fromtimestamp(result["date"]),
                        meta={
                            "from": result.get("from", {}),
                            "chat_type": result["chat"].get("type"),
                        }
                    )
                else:
                    return DeliveryResult(
                        success=False,
                        channel=self.channel_type,
                        error=data.get("description", "Unknown Telegram error"),
                        meta={"error_code": data.get("error_code")}
                    )

        except httpx.TimeoutException:
            return DeliveryResult(
                success=False,
                channel=self.channel_type,
                error="Telegram API timeout"
            )
        except Exception as e:
            return DeliveryResult(
                success=False,
                channel=self.channel_type,
                error=str(e)
            )

    async def send_media(self, message: OutboundMessage) -> DeliveryResult:
        """Send media (photo/document) via Telegram"""
        if not message.media_url:
            return await self.send_text(message)

        chat_id = self._get_chat_id(message.to)

        # Detect media type from URL
        url = message.media_url.lower()
        if any(ext in url for ext in ['.jpg', '.jpeg', '.png', '.gif', '.webp']):
            method = "sendPhoto"
            media_key = "photo"
        elif any(ext in url for ext in ['.mp4', '.mov', '.avi']):
            method = "sendVideo"
            media_key = "video"
        elif any(ext in url for ext in ['.mp3', '.ogg', '.wav']):
            method = "sendAudio"
            media_key = "audio"
        else:
            method = "sendDocument"
            media_key = "document"

        payload: Dict[str, Any] = {
            "chat_id": chat_id,
            media_key: message.media_url,
        }

        # Add caption
        if message.text:
            payload["caption"] = message.text[:1024]  # Telegram caption limit

        if message.reply_to:
            payload["reply_to_message_id"] = int(message.reply_to)
        if message.thread_id:
            payload["message_thread_id"] = int(message.thread_id)

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.BASE_URL}{self.bot_token}/{method}",
                    json=payload,
                    timeout=60.0,
                )
                data = response.json()

                if data.get("ok"):
                    result = data["result"]
                    return DeliveryResult(
                        success=True,
                        channel=self.channel_type,
                        message_id=str(result["message_id"]),
                        chat_id=str(result["chat"]["id"]),
                        timestamp=datetime.fromtimestamp(result["date"]),
                        meta={"media_type": media_key}
                    )
                else:
                    return DeliveryResult(
                        success=False,
                        channel=self.channel_type,
                        error=data.get("description", "Unknown Telegram error"),
                    )

        except Exception as e:
            return DeliveryResult(
                success=False,
                channel=self.channel_type,
                error=str(e)
            )

    async def get_me(self) -> Dict[str, Any]:
        """Get bot info (useful for testing connection)"""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.BASE_URL}{self.bot_token}/getMe",
                timeout=10.0,
            )
            return response.json()

    async def get_updates(self, offset: int = 0) -> Dict[str, Any]:
        """Get recent updates (for debugging)"""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.BASE_URL}{self.bot_token}/getUpdates",
                params={"offset": offset, "limit": 10},
                timeout=30.0,
            )
            return response.json()
