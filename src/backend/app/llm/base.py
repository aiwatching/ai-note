"""
LLM Provider 基类
"""
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, AsyncIterator
from pydantic import BaseModel


class ToolCall(BaseModel):
    """工具调用"""
    id: str
    name: str
    arguments: Dict[str, Any]


class LLMResponse(BaseModel):
    """LLM 响应"""
    content: str = ""
    tool_calls: List[ToolCall] = []
    model: str = ""
    usage: Dict[str, int] = {}
    finish_reason: str = ""


class BaseLLMProvider(ABC):
    """LLM Provider 基类"""

    name: str = "base"

    @abstractmethod
    async def chat(
        self,
        messages: List[Dict[str, Any]],
        system: Optional[str] = None,
        tools: Optional[List[Dict]] = None,
        **kwargs
    ) -> LLMResponse:
        """发送聊天请求"""
        pass

    @abstractmethod
    async def chat_stream(
        self,
        messages: List[Dict[str, Any]],
        system: Optional[str] = None,
        tools: Optional[List[Dict]] = None,
        **kwargs
    ) -> AsyncIterator[str]:
        """流式聊天"""
        pass
