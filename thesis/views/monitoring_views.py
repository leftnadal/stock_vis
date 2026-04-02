"""Monitoring Views: 관제실 대시보드 + 알림 API"""

import logging
from datetime import timedelta

from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from thesis.models import Thesis, ThesisAlert, ThesisIndicator
from thesis.serializers import ThesisAlertSerializer
from thesis.services.arrow_calculator import (
    calculate_indicator_arrow,
    score_to_degree, degree_to_color,
)
from thesis.services.prompt_builder import get_indicator_description
from thesis.services.thesis_state_machine import score_to_phase

logger = logging.getLogger(__name__)


def _prefetch_quarterly_data(indicators) -> dict:
    """
    metrics 지표들의 분기 데이터를 batch로 조회.
    Returns: {(symbol, metric_code): quarterly_data_dict, ...}
    """
    from thesis.services.quarterly_metric_fetcher import fetch_quarterly_metric

    cache = {}
    for indicator in indicators:
        params = indicator.data_params or {}
        metric_code = params.get('metric_code')
        symbol = params.get('symbol') or getattr(indicator.thesis, 'target', '').upper()
        if not metric_code or not symbol:
            continue

        key = (symbol.upper(), metric_code)
        if key in cache:
            continue  # 동일 symbol+metric은 1번만 조회

        result = fetch_quarterly_metric(symbol.upper(), metric_code)
        cache[key] = result

    return cache


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
        active_indicators = list(thesis.indicators.filter(is_active=True))

        # 분기 지표 batch 조회 (metrics 소스만 대상)
        metrics_indicators = [i for i in active_indicators if i.data_source == 'metrics']
        quarterly_cache = _prefetch_quarterly_data(metrics_indicators) if metrics_indicators else {}

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

            # Phase 3: raw_value 추출 (latest validated reading)
            latest_reading = indicator.readings.filter(
                validation_status__in=['ok', 'extreme_jump_allowed']
            ).order_by('-asof').first()

            prev_reading = indicator.readings.filter(
                validation_status__in=['ok', 'extreme_jump_allowed']
            ).order_by('-asof')[1:2].first() if latest_reading else None

            raw_value = latest_reading.raw_value if latest_reading else None
            previous_raw_value = prev_reading.raw_value if prev_reading else None

            change_pct = None
            if raw_value is not None and previous_raw_value and previous_raw_value != 0:
                change_pct = round(
                    ((raw_value - previous_raw_value) / abs(previous_raw_value)) * 100, 2
                )

            raw_value_unit = indicator.display_unit or _infer_unit(indicator)

            # 분기 지표 확장 필드 초기화 (metrics 소스인 경우 override)
            fiscal_label = None
            quarterly_history = None
            is_quarterly = False
            comparison_type = None

            if indicator.data_source == 'metrics':
                from thesis.services.quarterly_metric_fetcher import RATIO_METRICS

                params = indicator.data_params or {}
                metric_code = params.get('metric_code')
                symbol = (params.get('symbol') or getattr(indicator.thesis, 'target', '').upper()).upper()
                qdata = quarterly_cache.get((symbol, metric_code))

                if qdata:
                    is_quarterly = True
                    raw_value = qdata['value']
                    change_pct = qdata.get('change_pct')
                    quarterly_history = qdata.get('quarterly_history')
                    comparison_type = qdata.get('comparison_type')

                    # 비율값(0~1)을 % 단위로 변환 (display_unit='%'인 경우)
                    if raw_value_unit == '%' and metric_code in RATIO_METRICS:
                        if raw_value is not None:
                            raw_value = round(raw_value * 100, 2)
                        if quarterly_history:
                            quarterly_history = [
                                {**h, 'value': round(h['value'] * 100, 2)}
                                for h in quarterly_history
                            ]

                    if qdata.get('fiscal_quarter'):
                        fiscal_label = f"{qdata['fiscal_year']} Q{qdata['fiscal_quarter']}"
                    else:
                        fiscal_label = f"{qdata['fiscal_year']} FY"

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
                'raw_value': raw_value,
                'raw_value_unit': raw_value_unit,
                'previous_raw_value': previous_raw_value,
                'change_pct': change_pct,
                'raw_value_asof': latest_reading.asof.isoformat() if latest_reading else None,
                # 분기 지표 확장 필드
                'fiscal_label': fiscal_label,
                'quarterly_history': quarterly_history,
                'is_quarterly': is_quarterly,
                'comparison_type': comparison_type,
                # 지표 설명 + 가설 관계성
                'description': get_indicator_description(indicator.name),
                'recommendation_reason': indicator.recommendation_reason,
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
                'ai_summary': latest_snapshot.ai_summary if latest_snapshot else '',
                'notable_changes': (latest_snapshot.notable_changes or [])[:5] if latest_snapshot else [],
                'snapshot_date': latest_snapshot.asof_date.isoformat() if latest_snapshot else None,
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


