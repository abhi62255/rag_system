# RAG Knowledge Assistant

A production-grade Retrieval-Augmented Generation system using **Google Gemini**, **ChromaDB**, **LangGraph**, and **React**.

## Architecture

```
Frontend (React + Vite)
    └── POST /api/chat → FastAPI → LangGraph Graph
                                    ├── rewrite_query  (Gemini)
                                    ├── retrieve       (ChromaDB cosine search)
                                    └── generate       (Gemini + conversation history)

Ingestion Pipeline (APScheduler — daily)
    └── watch/ folder scan
        ├── New file    → Load → SemanticChunk → Embed → ChromaDB + SQLite
        ├── Modified    → Delete old chunks → Re-ingest
        └── Deleted     → Delete chunks from ChromaDB → Mark SQLite deleted
```

## Tech Stack

| Component     | Technology                                 |
|---------------|--------------------------------------------|
| LLM           | `gemini-1.5-flash` (Google Generative AI)  |
| Embeddings    | `models/embedding-001` (Google)            |
| Vector DB     | ChromaDB (persistent file mode)            |
| Tracking DB   | SQLite via SQLAlchemy                      |
| Chunking      | `SemanticChunker` (LangChain Experimental) |
| Graph / Agent | LangGraph `StateGraph` + MemorySaver       |
| Backend       | FastAPI + APScheduler                      |
| Frontend      | React 18 + Vite + Tailwind CSS             |

## Quickstart

### 1. Prerequisites

- Python 3.11+
- Node.js 20+
- A Google Gemini API key → [aistudio.google.com](https://aistudio.google.com)

### 2. Backend Setup

```bash
cd backend
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env
# Edit .env and set your GOOGLE_API_KEY
```

### 3. Run Backend

```bash
cd backend
 .venv\Scripts\Activate.ps1
uvicorn main:app --reload --port 8000
```

The server starts, initializes the SQLite DB, and runs an initial document sync from `./data/watch/`.

### 4. Frontend Setup

```bash
cd frontend
npm install
npm run dev
```

Open [http://localhost:5173](http://localhost:5173)

### 5. Ingest Documents

**Option A — Drop files in the watch folder:**
```bash
cp your-documents/*.pdf ./data/watch/
# Trigger manual sync via UI "Sync Now" button, or wait for daily schedule
```

**Option B — Upload via UI:**
Click "Upload" in the sidebar to directly upload and ingest a file.

**Option C — API:**
```bash
curl -X POST http://localhost:8000/api/admin/ingest/trigger
```

## API Reference

### Chat
```
POST /api/chat
Body:  { "message": "string", "session_id": "uuid" }
Response: { "answer": "string", "sources": [...], "session_id": "uuid" }
```

### Admin
```
GET    /api/admin/documents          # List all tracked documents
GET    /api/admin/stats              # ChromaDB + DB stats
POST   /api/admin/ingest/trigger     # Manually trigger full sync
POST   /api/admin/ingest/upload      # Upload and ingest a file
DELETE /api/admin/documents/{id}     # Remove document + its chunks
```

## Supported File Types

| Format      | Extension(s)        |
|-------------|---------------------|
| PDF         | `.pdf`              |
| Word        | `.docx`, `.doc`     |
| Web / HTML  | `.html`, `.htm`     |
| Plain Text  | `.txt`, `.md`       |

## File Lifecycle

```
File added    → hash computed → chunks stored in ChromaDB → tracked in SQLite (status=active)
File modified → hash mismatch → old chunks deleted → re-ingested → version incremented
File deleted  → chunk_ids from SQLite → deleted from ChromaDB → status=deleted
```

## Docker Compose

```bash
cp backend/.env.example .env
# Set GOOGLE_API_KEY in .env

docker-compose up --build
```

- Frontend: http://localhost:5173
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/docs

## Project Structure

```
rag-system/
├── backend/
│   ├── main.py                           # FastAPI app + scheduler
│   ├── config.py                         # Pydantic settings
│   ├── models/db.py                      # SQLAlchemy models
│   ├── pipelines/
│   │   ├── ingestion/
│   │   │   ├── file_tracker.py           # SQLite CRUD
│   │   │   ├── loaders.py                # PDF/DOCX/HTML/TXT loaders
│   │   │   ├── chunker.py                # Gemini SemanticChunker
│   │   │   ├── vector_store.py           # ChromaDB operations
│   │   │   └── sync.py                   # Orchestrator (new/modified/deleted)
│   │   └── retrieval/
│   │       ├── prompts.py                # LangChain prompt templates
│   │       ├── retriever.py              # Cosine similarity search
│   │       └── graph.py                  # LangGraph StateGraph
│   └── api/
│       ├── chat.py                       # POST /chat
│       └── admin.py                      # Admin endpoints
├── frontend/
│   └── src/
│       ├── App.jsx                       # Root layout
│       ├── hooks/useChat.js              # Chat state + session mgmt
│       ├── api/chat.js                   # Axios API client
│       └── components/
│           ├── ChatWindow.jsx            # Message list
│           ├── MessageBubble.jsx         # Markdown message with sources
│           ├── InputBar.jsx              # Textarea + send
│           └── Sidebar.jsx               # Files + sync + upload
├── data/
│   └── watch/                            # Drop files here for ingestion
└── docker-compose.yml
```


## Configuration (`.env`)

| Variable                    | Default              | Description                          |
|-----------------------------|----------------------|--------------------------------------|
| `GOOGLE_API_KEY`            | *required*           | Gemini API key                       |
| `CHROMA_PERSIST_DIR`        | `./data/chroma`      | ChromaDB storage path                |
| `CHROMA_COLLECTION`         | `rag_docs`           | Collection name                      |
| `WATCH_DIR`                 | `./data/watch`       | Folder to watch for documents        |
| `TRACKING_DB_URL`           | `sqlite:///./data/tracking.db` | SQLite path               |
| `TOP_K_RETRIEVAL`           | `5`                  | Number of chunks to retrieve         |
| `SIMILARITY_THRESHOLD`      | `0.4`                | Minimum cosine similarity (0–1)      |
| `SEMANTIC_BREAKPOINT_TYPE`  | `percentile`         | `percentile` or `standard_deviation` |
| `SEMANTIC_BREAKPOINT_AMOUNT`| `95`                 | Breakpoint percentile                |
| `INGESTION_SCHEDULE_HOUR`   | `2`                  | Daily sync hour (UTC)                |
| `INGESTION_SCHEDULE_MINUTE` | `0`                  | Daily sync minute (UTC)              |
