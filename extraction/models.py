from django.db import models
import uuid


class ExtractionJob(models.Model):
    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("in_progress", "In Progress"),
        ("completed", "Completed"),
        ("failed", "Failed"),
        ("cancelled", "Cancelled"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    source = models.CharField(max_length=100)
    api_token = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")

    total_records = models.IntegerField(default=0)
    extracted_records = models.IntegerField(default=0)
    result_data = models.JSONField(default=list, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.id} - {self.status}"
