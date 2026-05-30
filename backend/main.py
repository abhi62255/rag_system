import logging
import os
from contextlib import asynccontextmanager

from apscheduler.schedulers.background import BackgroundScheduler
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import settings
from models.db import init_db
from api.chat import router as chat_router
from api.admin import router as admin_router
from pipelines.ingestion.sync import run_sync

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

scheduler = BackgroundScheduler()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    settings.ensure_dirs()
    init_db()
    logger.info("Database initialized")

    # Schedule daily ingestion sync
    scheduler.add_job(
        run_sync,
        trigger="cron",
        hour=settings.ingestion_schedule_hour,
        minute=settings.ingestion_schedule_minute,
        id="daily_sync",
        replace_existing=True,
    )
    scheduler.start()
    logger.info(
        f"Ingestion scheduler started — runs daily at "
        f"{settings.ingestion_schedule_hour:02d}:{settings.ingestion_schedule_minute:02d} UTC"
    )

    # Run initial sync on startup
    logger.info("Running initial ingestion sync on startup...")
    try:
        stats = run_sync()
        logger.info(f"Startup sync complete: {stats}")
    except Exception as e:
        logger.warning(f"Startup sync failed (non-fatal): {e}")

    yield

    # Shutdown
    scheduler.shutdown(wait=False)
    logger.info("Scheduler stopped")


app = FastAPI(
    title="RAG System API",
    description="Retrieval-Augmented Generation with Gemini + ChromaDB",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat_router, prefix="/api")
app.include_router(admin_router, prefix="/api")


@app.get("/health")
def health():
    return {"status": "ok", "version": "1.0.0"}
