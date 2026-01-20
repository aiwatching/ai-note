"""Search API routes."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..database import get_db
from ..models.user import User
from ..schemas.search_schema import SearchQuery, SearchResponse
from ..services.search_service import SearchService

router = APIRouter()

DEFAULT_USER_ID = 1


def get_or_create_default_user(db: Session) -> int:
    """Get or create default user for MVP."""
    user = db.query(User).filter(User.id == DEFAULT_USER_ID).first()
    if not user:
        user = User(id=DEFAULT_USER_ID, username="default_user")
        db.add(user)
        db.commit()
    return DEFAULT_USER_ID


@router.post("", response_model=SearchResponse)
async def search_notes(
    query: SearchQuery,
    db: Session = Depends(get_db),
):
    """
    Perform conversational search on notes.

    The search query is analyzed by AI to understand intent and extract
    relevant filters. Results include matching notes and suggested actions.

    Examples:
    - "有哪些需求问题还没确定？" - Search for unconfirmed requirement issues
    - "上周和客户 A 相关的问题" - Search for Client A issues from last week
    - "我学了哪些关于 Python 的知识？" - Search for Python learning notes
    - "本周需要开哪些会？" - Search for meetings this week
    """
    user_id = get_or_create_default_user(db)
    service = SearchService(db)

    response = await service.search(user_id, query)
    return response
