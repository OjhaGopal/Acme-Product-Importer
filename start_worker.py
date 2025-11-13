#!/usr/bin/env python3
"""
Start Celery worker for processing tasks
"""
from app.celery_app import celery_app

if __name__ == "__main__":
    celery_app.start()