import os
import hashlib
import logging
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from sqlalchemy.orm import Session

from models.db import TrackedDocument

logger = logging.getLogger(__name__)


class DocumentTracker:
    """Manages document state tracking database operations."""

    def __init__(self, db: Session):
        self.db = db

    @staticmethod
    def compute_file_hash(filepath: str) -> str:
        """Compute the SHA256 hash of a file."""
        sha256 = hashlib.sha256()
        with open(filepath, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                sha256.update(chunk)
        return sha256.hexdigest()

    @staticmethod
    def get_doc_type(filepath: str) -> str:
        """Determine document type based on file extension."""
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

    def get_all_active_docs(self) -> List[TrackedDocument]:
        """Fetch all actively tracked documents."""
        return self.db.query(TrackedDocument).filter(TrackedDocument.status == "active").all()

    def get_doc_by_filepath(self, filepath: str) -> Optional[TrackedDocument]:
        """Fetch a document by its absolute path."""
        filepath = os.path.abspath(filepath)
        return self.db.query(TrackedDocument).filter(TrackedDocument.filepath == filepath).first()

    def create_doc_record(
        self,
        filename: str,
        filepath: str,
        file_hash: str,
        doc_type: str,
        chunk_ids: List[str],
    ) -> TrackedDocument:
        """Create a new document tracking record."""
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
        self.db.add(doc)
        self.db.commit()
        self.db.refresh(doc)
        logger.info(f"Tracked new document: {filename} (v1, {len(chunk_ids)} chunks)")
        return doc

    def update_doc_record(
        self,
        doc: TrackedDocument,
        file_hash: str,
        chunk_ids: List[str],
    ) -> TrackedDocument:
        """Update an existing document tracking record with new version and chunks."""
        doc.file_hash = file_hash
        doc.version += 1
        doc.status = "active"
        doc.chunk_count = len(chunk_ids)
        doc.set_chunk_ids(chunk_ids)
        doc.updated_at = datetime.utcnow()
        doc.error_message = None
        self.db.commit()
        self.db.refresh(doc)
        logger.info(f"Updated document: {doc.filename} (now v{doc.version}, {len(chunk_ids)} chunks)")
        return doc

    def mark_doc_deleted(self, doc: TrackedDocument) -> TrackedDocument:
        """Mark document record status as deleted."""
        doc.status = "deleted"
        doc.deleted_at = datetime.utcnow()
        doc.set_chunk_ids([])
        self.db.commit()
        self.db.refresh(doc)
        logger.info(f"Marked document deleted: {doc.filename}")
        return doc

    def mark_doc_failed(self, doc: TrackedDocument, error: str) -> TrackedDocument:
        """Mark document record status as failed with error details."""
        doc.status = "failed"
        doc.error_message = error[:1000]
        doc.updated_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(doc)
        logger.warning(f"Document ingestion failed: {doc.filename} — {error[:100]}")
        return doc

    def get_all_docs(self) -> List[TrackedDocument]:
        """Fetch all tracked documents (active, failed, or deleted)."""
        return self.db.query(TrackedDocument).order_by(TrackedDocument.ingested_at.desc()).all()
