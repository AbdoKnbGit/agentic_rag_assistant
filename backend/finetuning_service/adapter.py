"""
finetuning_service/adapter.py — Adaptive fine-tuning based on user feedbacks
3 levels of adaptation based on feedback count:
  Level 1 (≥10):  Adjust RRF/BM25 weights per document
  Level 2 (≥50):  Adapt system prompts based on bad-response patterns
  Level 3 (≥100): Re-index low-scored documents with adjusted parameters
"""
import structlog
from datetime import datetime, timezone
from typing import Optional

logger = structlog.get_logger()


def _get_db():
    """Get MongoDB database with graceful degradation."""
    try:
        from backend.mongodb import get_mongo_db
        return get_mongo_db()
    except Exception:
        return None


# ── Level 1: RRF Weight Adjustment (≥10 feedbacks) ──────────────────────────

def compute_document_weights() -> dict:
    """
    Compute RRF weight adjustments per document based on average feedback scores.
    Documents with avg score < 0.3 → weight reduced
    Documents with avg score > 0.7 → weight increased
    """
    db = _get_db()
    if db is None:
        return {"weights": {}, "status": "mongodb_unavailable"}

    try:
        total_feedbacks = db.feedbacks.count_documents({})
        if total_feedbacks < 10:
            return {
                "weights": {},
                "level": 0,
                "feedbacks_count": total_feedbacks,
                "message": f"Need at least 10 feedbacks (currently {total_feedbacks})",
                "status": "insufficient_data",
            }

        # Aggregate avg score per source document
        pipeline = [
            {"$unwind": "$sources_used"},
            {"$group": {
                "_id": "$sources_used",
                "avg_score": {"$avg": {"$cond": [{"$eq": ["$score", 1]}, 1.0, 0.0]}},
                "count": {"$sum": 1},
            }},
            {"$match": {"count": {"$gte": 2}}},  # At least 2 feedbacks per doc
        ]

        results = list(db.feedbacks.aggregate(pipeline))
        weights = {}
        for doc in results:
            source = doc["_id"]
            avg = doc["avg_score"]
            if avg < 0.3:
                weights[source] = {"weight": 0.5, "avg_score": round(avg, 2), "action": "reduced"}
            elif avg > 0.7:
                weights[source] = {"weight": 1.5, "avg_score": round(avg, 2), "action": "boosted"}
            else:
                weights[source] = {"weight": 1.0, "avg_score": round(avg, 2), "action": "neutral"}

        return {
            "weights": weights,
            "level": 1,
            "feedbacks_count": total_feedbacks,
            "status": "ok",
        }
    except Exception as e:
        logger.error("weight_computation_error", error=str(e))
        return {"weights": {}, "status": "error"}


def save_weights(weights: dict) -> bool:
    """Save computed weights to MongoDB for persistence across restarts."""
    db = _get_db()
    if db is None:
        return False

    try:
        db.rrf_weights.replace_one(
            {"_id": "current"},
            {
                "_id": "current",
                "weights": weights,
                "updated_at": datetime.now(timezone.utc),
            },
            upsert=True,
        )
        logger.info("weights_saved", num_docs=len(weights))
        return True
    except Exception as e:
        logger.error("weights_save_error", error=str(e))
        return False


def load_weights() -> dict:
    """Load saved weights from MongoDB."""
    db = _get_db()
    if db is None:
        return {}

    try:
        doc = db.rrf_weights.find_one({"_id": "current"})
        if doc:
            return doc.get("weights", {})
        return {}
    except Exception as e:
        logger.error("weights_load_error", error=str(e))
        return {}


# ── Level 2: Prompt Adaptation (≥50 feedbacks) ──────────────────────────────

