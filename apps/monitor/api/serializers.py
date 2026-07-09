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
            "weight", "source_key", "epsilon", "window", "decay", "is_active",
            "is_paused", "override_score", "created_at", "updated_at",
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
    # 리스트 카드용 파생값 (ViewSet get_queryset annotation, create 응답서는 None)
    latest_score = serializers.SerializerMethodField()
    indicator_count = serializers.SerializerMethodField()
    next_deadline = serializers.SerializerMethodField()
    has_claim = serializers.SerializerMethodField()
    # 파생 표시값(각도·색·라벨·달위상) — BE 엔진이 단일 소스, FE는 렌더 전용
    display = serializers.SerializerMethodField()

    class Meta:
        model = Monitor
        fields = [
            "id", "scope", "target_ref", "name", "status", "current_state",
            "target_date_end", "resolved_label", "latest_score", "display",
            "indicator_count", "next_deadline", "has_claim", "created_at", "updated_at",
        ]
        # current_state는 파이프라인(엔진) 소유 — 사용자 입력 불가
        read_only_fields = ["id", "current_state", "created_at", "updated_at"]

    def get_resolved_label(self, obj):
        try:
            return resolve(obj.scope, obj.target_ref).label
        except ScopeResolutionError:
            return None

    def get_latest_score(self, obj):
        return getattr(obj, "latest_score", None)

    def get_indicator_count(self, obj):
        return getattr(obj, "indicator_count", None)

    def get_next_deadline(self, obj):
        d = getattr(obj, "next_deadline", None)
        return d.isoformat() if d else None

    def get_has_claim(self, obj):
        return bool(getattr(obj, "has_claim", False))

    def get_display(self, obj):
        # latest_score(스냅샷 overall_score)에서 파생값을 BE 엔진으로 산출(단일 소스).
        score = getattr(obj, "latest_score", None)
        if score is None:
            return None
        from apps.monitor.services.arrow_calculator import (
            degree_to_color,
            degree_to_label,
            score_to_degree,
        )
        from apps.monitor.services.state_machine import score_to_phase

        degree = round(score_to_degree(score), 1)
        phase = score_to_phase(score)
        return {
            "degree": degree,
            "color": degree_to_color(degree),
            "label": degree_to_label(degree),
            "phase": phase["phase"],
            "phase_label": phase["label"],
            "phase_icon": phase["icon"],
        }

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
