import logging
import os
from datetime import datetime
from pathlib import Path

from config import settings
from models.db import init_db
from pipelines.ingestion.file_tracker import (
    compute_file_hash,
    create_doc_record,
    get_all_active_docs,
    get_db_session,
    get_doc_by_filepath,
    get_doc_type,
    mark_doc_deleted,
    mark_doc_failed,
    update_doc_record,
)
from pipelines.ingestion.loaders import is_supported, load_document
from pipelines.ingestion.chunker import chunk_documents
from pipelines.ingestion.vector_store import delete_chunks, upsert_chunks

logger = logging.getLogger(__name__)


def _ingest_new_file(db, filepath: str) -> None:
    filename = Path(filepath).name
    file_hash = compute_file_hash(filepath)
    doc_type = get_doc_type(filepath)

    doc = create_doc_record(
        db=db,
        filename=filename,
        filepath=filepath,
        file_hash=file_hash,
        doc_type=doc_type,
        chunk_ids=[],  # placeholder until ingestion completes
    )

    try:
        raw_docs = load_document(filepath)
        chunks = chunk_documents(raw_docs)

        if not chunks:
            logger.warning(f"No chunks extracted from '{filename}' — skipping")
            mark_doc_failed(db, doc, "No content extracted")
            return

        chunk_ids = upsert_chunks(
            chunks=chunks,
            doc_id=doc.id,
            filename=filename,
            version=doc.version,
            doc_type=doc_type,
        )
        update_doc_record(db, doc, file_hash, chunk_ids)
        logger.info(f"Ingested new file: {filename} → {len(chunk_ids)} chunks")

    except Exception as e:
        logger.error(f"Error ingesting '{filename}': {e}", exc_info=True)
        mark_doc_failed(db, doc, str(e))


def _reingest_modified_file(db, doc, filepath: str) -> None:
    filename = Path(filepath).name
    logger.info(f"Re-ingesting modified file: {filename}")

    old_chunk_ids = doc.get_chunk_ids()
    if old_chunk_ids:
        delete_chunks(old_chunk_ids)

    try:
        new_hash = compute_file_hash(filepath)
        raw_docs = load_document(filepath)
        chunks = chunk_documents(raw_docs)

        if not chunks:
            logger.warning(f"No chunks extracted from modified '{filename}' — marking failed")
            mark_doc_failed(db, doc, "No content extracted on re-ingest")
            return

        chunk_ids = upsert_chunks(
            chunks=chunks,
            doc_id=doc.id,
            filename=filename,
            version=doc.version + 1,
            doc_type=doc.doc_type,
        )
        update_doc_record(db, doc, new_hash, chunk_ids)
        logger.info(f"Re-ingested modified file: {filename} → {len(chunk_ids)} chunks (v{doc.version})")

    except Exception as e:
        logger.error(f"Error re-ingesting '{filename}': {e}", exc_info=True)
        mark_doc_failed(db, doc, str(e))


def _delete_removed_file(db, doc) -> None:
    old_chunk_ids = doc.get_chunk_ids()
    if old_chunk_ids:
        deleted = delete_chunks(old_chunk_ids)
        logger.info(f"Removed {deleted} chunks from ChromaDB for deleted file: {doc.filename}")
    mark_doc_deleted(db, doc)


def run_sync() -> dict:
    logger.info(f"[{datetime.utcnow().isoformat()}] Starting ingestion sync...")
    init_db()

    stats = {
        "new": 0,
        "modified": 0,
        "deleted": 0,
        "skipped": 0,
        "failed": 0,
        "started_at": datetime.utcnow().isoformat(),
    }

    db = get_db_session()
    try:
        # --- Build map of files currently on disk ---
        disk_files: dict[str, str] = {}  # filepath -> hash
        watch_path = Path(settings.watch_dir)

        if not watch_path.exists():
            watch_path.mkdir(parents=True, exist_ok=True)
            logger.info(f"Created watch directory: {settings.watch_dir}")

        for root, _, files in os.walk(watch_path):
            for fname in files:
                fpath = str(Path(root) / fname)
                fpath = os.path.abspath(fpath)
                if is_supported(fpath):
                    try:
                        disk_files[fpath] = compute_file_hash(fpath)
                    except Exception as e:
                        logger.warning(f"Could not hash {fpath}: {e}")

        # --- Build map of tracked active docs ---
        tracked = {doc.filepath: doc for doc in get_all_active_docs(db)}

        # --- Detect new and modified ---
        for fpath, fhash in disk_files.items():
            existing = get_doc_by_filepath(db, fpath)

            if existing is None:
                # Brand new file
                _ingest_new_file(db, fpath)
                stats["new"] += 1

            elif existing.status == "deleted":
                # Previously deleted, now back — treat as new
                _ingest_new_file(db, fpath)
                stats["new"] += 1

            elif existing.file_hash != fhash:
                # Content changed
                _reingest_modified_file(db, existing, fpath)
                stats["modified"] += 1

            else:
                # No change
                stats["skipped"] += 1

        # --- Detect deleted files ---
        for fpath, doc in tracked.items():
            if fpath not in disk_files:
                _delete_removed_file(db, doc)
                stats["deleted"] += 1

    except Exception as e:
        logger.error(f"Sync failed: {e}", exc_info=True)
        stats["error"] = str(e)
    finally:
        db.close()

    stats["finished_at"] = datetime.utcnow().isoformat()
    logger.info(f"Sync complete: {stats}")
    return stats


def ingest_single_file(filepath: str) -> dict:
    init_db()
    filepath = os.path.abspath(filepath)
    db = get_db_session()
    try:
        existing = get_doc_by_filepath(db, filepath)
        if existing and existing.status == "active":
            current_hash = compute_file_hash(filepath)
            if existing.file_hash == current_hash:
                return {"status": "skipped", "reason": "File unchanged"}
            _reingest_modified_file(db, existing, filepath)
            return {"status": "updated", "filename": Path(filepath).name}
        else:
            _ingest_new_file(db, filepath)
            return {"status": "ingested", "filename": Path(filepath).name}
    finally:
        db.close()
