import pytest
from unittest.mock import MagicMock
from pipelines.ingestion.vector_store import VectorStoreService
from pipelines.retrieval.retriever import RetrievalService


def test_retrieval_filtering():
    mock_vs = MagicMock(spec=VectorStoreService)
    # Cosine distances: 0.1 (similarity = 0.9) and 0.7 (similarity = 0.3)
    mock_vs.search_chunks.return_value = {
        "documents": [["Match 1", "Match 2"]],
        "metadatas": [[
            {"filename": "doc1.txt", "chunk_index": 0, "doc_type": "txt", "version": 1, "source": "s1"},
            {"filename": "doc2.txt", "chunk_index": 1, "doc_type": "txt", "version": 2, "source": "s2"},
        ]],
        "distances": [[0.1, 0.7]],
    }

    retriever = RetrievalService(
        vector_store=mock_vs,
        top_k=2,
        similarity_threshold=0.4, # 1 - distance >= 0.4. Match 1 (0.9) passes; Match 2 (0.3) fails.
    )

    docs, sources = retriever.retrieve("query text")

    assert len(docs) == 1
    assert docs[0] == "Match 1"
    assert len(sources) == 1
    assert sources[0]["filename"] == "doc1.txt"
    assert sources[0]["similarity"] == 0.9
