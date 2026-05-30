from pydantic_settings import BaseSettings
from pydantic import Field
from typing import List
import os


class Settings(BaseSettings):
    google_api_key: str = Field(..., env="GOOGLE_API_KEY")

    chroma_persist_dir: str = Field("./data/chroma", env="CHROMA_PERSIST_DIR")
    chroma_collection: str = Field("rag_docs", env="CHROMA_COLLECTION")

    watch_dir: str = Field("./data/watch", env="WATCH_DIR")
    tracking_db_url: str = Field("sqlite:///./data/tracking.db", env="TRACKING_DB_URL")

    ingestion_schedule_hour: int = Field(2, env="INGESTION_SCHEDULE_HOUR")
    ingestion_schedule_minute: int = Field(0, env="INGESTION_SCHEDULE_MINUTE")

    top_k_retrieval: int = Field(5, env="TOP_K_RETRIEVAL")
    similarity_threshold: float = Field(0.4, env="SIMILARITY_THRESHOLD")

    semantic_breakpoint_type: str = Field("percentile", env="SEMANTIC_BREAKPOINT_TYPE")
    semantic_breakpoint_amount: float = Field(95.0, env="SEMANTIC_BREAKPOINT_AMOUNT")

    cors_origins: List[str] = Field(
        default=["http://localhost:5173", "http://localhost:3000"],
        env="CORS_ORIGINS",
    )

    gemini_chat_model: str = Field("gemini-2.5-flash", env="GEMINI_CHAT_MODEL")
    gemini_embedding_model: str = Field("models/gemini-embedding-001", env="GEMINI_EMBEDDING_MODEL")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

    def ensure_dirs(self):
        os.makedirs(self.watch_dir, exist_ok=True)
        os.makedirs(self.chroma_persist_dir, exist_ok=True)
        os.makedirs(os.path.dirname(self.tracking_db_url.replace("sqlite:///", "")), exist_ok=True)


settings = Settings()
