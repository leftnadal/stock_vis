"""Monitoring Views: 관제실 대시보드 + 알림 API"""

import logging

from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from thesis.models import Thesis, ThesisAlert
from thesis.serializers import ThesisAlertSerializer
from thesis.services.arrow_calculator import (
    calculate_indicator_arrow,
    score_to_degree, degree_to_color,
)
from thesis.services.thesis_state_machine import score_to_phase

logger = logging.getLogger(__name__)


class DashboardView(APIView):
    """
    GET /{thesis_id}/dashboard/
    관제실 대시보드 데이터 (설계 문서 6.2).
    Phase 1: 실시간 계산 (캐싱 없음).
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, thesis_id):
        thesis = get_object_or_404(Thesis, id=thesis_id, user=request.user)

        days_active = (timezone.now() - thesis.created_at).days

        # 각 지표의 현재 화살표 계산
        indicators_data = []
        heatmap_cells = []
        active_indicators = thesis.indicators.filter(is_active=True)

        for indicator in active_indicators:
            try:
                arrow = calculate_indicator_arrow(indicator)
            except Exception as e:
                logger.warning(f"Arrow calculation failed for {indicator.name}: {e}")
                arrow = {
                    'score': 0.0, 'degree': 90.0, 'color': '#9CA3AF',
                    'label': '계산 불가', 'is_extreme_vol': False,
                }

            # 이전 degree (current_degree에 저장된 값)
            previous_degree = indicator.current_degree

            # 트렌드 판정
            trend = 'stable'
            if previous_degree is not None:
                diff = arrow['degree'] - previous_degree
                if diff < -10:
                    trend = 'strengthening'
                elif diff > 10:
                    trend = 'weakening'

            premise_name = ''
            if indicator.premise:
                premise_name = indicator.premise.content[:50]

            indicators_data.append({
                'id': str(indicator.id),
                'name': indicator.name,
                'arrow_degree': arrow['degree'],
                'score': arrow['score'],
                'color': arrow['color'],
                'label': arrow['label'],
                'previous_degree': previous_degree,
                'trend': trend,
                'premise_name': premise_name,
                'is_extreme_vol': arrow.get('is_extreme_vol', False),
            })

            heatmap_cells.append({
                'name': indicator.name[:10],
                'color': arrow['color'],
                'degree': arrow['degree'],
            })

        # 전체 흐름 (overall)
        overall_score = thesis.current_score or 0.0
        phase = score_to_phase(overall_score)

        # 최근 변화 (latest notable changes)
        latest_snapshot = thesis.snapshots.first()
        recent_change = ''
        if latest_snapshot and latest_snapshot.notable_changes:
            changes = latest_snapshot.notable_changes
            if changes:
                first = changes[0]
                recent_change = f'{first.get("indicator_name", "")} 점수 변화 감지'

        # 히트맵 그리드 크기 계산
        count = len(heatmap_cells)
        if count <= 3:
            rows, cols = 1, count or 1
        elif count <= 6:
            rows, cols = 2, 3
        else:
            cols = 3
            rows = (count + cols - 1) // cols

        return Response({
            'thesis': {
                'id': str(thesis.id),
                'title': thesis.title,
                'direction': thesis.direction,
                'status': thesis.status,
                'days_active': days_active,
                'overall_score': overall_score,
                'overall_label': phase['label'],
                'overall_phase': phase['phase'],
                'recent_change': recent_change,
            },
            'indicators': indicators_data,
            'heatmap': {
                'rows': rows,
                'cols': cols,
                'cells': heatmap_cells,
            },
        })


class AlertListView(APIView):
    """
    GET /alerts/ → 내 알림 목록 (미읽음 우선, 최대 50개)
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        base_qs = ThesisAlert.objects.filter(thesis__user=request.user)
        unread_count = base_qs.filter(is_read=False).count()
        alerts = base_qs.order_by('is_read', '-created_at')[:50]

        serializer = ThesisAlertSerializer(alerts, many=True)
        return Response({
            'alerts': serializer.data,
            'unread_count': unread_count,
        })


class AlertReadView(APIView):
    """
    PATCH /alerts/{aid}/read/ → 읽음 처리
    """
    permission_classes = [IsAuthenticated]

    def patch(self, request, aid):
        alert = get_object_or_404(ThesisAlert, id=aid, thesis__user=request.user)
        alert.is_read = True
        alert.save(update_fields=['is_read'])
        return Response({'status': 'read'})
