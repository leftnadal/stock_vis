"""
EOD Dashboard API Views (Step 8)

admin/debug용 REST API 엔드포인트.
실제 프론트엔드는 JSON Baker가 생성한 정적 파일을 직접 서빙합니다.
"""

import logging
from datetime import date

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from stocks.models import EODDashboardSnapshot, EODSignal, PipelineLog

logger = logging.getLogger(__name__)


class EODDashboardView(APIView):
    """
    GET /api/v1/stocks/eod/dashboard/?date=YYYY-MM-DD

    DB에 저장된 EODDashboardSnapshot을 반환합니다.
    admin/debug 전용 fallback 엔드포인트.
    """

    def get(self, request):
        target_date_str = request.query_params.get('date')
        if target_date_str:
            try:
                target_date = date.fromisoformat(target_date_str)
            except ValueError:
                return Response(
                    {'error': f'Invalid date format: {target_date_str}. Use YYYY-MM-DD.'},
                    status=status.HTTP_400_BAD_REQUEST,
                )
        else:
            target_date = date.today()

        snapshot = EODDashboardSnapshot.objects.filter(date=target_date).first()
        if not snapshot:
            return Response(
                {'error': f'No snapshot for date: {target_date}'},
                status=status.HTTP_404_NOT_FOUND,
            )

        return Response(snapshot.json_data)


class EODSignalDetailView(APIView):
    """
    GET /api/v1/stocks/eod/signal/<signal_id>/?date=YYYY-MM-DD

    특정 시그널 ID에 해당하는 종목 목록을 composite_score 기준 내림차순으로 반환합니다.
    최대 50개.
    """

    def get(self, request, signal_id: str):
        target_date_str = request.query_params.get('date')
        if target_date_str:
            try:
                target_date = date.fromisoformat(target_date_str)
            except ValueError:
                return Response(
                    {'error': f'Invalid date format: {target_date_str}. Use YYYY-MM-DD.'},
                    status=status.HTTP_400_BAD_REQUEST,
                )
        else:
            target_date = date.today()

        signals = (
            EODSignal.objects.filter(
                date=target_date,
                signals__contains=[{'id': signal_id}],
            )
            .select_related('stock')
            .order_by('-composite_score')[:50]
        )

        data = [
            {
                'symbol': s.stock_id,
                'company_name': s.stock.stock_name or '',
                'signals': s.signals,
                'tag_details': s.tag_details,
                'close_price': float(s.close_price),
                'change_percent': s.change_percent,
                'volume': s.volume,
                'sector': s.sector,
                'industry': s.industry,
                'market_cap': s.market_cap,
                'composite_score': s.composite_score,
                'signal_count': s.signal_count,
                'bullish_count': s.bullish_count,
                'bearish_count': s.bearish_count,
                'news_context': s.news_context,
            }
            for s in signals
        ]

        return Response({
            'signal_id': signal_id,
            'date': str(target_date),
            'count': len(data),
            'stocks': data,
        })


class EODPipelineStatusView(APIView):
    """
    GET /api/v1/stocks/eod/pipeline/status/

    최근 7일간의 파이프라인 실행 로그를 반환합니다.
    admin 전용.
    """

    def get(self, request):
        logs = PipelineLog.objects.order_by('-date')[:7]

        data = [
            {
                'date': str(log.date),
                'run_id': str(log.run_id),
                'status': log.status,
                'stages': log.stages,
                'ingest_quality': log.ingest_quality,
                'total_duration_seconds': log.total_duration_seconds,
                'error_message': log.error_message,
                'started_at': log.started_at.isoformat() if log.started_at else None,
                'completed_at': log.completed_at.isoformat() if log.completed_at else None,
            }
            for log in logs
        ]

        return Response({'logs': data})
