import logging
import os
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from pydantic import BaseModel

from config import settings
from models.db import TrackedDocument
from api.deps import (
    get_document_tracker,
    get_vector_store_service,
    get_ingestion_pipeline,
)
from pipelines.ingestion.file_tracker import DocumentTracker
from pipelines.ingestion.vector_store import VectorStoreService
from pipelines.ingestion.sync import IngestionPipeline

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin", tags=["admin"])


class SyncResponse(BaseModel):
    new: int
    modified: int
    deleted: int
    skipped: int
    started_at: str
    finished_at: str
    error: Optional[str] = None


class DocumentStatus(BaseModel):
    id: int
    filename: str
    filepath: str
    version: int
    status: str
    doc_type: Optional[str]
    chunk_count: int
    ingested_at: Optional[str]
    updated_at: Optional[str]
    deleted_at: Optional[str]
    error_message: Optional[str]


class StatsResponse(BaseModel):
    total_chunks: int
    collection_name: str
    total_documents: int
    active_documents: int
    deleted_documents: int


@router.post("/ingest/trigger", response_model=SyncResponse)
async def trigger_ingestion(
    pipeline: IngestionPipeline = Depends(get_ingestion_pipeline),
):
    try:
        stats = pipeline.sync_directory()
        return SyncResponse(**{k: v for k, v in stats.items() if k != "error"}, error=stats.get("error"))
    except Exception as e:
        logger.error(f"Manual sync failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/ingest/upload")
async def upload_and_ingest(
    file: UploadFile = File(...),
    pipeline: IngestionPipeline = Depends(get_ingestion_pipeline),
):
    allowed_ext = {".pdf", ".docx", ".doc", ".html", ".htm", ".txt", ".md"}
    ext = Path(file.filename).suffix.lower()
    if ext not in allowed_ext:
        raise HTTPException(status_code=400, detail=f"Unsupported file type: {ext}")

    dest_path = os.path.abspath(os.path.join(settings.watch_dir, file.filename))
    try:
        with open(dest_path, "wb") as f:
            content = await file.read()
            f.write(content)

        result = pipeline.ingest_file(dest_path)
        return {"filename": file.filename, **result}
    except Exception as e:
        if os.path.exists(dest_path):
            os.remove(dest_path)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/documents", response_model=list[DocumentStatus])
def list_documents(
    tracker: DocumentTracker = Depends(get_document_tracker),
):
    docs = tracker.get_all_docs()
    return [DocumentStatus(**doc.to_dict()) for doc in docs]


@router.delete("/documents/{doc_id}")
def delete_document(
    doc_id: int,
    tracker: DocumentTracker = Depends(get_document_tracker),
    vector_store: VectorStoreService = Depends(get_vector_store_service),
):
    doc = tracker.db.query(TrackedDocument).filter(TrackedDocument.id == doc_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    chunk_ids = doc.get_chunk_ids()
    if chunk_ids:
        vector_store.delete_chunks(chunk_ids)

    # Remove physical file if it exists
    if os.path.exists(doc.filepath):
        try:
            os.remove(doc.filepath)
        except Exception as e:
            logger.warning(f"Could not remove file {doc.filepath}: {e}")

    tracker.mark_doc_deleted(doc)
    return {"status": "deleted", "filename": doc.filename, "chunks_removed": len(chunk_ids)}


@router.get("/stats", response_model=StatsResponse)
def get_stats(
    tracker: DocumentTracker = Depends(get_document_tracker),
    vector_store: VectorStoreService = Depends(get_vector_store_service),
):
    chroma_stats = vector_store.get_collection_stats()
    all_docs = tracker.get_all_docs()
    active = sum(1 for d in all_docs if d.status == "active")
    deleted = sum(1 for d in all_docs if d.status == "deleted")

    return StatsResponse(
        total_chunks=chroma_stats["total_chunks"],
        collection_name=chroma_stats["collection_name"],
        total_documents=len(all_docs),
        active_documents=active,
        deleted_documents=deleted,
    )
