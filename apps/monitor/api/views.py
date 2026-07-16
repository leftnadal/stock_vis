"""Monitor API views (MON-P2-S3).

user 스코프 격리: 모든 queryset은 request.user 소유로 제한(IDOR 방지).
평가 트리거 = MonitorViewSet.evaluate action (수동). beat 주기 등록은 별도 스텝.
"""
from django.db.models import (
    Case,
    Count,
    Exists,
    F,
    IntegerField,
    Min,
    OuterRef,
    Q,
    Subquery,
    Value,
    When,
)
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.monitor.catalog import catalog_for

from apps.monitor.api.serializers import (
    AlertEventSerializer,
    ClaimSerializer,
    IndicatorReadingSerializer,
    MonitorIndicatorSerializer,
    MonitorSerializer,
)
from apps.monitor.models import (
    AlertEvent,
    Claim,
    IndicatorReading,
    Monitor,
    MonitorIndicator,
    MonitorSnapshot,
)
from apps.monitor.services import closure
from apps.monitor.services.pipeline import evaluate_monitor
from apps.monitor.services.sparkline import score_series

# 상태 심각도 랭크: 위험(0) → 약화(1) → 관찰(2) → 유지(3). 트리아지 정렬 1차 키.
_SEVERITY_WHENS = [
    When(current_state__in=["critical", "expired", "needs_review"], then=Value(0)),
    When(current_state="weakening", then=Value(1)),
    When(current_state__in=["warming_up", "active"], then=Value(2)),
    # strengthening·paused → 유지(3, default)
]


class IndicatorCatalogView(APIView):
    """scope별 지표 카탈로그 (빌더 3단계). GET /monitor/catalog/?scope=stock."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        scope = request.query_params.get("scope", "stock")
        return Response({"scope": scope, "indicators": catalog_for(scope)})


class ScenarioSuggestView(APIView):
    """L계열 가격 제안 (빌더 4단계, 읽기 전용). GET /monitor/scenario-suggest/?symbol=AAPL.

    DailyPrice에서 지지선(스윙 저점)·ATR×2 손절 폭 산출(서버측 — 3년 OHLC 클라 전송 금지).
    확정은 항상 사용자(3-B). 히스토리 부족 시 available=False.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        from apps.monitor.services.scenario_suggest import suggest_scenario

        symbol = (request.query_params.get("symbol") or "").strip()
        if not symbol:
            return Response(
                {"detail": "symbol 파라미터가 필요합니다."}, status=status.HTTP_400_BAD_REQUEST
            )
        return Response(suggest_scenario(symbol))


class MonitorViewSet(viewsets.ModelViewSet):
    serializer_class = MonitorSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        # 카드 렌더 데이터 + 트리아지 정렬을 서버에서 확정(페이지네이션 하 클라 정렬 금지).
        latest_snap = (
            MonitorSnapshot.objects.filter(monitor=OuterRef("pk"))
            .order_by("-asof_date")
            .values("overall_score")[:1]
        )
        qs = (
            Monitor.objects.filter(user=self.request.user)
            .annotate(
                severity_rank=Case(
                    *_SEVERITY_WHENS, default=Value(3), output_field=IntegerField()
                ),
                latest_score=Subquery(latest_snap),
                indicator_count=Count(
                    "indicators",
                    filter=Q(indicators__is_active=True),
                    distinct=True,
                ),
                next_deadline=Min(
                    "claims__deadline", filter=Q(claims__status="active")
                ),
                has_claim=Exists(Claim.objects.filter(monitor=OuterRef("pk"))),
            )
        )

        # filter: scope, has_claim (Exists로 distinct 회피)
        scope = self.request.query_params.get("scope")
        if scope:
            qs = qs.filter(scope=scope)
        has_claim = self.request.query_params.get("has_claim")
        if has_claim == "true":
            qs = qs.filter(Exists(Claim.objects.filter(monitor=OuterRef("pk"))))

        # 정렬: 심각도 → 마감 임박(nulls last) → 최근 갱신
        return qs.order_by(
            "severity_rank", F("next_deadline").asc(nulls_last=True), "-updated_at"
        )

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    @action(detail=True, methods=["post"])
    def evaluate(self, request, pk=None):
        """지표 스코어 → 집계 → 스냅샷 → 상태 판정 파이프라인 실행(수동 트리거)."""
        monitor = self.get_object()  # user 스코프 자동 적용
        result = evaluate_monitor(monitor)
        return Response(result, status=status.HTTP_200_OK)

    @action(detail=True, methods=["get"])
    def sparkline(self, request, pk=None):
        """상태밴드 스파크라인 데이터 — 최근 N거래일 score 시계열 + 밴드 + 전이 표식."""
        monitor = self.get_object()  # user 스코프 자동 적용
        try:
            window = int(request.query_params.get("window", 30))
        except (TypeError, ValueError):
            window = 30
        window = max(5, min(window, 120))
        return Response(score_series(monitor, window=window))


