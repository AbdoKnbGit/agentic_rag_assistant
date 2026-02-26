"""
config.py — Configuration centrale via pydantic-settings
Lit automatiquement le fichier .env
"""
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # LLM - NVIDIA API
    llm_model: str = "qwen/qwen3-235b-a22b"
    nvidia_api_key: str = ""
    llm_temperature: float = 0.2
    llm_top_p: float = 0.7
    llm_max_tokens: int = 8192

    # Embeddings
    embed_model: str = "BAAI/bge-small-en-v1.5"

    # Qdrant
    qdrant_host: str = "qdrant"  # Nom du service Docker
    qdrant_port: int = 6333
    qdrant_collection: str = "rag_docs"

    # Backend
    backend_host: str = "0.0.0.0"
    backend_port: int = 8000
    debug: bool = True

    # Chunking & Retrieval
    chunk_size: int = 600
    chunk_overlap: int = 100
    top_k: int = 6

    # Upload
    upload_dir: str = "./uploads"
    max_file_size_mb: int = 50
    
    # Critic / Évaluation
    critic_enabled: bool = True  # Activer/désactiver le critic
    critic_temperature: float = 0.0

    # Redis Cache
    redis_url: str = "redis://redis:6379/0"
    cache_ttl: int = 3600  # 1 hour default

    # MongoDB
    mongodb_url: str = "mongodb://mongodb:27017/rag_saas"

    # Celery
    celery_broker_url: str = "redis://redis:6379/1"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
        extra = "ignore"  # Ignorer les variables inconnues


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()