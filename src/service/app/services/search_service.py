"""Search business logic service."""
from datetime import datetime
from typing import List, Optional

from loguru import logger
from sqlalchemy.orm import Session

from ..ai.factory import AIServiceFactory
from ..config import get_settings
from ..models.note import Note
from ..schemas.search_schema import (
    ParsedSearchQuery,
    SearchQuery,
    SearchResponse,
    SearchResult,
    SearchSuggestion,
)
from .note_service import NoteService


class SearchService:
    """Service for search-related operations."""

    def __init__(self, db: Session):
        """
        Initialize search service.

        Args:
            db: Database session
        """
        self.db = db
        self.note_service = NoteService(db)
        self._ai_service = None

    @property
    def ai_service(self):
        """Lazy load AI service based on configured provider."""
        if self._ai_service is None:
            settings = get_settings()
            service_type = settings.ai_service

            if service_type == "deepseek" and settings.deepseek_api_key:
                self._ai_service = AIServiceFactory.create(
                    "deepseek",
                    api_key=settings.deepseek_api_key,
                    model=settings.deepseek_model,
                    base_url=settings.deepseek_base_url,
                )
            elif service_type == "claude" and settings.claude_api_key:
                self._ai_service = AIServiceFactory.create(
                    "claude",
                    api_key=settings.claude_api_key,
                    model=settings.claude_model,
                )

        return self._ai_service

    async def search(
        self, user_id: int, query: SearchQuery
    ) -> SearchResponse:
        """
        Perform conversational search.

        Args:
            user_id: User ID
            query: Search query

        Returns:
            Search response with results and suggestions
        """
        # Parse the query using AI
        parsed_query = await self._parse_query(query.query, query.context)

        # Execute search
        notes = await self._execute_search(user_id, parsed_query)

        # Build results
        results = self._build_results(notes, parsed_query.keywords)

        # Generate suggestions
        suggestions = self._generate_suggestions(notes, parsed_query)

        return SearchResponse(
            intent=parsed_query.intent,
            results=results,
            suggestions=suggestions,
            total=len(results),
        )

    async def _parse_query(
        self, query: str, context: Optional[dict] = None
    ) -> ParsedSearchQuery:
        """
        Parse natural language query into structured parameters.

        Args:
            query: Natural language query
            context: Additional context

        Returns:
            Parsed search query
        """
        if self.ai_service:
            try:
                parsed = await self.ai_service.parse_search_query(query, context)
                return ParsedSearchQuery(
                    intent=parsed.get("intent", "General search"),
                    filters=parsed.get("filters", {}),
                    time_range=parsed.get("time_range"),
                    keywords=parsed.get("keywords", []),
                    sort_by=parsed.get("sort_by", "created_at"),
                    order=parsed.get("order", "desc"),
                )
            except Exception as e:
                logger.error(f"Query parsing failed: {e}")

        # Fallback to simple keyword extraction
        return ParsedSearchQuery(
            intent="General search",
            keywords=query.split(),
        )

    async def _execute_search(
        self, user_id: int, parsed_query: ParsedSearchQuery
    ) -> List[Note]:
        """
        Execute search with parsed parameters.

        Args:
            user_id: User ID
            parsed_query: Parsed search parameters

        Returns:
            List of matching notes
        """
        # Extract filters
        filters = parsed_query.filters
        time_range = parsed_query.time_range

        start_date = None
        end_date = None
        if time_range:
            start_date = time_range.start
            end_date = time_range.end

        # Convert dates to datetime if needed
        if start_date:
            start_date = datetime.combine(start_date, datetime.min.time())
        if end_date:
            end_date = datetime.combine(end_date, datetime.max.time())

        return self.note_service.search_notes(
            user_id=user_id,
            keywords=parsed_query.keywords,
            category=filters.category if filters else None,
            tags=filters.tags if filters else None,
            start_date=start_date,
            end_date=end_date,
        )

    def _build_results(
        self, notes: List[Note], keywords: List[str]
    ) -> List[SearchResult]:
        """
        Build search results from notes.

        Args:
            notes: List of notes
            keywords: Search keywords for highlighting

        Returns:
            List of search results
        """
        results = []
        for i, note in enumerate(notes):
            # Calculate simple relevance score based on position
            relevance_score = max(0.5, 1.0 - (i * 0.05))

            # Generate highlight from content
            highlight = self._generate_highlight(note.raw_content, keywords)

            results.append(
                SearchResult(
                    note_id=note.id,
                    title=note.title,
                    summary=note.summary,
                    category=note.category,
                    tags=note.tags,
                    relevance_score=relevance_score,
                    highlight=highlight,
                    created_at=note.created_at.isoformat(),
                )
            )

        return results

    def _generate_highlight(
        self, content: str, keywords: List[str], max_length: int = 150
    ) -> str:
        """
        Generate highlighted excerpt from content.

        Args:
            content: Note content
            keywords: Keywords to highlight
            max_length: Maximum highlight length

        Returns:
            Highlighted excerpt
        """
        if not content:
            return ""

        content_lower = content.lower()

        # Find the best position to start the highlight
        best_pos = 0
        for keyword in keywords:
            pos = content_lower.find(keyword.lower())
            if pos != -1:
                best_pos = max(0, pos - 30)
                break

        # Extract excerpt
        excerpt = content[best_pos : best_pos + max_length]
        if best_pos > 0:
            excerpt = "..." + excerpt
        if best_pos + max_length < len(content):
            excerpt = excerpt + "..."

        return excerpt

    def _generate_suggestions(
        self, notes: List[Note], parsed_query: ParsedSearchQuery
    ) -> List[SearchSuggestion]:
        """
        Generate action suggestions based on search results.

        Args:
            notes: Search results
            parsed_query: Parsed query

        Returns:
            List of suggestions
        """
        suggestions = []

        # Suggest creating todo if results have pending items
        todo_notes = [n for n in notes if n.is_todo]
        if todo_notes:
            suggestions.append(
                SearchSuggestion(
                    action="create_todo",
                    description=f"Create todos from {len(todo_notes)} notes with task items",
                    data={"note_ids": [n.id for n in todo_notes]},
                )
            )

        # Suggest creating schedule if results have meeting info
        schedule_notes = [n for n in notes if n.is_schedule]
        if schedule_notes:
            suggestions.append(
                SearchSuggestion(
                    action="create_schedule",
                    description=f"Create schedule from {len(schedule_notes)} notes with meeting info",
                    data={"note_ids": [n.id for n in schedule_notes]},
                )
            )

        # Suggest refining search if too many results
        if len(notes) > 10:
            suggestions.append(
                SearchSuggestion(
                    action="refine_search",
                    description="Try adding more specific keywords or time range to narrow results",
                    data=None,
                )
            )

        return suggestions
