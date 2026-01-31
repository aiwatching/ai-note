"""
DeepSeek Provider (OpenAI 兼容 API)
"""
import json
from typing import List, Dict, Any, Optional, AsyncIterator
from openai import AsyncOpenAI
from .base import BaseLLMProvider, LLMResponse, ToolCall


class DeepSeekProvider(BaseLLMProvider):
    """DeepSeek API Provider"""

    name = "deepseek"

    def __init__(self, api_key: str, model: str = "deepseek-chat"):
        self.client = AsyncOpenAI(
            api_key=api_key,
            base_url="https://api.deepseek.com/v1"
        )
        self.model = model

    async def chat(
        self,
        messages: List[Dict[str, Any]],
        system: Optional[str] = None,
        tools: Optional[List[Dict]] = None,
        **kwargs
    ) -> LLMResponse:
        """发送聊天请求"""
        formatted_messages = self._format_messages(messages, system)

        params = {
            "model": kwargs.get("model", self.model),
            "messages": formatted_messages,
            "max_tokens": kwargs.get("max_tokens", 4096),
        }

        if tools:
            params["tools"] = self._convert_tools(tools)
            params["tool_choice"] = "auto"

        response = await self.client.chat.completions.create(**params)

        return self._parse_response(response)

    async def chat_stream(
        self,
        messages: List[Dict[str, Any]],
        system: Optional[str] = None,
        tools: Optional[List[Dict]] = None,
        **kwargs
    ) -> AsyncIterator[str]:
        """流式聊天"""
        formatted_messages = self._format_messages(messages, system)

        params = {
            "model": kwargs.get("model", self.model),
            "messages": formatted_messages,
            "max_tokens": kwargs.get("max_tokens", 4096),
            "stream": True,
        }

        if tools:
            params["tools"] = self._convert_tools(tools)

        stream = await self.client.chat.completions.create(**params)

        async for chunk in stream:
            if chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content

    def _format_messages(
        self,
        messages: List[Dict],
        system: Optional[str]
    ) -> List[Dict]:
        """格式化消息"""
        formatted = []

        if system:
            formatted.append({"role": "system", "content": system})

        for msg in messages:
            if msg["role"] == "system":
                formatted.insert(0, msg)
            else:
                formatted.append(msg)

        return formatted

    def _convert_tools(self, tools: List[Dict]) -> List[Dict]:
        """转换工具格式为 OpenAI 格式"""
        return [
            {
                "type": "function",
                "function": {
                    "name": tool["name"],
                    "description": tool.get("description", ""),
                    "parameters": tool.get("parameters", tool.get("input_schema", {}))
                }
            }
            for tool in tools
        ]

    def _parse_response(self, response) -> LLMResponse:
        """解析响应"""
        message = response.choices[0].message
        content = message.content or ""
        tool_calls = []

        if message.tool_calls:
            for tc in message.tool_calls:
                tool_calls.append(ToolCall(
                    id=tc.id,
                    name=tc.function.name,
                    arguments=json.loads(tc.function.arguments)
                ))

        return LLMResponse(
            content=content,
            tool_calls=tool_calls,
            model=response.model,
            usage={
                "input_tokens": response.usage.prompt_tokens,
                "output_tokens": response.usage.completion_tokens
            },
            finish_reason=response.choices[0].finish_reason
        )
