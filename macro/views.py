"""
거시경제 데이터 API Views
"""
import logging
import threading
from django.core.cache import cache
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny

from .services import MacroEconomicService
from .serializers import (
    FearGreedResponseSerializer,
    InterestRatesResponseSerializer,
    InflationResponseSerializer,
    GlobalMarketsResponseSerializer,
    EconomicCalendarResponseSerializer,
    MarketPulseResponseSerializer,
)

logger = logging.getLogger(__name__)


class MarketPulseView(APIView):
    """
    Market Pulse 전체 대시보드

    GET /api/v1/macro/pulse/
    """
    permission_classes = [AllowAny]

    def get(self, request):
        """전체 대시보드 데이터 반환"""
        try:
            service = MacroEconomicService()
            data = service.get_market_pulse_dashboard()

            serializer = MarketPulseResponseSerializer(data)
            return Response(serializer.data)

        except Exception as e:
            logger.error(f"MarketPulseView error: {e}")
            return Response(
                {'error': 'Failed to fetch market pulse data'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class FearGreedIndexView(APIView):
    """
    공포/탐욕 지수

    GET /api/v1/macro/fear-greed/
    """
    permission_classes = [AllowAny]

    def get(self, request):
        """공포/탐욕 지수 반환"""
        try:
            service = MacroEconomicService()
            data = service.get_fear_greed_index()

            serializer = FearGreedResponseSerializer(data)
            return Response(serializer.data)

        except Exception as e:
            logger.error(f"FearGreedIndexView error: {e}")
            return Response(
                {'error': 'Failed to fetch fear/greed index'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class InterestRatesView(APIView):
    """
    금리 & 수익률 곡선 대시보드

    GET /api/v1/macro/interest-rates/
    """
    permission_classes = [AllowAny]

    def get(self, request):
        """금리 대시보드 데이터 반환"""
        try:
            service = MacroEconomicService()
            data = service.get_interest_rates_dashboard()

            if 'error' in data:
                return Response(
                    {'error': data['error']},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )

            serializer = InterestRatesResponseSerializer(data)
            return Response(serializer.data)

        except Exception as e:
            logger.error(f"InterestRatesView error: {e}")
            return Response(
                {'error': 'Failed to fetch interest rates'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class InflationDashboardView(APIView):
    """
    인플레이션 & 고용 대시보드

    GET /api/v1/macro/inflation/
    """
    permission_classes = [AllowAny]

    def get(self, request):
        """인플레이션/고용 대시보드 데이터 반환"""
        try:
            service = MacroEconomicService()
            data = service.get_inflation_dashboard()

            if 'error' in data:
                return Response(
                    {'error': data['error']},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )

            serializer = InflationResponseSerializer(data)
            return Response(serializer.data)

        except Exception as e:
            logger.error(f"InflationDashboardView error: {e}")
            return Response(
                {'error': 'Failed to fetch inflation data'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class GlobalMarketsView(APIView):
    """
    글로벌 시장 대시보드

    GET /api/v1/macro/global-markets/
    """
    permission_classes = [AllowAny]

    def get(self, request):
        """글로벌 시장 데이터 반환"""
        try:
            service = MacroEconomicService()
            data = service.get_global_markets_dashboard()

            if 'error' in data:
                return Response(
                    {'error': data['error']},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )

            serializer = GlobalMarketsResponseSerializer(data)
            return Response(serializer.data)

        except Exception as e:
            logger.error(f"GlobalMarketsView error: {e}")
            return Response(
                {'error': 'Failed to fetch global markets data'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class EconomicCalendarView(APIView):
    """
    경제 캘린더

    GET /api/v1/macro/calendar/
    GET /api/v1/macro/calendar/?days=14&importance=high
    """
    permission_classes = [AllowAny]

    def get(self, request):
        """경제 캘린더 데이터 반환"""
        try:
            days = int(request.query_params.get('days', 7))
            importance = request.query_params.get('importance')

            # 유효성 검사
            days = min(max(days, 1), 30)  # 1-30일 범위

            service = MacroEconomicService()
            data = service.get_economic_calendar(
                days_ahead=days,
                importance_filter=importance
            )

            if 'error' in data and 'events_by_date' not in data:
                return Response(
                    {'error': data['error']},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )

            serializer = EconomicCalendarResponseSerializer(data)
            return Response(serializer.data)

        except ValueError:
            return Response(
                {'error': 'Invalid days parameter'},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            logger.error(f"EconomicCalendarView error: {e}")
            return Response(
                {'error': 'Failed to fetch economic calendar'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class VIXView(APIView):
    """
    VIX 지수

    GET /api/v1/macro/vix/
    """
    permission_classes = [AllowAny]

    def get(self, request):
        """VIX 지수 반환"""
        try:
            service = MacroEconomicService()
            vix_data = service.fred.get_vix()

            if vix_data:
                return Response(vix_data)

            return Response(
                {'error': 'VIX data not available'},
                status=status.HTTP_404_NOT_FOUND
            )

        except Exception as e:
            logger.error(f"VIXView error: {e}")
            return Response(
                {'error': 'Failed to fetch VIX'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class SectorPerformanceView(APIView):
    """
    섹터 성과

    GET /api/v1/macro/sectors/
    """
    permission_classes = [AllowAny]

    def get(self, request):
        """섹터 성과 데이터 반환"""
        try:
            service = MacroEconomicService()
            data = service.fmp.get_sector_performance()

            return Response(data)

        except Exception as e:
            logger.error(f"SectorPerformanceView error: {e}")
            return Response(
                {'error': 'Failed to fetch sector performance'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


# 동기화 상태 캐시 키
SYNC_STATUS_KEY = 'macro:sync_status'
SYNC_PROGRESS_KEY = 'macro:sync_progress'


def _run_data_sync():
    """백그라운드에서 데이터 동기화 실행"""
    try:
        cache.set(SYNC_STATUS_KEY, 'running', timeout=300)
        cache.set(SYNC_PROGRESS_KEY, {
            'current_step': 'economic_indicators',
            'steps_completed': 0,
            'total_steps': 4,
            'message': '경제 지표 수집 중...'
        }, timeout=300)

        service = MacroEconomicService()

        # Step 1: 경제 지표 (FRED)
        logger.info("Syncing economic indicators...")
        cache.set(SYNC_PROGRESS_KEY, {
            'current_step': 'economic_indicators',
            'steps_completed': 0,
            'total_steps': 4,
            'message': '경제 지표 수집 중 (FRED API)...'
        }, timeout=300)

        # FRED 데이터 수집 및 DB 저장
        service.sync_all_indicators()

        # Step 2: 시장 지수 (FMP)
        logger.info("Syncing market indices...")
        cache.set(SYNC_PROGRESS_KEY, {
            'current_step': 'market_indices',
            'steps_completed': 1,
            'total_steps': 4,
            'message': '시장 지수 수집 중 (FMP API)...'
        }, timeout=300)

        service.sync_market_indices()

        # Step 3: 글로벌 시장 데이터
        logger.info("Syncing global markets...")
        cache.set(SYNC_PROGRESS_KEY, {
            'current_step': 'global_markets',
            'steps_completed': 2,
            'total_steps': 4,
            'message': '글로벌 시장 데이터 수집 중...'
        }, timeout=300)

        service.sync_global_markets()

        # Step 4: 경제 캘린더
        logger.info("Syncing economic calendar...")
        cache.set(SYNC_PROGRESS_KEY, {
            'current_step': 'economic_calendar',
            'steps_completed': 3,
            'total_steps': 4,
            'message': '경제 캘린더 수집 중...'
        }, timeout=300)

        service.sync_economic_calendar()

        # 완료
        cache.set(SYNC_STATUS_KEY, 'completed', timeout=60)
        cache.set(SYNC_PROGRESS_KEY, {
            'current_step': 'done',
            'steps_completed': 4,
            'total_steps': 4,
            'message': '데이터 수집 완료!'
        }, timeout=60)

        logger.info("Data sync completed successfully")

    except Exception as e:
        logger.error(f"Data sync failed: {e}")
        cache.set(SYNC_STATUS_KEY, 'error', timeout=60)
        cache.set(SYNC_PROGRESS_KEY, {
            'current_step': 'error',
            'steps_completed': 0,
            'total_steps': 4,
            'message': f'오류 발생: {str(e)}'
        }, timeout=60)


class DataSyncView(APIView):
    """
    데이터 동기화 트리거

    POST /api/v1/macro/sync/
    """
    permission_classes = [AllowAny]

    def post(self, request):
        """데이터 동기화 시작"""
        try:
            # 이미 실행 중인지 확인
            current_status = cache.get(SYNC_STATUS_KEY)
            if current_status == 'running':
                return Response({
                    'status': 'already_running',
                    'message': '데이터 동기화가 이미 진행 중입니다.'
                })

            # 백그라운드에서 동기화 시작
            thread = threading.Thread(target=_run_data_sync, daemon=True)
            thread.start()

            return Response({
                'status': 'started',
                'message': '데이터 동기화를 시작했습니다.'
            })

        except Exception as e:
            logger.error(f"DataSyncView error: {e}")
            return Response(
                {'error': 'Failed to start data sync'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class SyncStatusView(APIView):
    """
    데이터 동기화 상태 확인

    GET /api/v1/macro/sync/status/
    """
    permission_classes = [AllowAny]

    def get(self, request):
        """동기화 상태 반환"""
        sync_status = cache.get(SYNC_STATUS_KEY, 'idle')
        progress = cache.get(SYNC_PROGRESS_KEY, {
            'current_step': 'idle',
            'steps_completed': 0,
            'total_steps': 4,
            'message': '대기 중'
        })

        return Response({
            'status': sync_status,
            'progress': progress
        })
