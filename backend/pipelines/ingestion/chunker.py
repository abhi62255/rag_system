import logging
from functools import lru_cache

from langchain_core.documents import Document
from langchain_experimental.text_splitter import SemanticChunker
from langchain_google_genai import GoogleGenerativeAIEmbeddings

from config import settings

logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def get_embeddings() -> GoogleGenerativeAIEmbeddings:
    return GoogleGenerativeAIEmbeddings(
        model=settings.gemini_embedding_model,
        google_api_key=settings.google_api_key,
    )


@lru_cache(maxsize=1)
def get_chunker() -> SemanticChunker:
    return SemanticChunker(
        embeddings=get_embeddings(),
        breakpoint_threshold_type=settings.semantic_breakpoint_type,
        breakpoint_threshold_amount=settings.semantic_breakpoint_amount,
    )


def chunk_documents(documents: list[Document]) -> list[Document]:
    if not documents:
        return []

    full_text = "\n\n".join(doc.page_content for doc in documents if doc.page_content.strip())
    if not full_text.strip():
        return []

    source = documents[0].metadata.get("source", "unknown")

    try:
        chunker = get_chunker()
        chunks = chunker.create_documents([full_text])
        logger.info(f"Chunked '{source}' into {len(chunks)} semantic chunks")
        return chunks
    except Exception as e:
        logger.warning(f"Semantic chunking failed for '{source}': {e}. Falling back to fixed-size split.")
        return _fallback_chunk(full_text, source)


def _fallback_chunk(text: str, source: str, chunk_size: int = 1000, overlap: int = 100) -> list[Document]:
    chunks = []
    start = 0
    while start < len(text):
        end = min(start + chunk_size, len(text))
        chunk_text = text[start:end].strip()
        if chunk_text:
            chunks.append(Document(page_content=chunk_text, metadata={"source": source}))
        start += chunk_size - overlap
    return chunks
