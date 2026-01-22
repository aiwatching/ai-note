"""Abstract base class for AI services."""
from abc import ABC, abstractmethod
from typing import Dict, List, Optional


class AIServiceBase(ABC):
    """AI service abstract base class."""

    @abstractmethod
    async def deep_analyze_note(
        self,
        content: str,
        current_date: str,
        categories: Optional[List[str]] = None,
        domains: Optional[List[str]] = None,
        custom_prompt: Optional[str] = None,
    ) -> Dict:
        """
        Perform deep analysis on note content.

        Args:
            content: Raw note content
            current_date: Current date string for relative time conversion
            categories: Custom category list
            domains: Custom domain list
            custom_prompt: Optional custom prompt to override default

        Returns:
            Comprehensive analysis result with all extracted information
        """
        pass

    @abstractmethod
    async def analyze_note(
        self, content: str, context: Optional[Dict] = None, custom_prompt: Optional[str] = None
    ) -> Dict:
        """
        Analyze note content and extract structured information.

        Args:
            content: Raw note content
            context: Additional context (user preferences, historical categories, etc.)
            custom_prompt: Custom prompt for analysis (if provided, will be used instead of default)

        Returns:
            dict: {
                'title': str,
                'category': str,
                'subcategory': str,
                'tags': List[str],
                'summary': str,
                'is_todo': bool,
                'is_schedule': bool,
                'priority': str,
                'entities': {
                    'persons': List[str],
                    'dates': List[str],
                    'locations': List[str]
                },
                'suggested_actions': List[Dict]
            }
        """
        pass

    @abstractmethod
    async def parse_search_query(
        self, query: str, context: Optional[Dict] = None
    ) -> Dict:
        """
        Parse natural language search query into structured parameters.

        Args:
            query: Natural language query
            context: Search context (previous queries, filters, etc.)

        Returns:
            dict: {
                'intent': str,
                'filters': Dict,
                'keywords': List[str],
                'time_range': Optional[Dict],
                'sort_by': str,
                'order': str
            }
        """
        pass

    @abstractmethod
    async def extract_todos(self, content: str) -> List[Dict]:
        """
        Extract todo items from note content.

        Args:
            content: Note content

        Returns:
            List of todo items with title, due_date, priority
        """
        pass

    @abstractmethod
    async def extract_schedule(self, content: str) -> Optional[Dict]:
        """
        Extract schedule/meeting information from note content.

        Args:
            content: Note content

        Returns:
            Schedule info or None if no schedule found
        """
        pass

    @abstractmethod
    async def extract_title(
        self, content: str, categories: Optional[List[str]] = None
    ) -> Dict:
        """
        Extract title/core topic from note content (simplified analysis).

        Args:
            content: Note content
            categories: Optional list of categories

        Returns:
            dict: {
                'title': str,
                'category': str,
                'summary': str
            }
        """
        pass
