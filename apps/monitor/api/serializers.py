"""Monitor API serializers (MON-P2-S3)."""
from rest_framework import serializers

from apps.monitor.models import (
    AlertEvent,
    Claim,
    ClosureSnapshot,
    IndicatorReading,
    Monitor,
    MonitorIndicator,
)
from apps.monitor.services.scope_resolver import ScopeResolutionError, resolve


class ClosureSnapshotSerializer(serializers.ModelSerializer):
    """마감 동결 스냅샷 (읽기 전용). 동결값 표시용 — payload 통째 노출(개인용)."""

    class Meta:
        model = ClosureSnapshot
        fields = ["overall_score", "frozen_at", "payload"]
        read_only_fields = fields


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
    # 마감 동결 스냅샷 (resolved면 값, PENDING이면 null). 동결값 우선 표시용.
    closure_snapshot = serializers.SerializerMethodField()
    # 가격 구간축 표시 메타 (BE 완결 단일 소스 — FE 재계산 금지). 가격 없으면 null.
    zone_display = serializers.SerializerMethodField()

    class Meta:
        model = Claim
        fields = [
            "id", "monitor", "assertion", "deadline", "status", "outcome",
            "proposed_verdict", "resolved_by", "factor_tags", "retro_memo",
            # 매수 시나리오 가격 (write 허용 — 빌더 P2 대비) + 적정가 밴드
            "entry_price", "target_price", "stop_price",
            "fair_value_low", "fair_value_high",
            # 구간축 (read-only — 파이프라인 소유) + 표시 메타
            "last_price_zone", "entry_reached_at", "zone_display",
            "closure_snapshot", "created_at", "resolved_at",
        ]
        # 마감 회고 + 파이프라인 소유 필드는 직접 CRUD로 쓰지 못하게 read-only
        read_only_fields = [
            "id", "created_at", "proposed_verdict", "resolved_by",
            "factor_tags", "retro_memo", "closure_snapshot", "resolved_at",
            "last_price_zone", "entry_reached_at", "zone_display",
        ]

    def get_closure_snapshot(self, obj):
        # OneToOne 역참조 — 마감 전이면 미존재
        try:
            return ClosureSnapshotSerializer(obj.closure_snapshot).data
        except ClosureSnapshot.DoesNotExist:
            return None

    def validate(self, attrs):
        # 가격 시나리오 검증 (TIMING-P2 §3, additive — 가격 제출 시에만). 기존 무가격 Claim 무영향.
        inst = self.instance
        entry = attrs.get("entry_price", getattr(inst, "entry_price", None))
        target = attrs.get("target_price", getattr(inst, "target_price", None))
        stop = attrs.get("stop_price", getattr(inst, "stop_price", None))
        # 셋 다 있을 때만 순서 검증 (부분 입력·무가격은 통과 — 빌더가 4필수 강제)
        if entry is not None and target is not None and stop is not None:
            if not (stop < entry < target):
                raise serializers.ValidationError(
                    {"entry_price": "손절가 < 진입가 < 목표가 순서여야 합니다."}
                )
        # 기한 = 미래 (가격 시나리오 신규 제출 시). deadline 단독 수정은 검사 생략.
        deadline = attrs.get("deadline")
        if deadline is not None and entry is not None and inst is None:
            from django.utils import timezone

            if deadline <= timezone.localdate():
                raise serializers.ValidationError({"deadline": "기한은 미래 날짜여야 합니다."})
        return attrs

    def get_zone_display(self, obj):
        # 가격 3필드 모두 있어야 구간 산출. 라벨·경계값을 BE에서 완결(FE 렌더 전용).
        if obj.entry_price is None or obj.target_price is None or obj.stop_price is None:
            return None
        from decimal import Decimal

        from apps.monitor.services.price_zone import APPROACH_BUFFER, resolve_zone
        from apps.monitor.services.scenario import latest_close

        close = latest_close(obj.monitor.target_ref)
        zone = resolve_zone(close, obj.entry_price, obj.target_price, obj.stop_price)
        label_map = dict(Claim.PriceZone.choices)
        return {
            "zone": zone,
            "label": label_map.get(zone),
            "close": close,
            "boundaries": {
                "stop": float(obj.stop_price),
                "entry": float(obj.entry_price),
                "approach_ceiling": float(obj.entry_price * (Decimal("1") + APPROACH_BUFFER)),
                "target": float(obj.target_price),
            },
        }


class AlertEventSerializer(serializers.ModelSerializer):
    """전이 알림 — 인앱 패널 행(상태색/라벨 파생 포함)."""

    monitor_name = serializers.CharField(source="monitor.name", read_only=True)
    target_ref = serializers.CharField(source="monitor.target_ref", read_only=True)
    from_label = serializers.SerializerMethodField()
    to_label = serializers.SerializerMethodField()

    class Meta:
        model = AlertEvent
        fields = [
            "id", "monitor", "monitor_name", "target_ref",
            "from_state", "to_state", "from_label", "to_label",
            "asof", "score", "is_deterioration", "is_suppressed", "read", "created_at",
        ]
        read_only_fields = fields

    _LABELS = dict(Monitor.State.choices)

    def get_from_label(self, obj):
        return self._LABELS.get(obj.from_state, obj.from_state)

    def get_to_label(self, obj):
        return self._LABELS.get(obj.to_state, obj.to_state)


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
            "indicator_count", "next_deadline", "has_claim",
            "close_suggested", "danger_streak", "created_at", "updated_at",
        ]
        # current_state·마감제안은 파이프라인(엔진) 소유 — 사용자 입력 불가
        read_only_fields = [
            "id", "current_state", "close_suggested", "danger_streak",
            "created_at", "updated_at",
        ]

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
