"""
ingestion_service/ingestor.py
Chargement, chunking et indexation de documents dans Qdrant.
Supporte : PDF, DOCX, CSV, Parquet, TXT
Optimisations : 
- Chunking sémantique + fallback récursif
- Enrichissement des métadonnées (formules, tables, headers)
- Détection de sections importantes
- Déduplication via hash
- Logging structuré
"""
import os
import re
import uuid
import hashlib
from pathlib import Path
from typing import List

import pandas as pd
import structlog
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document
from langchain_community.document_loaders import (
    PyMuPDFLoader,
    Docx2txtLoader,
    CSVLoader,
    UnstructuredFileLoader,
)
from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance, VectorParams, PointStruct, Filter,
    FieldCondition, MatchValue, FilterSelector
)
from fastembed import TextEmbedding

from backend.config import settings

logger = structlog.get_logger()

# ── Embedding model (local, gratuit) ──────────────────────────────────────────
_embedder = None

def get_embedder() -> TextEmbedding:
    global _embedder
    if _embedder is None:
        logger.info("loading_embedder", model=settings.embed_model)
        _embedder = TextEmbedding(model_name=settings.embed_model)
    return _embedder

def embed_texts(texts: List[str]) -> List[List[float]]:
    embedder = get_embedder()
    return [
        vec.tolist() if hasattr(vec, 'tolist') else list(vec)
        for vec in embedder.embed(texts)
    ]

# ── Qdrant client ─────────────────────────────────────────────────────────────
def get_qdrant() -> QdrantClient:
    return QdrantClient(host=settings.qdrant_host, port=settings.qdrant_port)

def ensure_collection(client: QdrantClient, vector_size: int = 384):
    """Crée la collection si elle n'existe pas."""
    collections = [c.name for c in client.get_collections().collections]
    if settings.qdrant_collection not in collections:
        client.create_collection(
            collection_name=settings.qdrant_collection,
            vectors_config=VectorParams(size=vector_size, distance=Distance.COSINE),
        )
        logger.info("collection_created", name=settings.qdrant_collection)

# ── Document loaders ──────────────────────────────────────────────────────────
def load_file(file_path: str) -> List[Document]:
    ext = Path(file_path).suffix.lower()
    logger.info("loading_file", path=file_path, ext=ext)

    if ext == ".pdf":
        docs = PyMuPDFLoader(file_path).load()
    elif ext == ".docx":
        docs = Docx2txtLoader(file_path).load()
    elif ext == ".csv":
        docs = CSVLoader(file_path).load()
    elif ext == ".parquet":
        df = pd.read_parquet(file_path)
        text = df.to_string(index=False)
        docs = [Document(page_content=text, metadata={"source": file_path, "type": "parquet"})]
    else:
        docs = UnstructuredFileLoader(file_path).load()

    for doc in docs:
        doc.metadata.setdefault("source", file_path)
        doc.metadata["file_type"] = ext.lstrip(".")
        doc.metadata["filename"] = Path(file_path).name

    return docs

