"""
Agent Logging System

Provides structured logging for agent orchestration, tool calls, and sub-agent delegation.
"""
import logging
import json
from datetime import datetime
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field, asdict
from enum import Enum


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(name)s | %(message)s',
    datefmt='%H:%M:%S'
)


class EventType(str, Enum):
    """Agent event types"""
    # Lifecycle events
    INIT = "init"
    READY = "ready"
    # Chat events
    CHAT_START = "chat_start"
    CHAT_END = "chat_end"
    # Tool events
    TOOL_CALL = "tool_call"
    TOOL_RESULT = "tool_result"
    TOOL_REGISTER = "tool_register"
    # Agent events
    AGENT_DELEGATE = "agent_delegate"
    AGENT_RESPONSE = "agent_response"
    AGENT_REGISTER = "agent_register"
    # Context events
    MODEL_SELECT = "model_select"
    CONTEXT_LOAD = "context_load"
    MEMORY_SEARCH = "memory_search"
    MEMORY_ADD = "memory_add"
    # Error
    ERROR = "error"


@dataclass
class AgentEvent:
    """Structured agent event"""
    timestamp: str
    event_type: EventType
    agent_id: str
    data: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "event_type": self.event_type.value,
            "agent_id": self.agent_id,
            **self.data
        }


class AgentLogger:
    """
    Structured logger for agent activities.

    Logs to both Python logging and maintains an event history
    that can be queried for debugging.
    """

    def __init__(self, agent_id: str = "main"):
        self.agent_id = agent_id
        self.logger = logging.getLogger(f"agent.{agent_id}")
        self.events: List[AgentEvent] = []
        self._max_events = 1000  # Keep last N events

    def _emit(self, event_type: EventType, **data) -> AgentEvent:
        """Emit an event"""
        event = AgentEvent(
            timestamp=datetime.now().isoformat(),
            event_type=event_type,
            agent_id=self.agent_id,
            data=data
        )

        # Store event
        self.events.append(event)
        if len(self.events) > self._max_events:
            self.events = self.events[-self._max_events:]

        return event

    def chat_start(
        self,
        message: str,
        conversation_id: Optional[str],
        provider: str,
        context_messages: int = 0
    ):
        """Log start of chat"""
        event = self._emit(
            EventType.CHAT_START,
            message_preview=message[:100] + "..." if len(message) > 100 else message,
            conversation_id=conversation_id,
            provider=provider,
            context_messages=context_messages
        )

        self.logger.info(
            f"📨 CHAT START | provider={provider} | "
            f"conv={conversation_id or 'new'} | "
            f"context={context_messages} msgs | "
            f"msg=\"{event.data['message_preview']}\""
        )

    def chat_end(
        self,
        response_preview: str,
        tool_calls: int,
        agents_called: List[str],
        model_used: str,
        duration_ms: Optional[float] = None
    ):
        """Log end of chat"""
        event = self._emit(
            EventType.CHAT_END,
            response_preview=response_preview[:100] + "..." if len(response_preview) > 100 else response_preview,
            tool_calls=tool_calls,
            agents_called=agents_called,
            model_used=model_used,
            duration_ms=duration_ms
        )

        agents_str = ", ".join(agents_called) if agents_called else "none"
        duration_str = f" | {duration_ms:.0f}ms" if duration_ms else ""

        self.logger.info(
            f"✅ CHAT END | model={model_used} | "
            f"tools={tool_calls} | agents=[{agents_str}]{duration_str}"
        )

    def tool_call(self, tool_name: str, arguments: Dict[str, Any]):
        """Log tool call"""
        event = self._emit(
            EventType.TOOL_CALL,
            tool_name=tool_name,
            arguments=arguments
        )

        args_str = json.dumps(arguments, ensure_ascii=False)[:80]
        self.logger.info(f"🔧 TOOL CALL | {tool_name}({args_str})")

    def tool_result(self, tool_name: str, result: str, success: bool = True):
        """Log tool result"""
        event = self._emit(
            EventType.TOOL_RESULT,
            tool_name=tool_name,
            result_preview=result[:200] if len(result) > 200 else result,
            success=success
        )

        status = "✓" if success else "✗"
        result_preview = result[:100] + "..." if len(result) > 100 else result
        self.logger.info(f"   {status} TOOL RESULT | {tool_name} → {result_preview}")

    def agent_delegate(self, target_agent_id: str, message: str):
        """Log delegation to sub-agent"""
        event = self._emit(
            EventType.AGENT_DELEGATE,
            target_agent_id=target_agent_id,
            message_preview=message[:100] + "..." if len(message) > 100 else message
        )

        self.logger.info(
            f"🤖 DELEGATE | {self.agent_id} → {target_agent_id} | "
            f"\"{event.data['message_preview']}\""
        )

    def agent_response(self, source_agent_id: str, response: str):
        """Log response from sub-agent"""
        event = self._emit(
            EventType.AGENT_RESPONSE,
            source_agent_id=source_agent_id,
            response_preview=response[:100] + "..." if len(response) > 100 else response
        )

        self.logger.info(
            f"   ← RESPONSE | {source_agent_id} | "
            f"\"{event.data['response_preview']}\""
        )

    def model_select(self, provider: str, reason: str):
        """Log model selection"""
        event = self._emit(
            EventType.MODEL_SELECT,
            provider=provider,
            reason=reason
        )

        self.logger.debug(f"🎯 MODEL SELECT | {provider} | {reason}")

    def context_load(self, conversation_id: str, message_count: int):
        """Log conversation context loading"""
        event = self._emit(
            EventType.CONTEXT_LOAD,
            conversation_id=conversation_id,
            message_count=message_count
        )

        self.logger.debug(f"📚 CONTEXT LOAD | conv={conversation_id} | {message_count} messages")

    def error(self, error_type: str, message: str, details: Optional[Dict] = None):
        """Log error"""
        event = self._emit(
            EventType.ERROR,
            error_type=error_type,
            message=message,
            details=details or {}
        )

        self.logger.error(f"❌ ERROR | {error_type} | {message}")

    def init(self, name: str, description: str = ""):
        """Log agent initialization"""
        event = self._emit(
            EventType.INIT,
            name=name,
            description=description
        )
        self.logger.info(f"🚀 INIT | Agent '{name}' initializing")

    def ready(self, tools_count: int = 0, sub_agents_count: int = 0):
        """Log agent ready"""
        event = self._emit(
            EventType.READY,
            tools_count=tools_count,
            sub_agents_count=sub_agents_count
        )
        self.logger.info(f"✅ READY | tools={tools_count} | sub_agents={sub_agents_count}")

    def tool_register(self, tool_name: str):
        """Log tool registration"""
        event = self._emit(
            EventType.TOOL_REGISTER,
            tool_name=tool_name
        )
        self.logger.debug(f"🔧 TOOL REGISTER | {tool_name}")

    def agent_register(self, agent_id: str, agent_name: str):
        """Log sub-agent registration"""
        event = self._emit(
            EventType.AGENT_REGISTER,
            registered_agent_id=agent_id,
            registered_agent_name=agent_name
        )
        self.logger.info(f"🤖 AGENT REGISTER | {agent_name} ({agent_id})")

    def memory_search(self, query: str, results_count: int, duration_ms: float = 0):
        """Log memory search"""
        event = self._emit(
            EventType.MEMORY_SEARCH,
            query=query[:100],
            results_count=results_count,
            duration_ms=duration_ms
        )
        self.logger.info(f"🔍 MEMORY SEARCH | '{query[:50]}' → {results_count} results | {duration_ms:.0f}ms")

    def memory_add(self, source: str, source_id: str, chunks_count: int):
        """Log memory add"""
        event = self._emit(
            EventType.MEMORY_ADD,
            source=source,
            source_id=source_id,
            chunks_count=chunks_count
        )
        self.logger.info(f"💾 MEMORY ADD | {source}:{source_id} | {chunks_count} chunks")

    def get_recent_events(self, count: int = 50) -> List[Dict]:
        """Get recent events for debugging"""
        return [e.to_dict() for e in self.events[-count:]]

    def get_events_by_type(self, event_type: EventType) -> List[Dict]:
        """Get events by type"""
        return [e.to_dict() for e in self.events if e.event_type == event_type]

    def get_agent_calls(self) -> List[Dict]:
        """Get all agent delegation events"""
        return self.get_events_by_type(EventType.AGENT_DELEGATE)


# Global logger registry
_loggers: Dict[str, AgentLogger] = {}


def get_agent_logger(agent_id: str = "main") -> AgentLogger:
    """Get or create agent logger"""
    if agent_id not in _loggers:
        _loggers[agent_id] = AgentLogger(agent_id)
    return _loggers[agent_id]


def get_all_loggers() -> Dict[str, AgentLogger]:
    """Get all loggers"""
    return _loggers
