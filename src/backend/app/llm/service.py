"""
LLM 统一服务
"""
import asyncio
from typing import List, Dict, Any, Optional, AsyncIterator
from .base import BaseLLMProvider, LLMResponse
from .claude import ClaudeProvider
from .deepseek import DeepSeekProvider
from .openai import OpenAIProvider
from .grok import GrokProvider


# 模型费用排序 (从便宜到贵)
MODEL_COST_RANKING = {
    "deepseek": 1,      # 最便宜
    "grok": 2,          # grok-2-mini 便宜
    "openai": 3,        # gpt-4o-mini 中等
    "claude": 4,        # 最贵但最强
}


class LLMService:
    """统一的 LLM 服务"""

    def __init__(self):
        self.providers: Dict[str, BaseLLMProvider] = {}
        self.default_provider: str = "claude"

    def register_provider(self, name: str, provider: BaseLLMProvider):
        """注册 Provider"""
        self.providers[name] = provider

    def set_default(self, name: str):
        """设置默认 Provider"""
        if name in self.providers:
            self.default_provider = name

    def get_provider(self, name: Optional[str] = None) -> BaseLLMProvider:
        """获取 Provider"""
        name = name or self.default_provider
        if name not in self.providers:
            raise ValueError(f"Provider '{name}' not found. Available: {list(self.providers.keys())}")
        return self.providers[name]

    async def chat(
        self,
        messages: List[Dict[str, Any]],
        system: Optional[str] = None,
        tools: Optional[List[Dict]] = None,
        provider: Optional[str] = None,
        **kwargs
    ) -> LLMResponse:
        """发送聊天请求"""
        p = self.get_provider(provider)
        return await p.chat(messages, system, tools, **kwargs)

    async def chat_stream(
        self,
        messages: List[Dict[str, Any]],
        system: Optional[str] = None,
        tools: Optional[List[Dict]] = None,
        provider: Optional[str] = None,
        **kwargs
    ) -> AsyncIterator[str]:
        """流式聊天"""
        p = self.get_provider(provider)
        async for chunk in p.chat_stream(messages, system, tools, **kwargs):
            yield chunk

    async def multi_chat(
        self,
        messages: List[Dict[str, Any]],
        system: Optional[str] = None,
        providers: Optional[List[str]] = None,
        **kwargs
    ) -> Dict[str, LLMResponse]:
        """同时向多个模型发送请求"""
        providers = providers or list(self.providers.keys())

        tasks = {
            name: self.chat(messages, system, provider=name, **kwargs)
            for name in providers
            if name in self.providers
        }

        results = await asyncio.gather(*tasks.values(), return_exceptions=True)

        return {
            name: result if not isinstance(result, Exception) else LLMResponse(content=f"Error: {result}")
            for name, result in zip(tasks.keys(), results)
        }

    @property
    def available_providers(self) -> List[str]:
        """获取可用的 Providers"""
        return list(self.providers.keys())

    def get_cheapest_provider(self) -> Optional[str]:
        """获取最便宜的可用 Provider"""
        available = self.available_providers
        if not available:
            return None

        sorted_providers = sorted(
            available,
            key=lambda x: MODEL_COST_RANKING.get(x, 99)
        )
        return sorted_providers[0]

    def get_provider_by_task(self, task_type: str) -> str:
        """
        根据任务类型选择合适的模型

        Args:
            task_type: 任务类型
                - "simple": 简单任务 -> 最便宜
                - "code": 代码相关 -> deepseek (代码能力强)
                - "complex": 复杂推理 -> claude
                - "chat": 日常对话 -> 便宜模型

        Returns:
            Provider 名称
        """
        task_provider_map = {
            "simple": self.get_cheapest_provider(),
            "chat": self.get_cheapest_provider(),
            "code": "deepseek" if "deepseek" in self.providers else self.get_cheapest_provider(),
            "complex": "claude" if "claude" in self.providers else self.default_provider,
            "reasoning": "claude" if "claude" in self.providers else self.default_provider,
        }

        provider = task_provider_map.get(task_type, self.default_provider)
        return provider if provider in self.providers else self.default_provider


def create_llm_service(
    claude_api_key: Optional[str] = None,
    deepseek_api_key: Optional[str] = None,
    openai_api_key: Optional[str] = None,
    grok_api_key: Optional[str] = None,
    default: str = "claude"
) -> LLMService:
    """创建 LLM 服务实例"""
    service = LLMService()

    if claude_api_key:
        service.register_provider("claude", ClaudeProvider(claude_api_key))

    if deepseek_api_key:
        service.register_provider("deepseek", DeepSeekProvider(deepseek_api_key))

    if openai_api_key:
        service.register_provider("openai", OpenAIProvider(openai_api_key))

    if grok_api_key:
        service.register_provider("grok", GrokProvider(grok_api_key))

    # 设置默认
    if default in service.providers:
        service.set_default(default)
    elif service.providers:
        service.set_default(list(service.providers.keys())[0])

    print(f"[LLM Service] Available providers: {service.available_providers}")
    print(f"[LLM Service] Default: {service.default_provider}")

    return service
