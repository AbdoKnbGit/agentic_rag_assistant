"""
main.py — FastAPI Application
Agentic RAG SaaS — Entry Point
"""
import os
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import JSONResponse, StreamingResponse
from prometheus_client import make_asgi_app
import asyncio
from backend.config import settings
from backend.middleware import setup_cors, LoggingMetricsMiddleware
from backend.ingestion_service.router import router as ingest_router
from backend.retrieval_service.router import router as retrieval_router
from backend.feedback_service.router import router as feedback_router
from backend.analytics_service.router import router as analytics_router
from backend.finetuning_service.router import router as finetuning_router

# ── App ───────────────────────────────────────────────────────────────────────

app = FastAPI(
    title="Agentic RAG SaaS",
    description="API pédagogique RAG avec pipeline LangGraph et retrieval hybride.",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# ── Middleware ─────────────────────────────────────────────────────────────────
setup_cors(app)
app.add_middleware(LoggingMetricsMiddleware)

# ── Prometheus metrics endpoint ───────────────────────────────────────────────
metrics_app = make_asgi_app()
app.mount("/metrics", metrics_app)

# ── Routers ───────────────────────────────────────────────────────────────────
app.include_router(ingest_router)
app.include_router(retrieval_router)
app.include_router(feedback_router)
app.include_router(analytics_router)
app.include_router(finetuning_router)

# ── Upload dir ────────────────────────────────────────────────────────────────
Path(settings.upload_dir).mkdir(parents=True, exist_ok=True)


# ── Query endpoint (main RAG) ─────────────────────────────────────────────────
from pydantic import BaseModel
from typing import Optional, List
from fastapi.responses import JSONResponse


class ChatMessage(BaseModel):
    role: str
    content: str


class QueryRequest(BaseModel):
    query: str
    source_filter: Optional[List[str]] = None
    data_file: Optional[str] = None
    chat_history: Optional[List[ChatMessage]] = None
    reasoning: bool = False


@app.post("/query", tags=["RAG"])
async def query_rag(request: QueryRequest):
    """
    Pipeline RAG complet en streaming :
    analyze → retrieve → [data] → generate (stream) → réponse
    """
    from backend.graph import run_query_stream
    from backend.middleware import RAG_QUERY_COUNT
    RAG_QUERY_COUNT.inc()

    async def event_generator():
        try:
            history = [
                {"role": m.role, "content": m.content}
                for m in (request.chat_history or [])
            ]
            async for token in run_query_stream(
                query=request.query,
                source_filter=request.source_filter,
                data_file=request.data_file,
                chat_history=history,
                reasoning=request.reasoning,
            ):
                # Format SSE : "data: <token>\n\n"
                yield f"data: {token}\n\n"

            yield "data: [DONE]\n\n"

        except Exception as e:
            import traceback
            traceback.print_exc()
            yield f"data: [ERROR] {str(e)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )


# ── Health check ──────────────────────────────────────────────────────────────
@app.get("/health", tags=["System"])
async def health():
    return {"status": "ok", "model": settings.llm_model}


@app.get("/", tags=["System"])
async def root():
    return {
        "service": "Agentic RAG SaaS",
        "docs": "/docs",
        "health": "/health",
        "metrics": "/metrics",
    }


# ── Async Query (Celery) ──────────────────────────────────────────────────────

class AsyncQueryRequest(BaseModel):
    query: str
    source_filter: Optional[List[str]] = None
    data_file: Optional[str] = None
    chat_history: Optional[List[ChatMessage]] = None
    reasoning: bool = False
    student_goal: Optional[str] = None


@app.post("/query/async", tags=["RAG"])
async def query_rag_async(request: AsyncQueryRequest):
    """Submit a RAG query for async processing via Celery."""
    from backend.tasks import run_rag_pipeline, run_rag_pipeline_priority

    history = [
        {"role": m.role, "content": m.content}
        for m in (request.chat_history or [])
    ]

    task_fn = run_rag_pipeline_priority if request.student_goal == "examen" else run_rag_pipeline
    task = task_fn.delay(
        query=request.query,
        source_filter=request.source_filter,
        data_file=request.data_file,
        chat_history=history,
        reasoning=request.reasoning,
    )

    return {"task_id": task.id, "status": "queued"}


@app.get("/query/status/{task_id}", tags=["RAG"])
async def query_status(task_id: str):
    """Check the status of an async RAG query."""
    from backend.celery_app import app as celery_app
    result = celery_app.AsyncResult(task_id)

    response = {"task_id": task_id, "status": result.status}
    if result.ready():
        response["result"] = result.result
    return response


# ── Run ───────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "backend.main:app",
        host=settings.backend_host,
        port=settings.backend_port,
        reload=settings.debug,
    )
