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
    ClaimSerializer,
    IndicatorReadingSerializer,
    MonitorIndicatorSerializer,
    MonitorSerializer,
)
from apps.monitor.models import (
    Claim,
    IndicatorReading,
    Monitor,
    MonitorIndicator,
    MonitorSnapshot,
)
from apps.monitor.services.pipeline import evaluate_monitor

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


class IndicatorReadingViewSet(_OwnedByMonitorMixin, viewsets.ModelViewSet):
    serializer_class = IndicatorReadingSerializer

    def get_queryset(self):
        return IndicatorReading.objects.filter(
            indicator__monitor__user=self.request.user
        )

    def perform_create(self, serializer):
        self._assert_owner(serializer.validated_data["indicator"].monitor)
        serializer.save()
