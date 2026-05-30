
SWAGGER doc: http://localhost:8000/docs



### 1. Backend Setup

```bash
cd backend
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env
# Edit .env and set your GOOGLE_API_KEY
```

### 2. Run Backend

```bash
cd backend
uvicorn main:app --reload --port 8000
```

The server starts, initializes the SQLite DB, and runs an initial document sync from `./data/watch/`.