from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from celery import shared_task
from django.conf import settings
from redis import Redis
from redis.exceptions import ConnectionError, RedisError, TimeoutError

from .models import ExtractionJob
from .providers import get_extractor
from .webhooks import send_webhook

logger = logging.getLogger(__name__)


def dispatch_job(job_id: str) -> Any:
    """Dispatch a background job, falling back to inline execution when Redis is unavailable."""
    try:
        client = Redis.from_url(settings.CELERY_BROKER_URL, socket_connect_timeout=1)
        client.ping()
        return process_job.apply_async(args=[job_id], queue="default")
    except (ConnectionError, RedisError, TimeoutError, OSError, ValueError) as exc:
        logger.warning("Redis broker unavailable for job %s; running inline: %s", job_id, exc)
        return process_job(job_id)


@shared_task(bind=True, name="extraction.process_job")
def process_job(self: Any, job_id: str) -> dict[str, Any]:
    """Process an extraction job asynchronously and persist the result."""
    try:
        job = ExtractionJob.objects.get(pk=job_id)
    except ExtractionJob.DoesNotExist:
        logger.warning("Background job skipped because job %s no longer exists", job_id)
        return {"status": "missing"}

    if job.status == "cancelled":
        logger.info("Skipping cancelled job %s", job_id)
        return {"status": "cancelled"}

    job.status = "in_progress"
    job.started_at = datetime.now(timezone.utc)
    job.save(update_fields=["status", "started_at"])

    extractor = get_extractor(job.source)
    records: list[dict[str, Any]] = []
    last_error: str | None = None

    for attempt in range(3):
        try:
            records = extractor.extract(job.api_token)
            break
        except RuntimeError as exc:
            last_error = str(exc)
            logger.warning("Extraction provider failed for job %s on attempt %s: %s", job_id, attempt + 1, exc)
            if attempt < 2:
                continue

    if records:
        job.total_records = len(records)
        job.extracted_records = len(records)
        job.result_data = records
        job.status = "completed"
        job.completed_at = datetime.now(timezone.utc)
        job.save(update_fields=["status", "total_records", "extracted_records", "result_data", "completed_at"])
        send_webhook(
            settings.WEBHOOK_URL,
            {"event": "job.completed", "job_id": str(job.pk), "status": job.status},
        )
        logger.info("Completed background extraction job %s", job_id)
        return {"status": "completed", "job_id": job_id}

    job.total_records = 0
    job.extracted_records = 0
    job.result_data = []
    job.status = "failed"
    job.completed_at = datetime.now(timezone.utc)
    job.save(update_fields=["status", "total_records", "extracted_records", "result_data", "completed_at"])
    send_webhook(
        settings.WEBHOOK_URL,
        {"event": "job.failed", "job_id": str(job.pk), "status": job.status, "error": last_error},
    )
    logger.warning("Failed background extraction job %s: %s", job_id, last_error)
    return {"status": "failed", "job_id": job_id, "error": last_error}
