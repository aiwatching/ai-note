"""
Memory 存储实现
"""
import json
import sqlite3
from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional
from .models import Message, Conversation, UserPreference


class Memory(ABC):
    """Memory 抽象基类"""

    @abstractmethod
    def save_conversation(self, conversation: Conversation):
        """保存对话"""
        pass

    @abstractmethod
    def get_conversation(self, conversation_id: str) -> Optional[Conversation]:
        """获取对话"""
        pass

    @abstractmethod
    def list_conversations(self, limit: int = 20) -> List[Conversation]:
        """列出对话"""
        pass

    @abstractmethod
    def delete_conversation(self, conversation_id: str):
        """删除对话"""
        pass

    @abstractmethod
    def set_preference(self, key: str, value: Any):
        """设置用户偏好"""
        pass

    @abstractmethod
    def get_preference(self, key: str, default: Any = None) -> Any:
        """获取用户偏好"""
        pass


class SQLiteMemory(Memory):
    """SQLite 存储实现"""

    def __init__(self, db_path: str = "./data/memory.db"):
        self.db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self):
        """初始化数据库"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS conversations (
                    id TEXT PRIMARY KEY,
                    title TEXT,
                    created_at TEXT,
                    updated_at TEXT,
                    metadata TEXT
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS messages (
                    id TEXT PRIMARY KEY,
                    conversation_id TEXT,
                    role TEXT,
                    content TEXT,
                    tool_calls TEXT,
                    tool_call_id TEXT,
                    name TEXT,
                    timestamp TEXT,
                    metadata TEXT,
                    FOREIGN KEY (conversation_id) REFERENCES conversations(id)
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS preferences (
                    key TEXT PRIMARY KEY,
                    value TEXT,
                    updated_at TEXT
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_messages_conversation
                ON messages(conversation_id)
            """)
            conn.commit()

    def save_conversation(self, conversation: Conversation):
        """保存对话"""
        with sqlite3.connect(self.db_path) as conn:
            # 保存对话
            conn.execute("""
                INSERT OR REPLACE INTO conversations (id, title, created_at, updated_at, metadata)
                VALUES (?, ?, ?, ?, ?)
            """, (
                conversation.id,
                conversation.title,
                conversation.created_at.isoformat(),
                conversation.updated_at.isoformat(),
                json.dumps(conversation.metadata)
            ))

            # 删除旧消息
            conn.execute("DELETE FROM messages WHERE conversation_id = ?", (conversation.id,))

            # 保存新消息
            for msg in conversation.messages:
                conn.execute("""
                    INSERT INTO messages (id, conversation_id, role, content, tool_calls,
                                         tool_call_id, name, timestamp, metadata)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    msg.id,
                    conversation.id,
                    msg.role,
                    msg.content,
                    json.dumps(msg.tool_calls) if msg.tool_calls else None,
                    msg.tool_call_id,
                    msg.name,
                    msg.timestamp.isoformat(),
                    json.dumps(msg.metadata)
                ))

            conn.commit()

    def get_conversation(self, conversation_id: str) -> Optional[Conversation]:
        """获取对话"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row

            # 获取对话
            row = conn.execute(
                "SELECT * FROM conversations WHERE id = ?",
                (conversation_id,)
            ).fetchone()

            if not row:
                return None

            # 获取消息
            messages_rows = conn.execute(
                "SELECT * FROM messages WHERE conversation_id = ? ORDER BY timestamp",
                (conversation_id,)
            ).fetchall()

            messages = []
            for msg_row in messages_rows:
                messages.append(Message(
                    id=msg_row["id"],
                    role=msg_row["role"],
                    content=msg_row["content"],
                    tool_calls=json.loads(msg_row["tool_calls"]) if msg_row["tool_calls"] else None,
                    tool_call_id=msg_row["tool_call_id"],
                    name=msg_row["name"],
                    timestamp=datetime.fromisoformat(msg_row["timestamp"]),
                    metadata=json.loads(msg_row["metadata"]) if msg_row["metadata"] else {}
                ))

            return Conversation(
                id=row["id"],
                title=row["title"],
                messages=messages,
                created_at=datetime.fromisoformat(row["created_at"]),
                updated_at=datetime.fromisoformat(row["updated_at"]),
                metadata=json.loads(row["metadata"]) if row["metadata"] else {}
            )

    def list_conversations(self, limit: int = 20) -> List[Conversation]:
        """列出对话"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT * FROM conversations ORDER BY updated_at DESC LIMIT ?",
                (limit,)
            ).fetchall()

            conversations = []
            for row in rows:
                # 只获取基本信息，不获取消息
                conv = Conversation(
                    id=row["id"],
                    title=row["title"],
                    messages=[],
                    created_at=datetime.fromisoformat(row["created_at"]),
                    updated_at=datetime.fromisoformat(row["updated_at"]),
                    metadata=json.loads(row["metadata"]) if row["metadata"] else {}
                )
                conversations.append(conv)

            return conversations

    def delete_conversation(self, conversation_id: str):
        """删除对话"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("DELETE FROM messages WHERE conversation_id = ?", (conversation_id,))
            conn.execute("DELETE FROM conversations WHERE id = ?", (conversation_id,))
            conn.commit()

    def set_preference(self, key: str, value: Any):
        """设置用户偏好"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO preferences (key, value, updated_at)
                VALUES (?, ?, ?)
            """, (key, json.dumps(value), datetime.now().isoformat()))
            conn.commit()

    def get_preference(self, key: str, default: Any = None) -> Any:
        """获取用户偏好"""
        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute(
                "SELECT value FROM preferences WHERE key = ?",
                (key,)
            ).fetchone()

            if row:
                return json.loads(row[0])
            return default

    def get_all_preferences(self) -> Dict[str, Any]:
        """获取所有偏好"""
        with sqlite3.connect(self.db_path) as conn:
            rows = conn.execute("SELECT key, value FROM preferences").fetchall()
            return {row[0]: json.loads(row[1]) for row in rows}
