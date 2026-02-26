"""
retrieval_service/retriever_optimized.py
Hybrid retrieval optimisé : BM25 + Qdrant, async, LRU cache, pré-tokenisation.
"""
import asyncio
import hashlib
import time
from pathlib import Path
from typing import List, Tuple, Optional, Dict
import structlog
from rank_bm25 import BM25Okapi
from qdrant_client import QdrantClient
from qdrant_client.models import Filter, FieldCondition, MatchValue
from functools import lru_cache

from backend.config import settings
from backend.ingestion_service.ingestor import embed_texts, get_qdrant

logger = structlog.get_logger()

# ── Cache LRU avec TTL ────────────────────────────────────────────────────────
class TTLCache:
    def __init__(self, maxsize=100, ttl=300):
        self.cache: Dict[str, dict] = {}
        self.maxsize = maxsize
        self.ttl = ttl

    def _evict(self):
        if len(self.cache) >= self.maxsize:
            oldest = min(self.cache, key=lambda k: self.cache[k]["ts"])
            del self.cache[oldest]

    def get(self, key):
        entry = self.cache.get(key)
        if entry and time.time() - entry["ts"] < self.ttl:
            return entry["data"]
        if key in self.cache:
            del self.cache[key]
        return None

    def set(self, key, data):
        self._evict()
        self.cache[key] = {"ts": time.time(), "data": data}

_retrieval_cache = TTLCache(maxsize=100, ttl=300)

def _cache_key(query: str, top_k: int, source_filter=None) -> str:
    sf = '|'.join(sorted(source_filter)) if source_filter else ''
    return hashlib.md5(f"{query}|{top_k}|{sf}".encode()).hexdigest()

# ── Helpers ───────────────────────────────────────────────────────────────────
def _reciprocal_rank_fusion(lists: List[List[Tuple[str, float]]], k: int = 60) -> List[Tuple[str, float]]:
    scores: Dict[str, float] = {}
    for ranked_list in lists:
        for rank, (doc_id, _) in enumerate(ranked_list):
            scores[doc_id] = scores.get(doc_id, 0) + 1 / (k + rank + 1)
    return sorted(scores.items(), key=lambda x: x[1], reverse=True)

@lru_cache(maxsize=None)
def _tokenize(text: str) -> List[str]:
    return text.lower().split()

# ── Hybrid Retriever optimisé ───────────────────────────────────────────────
class HybridRetrieverOptimized:
    def __init__(self):
        self.client: QdrantClient = get_qdrant()
        self.pre_tokenized_docs: dict[str, list[str]] = {}
        logger.info(
            "qdrant_client_ready",
            has_query_points=hasattr(self.client, "query_points"),
            has_search=hasattr(self.client, "search"),
        )

    # ── Chunking optimisé ───────────────────────────────────────────────
    def chunk_text(self, text: str, chunk_size: int = 300, overlap: int = 50) -> list[str]:
        """
        Découpe le texte en chunks de longueur `chunk_size` tokens avec un overlap.
        """
        tokens = _tokenize(text)
        chunks = []
        for i in range(0, len(tokens), chunk_size - overlap):
            chunk_tokens = tokens[i:i + chunk_size]
            if chunk_tokens:
                chunks.append(" ".join(chunk_tokens))
        return chunks

    # ── Vector search async ─────────────────────────────────────────────
    async def _vector_search(self, query: str, top_k: int, source_filter: Optional[list[str]] = None):
        query_vec = embed_texts([query])[0]

        filt = None
        if source_filter:
            if len(source_filter) == 1:
                filt = Filter(
                    must=[FieldCondition(key="source", match=MatchValue(value=source_filter[0]))]
                )
            else:
                filt = Filter(
                    should=[FieldCondition(key="source", match=MatchValue(value=src)) for src in source_filter]
                )

        # Qdrant fallback optimisé
        if hasattr(self.client, "query_points"):
            points = self.client.query_points(
                collection_name=settings.qdrant_collection,
                query=query_vec,
                limit=top_k * 3,
                query_filter=filt,
                with_payload=True,
            ).points
        elif hasattr(self.client, "search"):
            points = self.client.search(
                collection_name=settings.qdrant_collection,
                query_vector=query_vec,
                limit=top_k * 3,
                query_filter=filt,
                with_payload=True,
            )
        else:
            logger.warning("qdrant_fallback_scroll", msg="scroll fallback utilisé")
            points = []

        return [(p.id, p.score, p.payload) for p in points]

    # ── BM25 search async ──────────────────────────────────────────────
    async def _bm25_search(self, query: str, all_docs: list[dict], top_k: int):
        if not all_docs:
            return []

        corpus = []
        for d in all_docs:
            chunk_id = d.get("chunk_id", str(id(d)))
            if chunk_id in self.pre_tokenized_docs:
                tokens = self.pre_tokenized_docs[chunk_id]
            else:
                tokens = _tokenize(d.get("text", ""))
                self.pre_tokenized_docs[chunk_id] = tokens
            corpus.append(tokens)

        bm25 = BM25Okapi(corpus)
        query_tokens = _tokenize(query)
        scores = bm25.get_scores(query_tokens)
        ranked = sorted(
            [(all_docs[i].get("chunk_id", str(i)), float(scores[i])) for i in range(len(all_docs))],
            key=lambda x: x[1], reverse=True
        )
        return ranked[:top_k]

    # ── Retrieve amélioré avec chunks ─────────────────────────────────
    async def retrieve(self, query: str, top_k: Optional[int] = None, source_filter: Optional[list[str]] = None):
        k = top_k or settings.top_k
        ck = _cache_key(query, k, source_filter)
        cached = _retrieval_cache.get(ck)
        if cached:
            logger.info("retrieval_cache_hit", query=query[:80])
            return cached

        logger.info("retrieval_start", query=query[:80], top_k=k)

        try:
            vector_results = await self._vector_search(query, top_k=k, source_filter=source_filter)
        except Exception as e:
            logger.error("qdrant_error", error=str(e))
            return []

        if not vector_results:
            logger.warning("no_vector_results", query=query)
            return []

        pool_docs = [payload for _, _, payload in vector_results]
        bm25_ranked = await self._bm25_search(query, pool_docs, top_k=k * 2)
        vector_ranked = [(str(rid), score) for rid, score, _ in vector_results]

        fused = _reciprocal_rank_fusion([vector_ranked, bm25_ranked])

        id_to_payload = {str(rid): payload for rid, _, payload in vector_results}
        result_docs = []
        for doc_id, rrf_score in fused[:k]:
            if doc_id in id_to_payload:
                doc = id_to_payload[doc_id].copy()
                doc["rrf_score"] = round(rrf_score, 4)

                # ✅ Crée des chunks de qualité avec overlap
                doc_text = doc.get("text", "")
                doc["chunks"] = self.chunk_text(doc_text, chunk_size=300, overlap=50)

                result_docs.append(doc)

        _retrieval_cache.set(ck, result_docs)
        logger.info("retrieval_done", count=len(result_docs))
        return result_docs

    # ── Formatage pour LLM ─────────────────────────────────────────────
    def format_context(self, docs: list[dict]) -> str:
        parts = []
        for i, doc in enumerate(docs, 1):
            source = Path(doc.get("source", "inconnu")).name
            score = doc.get("rrf_score", "N/A")
            for chunk in doc.get("chunks", [doc.get("text", "")]):
                parts.append(f"[Document {i} | Fichier: {source} | Pertinence: {score}]\n{chunk}")
        return "\n\n---\n\n".join(parts)