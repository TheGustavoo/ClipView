import os

from celery import Celery

broker_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")

celery_app = Celery(
    "clipview",
    broker=broker_url,
    backend=broker_url,
    include=["app.tasks.processing"],
)
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    task_time_limit=3 * 60 * 60,
    task_soft_time_limit=2 * 60 * 60 + 50 * 60,
)
