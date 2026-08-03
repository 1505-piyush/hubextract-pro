from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Q, QuerySet

from .models import ExtractionJob
from .validators import (
    SUPPORTED_SOURCES,
    validate_api_token,
    validate_pagination_params,
    validate_source,
    validate_status_filter,
)

logger = logging.getLogger(__name__)


class ExtractionError(Exception):
    """Base exception for extraction service errors."""


class JobNotFoundError(ExtractionError):
    """Raised when a requested extraction job does not exist."""


class InvalidJobStateError(ExtractionError):
    """Raised when an action cannot be performed for a job in its current state."""


class ExtractionService:
    """Service layer for managing extraction jobs and their lifecycle."""

    @staticmethod
    def create_job(source: str, api_token: str) -> ExtractionJob:
        normalized_source = validate_source(source)
        normalized_token = validate_api_token(api_token)

        with transaction.atomic():
            job = ExtractionJob.objects.create(
                source=normalized_source,
                api_token=normalized_token,
                status="pending",
            )
        logger.info("Created extraction job %s for source %s", job.pk, normalized_source)
        return job

    @staticmethod
    def get_job(job_id: str) -> ExtractionJob:
        try:
            return ExtractionJob.objects.get(pk=job_id)
        except ExtractionJob.DoesNotExist as exc:
            raise JobNotFoundError("job not found") from exc

    @staticmethod
    def get_status(job_id: str) -> dict[str, Any]:
        job = ExtractionService.get_job(job_id)
        return {
            "job_id": str(job.pk),
            "source": job.source,
            "status": job.status,
            "created_at": job.created_at.isoformat(),
            "started_at": job.started_at.isoformat() if job.started_at else None,
            "completed_at": job.completed_at.isoformat() if job.completed_at else None,
            "total_records": job.total_records,
            "extracted_records": job.extracted_records,
        }

    @staticmethod
    def get_result(job_id: str, page: int = 1, page_size: int = 20) -> dict[str, Any]:
        job = ExtractionService.get_job(job_id)
        if job.status != "completed":
            raise InvalidJobStateError("result is only available for completed jobs")

        page_number, size = validate_pagination_params(page, page_size)
        results = job.result_data or []
        paginator = Paginator(results, size)
        page_obj = paginator.get_page(page_number)

        return {
            "job_id": str(job.pk),
            "status": job.status,
            "count": len(results),
            "page": page_obj.number,
            "page_size": size,
            "pages": paginator.num_pages,
            "results": list(page_obj.object_list),
        }

    @staticmethod
    def cancel_job(job_id: str) -> ExtractionJob:
        job = ExtractionService.get_job(job_id)
        if job.status not in {"pending", "in_progress"}:
            raise InvalidJobStateError("only pending or in_progress jobs can be cancelled")

        with transaction.atomic():
            job.status = "cancelled"
            job.completed_at = datetime.now(timezone.utc)
            job.save(update_fields=["status", "completed_at"])

        logger.info("Cancelled extraction job %s", job.pk)
        return job

    @staticmethod
    def remove_job(job_id: str) -> None:
        job = ExtractionService.get_job(job_id)
        with transaction.atomic():
            job.delete()
        logger.info("Removed extraction job %s", job.pk)

    @staticmethod
    def list_jobs(
        *,
        search: str | None = None,
        status: str | None = None,
        ordering: str = "-created_at",
        page: int = 1,
        page_size: int = 20,
    ) -> dict[str, Any]:
        normalized_status = validate_status_filter(status)
        page_number, size = validate_pagination_params(page, page_size)

        queryset: QuerySet[ExtractionJob] = ExtractionJob.objects.all()
        if search:
            queryset = queryset.filter(Q(source__icontains=search) | Q(status__icontains=search))
        if normalized_status:
            queryset = queryset.filter(status=normalized_status)

        allowed_ordering = {"created_at", "-created_at", "status", "-status", "source", "-source"}
        if ordering not in allowed_ordering:
            ordering = "-created_at"

        queryset = queryset.order_by(ordering)
        paginator = Paginator(queryset, size)
        page_obj = paginator.get_page(page_number)

        return {
            "count": paginator.count,
            "page": page_obj.number,
            "page_size": size,
            "pages": paginator.num_pages,
            "results": list(page_obj.object_list.values("id", "source", "status", "created_at", "completed_at", "total_records", "extracted_records")),
        }

    @staticmethod
    def get_statistics() -> dict[str, Any]:
        jobs = ExtractionJob.objects.all()
        total_jobs = jobs.count()
        if total_jobs == 0:
            return {
                "total_jobs": 0,
                "pending": 0,
                "running": 0,
                "completed": 0,
                "failed": 0,
                "cancelled": 0,
                "success_rate": 0.0,
                "average_execution_time_seconds": 0.0,
            }

        pending = jobs.filter(status="pending").count()
        running = jobs.filter(status="in_progress").count()
        completed = jobs.filter(status="completed").count()
        failed = jobs.filter(status="failed").count()
        cancelled = jobs.filter(status="cancelled").count()

        completed_jobs = jobs.filter(status="completed")
        durations: list[float] = []
        for job in completed_jobs:
            if job.started_at and job.completed_at:
                delta = (job.completed_at - job.started_at).total_seconds()
                if delta >= 0:
                    durations.append(delta)

        average_execution_time = sum(durations) / len(durations) if durations else 0.0
        success_rate = round((completed / total_jobs) * 100, 2) if total_jobs else 0.0

        return {
            "total_jobs": total_jobs,
            "pending": pending,
            "running": running,
            "completed": completed,
            "failed": failed,
            "cancelled": cancelled,
            "success_rate": success_rate,
            "average_execution_time_seconds": round(average_execution_time, 2),
        }
