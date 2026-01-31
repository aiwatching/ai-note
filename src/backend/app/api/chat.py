"""
聊天 API
"""
from typing import Optional, List
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import json

from ..core.deps import get_agent


router = APIRouter(prefix="/chat", tags=["chat"])


class ChatRequest(BaseModel):
    """聊天请求"""
    message: str
    conversation_id: Optional[str] = None
    provider: Optional[str] = None
    stream: bool = False


class ChatResponse(BaseModel):
    """聊天响应"""
    content: str
    conversation_id: str
    model_used: str
    tool_calls_made: List[dict] = []


@router.post("", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """发送聊天消息"""
    agent = get_agent()

    if request.stream:
        # 流式响应
        async def generate():
            async for chunk in agent.chat_stream(
                message=request.message,
                conversation_id=request.conversation_id,
                provider=request.provider
            ):
                yield f"data: {json.dumps({'content': chunk})}\n\n"
            yield "data: [DONE]\n\n"

        return StreamingResponse(
            generate(),
            media_type="text/event-stream"
        )

    # 非流式响应
    result = await agent.chat(
        message=request.message,
        conversation_id=request.conversation_id,
        provider=request.provider
    )

    return ChatResponse(
        content=result.content,
        conversation_id=result.conversation_id,
        model_used=result.model_used,
        tool_calls_made=result.tool_calls_made
    )


@router.post("/stream")
async def chat_stream(request: ChatRequest):
    """流式聊天"""
    agent = get_agent()

    async def generate():
        conversation_id = None
        async for chunk in agent.chat_stream(
            message=request.message,
            conversation_id=request.conversation_id,
            provider=request.provider
        ):
            yield f"data: {json.dumps({'type': 'content', 'content': chunk})}\n\n"

        yield f"data: {json.dumps({'type': 'done'})}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream"
    )


class ModelsResponse(BaseModel):
    """可用模型"""
    models: List[str]
    default: str


@router.get("/models", response_model=ModelsResponse)
async def get_models():
    """获取可用的 LLM 模型"""
    agent = get_agent()
    return ModelsResponse(
        models=agent.llm.available_providers,
        default=agent.default_provider
    )
