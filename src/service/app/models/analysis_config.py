"""Analysis configuration model for storing customizable prompts and settings."""
import json
from datetime import datetime
from typing import List, Optional

from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String, Text, Boolean
from sqlalchemy.orm import relationship

from ..database import Base


class AnalysisConfig(Base):
    """
    Configuration for AI analysis including prompts and parameters.

    Supports version management and user customization.
    """

    __tablename__ = "analysis_configs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    # Config identification
    config_type = Column(String(50), nullable=False, index=True)
    # Types: note_analysis, search_query, todo_extract, schedule_extract, aggregation

    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    version = Column(Integer, default=1)
    is_active = Column(Boolean, default=True)
    is_default = Column(Boolean, default=False)

    # Prompt template
    prompt_template = Column(Text, nullable=False)

    # AI model settings
    model_name = Column(String(100), nullable=True)  # Override default model
    temperature = Column(Float, default=0.7)
    max_tokens = Column(Integer, default=4096)

    # Customizable lists (stored as JSON)
    _categories = Column("categories", Text, nullable=True)
    _domains = Column("domains", Text, nullable=True)
    _priorities = Column("priorities", Text, nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    @property
    def categories(self) -> List[str]:
        """Get categories as list."""
        if self._categories:
            return json.loads(self._categories)
        return [
            "学习笔记", "工作记录", "客户问题", "需求记录",
            "Bug记录", "会议记录", "想法灵感", "个人杂记"
        ]

    @categories.setter
    def categories(self, value: List[str]):
        """Set categories from list."""
        self._categories = json.dumps(value, ensure_ascii=False) if value else None

    @property
    def domains(self) -> List[str]:
        """Get domains as list."""
        if self._domains:
            return json.loads(self._domains)
        return ["技术", "产品", "市场", "管理", "设计", "运营", "财务", "人事", "其他"]

    @domains.setter
    def domains(self, value: List[str]):
        """Set domains from list."""
        self._domains = json.dumps(value, ensure_ascii=False) if value else None

    @property
    def priorities(self) -> List[str]:
        """Get priorities as list."""
        if self._priorities:
            return json.loads(self._priorities)
        return ["high", "medium", "low"]

    @priorities.setter
    def priorities(self, value: List[str]):
        """Set priorities from list."""
        self._priorities = json.dumps(value, ensure_ascii=False) if value else None

    def __repr__(self):
        return f"<AnalysisConfig(id={self.id}, type={self.config_type}, name={self.name}, v{self.version})>"


# Default deep analysis prompt template
DEFAULT_DEEP_ANALYSIS_PROMPT = '''你是一个专业的笔记分析助手。请对以下笔记内容进行深度分析，提取所有关键信息。

当前日期：{current_date}

笔记内容：
---
{content}
---

请以 JSON 格式返回分析结果，必须包含以下所有字段：

{{
  "basic_info": {{
    "title": "简洁标题（10字以内）",
    "category": "分类",
    "subcategory": "子分类（可选）",
    "summary": "一句话摘要（30字以内）"
  }},
  "entities": {{
    "persons": [
      {{"name": "标准名", "aliases": ["别名1", "别名2"], "role": "角色描述"}}
    ],
    "companies": [
      {{"name": "公司名", "aliases": [], "type": "客户/供应商/合作伙伴"}}
    ],
    "projects": [
      {{"name": "项目名", "status": "进行中/已完成/规划中"}}
    ],
    "locations": ["地点1", "地点2"],
    "technical_terms": ["术语1", "术语2"]
  }},
  "topic_analysis": {{
    "core_topic": "核心主题（一句话）",
    "keywords": ["关键词1", "关键词2", "关键词3"],
    "domain": "所属领域"
  }},
  "time_info": {{
    "event_times": [
      {{"description": "事件描述", "time": "YYYY-MM-DD HH:mm", "original_text": "原文表述"}}
    ],
    "deadlines": [
      {{"description": "截止事项", "time": "YYYY-MM-DD", "original_text": "原文表述"}}
    ],
    "follow_up_dates": [
      {{"description": "跟进事项", "time": "YYYY-MM-DD", "original_text": "原文表述"}}
    ]
  }},
  "relation_signals": {{
    "is_follow_up": false,
    "is_summary": false,
    "is_standalone": true,
    "reference_keywords": ["被引用的关键词"],
    "continuation_topic": "延续的主题（如果有）"
  }},
  "content_features": {{
    "intent": "笔记意图",
    "content_type": "内容类型",
    "has_todos": false,
    "has_questions": false,
    "has_decisions": false,
    "urgency": "urgent/important/normal/casual"
  }},
  "priority_assessment": {{
    "priority": "high/medium/low",
    "urgency_score": 0.5,
    "importance_score": 0.5,
    "reason": "评估理由"
  }},
  "action_suggestions": [
    {{
      "type": "todo/schedule/reminder/link_project",
      "title": "建议操作标题",
      "due_date": "YYYY-MM-DD（如适用）",
      "time": "HH:mm（如适用）",
      "reason": "建议理由"
    }}
  ],
  "key_points": [
    "关键要点1",
    "关键要点2",
    "关键要点3"
  ]
}}

可用的分类列表：{categories}
可用的领域列表：{domains}

注意：
1. 所有相对时间（如"明天"、"下周三"）必须转换为绝对日期
2. 人物姓名要识别所有可能的别名
3. 如果无法确定某个字段，使用 null 或空数组
4. 确保返回的是有效的 JSON 格式'''
