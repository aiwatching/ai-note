"""
Agent 核心实现
"""
import json
from typing import List, Dict, Any, Optional, AsyncIterator, Callable, TYPE_CHECKING
from pydantic import BaseModel, Field
from enum import Enum

from ..llm import LLMService, LLMResponse
from ..tools import ToolRegistry
from ..memory import Memory, Conversation, Message


class AgentResult(BaseModel):
    """Agent 执行结果"""
    content: str
    tool_calls_made: List[Dict] = []
    agents_called: List[str] = []  # 调用了哪些子 Agent
    conversation_id: str = ""
    model_used: str = ""


class Skill(BaseModel):
    """
    Agent 技能声明

    Skill 描述了 Agent 擅长什么，用于：
    1. 主 Agent 决定是否调用子 Agent
    2. 对外声明 Agent 的能力（A2A 场景）
    """
    name: str                           # 技能名称
    description: str                    # 技能描述
    examples: List[str] = []            # 示例输入


class AgentCard(BaseModel):
    """
    Agent 名片 (用于 A2A 发现)

    当其他 Agent 想要调用这个 Agent 时，
    通过 AgentCard 了解它的能力
    """
    id: str                             # Agent ID
    name: str                           # Agent 名称
    description: str                    # Agent 描述
    skills: List[Skill] = []            # 技能列表
    version: str = "1.0"
    endpoint: Optional[str] = None      # A2A 远程调用地址（可选）


