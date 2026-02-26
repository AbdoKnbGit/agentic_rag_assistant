"""
analytics_service/aggregator.py — MongoDB aggregation queries for analytics
Provides stats, satisfaction rates, and top questions.
"""
import structlog
from datetime import datetime, timezone, timedelta
from typing import Optional

logger = structlog.get_logger()


def _get_db():
    """Get MongoDB database with graceful degradation."""
    try:
        from backend.mongodb import get_mongo_db
        return get_mongo_db()
    except Exception:
        return None


def get_stats() -> dict:
    """General statistics: total queries, avg response time, queries today."""
    db = _get_db()
    if db is None:
        return {"total_queries": 0, "avg_response_time_ms": 0, "queries_today": 0, "status": "mongodb_unavailable"}

    try:
        total = db.interactions.count_documents({})
        today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
        today_count = db.interactions.count_documents({"timestamp": {"$gte": today_start}})

        # Average response time
        pipeline = [
            {"$group": {"_id": None, "avg_time": {"$avg": "$response_time_ms"}}}
        ]
        avg_result = list(db.interactions.aggregate(pipeline))
        avg_time = round(avg_result[0]["avg_time"], 1) if avg_result and avg_result[0]["avg_time"] else 0

        return {
            "total_queries": total,
            "avg_response_time_ms": avg_time,
            "queries_today": today_count,
            "status": "ok",
        }
    except Exception as e:
        logger.error("analytics_stats_error", error=str(e))
        return {"total_queries": 0, "avg_response_time_ms": 0, "queries_today": 0, "status": "error"}


def get_satisfaction() -> dict:
    """Satisfaction rate from feedbacks collection."""
    db = _get_db()
    if db is None:
        return {"satisfaction_rate": 0, "total_feedbacks": 0, "positive": 0, "negative": 0, "status": "mongodb_unavailable"}

    try:
        total = db.feedbacks.count_documents({})
        positive = db.feedbacks.count_documents({"score": 1})
        negative = db.feedbacks.count_documents({"score": -1})

        rate = round((positive / total) * 100, 1) if total > 0 else 0

        return {
            "satisfaction_rate": rate,
            "total_feedbacks": total,
            "positive": positive,
            "negative": negative,
            "status": "ok",
        }
    except Exception as e:
        logger.error("analytics_satisfaction_error", error=str(e))
        return {"satisfaction_rate": 0, "total_feedbacks": 0, "positive": 0, "negative": 0, "status": "error"}


def get_top_questions(limit: int = 10) -> dict:
    """Most frequently asked questions from interactions."""
    db = _get_db()
    if db is None:
        return {"questions": [], "status": "mongodb_unavailable"}

    try:
        pipeline = [
            {"$group": {"_id": "$query", "count": {"$sum": 1}, "last_asked": {"$max": "$timestamp"}}},
            {"$sort": {"count": -1}},
            {"$limit": limit},
            {"$project": {"query": "$_id", "count": 1, "last_asked": 1, "_id": 0}},
        ]
        questions = list(db.interactions.aggregate(pipeline))

        # Convert datetime to string for JSON serialization
        for q in questions:
            if q.get("last_asked"):
                q["last_asked"] = q["last_asked"].isoformat()

        return {"questions": questions, "status": "ok"}
    except Exception as e:
        logger.error("analytics_top_questions_error", error=str(e))
        return {"questions": [], "status": "error"}


def get_document_scores() -> dict:
    """Average feedback scores per document source."""
    db = _get_db()
    if db is None:
        return {"documents": [], "status": "mongodb_unavailable"}

    try:
        pipeline = [
            {"$unwind": "$sources_used"},
            {"$group": {
                "_id": "$sources_used",
                "avg_score": {"$avg": "$score"},
                "count": {"$sum": 1},
            }},
            {"$sort": {"count": -1}},
            {"$project": {"source": "$_id", "avg_score": {"$round": ["$avg_score", 2]}, "count": 1, "_id": 0}},
        ]
        documents = list(db.feedbacks.aggregate(pipeline))
        return {"documents": documents, "status": "ok"}
    except Exception as e:
        logger.error("analytics_doc_scores_error", error=str(e))
        return {"documents": [], "status": "error"}
