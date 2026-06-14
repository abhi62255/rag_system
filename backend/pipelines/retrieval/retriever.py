import logging
from typing import List, Optional, Tuple

from pipelines.ingestion.vector_store import VectorStoreService

logger = logging.getLogger(__name__)


class RetrievalService:
    """Handles document retrieval and similarity filtering using a vector store service."""

    def __init__(
        self,
        vector_store: VectorStoreService,
        top_k: int = 5,
        similarity_threshold: float = 0.4,
    ):
        self.vector_store = vector_store
        self.top_k = top_k
        self.similarity_threshold = similarity_threshold

    def retrieve(self, query: str, top_k: Optional[int] = None) -> Tuple[List[str], List[dict]]:
        k = top_k or self.top_k
        threshold = self.similarity_threshold

        try:
            results = self.vector_store.search_chunks(query, top_k=k)
        except Exception as e:
            logger.error(f"ChromaDB search failed: {e}")
            return [], []

        documents = results.get("documents", [[]])[0]
        metadatas = results.get("metadatas", [[]])[0]
        distances = results.get("distances", [[]])[0]

        if not documents:
            return [], []

        context_chunks: List[str] = []
        sources: List[dict] = []

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
