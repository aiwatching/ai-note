"""Grok AI service implementation (xAI)."""
import json
import re
from datetime import date, datetime
from typing import Dict, List, Optional

import httpx
from loguru import logger

from .base import AIServiceBase
from .prompts import (
    DEFAULT_CATEGORIES,
    EXTRACT_TITLE_PROMPT,
)


class GrokService(AIServiceBase):
    """xAI Grok API implementation (OpenAI-compatible)."""

    def __init__(
        self,
        api_key: str,
        model: str = "grok-3-latest",
        base_url: str = "https://api.x.ai/v1",
    ):
        """
        Initialize Grok service.

        Args:
            api_key: xAI API key
            model: Model to use
            base_url: API base URL
        """
        self.api_key = api_key
        self.model = model
        self.base_url = base_url
        self.client = httpx.Client(timeout=60.0)

    def _make_request(self, messages: List[Dict], max_tokens: int = 2048) -> str:
        """Make request to Grok API (OpenAI-compatible)."""
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
        json_match = re.search(r"```(?:json)?\s*\n?([\s\S]*?)\n?```", text)
        if json_match:
            text = json_match.group(1)
        text = text.strip()
        try:
            return json.loads(text)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON: {e}")
            return {}

    async def chat(self, messages: List[Dict], max_tokens: int = 2048) -> str:
        """Send chat messages and get response."""
        try:
            return self._make_request(messages, max_tokens)
        except Exception as e:
            logger.error(f"Grok chat error: {e}")
            raise

    async def extract_title(
        self, content: str, categories: Optional[List[str]] = None
    ) -> Dict:
        """Extract title from note content."""
        cats = categories or DEFAULT_CATEGORIES
        prompt = EXTRACT_TITLE_PROMPT.replace("{content}", content)
        prompt = prompt.replace("{categories}", ", ".join(cats))

        try:
            result_text = self._make_request(
                messages=[{"role": "user", "content": prompt}],
                max_tokens=512,
            )
            result = self._extract_json(result_text)
            return {
                "title": result.get("title"),
                "category": result.get("category", "个人杂记"),
                "summary": result.get("summary"),
            }
        except Exception as e:
            logger.error(f"Grok extract_title error: {e}")
            return {"title": None, "category": "个人杂记", "summary": None}

    # Implement required abstract methods with basic implementations
    async def deep_analyze_note(self, content: str, current_date: str,
                                categories: Optional[List[str]] = None,
                                domains: Optional[List[str]] = None,
                                custom_prompt: Optional[str] = None) -> Dict:
        """Basic implementation."""
        return await self.extract_title(content, categories)

    async def analyze_note(self, content: str, context: Optional[Dict] = None,
                          custom_prompt: Optional[str] = None) -> Dict:
        """Basic implementation."""
        return await self.extract_title(content)

    async def parse_search_query(self, query: str, context: Optional[Dict] = None) -> Dict:
        """Basic implementation."""
        return {"intent": "search", "keywords": query.split(), "filters": {}}

    async def extract_todos(self, content: str) -> List[Dict]:
        """Basic implementation."""
        return []

    async def extract_schedule(self, content: str) -> Optional[Dict]:
        """Basic implementation."""
        return None
