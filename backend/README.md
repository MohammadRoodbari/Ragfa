# RAGfa — Backend

FastAPI service for hybrid kNN + BM25 retrieval with LLM-powered generation and multi-turn conversation memory.

---

## Stack

| | |
|---|---|
| API | FastAPI + Uvicorn / Gunicorn |
| Task queue | Celery 5 → RabbitMQ (broker) · Redis DB1 (results) |
| Cache / sessions | Redis DB0 — conversation history + job status |
| Search | Elasticsearch 9 |
| LLM | Ollama · OpenAI |

---

## Quick Start

```bash
cp .env.example .env                                                # fill in ES_HOST, OLLAMA_MODEL at minimum
uvicorn backend.app.main:app --reload --host 0.0.0.0 --port 8000    # FastAPI on :8000 with hot-reload
```

Swagger UI → http://localhost:8000/docs

---

## Endpoints

| Method | Path | Description |
|---|---|---|
| `GET` | `/health` | ES + Redis liveness check |
| `POST` | `/api/v1/ingest/file` | Upload PDF or DOCX → returns `task_id` (202) |
| `POST` | `/api/v1/ingest/text` | Index raw text → returns `task_id` (202) |
| `GET` | `/api/v1/ingest/jobs/{task_id}` | Poll job state: `PENDING → STARTED → SUCCESS\|FAILURE` |
| `POST` | `/api/v1/query` | Full answer + attributed source chunks |
| `POST` | `/api/v1/query/stream` | Same, streamed token-by-token via SSE |

---

## Conversation Memory

Pass a `session_id` in any query request. The backend loads that session's history from Redis, sends it to the LLM, then appends the new turn. Sessions expire after `CHAT_TTL_SECONDS` (default 2 h) and are capped at `CHAT_MAX_HISTORY_TURNS` (default 20) pairs.

Omit `session_id` for stateless, one-shot queries.

---

## Ingest Flow

```
POST /ingest/file  →  save tmp file  →  enqueue Celery task  →  202 { task_id }
                                                ↓
                                        RabbitMQ → Worker
                                        chunk · embed · NER · ES index
                                        mirror status to Redis
```

Tasks auto-retry 3× on failure. Worker config: `task_acks_late=True`, `task_reject_on_worker_lost=True`.

---

## Key Config

Full variable list in `.env.example`.

---