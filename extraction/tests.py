from unittest.mock import patch

from django.test import override_settings
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from .models import ExtractionJob
from .providers import HubSpotExtractor


class ScanApiTests(APITestCase):
    def test_start_scan_creates_pending_job(self):
        response = self.client.post(
            reverse("scan-start"),
            {"source": "hubspot", "api_token": "token-123456"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(ExtractionJob.objects.filter(pk=response.data["job_id"]).exists())
        job = ExtractionJob.objects.get(pk=response.data["job_id"])
        self.assertIn(job.status, {"pending", "completed", "in_progress", "failed"})

    def test_status_and_result_endpoints_work(self):
        job = ExtractionJob.objects.create(
            source="hubspot",
            api_token="token-123456",
            status="completed",
            extracted_records=2,
            total_records=2,
            result_data=[{"id": "1", "name": "Acme"}, {"id": "2", "name": "Globex"}],
        )

        status_response = self.client.get(reverse("scan-status", args=[job.pk]))
        self.assertEqual(status_response.status_code, status.HTTP_200_OK)
        self.assertEqual(status_response.data["status"], "completed")

        result_response = self.client.get(reverse("scan-result", args=[job.pk]))
        self.assertEqual(result_response.status_code, status.HTTP_200_OK)
        self.assertEqual(result_response.data["count"], 2)

    def test_cancel_and_remove_job(self):
        job = ExtractionJob.objects.create(source="hubspot", api_token="token-123456", status="pending")

        cancel_response = self.client.post(reverse("scan-cancel", args=[job.pk]))
        self.assertEqual(cancel_response.status_code, status.HTTP_200_OK)
        job.refresh_from_db()
        self.assertEqual(job.status, "cancelled")

        remove_response = self.client.delete(reverse("scan-remove", args=[job.pk]))
        self.assertEqual(remove_response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(ExtractionJob.objects.filter(pk=job.pk).exists())

    def test_jobs_list_and_statistics_endpoints(self):
        ExtractionJob.objects.create(source="hubspot", api_token="token-123456", status="pending")
        ExtractionJob.objects.create(source="hubspot", api_token="token-123456", status="completed")
        ExtractionJob.objects.create(source="github", api_token="token-123456", status="failed")

        list_response = self.client.get(reverse("jobs-list"), {"search": "hubspot", "status": "completed"})
        self.assertEqual(list_response.status_code, status.HTTP_200_OK)
        self.assertEqual(list_response.data["count"], 1)

        stats_response = self.client.get(reverse("jobs-statistics"))
        self.assertEqual(stats_response.status_code, status.HTTP_200_OK)
        self.assertEqual(stats_response.data["total_jobs"], 3)
        self.assertEqual(stats_response.data["completed"], 1)

    def test_start_scan_processes_job_in_background(self):
        response = self.client.post(
            reverse("scan-start"),
            {"source": "hubspot", "api_token": "token-123456"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        job = ExtractionJob.objects.get(pk=response.data["job_id"])
        self.assertIn(job.status, {"completed", "failed"})
        self.assertGreaterEqual(job.extracted_records, 0)

    @override_settings(HUBSPOT_API_URL="https://example.test/contacts", HUBSPOT_API_LIMIT=3, HUBSPOT_TIMEOUT_SECONDS=7)
    @patch("extraction.providers.requests.get")
    def test_hubspot_extractor_uses_configured_settings(self, mock_get):
        mock_response = mock_get.return_value
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {
            "results": [
                {
                    "id": "1",
                    "properties": {"firstname": "Ada", "lastname": "Lovelace", "email": "ada@example.com"},
                }
            ]
        }

        extractor = HubSpotExtractor()
        records = extractor.extract("test-token")

        self.assertEqual(records[0]["email"], "ada@example.com")
        mock_get.assert_called_once_with(
            "https://example.test/contacts?limit=3",
            headers={"Authorization": "Bearer test-token", "Content-Type": "application/json"},
            timeout=7,
        )
