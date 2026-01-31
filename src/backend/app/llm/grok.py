"""
Grok Provider (xAI API - OpenAI 兼容)
"""
import json
from typing import List, Dict, Any, Optional, AsyncIterator
from openai import AsyncOpenAI
from .base import BaseLLMProvider, LLMResponse, ToolCall


class GrokProvider(BaseLLMProvider):
    """Grok (xAI) API Provider"""

    name = "grok"

    # 模型价格 (每 1M tokens, 输入/输出)
    MODEL_PRICING = {
        "grok-2": {"input": 2, "output": 10},
        "grok-2-mini": {"input": 0.3, "output": 0.5},
    }

    def __init__(self, api_key: str, model: str = "grok-2-mini"):
        self.client = AsyncOpenAI(
            api_key=api_key,
            base_url="https://api.x.ai/v1"
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
        """转换工具格式"""
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
                "input_tokens": response.usage.prompt_tokens if response.usage else 0,
                "output_tokens": response.usage.completion_tokens if response.usage else 0
            },
            finish_reason=response.choices[0].finish_reason or ""
        )

    def estimate_cost(self, input_tokens: int, output_tokens: int, model: str = None) -> float:
        """估算费用 (美元)"""
        model = model or self.model
        pricing = self.MODEL_PRICING.get(model, {"input": 0, "output": 0})
        return (input_tokens * pricing["input"] + output_tokens * pricing["output"]) / 1_000_000
