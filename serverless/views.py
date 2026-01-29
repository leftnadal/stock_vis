"""
Serverless App REST API Views

Market Movers, Market Breadth, Screener Presets, Sector Heatmap
"""
import logging
from rest_framework.decorators import api_view, permission_classes, authentication_classes
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from rest_framework import status
from django.core.cache import cache
from django.utils import timezone
from django.db import models

from serverless.models import MarketMover, ScreenerAlert, AlertHistory
from serverless.serializers import (
    MarketMoverSerializer,
    MarketMoverListSerializer,
    ScreenerAlertSerializer,
    ScreenerAlertCreateSerializer,
    AlertHistorySerializer,
    AlertHistoryListSerializer,
)
from serverless.tasks import sync_daily_market_movers


logger = logging.getLogger(__name__)


@api_view(['GET'])
@authentication_classes([])  # 인증 완전 비활성화 (공개 API)
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
@authentication_classes([])  # 인증 완전 비활성화 (공개 API)
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
@authentication_classes([])  # 인증 완전 비활성화 (공개 API)
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
@authentication_classes([])  # 인증 완전 비활성화 (공개 API)
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
@authentication_classes([])  # TODO: 프로덕션에서는 인증 추가
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
@authentication_classes([])  # 인증 완전 비활성화 (공개 API)
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


# ========================================
# Market Breadth API
# ========================================

@api_view(['GET'])
@authentication_classes([])
@permission_classes([AllowAny])
def market_breadth_api(request):
    """
    Market Breadth (시장 건강도) 조회

    GET /api/v1/serverless/breadth?date=2026-01-27

    Query Parameters:
        - date: 날짜 (YYYY-MM-DD, 기본값: 오늘)

    Response:
        {
            "success": true,
            "data": {
                "date": "2026-01-27",
                "advancing_count": 1500,
                "declining_count": 1000,
                "advance_decline_ratio": 1.5,
                "breadth_signal": "bullish",
                "signal_interpretation": {...},
                "indices": {...},
                "methodology": {...}
            }
        }
    """
    from serverless.services.market_breadth_service import MarketBreadthService
    from serverless.serializers import MarketBreadthSerializer
    from serverless.models import MarketBreadth

    date_str = request.GET.get('date')

    if date_str:
        from datetime import datetime
        try:
            target_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            return Response({
                'success': False,
                'error': {
                    'code': 'INVALID_DATE',
                    'message': f"Invalid date format: {date_str}. Use YYYY-MM-DD."
                }
            }, status=status.HTTP_400_BAD_REQUEST)
    else:
        target_date = timezone.now().date()

    # 캐시 확인
    cache_key = f'market_breadth_api:{target_date}'
    cached = cache.get(cache_key)
    if cached:
        return Response(cached)

    try:
        breadth = MarketBreadth.objects.get(date=target_date)
        serializer = MarketBreadthSerializer(breadth)

        # 주요 지수 데이터 추가 (yfinance)
        indices = _get_market_indices()

        # 방법론 설명 추가
        methodology = {
            'sample_size': 50,
            'total_market': 5000,
            'sample_rate': '1%',
            'data_source': 'FMP API (Most Active Stocks)',
            'accuracy': {
                'direction': '높음 (시장 방향성 판단)',
                'exact_count': '낮음 (1% 샘플링)',
                'volume': '추정치 (실제 거래량 데이터 없음)',
            },
            'interpretation_guide': {
                'strong_bullish': 'A/D 비율 2.0 이상 - 상승 종목이 하락 종목의 2배 이상',
                'bullish': 'A/D 비율 1.5~2.0 - 상승 우위',
                'neutral': 'A/D 비율 0.67~1.5 - 상승/하락 비슷',
                'bearish': 'A/D 비율 0.5~0.67 - 하락 우위',
                'strong_bearish': 'A/D 비율 0.5 미만 - 하락 종목이 2배 이상',
            },
            'limitations': [
                '거래량 상위 50개 종목만 샘플링 (대형주 편향)',
                '실제 NYSE/NASDAQ A/D 데이터와 다를 수 있음',
                '거래량은 가격 변동률로 추정한 값',
            ],
        }

        response_data = {
            'success': True,
            'data': {
                **serializer.data,
                'indices': indices,
                'methodology': methodology,
            }
        }

        cache.set(cache_key, response_data, 300)  # 5분 캐시
        return Response(response_data)

    except MarketBreadth.DoesNotExist:
        return Response({
            'success': False,
            'error': {
                'code': 'NOT_FOUND',
                'message': f"Market breadth data not found for {target_date}"
            }
        }, status=status.HTTP_404_NOT_FOUND)


