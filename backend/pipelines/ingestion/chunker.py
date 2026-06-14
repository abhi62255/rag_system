import logging
from abc import ABC, abstractmethod
from typing import List

from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings
from langchain_experimental.text_splitter import SemanticChunker

logger = logging.getLogger(__name__)


class BaseChunker(ABC):
    """Abstract base class for document chunkers."""

    @abstractmethod
    def chunk_documents(self, documents: List[Document]) -> List[Document]:
        """Split a list of Documents into smaller chunks."""
        pass


class SemanticDocumentChunker(BaseChunker):
    """Chunks documents semantically using embeddings to detect breakpoints."""

    def __init__(
        self,
        embeddings: Embeddings,
        breakpoint_type: str = "percentile",
        breakpoint_amount: float = 95.0,
    ):
        self.embeddings = embeddings
        self.breakpoint_type = breakpoint_type
        self.breakpoint_amount = breakpoint_amount
        self._chunker = None

    @property
    def chunker(self) -> SemanticChunker:
        """Lazy load semantic chunker."""
        if self._chunker is None:
            self._chunker = SemanticChunker(
                embeddings=self.embeddings,
                breakpoint_threshold_type=self.breakpoint_type,
                breakpoint_threshold_amount=self.breakpoint_amount,
            )
        return self._chunker

    def chunk_documents(self, documents: List[Document]) -> List[Document]:
        if not documents:
            return []

        full_text = "\n\n".join(doc.page_content for doc in documents if doc.page_content.strip())
        if not full_text.strip():
            return []

        source = documents[0].metadata.get("source", "unknown")

        try:
            chunks = self.chunker.create_documents([full_text])
            logger.info(f"Chunked '{source}' into {len(chunks)} semantic chunks")
            return chunks
        except Exception as e:
            logger.warning(f"Semantic chunking failed for '{source}': {e}. Falling back to fixed-size split.")
            return self._fallback_chunk(full_text, source)

    def _fallback_chunk(
        self, text: str, source: str, chunk_size: int = 1000, overlap: int = 100
    ) -> List[Document]:
        chunks = []
        start = 0
        while start < len(text):
            end = min(start + chunk_size, len(text))
            chunk_text = text[start:end].strip()
            if chunk_text:
                chunks.append(Document(page_content=chunk_text, metadata={"source": source}))
            start += chunk_size - overlap
        return chunks
