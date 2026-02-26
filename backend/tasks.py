"""
tasks.py — Celery tasks for async RAG processing
Runs the RAG pipeline in background workers with retry logic.
"""
import structlog
from celery import Task
from celery.exceptions import SoftTimeLimitExceeded

from backend.celery_app import app

logger = structlog.get_logger()


class RAGTask(Task):
    """Base task class with structured logging."""
    autoretry_for = (Exception,)
    retry_kwargs = {"max_retries": 3}
    retry_backoff = True
    retry_backoff_max = 60


@app.task(base=RAGTask, bind=True, name="backend.tasks.run_rag_pipeline")
def run_rag_pipeline(self, query: str, source_filter=None, data_file=None,
                     chat_history=None, reasoning=False):
    """Execute the RAG pipeline synchronously in a Celery worker."""
    try:
        logger.info("celery_task_start", task_id=self.request.id, query=query[:80])

        import asyncio
        from backend.graph import run_query
        # run_query est maintenant asynchrone, on utilise asyncio.run pour l'exécuter dans le worker
        result = asyncio.run(run_query(
            query=query,
            source_filter=source_filter,
            data_file=data_file,
            chat_history=chat_history or [],
            reasoning=reasoning,
        ))

        logger.info("celery_task_done", task_id=self.request.id)
        return result

    except SoftTimeLimitExceeded:
        logger.error("celery_task_timeout", task_id=self.request.id, query=query[:80])
        return {"error": "Task timed out after 3 minutes", "query": query}
    except Exception as e:
        logger.error("celery_task_error", task_id=self.request.id, error=str(e))
        raise


@app.task(base=RAGTask, bind=True, name="backend.tasks.run_rag_pipeline_priority")
def run_rag_pipeline_priority(self, query: str, source_filter=None, data_file=None,
                               chat_history=None, reasoning=False):
    """Priority RAG pipeline for student_goal='examen' — routed to priority queue."""
    return run_rag_pipeline(
        query=query,
        source_filter=source_filter,
        data_file=data_file,
        chat_history=chat_history,
        reasoning=reasoning,
    )
