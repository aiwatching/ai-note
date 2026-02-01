"""
Agent Core Implementation
"""
import json
import time
from typing import List, Dict, Any, Optional, AsyncIterator, Callable, TYPE_CHECKING
from pydantic import BaseModel, Field
from enum import Enum

from ..llm import LLMService, LLMResponse
from ..tools import ToolRegistry
from ..memory import Memory, Conversation, Message
from .logger import get_agent_logger, AgentLogger


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

        # Sub-agent registry
        self._sub_agents: Dict[str, 'Agent'] = {}

        # Logger for this agent
        self.logger: AgentLogger = get_agent_logger(agent_id)

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
        """Register call_agent tool for sub-agent delegation"""
        parent_agent = self  # Capture reference for closure

        async def call_agent(agent_id: str, message: str) -> str:
            """调用专业子Agent处理任务。查看系统提示了解可用的Agent ID（如 stock, dev）。

            Args:
                agent_id: Agent的ID，如 stock（投资分析）、dev（开发助手）
                message: 发送给Agent的任务描述
            """
            if agent_id not in parent_agent._sub_agents:
                available = list(parent_agent._sub_agents.keys())
                parent_agent.logger.error(
                    "agent_not_found",
                    f"Agent '{agent_id}' not found. Available: {available}"
                )
                return f"错误：Agent '{agent_id}' 不存在。可用的Agent: {available}"

            # Log delegation
            parent_agent.logger.agent_delegate(agent_id, message)

            sub_agent = parent_agent._sub_agents[agent_id]
            result = await sub_agent.chat(message)

            # Log response
            parent_agent.logger.agent_response(agent_id, result.content)

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
        Main chat method.

        Args:
            message: User message
            conversation_id: Conversation ID (optional, for continuing conversation)
            provider: LLM provider to use (direct specification)
            task_type: Task type for auto model selection
                - "simple": Simple task -> cheapest
                - "chat": Daily chat -> cheap model
                - "code": Code related -> deepseek
                - "complex": Complex reasoning -> claude
            stream: Whether to stream output
            **kwargs: Additional arguments

        Returns:
            AgentResult
        """
        start_time = time.time()

        # Select model based on task_type or use specified provider
        if provider:
            self.logger.model_select(provider, "explicitly specified")
        elif task_type and hasattr(self.llm, 'get_provider_by_task'):
            provider = self.llm.get_provider_by_task(task_type)
            self.logger.model_select(provider, f"task_type={task_type}")
        else:
            provider = self.default_provider
            self.logger.model_select(provider, "default")

        # Get or create conversation
        conversation = self._get_or_create_conversation(conversation_id)

        # Log context loading
        existing_messages = len(conversation.messages)
        if existing_messages > 0:
            self.logger.context_load(conversation.id, existing_messages)

        # Add user message
        conversation.add_message("user", message)

        # Prepare messages
        messages = conversation.get_messages_for_llm()

        # Log chat start
        self.logger.chat_start(
            message=message,
            conversation_id=conversation_id,
            provider=provider,
            context_messages=existing_messages
        )

        # Build full system prompt (including sub-agent info)
        full_system_prompt = self.system_prompt + self._get_agents_prompt()

        # Get tool schemas
        tool_schemas = self.tools.get_schemas() if self.tools.list_tools() else None

        # Debug: log tools being passed to LLM
        if tool_schemas:
            tool_names = [t.get("name", "unknown") for t in tool_schemas]
            self.logger.logger.info(f"📋 TOOLS PASSED TO LLM | count={len(tool_schemas)} | tools={tool_names}")
        else:
            self.logger.logger.warning("⚠️ NO TOOLS passed to LLM")

        # Tool call loop
        tool_calls_made = []
        agents_called = []
        iterations = 0

        while iterations < self.max_tool_iterations:
            iterations += 1

            # Call LLM
            response = await self.llm.chat(
                messages=messages,
                system=full_system_prompt,
                tools=tool_schemas,
                provider=provider,
                **kwargs
            )

            # If no tool calls, return result
            if not response.tool_calls:
                # Add assistant message to conversation
                conversation.add_message("assistant", response.content)

                # Save conversation
                if self.memory:
                    # Auto-generate title
                    if not conversation.title and len(conversation.messages) >= 2:
                        conversation.title = self._generate_title(conversation)
                    self.memory.save_conversation(conversation)

                # Log chat end
                duration_ms = (time.time() - start_time) * 1000
                self.logger.chat_end(
                    response_preview=response.content,
                    tool_calls=len(tool_calls_made),
                    agents_called=agents_called,
                    model_used=response.model,
                    duration_ms=duration_ms
                )

                return AgentResult(
                    content=response.content,
                    tool_calls_made=tool_calls_made,
                    agents_called=agents_called,
                    conversation_id=conversation.id,
                    model_used=response.model
                )

            # Execute tool calls with logging
            tool_results = await self._execute_tools_with_logging(response.tool_calls)

            for tc, tr in zip(response.tool_calls, tool_results):
                tool_calls_made.append({
                    "name": tc.name,
                    "arguments": tc.arguments,
                    "result": tr
                })
                # Record which sub-agents were called
                if tc.name == "call_agent":
                    agents_called.append(tc.arguments.get("agent_id", "unknown"))

            # Add assistant message (with tool calls)
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

            # Add tool results
            for tc, result in zip(response.tool_calls, tool_results):
                messages.append({
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": str(result)
                })

        # Exceeded max iterations
        duration_ms = (time.time() - start_time) * 1000
        self.logger.error("max_iterations", f"Exceeded {self.max_tool_iterations} iterations")
        self.logger.chat_end(
            response_preview="Processing timeout",
            tool_calls=len(tool_calls_made),
            agents_called=agents_called,
            model_used=provider,
            duration_ms=duration_ms
        )

        return AgentResult(
            content="Sorry, processing timed out.",
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

        策略：先执行完整的工具调用流程，然后流式返回最终结果。
        这样既支持工具调用，又能提供流式输出体验。
        """
        # 如果有工具或子Agent，使用非流式模式处理工具调用
        has_tools = bool(self.tools.list_tools())
        has_sub_agents = bool(self._sub_agents)

        if has_tools or has_sub_agents:
            # 使用完整的chat方法处理工具调用
            result = await self.chat(
                message=message,
                conversation_id=conversation_id,
                provider=provider,
                **kwargs
            )

            # 流式输出最终结果
            # 分块输出以提供更好的用户体验
            content = result.content
            chunk_size = 20  # 每次输出的字符数

            for i in range(0, len(content), chunk_size):
                chunk = content[i:i + chunk_size]
                yield chunk
                # 可以添加小延迟模拟打字效果
                # await asyncio.sleep(0.01)

            return

        # 没有工具时，使用纯流式模式
        provider = provider or self.default_provider

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
        """Execute tool calls (without logging)"""
        results = []
        for tc in tool_calls:
            try:
                result = await self.tools.execute(tc.name, tc.arguments)
                results.append(str(result))
            except Exception as e:
                results.append(f"Error executing {tc.name}: {str(e)}")
        return results

    async def _execute_tools_with_logging(self, tool_calls: List) -> List[str]:
        """Execute tool calls with logging"""
        results = []
        for tc in tool_calls:
            # Log tool call
            self.logger.tool_call(tc.name, tc.arguments)

            try:
                result = await self.tools.execute(tc.name, tc.arguments)
                result_str = str(result)
                results.append(result_str)

                # Log success
                self.logger.tool_result(tc.name, result_str, success=True)

            except Exception as e:
                error_msg = f"Error executing {tc.name}: {str(e)}"
                results.append(error_msg)

                # Log error
                self.logger.tool_result(tc.name, error_msg, success=False)
                self.logger.error("tool_execution", error_msg, {"tool": tc.name})

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
