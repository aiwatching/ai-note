"""
Memory 数据模型
"""
from datetime import datetime
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
import uuid


class Message(BaseModel):
    """消息"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    role: str  # user, assistant, system, tool
    content: str
    tool_calls: Optional[List[Dict]] = None
    tool_call_id: Optional[str] = None
    name: Optional[str] = None  # tool name
    timestamp: datetime = Field(default_factory=datetime.now)
    metadata: Dict[str, Any] = {}

    def to_llm_format(self) -> Dict[str, Any]:
        """转换为 LLM 消息格式"""
        msg = {"role": self.role, "content": self.content}

        if self.tool_calls:
            msg["tool_calls"] = self.tool_calls

        if self.tool_call_id:
            msg["tool_call_id"] = self.tool_call_id

        if self.name:
            msg["name"] = self.name

        return msg


class Conversation(BaseModel):
    """对话/会话"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    title: Optional[str] = None
    messages: List[Message] = []
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    metadata: Dict[str, Any] = {}

    def add_message(self, role: str, content: str, **kwargs) -> Message:
        """添加消息"""
        msg = Message(role=role, content=content, **kwargs)
        self.messages.append(msg)
        self.updated_at = datetime.now()
        return msg

    def get_messages_for_llm(self, limit: Optional[int] = None) -> List[Dict]:
        """获取 LLM 格式的消息列表"""
        messages = self.messages[-limit:] if limit else self.messages
        return [msg.to_llm_format() for msg in messages]

    def get_last_user_message(self) -> Optional[Message]:
        """获取最后一条用户消息"""
        for msg in reversed(self.messages):
            if msg.role == "user":
                return msg
        return None


class UserPreference(BaseModel):
    """用户偏好"""
    key: str
    value: Any
    updated_at: datetime = Field(default_factory=datetime.now)
