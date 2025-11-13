"""
Celery configuration for asynchronous task processing
"""
from celery import Celery
import os

# Get Redis URL for Celery broker
redis_url = os.getenv("REDIS_PUBLIC_URL") or os.getenv("REDIS_URL", "redis://localhost:6379/0")

# Create Celery app
celery_app = Celery(
    "acme_importer",
    broker=redis_url,
    backend=redis_url,
    include=["app.tasks"]
)

# Celery configuration
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=7200,  # 2 hours max
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=1000,
)