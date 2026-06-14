from functools import lru_cache
from fastapi import Depends
from sqlalchemy.orm import Session

from config import settings
from models.db import get_db
from pipelines.ingestion.loaders import LoaderRegistry
from pipelines.ingestion.chunker import SemanticDocumentChunker
from pipelines.ingestion.vector_store import VectorStoreService
from pipelines.ingestion.file_tracker import DocumentTracker
from pipelines.ingestion.sync import IngestionPipeline
from pipelines.retrieval.retriever import RetrievalService
from pipelines.retrieval.graph import RAGAgent

from langchain_google_genai import GoogleGenerativeAIEmbeddings, ChatGoogleGenerativeAI


@lru_cache(maxsize=1)
def get_embeddings() -> GoogleGenerativeAIEmbeddings:
    """Singleton getter for GoogleGenerativeAIEmbeddings."""
    return GoogleGenerativeAIEmbeddings(
        model=settings.gemini_embedding_model,
        google_api_key=settings.google_api_key,
    )


@lru_cache(maxsize=1)
def get_llm() -> ChatGoogleGenerativeAI:
    """Singleton getter for ChatGoogleGenerativeAI."""
    return ChatGoogleGenerativeAI(
        model=settings.gemini_chat_model,
        google_api_key=settings.google_api_key,
        temperature=0.2,
        max_output_tokens=2048,
    )


@lru_cache(maxsize=1)
def get_loader_registry() -> LoaderRegistry:
    """Singleton getter for document LoaderRegistry."""
    return LoaderRegistry()


@lru_cache(maxsize=1)
def get_chunker_service() -> SemanticDocumentChunker:
    """Singleton getter for SemanticDocumentChunker."""
    return SemanticDocumentChunker(
        embeddings=get_embeddings(),
        breakpoint_type=settings.semantic_breakpoint_type,
        breakpoint_amount=settings.semantic_breakpoint_amount,
    )


@lru_cache(maxsize=1)
def get_vector_store_service() -> VectorStoreService:
    """Singleton getter for VectorStoreService."""
    return VectorStoreService(
        persist_dir=settings.chroma_persist_dir,
        collection_name=settings.chroma_collection,
        embeddings=get_embeddings(),
    )


@lru_cache(maxsize=1)
def get_retrieval_service() -> RetrievalService:
    """Singleton getter for RetrievalService."""
    return RetrievalService(
        vector_store=get_vector_store_service(),
        top_k=settings.top_k_retrieval,
        similarity_threshold=settings.similarity_threshold,
    )


@lru_cache(maxsize=1)
def get_rag_agent() -> RAGAgent:
    """Singleton getter for RAGAgent."""
    return RAGAgent(
        llm=get_llm(),
        retriever=get_retrieval_service(),
    )


def get_document_tracker(db: Session = Depends(get_db)) -> DocumentTracker:
    """Request-scoped provider for DocumentTracker (depends on SQL session)."""
    return DocumentTracker(db)


def get_ingestion_pipeline(db: Session = Depends(get_db)) -> IngestionPipeline:
    """Request-scoped provider for IngestionPipeline (depends on SQL session)."""
    return IngestionPipeline(
        tracker=get_document_tracker(db),
        loader_registry=get_loader_registry(),
        chunker=get_chunker_service(),
        vector_store=get_vector_store_service(),
        watch_dir=settings.watch_dir,
    )
