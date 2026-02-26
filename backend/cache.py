"""
cache.py — Redis Cache for RAG responses
Cache hit → simulated streaming from cache
Cache miss → normal pipeline, stores response after generation
Graceful degradation: if Redis is down, the RAG continues normally.
"""
import asyncio
import hashlib
import json
from typing import Optional, AsyncGenerator

import structlog
import redis

from backend.config import settings

logger = structlog.get_logger()

# ── Redis connection (lazy singleton) ─────────────────────────────────────────

_redis_client: Optional[redis.Redis] = None


def get_redis() -> Optional[redis.Redis]:
    """Return a Redis client or None if Redis is unavailable."""
    global _redis_client
    if _redis_client is not None:
        try:
            _redis_client.ping()
            return _redis_client
        except Exception:
            _redis_client = None

    try:
        client = redis.from_url(
            settings.redis_url,
            decode_responses=True,
            socket_connect_timeout=2,
            socket_timeout=2,
        )
        client.ping()
        _redis_client = client
        logger.info("redis_connected", url=settings.redis_url)
        return _redis_client
    except Exception as e:
        logger.warning("redis_unavailable", error=str(e))
        return None


# ── Cache key generation ──────────────────────────────────────────────────────

def cache_key(query: str, student_level: str = "", student_goal: str = "") -> str:
    """Generate a deterministic cache key from query + context."""
    raw = f"{query.strip().lower()}|{student_level}|{student_goal}"
    return f"rag:cache:{hashlib.sha256(raw.encode()).hexdigest()}"


# ── Get / Set ─────────────────────────────────────────────────────────────────

def get_cached(key: str) -> Optional[dict]:
    """Retrieve cached response data, or None on miss/error."""
    r = get_redis()
    if r is None:
        return None
    try:
        data = r.get(key)
        if data:
            logger.info("cache_hit", key=key[:30])
            return json.loads(data)
        return None
    except Exception as e:
        logger.warning("cache_get_error", error=str(e))
        return None


def set_cached(key: str, response_data: dict, ttl: Optional[int] = None) -> None:
    """Store response data in cache with TTL."""
    r = get_redis()
    if r is None:
        return
    try:
        ttl = ttl or settings.cache_ttl
        r.setex(key, ttl, json.dumps(response_data, ensure_ascii=False))
        logger.info("cache_set", key=key[:30], ttl=ttl)
    except Exception as e:
        logger.warning("cache_set_error", error=str(e))


# ── Simulated streaming from cache ───────────────────────────────────────────

async def stream_cached(cached_data: dict) -> AsyncGenerator[str, None]:
    """
    Simulate SSE streaming from cached data.
    Yields the same JSON event format as the normal pipeline so the frontend
    sees no difference between a cache hit and a cache miss.
    """
    # Status events
    yield json.dumps({"type": "status", "step": "analyzing"})
    await asyncio.sleep(0.05)
    yield json.dumps({"type": "status", "step": "retrieving"})
    await asyncio.sleep(0.05)

    # Chunks
    chunks = cached_data.get("chunks", [])
    for chunk in chunks:
        yield json.dumps(chunk)
        await asyncio.sleep(0.01)

    # Generating status
    yield json.dumps({"type": "status", "step": "generating"})
    await asyncio.sleep(0.05)

    # Stream tokens word by word
    answer = cached_data.get("answer", "")
    words = answer.split(" ")
    for i, word in enumerate(words):
        token = word if i == 0 else " " + word
        yield json.dumps({"type": "token", "data": token})
        await asyncio.sleep(0.02)

    # Done event with critic
    yield json.dumps({
        "type": "done",
        "critic": cached_data.get("critic", {}),
        "interaction_id": cached_data.get("interaction_id", ""),
        "cached": True,
    })