def _get_market_indices():
    """주요 시장 지수 데이터 조회 (yfinance)"""
    import yfinance as yf

    indices = {}
    index_symbols = {
        'sp500': ('^GSPC', 'S&P 500'),
        'nasdaq': ('^IXIC', 'NASDAQ'),
        'dow': ('^DJI', 'Dow Jones'),
    }

    for key, (symbol, name) in index_symbols.items():
        try:
            ticker = yf.Ticker(symbol)
            info = ticker.fast_info
            price = info.last_price
            prev_close = info.previous_close
            change = price - prev_close
            change_pct = (change / prev_close) * 100 if prev_close else 0

            indices[key] = {
                'name': name,
                'symbol': symbol,
                'price': round(price, 2),
                'change': round(change, 2),
                'change_pct': round(change_pct, 2),
            }
        except Exception as e:
            logger.warning(f"지수 조회 실패 {symbol}: {e}")
            indices[key] = {
                'name': name,
                'symbol': symbol,
                'price': None,
                'change': None,
                'change_pct': None,
                'error': str(e),
            }

    return indices


@api_view(['GET'])
@authentication_classes([])
@permission_classes([AllowAny])
def market_breadth_history(request):
    """
    Market Breadth 히스토리 조회

    GET /api/v1/serverless/breadth/history?days=30

    Query Parameters:
        - days: 조회 일수 (기본값: 30, 최대: 90)

    Response:
        {
            "success": true,
            "data": {
                "count": 30,
                "history": [...]
            }
        }
    """
    from serverless.services.market_breadth_service import MarketBreadthService
    from serverless.serializers import MarketBreadthHistorySerializer
    from serverless.models import MarketBreadth
    from datetime import timedelta

    days = int(request.GET.get('days', 30))
    days = min(days, 90)  # 최대 90일

    # 캐시 확인
    cache_key = f'market_breadth_history:{days}'
    cached = cache.get(cache_key)
    if cached:
        return Response(cached)

    start_date = timezone.now().date() - timedelta(days=days)
    breadths = MarketBreadth.objects.filter(date__gte=start_date).order_by('-date')

    serializer = MarketBreadthHistorySerializer(breadths, many=True)

    response_data = {
        'success': True,
        'data': {
            'count': len(serializer.data),
            'days': days,
            'history': serializer.data
        }
    }

    cache.set(cache_key, response_data, 3600)  # 1시간 캐시
    return Response(response_data)