def analyze_bad_patterns() -> dict:
    """
    Analyze patterns of bad responses by student_level.
    Returns prompt enrichment suggestions.
    """
    db = _get_db()
    if db is None:
        return {"patterns": [], "status": "mongodb_unavailable"}

    try:
        total = db.feedbacks.count_documents({})
        if total < 50:
            return {
                "patterns": [],
                "level": 1,
                "message": f"Need at least 50 feedbacks for pattern analysis (currently {total})",
                "status": "insufficient_data",
            }

        # Find queries with negative feedback, grouped by student_level
        pipeline = [
            {"$match": {"score": -1}},
            {"$lookup": {
                "from": "interactions",
                "localField": "interaction_id",
                "foreignField": "session_id",
                "as": "interaction",
            }},
            {"$group": {
                "_id": {
                    "student_level": {"$arrayElemAt": ["$interaction.student_level", 0]},
                },
                "bad_queries": {"$push": "$query"},
                "count": {"$sum": 1},
            }},
            {"$match": {"count": {"$gte": 3}}},
            {"$sort": {"count": -1}},
        ]

        patterns = list(db.feedbacks.aggregate(pipeline))
        suggestions = []

        for p in patterns:
            level = p["_id"].get("student_level", "unknown") or "unknown"
            sample_queries = p["bad_queries"][:5]
            suggestions.append({
                "student_level": level,
                "bad_response_count": p["count"],
                "sample_queries": sample_queries,
                "suggestion": f"Consider adding examples and more structured answers for {level} level students",
            })

        return {
            "patterns": suggestions,
            "level": 2,
            "feedbacks_count": total,
            "status": "ok",
        }
    except Exception as e:
        logger.error("pattern_analysis_error", error=str(e))
        return {"patterns": [], "status": "error"}


# ── Level 3: Re-indexation (≥100 feedbacks) ──────────────────────────────────

def detect_low_scored_documents() -> dict:
    """
    Detect documents with consistently low feedback scores (avg < 0.2).
    Suggests re-ingestion with adjusted chunk_size and overlap.
    """
    db = _get_db()
    if db is None:
        return {"documents": [], "status": "mongodb_unavailable"}

    try:
        total = db.feedbacks.count_documents({})
        if total < 100:
            return {
                "documents": [],
                "level": 2,
                "message": f"Need at least 100 feedbacks for re-indexation analysis (currently {total})",
                "status": "insufficient_data",
            }

        pipeline = [
            {"$unwind": "$sources_used"},
            {"$group": {
                "_id": "$sources_used",
                "avg_score": {"$avg": {"$cond": [{"$eq": ["$score", 1]}, 1.0, 0.0]}},
                "count": {"$sum": 1},
            }},
            {"$match": {"avg_score": {"$lt": 0.2}, "count": {"$gte": 5}}},
            {"$sort": {"avg_score": 1}},
        ]

        low_docs = list(db.feedbacks.aggregate(pipeline))
        recommendations = []

        for doc in low_docs:
            source = doc["_id"]
            recommendations.append({
                "source": source,
                "avg_score": round(doc["avg_score"], 2),
                "feedback_count": doc["count"],
                "recommendation": "re-ingest",
                "suggested_chunk_size": 400,  # Smaller chunks for better precision
                "suggested_overlap": 150,     # More overlap for better context
            })

        return {
            "documents": recommendations,
            "level": 3,
            "feedbacks_count": total,
            "status": "ok",
        }
    except Exception as e:
        logger.error("reindexation_analysis_error", error=str(e))
        return {"documents": [], "status": "error"}


# ── Full Analysis (triggered by admin) ───────────────────────────────────────

def run_full_analysis() -> dict:
    """Run all 3 levels of analysis and return combined results."""
    db = _get_db()
    if db is None:
        return {"status": "mongodb_unavailable"}

    total = db.feedbacks.count_documents({})

    result = {
        "feedbacks_count": total,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "levels_completed": [],
    }

    # Level 1: Weights
    if total >= 10:
        weight_result = compute_document_weights()
        if weight_result.get("weights"):
            save_weights(weight_result["weights"])
        result["weights"] = weight_result
        result["levels_completed"].append(1)

    # Level 2: Patterns
    if total >= 50:
        pattern_result = analyze_bad_patterns()
        result["patterns"] = pattern_result
        result["levels_completed"].append(2)

    # Level 3: Re-indexation
    if total >= 100:
        reindex_result = detect_low_scored_documents()
        result["reindexation"] = reindex_result
        result["levels_completed"].append(3)

    if not result["levels_completed"]:
        result["message"] = f"Need at least 10 feedbacks to start analysis (currently {total})"

    result["status"] = "ok"

    # Save analysis result
    try:
        db.finetune_analyses.insert_one({
            **result,
            "_id": None,  # Let MongoDB generate
        })
    except Exception:
        pass  # Non-critical

    logger.info("finetune_analysis_complete", levels=result["levels_completed"], feedbacks=total)
    return result
