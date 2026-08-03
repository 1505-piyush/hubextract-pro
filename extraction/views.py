from __future__ import annotations

import logging
from typing import Any

from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.request import Request
from rest_framework.response import Response

from .serializers import (
    CancelScanSerializer,
    ExtractionJobSerializer,
    ScanStartSerializer,
    ScanStatusSerializer,
)
from .services import (
    ExtractionService,
    InvalidJobStateError,
    JobNotFoundError,
)
from .tasks import dispatch_job

logger = logging.getLogger(__name__)


@api_view(["POST"])
def start_scan(request: Request) -> Response:
    """Create a new extraction job and return its identifier."""
    serializer = ScanStartSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    try:
        job = ExtractionService.create_job(
            source=serializer.validated_data["source"],
            api_token=serializer.validated_data["api_token"],
        )
    except ValueError as exc:
        logger.warning("Invalid scan start payload: %s", exc)
        return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

    try:
        dispatch_job(str(job.pk))
    except Exception as exc:  # pragma: no cover - safety fallback for missing broker
        logger.warning("Background task dispatch failed for job %s: %s", job.pk, exc)

    return Response(
        {"job_id": str(job.pk), "status": job.status, "message": "scan job created"},
        status=status.HTTP_201_CREATED,
    )


@api_view(["GET"])
def get_scan_status(request: Request, job_id: str) -> Response:
    """Return the current state of a scan job."""
    serializer = ScanStatusSerializer(data={"job_id": job_id})
    serializer.is_valid(raise_exception=True)

    try:
        payload = ExtractionService.get_status(str(serializer.validated_data["job_id"]))
    except JobNotFoundError as exc:
        logger.warning("Status lookup failed for job %s: %s", job_id, exc)
        return Response({"detail": str(exc)}, status=status.HTTP_404_NOT_FOUND)

    return Response(payload, status=status.HTTP_200_OK)


@api_view(["GET"])
def get_scan_result(request: Request, job_id: str) -> Response:
    """Return paginated extraction results for a completed job."""
    serializer = ScanStatusSerializer(data={"job_id": job_id})
    serializer.is_valid(raise_exception=True)

    page = request.query_params.get("page", 1)
    page_size = request.query_params.get("page_size", 20)

    try:
        payload = ExtractionService.get_result(str(serializer.validated_data["job_id"]), page=page, page_size=page_size)
    except JobNotFoundError as exc:
        logger.warning("Result lookup failed for job %s: %s", job_id, exc)
        return Response({"detail": str(exc)}, status=status.HTTP_404_NOT_FOUND)
    except InvalidJobStateError as exc:
        logger.warning("Result retrieval blocked for job %s: %s", job_id, exc)
        return Response({"detail": str(exc)}, status=status.HTTP_409_CONFLICT)

    return Response(payload, status=status.HTTP_200_OK)


@api_view(["POST"])
def cancel_scan(request: Request, job_id: str) -> Response:
    """Cancel a pending or in-progress scan job."""
    serializer = CancelScanSerializer(data={"job_id": job_id})
    serializer.is_valid(raise_exception=True)

    try:
        job = ExtractionService.cancel_job(str(serializer.validated_data["job_id"]))
    except JobNotFoundError as exc:
        logger.warning("Cancel failed for job %s: %s", job_id, exc)
        return Response({"detail": str(exc)}, status=status.HTTP_404_NOT_FOUND)
    except InvalidJobStateError as exc:
        logger.warning("Cancel blocked for job %s: %s", job_id, exc)
        return Response({"detail": str(exc)}, status=status.HTTP_409_CONFLICT)

    return Response(
        {"job_id": str(job.pk), "status": job.status, "message": "scan job cancelled"},
        status=status.HTTP_200_OK,
    )


@api_view(["DELETE"])
def remove_scan(request: Request, job_id: str) -> Response:
    """Delete a scan job and its associated records."""
    serializer = CancelScanSerializer(data={"job_id": job_id})
    serializer.is_valid(raise_exception=True)

    try:
        ExtractionService.remove_job(str(serializer.validated_data["job_id"]))
    except JobNotFoundError as exc:
        logger.warning("Remove failed for job %s: %s", job_id, exc)
        return Response({"detail": str(exc)}, status=status.HTTP_404_NOT_FOUND)

    return Response(status=status.HTTP_204_NO_CONTENT)


@api_view(["GET"])
def list_jobs(request: Request) -> Response:
    """Return a paginated list of scan jobs with search and filter support."""
    search = request.query_params.get("search")
    status_filter = request.query_params.get("status")
    ordering = request.query_params.get("ordering", "-created_at")
    page = request.query_params.get("page", 1)
    page_size = request.query_params.get("page_size", 20)

    try:
        payload = ExtractionService.list_jobs(
            search=search,
            status=status_filter,
            ordering=ordering,
            page=page,
            page_size=page_size,
        )
    except ValueError as exc:
        return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

    return Response(payload, status=status.HTTP_200_OK)


@api_view(["GET"])
def get_statistics(request: Request) -> Response:
    """Return aggregate statistics for all scan jobs."""
    return Response(ExtractionService.get_statistics(), status=status.HTTP_200_OK)
