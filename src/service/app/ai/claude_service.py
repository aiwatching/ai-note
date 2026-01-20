"""Claude AI service implementation."""
import json
import re
from datetime import date, datetime
from typing import Dict, List, Optional

import anthropic
from loguru import logger

from .base import AIServiceBase
from .prompts import (
    ANALYZE_NOTE_PROMPT,
    SEMANTIC_SEARCH_PROMPT,
    EXTRACT_TODOS_PROMPT,
    EXTRACT_SCHEDULE_PROMPT,
)


class ClaudeService(AIServiceBase):
    """Claude API implementation of AI service."""

    def __init__(self, api_key: str, model: str = "claude-sonnet-4-20250514"):
        """
        Initialize Claude service.

        Args:
            api_key: Anthropic API key
            model: Claude model to use
        """
        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = model

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
        self, content: str, context: Optional[Dict] = None
    ) -> Dict:
        """Analyze note content using Claude."""
        prompt = ANALYZE_NOTE_PROMPT.format(content=content)

        try:
            message = self.client.messages.create(
                model=self.model,
                max_tokens=2048,
                messages=[{"role": "user", "content": prompt}],
            )

            result_text = message.content[0].text
            result = self._extract_json(result_text)

            # Normalize and validate the result
            return self._normalize_analysis_result(result)

        except anthropic.APIError as e:
            logger.error(f"Claude API error: {e}")
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
        """Parse search query using Claude."""
        current_date = date.today().isoformat()
        context_str = json.dumps(context, ensure_ascii=False) if context else "None"

        prompt = SEMANTIC_SEARCH_PROMPT.format(
            query=query,
            context=context_str,
            current_date=current_date,
        )

        try:
            message = self.client.messages.create(
                model=self.model,
                max_tokens=1024,
                messages=[{"role": "user", "content": prompt}],
            )

            result_text = message.content[0].text
            result = self._extract_json(result_text)

            return self._normalize_search_result(result)

        except anthropic.APIError as e:
            logger.error(f"Claude API error: {e}")
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
                        # Try to parse as date
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
            message = self.client.messages.create(
                model=self.model,
                max_tokens=1024,
                messages=[{"role": "user", "content": prompt}],
            )

            result_text = message.content[0].text
            result = self._extract_json(result_text)

            todos = result.get("todos", [])
            return [self._normalize_todo(todo) for todo in todos]

        except anthropic.APIError as e:
            logger.error(f"Claude API error: {e}")
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
            message = self.client.messages.create(
                model=self.model,
                max_tokens=1024,
                messages=[{"role": "user", "content": prompt}],
            )

            result_text = message.content[0].text
            result = self._extract_json(result_text)

            schedule = result.get("schedule")
            if schedule:
                return self._normalize_schedule(schedule)
            return None

        except anthropic.APIError as e:
            logger.error(f"Claude API error: {e}")
            return None

    def _normalize_schedule(self, schedule: Dict) -> Dict:
        """Normalize extracted schedule."""
        start_time = schedule.get("start_time")
        end_time = schedule.get("end_time")

        # Parse datetime strings
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
