"""Monitor API views (MON-P2-S3).

user 스코프 격리: 모든 queryset은 request.user 소유로 제한(IDOR 방지).
평가 트리거 = MonitorViewSet.evaluate action (수동). beat 주기 등록은 별도 스텝.
"""
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

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
)
from apps.monitor.services.pipeline import evaluate_monitor


class MonitorViewSet(viewsets.ModelViewSet):
    serializer_class = MonitorSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Monitor.objects.filter(user=self.request.user)

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
