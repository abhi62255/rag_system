import pytest
from unittest.mock import MagicMock
from langchain_core.documents import Document
from pipelines.ingestion.chunker import SemanticDocumentChunker


def test_chunker_empty_docs(fake_embeddings):
    chunker = SemanticDocumentChunker(embeddings=fake_embeddings)
    assert chunker.chunk_documents([]) == []


def test_chunker_fallback_split(fake_embeddings):
    chunker = SemanticDocumentChunker(embeddings=fake_embeddings)
    # Force semantic chunker to fail to verify the fallback split mechanism
    chunker._chunker = MagicMock()
    chunker._chunker.create_documents.side_effect = Exception("Semantic fail")

    doc = Document(page_content="This is a test document to check fallback chunking behavior.", metadata={"source": "test.txt"})
    chunks = chunker.chunk_documents([doc])

    assert len(chunks) > 0
    assert chunks[0].metadata["source"] == "test.txt"
