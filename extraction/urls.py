from django.urls import path

from .views import (
    cancel_scan,
    get_scan_result,
    get_scan_status,
    get_statistics,
    list_jobs,
    remove_scan,
    start_scan,
)

urlpatterns = [
    path("scan/start/", start_scan, name="scan-start"),
    path("scan/status/<uuid:job_id>/", get_scan_status, name="scan-status"),
    path("scan/result/<uuid:job_id>/", get_scan_result, name="scan-result"),
    path("scan/cancel/<uuid:job_id>/", cancel_scan, name="scan-cancel"),
    path("scan/remove/<uuid:job_id>/", remove_scan, name="scan-remove"),
    path("jobs/jobs/", list_jobs, name="jobs-list"),
    path("jobs/statistics/", get_statistics, name="jobs-statistics"),
]