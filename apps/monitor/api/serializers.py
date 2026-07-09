"""Monitor API serializers (MON-P2-S3)."""
from rest_framework import serializers

from apps.monitor.models import (
    Claim,
    IndicatorReading,
    Monitor,
    MonitorIndicator,
)
from apps.monitor.services.scope_resolver import ScopeResolutionError, resolve


class MonitorIndicatorSerializer(serializers.ModelSerializer):
    class Meta:
        model = MonitorIndicator
        fields = [
            "id", "monitor", "name", "indicator_type", "support_direction",
            "weight", "epsilon", "window", "decay", "is_active", "is_paused",
            "override_score", "created_at", "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class IndicatorReadingSerializer(serializers.ModelSerializer):
    class Meta:
        model = IndicatorReading
        fields = ["id", "indicator", "value", "asof", "validation_status", "created_at"]
        read_only_fields = ["id", "created_at"]


class ClaimSerializer(serializers.ModelSerializer):
    class Meta:
        model = Claim
        fields = [
            "id", "monitor", "assertion", "deadline", "status", "outcome",
            "created_at", "resolved_at",
        ]
        read_only_fields = ["id", "created_at"]


class MonitorSerializer(serializers.ModelSerializer):
    # ScopeResolver가 정규화한 표시명 (읽기 전용)
    resolved_label = serializers.SerializerMethodField()

    class Meta:
        model = Monitor
        fields = [
            "id", "scope", "target_ref", "name", "status", "current_state",
            "target_date_end", "resolved_label", "created_at", "updated_at",
        ]
        # current_state는 파이프라인(엔진) 소유 — 사용자 입력 불가
        read_only_fields = ["id", "current_state", "created_at", "updated_at"]

    def get_resolved_label(self, obj):
        try:
            return resolve(obj.scope, obj.target_ref).label
        except ScopeResolutionError:
            return None

    def validate(self, attrs):
        # 생성/수정 시 (scope, target_ref)를 검증·정규화
        scope = attrs.get("scope", getattr(self.instance, "scope", None))
        target_ref = attrs.get("target_ref", getattr(self.instance, "target_ref", None))
        if scope is not None and target_ref is not None:
            try:
                resolved = resolve(scope, target_ref)
                attrs["target_ref"] = resolved.target_ref  # 정규화(대문자 등)
            except ScopeResolutionError as e:
                raise serializers.ValidationError({"target_ref": str(e)})
        return attrs
