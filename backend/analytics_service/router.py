"""
analytics_service/router.py — FastAPI routes for analytics
GET /analytics/stats, /analytics/satisfaction, /analytics/top-questions
"""
from fastapi import APIRouter, Query

from backend.analytics_service.aggregator import (
    get_stats,
    get_satisfaction,
    get_top_questions,
    get_document_scores,
)

router = APIRouter(prefix="/analytics", tags=["Analytics"])


@router.get("/stats")
async def stats():
    """General platform statistics."""
    return get_stats()


@router.get("/satisfaction")
async def satisfaction():
    """Satisfaction rate from user feedbacks."""
    return get_satisfaction()


@router.get("/top-questions")
async def top_questions(limit: int = Query(default=10, ge=1, le=100)):
    """Most frequently asked questions."""
    return get_top_questions(limit)


@router.get("/document-scores")
async def document_scores():
    """Average feedback scores per document source."""
    return get_document_scores()
