"""공용 Serializer — OpenAPI 스키마용.

상세: docs/features/api_envelope/policy.md §5
"""
from rest_framework import serializers


class ErrorSerializer(serializers.Serializer):
    """표준 에러 응답 envelope (drf-spectacular용)."""

    detail = serializers.CharField()
    code = serializers.CharField(required=False)
    errors = serializers.DictField(
        required=False,
        child=serializers.ListField(child=serializers.CharField()),
    )
    status_code = serializers.IntegerField()
