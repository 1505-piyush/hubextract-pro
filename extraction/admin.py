from django.contrib import admin

from .models import ExtractionJob


@admin.register(ExtractionJob)
class ExtractionJobAdmin(admin.ModelAdmin):
    list_display = ("id", "source", "status", "total_records", "extracted_records", "created_at")
    list_filter = ("status", "source", "created_at")
    search_fields = ("source", "status", "id")
    readonly_fields = ("id", "created_at", "started_at", "completed_at")
    ordering = ("-created_at",)
