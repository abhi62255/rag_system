import os
import hashlib
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

from sqlalchemy.orm import Session

from models.db import SessionLocal, TrackedDocument

logger = logging.getLogger(__name__)


def compute_file_hash(filepath: str) -> str:
    sha256 = hashlib.sha256()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            sha256.update(chunk)
    return sha256.hexdigest()


def get_doc_type(filepath: str) -> str:
    ext = Path(filepath).suffix.lower()
    mapping = {
        ".pdf": "pdf",
        ".docx": "docx",
        ".doc": "docx",
        ".html": "html",
        ".htm": "html",
        ".txt": "txt",
        ".md": "txt",
    }
    return mapping.get(ext, "txt")


def get_all_active_docs(db: Session) -> list[TrackedDocument]:
    return db.query(TrackedDocument).filter(TrackedDocument.status == "active").all()


def get_doc_by_filepath(db: Session, filepath: str) -> Optional[TrackedDocument]:
    filepath = os.path.abspath(filepath)
    return db.query(TrackedDocument).filter(TrackedDocument.filepath == filepath).first()


def create_doc_record(
    db: Session,
    filename: str,
    filepath: str,
    file_hash: str,
    doc_type: str,
    chunk_ids: list[str],
) -> TrackedDocument:
    filepath = os.path.abspath(filepath)
    doc = TrackedDocument(
        filename=filename,
        filepath=filepath,
        file_hash=file_hash,
        doc_type=doc_type,
        status="active",
        version=1,
        chunk_count=len(chunk_ids),
        ingested_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    doc.set_chunk_ids(chunk_ids)
    db.add(doc)
    db.commit()
    db.refresh(doc)
    logger.info(f"Tracked new document: {filename} (v1, {len(chunk_ids)} chunks)")
    return doc


def update_doc_record(
    db: Session,
    doc: TrackedDocument,
    file_hash: str,
    chunk_ids: list[str],
) -> TrackedDocument:
    doc.file_hash = file_hash
    doc.version += 1
    doc.status = "active"
    doc.chunk_count = len(chunk_ids)
    doc.set_chunk_ids(chunk_ids)
    doc.updated_at = datetime.utcnow()
    doc.error_message = None
    db.commit()
    db.refresh(doc)
    logger.info(f"Updated document: {doc.filename} (now v{doc.version}, {len(chunk_ids)} chunks)")
    return doc


def mark_doc_deleted(db: Session, doc: TrackedDocument) -> TrackedDocument:
    doc.status = "deleted"
    doc.deleted_at = datetime.utcnow()
    doc.set_chunk_ids([])
    db.commit()
    db.refresh(doc)
    logger.info(f"Marked document deleted: {doc.filename}")
    return doc


def mark_doc_failed(db: Session, doc: TrackedDocument, error: str) -> TrackedDocument:
    doc.status = "failed"
    doc.error_message = error[:1000]
    doc.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(doc)
    logger.warning(f"Document ingestion failed: {doc.filename} — {error[:100]}")
    return doc


def get_all_docs(db: Session) -> list[TrackedDocument]:
    return db.query(TrackedDocument).order_by(TrackedDocument.ingested_at.desc()).all()


def get_db_session() -> Session:
    return SessionLocal()
