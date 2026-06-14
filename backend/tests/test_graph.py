import pytest
from unittest.mock import MagicMock
from pipelines.retrieval.retriever import RetrievalService
from pipelines.retrieval.graph import RAGAgent


def test_agent_answer_question(fake_chat_model):
    mock_retriever = MagicMock(spec=RetrievalService)
    mock_retriever.retrieve.return_value = (
        ["This is a retrieved document chunk text."],
        [{"filename": "test.txt", "chunk_index": 0, "doc_type": "txt", "version": 1, "similarity": 0.95, "source": "s1"}],
    )

    agent = RAGAgent(llm=fake_chat_model, retriever=mock_retriever)
    
    fake_chat_model.response_text = "Generated final answer citing [Source: test.txt, chunk 0]."

    answer, sources = agent.answer_question(
        user_message="Hello, what does the document say?",
        session_id="test-session-123",
    )

    assert "Generated final answer" in answer
    assert len(sources) == 1
    assert sources[0]["filename"] == "test.txt"
    assert sources[0]["similarity"] == 0.95
