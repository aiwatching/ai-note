"""
Chat API
"""
from typing import Optional, List
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import json

from ..core.deps import get_agent
from ..agent import get_agent_logger, get_all_loggers


router = APIRouter(prefix="/chat", tags=["chat"])


class ChatRequest(BaseModel):
    """Chat request"""
    message: str
    conversation_id: Optional[str] = None
    provider: Optional[str] = None
    task_type: Optional[str] = None  # simple, chat, code, complex
    stream: bool = False


class ChatResponse(BaseModel):
    """Chat response"""
    content: str
    conversation_id: str
    model_used: str
    tool_calls_made: List[dict] = []
    agents_called: List[str] = []  # Which sub-agents were called


@router.post("", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """Send a chat message"""
    agent = get_agent()

    if request.stream:
        # Streaming response
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

    # Non-streaming response
    result = await agent.chat(
        message=request.message,
        conversation_id=request.conversation_id,
        provider=request.provider,
        task_type=request.task_type
    )

    return ChatResponse(
        content=result.content,
        conversation_id=result.conversation_id,
        model_used=result.model_used,
        tool_calls_made=result.tool_calls_made,
        agents_called=result.agents_called
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
    """Get available LLM models"""
    agent = get_agent()
    return ModelsResponse(
        models=agent.llm.available_providers,
        default=agent.default_provider
    )


# ==================== Agent Logs ====================

@router.get("/logs")
async def get_logs(agent_id: str = "main", count: int = 50):
    """
    Get recent agent activity logs.

    Useful for debugging agent orchestration, tool calls, and sub-agent delegation.

    Args:
        agent_id: Agent ID to get logs for (default: main)
        count: Number of recent events to return
    """
    logger = get_agent_logger(agent_id)
    return {
        "agent_id": agent_id,
        "events": logger.get_recent_events(count)
    }


@router.get("/logs/agents")
async def get_agent_delegation_logs():
    """
    Get all agent delegation events.

    Shows when the main agent delegated tasks to sub-agents.
    """
    logger = get_agent_logger("main")
    return {
        "delegations": logger.get_agent_calls()
    }


@router.get("/logs/all")
async def get_all_agent_logs(count: int = 20):
    """
    Get logs from all agents.

    Returns recent events from each registered agent.
    """
    all_logs = {}
    for agent_id, logger in get_all_loggers().items():
        all_logs[agent_id] = logger.get_recent_events(count)

    return all_logs


class AgentInfo(BaseModel):
    """Agent information"""
    id: str
    name: str
    description: str
    provider: str
    skills: List[str]
    tools: List[str]


@router.get("/agents", response_model=List[AgentInfo])
async def list_agents():
    """
    List all registered agents and their capabilities.

    Returns the main agent and all sub-agents with their skills and tools.
    """
    agent = get_agent()

    agents_info = []

    # Main agent
    agents_info.append(AgentInfo(
        id=agent.agent_id,
        name=agent.name,
        description=agent.description,
        provider=agent.default_provider,
        skills=[s.name for s in agent.skills],
        tools=agent.tools.list_tools()
    ))

    # Sub-agents
    for card in agent.list_agents():
        sub_agent = agent._sub_agents.get(card.id)
        if sub_agent:
            agents_info.append(AgentInfo(
                id=card.id,
                name=card.name,
                description=card.description,
                provider=sub_agent.default_provider,
                skills=[s.name for s in card.skills],
                tools=sub_agent.tools.list_tools()
            ))

    return agents_info


@router.get("/debug/tools")
async def debug_tools():
    """
    Debug endpoint: Get all tool schemas being passed to LLM.

    Shows the exact tool definitions that will be sent to the LLM.
    """
    agent = get_agent()

    return {
        "main_agent": {
            "id": agent.agent_id,
            "tools_count": len(agent.tools.list_tools()),
            "tool_names": agent.tools.list_tools(),
            "tool_schemas": agent.tools.get_schemas(),
        },
        "sub_agents": {
            sub_id: {
                "id": sub.agent_id,
                "name": sub.name,
                "provider": sub.default_provider,
                "tools_count": len(sub.tools.list_tools()),
                "tool_names": sub.tools.list_tools(),
            }
            for sub_id, sub in agent._sub_agents.items()
        }
    }
