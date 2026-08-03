from __future__ import annotations

from rest_framework import serializers

from .models import ExtractionJob
from .validators import validate_api_token, validate_source


class ExtractionJobSerializer(serializers.ModelSerializer):
    class Meta:
        model = ExtractionJob
        fields = "__all__"


class ScanStartSerializer(serializers.Serializer):
    source = serializers.CharField(required=True, trim_whitespace=True)
    api_token = serializers.CharField(required=True, trim_whitespace=True)

    def validate_source(self, value: str) -> str:
        return validate_source(value)

    def validate_api_token(self, value: str) -> str:
        return validate_api_token(value)


class ScanStatusSerializer(serializers.Serializer):
    job_id = serializers.UUIDField(required=True)


class CancelScanSerializer(serializers.Serializer):
    job_id = serializers.UUIDField(required=True)
