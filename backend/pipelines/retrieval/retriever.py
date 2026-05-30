import logging
from typing import Optional

from config import settings
from pipelines.ingestion.vector_store import search_chunks

logger = logging.getLogger(__name__)


def retrieve(query: str, top_k: Optional[int] = None) -> tuple[list[str], list[dict]]:
    k = top_k or settings.top_k_retrieval
    threshold = settings.similarity_threshold

    try:
        results = search_chunks(query, top_k=k)
    except Exception as e:
        logger.error(f"ChromaDB search failed: {e}")
        return [], []

    documents = results.get("documents", [[]])[0]
    metadatas = results.get("metadatas", [[]])[0]
    distances = results.get("distances", [[]])[0]

    if not documents:
        return [], []

    context_chunks: list[str] = []
    sources: list[dict] = []

    for doc, meta, dist in zip(documents, metadatas, distances):
        # cosine distance: lower = more similar. similarity = 1 - distance
        similarity = 1.0 - float(dist)
        if similarity < threshold:
            logger.debug(f"Chunk below threshold ({similarity:.3f} < {threshold}): skipped")
            continue

        context_chunks.append(doc)
        sources.append({
            "filename": meta.get("filename", "unknown"),
            "chunk_index": meta.get("chunk_index", 0),
            "doc_type": meta.get("doc_type", ""),
            "version": meta.get("version", 1),
            "similarity": round(similarity, 4),
            "source": meta.get("source", ""),
        })

    logger.info(f"Retrieved {len(context_chunks)} chunks (from {k} candidates) for query: {query[:80]!r}")
    return context_chunks, sources
