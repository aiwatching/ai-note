"""
对话管理 API
"""
from typing import List, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from datetime import datetime

from ..core.deps import get_memory


router = APIRouter(prefix="/conversations", tags=["conversations"])


class MessageResponse(BaseModel):
    """消息响应"""
    id: str
    role: str
    content: str
    timestamp: datetime


class ConversationSummary(BaseModel):
    """对话摘要"""
    id: str
    title: Optional[str]
    created_at: datetime
    updated_at: datetime


class ConversationDetail(BaseModel):
    """对话详情"""
    id: str
    title: Optional[str]
    messages: List[MessageResponse]
    created_at: datetime
    updated_at: datetime


@router.get("", response_model=List[ConversationSummary])
async def list_conversations(limit: int = 20):
    """获取对话列表"""
    memory = get_memory()
    if not memory:
        return []

    conversations = memory.list_conversations(limit)
    return [
        ConversationSummary(
            id=conv.id,
            title=conv.title,
            created_at=conv.created_at,
            updated_at=conv.updated_at
        )
        for conv in conversations
    ]


@router.get("/{conversation_id}", response_model=ConversationDetail)
async def get_conversation(conversation_id: str):
    """获取对话详情"""
    memory = get_memory()
    if not memory:
        raise HTTPException(status_code=404, detail="Memory not configured")

    conversation = memory.get_conversation(conversation_id)
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    return ConversationDetail(
        id=conversation.id,
        title=conversation.title,
        messages=[
            MessageResponse(
                id=msg.id,
                role=msg.role,
                content=msg.content,
                timestamp=msg.timestamp
            )
            for msg in conversation.messages
        ],
        created_at=conversation.created_at,
        updated_at=conversation.updated_at
    )


@router.delete("/{conversation_id}")
async def delete_conversation(conversation_id: str):
    """删除对话"""
    memory = get_memory()
    if not memory:
        raise HTTPException(status_code=404, detail="Memory not configured")

    memory.delete_conversation(conversation_id)
    return {"status": "ok"}


class UpdateConversationRequest(BaseModel):
    """更新对话请求"""
    title: Optional[str] = None


@router.patch("/{conversation_id}")
async def update_conversation(conversation_id: str, request: UpdateConversationRequest):
    """更新对话（如标题）"""
    memory = get_memory()
    if not memory:
        raise HTTPException(status_code=404, detail="Memory not configured")

    conversation = memory.get_conversation(conversation_id)
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    if request.title is not None:
        conversation.title = request.title

    memory.save_conversation(conversation)
    return {"status": "ok"}
