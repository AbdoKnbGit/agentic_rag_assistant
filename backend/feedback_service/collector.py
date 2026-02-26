"""
collector.py — Feedback storage service
Stores user feedback (👍/👎) to MongoDB with graceful degradation.
"""
import structlog
from datetime import datetime, timezone
from typing import Optional, List

from pydantic import BaseModel

logger = structlog.get_logger()


# ── Pydantic models ──────────────────────────────────────────────────────────

class FeedbackPayload(BaseModel):
    interaction_id: str
    score: int  # 1 or -1
    query: str
    answer: str
    sources_used: List[str] = []


# ── Storage ──────────────────────────────────────────────────────────────────

def save_feedback(payload: FeedbackPayload) -> dict:
    """Save feedback to MongoDB. Falls back to structlog if MongoDB is down."""
    doc = {
        "interaction_id": payload.interaction_id,
        "score": payload.score,
        "query": payload.query,
        "answer": payload.answer[:2000],
        "sources_used": payload.sources_used,
        "timestamp": datetime.now(timezone.utc),
    }

    try:
        from backend.mongodb import get_mongo_db
        db = get_mongo_db()
        if db is not None:
            result = db.feedbacks.insert_one(doc)
            logger.info(
                "feedback_saved",
                interaction_id=payload.interaction_id,
                score=payload.score,
                mongo_id=str(result.inserted_id),
            )
            return {"status": "saved", "id": str(result.inserted_id)}
        else:
            logger.warning(
                "feedback_fallback_log",
                interaction_id=payload.interaction_id,
                score=payload.score,
                query=payload.query[:100],
            )
            return {"status": "logged"}
    except Exception as e:
        logger.error("feedback_save_error", error=str(e))
        logger.warning(
            "feedback_fallback_log",
            interaction_id=payload.interaction_id,
            score=payload.score,
            query=payload.query[:100],
        )
        return {"status": "logged"}
