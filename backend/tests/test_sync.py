import os
import pytest
from unittest.mock import MagicMock
from langchain_core.documents import Document
from pipelines.ingestion.loaders import LoaderRegistry
from pipelines.ingestion.chunker import BaseChunker
from pipelines.ingestion.vector_store import VectorStoreService
from pipelines.ingestion.file_tracker import DocumentTracker
from pipelines.ingestion.sync import IngestionPipeline


def test_sync_directory_lifecycle(db_session, temp_watch_dir):
    # Setup mock file in watch directory
    file_path = os.path.join(temp_watch_dir, "test.txt")
    with open(file_path, "w", encoding="utf-8") as f:
        f.write("Some mock text data.")

    # Mocks
    tracker = DocumentTracker(db_session)
    
    mock_loader = MagicMock(spec=LoaderRegistry)
    mock_loader.is_supported.return_value = True
    mock_loader.load_document.return_value = [Document(page_content="Some mock text data.", metadata={"source": file_path})]

    mock_chunker = MagicMock(spec=BaseChunker)
    mock_chunker.chunk_documents.return_value = [Document(page_content="Some mock text data.", metadata={"source": file_path})]

    mock_vector_store = MagicMock(spec=VectorStoreService)
    mock_vector_store.upsert_chunks.return_value = ["chunk-id-1"]

    pipeline = IngestionPipeline(
        tracker=tracker,
        loader_registry=mock_loader,
        chunker=mock_chunker,
        vector_store=mock_vector_store,
        watch_dir=temp_watch_dir,
    )

    # 1. Sync first time (new file)
    stats1 = pipeline.sync_directory()
    assert stats1["new"] == 1
    assert stats1["modified"] == 0
    assert stats1["deleted"] == 0

    doc = tracker.get_doc_by_filepath(file_path)
    assert doc is not None
    assert doc.status == "active"
    assert doc.get_chunk_ids() == ["chunk-id-1"]

    # 2. Sync second time (no change)
    stats2 = pipeline.sync_directory()
    assert stats2["new"] == 0
    assert stats2["modified"] == 0
    assert stats2["skipped"] == 1

    # 3. Modify file content
    with open(file_path, "w", encoding="utf-8") as f:
        f.write("Modified mock text data.")
    mock_loader.load_document.return_value = [Document(page_content="Modified mock text data.", metadata={"source": file_path})]

    stats3 = pipeline.sync_directory()
    assert stats3["modified"] == 1
    mock_vector_store.delete_chunks.assert_called_once_with(["chunk-id-1"])

    # 4. Delete file on disk
    os.remove(file_path)
    stats4 = pipeline.sync_directory()
    assert stats4["deleted"] == 1
    assert doc.status == "deleted"