class Agent:
    """
    Agent 类

    核心功能:
    - 对话管理
    - 工具调用
    - 记忆存储
    - 多模型支持
    - 子 Agent 协作
    """

    def __init__(
        self,
        llm: LLMService,
        agent_id: str = "main",
        name: str = "Assistant",
        description: str = "",
        skills: Optional[List[Skill]] = None,
        tools: Optional[ToolRegistry] = None,
        memory: Optional[Memory] = None,
        system_prompt: str = "",
        default_provider: str = "claude",
        max_tool_iterations: int = 10
    ):
        self.llm = llm
        self.agent_id = agent_id
        self.name = name
        self.description = description
        self.skills = skills or []
        self.tools = tools or ToolRegistry()
        self.memory = memory
        self.system_prompt = system_prompt
        self.default_provider = default_provider
        self.max_tool_iterations = max_tool_iterations

        # 子 Agent 注册表
        self._sub_agents: Dict[str, 'Agent'] = {}

    # ==================== Agent Card ====================

    def get_card(self) -> AgentCard:
        """获取 Agent 名片"""
        return AgentCard(
            id=self.agent_id,
            name=self.name,
            description=self.description,
            skills=self.skills
        )

    # ==================== 子 Agent 管理 ====================

    def register_agent(self, agent: 'Agent'):
        """
        注册子 Agent

        注册后，主 Agent 可以通过 call_agent 工具调用子 Agent
        """
        self._sub_agents[agent.agent_id] = agent
        # 自动注册 call_agent 工具（如果还没注册）
        if "call_agent" not in self.tools.list_tools():
            self._register_call_agent_tool()

    def unregister_agent(self, agent_id: str):
        """注销子 Agent"""
        if agent_id in self._sub_agents:
            del self._sub_agents[agent_id]

    def list_agents(self) -> List[AgentCard]:
        """列出所有子 Agent"""
        return [agent.get_card() for agent in self._sub_agents.values()]

    def _register_call_agent_tool(self):
        """注册调用子 Agent 的工具"""

        async def call_agent(agent_id: str, message: str) -> str:
            """
            调用子 Agent 处理任务

            Args:
                agent_id: 要调用的 Agent ID
                message: 发送给 Agent 的消息
            """
            if agent_id not in self._sub_agents:
                available = list(self._sub_agents.keys())
                return f"Agent '{agent_id}' 不存在。可用的 Agent: {available}"

            sub_agent = self._sub_agents[agent_id]
            result = await sub_agent.chat(message)
            return result.content

        self.tools.register_function(call_agent)

    def _get_agents_prompt(self) -> str:
        """生成子 Agent 描述，加入 system prompt"""
        if not self._sub_agents:
            return ""

        lines = ["\n\n## 可用的专业 Agent\n"]
        lines.append("你可以使用 call_agent 工具调用以下专业 Agent：\n")

        for agent in self._sub_agents.values():
            lines.append(f"### {agent.name} (ID: {agent.agent_id})")
            lines.append(f"{agent.description}")
            if agent.skills:
                lines.append("技能:")
                for skill in agent.skills:
                    lines.append(f"  - {skill.name}: {skill.description}")
            lines.append("")

        return "\n".join(lines)

    # ==================== 核心对话 ====================

    async def chat(
        self,
        message: str,
        conversation_id: Optional[str] = None,
        provider: Optional[str] = None,
        task_type: Optional[str] = None,
        stream: bool = False,
        **kwargs
    ) -> AgentResult:
        """
        主对话方法

        Args:
            message: 用户消息
            conversation_id: 对话 ID（可选，用于继续对话）
            provider: 使用的 LLM provider（直接指定）
            task_type: 任务类型，用于自动选择模型
                - "simple": 简单任务 -> 最便宜
                - "chat": 日常对话 -> 便宜模型
                - "code": 代码相关 -> deepseek
                - "complex": 复杂推理 -> claude
            stream: 是否流式输出
            **kwargs: 其他参数

        Returns:
            AgentResult
        """
        # 根据 task_type 自动选择模型，或使用指定的 provider
        if provider:
            pass  # 使用指定的 provider
        elif task_type and hasattr(self.llm, 'get_provider_by_task'):
            provider = self.llm.get_provider_by_task(task_type)
        else:
            provider = self.default_provider

        # 获取或创建对话
        conversation = self._get_or_create_conversation(conversation_id)

        # 添加用户消息
        conversation.add_message("user", message)

        # 准备消息
        messages = conversation.get_messages_for_llm()

        # 构建完整的 system prompt（包含子 Agent 信息）
        full_system_prompt = self.system_prompt + self._get_agents_prompt()

        # 获取工具 schemas
        tool_schemas = self.tools.get_schemas() if self.tools.list_tools() else None

        # 工具调用循环
        tool_calls_made = []
        agents_called = []
        iterations = 0

        while iterations < self.max_tool_iterations:
            iterations += 1

            # 调用 LLM
            response = await self.llm.chat(
                messages=messages,
                system=full_system_prompt,
                tools=tool_schemas,
                provider=provider,
                **kwargs
            )

            # 如果没有工具调用，返回结果
            if not response.tool_calls:
                # 添加助手消息到对话
                conversation.add_message("assistant", response.content)

                # 保存对话
                if self.memory:
                    # 自动生成标题
                    if not conversation.title and len(conversation.messages) >= 2:
                        conversation.title = self._generate_title(conversation)
                    self.memory.save_conversation(conversation)

                return AgentResult(
                    content=response.content,
                    tool_calls_made=tool_calls_made,
                    agents_called=agents_called,
                    conversation_id=conversation.id,
                    model_used=response.model
                )

            # 执行工具调用
            tool_results = await self._execute_tools(response.tool_calls)

            for tc, tr in zip(response.tool_calls, tool_results):
                tool_calls_made.append({
                    "name": tc.name,
                    "arguments": tc.arguments,
                    "result": tr
                })
                # 记录调用了哪些子 Agent
                if tc.name == "call_agent":
                    agents_called.append(tc.arguments.get("agent_id", "unknown"))

            # 添加助手消息（包含工具调用）
            messages.append({
                "role": "assistant",
                "content": response.content or "",
                "tool_calls": [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.name,
                            "arguments": json.dumps(tc.arguments)
                        }
                    }
                    for tc in response.tool_calls
                ]
            })

            # 添加工具结果
            for tc, result in zip(response.tool_calls, tool_results):
                messages.append({
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": str(result)
                })

        # 超过最大迭代次数
        return AgentResult(
            content="抱歉，处理过程超时了。",
            tool_calls_made=tool_calls_made,
            agents_called=agents_called,
            conversation_id=conversation.id,
            model_used=provider
        )

    async def chat_stream(
        self,
        message: str,
        conversation_id: Optional[str] = None,
        provider: Optional[str] = None,
        **kwargs
    ) -> AsyncIterator[str]:
        """
        流式对话

        注意：流式模式下不支持工具调用
        """
        provider = provider or self.default_provider

        # 获取或创建对话
        conversation = self._get_or_create_conversation(conversation_id)
        conversation.add_message("user", message)

        messages = conversation.get_messages_for_llm()
        full_response = ""

        async for chunk in self.llm.chat_stream(
            messages=messages,
            system=self.system_prompt,
            provider=provider,
            **kwargs
        ):
            full_response += chunk
            yield chunk

        # 保存对话
        conversation.add_message("assistant", full_response)
        if self.memory:
            if not conversation.title:
                conversation.title = self._generate_title(conversation)
            self.memory.save_conversation(conversation)

    # ==================== 内部方法 ====================

    def _get_or_create_conversation(self, conversation_id: Optional[str]) -> Conversation:
        """获取或创建对话"""
        if conversation_id and self.memory:
            conversation = self.memory.get_conversation(conversation_id)
            if conversation:
                return conversation

        return Conversation()

    async def _execute_tools(self, tool_calls: List) -> List[str]:
        """执行工具调用"""
        results = []
        for tc in tool_calls:
            try:
                result = await self.tools.execute(tc.name, tc.arguments)
                results.append(str(result))
            except Exception as e:
                results.append(f"Error executing {tc.name}: {str(e)}")
        return results

    def _generate_title(self, conversation: Conversation) -> str:
        """生成对话标题"""
        first_user_msg = conversation.get_last_user_message()
        if first_user_msg:
            title = first_user_msg.content[:50]
            if len(first_user_msg.content) > 50:
                title += "..."
            return title
        return "新对话"

    # ==================== 模型切换 ====================

    def set_provider(self, provider: str):
        """动态切换默认模型"""
        self.default_provider = provider

    def use_cheap_model(self):
        """切换到最便宜的模型"""
        if hasattr(self.llm, 'get_cheapest_provider'):
            cheap = self.llm.get_cheapest_provider()
            if cheap:
                self.default_provider = cheap

    def use_smart_model(self):
        """切换到最智能的模型 (claude)"""
        if "claude" in self.llm.available_providers:
            self.default_provider = "claude"

    def get_available_providers(self) -> List[str]:
        """获取可用的模型列表"""
        return self.llm.available_providers

    # ==================== 工具注册 ====================

    def register_tool(self, func: Callable, name: Optional[str] = None):
        """注册工具"""
        self.tools.register_function(func, name)

    def tool(self, name: Optional[str] = None):
        """工具装饰器"""
        def decorator(func: Callable):
            self.register_tool(func, name)
            return func
        return decorator


# ==================== 快捷创建函数 ====================

def create_agent(
    llm: LLMService,
    agent_id: str,
    name: str,
    description: str,
    skills: List[Dict[str, Any]],
    system_prompt: str = "",
    default_provider: str = "claude"
) -> Agent:
    """
    快捷创建 Agent

    Example:
        stock_agent = create_agent(
            llm=llm_service,
            agent_id="stock",
            name="Stock Analyst",
            description="股票分析专家",
            skills=[
                {"name": "股票分析", "description": "分析股票走势和基本面"},
                {"name": "行情查询", "description": "查询实时股票价格"},
            ],
            system_prompt="你是一个专业的股票分析师..."
        )
    """
    skill_objects = [
        Skill(
            name=s["name"],
            description=s["description"],
            examples=s.get("examples", [])
        )
        for s in skills
    ]

    return Agent(
        llm=llm,
        agent_id=agent_id,
        name=name,
        description=description,
        skills=skill_objects,
        system_prompt=system_prompt,
        default_provider=default_provider
    )
