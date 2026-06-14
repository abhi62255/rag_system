import pytest
from unittest.mock import MagicMock, patch
from langchain_core.documents import Document
from pipelines.ingestion.vector_store import VectorStoreService


@pytest.fixture
def mock_chroma_client():
    with patch("chromadb.PersistentClient") as mock_client_cls:
        mock_client = MagicMock()
        mock_collection = MagicMock()
        mock_client.get_or_create_collection.return_value = mock_collection
        mock_client_cls.return_value = mock_client
        yield mock_client, mock_collection


def test_vector_store_upsert(fake_embeddings, mock_chroma_client):
    _, mock_collection = mock_chroma_client

    service = VectorStoreService(
        persist_dir="/tmp/chroma",
        collection_name="test_collection",
        embeddings=fake_embeddings,
    )

    chunks = [
        Document(page_content="Chunk 1 content", metadata={"source": "doc1.txt"}),
        Document(page_content="Chunk 2 content", metadata={"source": "doc1.txt"}),
    ]

    chunk_ids = service.upsert_chunks(
        chunks=chunks,
        doc_id=123,
        filename="doc1.txt",
        version=1,
        doc_type="txt",
    )

    assert len(chunk_ids) == 2
    assert mock_collection.upsert.called


def test_vector_store_delete(fake_embeddings, mock_chroma_client):
    _, mock_collection = mock_chroma_client

    service = VectorStoreService(
        persist_dir="/tmp/chroma",
        collection_name="test_collection",
        embeddings=fake_embeddings,
    )

    deleted_count = service.delete_chunks(["id1", "id2"])
    assert deleted_count == 2
    mock_collection.delete.assert_called_once_with(ids=["id1", "id2"])


def test_vector_store_search(fake_embeddings, mock_chroma_client):
    _, mock_collection = mock_chroma_client
    mock_collection.count.return_value = 10
    mock_collection.query.return_value = {
        "documents": [["Doc match 1"]],
        "metadatas": [[{"filename": "match.txt"}]],
        "distances": [[0.1]],
    }

    service = VectorStoreService(
        persist_dir="/tmp/chroma",
        collection_name="test_collection",
        embeddings=fake_embeddings,
    )

    results = service.search_chunks(query="search term", top_k=2)
    assert results["documents"][0][0] == "Doc match 1"
    assert mock_collection.query.called
