"""Note model with enhanced AI analysis metadata."""
import json
from datetime import datetime
from typing import List, Optional, Dict, Any

from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from ..database import Base


class Note(Base):
    """Note model with comprehensive AI analysis metadata."""

    __tablename__ = "notes"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    # ===== Basic Information =====
    title = Column(String(200), nullable=True)
    raw_content = Column(Text, nullable=False)  # Original markdown content
    raw_file_path = Column(String(500), nullable=True)  # Path to raw markdown file
    organized_file_path = Column(String(500), nullable=True)  # Path to organized file

    # Category and classification
    category = Column(String(50), nullable=True, index=True)
    subcategory = Column(String(50), nullable=True)
    _tags = Column("tags", Text, nullable=True)  # JSON array
    summary = Column(Text, nullable=True)

    # ===== Topic Analysis =====
    core_topic = Column(String(200), nullable=True)
    _keywords = Column("keywords", Text, nullable=True)  # JSON array
    domain = Column(String(50), nullable=True)  # 所属领域

    # ===== Entities (JSON storage) =====
    _entities = Column("entities", Text, nullable=True)
    # Structure:
    # {
    #   "persons": [{"name": "标准名", "aliases": [], "role": ""}],
    #   "companies": [{"name": "", "aliases": [], "type": ""}],
    #   "projects": [{"name": "", "status": ""}],
    #   "locations": [],
    #   "technical_terms": []
    # }

    # ===== Time Information (JSON storage) =====
    _time_info = Column("time_info", Text, nullable=True)
    # Structure:
    # {
    #   "event_times": [{"description": "", "time": "", "original_text": ""}],
    #   "deadlines": [{"description": "", "time": "", "original_text": ""}],
    #   "follow_up_dates": [{"description": "", "time": "", "original_text": ""}]
    # }

    # ===== Relation Signals =====
    is_follow_up = Column(Boolean, default=False)  # 是否跟进笔记
    is_summary_note = Column(Boolean, default=False)  # 是否总结笔记
    is_standalone = Column(Boolean, default=True)  # 是否独立笔记
    _reference_keywords = Column("reference_keywords", Text, nullable=True)  # JSON array
    continuation_topic = Column(String(200), nullable=True)  # 延续的主题

    # ===== Content Features =====
    intent = Column(String(50), nullable=True)  # 笔记意图
    content_type = Column(String(50), nullable=True)  # 内容类型
    is_todo = Column(Boolean, default=False)
    is_schedule = Column(Boolean, default=False)
    has_questions = Column(Boolean, default=False)
    has_decisions = Column(Boolean, default=False)
    urgency = Column(String(20), nullable=True)  # urgent/important/normal/casual

    # ===== Priority Assessment =====
    priority = Column(String(20), nullable=True)  # high/medium/low
    urgency_score = Column(Float, nullable=True)  # 0-1
    importance_score = Column(Float, nullable=True)  # 0-1
    priority_reason = Column(Text, nullable=True)

    # ===== Action Suggestions (JSON storage) =====
    _action_suggestions = Column("action_suggestions", Text, nullable=True)
    # Array of: {"type": "", "title": "", "due_date": "", "time": "", "reason": ""}

    # ===== Key Points (JSON storage) =====
    _key_points = Column("key_points", Text, nullable=True)  # JSON array

    # ===== Legacy fields for compatibility =====
    _related_persons = Column("related_persons", Text, nullable=True)
    _related_dates = Column("related_dates", Text, nullable=True)

    # ===== Status and Timestamps =====
    status = Column(String(20), default="active", index=True)
    analysis_version = Column(Integer, default=1)  # Track analysis prompt version
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # ===== Relationships =====
    todos = relationship("Todo", back_populates="note", lazy="dynamic")
    schedules = relationship("Schedule", back_populates="note", lazy="dynamic")

    # ===== JSON Property Helpers =====
    @property
    def tags(self) -> List[str]:
        if self._tags:
            return json.loads(self._tags)
        return []

    @tags.setter
    def tags(self, value: List[str]):
        self._tags = json.dumps(value, ensure_ascii=False) if value else None

    @property
    def keywords(self) -> List[str]:
        if self._keywords:
            return json.loads(self._keywords)
        return []

    @keywords.setter
    def keywords(self, value: List[str]):
        self._keywords = json.dumps(value, ensure_ascii=False) if value else None

    @property
    def entities(self) -> Dict[str, Any]:
        if self._entities:
            return json.loads(self._entities)
        return {"persons": [], "companies": [], "projects": [], "locations": [], "technical_terms": []}

    @entities.setter
    def entities(self, value: Dict[str, Any]):
        self._entities = json.dumps(value, ensure_ascii=False) if value else None

    @property
    def time_info(self) -> Dict[str, Any]:
        if self._time_info:
            return json.loads(self._time_info)
        return {"event_times": [], "deadlines": [], "follow_up_dates": []}

    @time_info.setter
    def time_info(self, value: Dict[str, Any]):
        self._time_info = json.dumps(value, ensure_ascii=False) if value else None

    @property
    def reference_keywords(self) -> List[str]:
        if self._reference_keywords:
            return json.loads(self._reference_keywords)
        return []

    @reference_keywords.setter
    def reference_keywords(self, value: List[str]):
        self._reference_keywords = json.dumps(value, ensure_ascii=False) if value else None

    @property
    def action_suggestions(self) -> List[Dict[str, Any]]:
        if self._action_suggestions:
            return json.loads(self._action_suggestions)
        return []

    @action_suggestions.setter
    def action_suggestions(self, value: List[Dict[str, Any]]):
        self._action_suggestions = json.dumps(value, ensure_ascii=False) if value else None

    @property
    def key_points(self) -> List[str]:
        if self._key_points:
            return json.loads(self._key_points)
        return []

    @key_points.setter
    def key_points(self, value: List[str]):
        self._key_points = json.dumps(value, ensure_ascii=False) if value else None

    # Legacy properties for backward compatibility
    @property
    def related_persons(self) -> List[str]:
        if self._related_persons:
            return json.loads(self._related_persons)
        # Fallback to entities.persons
        persons = self.entities.get("persons", [])
        return [p["name"] if isinstance(p, dict) else p for p in persons]

    @related_persons.setter
    def related_persons(self, value: List[str]):
        self._related_persons = json.dumps(value, ensure_ascii=False) if value else None

    @property
    def related_dates(self) -> List[str]:
        if self._related_dates:
            return json.loads(self._related_dates)
        return []

    @related_dates.setter
    def related_dates(self, value: List[str]):
        self._related_dates = json.dumps(value, ensure_ascii=False) if value else None

    def __repr__(self):
        return f"<Note(id={self.id}, title={self.title}, category={self.category})>"
