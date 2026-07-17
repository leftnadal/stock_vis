"""Slice 20a — 권유 REST 표면 (DRF 얇은 어댑터, Pydantic 계약 = 진실 소스).

4 엔드포인트(전부 user 스코프, IsAuthenticated):
  GET  advisory/latest/   최신 권유(최근 AdvisoryRun 산출 전문 + trigger + 실행 시각)
  GET  advisory/summary/  자산 요약(최근 PortfolioSnapshot) + 진행/배치 갭 + 모드
  GET  advisory/knobs/    손잡이 5종(UserGoal, 읽기 전용 — 쓰기는 20b)
  POST advisory/run/      수동 진단(trigger=manual 기록 후 결과 반환)

serializer는 스키마 앵커(빈 필드) + passthrough. 실 스키마는 spectacular 확장이
Pydantic 계약(advisory_contract)으로 매핑(advisory_schema.py, apps.ready() 등록).
"""

from __future__ import annotations

from decimal import Decimal, InvalidOperation

from django.core.exceptions import ValidationError as DjangoValidationError
from django.urls import path
from drf_spectacular.utils import extend_schema
from rest_framework import serializers
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response

from apps.portfolio.models_my import AdvisoryRun, PortfolioSnapshot, UserGoal
from apps.portfolio.services.advisory_engine import (
    _jsonable,
    compute_allocation_gap,
    compute_dial,
    compute_progress_gap,
    determine_mode,
    recommend,
    run_advisory,
)


# ── 스키마 앵커 serializer (빈 필드 — 실 스키마는 advisory_schema 확장) ──


class LatestAdvisorySerializer(serializers.Serializer):
    def to_representation(self, instance):
        return instance


class AssetSummarySerializer(serializers.Serializer):
    def to_representation(self, instance):
        return instance


class KnobsReadSerializer(serializers.Serializer):
    def to_representation(self, instance):
        return instance


class KnobsUpdateSerializer(serializers.Serializer):
    """손잡이 5종 + 목표 수익률 부분 수정 요청(SLICE20B). 전부 optional(partial).

    검증은 모델 계층(UserGoal.full_clean → validators + KNOB_RANGES)이 진실 소스 —
    여기 선언은 스키마 앵커일 뿐, 범위 강제는 뷰에서 full_clean 경유(프론트 검증 대체 금지).
    """

    target_return_pct = serializers.DecimalField(max_digits=6, decimal_places=2, required=False)
    aggressiveness_offset = serializers.IntegerField(required=False)
    growth_boost = serializers.IntegerField(required=False)
    diversification_weight = serializers.DecimalField(max_digits=3, decimal_places=2, required=False)
    concentration_limit = serializers.IntegerField(required=False)
    exploration_ratio = serializers.IntegerField(required=False)


# ── 헬퍼 ──

# 손잡이 PATCH 대상 필드 (모델 검증기가 범위 강제 — 여기선 형변환만)
_KNOB_INT_FIELDS = {
    "aggressiveness_offset",
    "growth_boost",
    "concentration_limit",
    "exploration_ratio",
}
_KNOB_DEC_FIELDS = {"diversification_weight", "target_return_pct"}
_PATCHABLE_FIELDS = _KNOB_INT_FIELDS | _KNOB_DEC_FIELDS


def _knobs_payload(goal: UserGoal) -> dict:
    """손잡이 5종 + 목표 수익률 봉투(GET/PATCH 공용). target_return_pct는 20b 가산."""
    return _jsonable(
        {
            "available": True,
            "target_return_pct": goal.target_return_pct,
            "aggressiveness_offset": goal.aggressiveness_offset,
            "growth_boost": goal.growth_boost,
            "diversification_weight": goal.diversification_weight,
            "concentration_limit": goal.concentration_limit,
            "exploration_ratio": goal.exploration_ratio,
        }
    )


def _latest_advisory_payload(user) -> dict:
    run = AdvisoryRun.objects.for_user(user).order_by("-run_at").first()
    if run is None:
        return {"available": False, "trigger": None, "run_at": None, "output": None}
    return {
        "available": True,
        "trigger": run.trigger,
        "run_at": run.run_at.isoformat(),
        "output": run.output,  # 이미 _jsonable 저장(계약 v3)
    }


# ── 뷰 ──


