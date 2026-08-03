from __future__ import annotations

from typing import Any

SUPPORTED_SOURCES = ("hubspot", "github", "salesforce", "jira")


def validate_source(value: str) -> str:
    if not value or not str(value).strip():
        raise ValueError("source is required")

    normalized = str(value).strip().lower()
    if normalized not in SUPPORTED_SOURCES:
        raise ValueError(f"unsupported source: {value}")

    return normalized


def validate_api_token(value: str) -> str:
    if not value or not str(value).strip():
        raise ValueError("api_token is required")

    token = str(value).strip()
    if len(token) < 6:
        raise ValueError("api_token must be at least 6 characters")

    return token


def validate_status_filter(value: str | None) -> str | None:
    if not value:
        return None

    normalized = str(value).strip().lower()
    valid_statuses = {choice[0] for choice in [
        ("pending", "Pending"),
        ("in_progress", "In Progress"),
        ("completed", "Completed"),
        ("failed", "Failed"),
        ("cancelled", "Cancelled"),
    ]}
    if normalized not in valid_statuses:
        raise ValueError("invalid status filter")
    return normalized


def validate_pagination_params(page: Any, page_size: Any) -> tuple[int, int]:
    try:
        page_number = int(page or 1)
    except (TypeError, ValueError) as exc:
        raise ValueError("page must be an integer") from exc

    try:
        size = int(page_size or 20)
    except (TypeError, ValueError) as exc:
        raise ValueError("page_size must be an integer") from exc

    if page_number < 1:
        raise ValueError("page must be greater than or equal to 1")
    if size < 1 or size > 100:
        raise ValueError("page_size must be between 1 and 100")

    return page_number, size
