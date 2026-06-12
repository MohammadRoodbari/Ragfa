"""
Celery application factory.

Broker  : RabbitMQ  (AMQP)
Backend : Redis     (separate DB from the chat cache)

Import this module to get the ready-to-use Celery app:

    from app.workers.celery_app import celery_app

Worker startup:
    celery -A app.workers.celery_app worker --loglevel=info --concurrency=4
"""
from __future__ import annotations

from celery import Celery

from backend.app.core.config import get_settings

settings = get_settings()

celery_app = Celery(
    "rag_worker",
    broker=settings.RABBITMQ_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=[
        "backend.app.workers.ingest_tasks",
    ],
)

# ── Configuration ─────────────────────────────────────────────────────────────
celery_app.conf.update(
    # Serialisation
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],

    # Reliability
    task_acks_late=True,               # ack only after task completes
    task_reject_on_worker_lost=True,   # requeue if worker dies mid-task
    worker_prefetch_multiplier=1,      # fair dispatch; one task at a time per worker

    # Timeouts
    task_soft_time_limit=settings.CELERY_TASK_TIMEOUT,
    task_time_limit=settings.CELERY_TASK_TIMEOUT + 30,

    # Result expiry
    result_expires=settings.JOB_TTL_SECONDS,

    # Routing — all ingest tasks go to the dedicated queue
    task_routes={
        "backend.app.workers.ingest_tasks.*": {"queue": "ingest"},
    },

    # Timezone
    timezone="UTC",
    enable_utc=True,
)