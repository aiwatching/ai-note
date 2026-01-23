"""DeepSeek AI service implementation."""
import json
import re
from datetime import date, datetime
from typing import Dict, List, Optional

import httpx
from loguru import logger

from .base import AIServiceBase
from .prompts import (
    ANALYZE_NOTE_PROMPT,
    DEEP_ANALYZE_NOTE_PROMPT,
    DEFAULT_CATEGORIES,
    DEFAULT_DOMAINS,
    SEMANTIC_SEARCH_PROMPT,
    EXTRACT_TODOS_PROMPT,
    EXTRACT_SCHEDULE_PROMPT,
    EXTRACT_TITLE_PROMPT,
)


class DeepSeekService(AIServiceBase):
    """DeepSeek API implementation of AI service (OpenAI-compatible)."""

    def __init__(
        self,
        api_key: str,
        model: str = "deepseek-chat",
        base_url: str = "https://api.deepseek.com/v1",
    ):
        """
        Initialize DeepSeek service.

        Args:
            api_key: DeepSeek API key
            model: Model to use (deepseek-chat or deepseek-coder)
            base_url: API base URL
        """
        self.api_key = api_key
        self.model = model
        self.base_url = base_url
        self.client = httpx.Client(timeout=60.0)

    async def deep_analyze_note(
        self,
        content: str,
        current_date: str,
        categories: Optional[List[str]] = None,
        domains: Optional[List[str]] = None,
        custom_prompt: Optional[str] = None,
    ) -> Dict:
        """Perform deep analysis on note content using DeepSeek."""
        cats = categories or DEFAULT_CATEGORIES
        doms = domains or DEFAULT_DOMAINS

        if custom_prompt:
            # Check if it's a full template (has {content}) or just an instruction
            if "{content}" in custom_prompt:
                # Full template - use string replace to avoid issues with JSON braces
                prompt = custom_prompt
                prompt = prompt.replace("{content}", content)
                prompt = prompt.replace("{current_date}", current_date)
                prompt = prompt.replace("{categories}", ", ".join(cats))
                prompt = prompt.replace("{domains}", ", ".join(doms))
            else:
                # Short instruction - use default template but add the instruction
                logger.info(f"Custom prompt is a short instruction: {custom_prompt[:50]}...")
                base_prompt = DEEP_ANALYZE_NOTE_PROMPT.format(
                    content=content,
                    current_date=current_date,
                    categories=", ".join(cats),
                    domains=", ".join(doms),
                )
                prompt = f"用户额外指令：{custom_prompt}\n\n{base_prompt}"
        else:
            prompt = DEEP_ANALYZE_NOTE_PROMPT.format(
                content=content,
                current_date=current_date,
                categories=", ".join(cats),
                domains=", ".join(doms),
            )

        # Debug: Log the prompt being sent
        logger.debug(f"Prompt length: {len(prompt)} chars")
        logger.debug(f"Prompt preview: {prompt[:500]}...")

        try:
            system_message = """你是一个专业的笔记分析助手。你必须严格按照用户的要求，以 JSON 格式返回分析结果。
重要规则：
1. 只返回 JSON，不要有任何其他文字、解释或对话
2. 不要问问题，直接分析提供的内容
3. 如果内容很短或不完整，仍然要返回完整的 JSON 结构，用 null 或空数组填充未知字段
4. 确保 JSON 格式正确，可以被解析"""

            result_text = self._make_request(
                messages=[
                    {"role": "system", "content": system_message},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=4096,
            )

            logger.debug(f"DeepSeek raw response: {result_text[:500]}...")
            result = self._extract_json(result_text)
            return self._normalize_deep_analysis_result(result)

        except Exception as e:
            logger.error(f"DeepSeek API error during deep analysis: {e}")
            return self._default_deep_analysis_result()

    def _normalize_deep_analysis_result(self, result: Dict) -> Dict:
        """Normalize and validate deep analysis result."""
        basic = result.get("basic_info", {})
        entities = result.get("entities", {})
        topic = result.get("topic_analysis", {})
        time_info = result.get("time_info", {})
        relation = result.get("relation_signals", {})
        features = result.get("content_features", {})
        priority = result.get("priority_assessment", {})

        return {
            "basic_info": {
                "title": basic.get("title"),
                "category": basic.get("category"),
                "subcategory": basic.get("subcategory"),
                "summary": basic.get("summary"),
            },
            "entities": {
                "persons": entities.get("persons", []) or [],
                "companies": entities.get("companies", []) or [],
                "projects": entities.get("projects", []) or [],
                "locations": entities.get("locations", []) or [],
                "technical_terms": entities.get("technical_terms", []) or [],
            },
            "topic_analysis": {
                "core_topic": topic.get("core_topic"),
                "keywords": topic.get("keywords", []) or [],
                "domain": topic.get("domain"),
            },
            "time_info": {
                "event_times": time_info.get("event_times", []) or [],
                "deadlines": time_info.get("deadlines", []) or [],
                "follow_up_dates": time_info.get("follow_up_dates", []) or [],
            },
            "relation_signals": {
                "is_follow_up": bool(relation.get("is_follow_up", False)),
                "is_summary": bool(relation.get("is_summary", False)),
                "is_standalone": bool(relation.get("is_standalone", True)),
                "reference_keywords": relation.get("reference_keywords", []) or [],
                "continuation_topic": relation.get("continuation_topic"),
            },
            "content_features": {
                "intent": features.get("intent"),
                "content_type": features.get("content_type"),
                "has_todos": bool(features.get("has_todos", False)),
                "has_questions": bool(features.get("has_questions", False)),
                "has_decisions": bool(features.get("has_decisions", False)),
                "urgency": features.get("urgency", "normal"),
            },
            "priority_assessment": {
                "priority": priority.get("priority", "medium"),
                "urgency_score": float(priority.get("urgency_score", 0.5)),
                "importance_score": float(priority.get("importance_score", 0.5)),
                "reason": priority.get("reason"),
            },
            "action_suggestions": result.get("action_suggestions", []) or [],
            "key_points": result.get("key_points", []) or [],
        }

    def _default_deep_analysis_result(self) -> Dict:
        """Return default deep analysis result on error."""
        return {
            "basic_info": {
                "title": None,
                "category": "个人杂记",
                "subcategory": None,
                "summary": None,
            },
            "entities": {
                "persons": [],
                "companies": [],
                "projects": [],
                "locations": [],
                "technical_terms": [],
            },
            "topic_analysis": {
                "core_topic": None,
                "keywords": [],
                "domain": None,
            },
            "time_info": {
                "event_times": [],
                "deadlines": [],
                "follow_up_dates": [],
            },
            "relation_signals": {
                "is_follow_up": False,
                "is_summary": False,
                "is_standalone": True,
                "reference_keywords": [],
                "continuation_topic": None,
            },
            "content_features": {
                "intent": None,
                "content_type": None,
                "has_todos": False,
                "has_questions": False,
                "has_decisions": False,
                "urgency": "normal",
            },
            "priority_assessment": {
                "priority": "medium",
                "urgency_score": 0.5,
                "importance_score": 0.5,
                "reason": None,
            },
            "action_suggestions": [],
            "key_points": [],
        }

    def _make_request(self, messages: List[Dict], max_tokens: int = 2048) -> str:
        """Make request to DeepSeek API."""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        data = {
            "model": self.model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": 0.7,
        }

        response = self.client.post(
            f"{self.base_url}/chat/completions",
            headers=headers,
            json=data,
        )
        response.raise_for_status()

        result = response.json()
        return result["choices"][0]["message"]["content"]

    def _extract_json(self, text: str) -> Dict:
        """Extract JSON from text that might contain markdown code blocks."""
        # Try to find JSON in code blocks first
        json_match = re.search(r"```(?:json)?\s*\n?([\s\S]*?)\n?```", text)
        if json_match:
            text = json_match.group(1)

        # Clean up the text
        text = text.strip()

        try:
            return json.loads(text)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON: {e}")
            logger.debug(f"Raw text: {text}")
            return {}

    async def analyze_note(
        self, content: str, context: Optional[Dict] = None, custom_prompt: Optional[str] = None
    ) -> Dict:
        """Analyze note content using DeepSeek."""
        if custom_prompt:
            # 使用自定义 prompt，并附加 JSON 输出要求
            prompt = f"""{custom_prompt}

以下是要分析的内容：
---
{content}
---

请以 JSON 格式返回分析结果，包含以下字段：
{{
    "title": "简洁的标题",
    "category": "分类（工作笔记/学习笔记/生活记录/想法灵感/会议记录/项目文档/其他）",
    "subcategory": "子分类（可选）",
    "tags": ["标签1", "标签2"],
    "summary": "内容摘要",
    "is_todo": false,
    "is_schedule": false,
    "priority": "medium",
    "entities": {{"persons": [], "dates": [], "locations": []}},
    "suggested_actions": []
}}"""
        else:
            prompt = ANALYZE_NOTE_PROMPT.format(content=content)

        try:
            system_message = "你是一个笔记分析助手。必须只返回 JSON 格式的分析结果，不要有任何其他文字。"
            result_text = self._make_request(
                messages=[
                    {"role": "system", "content": system_message},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=2048,
            )

            result = self._extract_json(result_text)
            return self._normalize_analysis_result(result)

        except Exception as e:
            logger.error(f"DeepSeek API error: {e}")
            return self._default_analysis_result()

    def _normalize_analysis_result(self, result: Dict) -> Dict:
        """Normalize and validate analysis result."""
        return {
            "title": result.get("title"),
            "category": result.get("category"),
            "subcategory": result.get("subcategory"),
            "tags": result.get("tags", []) or [],
            "summary": result.get("summary"),
            "is_todo": bool(result.get("is_todo", False)),
            "is_schedule": bool(result.get("is_schedule", False)),
            "priority": result.get("priority"),
            "entities": result.get("entities", {}),
            "suggested_actions": result.get("suggested_actions", []) or [],
        }

    def _default_analysis_result(self) -> Dict:
        """Return default analysis result on error."""
        return {
            "title": None,
            "category": "个人杂记",
            "subcategory": None,
            "tags": [],
            "summary": None,
            "is_todo": False,
            "is_schedule": False,
            "priority": "medium",
            "entities": {},
            "suggested_actions": [],
        }

    async def parse_search_query(
        self, query: str, context: Optional[Dict] = None
    ) -> Dict:
        """Parse search query using DeepSeek."""
        current_date = date.today().isoformat()
        context_str = json.dumps(context, ensure_ascii=False) if context else "None"

        prompt = SEMANTIC_SEARCH_PROMPT.format(
            query=query,
            context=context_str,
            current_date=current_date,
        )

        try:
            result_text = self._make_request(
                messages=[{"role": "user", "content": prompt}],
                max_tokens=1024,
            )

            result = self._extract_json(result_text)
            return self._normalize_search_result(result)

        except Exception as e:
            logger.error(f"DeepSeek API error: {e}")
            return self._default_search_result(query)

    def _normalize_search_result(self, result: Dict) -> Dict:
        """Normalize search query parsing result."""
        filters = result.get("filters", {})
        time_range = result.get("time_range")

        # Parse time range dates if present
        if time_range:
            for key in ["start", "end"]:
                if time_range.get(key):
                    try:
                        if isinstance(time_range[key], str):
                            time_range[key] = datetime.strptime(
                                time_range[key], "%Y-%m-%d"
                            ).date()
                    except ValueError:
                        time_range[key] = None

        return {
            "intent": result.get("intent", "General search"),
            "filters": {
                "category": filters.get("category"),
                "tags": filters.get("tags", []),
                "status": filters.get("status"),
                "is_todo": filters.get("is_todo"),
                "is_schedule": filters.get("is_schedule"),
                "priority": filters.get("priority"),
                "persons": filters.get("persons", []),
                "companies": filters.get("companies", []),
            },
            "time_range": time_range,
            "keywords": result.get("keywords", []) or [],
            "sort_by": result.get("sort_by", "created_at"),
            "order": result.get("order", "desc"),
        }

    def _default_search_result(self, query: str) -> Dict:
        """Return default search result on error."""
        return {
            "intent": "General search",
            "filters": {},
            "time_range": None,
            "keywords": query.split(),
            "sort_by": "created_at",
            "order": "desc",
        }

    async def extract_todos(self, content: str) -> List[Dict]:
        """Extract todo items from note content."""
        prompt = EXTRACT_TODOS_PROMPT.format(content=content)

        try:
            result_text = self._make_request(
                messages=[{"role": "user", "content": prompt}],
                max_tokens=1024,
            )

            result = self._extract_json(result_text)
            todos = result.get("todos", [])
            return [self._normalize_todo(todo) for todo in todos]

        except Exception as e:
            logger.error(f"DeepSeek API error: {e}")
            return []

    def _normalize_todo(self, todo: Dict) -> Dict:
        """Normalize extracted todo item."""
        due_date = todo.get("due_date")
        if due_date:
            try:
                due_date = datetime.strptime(due_date, "%Y-%m-%d").date()
            except (ValueError, TypeError):
                due_date = None

        return {
            "title": todo.get("title", "Untitled Task"),
            "description": todo.get("description"),
            "due_date": due_date,
            "priority": todo.get("priority", "medium"),
        }

    async def extract_schedule(self, content: str) -> Optional[Dict]:
        """Extract schedule information from note content."""
        current_date = date.today().isoformat()
        prompt = EXTRACT_SCHEDULE_PROMPT.format(
            content=content,
            current_date=current_date,
        )

        try:
            result_text = self._make_request(
                messages=[{"role": "user", "content": prompt}],
                max_tokens=1024,
            )

            result = self._extract_json(result_text)
            schedule = result.get("schedule")
            if schedule:
                return self._normalize_schedule(schedule)
            return None

        except Exception as e:
            logger.error(f"DeepSeek API error: {e}")
            return None

    def _normalize_schedule(self, schedule: Dict) -> Dict:
        """Normalize extracted schedule."""
        start_time = schedule.get("start_time")
        end_time = schedule.get("end_time")

        for time_key, time_val in [("start_time", start_time), ("end_time", end_time)]:
            if time_val:
                try:
                    schedule[time_key] = datetime.strptime(time_val, "%Y-%m-%d %H:%M")
                except (ValueError, TypeError):
                    try:
                        schedule[time_key] = datetime.strptime(time_val, "%Y-%m-%d")
                    except (ValueError, TypeError):
                        schedule[time_key] = None

        return {
            "title": schedule.get("title", "Untitled Event"),
            "description": schedule.get("description"),
            "start_time": schedule.get("start_time"),
            "end_time": schedule.get("end_time"),
            "location": schedule.get("location"),
            "participants": schedule.get("participants", []),
            "is_all_day": schedule.get("is_all_day", False),
        }

    async def extract_title(
        self, content: str, categories: Optional[List[str]] = None
    ) -> Dict:
        """Extract title/core topic from note content (simplified analysis)."""
        cats = categories or DEFAULT_CATEGORIES
        prompt = EXTRACT_TITLE_PROMPT.replace("{content}", content)
        prompt = prompt.replace("{categories}", ", ".join(cats))

        try:
            system_message = "你是一个笔记分析助手。只返回 JSON 格式的结果，不要有任何其他文字。"
            result_text = self._make_request(
                messages=[
                    {"role": "system", "content": system_message},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=512,
            )

            result = self._extract_json(result_text)
            return {
                "title": result.get("title"),
                "category": result.get("category", "个人杂记"),
                "summary": result.get("summary"),
            }

        except Exception as e:
            logger.error(f"DeepSeek extract_title error: {e}")
            return {
                "title": None,
                "category": "个人杂记",
                "summary": None,
            }

    async def chat(self, messages: List[Dict], max_tokens: int = 2048) -> str:
        """Send chat messages and get response."""
        try:
            return self._make_request(messages, max_tokens)
        except Exception as e:
            logger.error(f"DeepSeek chat error: {e}")
            raise
