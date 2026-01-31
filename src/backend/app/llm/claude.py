"""
Claude (Anthropic) Provider
"""
import json
from typing import List, Dict, Any, Optional, AsyncIterator
import anthropic
from .base import BaseLLMProvider, LLMResponse, ToolCall


class ClaudeProvider(BaseLLMProvider):
    """Claude API Provider"""

    name = "claude"

    def __init__(self, api_key: str, model: str = "claude-sonnet-4-20250514"):
        self.client = anthropic.AsyncAnthropic(api_key=api_key)
        self.model = model

    async def chat(
        self,
        messages: List[Dict[str, Any]],
        system: Optional[str] = None,
        tools: Optional[List[Dict]] = None,
        **kwargs
    ) -> LLMResponse:
        """发送聊天请求"""
        params = {
            "model": kwargs.get("model", self.model),
            "max_tokens": kwargs.get("max_tokens", 4096),
            "messages": self._convert_messages(messages),
        }

        if system:
            params["system"] = system

        if tools:
            params["tools"] = self._convert_tools(tools)

        response = await self.client.messages.create(**params)

        return self._parse_response(response)

    async def chat_stream(
        self,
        messages: List[Dict[str, Any]],
        system: Optional[str] = None,
        tools: Optional[List[Dict]] = None,
        **kwargs
    ) -> AsyncIterator[str]:
        """流式聊天"""
        params = {
            "model": kwargs.get("model", self.model),
            "max_tokens": kwargs.get("max_tokens", 4096),
            "messages": self._convert_messages(messages),
        }

        if system:
            params["system"] = system

        if tools:
            params["tools"] = self._convert_tools(tools)

        async with self.client.messages.stream(**params) as stream:
            async for text in stream.text_stream:
                yield text

    def _convert_messages(self, messages: List[Dict]) -> List[Dict]:
        """转换消息格式"""
        converted = []
        for msg in messages:
            if msg["role"] == "system":
                continue  # system 单独处理
            converted.append(msg)
        return converted

    def _convert_tools(self, tools: List[Dict]) -> List[Dict]:
        """转换工具格式为 Claude 格式"""
        return [
            {
                "name": tool["name"],
                "description": tool.get("description", ""),
                "input_schema": tool.get("parameters", tool.get("input_schema", {}))
            }
            for tool in tools
        ]

    def _parse_response(self, response) -> LLMResponse:
        """解析 Claude 响应"""
        content = ""
        tool_calls = []

        for block in response.content:
            if block.type == "text":
                content += block.text
            elif block.type == "tool_use":
                tool_calls.append(ToolCall(
                    id=block.id,
                    name=block.name,
                    arguments=block.input
                ))

        return LLMResponse(
            content=content,
            tool_calls=tool_calls,
            model=response.model,
            usage={
                "input_tokens": response.usage.input_tokens,
                "output_tokens": response.usage.output_tokens
            },
            finish_reason=response.stop_reason or ""
        )
