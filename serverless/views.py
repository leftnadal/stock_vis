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
    Market Movers API (키워드 포함)

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
                "movers": [
                    {
                        "symbol": "NVDA",
                        "company_name": "NVIDIA Corporation",
                        "indicators": {...},
                        "keywords": ["AI 반도체 수요", "데이터센터 확장"]  # ⭐ 추가
                    },
                    ...
                ]
            }
        }
    """
    from serverless.processors import MarketMoversProcessor

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

    # 캐시 확인 (키워드 포함)
    cache_key = f'movers_with_keywords:{date_str}:{mover_type}'
    cached = cache.get(cache_key)
    if cached:
        logger.debug(f"캐시 HIT: {cache_key}")
        return Response(cached)

    # Processor 사용 ⭐
    processor = MarketMoversProcessor()
    movers = processor.get_movers_with_keywords(date_str, mover_type)

    # 응답 데이터
    response_data = {
        'success': True,
        'data': {
            'date': date_str,
            'type': mover_type,
            'count': len(movers),
            'movers': movers
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
def get_keywords(request, symbol):
    """
    특정 종목의 LLM 키워드 조회

    GET /api/v1/serverless/keywords/AAPL?date=2026-01-24

    Query Parameters:
        - date: 날짜 (YYYY-MM-DD, 기본값: 오늘)

    Response:
        {
            "success": true,
            "data": {
                "symbol": "AAPL",
                "date": "2026-01-24",
                "keywords": [
                    {"text": "AI 반도체", "category": "sector", "confidence": 0.95},
                    ...
                ]
            }
        }
    """
    from serverless.models import StockKeyword

    symbol = symbol.upper()
    date_str = request.GET.get('date', timezone.now().date().isoformat())

    # DB 조회
    try:
        keyword_obj = StockKeyword.objects.get(
            symbol=symbol,
            date=date_str,
            status='completed'
        )
        keywords = keyword_obj.keywords
    except StockKeyword.DoesNotExist:
        # 키워드가 없으면 빈 배열 반환
        keywords = []

    return Response({
        'success': True,
        'data': {
            'symbol': symbol,
            'date': date_str,
            'keywords': keywords
        }
    })


@api_view(['POST'])
@permission_classes([AllowAny])
def get_batch_keywords(request):
    """
    여러 종목의 LLM 키워드 일괄 조회

    POST /api/v1/serverless/keywords/batch
    {
        "symbols": ["AAPL", "NVDA", "MSFT"],
        "date": "2026-01-24"  (optional)
    }

    Response:
        {
            "success": true,
            "data": {
                "date": "2026-01-24",
                "keywords": {
                    "AAPL": [...],
                    "NVDA": [...],
                    "MSFT": [...]
                }
            }
        }
    """
    from serverless.models import StockKeyword

    symbols = request.data.get('symbols', [])
    date_str = request.data.get('date', timezone.now().date().isoformat())

    # 심볼 대문자 변환
    symbols = [s.upper() for s in symbols]

    # DB 조회 (N+1 방지)
    keyword_objs = StockKeyword.objects.filter(
        symbol__in=symbols,
        date=date_str,
        status='completed'
    )

    # 심볼별 키워드 매핑
    keywords_map = {obj.symbol: obj.keywords for obj in keyword_objs}

    # 없는 종목은 빈 배열
    result = {symbol: keywords_map.get(symbol, []) for symbol in symbols}

    return Response({
        'success': True,
        'data': {
            'date': date_str,
            'keywords': result
        }
    })


@api_view(['POST'])
@permission_classes([AllowAny])  # TODO: 프로덕션에서는 IsAdminUser로 변경
def trigger_keyword_generation(request):
    """
    AI 키워드 생성 트리거 (Celery 비동기)

    POST /api/v1/serverless/keywords/generate-all
    {
        "type": "gainers",  (optional, default: "gainers")
        "date": "2026-01-24"  (optional, default: 오늘)
    }

    Response:
        {
            "success": true,
            "data": {
                "message": "Keyword generation started",
                "task_id": "...",
                "mover_type": "gainers",
                "date": "2026-01-24"
            }
        }
    """
    from serverless.tasks import keyword_generation_pipeline

    mover_type = request.data.get('type', 'gainers')
    date_str = request.data.get('date', timezone.now().date().isoformat())

    # 유효성 검사
    if mover_type not in ['gainers', 'losers', 'actives']:
        return Response({
            'success': False,
            'error': {
                'code': 'INVALID_TYPE',
                'message': f"Invalid type: {mover_type}. Must be one of: gainers, losers, actives"
            }
        }, status=status.HTTP_400_BAD_REQUEST)

    try:
        # Celery 파이프라인 시작
        result = keyword_generation_pipeline.delay(movers_date=date_str, mover_type=mover_type)

        logger.info(f"✅ AI 키워드 생성 시작: task_id={result.id}, type={mover_type}, date={date_str}")

        return Response({
            'success': True,
            'data': {
                'message': 'Keyword generation started',
                'task_id': result.id,
                'mover_type': mover_type,
                'date': date_str
            }
        })

    except Exception as e:
        logger.exception(f"❌ 키워드 생성 트리거 실패: {e}")
        return Response({
            'success': False,
            'error': {
                'code': 'GENERATION_FAILED',
                'message': str(e)
            }
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([AllowAny])  # TODO: 프로덕션에서는 IsAdminUser로 변경
def generate_screener_keywords(request):
    """
    스크리너 종목들의 AI 키워드 일괄 생성 (Celery 비동기)

    POST /api/v1/serverless/keywords/generate-screener
    {
        "stocks": [
            {"symbol": "AAPL", "company_name": "Apple Inc.", "sector": "Technology", "change_percent": 2.5},
            {"symbol": "NVDA", "company_name": "NVIDIA Corporation", "sector": "Technology", "change_percent": 5.3},
            ...
        ]
    }

    Response:
        {
            "success": true,
            "data": {
                "message": "Screener keyword generation started",
                "task_id": "...",
                "stock_count": 50
            }
        }
    """
    from serverless.tasks import generate_screener_keywords_task

    stocks = request.data.get('stocks', [])

    if not stocks:
        return Response({
            'success': False,
            'error': {
                'code': 'NO_STOCKS',
                'message': 'No stocks provided'
            }
        }, status=status.HTTP_400_BAD_REQUEST)

    if len(stocks) > 100:
        return Response({
            'success': False,
            'error': {
                'code': 'TOO_MANY_STOCKS',
                'message': f'Maximum 100 stocks allowed, got {len(stocks)}'
            }
        }, status=status.HTTP_400_BAD_REQUEST)

    try:
        # Celery 태스크 시작
        result = generate_screener_keywords_task.delay(stocks)

        logger.info(f"✅ 스크리너 키워드 생성 시작: task_id={result.id}, stocks={len(stocks)}")

        return Response({
            'success': True,
            'data': {
                'message': 'Screener keyword generation started',
                'task_id': result.id,
                'stock_count': len(stocks)
            }
        })

    except Exception as e:
        logger.exception(f"❌ 스크리너 키워드 생성 트리거 실패: {e}")
        return Response({
            'success': False,
            'error': {
                'code': 'GENERATION_FAILED',
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
