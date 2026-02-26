"""
finetuning_service/router.py — Admin endpoints for adaptive fine-tuning
POST /admin/finetune/trigger → run analysis
GET  /admin/finetune/status  → current state
GET  /admin/finetune/weights → current RRF weights
"""
import structlog
from fastapi import APIRouter

from backend.finetuning_service.adapter import (
    run_full_analysis,
    load_weights,
    compute_document_weights,
    analyze_bad_patterns,
    detect_low_scored_documents,
)

logger = structlog.get_logger()

router = APIRouter(prefix="/admin/finetune", tags=["Admin — Fine-tuning"])


@router.post("/trigger")
async def trigger_analysis():
    """Trigger a full fine-tuning analysis across all 3 levels."""
    result = run_full_analysis()
    return result


@router.get("/status")
async def finetune_status():
    """Get current fine-tuning status and recommendations."""
    try:
        from backend.mongodb import get_mongo_db
        db = get_mongo_db()
        if db is None:
            return {"status": "mongodb_unavailable"}

        # Get latest analysis
        latest = db.finetune_analyses.find_one(
            sort=[("timestamp", -1)]
        )

        total_feedbacks = db.feedbacks.count_documents({})

        # Determine available level
        if total_feedbacks >= 100:
            available_level = 3
        elif total_feedbacks >= 50:
            available_level = 2
        elif total_feedbacks >= 10:
            available_level = 1
        else:
            available_level = 0

        return {
            "total_feedbacks": total_feedbacks,
            "available_level": available_level,
            "last_analysis": latest.get("timestamp") if latest else None,
            "levels_completed": latest.get("levels_completed", []) if latest else [],
            "status": "ok",
        }
    except Exception as e:
        logger.error("finetune_status_error", error=str(e))
        return {"status": "error", "detail": str(e)}


@router.get("/weights")
async def get_weights():
    """Get current RRF weights per document."""
    weights = load_weights()
    return {"weights": weights, "count": len(weights), "status": "ok"}
