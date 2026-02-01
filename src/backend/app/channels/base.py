"""
Channel Abstraction Layer

Provides a unified interface for sending notifications across different platforms.
Inspired by OpenClaw's channel plugin architecture.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List
from enum import Enum
from datetime import datetime


class ChannelType(str, Enum):
    """Supported channel types"""
    TELEGRAM = "telegram"
    DISCORD = "discord"
    SLACK = "slack"
    EMAIL = "email"
    WEBHOOK = "webhook"


@dataclass
class ChannelCapabilities:
    """What a channel supports"""
    direct_message: bool = True
    group_message: bool = False
    media: bool = False
    markdown: bool = False
    html: bool = False
    threading: bool = False
    reactions: bool = False
    text_chunk_limit: int = 4096


@dataclass
class DeliveryResult:
    """Standardized delivery result"""
    success: bool
    channel: ChannelType
    message_id: Optional[str] = None
    chat_id: Optional[str] = None
    timestamp: Optional[datetime] = None
    error: Optional[str] = None
    meta: Dict[str, Any] = field(default_factory=dict)


@dataclass
class OutboundMessage:
    """Message to send"""
    to: str                                     # Recipient identifier
    text: str                                   # Message text
    media_url: Optional[str] = None             # Optional media attachment
    reply_to: Optional[str] = None              # Message ID to reply to
    thread_id: Optional[str] = None             # Thread ID
    parse_mode: Optional[str] = None            # "markdown" or "html"
    meta: Dict[str, Any] = field(default_factory=dict)


class BaseChannel(ABC):
    """
    Abstract base class for notification channels.

    Each channel implementation must provide:
    - send_text(): Send a text message
    - send_media(): Send media (optional)
    - validate_config(): Validate channel configuration
    """

    channel_type: ChannelType
    capabilities: ChannelCapabilities

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self._validate_config()

    @abstractmethod
    def _validate_config(self) -> None:
        """Validate channel-specific configuration"""
        pass

    @abstractmethod
    async def send_text(self, message: OutboundMessage) -> DeliveryResult:
        """Send a text message"""
        pass

    async def send_media(self, message: OutboundMessage) -> DeliveryResult:
        """Send media message (default: not supported)"""
        return DeliveryResult(
            success=False,
            channel=self.channel_type,
            error="Media not supported by this channel"
        )

    async def send(self, message: OutboundMessage) -> DeliveryResult:
        """
        Send a message, automatically choosing text or media.
        Handles text chunking if needed.
        """
        if message.media_url and self.capabilities.media:
            return await self.send_media(message)

        # Chunk text if needed
        text = message.text
        limit = self.capabilities.text_chunk_limit

        if len(text) <= limit:
            return await self.send_text(message)

        # Send in chunks
        chunks = self._chunk_text(text, limit)
        last_result = None

        for i, chunk in enumerate(chunks):
            chunk_message = OutboundMessage(
                to=message.to,
                text=chunk,
                reply_to=last_result.message_id if last_result else message.reply_to,
                thread_id=message.thread_id,
                parse_mode=message.parse_mode,
                meta={**message.meta, "chunk": i + 1, "total_chunks": len(chunks)}
            )
            last_result = await self.send_text(chunk_message)
            if not last_result.success:
                return last_result

        return last_result

    def _chunk_text(self, text: str, limit: int) -> List[str]:
        """Split text into chunks respecting word boundaries"""
        chunks = []
        current = ""

        for line in text.split('\n'):
            if len(current) + len(line) + 1 <= limit:
                current += ('\n' if current else '') + line
            else:
                if current:
                    chunks.append(current)
                # Handle lines longer than limit
                while len(line) > limit:
                    chunks.append(line[:limit])
                    line = line[limit:]
                current = line

        if current:
            chunks.append(current)

        return chunks

    @property
    def is_configured(self) -> bool:
        """Check if channel is properly configured"""
        try:
            self._validate_config()
            return True
        except Exception:
            return False


class ChannelRegistry:
    """Registry of available channels"""

    def __init__(self):
        self._channels: Dict[ChannelType, BaseChannel] = {}
        self._factories: Dict[ChannelType, type] = {}

    def register_factory(self, channel_type: ChannelType, factory: type):
        """Register a channel class"""
        self._factories[channel_type] = factory

    def configure(self, channel_type: ChannelType, config: Dict[str, Any]) -> bool:
        """Configure and instantiate a channel"""
        if channel_type not in self._factories:
            return False

        try:
            channel = self._factories[channel_type](config)
            self._channels[channel_type] = channel
            return True
        except Exception as e:
            print(f"[Channels] Failed to configure {channel_type}: {e}")
            return False

    def get(self, channel_type: ChannelType) -> Optional[BaseChannel]:
        """Get a configured channel"""
        return self._channels.get(channel_type)

    def list_available(self) -> List[ChannelType]:
        """List configured channels"""
        return list(self._channels.keys())

    async def send(
        self,
        channel_type: ChannelType,
        message: OutboundMessage
    ) -> DeliveryResult:
        """Send via a specific channel"""
        channel = self.get(channel_type)
        if not channel:
            return DeliveryResult(
                success=False,
                channel=channel_type,
                error=f"Channel {channel_type} not configured"
            )
        return await channel.send(message)

    async def broadcast(
        self,
        message: OutboundMessage,
        channels: Optional[List[ChannelType]] = None
    ) -> Dict[ChannelType, DeliveryResult]:
        """Send to multiple channels"""
        targets = channels or self.list_available()
        results = {}

        for channel_type in targets:
            results[channel_type] = await self.send(channel_type, message)

        return results


# Global registry
registry = ChannelRegistry()
