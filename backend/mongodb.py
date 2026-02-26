"""
mongodb.py — MongoDB connection helper with graceful degradation
If MongoDB is down → returns None, the RAG continues normally.
"""
import structlog
from typing import Optional

from pymongo import MongoClient
from pymongo.database import Database

from backend.config import settings

logger = structlog.get_logger()

# ── Synchronous connection (lazy singleton) ──────────────────────────────────

_mongo_client: Optional[MongoClient] = None
_mongo_db: Optional[Database] = None


def get_mongo_db() -> Optional[Database]:
    """Return a MongoDB Database or None if connection fails."""
    global _mongo_client, _mongo_db
    if _mongo_db is not None:
        try:
            _mongo_client.admin.command("ping")
            return _mongo_db
        except Exception:
            _mongo_client = None
            _mongo_db = None

    try:
        client = MongoClient(
            settings.mongodb_url,
            serverSelectionTimeoutMS=2000,
            connectTimeoutMS=2000,
        )
        client.admin.command("ping")
        db_name = settings.mongodb_url.rsplit("/", 1)[-1].split("?")[0] or "rag_saas"
        db = client[db_name]
        _mongo_client = client
        _mongo_db = db
        logger.info("mongodb_connected", db=db_name)
        return db
    except Exception as e:
        logger.warning("mongodb_unavailable", error=str(e))
        return None


# ── Async connection (motor) ─────────────────────────────────────────────────

_async_client = None
_async_db = None


def get_async_mongo_db():
    """Return a motor AsyncIOMotorDatabase or None."""
    global _async_client, _async_db
    if _async_db is not None:
        return _async_db

    try:
        from motor.motor_asyncio import AsyncIOMotorClient
        client = AsyncIOMotorClient(
            settings.mongodb_url,
            serverSelectionTimeoutMS=2000,
            connectTimeoutMS=2000,
        )
        db_name = settings.mongodb_url.rsplit("/", 1)[-1].split("?")[0] or "rag_saas"
        _async_client = client
        _async_db = client[db_name]
        logger.info("mongodb_async_connected", db=db_name)
        return _async_db
    except Exception as e:
        logger.warning("mongodb_async_unavailable", error=str(e))
        return None