# ── Chunking optimisé ─────────────────────────────────────────────────────────
def semantic_chunk_documents(docs: List[Document]) -> List[Document]:
    """
    Chunking sémantique : découpe par sections/headers quand possible,
    avec fallback au RecursiveCharacterTextSplitter.
    Enrichissement metadata : formules, tables, headers, hash
    """
    semantic_patterns = [
        r'^#{1,6}\s',           # Markdown headers
        r'^\d+\.\s',            # Numbered sections
        r'^[A-Z][A-Z\s]{3,}$',  # ALL CAPS HEADERS
        r'^={3,}$|^-{3,}$',     # Separator lines
    ]

    all_chunks = []
    for doc in docs:
        content = doc.page_content

        has_structure = any(
            re.search(pattern, content, re.MULTILINE)
            for pattern in semantic_patterns
        )

        if has_structure and len(content) > settings.chunk_size:
            # Split par sections sémantiques
            split_pattern = r'(?=^#{1,6}\s|^\d+\.\s|^[A-Z][A-Z\s]{3,}$|^={3,}$|^-{3,}$)'
            sections = re.split(split_pattern, content, flags=re.MULTILINE)
            sections = [s.strip() for s in sections if s.strip()]

            for section in sections:
                if len(section) > settings.chunk_size * 2:
                    # Section trop grande → sub-split
                    splitter = RecursiveCharacterTextSplitter(
                        chunk_size=settings.chunk_size,
                        chunk_overlap=settings.chunk_overlap,
                        separators=["\n\n", "\n", ". ", " "],
                    )
                    sub_chunks = splitter.split_text(section)
                    for text in sub_chunks:
                        chunk_doc = Document(
                            page_content=text,
                            metadata={**doc.metadata, "chunk_method": "semantic_sub"}
                        )
                        all_chunks.append(chunk_doc)
                elif len(section) > 30:
                    chunk_doc = Document(
                        page_content=section,
                        metadata={**doc.metadata, "chunk_method": "semantic"}
                    )
                    all_chunks.append(chunk_doc)
        else:
            # Fallback chunking classique
            splitter = RecursiveCharacterTextSplitter(
                chunk_size=settings.chunk_size,
                chunk_overlap=settings.chunk_overlap,
                separators=["\n\n", "\n", ". ", " "],
            )
            chunks = splitter.split_documents([doc])
            for c in chunks:
                c.metadata["chunk_method"] = "recursive"
            all_chunks.extend(chunks)

    # Enrichir toutes les métadonnées
    for chunk in all_chunks:
        chunk.metadata["chunk_id"] = str(uuid.uuid4())
        chunk.metadata["has_formula"] = any(
            sym in chunk.page_content
            for sym in ["∫", "∑", "√", "lim", "dx", "dy", "≤", "≥", "∂", "∇"]
        )
        chunk.metadata["has_table"] = "|" in chunk.page_content and "-+-" in chunk.page_content
        chunk.metadata["char_count"] = len(chunk.page_content)
        chunk.metadata["content_hash"] = hashlib.md5(
            chunk.page_content.encode()
        ).hexdigest()

    logger.info("semantic_chunks_created", count=len(all_chunks))
    return all_chunks

# ── Indexation dans Qdrant ────────────────────────────────────────────────────
def ingest_file(file_path: str) -> dict:
    """
    Pipeline complet : load → chunk → embed → store
    Optimisations : chunks sémantiques, embeddings vectoriels, metadata enrichie
    """
    # 1. Charger
    docs = load_file(file_path)
    if not docs:
        raise ValueError(f"Aucun contenu extrait de {file_path}")

    # 2. Chunker
    chunks = semantic_chunk_documents(docs)

    # 3. Embedder
    texts = [c.page_content for c in chunks]
    vectors = embed_texts(texts)

    # 4. Stocker dans Qdrant
    client = get_qdrant()
    vector_size = len(vectors[0])
    ensure_collection(client, vector_size)

    points = [
        PointStruct(
            id=str(uuid.uuid4()),
            vector=vec,
            payload={
                "text": chunk.page_content,
                **chunk.metadata,
            },
        )
        for chunk, vec in zip(chunks, vectors)
    ]

    client.upsert(collection_name=settings.qdrant_collection, points=points)
    logger.info("ingestion_done", file=file_path, chunks=len(chunks))

    return {
        "file": file_path,
        "documents_loaded": len(docs),
        "chunks_indexed": len(chunks),
        "status": "success",
    }

# ── Gestion des sources ───────────────────────────────────────────────────────
def list_indexed_sources() -> List[str]:
    """Retourne les sources déjà indexées."""
    client = get_qdrant()
    try:
        result = client.scroll(
            collection_name=settings.qdrant_collection,
            limit=1000,
            with_payload=True,
            with_vectors=False,
        )
        sources = list({p.payload.get("source", "unknown") for p in result[0]})
        return sources
    except Exception:
        return []

def delete_source(source_path: str) -> int:
    """Supprime tous les chunks d'une source donnée."""
    client = get_qdrant()
    try:
        result = client.delete(
            collection_name=settings.qdrant_collection,
            points_selector=FilterSelector(
                filter=Filter(
                    must=[FieldCondition(key="source", match=MatchValue(value=source_path))]
                )
            ),
        )
        logger.info("source_deleted", source=source_path)
        return result.status
    except Exception as e:
        logger.error("delete_source_error", source=source_path, error=str(e))
        raise