import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Dict

from models.db import TrackedDocument
from pipelines.ingestion.file_tracker import DocumentTracker
from pipelines.ingestion.loaders import LoaderRegistry
from pipelines.ingestion.chunker import BaseChunker
from pipelines.ingestion.vector_store import VectorStoreService

logger = logging.getLogger(__name__)


class IngestionPipeline:
    """Orchestrates file tracking, document loading, semantic chunking, and vector database updates."""

    def __init__(
        self,
        tracker: DocumentTracker,
        loader_registry: LoaderRegistry,
        chunker: BaseChunker,
        vector_store: VectorStoreService,
        watch_dir: str,
    ):
        self.tracker = tracker
        self.loader_registry = loader_registry
        self.chunker = chunker
        self.vector_store = vector_store
        self.watch_dir = watch_dir

    def _ingest_new_file(self, filepath: str) -> None:
        filename = Path(filepath).name
        file_hash = self.tracker.compute_file_hash(filepath)
        doc_type = self.tracker.get_doc_type(filepath)

        doc = self.tracker.create_doc_record(
            filename=filename,
            filepath=filepath,
            file_hash=file_hash,
            doc_type=doc_type,
            chunk_ids=[],  # placeholder
        )

        try:
            raw_docs = self.loader_registry.load_document(filepath)
            chunks = self.chunker.chunk_documents(raw_docs)

            if not chunks:
                logger.warning(f"No chunks extracted from '{filename}' — skipping")
                self.tracker.mark_doc_failed(doc, "No content extracted")
                return

            chunk_ids = self.vector_store.upsert_chunks(
                chunks=chunks,
                doc_id=doc.id,
                filename=filename,
                version=doc.version,
                doc_type=doc_type,
            )
            self.tracker.update_doc_record(doc, file_hash, chunk_ids)
            logger.info(f"Ingested new file: {filename} → {len(chunk_ids)} chunks")

        except Exception as e:
            logger.error(f"Error ingesting '{filename}': {e}", exc_info=True)
            self.tracker.mark_doc_failed(doc, str(e))

    def _reingest_modified_file(self, doc: TrackedDocument, filepath: str) -> None:
        filename = Path(filepath).name
        logger.info(f"Re-ingesting modified file: {filename}")

        old_chunk_ids = doc.get_chunk_ids()
        if old_chunk_ids:
            self.vector_store.delete_chunks(old_chunk_ids)

        try:
            new_hash = self.tracker.compute_file_hash(filepath)
            raw_docs = self.loader_registry.load_document(filepath)
            chunks = self.chunker.chunk_documents(raw_docs)

            if not chunks:
                logger.warning(f"No chunks extracted from modified '{filename}' — marking failed")
                self.tracker.mark_doc_failed(doc, "No content extracted on re-ingest")
                return

            chunk_ids = self.vector_store.upsert_chunks(
                chunks=chunks,
                doc_id=doc.id,
                filename=filename,
                version=doc.version + 1,
                doc_type=doc.doc_type,
            )
            self.tracker.update_doc_record(doc, new_hash, chunk_ids)
            logger.info(f"Re-ingested modified file: {filename} → {len(chunk_ids)} chunks (v{doc.version})")

        except Exception as e:
            logger.error(f"Error re-ingesting '{filename}': {e}", exc_info=True)
            self.tracker.mark_doc_failed(doc, str(e))

    def _delete_removed_file(self, doc: TrackedDocument) -> None:
        old_chunk_ids = doc.get_chunk_ids()
        if old_chunk_ids:
            deleted = self.vector_store.delete_chunks(old_chunk_ids)
            logger.info(f"Removed {deleted} chunks from ChromaDB for deleted file: {doc.filename}")
        self.tracker.mark_doc_deleted(doc)

    def sync_directory(self) -> dict:
        logger.info(f"[{datetime.utcnow().isoformat()}] Starting ingestion sync...")
        stats = {
            "new": 0,
            "modified": 0,
            "deleted": 0,
            "skipped": 0,
            "failed": 0,
            "started_at": datetime.utcnow().isoformat(),
        }

        try:
            # --- Build map of files currently on disk ---
            disk_files: Dict[str, str] = {}
            watch_path = Path(self.watch_dir)

            if not watch_path.exists():
                watch_path.mkdir(parents=True, exist_ok=True)
                logger.info(f"Created watch directory: {self.watch_dir}")

            for root, _, files in os.walk(watch_path):
                for fname in files:
                    fpath = str(Path(root) / fname)
                    fpath = os.path.abspath(fpath)
                    if self.loader_registry.is_supported(fpath):
                        try:
                            disk_files[fpath] = self.tracker.compute_file_hash(fpath)
                        except Exception as e:
                            logger.warning(f"Could not hash {fpath}: {e}")

            # --- Build map of tracked active docs ---
            tracked = {doc.filepath: doc for doc in self.tracker.get_all_active_docs()}

            # --- Detect new and modified ---
            for fpath, fhash in disk_files.items():
                existing = self.tracker.get_doc_by_filepath(fpath)

                if existing is None:
                    # Brand new file
                    self._ingest_new_file(fpath)
                    stats["new"] += 1

                elif existing.status == "deleted":
                    # Previously deleted, now back — treat as new
                    self._ingest_new_file(fpath)
                    stats["new"] += 1

                elif existing.file_hash != fhash:
                    # Content changed
                    self._reingest_modified_file(existing, fpath)
                    stats["modified"] += 1

                else:
                    # No change
                    stats["skipped"] += 1

            # --- Detect deleted files ---
            for fpath, doc in tracked.items():
                if fpath not in disk_files:
                    self._delete_removed_file(doc)
                    stats["deleted"] += 1

        except Exception as e:
            logger.error(f"Sync failed: {e}", exc_info=True)
            stats["error"] = str(e)

        stats["finished_at"] = datetime.utcnow().isoformat()
        logger.info(f"Sync complete: {stats}")
        return stats

    def ingest_file(self, filepath: str) -> dict:
        filepath = os.path.abspath(filepath)
        existing = self.tracker.get_doc_by_filepath(filepath)
        if existing and existing.status == "active":
            current_hash = self.tracker.compute_file_hash(filepath)
            if existing.file_hash == current_hash:
                return {"status": "skipped", "reason": "File unchanged"}
            self._reingest_modified_file(existing, filepath)
            return {"status": "updated", "filename": Path(filepath).name}
        else:
            self._ingest_new_file(filepath)
            return {"status": "ingested", "filename": Path(filepath).name}


