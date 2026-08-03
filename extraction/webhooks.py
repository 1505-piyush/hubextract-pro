from __future__ import annotations

import logging
from typing import Any

import requests

logger = logging.getLogger(__name__)


def send_webhook(url: str | None, payload: dict[str, Any]) -> None:
    """Send a JSON payload to a webhook endpoint when configured."""
    if not url:
        return

    try:
        requests.post(url, json=payload, timeout=5)
    except requests.RequestException as exc:
        logger.warning("Webhook delivery failed: %s", exc)