@api_view(['POST'])
@permission_classes([AllowAny])  # TODO: 프로덕션에서는 IsAdminUser로 변경
def trigger_breadth_sync(request):
    """
    Market Breadth 수동 동기화

    POST /api/v1/serverless/breadth/sync
    """
    from serverless.tasks import calculate_daily_market_breadth

    date_str = request.data.get('date')

    try:
        task = calculate_daily_market_breadth.delay(target_date=date_str)

        return Response({
            'success': True,
            'data': {
                'message': 'Market breadth sync started',
                'task_id': task.id,
                'date': date_str or timezone.now().date().isoformat()
            }
        })
    except Exception as e:
        logger.exception(f"Market breadth sync failed: {e}")
        return Response({
            'success': False,
            'error': {'code': 'SYNC_FAILED', 'message': str(e)}
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# ========================================
# Sector Heatmap API
# ========================================

@api_view(['GET'])
@authentication_classes([])
@permission_classes([AllowAny])
def sector_heatmap_api(request):
    """
    섹터 히트맵 조회

    GET /api/v1/serverless/heatmap/sectors?date=2026-01-27

    Response:
        {
            "success": true,
            "data": {
                "date": "2026-01-27",
                "sectors": [
                    {
                        "name": "Technology",
                        "name_ko": "기술",
                        "return_pct": 2.5,
                        "color": "#22c55e",
                        ...
                    }
                ]
            }
        }
    """
    from serverless.services.sector_heatmap_service import SectorHeatmapService
    from serverless.serializers import SectorPerformanceSerializer
    from serverless.models import SectorPerformance
    from datetime import datetime

    date_str = request.GET.get('date')

    if date_str:
        try:
            target_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            return Response({
                'success': False,
                'error': {'code': 'INVALID_DATE', 'message': f"Invalid date: {date_str}"}
            }, status=status.HTTP_400_BAD_REQUEST)
    else:
        target_date = timezone.now().date()

    # 캐시 확인
    cache_key = f'sector_heatmap_api:{target_date}'
    cached = cache.get(cache_key)
    if cached:
        return Response(cached)

    sectors = SectorPerformance.objects.filter(date=target_date).order_by('-return_pct')

    if not sectors.exists():
        return Response({
            'success': True,
            'data': {
                'date': target_date.isoformat(),
                'sectors': [],
                'message': 'No sector data for this date'
            }
        })

    serializer = SectorPerformanceSerializer(sectors, many=True)

    # 요약 정보 계산
    sectors_list = list(sectors)
    gains = [s for s in sectors_list if s.return_pct >= 0]
    losses = [s for s in sectors_list if s.return_pct < 0]
    avg_return = sum(float(s.return_pct) for s in sectors_list) / len(sectors_list)

    response_data = {
        'success': True,
        'data': {
            'date': target_date.isoformat(),
            'sectors': serializer.data,
            'summary': {
                'sectors_up': len(gains),
                'sectors_down': len(losses),
                'avg_return_pct': round(avg_return, 2),
                'best_sector': sectors_list[0].sector if sectors_list else None,
                'worst_sector': sectors_list[-1].sector if sectors_list else None,
            }
        }
    }

    cache.set(cache_key, response_data, 300)  # 5분 캐시
    return Response(response_data)


@api_view(['GET'])
@authentication_classes([])
@permission_classes([AllowAny])
def sector_stocks_api(request, sector):
    """
    특정 섹터의 Top Movers 조회

    GET /api/v1/serverless/heatmap/sectors/Technology/stocks?limit=5

    Response:
        {
            "success": true,
            "data": {
                "sector": "Technology",
                "sector_ko": "기술",
                "top_gainers": [...],
                "top_losers": [...]
            }
        }
    """
    from serverless.services.sector_heatmap_service import SectorHeatmapService

    limit = int(request.GET.get('limit', 5))
    limit = min(limit, 10)  # 최대 10개

    date_str = request.GET.get('date')
    if date_str:
        from datetime import datetime
        try:
            target_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            return Response({
                'success': False,
                'error': {'code': 'INVALID_DATE', 'message': f"Invalid date: {date_str}"}
            }, status=status.HTTP_400_BAD_REQUEST)
    else:
        target_date = timezone.now().date()

    service = SectorHeatmapService()
    result = service.get_top_movers_by_sector(sector, limit=limit, target_date=target_date)

    return Response({
        'success': True,
        'data': result
    })


@api_view(['POST'])
@permission_classes([AllowAny])  # TODO: 프로덕션에서는 IsAdminUser로 변경
def trigger_heatmap_sync(request):
    """
    섹터 히트맵 수동 동기화

    POST /api/v1/serverless/heatmap/sync
    """
    from serverless.tasks import calculate_daily_sector_heatmap

    date_str = request.data.get('date')

    try:
        task = calculate_daily_sector_heatmap.delay(target_date=date_str)

        return Response({
            'success': True,
            'data': {
                'message': 'Sector heatmap sync started',
                'task_id': task.id,
                'date': date_str or timezone.now().date().isoformat()
            }
        })
    except Exception as e:
        logger.exception(f"Sector heatmap sync failed: {e}")
        return Response({
            'success': False,
            'error': {'code': 'SYNC_FAILED', 'message': str(e)}
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# ========================================
# Screener Preset API
# ========================================

@api_view(['GET', 'POST'])
@authentication_classes([])
@permission_classes([AllowAny])
def screener_presets_api(request):
    """
    스크리너 프리셋 목록 조회 / 생성

    GET /api/v1/serverless/presets?category=beginner
    POST /api/v1/serverless/presets
    """
    from serverless.models import ScreenerPreset
    from serverless.serializers import ScreenerPresetListSerializer, ScreenerPresetCreateSerializer

    if request.method == 'GET':
        category = request.GET.get('category')

        queryset = ScreenerPreset.objects.all()

        # 카테고리 필터
        if category:
            queryset = queryset.filter(category=category)
        else:
            # 기본: 시스템 프리셋 + 공개 프리셋
            queryset = queryset.filter(
                models.Q(category__in=['system', 'beginner', 'intermediate']) |
                models.Q(is_public=True)
            )

        # 사용자 본인 프리셋 추가
        if request.user.is_authenticated:
            user_presets = ScreenerPreset.objects.filter(user=request.user)
            queryset = queryset | user_presets

        queryset = queryset.distinct().order_by('-use_count', 'name')

        serializer = ScreenerPresetListSerializer(queryset, many=True)

        return Response({
            'success': True,
            'data': {
                'count': len(serializer.data),
                'presets': serializer.data
            }
        })

    elif request.method == 'POST':
        serializer = ScreenerPresetCreateSerializer(
            data=request.data,
            context={'request': request}
        )

        if serializer.is_valid():
            preset = serializer.save()
            return Response({
                'success': True,
                'data': {
                    'id': preset.id,
                    'message': 'Preset created successfully'
                }
            }, status=status.HTTP_201_CREATED)
        else:
            return Response({
                'success': False,
                'error': {
                    'code': 'VALIDATION_ERROR',
                    'message': serializer.errors
                }
            }, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET', 'PATCH', 'DELETE'])
@permission_classes([AllowAny])
def screener_preset_detail(request, preset_id):
    """
    스크리너 프리셋 상세 조회 / 수정 / 삭제

    GET /api/v1/serverless/presets/{id}
    PATCH /api/v1/serverless/presets/{id}
    DELETE /api/v1/serverless/presets/{id}
    """
    from serverless.models import ScreenerPreset
    from serverless.serializers import ScreenerPresetSerializer

    try:
        preset = ScreenerPreset.objects.get(id=preset_id)
    except ScreenerPreset.DoesNotExist:
        return Response({
            'success': False,
            'error': {'code': 'NOT_FOUND', 'message': f"Preset not found: {preset_id}"}
        }, status=status.HTTP_404_NOT_FOUND)

    if request.method == 'GET':
        # 사용 횟수 증가
        preset.use_count += 1
        preset.last_used_at = timezone.now()
        preset.save(update_fields=['use_count', 'last_used_at'])

        serializer = ScreenerPresetSerializer(preset, context={'request': request})
        return Response({
            'success': True,
            'data': serializer.data
        })

    elif request.method == 'PATCH':
        # 소유자만 수정 가능
        if preset.user and preset.user != request.user:
            return Response({
                'success': False,
                'error': {'code': 'FORBIDDEN', 'message': 'You can only edit your own presets'}
            }, status=status.HTTP_403_FORBIDDEN)

        serializer = ScreenerPresetSerializer(
            preset, data=request.data, partial=True, context={'request': request}
        )
        if serializer.is_valid():
            serializer.save()
            return Response({
                'success': True,
                'data': serializer.data
            })
        else:
            return Response({
                'success': False,
                'error': {'code': 'VALIDATION_ERROR', 'message': serializer.errors}
            }, status=status.HTTP_400_BAD_REQUEST)

    elif request.method == 'DELETE':
        # 소유자만 삭제 가능 (시스템 프리셋은 삭제 불가)
        if preset.category in ['system', 'beginner', 'intermediate']:
            return Response({
                'success': False,
                'error': {'code': 'FORBIDDEN', 'message': 'Cannot delete system presets'}
            }, status=status.HTTP_403_FORBIDDEN)

        if preset.user and preset.user != request.user:
            return Response({
                'success': False,
                'error': {'code': 'FORBIDDEN', 'message': 'You can only delete your own presets'}
            }, status=status.HTTP_403_FORBIDDEN)

        preset.delete()
        return Response({
            'success': True,
            'data': {'message': 'Preset deleted successfully'}
        })


@api_view(['POST'])
@permission_classes([AllowAny])
def execute_preset(request, preset_id):
    """
    프리셋 실행 (필터 적용 결과 반환)

    POST /api/v1/serverless/presets/{id}/execute
    {
        "page": 1,
        "page_size": 50
    }
    """
    from serverless.models import ScreenerPreset
    from serverless.services.filter_engine import FilterEngine

    try:
        preset = ScreenerPreset.objects.get(id=preset_id)
    except ScreenerPreset.DoesNotExist:
        return Response({
            'success': False,
            'error': {'code': 'NOT_FOUND', 'message': f"Preset not found: {preset_id}"}
        }, status=status.HTTP_404_NOT_FOUND)

    page = int(request.data.get('page', 1))
    page_size = int(request.data.get('page_size', 50))
    page_size = min(page_size, 100)  # 최대 100개

    offset = (page - 1) * page_size

    engine = FilterEngine()
    results = engine.apply_filters(
        filters_dict=preset.filters_json,
        limit=page_size,
        offset=offset,
        sort_by=preset.sort_by,
        sort_order=preset.sort_order
    )

    # 사용 횟수 증가
    preset.use_count += 1
    preset.last_used_at = timezone.now()
    preset.save(update_fields=['use_count', 'last_used_at'])

    return Response({
        'success': True,
        'data': {
            'preset_id': preset_id,
            'preset_name': preset.name,
            **results
        }
    })


# ========================================
# Screener Filter Metadata API
# ========================================

@api_view(['GET'])
@authentication_classes([])
@permission_classes([AllowAny])
def screener_filters_api(request):
    """
    사용 가능한 필터 목록 조회

    GET /api/v1/serverless/filters?category=fundamental

    Response:
        {
            "success": true,
            "data": {
                "categories": [...],
                "filters": {...}
            }
        }
    """
    from serverless.models import ScreenerFilter
    from serverless.serializers import ScreenerFilterSerializer

    category = request.GET.get('category')

    # 캐시 확인
    cache_key = f'screener_filters:{category or "all"}'
    cached = cache.get(cache_key)
    if cached:
        return Response(cached)

    queryset = ScreenerFilter.objects.filter(is_active=True)

    if category:
        queryset = queryset.filter(category=category)

    queryset = queryset.order_by('category', 'display_order')

    # 카테고리별 그룹화
    filters_by_category = {}
    for f in queryset:
        if f.category not in filters_by_category:
            filters_by_category[f.category] = []
        filters_by_category[f.category].append(ScreenerFilterSerializer(f).data)

    # 카테고리 목록
    categories = [
        {'id': 'price', 'label': '가격', 'label_ko': '가격'},
        {'id': 'volume', 'label': 'Volume', 'label_ko': '거래량'},
        {'id': 'fundamental', 'label': 'Fundamental', 'label_ko': '펀더멘탈'},
        {'id': 'technical', 'label': 'Technical', 'label_ko': '기술적'},
        {'id': 'dividend', 'label': 'Dividend', 'label_ko': '배당'},
        {'id': 'other', 'label': 'Other', 'label_ko': '기타'},
    ]

    response_data = {
        'success': True,
        'data': {
            'categories': categories,
            'filters': filters_by_category,
            'total_count': queryset.count()
        }
    }

    cache.set(cache_key, response_data, 3600)  # 1시간 캐시
    return Response(response_data)


# ========================================
# Advanced Screener API (with pagination)
# ========================================

@api_view(['POST'])
@authentication_classes([])
@permission_classes([AllowAny])
def advanced_screener_api(request):
    """
    고급 스크리너 API (50개 필터, 페이지네이션 지원)

    POST /api/v1/serverless/screener
    {
        "filters": {
            "market_cap_min": 1000000000,
            "pe_ratio_max": 20,
            "sector": ["Technology"]
        },
        "sort_by": "change_percent",
        "sort_order": "desc",
        "page": 1,
        "page_size": 50
    }

    Response:
        {
            "success": true,
            "data": {
                "results": [...],
                "count": 234,
                "total_pages": 5,
                "current_page": 1,
                ...
            }
        }
    """
    from serverless.services.filter_engine import FilterEngine

    filters_dict = request.data.get('filters', {})
    sort_by = request.data.get('sort_by', 'marketCap')
    sort_order = request.data.get('sort_order', 'desc')
    page = int(request.data.get('page', 1))
    page_size = int(request.data.get('page_size', 50))
    page_size = min(page_size, 100)  # 최대 100개

    offset = (page - 1) * page_size

    engine = FilterEngine()

    # 필터 유효성 검증
    validation = engine.validate_filters(filters_dict)
    if not validation['valid']:
        return Response({
            'success': False,
            'error': {
                'code': 'INVALID_FILTERS',
                'message': validation['errors']
            }
        }, status=status.HTTP_400_BAD_REQUEST)

    # 필터 적용
    try:
        results = engine.apply_filters(
            filters_dict=filters_dict,
            limit=page_size,
            offset=offset,
            sort_by=sort_by,
            sort_order=sort_order
        )

        # 페이지네이션 URL 생성
        base_url = request.build_absolute_uri().split('?')[0]
        next_url = None
        previous_url = None

        if results['current_page'] < results['total_pages']:
            next_url = f"{base_url}?page={results['current_page'] + 1}"
        if results['current_page'] > 1:
            previous_url = f"{base_url}?page={results['current_page'] - 1}"

        return Response({
            'success': True,
            'data': {
                **results,
                'next': next_url,
                'previous': previous_url,
            }
        })

    except Exception as e:
        logger.exception(f"Screener error: {e}")
        return Response({
            'success': False,
            'error': {'code': 'SCREENER_ERROR', 'message': str(e)}
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# ========================================
# Screener Alert API (Phase 1)
# ========================================

@api_view(['GET', 'POST'])
@permission_classes([AllowAny])  # TODO: 프로덕션에서는 IsAuthenticated로 변경
def screener_alerts_api(request):
    """
    스크리너 알림 목록 조회 / 생성

    GET /api/v1/serverless/alerts
    POST /api/v1/serverless/alerts

    Response:
        {
            "success": true,
            "data": {
                "count": 5,
                "alerts": [...]
            }
        }
    """
    if request.method == 'GET':
        # 사용자 알림 목록 조회
        if request.user.is_authenticated:
            alerts = ScreenerAlert.objects.filter(user=request.user).order_by('-created_at')
        else:
            # 비인증 사용자는 빈 목록
            alerts = ScreenerAlert.objects.none()

        serializer = ScreenerAlertSerializer(alerts, many=True)

        return Response({
            'success': True,
            'data': {
                'count': len(serializer.data),
                'alerts': serializer.data
            }
        })

    elif request.method == 'POST':
        if not request.user.is_authenticated:
            return Response({
                'success': False,
                'error': {'code': 'UNAUTHORIZED', 'message': 'Login required'}
            }, status=status.HTTP_401_UNAUTHORIZED)

        serializer = ScreenerAlertCreateSerializer(
            data=request.data,
            context={'request': request}
        )

        if serializer.is_valid():
            alert = serializer.save()
            return Response({
                'success': True,
                'data': {
                    'id': alert.id,
                    'message': 'Alert created successfully'
                }
            }, status=status.HTTP_201_CREATED)
        else:
            return Response({
                'success': False,
                'error': {'code': 'VALIDATION_ERROR', 'message': serializer.errors}
            }, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET', 'PATCH', 'DELETE'])
@permission_classes([AllowAny])  # TODO: 프로덕션에서는 IsAuthenticated로 변경
def screener_alert_detail(request, alert_id):
    """
    스크리너 알림 상세 조회 / 수정 / 삭제

    GET /api/v1/serverless/alerts/{id}
    PATCH /api/v1/serverless/alerts/{id}
    DELETE /api/v1/serverless/alerts/{id}
    """
    try:
        alert = ScreenerAlert.objects.get(id=alert_id)
    except ScreenerAlert.DoesNotExist:
        return Response({
            'success': False,
            'error': {'code': 'NOT_FOUND', 'message': f"Alert not found: {alert_id}"}
        }, status=status.HTTP_404_NOT_FOUND)

    # 소유자 체크
    if request.user.is_authenticated and alert.user != request.user:
        return Response({
            'success': False,
            'error': {'code': 'FORBIDDEN', 'message': 'Access denied'}
        }, status=status.HTTP_403_FORBIDDEN)

    if request.method == 'GET':
        serializer = ScreenerAlertSerializer(alert, context={'request': request})
        return Response({
            'success': True,
            'data': serializer.data
        })

    elif request.method == 'PATCH':
        serializer = ScreenerAlertSerializer(
            alert, data=request.data, partial=True, context={'request': request}
        )
        if serializer.is_valid():
            serializer.save()
            return Response({
                'success': True,
                'data': serializer.data
            })
        else:
            return Response({
                'success': False,
                'error': {'code': 'VALIDATION_ERROR', 'message': serializer.errors}
            }, status=status.HTTP_400_BAD_REQUEST)

    elif request.method == 'DELETE':
        alert.delete()
        return Response({
            'success': True,
            'data': {'message': 'Alert deleted successfully'}
        })


@api_view(['POST'])
@permission_classes([AllowAny])  # TODO: 프로덕션에서는 IsAuthenticated로 변경
def toggle_alert(request, alert_id):
    """
    알림 활성화/비활성화 토글

    POST /api/v1/serverless/alerts/{id}/toggle
    """
    try:
        alert = ScreenerAlert.objects.get(id=alert_id)
    except ScreenerAlert.DoesNotExist:
        return Response({
            'success': False,
            'error': {'code': 'NOT_FOUND', 'message': f"Alert not found: {alert_id}"}
        }, status=status.HTTP_404_NOT_FOUND)

    if request.user.is_authenticated and alert.user != request.user:
        return Response({
            'success': False,
            'error': {'code': 'FORBIDDEN', 'message': 'Access denied'}
        }, status=status.HTTP_403_FORBIDDEN)

    alert.is_active = not alert.is_active
    alert.save(update_fields=['is_active', 'updated_at'])

    return Response({
        'success': True,
        'data': {
            'id': alert.id,
            'is_active': alert.is_active,
            'message': f"Alert {'activated' if alert.is_active else 'deactivated'}"
        }
    })


@api_view(['GET'])
@permission_classes([AllowAny])  # TODO: 프로덕션에서는 IsAuthenticated로 변경
def alert_history_api(request):
    """
    알림 이력 조회

    GET /api/v1/serverless/alerts/history?limit=20

    Query Parameters:
        - limit: 조회 개수 (기본값: 20, 최대: 100)
        - unread_only: 읽지 않은 알림만 (기본값: false)
    """
    if not request.user.is_authenticated:
        return Response({
            'success': True,
            'data': {'count': 0, 'history': [], 'unread_count': 0}
        })

    limit = int(request.GET.get('limit', 20))
    limit = min(limit, 100)
    unread_only = request.GET.get('unread_only', 'false').lower() == 'true'

    # 사용자 알림 이력 조회
    queryset = AlertHistory.objects.filter(
        alert__user=request.user
    ).select_related('alert').order_by('-triggered_at')

    if unread_only:
        queryset = queryset.filter(read_at__isnull=True, dismissed=False)

    history = queryset[:limit]
    unread_count = AlertHistory.objects.filter(
        alert__user=request.user,
        read_at__isnull=True,
        dismissed=False
    ).count()

    serializer = AlertHistoryListSerializer(history, many=True)

    return Response({
        'success': True,
        'data': {
            'count': len(serializer.data),
            'history': serializer.data,
            'unread_count': unread_count
        }
    })


@api_view(['POST'])
@permission_classes([AllowAny])  # TODO: 프로덕션에서는 IsAuthenticated로 변경
def mark_alert_read(request, history_id):
    """
    알림 읽음 처리

    POST /api/v1/serverless/alerts/history/{id}/read
    """
    try:
        history = AlertHistory.objects.select_related('alert').get(id=history_id)
    except AlertHistory.DoesNotExist:
        return Response({
            'success': False,
            'error': {'code': 'NOT_FOUND', 'message': f"History not found: {history_id}"}
        }, status=status.HTTP_404_NOT_FOUND)

    if request.user.is_authenticated and history.alert.user != request.user:
        return Response({
            'success': False,
            'error': {'code': 'FORBIDDEN', 'message': 'Access denied'}
        }, status=status.HTTP_403_FORBIDDEN)

    history.read_at = timezone.now()
    history.save(update_fields=['read_at'])

    return Response({
        'success': True,
        'data': {'message': 'Marked as read'}
    })


@api_view(['POST'])
@permission_classes([AllowAny])  # TODO: 프로덕션에서는 IsAuthenticated로 변경
def dismiss_alert(request, history_id):
    """
    알림 해제

    POST /api/v1/serverless/alerts/history/{id}/dismiss
    """
    try:
        history = AlertHistory.objects.select_related('alert').get(id=history_id)
    except AlertHistory.DoesNotExist:
        return Response({
            'success': False,
            'error': {'code': 'NOT_FOUND', 'message': f"History not found: {history_id}"}
        }, status=status.HTTP_404_NOT_FOUND)

    if request.user.is_authenticated and history.alert.user != request.user:
        return Response({
            'success': False,
            'error': {'code': 'FORBIDDEN', 'message': 'Access denied'}
        }, status=status.HTTP_403_FORBIDDEN)

    history.dismissed = True
    history.read_at = history.read_at or timezone.now()
    history.save(update_fields=['dismissed', 'read_at'])

    return Response({
        'success': True,
        'data': {'message': 'Alert dismissed'}
    })


# ========================================
# Preset Sharing System (Phase 2.1)
# ========================================

@api_view(['POST'])
@permission_classes([AllowAny])  # TODO: 프로덕션에서는 IsAuthenticated로 변경
def share_preset(request, preset_id):
    """
    프리셋 공유 코드 생성

    POST /api/v1/serverless/presets/{preset_id}/share

    Response:
        {
            "success": true,
            "data": {
                "share_code": "abc12345",
                "share_url": "https://stock-vis.com/screener/presets/shared/abc12345"
            }
        }
    """
    from serverless.models import ScreenerPreset
    import secrets

    try:
        preset = ScreenerPreset.objects.get(id=preset_id)
    except ScreenerPreset.DoesNotExist:
        return Response({
            'success': False,
            'error': {'code': 'NOT_FOUND', 'message': f"Preset not found: {preset_id}"}
        }, status=status.HTTP_404_NOT_FOUND)

    # 소유자만 공유 가능
    if request.user.is_authenticated and preset.user and preset.user != request.user:
        return Response({
            'success': False,
            'error': {'code': 'FORBIDDEN', 'message': 'You can only share your own presets'}
        }, status=status.HTTP_403_FORBIDDEN)

    # 이미 공유 코드가 있으면 재사용
    if preset.share_code:
        share_code = preset.share_code
    else:
        # 공유 코드 생성 (8자리 영숫자)
        share_code = secrets.token_urlsafe(6)[:8]

        # 중복 체크 (극히 드물지만 안전장치)
        while ScreenerPreset.objects.filter(share_code=share_code).exists():
            share_code = secrets.token_urlsafe(6)[:8]

        # 저장
        preset.is_public = True
        preset.share_code = share_code
        preset.save(update_fields=['is_public', 'share_code', 'updated_at'])

    # 공유 URL 생성
    base_url = request.build_absolute_uri('/').rstrip('/')
    share_url = f"{base_url}/screener/presets/shared/{share_code}"

    logger.info(f"✅ 프리셋 공유: preset_id={preset_id}, share_code={share_code}")

    return Response({
        'success': True,
        'data': {
            'share_code': share_code,
            'share_url': share_url
        }
    })


@api_view(['GET'])
@authentication_classes([])
@permission_classes([AllowAny])
def get_shared_preset(request, share_code):
    """
    공유 코드로 프리셋 조회

    GET /api/v1/serverless/presets/shared/{share_code}

    Response:
        {
            "success": true,
            "data": {
                "id": 123,
                "name": "고배당 우량주",
                "description": "...",
                "filters_json": {...},
                "view_count": 150,
                "creator": "user@example.com"
            }
        }
    """
    from serverless.models import ScreenerPreset
    from serverless.serializers import ScreenerPresetSerializer

    try:
        preset = ScreenerPreset.objects.get(share_code=share_code, is_public=True)
    except ScreenerPreset.DoesNotExist:
        return Response({
            'success': False,
            'error': {'code': 'NOT_FOUND', 'message': f"Shared preset not found: {share_code}"}
        }, status=status.HTTP_404_NOT_FOUND)

    # 조회수 증가 (트랜잭션 없이 안전하게)
    ScreenerPreset.objects.filter(id=preset.id).update(
        view_count=models.F('view_count') + 1
    )
    preset.refresh_from_db()

    serializer = ScreenerPresetSerializer(preset, context={'request': request})

    return Response({
        'success': True,
        'data': serializer.data
    })


@api_view(['POST'])
@permission_classes([AllowAny])  # TODO: 프로덕션에서는 IsAuthenticated로 변경
def import_preset(request, share_code):
    """
    공유 프리셋을 내 프리셋으로 복사

    POST /api/v1/serverless/presets/import/{share_code}
    {
        "name": "복사된 프리셋 이름"  (optional, 기본값: "Copy of {원본 이름}")
    }

    Response:
        {
            "success": true,
            "data": {
                "id": 456,
                "message": "Preset imported successfully"
            }
        }
    """
    from serverless.models import ScreenerPreset

    if not request.user.is_authenticated:
        return Response({
            'success': False,
            'error': {'code': 'UNAUTHORIZED', 'message': 'Login required to import presets'}
        }, status=status.HTTP_401_UNAUTHORIZED)

    try:
        original_preset = ScreenerPreset.objects.get(share_code=share_code, is_public=True)
    except ScreenerPreset.DoesNotExist:
        return Response({
            'success': False,
            'error': {'code': 'NOT_FOUND', 'message': f"Shared preset not found: {share_code}"}
        }, status=status.HTTP_404_NOT_FOUND)

    # 복사본 이름 설정
    new_name = request.data.get('name')
    if not new_name:
        new_name = f"Copy of {original_preset.name}"

    # 프리셋 복사
    new_preset = ScreenerPreset.objects.create(
        user=request.user,
        name=new_name,
        description=original_preset.description,
        description_ko=original_preset.description_ko,
        category='custom',
        icon=original_preset.icon,
        filters_json=original_preset.filters_json,
        sort_by=original_preset.sort_by,
        sort_order=original_preset.sort_order,
        is_public=False,  # 복사본은 비공개
    )

    logger.info(f"✅ 프리셋 복사: user={request.user.email}, original={original_preset.id}, new={new_preset.id}")

    return Response({
        'success': True,
        'data': {
            'id': new_preset.id,
            'message': 'Preset imported successfully'
        }
    }, status=status.HTTP_201_CREATED)


@api_view(['GET'])
@authentication_classes([])
@permission_classes([AllowAny])
def trending_presets(request):
    """
    인기 프리셋 목록 (트렌딩)

    GET /api/v1/serverless/presets/trending?days=7

    Query Parameters:
        - days: 최근 N일 데이터 (기본값: 7, 최대: 30)

    Response:
        {
            "success": true,
            "data": {
                "count": 10,
                "presets": [
                    {
                        "id": 123,
                        "name": "고배당 우량주",
                        "view_count": 500,
                        "use_count": 200,
                        "share_code": "abc12345",
                        ...
                    }
                ]
            }
        }
    """
    from serverless.models import ScreenerPreset
    from serverless.serializers import ScreenerPresetListSerializer
    from datetime import timedelta

    days = int(request.GET.get('days', 7))
    days = min(days, 30)  # 최대 30일

    # 최근 N일 데이터 (last_used_at 기준)
    cutoff_date = timezone.now() - timedelta(days=days)

    # 인기 프리셋 (공개 + 사용/조회 많은 순)
    presets = ScreenerPreset.objects.filter(
        is_public=True,
        last_used_at__gte=cutoff_date
    ).order_by(
        '-view_count',
        '-use_count'
    )[:10]

    # last_used_at 필터 결과가 없으면 전체 공개 프리셋에서 TOP 10
    if not presets.exists():
        presets = ScreenerPreset.objects.filter(
            is_public=True
        ).order_by('-view_count', '-use_count')[:10]

    serializer = ScreenerPresetListSerializer(presets, many=True)

    return Response({
        'success': True,
        'data': {
            'count': len(serializer.data),
            'days': days,
            'presets': serializer.data
        }
    })