def run_sync_job() -> dict:
    """Convenience job function for background scheduler.
    Instantiates dependencies and runs directory sync.
    """
    from config import settings
    from models.db import init_db, SessionLocal
    from pipelines.ingestion.loaders import LoaderRegistry
    from pipelines.ingestion.chunker import SemanticDocumentChunker
    from pipelines.ingestion.vector_store import VectorStoreService
    from pipelines.ingestion.file_tracker import DocumentTracker
    from langchain_google_genai import GoogleGenerativeAIEmbeddings

    init_db()
    db = SessionLocal()
    try:
        embeddings = GoogleGenerativeAIEmbeddings(
            model=settings.gemini_embedding_model,
            google_api_key=settings.google_api_key,
        )
        tracker = DocumentTracker(db)
        loader_registry = LoaderRegistry()
        chunker = SemanticDocumentChunker(
            embeddings=embeddings,
            breakpoint_type=settings.semantic_breakpoint_type,
            breakpoint_amount=settings.semantic_breakpoint_amount,
        )
        vector_store = VectorStoreService(
            persist_dir=settings.chroma_persist_dir,
            collection_name=settings.chroma_collection,
            embeddings=embeddings,
        )
        pipeline = IngestionPipeline(
            tracker=tracker,
            loader_registry=loader_registry,
            chunker=chunker,
            vector_store=vector_store,
            watch_dir=settings.watch_dir,
        )
        return pipeline.sync_directory()
    finally:
        db.close()
