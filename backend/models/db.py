import json
from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Text, DateTime, create_engine, event
)
from sqlalchemy.orm import DeclarativeBase, sessionmaker, Session
from config import settings


class Base(DeclarativeBase):
    pass


class TrackedDocument(Base):
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, autoincrement=True)
    filename = Column(String(512), nullable=False)
    filepath = Column(String(1024), nullable=False, unique=True)
    file_hash = Column(String(64), nullable=False)
    version = Column(Integer, default=1)
    status = Column(String(20), default="active")   # active | deleted | failed
    doc_type = Column(String(10), nullable=True)    # pdf | docx | html | txt
    chunk_ids = Column(Text, default="[]")          # JSON array of ChromaDB chunk IDs
    chunk_count = Column(Integer, default=0)
    ingested_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    deleted_at = Column(DateTime, nullable=True)
    error_message = Column(Text, nullable=True)

    def get_chunk_ids(self) -> list[str]:
        try:
            return json.loads(self.chunk_ids or "[]")
        except (json.JSONDecodeError, TypeError):
            return []

    def set_chunk_ids(self, ids: list[str]):
        self.chunk_ids = json.dumps(ids)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "filename": self.filename,
            "filepath": self.filepath,
            "file_hash": self.file_hash,
            "version": self.version,
            "status": self.status,
            "doc_type": self.doc_type,
            "chunk_count": self.chunk_count,
            "ingested_at": self.ingested_at.isoformat() if self.ingested_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "deleted_at": self.deleted_at.isoformat() if self.deleted_at else None,
            "error_message": self.error_message,
        }


engine = create_engine(
    settings.tracking_db_url,
    connect_args={"check_same_thread": False},
)

# Enable WAL mode for SQLite concurrency
@event.listens_for(engine, "connect")
def set_sqlite_pragma(dbapi_conn, connection_record):
    cursor = dbapi_conn.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.close()

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db():
    Base.metadata.create_all(bind=engine)


def get_db() -> Session:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
