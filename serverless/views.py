"""
Market Movers REST API Views
"""
import logging
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from rest_framework import status
from django.core.cache import cache
from django.utils import timezone

from serverless.models import MarketMover
from serverless.serializers import MarketMoverSerializer, MarketMoverListSerializer
from serverless.tasks import sync_daily_market_movers


logger = logging.getLogger(__name__)


@api_view(['GET'])
@permission_classes([AllowAny])
def market_movers_api(request):
    """
    Market Movers API

    GET /api/v1/serverless/movers?type=gainers&date=2025-01-06

    Query Parameters:
        - type: 'gainers', 'losers', 'actives' (기본값: 'gainers')
        - date: 날짜 (YYYY-MM-DD, 기본값: 오늘)

    Response:
        {
            "success": true,
            "data": {
                "date": "2025-01-06",
                "type": "gainers",
                "count": 20,
                "movers": [...]
            }
        }
    """
    # 쿼리 파라미터
    mover_type = request.GET.get('type', 'gainers')
    date_str = request.GET.get('date', timezone.now().date().isoformat())

    # 유효성 검사
    if mover_type not in ['gainers', 'losers', 'actives']:
        return Response({
            'success': False,
            'error': {
                'code': 'INVALID_TYPE',
                'message': f"Invalid type: {mover_type}. Must be one of: gainers, losers, actives"
            }
        }, status=status.HTTP_400_BAD_REQUEST)

    # 캐시 확인
    cache_key = f'movers:{date_str}:{mover_type}'
    cached = cache.get(cache_key)
    if cached:
        logger.debug(f"캐시 HIT: {cache_key}")
        return Response(cached)

    # DB 조회
    movers = MarketMover.objects.filter(
        date=date_str,
        mover_type=mover_type
    ).order_by('rank')

    # 직렬화
    serializer = MarketMoverListSerializer(movers, many=True)

    # 응답 데이터
    response_data = {
        'success': True,
        'data': {
            'date': date_str,
            'type': mover_type,
            'count': len(serializer.data),
            'movers': serializer.data
        }
    }

    # 캐시 저장 (5분)
    cache.set(cache_key, response_data, 300)

    return Response(response_data)


@api_view(['GET'])
@permission_classes([AllowAny])
def market_mover_detail(request, symbol):
    """
    특정 종목의 Market Mover 상세 정보

    GET /api/v1/serverless/movers/AAPL?date=2025-01-06

    Query Parameters:
        - date: 날짜 (YYYY-MM-DD, 기본값: 오늘)

    Response:
        {
            "success": true,
            "data": {...}
        }
    """
    symbol = symbol.upper()
    date_str = request.GET.get('date', timezone.now().date().isoformat())

    # 캐시 확인
    cache_key = f'mover_detail:{symbol}:{date_str}'
    cached = cache.get(cache_key)
    if cached:
        logger.debug(f"캐시 HIT: {cache_key}")
        return Response(cached)

    # DB 조회
    try:
        mover = MarketMover.objects.get(
            date=date_str,
            symbol=symbol
        )
    except MarketMover.DoesNotExist:
        return Response({
            'success': False,
            'error': {
                'code': 'NOT_FOUND',
                'message': f"Market mover not found: {symbol} on {date_str}"
            }
        }, status=status.HTTP_404_NOT_FOUND)

    # 직렬화
    serializer = MarketMoverSerializer(mover)

    # 응답 데이터
    response_data = {
        'success': True,
        'data': serializer.data
    }

    # 캐시 저장 (5분)
    cache.set(cache_key, response_data, 300)

    return Response(response_data)


@api_view(['POST'])
@permission_classes([AllowAny])  # TODO: 프로덕션에서는 IsAdminUser로 변경
def trigger_sync(request):
    """
    수동 동기화 트리거 (관리자 도구용)

    POST /api/v1/serverless/sync
    {
        "date": "2025-01-06"  (optional)
    }

    Response:
        {
            "success": true,
            "data": {
                "message": "Sync task started",
                "task_id": "..."
            }
        }
    """
    date_str = request.data.get('date')

    try:
        # Celery 태스크 시작
        task = sync_daily_market_movers.delay(target_date=date_str)

        logger.info(f"✅ 수동 동기화 시작: task_id={task.id}, date={date_str or 'today'}")

        return Response({
            'success': True,
            'data': {
                'message': 'Sync task started',
                'task_id': task.id,
                'date': date_str or timezone.now().date().isoformat()
            }
        })

    except Exception as e:
        logger.exception(f"❌ 동기화 트리거 실패: {e}")
        return Response({
            'success': False,
            'error': {
                'code': 'SYNC_FAILED',
                'message': str(e)
            }
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([AllowAny])  # TODO: 프로덕션에서는 IsAdminUser로 변경
def sync_now(request):
    """
    즉시 동기화 (Celery 없이 동기 실행)

    POST /api/v1/serverless/sync-now
    {
        "date": "2025-01-06"  (optional)
    }

    Response:
        {
            "success": true,
            "data": {
                "message": "Sync completed",
                "results": {"gainers": 20, "losers": 20, "actives": 20}
            }
        }
    """
    from serverless.services.data_sync import MarketMoversSync

    date_str = request.data.get('date')

    try:
        # 동기 실행
        sync = MarketMoversSync()
        results = sync.sync_daily_movers(target_date=date_str)

        # 캐시 무효화
        today = date_str or timezone.now().date().isoformat()
        for mover_type in ['gainers', 'losers', 'actives']:
            cache_key = f'movers:{today}:{mover_type}'
            cache.delete(cache_key)

        logger.info(f"✅ 즉시 동기화 완료: date={today}, results={results}")

        return Response({
            'success': True,
            'data': {
                'message': 'Sync completed',
                'date': today,
                'results': results
            }
        })

    except Exception as e:
        logger.exception(f"❌ 즉시 동기화 실패: {e}")
        return Response({
            'success': False,
            'error': {
                'code': 'SYNC_FAILED',
                'message': str(e)
            }
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([AllowAny])
def health_check(request):
    """
    헬스체크 엔드포인트

    GET /api/v1/serverless/health

    Response:
        {
            "success": true,
            "data": {
                "status": "healthy",
                "movers_count": 60
            }
        }
    """
    # 오늘 날짜 데이터 개수 확인
    today = timezone.now().date()
    movers_count = MarketMover.objects.filter(date=today).count()

    return Response({
        'success': True,
        'data': {
            'status': 'healthy',
            'date': today.isoformat(),
            'movers_count': movers_count,
            'expected_count': 60  # gainers 20 + losers 20 + actives 20
        }
    })
