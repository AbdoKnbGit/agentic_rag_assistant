"""
ingestion_service/router.py — FastAPI routes pour l'ingestion de documents
"""
import os
import shutil
from pathlib import Path

from fastapi import APIRouter, UploadFile, File, HTTPException, BackgroundTasks
from pydantic import BaseModel

from backend.config import settings
from backend.ingestion_service.ingestor import ingest_file, list_indexed_sources, delete_source
from backend.middleware import INGESTION_COUNT

router = APIRouter(prefix="/ingest", tags=["Ingestion"])

ALLOWED_EXTENSIONS = {".pdf", ".docx", ".csv", ".parquet", ".txt"}


class DeleteRequest(BaseModel):
    source_path: str


@router.post("/upload")
async def upload_and_ingest(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
):
    """Upload et indexe un document."""
    ext = Path(file.filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Extension non supportée: {ext}. Acceptées: {ALLOWED_EXTENSIONS}"
        )

    # Sauvegarder le fichier
    upload_dir = Path(settings.upload_dir)
    upload_dir.mkdir(parents=True, exist_ok=True)
    dest = upload_dir / file.filename

    with open(dest, "wb") as f:
        shutil.copyfileobj(file.file, f)

    # Ingestion en background
    background_tasks.add_task(_ingest_background, str(dest))
    INGESTION_COUNT.inc()

    return {"message": f"Fichier '{file.filename}' reçu, indexation en cours...", "path": str(dest)}


async def _ingest_background(file_path: str):
    try:
        result = ingest_file(file_path)
    except Exception as e:
        import structlog
        structlog.get_logger().error("ingestion_error", path=file_path, error=str(e))


@router.post("/ingest-path")
async def ingest_from_path(file_path: str):
    """Indexe un fichier déjà présent sur le serveur."""
    if not Path(file_path).exists():
        raise HTTPException(status_code=404, detail=f"Fichier non trouvé: {file_path}")
    result = ingest_file(file_path)
    return result


@router.get("/sources")
async def get_sources():
    """Liste les documents indexés."""
    sources = list_indexed_sources()
    return {"sources": sources, "count": len(sources)}


@router.delete("/source")
async def remove_source(request: DeleteRequest):
    """Supprime un document de l'index."""
    status = delete_source(request.source_path)
    return {"status": str(status), "deleted": request.source_path}