@extend_schema(responses={200: LatestAdvisorySerializer}, tags=["portfolio-advisory"])
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def advisory_latest(request: Request) -> Response:
    """최신 권유(최근 AdvisoryRun). 없으면 available=False."""
    return Response(_latest_advisory_payload(request.user))


@extend_schema(responses={200: AssetSummarySerializer}, tags=["portfolio-advisory"])
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def advisory_summary(request: Request) -> Response:
    """자산 요약(최근 스냅샷) + 진행/배치 갭 + 모드. 스냅샷 없으면 available=False."""
    user = request.user
    snap = PortfolioSnapshot.objects.for_user(user).order_by("-date").first()
    if snap is None:
        return Response({"available": False})
    goal = UserGoal.objects.for_user(user).first()
    progress = compute_progress_gap(user, goal)
    allocation = compute_allocation_gap(user)
    dial = compute_dial(user, allocation, goal)
    mode = determine_mode(progress, dial)
    return Response(
        _jsonable(
            {
                "available": True,
                "date": snap.date,
                "total_krw": snap.total_krw,
                "by_currency": snap.by_currency,
                "price_as_of": snap.price_as_of,
                "progress_gap": progress,
                "allocation_gap": allocation,
                "mode": mode,
            }
        )
    )


@extend_schema(methods=["GET"], responses={200: KnobsReadSerializer}, tags=["portfolio-advisory"])
@extend_schema(
    methods=["PATCH"],
    request=KnobsUpdateSerializer,
    responses={200: KnobsReadSerializer},
    tags=["portfolio-advisory"],
)
@api_view(["GET", "PATCH"])
@permission_classes([IsAuthenticated])
def advisory_knobs(request: Request) -> Response:
    """손잡이 5종 + 목표 수익률.

    GET   현재값(읽기).
    PATCH 부분 수정(SLICE20B) — 목표 수익률 + 손잡이 5종. **서버측 검증기 강제**:
          UserGoal.full_clean()이 필드 validators + KNOB_RANGES(clean)를 실행,
          범위 밖은 400(프론트 검증만으로 대체 금지). 저장은 사용자 명시 요청만 —
          엔진/시스템 자동 조정 경로 아님. **저장 ≠ 진단 실행**(D2, [지금 진단] 별도).
    """
    goal = UserGoal.objects.for_user(request.user).first()

    if request.method == "PATCH":
        if goal is None:
            return Response(
                {"available": False, "detail": "먼저 투자 목표를 설정하세요(admin)."},
                status=400,
            )
        provided = {k: v for k, v in request.data.items() if k in _PATCHABLE_FIELDS}
        if not provided:
            return Response({"detail": "수정할 손잡이/목표 필드가 없습니다."}, status=400)

        coerce_errors: dict[str, str] = {}
        for field, raw in provided.items():
            try:
                if field in _KNOB_INT_FIELDS:
                    setattr(goal, field, int(raw))
                else:
                    setattr(goal, field, Decimal(str(raw)))
            except (ValueError, TypeError, InvalidOperation):
                coerce_errors[field] = f"{field}: 숫자 형식이 아닙니다 (입력: {raw})."
        if coerce_errors:
            return Response({"errors": coerce_errors}, status=400)

        try:
            goal.full_clean()  # 필드 validators + KNOB_RANGES(clean) 강제
        except DjangoValidationError as exc:
            return Response({"errors": exc.message_dict}, status=400)
        goal.save()
        return Response(_knobs_payload(goal))

    # GET
    if goal is None:
        return Response({"available": False})
    return Response(_knobs_payload(goal))


@extend_schema(request=None, responses={200: LatestAdvisorySerializer}, tags=["portfolio-advisory"])
@api_view(["POST"])
@permission_classes([IsAuthenticated])
def advisory_run(request: Request) -> Response:
    """수동 진단 실행(trigger=manual 기록) 후 최신 권유 봉투 반환."""
    run_advisory(request.user, trigger="manual")
    return Response(_latest_advisory_payload(request.user))


urlpatterns = [
    path("advisory/latest/", advisory_latest, name="advisory_latest"),
    path("advisory/summary/", advisory_summary, name="advisory_summary"),
    path("advisory/knobs/", advisory_knobs, name="advisory_knobs"),
    path("advisory/run/", advisory_run, name="advisory_run"),
]
