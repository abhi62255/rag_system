import pytest
from sqlalchemy.orm import Session
from models.db import TrackedDocument
from pipelines.ingestion.file_tracker import DocumentTracker


def test_tracker_create_and_fetch(db_session: Session):
    tracker = DocumentTracker(db_session)
    
    doc = tracker.create_doc_record(
        filename="test.txt",
        filepath="/watch/test.txt",
        file_hash="hash123",
        doc_type="txt",
        chunk_ids=["chunk1", "chunk2"],
    )

    assert doc.id is not None
    assert doc.filename == "test.txt"
    assert doc.version == 1
    assert doc.status == "active"
    assert doc.get_chunk_ids() == ["chunk1", "chunk2"]

    # Fetch
    fetched = tracker.get_doc_by_filepath("/watch/test.txt")
    assert fetched is not None
    assert fetched.id == doc.id
    assert fetched.file_hash == "hash123"


def test_tracker_update(db_session: Session):
    tracker = DocumentTracker(db_session)
    
    doc = tracker.create_doc_record(
        filename="test.txt",
        filepath="/watch/test.txt",
        file_hash="hash123",
        doc_type="txt",
        chunk_ids=["chunk1"],
    )

    updated_doc = tracker.update_doc_record(
        doc=doc,
        file_hash="new_hash",
        chunk_ids=["chunk3", "chunk4"],
    )

    assert updated_doc.version == 2
    assert updated_doc.file_hash == "new_hash"
    assert updated_doc.get_chunk_ids() == ["chunk3", "chunk4"]


def test_tracker_delete_and_fail(db_session: Session):
    tracker = DocumentTracker(db_session)
    
    doc = tracker.create_doc_record(
        filename="test.txt",
        filepath="/watch/test.txt",
        file_hash="hash123",
        doc_type="txt",
        chunk_ids=["chunk1"],
    )

    tracker.mark_doc_failed(doc, "Ingestion error message")
    assert doc.status == "failed"
    assert doc.error_message == "Ingestion error message"

    tracker.mark_doc_deleted(doc)
    assert doc.status == "deleted"
    assert doc.get_chunk_ids() == []
