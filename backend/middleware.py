"""
middleware.py — CORS, structured logging, Prometheus metrics
"""
import time
import structlog
from fastapi import Request, Response
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import Counter, Histogram
from starlette.middleware.base import BaseHTTPMiddleware

# ── Structured logger ─────────────────────────────────────────────────────────
structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.add_log_level,
        structlog.dev.ConsoleRenderer(),
    ]
)
logger = structlog.get_logger()

# ── Prometheus metrics ────────────────────────────────────────────────────────
REQUEST_COUNT = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ["method", "endpoint", "status"]
)
REQUEST_LATENCY = Histogram(
    "http_request_duration_seconds",
    "HTTP request latency",
    ["method", "endpoint"]
)
RAG_QUERY_COUNT = Counter(
    "rag_queries_total",
    "Total RAG queries processed"
)
INGESTION_COUNT = Counter(
    "documents_ingested_total",
    "Total documents ingested"
)


# ── Middleware class ──────────────────────────────────────────────────────────
class LoggingMetricsMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        start = time.perf_counter()

        response = await call_next(request)

        duration = time.perf_counter() - start
        endpoint = request.url.path
        method = request.method
        status = response.status_code

        REQUEST_COUNT.labels(method=method, endpoint=endpoint, status=status).inc()
        REQUEST_LATENCY.labels(method=method, endpoint=endpoint).observe(duration)

        logger.info(
            "request",
            method=method,
            path=endpoint,
            status=status,
            duration_ms=round(duration * 1000, 2),
        )
        return response


def setup_cors(app):
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],          # En production: mettre ton domaine
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
