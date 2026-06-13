# Ragfa

**Intelligent Persian document retrieval and question answering with RAG.**

Ragfa is a full-stack system for ingesting Persian (and multilingual) documents and answering questions over them using a hybrid retrieval pipeline — combining dense kNN vector search with BM25 — backed by an LLM for generation with multi-turn conversation memory.

---

## Architecture

```
frontend/   React + Vite UI
backend/    FastAPI service · Celery workers · Redis · RabbitMQ
src/        Core RAG library (indexing · retrieval · generation)
config/     Shared configuration
```

### Indexing flow

```
PDF / DOCX / Text ─► extract ─► chunk ─► embed ─► Elasticsearch
```

### Query flow

```
Question ─► Query Condenser (last 5 turns) ─► Hybrid Retrieve ─► LLM Generate ─► Answer + Sources
```

---

## Stack

| Layer | Tech |
|---|---|
| Frontend | React 18, Vite |
| Backend | FastAPI, Uvicorn/Gunicorn |
| Task queue | Celery 5 → RabbitMQ (broker) · Redis (results) |
| Sessions / cache | Redis |
| Search | Elasticsearch 9 (kNN + BM25) |
| Embedding | Ollama (`qwen3-embedding:4b`) or OpenAI |
| LLM | Ollama or OpenAI (`gpt-4o-mini`) |

---

## Quick Start

### 1. Configure

```bash
cp .env.example .env
# set LLM_PROVIDER, OPENAI_API_KEY / OLLAMA_BASE_URL at minimum
```

### 2. Start services

```bash
docker compose up -d
```

### Services & ports

| Service | URL | Notes |
|---|---|---|
| Frontend | http://localhost:3001 | React UI (Nginx) |
| Backend API | http://localhost:8000 | FastAPI · Swagger at `/docs` |
| Elasticsearch | http://localhost:9200 | |
| Redis | localhost:6379 | |
| RabbitMQ | http://localhost:15672 | Management UI (`guest` / `guest`) |
| Ollama | http://localhost:11434 | GPU-accelerated if available |

---

## Using the RAG library directly

### Indexing a document

```python
from src.indexing.pipeline import IndexingPipeline

pipeline = IndexingPipeline.build()
pipeline.run_file("path/to/document.docx")
```

### Querying

```python
from src.rag.pipeline import RAGPipeline, RAGRequest

pipeline = RAGPipeline.build()
request  = RAGRequest(question="Your question here")

# Blocking
response = pipeline.run(request)

# Streaming
for token in pipeline.stream(request):
    print(token, end="", flush=True)
```

---

## API

The backend exposes a REST API at `http://localhost:8000` (Swagger UI at `/docs`).

| Method | Path | Description |
|---|---|---|
| `GET` | `/health` | ES + Redis liveness |
| `POST` | `/api/v1/ingest/file` | Upload PDF or DOCX → `task_id` |
| `POST` | `/api/v1/ingest/text` | Index raw text → `task_id` |
| `GET` | `/api/v1/ingest/jobs/{task_id}` | Poll job state |
| `POST` | `/api/v1/query` | Blocking answer + source chunks |
| `POST` | `/api/v1/query/stream` | Streaming answer via SSE |

Pass a `session_id` in query requests to enable multi-turn conversation memory (sessions expire after 2 h, capped at 5 history turns by default).

---

## Key Configuration

| Variable | Default | Description |
|---|---|---|
| `ES_HOST` | `http://elasticsearch:9200` | Elasticsearch URL |
| `EMBEDDING_PROVIDER` | `ollama` | `ollama` or `openai` |
| `EMBEDDING_MODEL` | `qwen3-embedding:4b` | Embedding model name |
| `LLM_PROVIDER` | `openai` | `ollama` or `openai` |
| `LLM_MODEL` | `gpt-4o-mini` | LLM model name |
| `CHUNK_SIZE` | `1500` | Characters per chunk |
| `RETRIEVAL_TOP_K` | `15` | Candidates fetched before reranking |
| `RERANK_TOP_N` | `3` | Chunks passed to LLM |
| `CHAT_MAX_HISTORY_TURNS` | `5` | Turns kept in session memory |
| `UPLOAD_MAX_BYTES` | `52428800` | Max upload size (50 MB) |

See `.env.example` for the full list.

---

## Frontend

The React UI runs at `http://localhost:5173` in development. It proxies all API calls to the backend automatically. See [`frontend/README.md`](frontend/README.md) for details.