import logging
import uuid
from typing import List, Optional

import chromadb
from chromadb.config import Settings as ChromaSettings
from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings

logger = logging.getLogger(__name__)


class VectorStoreService:
    """Manages documents embedding and vector search operations in ChromaDB."""

    def __init__(
        self,
        persist_dir: str,
        collection_name: str,
        embeddings: Embeddings,
    ):
        self.persist_dir = persist_dir
        self.collection_name = collection_name
        self.embeddings = embeddings
        self._client = None
        self._collection = None

    @property
    def client(self) -> chromadb.PersistentClient:
        """Lazy load and cache the Chroma client."""
        if self._client is None:
            self._client = chromadb.PersistentClient(
                path=self.persist_dir,
                settings=ChromaSettings(anonymized_telemetry=False),
            )
            logger.info(f"ChromaDB client initialized at {self.persist_dir}")
        return self._client

    @property
    def collection(self) -> chromadb.Collection:
        """Lazy load and cache the collection."""
        if self._collection is None:
            self._collection = self.client.get_or_create_collection(
                name=self.collection_name,
                metadata={"hnsw:space": "cosine"},
            )
            logger.info(f"Using ChromaDB collection: {self.collection_name}")
        return self._collection

    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for a list of texts."""
        return self.embeddings.embed_documents(texts)

    def upsert_chunks(
        self,
        chunks: List[Document],
        doc_id: int,
        filename: str,
        version: int,
        doc_type: str,
    ) -> List[str]:
        if not chunks:
            return []

        collection = self.collection
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
        embeddings = self.embed_texts(texts)

        collection.upsert(
            ids=chunk_ids,
            documents=texts,
            embeddings=embeddings,
            metadatas=metadatas,
        )
        logger.info(f"Upserted {len(chunk_ids)} chunks for '{filename}' (doc_id={doc_id})")
        return chunk_ids

    def delete_chunks(self, chunk_ids: List[str]) -> int:
        if not chunk_ids:
            return 0
        collection = self.collection
        collection.delete(ids=chunk_ids)
        logger.info(f"Deleted {len(chunk_ids)} chunks from ChromaDB")
        return len(chunk_ids)

    def search_chunks(
        self,
        query: str,
        top_k: int = 5,
        where: Optional[dict] = None,
    ) -> dict:
        collection = self.collection
        query_embedding = self.embeddings.embed_query(query)

        count = collection.count()
        if count == 0:
            return {"documents": [[]], "metadatas": [[]], "distances": [[]]}

        kwargs = {
            "query_embeddings": [query_embedding],
            "n_results": min(top_k, max(1, count)),
            "include": ["documents", "metadatas", "distances"],
        }
        if where:
            kwargs["where"] = where

        results = collection.query(**kwargs)
        return results

    def get_collection_stats(self) -> dict:
        try:
            collection = self.collection
            return {
                "total_chunks": collection.count(),
                "collection_name": self.collection_name,
            }
        except Exception as e:
            logger.error(f"Failed to get collection stats: {e}")
            return {"total_chunks": 0, "collection_name": self.collection_name}
