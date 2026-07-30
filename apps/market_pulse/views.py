"""
거시경제 데이터 API Views — macro v1 호환 엔드포인트.

소속: apps/market_pulse (app 레이어 root).
역할: 옛 macro v1 화면을 위한 view 집합. MP-UNIFY-1(2026-07-29)에서
  무소비 개별 엔드포인트(fear-greed/interest-rates/inflation/global-markets/
  calendar/vix/sectors)를 제거하고, 실소비 3종(pulse·sync·sync/status)만 존치.
  개별 섹션 로직은 MacroEconomicService에 보존되어 pulse 집계 경유로 유지된다.
주의: v2 화면은 `api/views/*`가 진입점. v1·v2는 응답 구조 자체가 다르므로 혼동 금지.
"""
import logging
import threading

from django.core.cache import cache
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAdminUser
from rest_framework.response import Response
from rest_framework.views import APIView

from .serializers import MarketPulseResponseSerializer
from apps.market_pulse.services.macro_service import MacroEconomicService

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
    데이터 동기화 트리거 (audit P0 #6 — IsAdminUser).

    POST /api/v1/macro/sync/
    """
    permission_classes = [IsAdminUser]

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
