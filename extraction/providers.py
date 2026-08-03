from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import Any

import requests
from django.conf import settings

logger = logging.getLogger(__name__)


class BaseExtractor(ABC):
    """Abstract base for extraction providers."""

    @abstractmethod
    def extract(self, api_token: str) -> list[dict[str, Any]]:
        """Return extracted records for the provider."""


class HubSpotExtractor(BaseExtractor):
    """Extractor that calls the HubSpot CRM API."""

    def extract(self, api_token: str) -> list[dict[str, Any]]:
        headers = {"Authorization": f"Bearer {api_token}", "Content-Type": "application/json"}
        api_url = getattr(settings, "HUBSPOT_API_URL", "https://api.hubapi.com/crm/v3/objects/contacts")
        api_limit = getattr(settings, "HUBSPOT_API_LIMIT", 5)
        timeout = getattr(settings, "HUBSPOT_TIMEOUT_SECONDS", 10)
        request_url = f"{api_url}?limit={api_limit}" if "?" not in api_url else f"{api_url}&limit={api_limit}"

        try:
            response = requests.get(
                request_url,
                headers=headers,
                timeout=timeout,
            )
            response.raise_for_status()
        except requests.RequestException as exc:
            logger.warning("HubSpot extraction failed: %s", exc)
            raise RuntimeError("HubSpot API request failed") from exc

        payload = response.json()
        results: list[dict[str, Any]] = []
        for item in payload.get("results", [])[:api_limit]:
            properties = item.get("properties", {})
            results.append(
                {
                    "id": item.get("id"),
                    "firstname": properties.get("firstname", ""),
                    "lastname": properties.get("lastname", ""),
                    "email": properties.get("email", ""),
                    "source": "hubspot",
                }
            )
        return results


class SampleExtractor(BaseExtractor):
    """Fallback extractor used for local development and tests."""

    def extract(self, api_token: str) -> list[dict[str, Any]]:
        return [
            {"id": "sample-1", "name": "Sample Record A", "source": "sample"},
            {"id": "sample-2", "name": "Sample Record B", "source": "sample"},
        ]


def get_extractor(source: str) -> BaseExtractor:
    if source == "hubspot":
        return HubSpotExtractor()
    return SampleExtractor()
