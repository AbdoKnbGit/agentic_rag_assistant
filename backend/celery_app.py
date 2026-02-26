"""
celery_app.py — Celery application configuration
Uses Redis as broker for async RAG task processing.
"""
from celery import Celery
from backend.config import settings

app = Celery(
    "rag_worker",
    broker=settings.celery_broker_url,
    backend=settings.celery_broker_url,
    include=["backend.tasks"],
)

# ── Configuration ─────────────────────────────────────────────────────────────

app.conf.update(
    # Serialization
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",

    # Timeouts
    task_time_limit=180,      # 3 minutes hard limit
    task_soft_time_limit=170,  # Soft limit triggers SoftTimeLimitExceeded

    # Results
    result_expires=3600,  # Results expire after 1 hour

    # Task routing for priority queues
    task_routes={
        "backend.tasks.run_rag_pipeline_priority": {"queue": "priority"},
    },

    # Worker
    worker_prefetch_multiplier=1,
    worker_concurrency=2,
)
