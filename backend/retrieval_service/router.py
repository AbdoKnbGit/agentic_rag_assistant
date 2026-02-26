"""
retrieval_service/router.py — FastAPI routes pour la recherche
"""
from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional

from backend.retrieval_service.retriever import HybridRetrieverOptimized as HybridRetriever

router = APIRouter(prefix="/retrieve", tags=["Retrieval"])


class RetrieveRequest(BaseModel):
    query: str
    top_k: int = 6
    source_filter: Optional[str] = None


@router.post("/search")
async def search(request: RetrieveRequest):
    """Recherche hybride dans les documents indexés."""
    retriever = HybridRetriever()
    docs = await retriever.retrieve(      # ← await car la méthode est async
        query=request.query,
        top_k=request.top_k,
        source_filter=request.source_filter,
    )
    return {"query": request.query, "results": docs, "count": len(docs)}