import logging
import uuid
from functools import lru_cache
from typing import Optional

import chromadb
from chromadb.config import Settings as ChromaSettings
from langchain_core.documents import Document

from config import settings
from pipelines.ingestion.chunker import get_embeddings

logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def get_chroma_client() -> chromadb.PersistentClient:
    client = chromadb.PersistentClient(
        path=settings.chroma_persist_dir,
        settings=ChromaSettings(anonymized_telemetry=False),
    )
    logger.info(f"ChromaDB client initialized at {settings.chroma_persist_dir}")
    return client


@lru_cache(maxsize=1)
def get_collection() -> chromadb.Collection:
    client = get_chroma_client()
    collection = client.get_or_create_collection(
        name=settings.chroma_collection,
        metadata={"hnsw:space": "cosine"},
    )
    logger.info(f"Using ChromaDB collection: {settings.chroma_collection}")
    return collection


def embed_texts(texts: list[str]) -> list[list[float]]:
    embeddings_model = get_embeddings()
    return embeddings_model.embed_documents(texts)


def upsert_chunks(
    chunks: list[Document],
    doc_id: int,
    filename: str,
    version: int,
    doc_type: str,
) -> list[str]:
    if not chunks:
        return []

    collection = get_collection()
    chunk_ids = [str(uuid.uuid4()) for _ in chunks]
    texts = [chunk.page_content for chunk in chunks]

    metadatas = [
        {
            "doc_id": str(doc_id),
            "filename": filename,
            "version": version,
            "doc_type": doc_type,
            "chunk_index": i,
            "source": chunk.metadata.get("source", filename),
        }
        for i, chunk in enumerate(chunks)
    ]

    logger.info(f"Embedding {len(texts)} chunks for '{filename}'...")
    embeddings = embed_texts(texts)

    collection.upsert(
        ids=chunk_ids,
        documents=texts,
        embeddings=embeddings,
        metadatas=metadatas,
    )
    logger.info(f"Upserted {len(chunk_ids)} chunks for '{filename}' (doc_id={doc_id})")
    return chunk_ids


def delete_chunks(chunk_ids: list[str]) -> int:
    if not chunk_ids:
        return 0
    collection = get_collection()
    collection.delete(ids=chunk_ids)
    logger.info(f"Deleted {len(chunk_ids)} chunks from ChromaDB")
    return len(chunk_ids)


def search_chunks(
    query: str,
    top_k: int = 5,
    where: Optional[dict] = None,
) -> dict:
    collection = get_collection()
    embeddings_model = get_embeddings()
    query_embedding = embeddings_model.embed_query(query)

    kwargs = {
        "query_embeddings": [query_embedding],
        "n_results": min(top_k, max(1, collection.count())),
        "include": ["documents", "metadatas", "distances"],
    }
    if where:
        kwargs["where"] = where

    results = collection.query(**kwargs)
    return results


def get_collection_stats() -> dict:
    try:
        collection = get_collection()
        return {
            "total_chunks": collection.count(),
            "collection_name": settings.chroma_collection,
        }
    except Exception as e:
        logger.error(f"Failed to get collection stats: {e}")
        return {"total_chunks": 0, "collection_name": settings.chroma_collection}
