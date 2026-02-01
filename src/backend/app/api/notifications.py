"""
Notification API Endpoints

REST API for sending notifications via configured channels.
"""
from typing import List, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from ..channels import (
    notification_service,
    Notification,
    NotificationPriority,
    ChannelType,
)

router = APIRouter(prefix="/notifications", tags=["notifications"])


# ==================== Request/Response Models ====================

class SendNotificationRequest(BaseModel):
    """Request to send a notification"""
    title: Optional[str] = None
    message: str = Field(..., min_length=1)
    priority: str = "normal"  # low, normal, high, urgent
    channels: Optional[List[str]] = None  # telegram, discord, slack, webhook
    recipient: Optional[str] = None

    class Config:
        json_schema_extra = {
            "example": {
                "title": "Reminder",
                "message": "Don't forget the meeting at 3pm!",
                "priority": "high",
                "channels": ["telegram"],
            }
        }


class ChannelStatus(BaseModel):
    """Channel configuration status"""
    type: str
    configured: bool
    default_recipient: Optional[str] = None


class NotificationResponse(BaseModel):
    """Notification result"""
    success: bool
    message: str
    channels: dict = {}
    errors: List[str] = []


class TestMessageRequest(BaseModel):
    """Request to send a test message"""
    channel: str  # telegram, discord, slack, webhook
    recipient: Optional[str] = None


# ==================== Endpoints ====================

@router.get("/channels", response_model=List[ChannelStatus])
async def list_channels():
    """
    List all notification channels and their configuration status.

    Returns which channels are configured and ready to use.
    """
    return notification_service.list_channels()


@router.post("/send", response_model=NotificationResponse)
async def send_notification(request: SendNotificationRequest):
    """
    Send a notification via configured channels.

    Priority levels:
    - low: Informational, non-urgent
    - normal: Standard notifications
    - high: Important, needs attention
    - urgent: Critical, immediate attention required

    If no channels specified, sends to all configured channels.
    """
    # Parse priority
    try:
        priority = NotificationPriority(request.priority.lower())
    except ValueError:
        priority = NotificationPriority.NORMAL

    # Parse channels
    channels = None
    if request.channels:
        channels = []
        for ch in request.channels:
            try:
                channels.append(ChannelType(ch.lower()))
            except ValueError:
                pass

    notification = Notification(
        title=request.title,
        message=request.message,
        priority=priority,
        channels=channels if channels else None,
        recipient=request.recipient,
    )

    result = await notification_service.notify(notification)

    return NotificationResponse(
        success=result.success,
        message="Notification sent" if result.success else "Some channels failed",
        channels={
            ch.value: {
                "success": r.success,
                "message_id": r.message_id,
                "error": r.error,
            }
            for ch, r in result.results.items()
        },
        errors=result.errors,
    )


@router.post("/reminder", response_model=NotificationResponse)
async def send_reminder(
    message: str,
    title: str = "Reminder",
    channels: Optional[List[str]] = None
):
    """Send a reminder notification."""
    channel_types = None
    if channels:
        channel_types = [ChannelType(ch) for ch in channels if ch in ChannelType.__members__]

    result = await notification_service.send_reminder(
        message=message,
        title=title,
        channels=channel_types,
    )

    return NotificationResponse(
        success=result.success,
        message="Reminder sent" if result.success else "Failed to send reminder",
        channels={ch.value: {"success": r.success} for ch, r in result.results.items()},
        errors=result.errors,
    )


@router.post("/alert", response_model=NotificationResponse)
async def send_alert(
    message: str,
    title: str = "Alert",
    channels: Optional[List[str]] = None
):
    """Send a high-priority alert notification."""
    channel_types = None
    if channels:
        channel_types = [ChannelType(ch) for ch in channels if ch in ChannelType.__members__]

    result = await notification_service.send_alert(
        message=message,
        title=title,
        channels=channel_types,
    )

    return NotificationResponse(
        success=result.success,
        message="Alert sent" if result.success else "Failed to send alert",
        channels={ch.value: {"success": r.success} for ch, r in result.results.items()},
        errors=result.errors,
    )


@router.post("/test", response_model=NotificationResponse)
async def test_channel(request: TestMessageRequest):
    """
    Send a test message to verify channel configuration.

    Useful for testing that a channel is properly configured.
    """
    try:
        channel_type = ChannelType(request.channel.lower())
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid channel: {request.channel}. Valid: telegram, discord, slack, webhook"
        )

    channel = notification_service.registry.get(channel_type)
    if not channel:
        raise HTTPException(
            status_code=400,
            detail=f"Channel {request.channel} is not configured"
        )

    result = await notification_service.notify(Notification(
        title="Test Notification",
        message=f"✅ This is a test message from AI Assistant.\n\nTimestamp: {__import__('datetime').datetime.now().isoformat()}",
        priority=NotificationPriority.NORMAL,
        channels=[channel_type],
        recipient=request.recipient,
    ))

    return NotificationResponse(
        success=result.success,
        message="Test message sent" if result.success else "Test failed",
        channels={ch.value: {"success": r.success, "error": r.error} for ch, r in result.results.items()},
        errors=result.errors,
    )


# ==================== Telegram-specific ====================

@router.get("/telegram/info")
async def telegram_bot_info():
    """Get Telegram bot information (if configured)."""
    channel = notification_service.registry.get(ChannelType.TELEGRAM)
    if not channel:
        raise HTTPException(status_code=400, detail="Telegram not configured")

    from ..channels.telegram import TelegramChannel
    if isinstance(channel, TelegramChannel):
        result = await channel.get_me()
        return result
    raise HTTPException(status_code=500, detail="Invalid channel type")


@router.get("/telegram/updates")
async def telegram_updates(offset: int = 0):
    """
    Get recent Telegram updates (for finding chat IDs).

    Send a message to your bot, then call this endpoint to see
    the chat ID you need to configure.
    """
    channel = notification_service.registry.get(ChannelType.TELEGRAM)
    if not channel:
        raise HTTPException(status_code=400, detail="Telegram not configured")

    from ..channels.telegram import TelegramChannel
    if isinstance(channel, TelegramChannel):
        result = await channel.get_updates(offset)
        return result
    raise HTTPException(status_code=500, detail="Invalid channel type")