class IndicatorReadingsView(APIView):
    """GET /{thesis_id}/indicators/{indicator_id}/readings/?days=14"""
    permission_classes = [IsAuthenticated]

    def get(self, request, thesis_id, indicator_id):
        thesis = get_object_or_404(Thesis, id=thesis_id, user=request.user)
        indicator = get_object_or_404(
            thesis.indicators, id=indicator_id
        )
        days = min(int(request.query_params.get('days', 14)), 1825)  # 최대 5Y
        cutoff = timezone.now() - timedelta(days=days)

        readings = list(
            indicator.readings.filter(
                validation_status__in=['ok', 'extreme_jump_allowed'],
                asof__gte=cutoff,
            ).order_by('asof').values('asof', 'value', 'raw_value')
        )

        # DB readings가 부족하면 FMP 히스토리 API fallback
        if len(readings) < min(days, 30) and indicator.data_source == 'fmp':
            readings = _fetch_fmp_history(indicator, days)

        return Response({
            'indicator_id': str(indicator.id),
            'indicator_name': indicator.name,
            'support_direction': indicator.support_direction,
            'unit': indicator.display_unit or _infer_unit(indicator),
            'readings': readings,
            'count': len(readings),
        })


def _fetch_fmp_history(indicator, days: int) -> list:
    """FMP get_historical_price로 히스토리 조회. DB readings 부족 시 fallback."""
    from api_request.providers.fmp.client import FMPClient, FMPClientError, FMPPremiumError
    from django.conf import settings
    from datetime import datetime

    params = indicator.data_params or {}
    symbol = params.get('symbol')
    if not symbol:
        return []

    try:
        api_key = getattr(settings, 'FMP_API_KEY', None)
        if not api_key:
            return []

        client = FMPClient(api_key=api_key)
        from_date = (timezone.now() - timedelta(days=days)).strftime('%Y-%m-%d')
        to_date = timezone.now().strftime('%Y-%m-%d')

        data = client.get_historical_price(symbol, from_date=from_date, to_date=to_date)
        if not data:
            return []

        # FMP 응답을 readings 형식으로 변환
        metric = params.get('metric', 'price')
        field_map = {
            'price': 'close', 'change_percent': 'changePercent',
            'volume': 'volume',
        }
        field = field_map.get(metric, 'close')

        readings = []
        for row in data:
            date_str = row.get('date')
            val = row.get(field)
            if date_str and val is not None:
                readings.append({
                    'asof': f"{date_str}T18:00:00Z",
                    'value': float(val),
                    'raw_value': float(val),
                })

        # 오래된 순 정렬
        readings.sort(key=lambda r: r['asof'])
        return readings

    except (FMPPremiumError, FMPClientError):
        return []
    except Exception as e:
        logger.warning(f"FMP history fallback 실패 ({symbol}): {e}")
        return []


def _infer_unit(indicator):
    """data_params + indicator_type으로 단위 추론. display_unit이 비어있을 때만 사용."""
    params = indicator.data_params or {}
    series_id = params.get('series_id', '')

    if series_id in ('FEDFUNDS', 'DGS10', 'DGS2'):
        return '%'
    if indicator.indicator_type == 'sentiment':
        return ''

    symbol = params.get('symbol', '').upper()
    if 'KRW' in symbol or 'USDKRW' in symbol:
        return '원'
    if symbol.startswith('^'):
        return 'pt'

    if indicator.data_source == 'fmp':
        return '$'
    return ''
