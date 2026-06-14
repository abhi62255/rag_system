import os
import shutil
import tempfile
from typing import Generator, List
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from models.db import Base
from langchain_core.embeddings import Embeddings
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage
from langchain_core.outputs import ChatResult, ChatGeneration


class FakeEmbeddings(Embeddings):
    """Simple fake embeddings for testing."""

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        return [[0.1] * 768 for _ in texts]

    def embed_query(self, text: str) -> List[float]:
        return [0.1] * 768


class FakeChatModel(BaseChatModel):
    """Simple fake ChatModel for testing."""

    response_text: str = "Fake response text"

    def _generate(
        self,
        messages: List[BaseMessage],
        stop: list[str] | None = None,
        run_manager=None,
        **kwargs,
    ) -> ChatResult:
        # Simple query rewrite logic mock
        prompt = messages[-1].content
        if "rewrite" in prompt.lower() or "latest question" in prompt.lower():
            content = "rewritten text query"
        else:
            content = self.response_text
        
        generation = ChatGeneration(message=AIMessage(content=content))
        return ChatResult(generations=[generation])

    @property
    def _llm_type(self) -> str:
        return "fake-chat-model"


@pytest.fixture
def fake_embeddings() -> Embeddings:
    return FakeEmbeddings()


@pytest.fixture
def fake_chat_model() -> FakeChatModel:
    return FakeChatModel()


@pytest.fixture
def temp_watch_dir() -> Generator[str, None, None]:
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir)


@pytest.fixture
def db_session() -> Generator[sessionmaker, None, None]:
    # In-memory database
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)
