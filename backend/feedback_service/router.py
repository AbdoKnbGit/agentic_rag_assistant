"""
feedback_service/router.py — FastAPI routes for user feedback
POST /feedback → stores feedback from 👍/👎 buttons
"""
import structlog
from fastapi import APIRouter

from backend.feedback_service.collector import FeedbackPayload, save_feedback

logger = structlog.get_logger()

router = APIRouter(tags=["Feedback"])


@router.post("/feedback")
async def submit_feedback(payload: FeedbackPayload):
    """Receives 👍/👎 feedback from the frontend."""
    if payload.score not in (1, -1):
        return {"status": "error", "detail": "score must be 1 or -1"}

    result = save_feedback(payload)
    return result