class AlertEventViewSet(viewsets.ReadOnlyModelViewSet):
    """전이 알림 — 인앱 패널·헤더 벨 (user 스코프, 읽기 + 읽음 처리 action)."""

    serializer_class = AlertEventSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        # 억제 알림은 개별 행에서 제외(배지·목록 숨김, 결정 1-C 쿨다운)
        qs = AlertEvent.objects.filter(
            monitor__user=self.request.user, is_suppressed=False
        ).select_related("monitor")
        if self.request.query_params.get("unread") == "true":
            qs = qs.filter(read=False)
        if self.request.query_params.get("deterioration") == "true":
            qs = qs.filter(is_deterioration=True)
        return qs

    @action(detail=False, methods=["get"])
    def summary(self, request):
        """헤더 벨 배지용 — 미확인 악화 알림 수(악화만 카운트, 결정 1-C)."""
        count = AlertEvent.objects.filter(
            monitor__user=request.user,
            is_suppressed=False,
            is_deterioration=True,
            read=False,
        ).count()
        return Response({"unread_deterioration_count": count})

    @action(detail=True, methods=["post"])
    def read(self, request, pk=None):
        """개별 알림 읽음 처리."""
        alert = self.get_object()
        if not alert.read:
            alert.read = True
            alert.save(update_fields=["read"])
        return Response(self.get_serializer(alert).data)

    @action(detail=False, methods=["post"])
    def read_all(self, request):
        """미확인 알림 일괄 읽음 처리."""
        n = self.get_queryset().filter(read=False).update(read=True)
        return Response({"marked_read": n})


class _OwnedByMonitorMixin:
    """monitor__user 소유 검증 공통 로직."""

    permission_classes = [IsAuthenticated]
    monitor_lookup = "monitor"  # override: 'indicator__monitor' 등

    def _assert_owner(self, obj_monitor):
        if obj_monitor.user_id != self.request.user.id:
            raise PermissionDenied("본인 소유 Monitor가 아닙니다.")


class MonitorIndicatorViewSet(_OwnedByMonitorMixin, viewsets.ModelViewSet):
    serializer_class = MonitorIndicatorSerializer

    def get_queryset(self):
        return MonitorIndicator.objects.filter(monitor__user=self.request.user)

    def perform_create(self, serializer):
        self._assert_owner(serializer.validated_data["monitor"])
        serializer.save()


class ClaimViewSet(_OwnedByMonitorMixin, viewsets.ModelViewSet):
    serializer_class = ClaimSerializer

    def get_queryset(self):
        return Claim.objects.filter(monitor__user=self.request.user)

    def perform_create(self, serializer):
        self._assert_owner(serializer.validated_data["monitor"])
        serializer.save()

    @action(detail=True, methods=["get"], url_path="close-preview")
    def close_preview(self, request, pk=None):
        """마감 모달 프리필 — 제안 판정·종합점수·지표 목록 (상태 변경 없음)."""
        claim = self.get_object()  # owner 스코프 자동 적용
        return Response(closure.close_preview(claim), status=status.HTTP_200_OK)

    @action(detail=True, methods=["post"])
    def close(self, request, pk=None):
        """가설 마감 (원자적) — 판정·회고·지표별 결과·동결 스냅샷."""
        claim = self.get_object()
        data = request.data
        try:
            closed = closure.close_claim(
                claim,
                final_verdict=data.get("final_verdict"),
                factor_tags=data.get("factor_tags", []),
                retro_memo=data.get("retro_memo", ""),
                indicator_results=data.get("indicator_results", []),
                user=request.user,
            )
        except closure.AlreadyClosedError as e:
            return Response({"detail": str(e)}, status=status.HTTP_409_CONFLICT)
        except closure.ClosureValidationError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(self.get_serializer(closed).data, status=status.HTTP_200_OK)


class IndicatorReadingViewSet(_OwnedByMonitorMixin, viewsets.ModelViewSet):
    serializer_class = IndicatorReadingSerializer

    def get_queryset(self):
        return IndicatorReading.objects.filter(
            indicator__monitor__user=self.request.user
        )

    def perform_create(self, serializer):
        self._assert_owner(serializer.validated_data["indicator"].monitor)
        serializer.save()
