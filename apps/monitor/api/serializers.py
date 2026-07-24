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


_SCENARIO_LABEL = dict(Claim.ScenarioType.choices)


def _fraction(value, lo, hi):
    """value를 [lo, hi] 스케일의 0~1 위치로. 밖이면 클램프. hi<=lo면 None."""
    if value is None or hi <= lo:
        return None
    return max(0.0, min(1.0, (float(value) - lo) / (hi - lo)))


def build_zone_display(claim, anchor, close):
    """zone 표시 메타 완결 (BE 단일 소스 — FE는 bands/ticks/rows/marker 렌더만, D-HOLD-DECISIONS 2).

    anchor = zone 중심(hold=매입가·그 외=진입가). new_entry는 기존 5구간/라벨/틱을 그대로 재현,
    hold는 4표시구간(이탈/보유/익절 접근/목표 도달) + 매입가 앵커 마커 + pnl로 완결한다.
    """
    from decimal import Decimal

    from apps.monitor.services.price_zone import (
        APPROACH_BUFFER,
        NEAR_TARGET_BUFFER,
        resolve_zone,
    )

    stop = float(claim.stop_price)
    target = float(claim.target_price)
    anchor_f = float(anchor)
    is_hold = claim.scenario_type == Claim.ScenarioType.HOLD

    zone = resolve_zone(close, anchor, claim.target_price, claim.stop_price)
    marker_fraction = _fraction(close, stop, target)

    common = {
        "zone": zone,
        "close": close,
        "mode": claim.scenario_type,
        "mode_label": _SCENARIO_LABEL.get(claim.scenario_type),
        "marker_fraction": marker_fraction,
    }

    if not is_hold:
        # 신규/추가 매수 — 기존 5구간 표시 재현(하위호환).
        approach_ceiling = float(claim.entry_price * (Decimal("1") + APPROACH_BUFFER))
        label_map = dict(Claim.PriceZone.choices)
        bands = [
            {"key": z, "tone": z, "active": z == zone}
            for z in ("exited", "entry", "approach", "waiting", "overheated")
        ]
        return {
            **common,
            "label": label_map.get(zone),
            "pnl_pct": None,
            "anchor_fraction": None,
            "boundaries": {
                "stop": stop,
                "entry": anchor_f,
                "approach_ceiling": approach_ceiling,
                "target": target,
            },
            "bands": bands,
            "ticks": [
                {"label": "손절", "value": stop},
                {"label": "진입", "value": anchor_f},
                {"label": "목표", "value": target},
            ],
            "rows": [
                {"label": "목표", "value": target},
                {"label": "접근 상한", "value": approach_ceiling},
                {"label": "진입", "value": anchor_f},
                {"label": "손절", "value": stop},
            ],
        }

    # 보유 관리 — 4표시구간 재구간화(저장 zone 무관 표시 전용).
    near_target = round(target * (1.0 - float(NEAR_TARGET_BUFFER)), 4)
    if zone == Claim.PriceZone.EXITED:
        active_key, label = "exited", "이탈"
    elif zone == Claim.PriceZone.OVERHEATED:
        active_key, label = "reached", "목표 도달"
    elif close is not None and close >= near_target:
        active_key, label = "near_target", "익절 접근"
    else:
        active_key, label = "holding", "보유"

    hold_bands = [
        {"key": "exited", "tone": "exited"},
        {"key": "holding", "tone": "waiting"},
        {"key": "near_target", "tone": "approach"},
        {"key": "reached", "tone": "overheated"},
    ]
    pnl_pct = ((close - anchor_f) / anchor_f * 100.0) if (close is not None and anchor_f) else None
    return {
        **common,
        "label": label,
        "pnl_pct": round(pnl_pct, 4) if pnl_pct is not None else None,
        "anchor_fraction": _fraction(anchor_f, stop, target),  # 매입가 마커
        "boundaries": {
            "stop": stop,
            "entry": anchor_f,  # 앵커=매입가(하위호환 키)
            "approach_ceiling": near_target,
            "target": target,
        },
        "bands": [{**b, "active": b["key"] == active_key} for b in hold_bands],
        "ticks": [
            {"label": "손절", "value": stop},
            {"label": "매입가", "value": anchor_f},
            {"label": "목표", "value": target},
        ],
        "rows": [
            {"label": "목표", "value": target},
            {"label": "익절 접근", "value": near_target},
            {"label": "매입가", "value": anchor_f},
            {"label": "손절", "value": stop},
        ],
    }


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
            # 시나리오 모드 + 매수 시나리오 가격 (write 허용) + 보유 확정 사실 + 적정가 밴드
            "scenario_type", "entry_price", "target_price", "stop_price",
            "purchase_price", "purchase_date",
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
        mode = attrs.get(
            "scenario_type", getattr(inst, "scenario_type", Claim.ScenarioType.NEW_ENTRY)
        )
        entry = attrs.get("entry_price", getattr(inst, "entry_price", None))
        target = attrs.get("target_price", getattr(inst, "target_price", None))
        stop = attrs.get("stop_price", getattr(inst, "stop_price", None))

        if mode == Claim.ScenarioType.HOLD:
            # 보유 관리 (D-HOLD-DECISIONS 부속): 매입가·매입일·목표·손절·기한 필수.
            purchase = attrs.get("purchase_price", getattr(inst, "purchase_price", None))
            pdate = attrs.get("purchase_date", getattr(inst, "purchase_date", None))
            deadline = attrs.get("deadline", getattr(inst, "deadline", None))
            missing = {}
            if purchase is None:
                missing["purchase_price"] = "보유 관리는 매입가가 필요합니다."
            if pdate is None:
                missing["purchase_date"] = "보유 관리는 매입일이 필요합니다."
            if target is None:
                missing["target_price"] = "보유 관리는 목표가가 필요합니다."
            if stop is None:
                missing["stop_price"] = "보유 관리는 손절가가 필요합니다."
            if deadline is None:
                missing["deadline"] = "보유 관리는 기한이 필요합니다."
            if missing:
                raise serializers.ValidationError(missing)
            # stop < target만 강제 — stop<purchase는 미강제(본전 승격 손절이 매입가 위일 수 있음).
            if not (stop < target):
                raise serializers.ValidationError(
                    {"stop_price": "손절가 < 목표가 순서여야 합니다."}
                )
        else:
            # 신규 매수/추가 매수: 셋 다 있을 때만 순서 검증 (부분 입력·무가격 통과 — 빌더가 4필수 강제)
            if entry is not None and target is not None and stop is not None:
                if not (stop < entry < target):
                    raise serializers.ValidationError(
                        {"entry_price": "손절가 < 진입가 < 목표가 순서여야 합니다."}
                    )

        # 기한 = 미래 (신규 제출 시). deadline 단독 수정은 검사 생략.
        anchor_new = entry if mode != Claim.ScenarioType.HOLD else attrs.get(
            "purchase_price", getattr(inst, "purchase_price", None)
        )
        deadline = attrs.get("deadline")
        if deadline is not None and anchor_new is not None and inst is None:
            from django.utils import timezone

            if deadline <= timezone.localdate():
                raise serializers.ValidationError({"deadline": "기한은 미래 날짜여야 합니다."})
        return attrs

    def get_zone_display(self, obj):
        # 표시 메타를 BE에서 완결(FE 렌더 전용 — bands/ticks/rows/marker/라벨 단일 소스, D-HOLD-DECISIONS 2).
        # 앵커(hold=매입가·그 외=진입가)와 목표·손절이 모두 있어야 구간 산출.
        from apps.monitor.services.price_zone import zone_anchor
        from apps.monitor.services.scenario import latest_close

        anchor = zone_anchor(obj)
        if anchor is None or obj.target_price is None or obj.stop_price is None:
            return None

        close = latest_close(obj.monitor.target_ref)
        return build_zone_display(obj, anchor, close)


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
