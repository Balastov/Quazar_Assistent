import os
import sys

from celery import Celery

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "apps", "api"))

from config import get_settings

settings = get_settings()

app = Celery(
    "quazar",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=["workers.tasks"],
)

app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
)

app.conf.beat_schedule = {
    "confluence-sync-hourly": {
        "task": "workers.tasks.sync_all_confluence_bindings",
        "schedule": 3600.0,
    },
}
