"""
뉴스 API Views
"""

import logging
from datetime import timedelta

import pytz
from django.utils import timezone
from decimal import Decimal

from django.db.models import Count, Avg, Q, Sum, FloatField
from django.db.models.functions import TruncDate
from django.core.cache import cache
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import AllowAny, IsAuthenticated, IsAdminUser

from ..models import NewsArticle, NewsEntity, SentimentHistory, DailyNewsKeyword, NewsCollectionLog, MLModelHistory, AlertLog
from ..services import NewsAggregatorService
from .serializers import (
    NewsArticleListSerializer,
    NewsArticleDetailSerializer,
    SentimentHistorySerializer,
    SentimentSummarySerializer,
    TrendingStockSerializer
)

KST = pytz.timezone('Asia/Seoul')

logger = logging.getLogger(__name__)


def _kst_today_start():
    """KST 기준 오늘 자정을 UTC로 변환"""
    now = timezone.now()
    return now.astimezone(KST).replace(hour=0, minute=0, second=0, microsecond=0).astimezone(pytz.utc)


class NewsViewSet(viewsets.ReadOnlyModelViewSet):
    """뉴스 API ViewSet"""

    queryset = NewsArticle.objects.all().prefetch_related('entities')
    serializer_class = NewsArticleListSerializer

    def get_serializer_class(self):
        """액션별 Serializer 선택"""
        if self.action == 'retrieve':
            return NewsArticleDetailSerializer
        return NewsArticleListSerializer

    @action(detail=False, methods=['get'], url_path='stock/(?P<symbol>[^/.]+)')
    def stock_news(self, request, symbol=None):
        """
        종목별 뉴스 조회

        Query Parameters:
            - days: 조회 기간 (기본값: 7)
            - refresh: 데이터 새로고침 여부 (기본값: false)
        """
        symbol = symbol.upper()
        days = int(request.query_params.get('days', 7))
        refresh = request.query_params.get('refresh', 'false').lower() == 'true'

        # 캐시 키
        cache_key = f"news:stock:{symbol}:{days}"

        # 캐시 확인 (refresh=false일 때만)
        if not refresh:
            cached_data = cache.get(cache_key)
            if cached_data:
                logger.info(f"Cache hit: {cache_key}")
                return Response(cached_data)

        # refresh=true인 경우, 새로운 뉴스 수집
        if refresh:
            try:
                service = NewsAggregatorService()
                result = service.fetch_and_save_company_news(symbol, days=days)
                logger.info(f"News refresh result: {result}")
            except Exception as e:
                logger.error(f"Failed to refresh news: {e}")
                # 에러가 발생해도 기존 데이터는 반환

        # 데이터베이스에서 조회
        from_date = timezone.now() - timedelta(days=days)
        articles = NewsArticle.objects.filter(
            entities__symbol=symbol,
            published_at__gte=from_date
        ).distinct().order_by('-published_at')

        serializer = self.get_serializer(articles, many=True)
        data = {
            'symbol': symbol,
            'count': articles.count(),
            'articles': serializer.data
        }

        # 캐시 저장 (10분)
        cache.set(cache_key, data, 600)

        return Response(data)

    @action(detail=False, methods=['get'], url_path='stock/(?P<symbol>[^/.]+)/sentiment')
    def stock_sentiment(self, request, symbol=None):
        """
        종목별 감성 분석 요약

        Query Parameters:
            - days: 조회 기간 (기본값: 7)
        """
        symbol = symbol.upper()
        days = int(request.query_params.get('days', 7))

        # 캐시 키
        cache_key = f"news:sentiment:{symbol}:{days}"

        # 캐시 확인
        cached_data = cache.get(cache_key)
        if cached_data:
            logger.info(f"Cache hit: {cache_key}")
            return Response(cached_data)

        # 데이터베이스에서 집계
        from_date = timezone.now() - timedelta(days=days)

        entities = NewsEntity.objects.filter(
            symbol=symbol,
            news__published_at__gte=from_date
        ).select_related('news')

        if not entities.exists():
            # 뉴스가 없어도 빈 데이터 반환 (404 대신)
            empty_data = {
                'symbol': symbol,
                'period': f'{days}d',
                'avg_sentiment': None,
                'news_count': 0,
                'positive_count': 0,
                'negative_count': 0,
                'neutral_count': 0,
                'sentiment_trend': 'stable',
                'total_articles': 0,
                'positive_ratio': 0,
                'negative_ratio': 0,
                'neutral_ratio': 0,
                'history': []
            }
            return Response(empty_data)

        # 감성 점수 집계
        sentiment_scores = [
            e.sentiment_score for e in entities if e.sentiment_score is not None
        ]

        if not sentiment_scores:
            avg_sentiment = None
            positive_count = 0
            negative_count = 0
            neutral_count = 0
            sentiment_trend = 'stable'
        else:
            avg_sentiment = sum(sentiment_scores) / len(sentiment_scores)
            positive_count = len([s for s in sentiment_scores if s > 0.1])
            negative_count = len([s for s in sentiment_scores if s < -0.1])
            neutral_count = len(sentiment_scores) - positive_count - negative_count

            # 트렌드 계산 (최근 3일 vs 이전 기간)
            mid_date = timezone.now() - timedelta(days=3)
            recent_scores = [
                e.sentiment_score for e in entities
                if e.sentiment_score is not None and e.news.published_at >= mid_date
            ]
            older_scores = [
                e.sentiment_score for e in entities
                if e.sentiment_score is not None and e.news.published_at < mid_date
            ]

            if recent_scores and older_scores:
                recent_avg = sum(recent_scores) / len(recent_scores)
                older_avg = sum(older_scores) / len(older_scores)
                diff = recent_avg - older_avg

                if diff > 0.1:
                    sentiment_trend = 'improving'
                elif diff < -0.1:
                    sentiment_trend = 'declining'
                else:
                    sentiment_trend = 'stable'
            else:
                sentiment_trend = 'stable'

        total_count = len(sentiment_scores) if sentiment_scores else 0

        data = {
            'symbol': symbol,
            'period': f'{days}d',
            'avg_sentiment': round(avg_sentiment, 3) if avg_sentiment is not None else None,
            'news_count': entities.count(),
            'positive_count': positive_count,
            'negative_count': negative_count,
            'neutral_count': neutral_count,
            'sentiment_trend': sentiment_trend,
            # 프론트엔드 호환 필드
            'total_articles': total_count,
            'positive_ratio': positive_count / total_count if total_count > 0 else 0,
            'negative_ratio': negative_count / total_count if total_count > 0 else 0,
            'neutral_ratio': neutral_count / total_count if total_count > 0 else 0,
            'history': []  # TODO: 일별 히스토리 데이터 추가
        }

        # 캐시 저장 (30분)
        cache.set(cache_key, data, 1800)

        return Response(data)

    @action(detail=False, methods=['get'])
    def market(self, request):
        """
        시장 전체 뉴스 조회

        Query Parameters:
            - category: general, forex, crypto, merger (기본값: general)
            - limit: 결과 개수 (기본값: 20)
            - refresh: 데이터 새로고침 여부 (기본값: false)
        """
        category = request.query_params.get('category', 'general')
        limit = int(request.query_params.get('limit', 20))
        refresh = request.query_params.get('refresh', 'false').lower() == 'true'

        # 유효한 카테고리 검증
        valid_categories = ['general', 'forex', 'crypto', 'merger']
        if category not in valid_categories:
            raise ValidationError({
                'category': f'Invalid category. Choose from: {", ".join(valid_categories)}'
            })

        # Finnhub 카테고리 매핑 (Finnhub는 자체 카테고리명 사용)
        # general -> top news, general, business 등
        category_mapping = {
            'general': ['general', 'top news', 'business', 'company news'],
            'forex': ['forex'],
            'crypto': ['crypto'],
            'merger': ['merger'],
        }
        db_categories = category_mapping.get(category, [category])

        # 캐시 키
        cache_key = f"news:market:{category}:{limit}"

        # 캐시 확인 (refresh=false일 때만)
        if not refresh:
            cached_data = cache.get(cache_key)
            if cached_data:
                logger.info(f"Cache hit: {cache_key}")
                return Response(cached_data)

        # refresh=true인 경우, 새로운 뉴스 수집
        if refresh:
            try:
                service = NewsAggregatorService()
                result = service.fetch_and_save_market_news(category=category)
                logger.info(f"Market news refresh result: {result}")
            except Exception as e:
                logger.error(f"Failed to refresh market news: {e}")

        # 데이터베이스에서 조회 (최근 7일, 매핑된 카테고리로 필터)
        from_date = timezone.now() - timedelta(days=7)
        articles = NewsArticle.objects.filter(
            category__in=db_categories,
            published_at__gte=from_date
        ).order_by('-published_at')[:limit]

        serializer = self.get_serializer(articles, many=True)
        data = {
            'category': category,
            'count': len(serializer.data),
            'articles': serializer.data
        }

        # 캐시 저장 (10분)
        cache.set(cache_key, data, 600)

        return Response(data)

    @action(detail=False, methods=['get'])
    def trending(self, request):
        """
        트렌딩 종목 (뉴스가 많이 나온 종목)

        Query Parameters:
            - timeframe: 1h, 24h, 7d (기본값: 24h)
            - limit: 결과 개수 (기본값: 10)
        """
        timeframe = request.query_params.get('timeframe', '24h')
        limit = int(request.query_params.get('limit', 10))

        # 시간 범위 계산
        timeframe_map = {
            '1h': timedelta(hours=1),
            '24h': timedelta(days=1),
            '7d': timedelta(days=7)
        }

        if timeframe not in timeframe_map:
            raise ValidationError({'timeframe': 'Invalid timeframe. Choose from: 1h, 24h, 7d'})

        from_date = timezone.now() - timeframe_map[timeframe]

        # 캐시 키
        cache_key = f"news:trending:{timeframe}:{limit}"

        # 캐시 확인
        cached_data = cache.get(cache_key)
        if cached_data:
            logger.info(f"Cache hit: {cache_key}")
            return Response(cached_data)

        # 집계 쿼리
        trending_data = NewsEntity.objects.filter(
            news__published_at__gte=from_date
        ).values('symbol').annotate(
            news_count=Count('id'),
            avg_sentiment=Avg('sentiment_score')
        ).order_by('-news_count')[:limit]

        # 각 종목의 최근 뉴스 가져오기
        results = []
        for item in trending_data:
            symbol = item['symbol']
            recent_articles = NewsArticle.objects.filter(
                entities__symbol=symbol,
                published_at__gte=from_date
            ).distinct().order_by('-published_at')[:3]

            results.append({
                'symbol': symbol,
                'news_count': item['news_count'],
                'avg_sentiment': round(item['avg_sentiment'], 3) if item['avg_sentiment'] else 0.0,
                'recent_articles': NewsArticleListSerializer(recent_articles, many=True).data
            })

        # 캐시 저장 (5분)
        cache.set(cache_key, results, 300)

        return Response(results)

    @action(detail=False, methods=['get'], url_path='all')
    def all_news(self, request):
        """
        모든 뉴스 조회 (소스 필터 지원)

        GET /api/v1/news/all/?source=finnhub&category=general&days=7&limit=50&offset=0&refresh=false

        Query Parameters:
            - source: 뉴스 소스 필터 (finnhub, marketaux, all) 기본값: all
            - category: 카테고리 필터 (general, forex, crypto, merger) 기본값: all
            - days: 조회 기간 (기본값: 7)
            - limit: 결과 개수 (기본값: 50)
            - offset: 페이지 오프셋 (기본값: 0)
            - refresh: 새 뉴스 수집 여부 (기본값: false)
        """
        source = request.query_params.get('source', 'all').lower()
        category = request.query_params.get('category', 'all').lower()
        days = int(request.query_params.get('days', 7))
        limit = min(int(request.query_params.get('limit', 50)), 100)  # 최대 100개
        offset = int(request.query_params.get('offset', 0))
        refresh = request.query_params.get('refresh', 'false').lower() == 'true'

        # refresh=true인 경우, 새 뉴스 수집
        if refresh:
            try:
                service = NewsAggregatorService()
                # 카테고리별 뉴스 수집
                fetch_category = category if category != 'all' else 'general'
                result = service.fetch_and_save_market_news(category=fetch_category)
                logger.info(f"News refresh result: {result}")
            except Exception as e:
                logger.error(f"Failed to refresh news: {e}")

        # 캐시 키
        cache_key = f"news:all:{source}:{category}:{days}:{limit}:{offset}"

        # 캐시 확인 (refresh=true일 때는 캐시 무시)
        if not refresh:
            cached_data = cache.get(cache_key)
            if cached_data:
                logger.info(f"Cache hit: {cache_key}")
                return Response(cached_data)

        # 기본 쿼리
        from_date = timezone.now() - timedelta(days=days)
        queryset = NewsArticle.objects.filter(
            published_at__gte=from_date
        ).prefetch_related('entities')

        # 소스 필터
        if source != 'all':
            # finnhub_id가 있으면 finnhub 소스, marketaux_uuid가 있으면 marketaux 소스
            if source == 'finnhub':
                queryset = queryset.filter(finnhub_id__isnull=False)
            elif source == 'marketaux':
                queryset = queryset.filter(marketaux_uuid__isnull=False)

        # 카테고리 필터
        if category != 'all':
            category_mapping = {
                'general': ['general', 'top news', 'business', 'company news'],
                'forex': ['forex'],
                'crypto': ['crypto'],
                'merger': ['merger'],
            }
            db_categories = category_mapping.get(category, [category])
            queryset = queryset.filter(category__in=db_categories)

        # 정렬 및 페이지네이션
        total_count = queryset.count()
        articles = queryset.order_by('-published_at')[offset:offset + limit]

        serializer = self.get_serializer(articles, many=True)
        data = {
            'source': source,
            'category': category,
            'days': days,
            'total': total_count,
            'count': len(serializer.data),
            'offset': offset,
            'limit': limit,
            'has_more': (offset + limit) < total_count,
            'articles': serializer.data
        }

        # 캐시 저장 (10분)
        cache.set(cache_key, data, 600)

        return Response(data)

    @action(detail=False, methods=['get'])
    def sources(self, request):
        """
        사용 가능한 뉴스 소스 목록 + 건수

        GET /api/v1/news/sources/

        Returns:
            [
                {"name": "finnhub", "label": "Finnhub", "count": 150},
                {"name": "marketaux", "label": "Marketaux", "count": 50}
            ]
        """
        # 캐시 키
        cache_key = "news:sources"

        # 캐시 확인
        cached_data = cache.get(cache_key)
        if cached_data:
            logger.info(f"Cache hit: {cache_key}")
            return Response(cached_data)

        # 최근 7일 기준 소스별 건수 집계
        from_date = timezone.now() - timedelta(days=7)

        # Finnhub 뉴스 건수 (finnhub_id가 있는 기사)
        finnhub_count = NewsArticle.objects.filter(
            published_at__gte=from_date,
            finnhub_id__isnull=False
        ).count()

        # Marketaux 뉴스 건수 (marketaux_uuid가 있는 기사)
        marketaux_count = NewsArticle.objects.filter(
            published_at__gte=from_date,
            marketaux_uuid__isnull=False
        ).count()

        # 전체 뉴스 건수
        total_count = NewsArticle.objects.filter(
            published_at__gte=from_date
        ).count()

        sources = [
            {
                'name': 'all',
                'label': '전체',
                'count': total_count
            },
            {
                'name': 'finnhub',
                'label': 'Finnhub',
                'count': finnhub_count
            },
            {
                'name': 'marketaux',
                'label': 'Marketaux',
                'count': marketaux_count
            }
        ]

        # 캐시 저장 (1시간)
        cache.set(cache_key, sources, 3600)

        return Response(sources)

    # ===== Phase 2: Daily Keywords API =====

    @action(detail=False, methods=['get'], url_path='daily-keywords')
    def daily_keywords(self, request):
        """
        일별 뉴스 키워드 조회

        GET /api/v1/news/daily-keywords/?date=2026-02-06

        Query Parameters:
            - date: 조회 날짜 (YYYY-MM-DD 형식, 기본값: 오늘)

        Returns:
            {
                "date": "2026-02-06",
                "keywords": [...],
                "total_news_count": 50,
                "sources": {"finnhub": 45, "marketaux": 5},
                "llm_model": "gemini-2.5-flash",
                "status": "completed"
            }
        """
        from datetime import datetime

        # 날짜 파라미터 파싱
        date_str = request.query_params.get('date')
        if date_str:
            try:
                target_date = datetime.strptime(date_str, '%Y-%m-%d').date()
            except ValueError:
                raise ValidationError({'date': 'Invalid date format. Use YYYY-MM-DD'})
        else:
            target_date = timezone.now().date()

        # 캐시 키
        cache_key = f"news:daily_keywords:{target_date}"

        # 캐시 확인
        cached_data = cache.get(cache_key)
        if cached_data:
            logger.info(f"Cache hit: {cache_key}")
            return Response(cached_data)

        # DailyNewsKeyword 조회
        keyword_obj = DailyNewsKeyword.objects.filter(date=target_date).first()

        if not keyword_obj:
            # 키워드가 없으면 빈 응답 (pending 상태로)
            data = {
                'date': str(target_date),
                'keywords': [],
                'total_news_count': 0,
                'sources': {},
                'llm_model': None,
                'status': 'not_found',
                'message': 'Keywords not yet generated for this date'
            }
            return Response(data)

        # 응답 데이터 구성
        data = {
            'date': str(keyword_obj.date),
            'keywords': keyword_obj.keywords,
            'total_news_count': keyword_obj.total_news_count,
            'sources': keyword_obj.sources,
            'llm_model': keyword_obj.llm_model,
            'status': keyword_obj.status,
            'generation_time_ms': keyword_obj.generation_time_ms,
        }

        # 완료 상태일 때만 캐시 (24시간)
        if keyword_obj.status == 'completed':
            cache.set(cache_key, data, 86400)

        return Response(data)

    @action(detail=False, methods=['post'], url_path='daily-keywords/generate')
    def generate_daily_keywords(self, request):
        """
        일별 뉴스 키워드 수동 생성 트리거

        POST /api/v1/news/daily-keywords/generate
        Body: {"date": "2026-02-06", "force": false}

        Returns:
            {"status": "started", "task_id": "..."}
        """
        from datetime import datetime
        from news.tasks import extract_daily_news_keywords

        # 요청 파라미터
        date_str = request.data.get('date')
        force = request.data.get('force', False)

        # 날짜 검증
        if date_str:
            try:
                datetime.strptime(date_str, '%Y-%m-%d')
            except ValueError:
                raise ValidationError({'date': 'Invalid date format. Use YYYY-MM-DD'})

        # Celery 태스크 시작
        task = extract_daily_news_keywords.delay(
            target_date=date_str,
            force=force
        )

        return Response({
            'status': 'started',
            'task_id': task.id,
            'date': date_str or str(timezone.now().date()),
        })

    # ===== Phase 3: Stock Insights API (Fact-Based) =====

    @action(detail=False, methods=['get'])
    def insights(self, request):
        """
        뉴스 기반 종목 인사이트 (팩트 중심)

        GET /api/v1/news/insights/?date=2026-02-06&limit=10

        Query Parameters:
            - date: 조회 날짜 (YYYY-MM-DD 형식, 기본값: 오늘)
            - limit: 종목 수 (기본값: 10, 최대: 20)
            - include_market_data: 시장 데이터 포함 여부 (기본값: true)

        Returns:
            {
                "date": "2026-02-06",
                "insights": [
                    {
                        "symbol": "NVDA",
                        "company_name": "NVIDIA Corp",
                        "keyword_mentions": [
                            {
                                "keyword": "AI 반도체 수요",
                                "sentiment": "positive",
                                "news_headline": "NVIDIA's AI chip...",
                                "news_source": "Marketaux",
                                "published_at": "2026-02-06T10:30:00Z"
                            }
                        ],
                        "sentiment_distribution": {
                            "positive": 3,
                            "negative": 1,
                            "neutral": 1,
                            "total": 5
                        },
                        "market_data": {...},
                        "total_news_count": 5
                    }
                ],
                "total_keywords": 10,
                "computation_time_ms": 50
            }
        """
        from datetime import datetime
        from news.services import NewsBasedStockInsights

        # 날짜 파라미터 파싱
        date_str = request.query_params.get('date')
        if date_str:
            try:
                target_date = datetime.strptime(date_str, '%Y-%m-%d').date()
            except ValueError:
                raise ValidationError({'date': 'Invalid date format. Use YYYY-MM-DD'})
        else:
            target_date = timezone.now().date()

        # limit 파라미터
        try:
            limit = min(int(request.query_params.get('limit', 10)), 20)
        except ValueError:
            limit = 10

        # include_market_data 파라미터
        include_market_data = request.query_params.get(
            'include_market_data', 'true'
        ).lower() == 'true'

        # 캐시 키
        cache_key = f"news:insights:{target_date}:{limit}:{include_market_data}"

        # 캐시 확인
        cached_data = cache.get(cache_key)
        if cached_data:
            logger.info(f"Cache hit: {cache_key}")
            return Response(cached_data)

        # 인사이트 서비스 호출
        insights_service = NewsBasedStockInsights()
        result = insights_service.get_insights(
            target_date=target_date,
            limit=limit,
            include_market_data=include_market_data
        )

        # 캐시 저장 (1시간)
        cache.set(cache_key, result, 3600)

        return Response(result)

    # ===== Phase 4: Cold Start + Personalized Feed =====

    @action(detail=False, methods=['get'], url_path='market-feed', permission_classes=[AllowAny])
    def market_feed(self, request):
        """
        AI 뉴스 브리핑 + 시장 컨텍스트. AllowAny (콜드 스타트용).

        GET /api/v1/news/market-feed/

        Returns:
            {
                "date": "2026-02-24",
                "is_fallback": false,
                "fallback_message": null,
                "briefing": {
                    "keywords": [
                        {
                            "text": "AI 반도체 수요",
                            "sentiment": "positive",
                            "related_symbols": ["NVDA", "AMD"],
                            "importance": 0.95,
                            "reason": "NVDA 실적 발표 임박, 공급망 전체 주목",
                            "news_count": 5,
                            "headlines": [{"title": "...", "url": "..."}]
                        }
                    ],
                    "total_news_count": 100,
                    "llm_model": "gemini-2.5-flash"
                },
                "market_context": {
                    "top_sectors": [...],
                    "hot_movers": [...]
                }
            }
        """
        from news.services.market_feed import MarketFeedService
        service = MarketFeedService()
        data = service.get_feed()
        return Response(data)

    @action(detail=False, methods=['get'], url_path='interest-options', permission_classes=[AllowAny])
    def interest_options(self, request):
        """
        관심사 선택 옵션 (테마 + 섹터). AllowAny (온보딩용).

        GET /api/v1/news/interest-options/

        Returns:
            {
                "themes": [
                    {
                        "interest_type": "theme",
                        "value": "ai_semiconductor",
                        "display_name": "AI & 반도체",
                        "sample_symbols": ["NVDA", "AMD", "INTC"]
                    }
                ],
                "sectors": [
                    {
                        "interest_type": "sector",
                        "value": "Technology",
                        "display_name": "Technology",
                        "sample_symbols": ["AAPL", "MSFT", "NVDA"]
                    }
                ]
            }
        """
        from news.services.interest_options import InterestOptionsService
        service = InterestOptionsService()
        data = service.get_options()
        return Response(data)

    @action(detail=False, methods=['get'], url_path='personalized-feed', permission_classes=[IsAuthenticated])
    def personalized_feed(self, request):
        """
        사용자 맞춤 뉴스 피드 (포트폴리오 > Watchlist > 관심사 > 시장 피드 순서).

        GET /api/v1/news/personalized-feed/

        Returns:
            {
                "source_type": "portfolio|watchlist|interests|market_feed",
                "personalized": true,
                "articles": [...],
                "symbols_used": {
                    "portfolio": ["AAPL", "NVDA"],
                    "watchlist": ["TSLA"]
                }
            }
        """
        from news.services.personalized_feed import PersonalizedFeedService
        service = PersonalizedFeedService()
        data = service.get_feed(request.user)
        return Response(data)

    # ===== Phase 3: News Events (Neo4j) API =====

    @action(detail=False, methods=['get'], url_path='news-events')
    def news_events(self, request):
        """
        뉴스 이벤트 조회 (Neo4j 기반)

        GET /api/v1/news/news-events/?symbol=NVDA&days=7

        Query Parameters:
            - symbol: 종목 심볼 (필수)
            - days: 조회 기간 (기본값: 7, 최대: 30)

        Returns:
            {
                "symbol": "NVDA",
                "days": 7,
                "events": [...],
                "summary": {
                    "total_events": 5,
                    "bullish_count": 3,
                    "bearish_count": 1,
                    "avg_confidence": 0.75,
                    "direct_count": 3,
                    "indirect_count": 2,
                    "opportunity_count": 1
                }
            }
        """
        symbol = request.query_params.get('symbol')
        if not symbol:
            raise ValidationError({'symbol': 'symbol parameter is required'})

        symbol = symbol.upper()
        days = min(int(request.query_params.get('days', 7)), 30)

        cache_key = f"news:events:{symbol}:{days}"
        cached_data = cache.get(cache_key)
        if cached_data:
            return Response(cached_data)

        from news.services import NewsNeo4jSyncService
        sync_service = NewsNeo4jSyncService()

        events = sync_service.get_news_events_for_symbol(
            symbol=symbol, days=days, limit=20,
        )
        summary = sync_service.get_symbol_impact_summary(
            symbol=symbol, days=days,
        )

        data = {
            'symbol': symbol,
            'days': days,
            'events': events,
            'summary': summary,
        }

        cache.set(cache_key, data, 300)  # 5분 캐시
        return Response(data)

    @action(detail=False, methods=['get'], url_path='news-events/impact-map')
    def news_events_impact_map(self, request):
        """
        뉴스 영향도 맵 (시각화용)

        GET /api/v1/news/news-events/impact-map/?days=7

        Query Parameters:
            - days: 조회 기간 (기본값: 7, 최대: 30)

        Returns:
            {
                "nodes": [
                    {"id": "article-uuid", "label": "Fed raises...", "type": "NewsEvent", ...},
                    {"id": "NVDA", "label": "NVIDIA", "type": "Stock"},
                    {"id": "Technology", "label": "Technology", "type": "Sector"}
                ],
                "edges": [
                    {"source": "article-uuid", "target": "NVDA", "type": "DIRECTLY_IMPACTS", ...}
                ],
                "stats": {
                    "total_events": 10,
                    "total_stocks": 15,
                    "total_sectors": 5,
                    "total_relationships": 25
                }
            }
        """
        days = min(int(request.query_params.get('days', 7)), 30)

        cache_key = f"news:impact_map:{days}"
        cached_data = cache.get(cache_key)
        if cached_data:
            return Response(cached_data)

        from news.services import NewsNeo4jSyncService
        sync_service = NewsNeo4jSyncService()
        data = sync_service.get_impact_map(days=days, limit=50)

        cache.set(cache_key, data, 300)  # 5분 캐시
        return Response(data)

    # ===== Phase 4: ML Model Status + Shadow Report API =====

    @action(detail=False, methods=['get'], url_path='ml-status')
    def ml_status(self, request):
        """
        ML 모델 현재 상태 조회

        GET /api/v1/news/ml-status/

        Returns:
            {
                "latest_model": {"version": "lr_v1_20260225_1", "f1_score": 0.72, ...},
                "deployed_model": {"version": ..., "weights": {...}, ...},
                "recent_history": [...],
                "labeled_data_count": 3500,
                "min_required": 200,
                "ready_for_training": true
            }
        """
        cache_key = "news:ml_status"
        cached_data = cache.get(cache_key)
        if cached_data:
            return Response(cached_data)

        from news.services.ml_weight_optimizer import MLWeightOptimizer
        data = MLWeightOptimizer.get_current_status()

        cache.set(cache_key, data, 300)  # 5분 캐시
        return Response(data)

    @action(detail=False, methods=['get'], url_path='ml-shadow-report')
    def ml_shadow_report(self, request):
        """
        Shadow Mode 비교 리포트 조회

        GET /api/v1/news/ml-shadow-report/

        Returns:
            {
                "model_version": "lr_v1_20260225_1",
                "shadow_comparison": {
                    "period": "Last 7 days",
                    "total_articles": 500,
                    "manual_selected": 75,
                    "ml_selected": 75,
                    "overlap": 60,
                    "agreement_rate": 0.80
                },
                "metrics": {"f1": 0.72, "precision": 0.68, ...},
                "weights": {"source_credibility": 0.15, ...}
            }
        """
        from ..models import MLModelHistory

        latest = MLModelHistory.objects.filter(
            deployment_status__in=['shadow', 'deployed'],
            shadow_comparison__isnull=False,
        ).order_by('-trained_at').first()

        if not latest:
            return Response({
                'status': 'no_report',
                'message': 'No shadow comparison report available',
            })

        data = {
            'model_version': latest.model_version,
            'deployment_status': latest.deployment_status,
            'shadow_comparison': latest.shadow_comparison,
            'metrics': {
                'f1': latest.f1_score,
                'precision': latest.precision,
                'recall': latest.recall,
                'accuracy': latest.accuracy,
            },
            'weights': latest.smoothed_weights,
            'safety_gate': latest.safety_gate_details,
            'trained_at': str(latest.trained_at),
        }
        return Response(data)

    # ===== Phase 5: ML Production + Weekly Report API =====

    @action(detail=False, methods=['get'], url_path='ml-weekly-report')
    def ml_weekly_report(self, request):
        """
        주간 ML 성능 리포트 조회

        GET /api/v1/news/ml-weekly-report/

        Returns:
            {
                "period": {"start": "2026-02-18", "end": "2026-02-25"},
                "model_status": {...},
                "performance_trend": {...},
                "llm_accuracy": {...},
                "data_stats": {...},
                "recommendations": [...]
            }
        """
        cache_key = "news:ml_weekly_report"
        cached_data = cache.get(cache_key)
        if cached_data:
            return Response(cached_data)

        from news.services.ml_production_manager import MLProductionManager
        manager = MLProductionManager()
        data = manager.generate_weekly_report()

        cache.set(cache_key, data, 3600)  # 1시간 캐시
        return Response(data)

    @action(detail=False, methods=['get'], url_path='ml-lightgbm-readiness')
    def ml_lightgbm_readiness(self, request):
        """
        LightGBM 전환 준비 상태 조회

        GET /api/v1/news/ml-lightgbm-readiness/

        Returns:
            {
                "ready": false,
                "conditions": {
                    "data_sufficient": {"met": false, "current": 5000, "required": 10000},
                    "lr_stagnation": {"met": true, "weeks_checked": 3, "f1_range": 0.005},
                    "feature_stability": {"met": true, "sector_coverage": 0.65}
                }
            }
        """
        from news.services.ml_weight_optimizer import MLWeightOptimizer
        data = MLWeightOptimizer.check_lightgbm_readiness()
        return Response(data)

    # ===== Legacy: Stock Recommendations API (Deprecated) =====

    @action(detail=False, methods=['get'])
    def recommendations(self, request):
        """
        뉴스 기반 주식 추천

        GET /api/v1/news/recommendations/?date=2026-02-06&limit=10

        Query Parameters:
            - date: 조회 날짜 (YYYY-MM-DD 형식, 기본값: 오늘)
            - limit: 추천 수 (기본값: 10, 최대: 20)

        Returns:
            {
                "date": "2026-02-06",
                "recommendations": [
                    {
                        "symbol": "NVDA",
                        "company_name": "NVIDIA Corp",
                        "score": 0.95,
                        "reasons": ["AI 반도체 수요", "실적 호조"],
                        "avg_sentiment": 0.45,
                        "mention_count": 15
                    }
                ],
                "total_keywords": 10,
                "computation_time_ms": 50
            }
        """
        from datetime import datetime
        from news.services import NewsBasedStockRecommender

        # 날짜 파라미터 파싱
        date_str = request.query_params.get('date')
        if date_str:
            try:
                target_date = datetime.strptime(date_str, '%Y-%m-%d').date()
            except ValueError:
                raise ValidationError({'date': 'Invalid date format. Use YYYY-MM-DD'})
        else:
            target_date = timezone.now().date()

        # limit 파라미터
        try:
            limit = min(int(request.query_params.get('limit', 10)), 20)
        except ValueError:
            limit = 10

        # 캐시 키
        cache_key = f"news:recommendations:{target_date}:{limit}"

        # 캐시 확인
        cached_data = cache.get(cache_key)
        if cached_data:
            logger.info(f"Cache hit: {cache_key}")
            return Response(cached_data)

        # 추천 서비스 호출
        recommender = NewsBasedStockRecommender()
        result = recommender.get_recommendations(
            target_date=target_date,
            limit=limit
        )

        # 캐시 저장 (1시간)
        cache.set(cache_key, result, 3600)

        return Response(result)

    # ===== Phase A: Pipeline Monitoring API =====

    @action(detail=False, methods=['get'], url_path='collection-logs', permission_classes=[IsAdminUser])
    def collection_logs(self, request):
        """
        뉴스 수집 로그 집계

        GET /api/v1/news/collection-logs/?days=7&provider=fmp&task_name=collect_sp500_news_fmp_batch

        Query Parameters:
            - days: 조회 기간 (기본값: 7, 최대: 30)
            - provider: 프로바이더 필터 (선택)
            - task_name: 태스크 이름 필터 (선택)

        Returns:
            {period_days, total_records, logs, aggregated: {by_provider, daily_summary}}
        """
        try:
            days = min(int(request.query_params.get('days', 7)), 30)
        except (ValueError, TypeError):
            days = 7
        provider_filter = request.query_params.get('provider')
        task_name_filter = request.query_params.get('task_name')

        cache_key = f"news:collection_logs:{days}:{provider_filter}:{task_name_filter}"
        cached_data = cache.get(cache_key)
        if cached_data:
            logger.info(f"Cache hit: {cache_key}")
            return Response(cached_data)

        # KST 자정 기준 cutoff 계산
        now_kst = timezone.now().astimezone(KST)
        kst_midnight = now_kst.replace(hour=0, minute=0, second=0, microsecond=0)
        cutoff = kst_midnight - timedelta(days=days - 1)

        qs = NewsCollectionLog.objects.filter(executed_at__gte=cutoff)
        if provider_filter:
            qs = qs.filter(provider=provider_filter)
        if task_name_filter:
            qs = qs.filter(task_name=task_name_filter)

        qs = qs.order_by('-executed_at')

        # 로그 목록
        logs = list(qs.values(
            'id', 'task_name', 'provider', 'executed_at',
            'symbols_tried', 'articles_new', 'articles_dup',
            'api_calls', 'errors', 'duration_sec',
        ))

        # provider별 집계
        provider_agg = qs.values('provider').annotate(
            total_runs=Count('id'),
            total_new=Sum('articles_new'),
            total_dup=Sum('articles_dup'),
            total_errors=Sum('errors'),
            avg_duration_sec=Avg('duration_sec'),
        )
        by_provider = {}
        for row in provider_agg:
            total_runs = row['total_runs'] or 0
            total_errors = row['total_errors'] or 0
            error_runs = qs.filter(provider=row['provider'], errors__gt=0).count()
            success_rate = round(1.0 - (error_runs / total_runs), 3) if total_runs > 0 else 1.0
            by_provider[row['provider']] = {
                'total_runs': total_runs,
                'total_new': row['total_new'] or 0,
                'total_dup': row['total_dup'] or 0,
                'total_errors': total_errors,
                'avg_duration_sec': round(row['avg_duration_sec'] or 0, 1),
                'success_rate': success_rate,
            }

        # 일별 집계 (KST 기준 TruncDate)
        daily_agg = (
            qs.annotate(date=TruncDate('executed_at', tzinfo=KST))
            .values('date')
            .annotate(
                total_new=Sum('articles_new'),
                total_dup=Sum('articles_dup'),
                total_errors=Sum('errors'),
                runs=Count('id'),
            )
            .order_by('-date')
        )
        daily_summary = [
            {
                'date': str(row['date']),
                'total_new': row['total_new'] or 0,
                'total_dup': row['total_dup'] or 0,
                'total_errors': row['total_errors'] or 0,
                'runs': row['runs'],
            }
            for row in daily_agg
        ]

        data = {
            'period_days': days,
            'total_records': len(logs),
            'logs': logs,
            'aggregated': {
                'by_provider': by_provider,
                'daily_summary': daily_summary,
            },
        }

        # 30일 요청은 캐시 30분, 그 외 5분
        cache_ttl = 1800 if days >= 30 else 300
        cache.set(cache_key, data, cache_ttl)

        return Response(data)

    @action(detail=False, methods=['get'], url_path='pipeline-health', permission_classes=[IsAdminUser])
    def pipeline_health(self, request):
        """
        파이프라인 6 Phase 통합 상태

        GET /api/v1/news/pipeline-health/?force_refresh=true

        Query Parameters:
            - force_refresh: true이면 캐시 우회

        Returns:
            {generated_at, is_weekend_kst, phases, ml_summary, llm_summary}
        """
        force_refresh = request.query_params.get('force_refresh', 'false').lower() == 'true'
        cache_key = "news:pipeline_health"

        if not force_refresh:
            cached_data = cache.get(cache_key)
            if cached_data:
                logger.info(f"Cache hit: {cache_key}")
                return Response(cached_data)

        PHASE_CONFIG = {
            1: {'expected_interval_hours': 12, 'weekday_only': False, 'name': '뉴스 수집'},
            2: {'expected_interval_hours': 3, 'weekday_only': True, 'name': '뉴스 분류 (Engine A/B/C)'},
            3: {'expected_interval_hours': 3, 'weekday_only': True, 'name': 'LLM 심층 분석'},
            4: {'expected_interval_hours': 26, 'weekday_only': False, 'name': 'ML Label + Neo4j 동기화'},
            5: {'expected_interval_hours': 192, 'weekday_only': False, 'name': 'ML 학습 + Shadow Mode'},
            6: {'expected_interval_hours': 192, 'weekday_only': False, 'name': 'LightGBM + 주간 리포트'},
        }

        now = timezone.now()
        is_weekend = now.astimezone(KST).weekday() >= 5

        def _determine_status(config, last_run, error_rate):
            if last_run is None:
                return 'stale'
            hours_since = (now - last_run).total_seconds() / 3600
            if config['weekday_only'] and is_weekend:
                if hours_since <= 62:
                    return 'ok' if error_rate < 0.1 else 'warning'
                return 'stale'
            if hours_since > config['expected_interval_hours']:
                return 'stale'
            if error_rate > 0.3:
                return 'error'
            if error_rate > 0.1:
                return 'warning'
            return 'ok'

        phases = []

        # Phase 1: 뉴스 수집 — NewsCollectionLog
        phase1_config = PHASE_CONFIG[1]
        phase1_logs = NewsCollectionLog.objects.filter(
            task_name__in=['collect_daily_news', 'collect_market_news', 'collect_category_news',
                           'collect_sp500_news_fmp_batch', 'collect_press_releases_fmp',
                           'collect_general_news_fmp', 'collect_av_single_symbol']
        ).order_by('-executed_at')
        phase1_recent = phase1_logs.first()
        phase1_last_run = phase1_recent.executed_at if phase1_recent else None
        phase1_window = now - timedelta(hours=24)
        phase1_stats = phase1_logs.filter(executed_at__gte=phase1_window).aggregate(
            total_new=Sum('articles_new'),
            total_errors=Sum('errors'),
            total_runs=Count('id'),
        )
        phase1_total_runs = phase1_stats['total_runs'] or 0
        phase1_errors = phase1_stats['total_errors'] or 0
        phase1_error_rate = phase1_errors / phase1_total_runs if phase1_total_runs > 0 else 0
        phase1_providers = list(
            phase1_logs.filter(executed_at__gte=phase1_window)
            .values_list('provider', flat=True)
            .distinct()
        )
        phases.append({
            'phase': 1,
            'name': phase1_config['name'],
            'expected_interval_hours': phase1_config['expected_interval_hours'],
            'weekday_only': phase1_config['weekday_only'],
            'last_run': phase1_last_run.isoformat() if phase1_last_run else None,
            'hours_since_last_run': round((now - phase1_last_run).total_seconds() / 3600, 2) if phase1_last_run else None,
            'status': _determine_status(phase1_config, phase1_last_run, phase1_error_rate),
            'recent_errors': phase1_errors,
            'recent_new': phase1_stats['total_new'] or 0,
            'providers_active': phase1_providers,
        })

        # Phase 2: 뉴스 분류
        phase2_config = PHASE_CONFIG[2]
        phase2_log = NewsCollectionLog.objects.filter(task_name='classify_news_batch').order_by('-executed_at').first()
        phase2_last_run = phase2_log.executed_at if phase2_log else None
        today_start = _kst_today_start()
        classified_today = NewsArticle.objects.filter(
            importance_score__isnull=False,
            updated_at__gte=today_start,
        ).count()
        phase2_window_logs = NewsCollectionLog.objects.filter(
            task_name='classify_news_batch',
            executed_at__gte=now - timedelta(hours=24),
        ).aggregate(total_errors=Sum('errors'), total_runs=Count('id'))
        phase2_runs = phase2_window_logs['total_runs'] or 0
        phase2_errors = phase2_window_logs['total_errors'] or 0
        phase2_error_rate = phase2_errors / phase2_runs if phase2_runs > 0 else 0
        phases.append({
            'phase': 2,
            'name': phase2_config['name'],
            'expected_interval_hours': phase2_config['expected_interval_hours'],
            'weekday_only': phase2_config['weekday_only'],
            'last_run': phase2_last_run.isoformat() if phase2_last_run else None,
            'hours_since_last_run': round((now - phase2_last_run).total_seconds() / 3600, 2) if phase2_last_run else None,
            'status': _determine_status(phase2_config, phase2_last_run, phase2_error_rate),
            'classified_today': classified_today,
            'errors_today': phase2_errors,
        })

        # Phase 3: LLM 심층 분석
        phase3_config = PHASE_CONFIG[3]
        phase3_log = NewsCollectionLog.objects.filter(task_name='analyze_news_deep').order_by('-executed_at').first()
        phase3_last_run = phase3_log.executed_at if phase3_log else None
        analyzed_today = NewsArticle.objects.filter(
            llm_analyzed=True,
            updated_at__gte=today_start,
        ).count()
        pending_llm = NewsArticle.objects.filter(
            importance_score__isnull=False,
            llm_analyzed=False,
        ).count()
        phase3_window_logs = NewsCollectionLog.objects.filter(
            task_name='analyze_news_deep',
            executed_at__gte=now - timedelta(hours=24),
        ).aggregate(total_errors=Sum('errors'), total_runs=Count('id'))
        phase3_runs = phase3_window_logs['total_runs'] or 0
        phase3_errors = phase3_window_logs['total_errors'] or 0
        phase3_error_rate = phase3_errors / phase3_runs if phase3_runs > 0 else 0
        phases.append({
            'phase': 3,
            'name': phase3_config['name'],
            'expected_interval_hours': phase3_config['expected_interval_hours'],
            'weekday_only': phase3_config['weekday_only'],
            'last_run': phase3_last_run.isoformat() if phase3_last_run else None,
            'hours_since_last_run': round((now - phase3_last_run).total_seconds() / 3600, 2) if phase3_last_run else None,
            'status': _determine_status(phase3_config, phase3_last_run, phase3_error_rate),
            'analyzed_today': analyzed_today,
            'errors_today': phase3_errors,
            'pending': pending_llm,
        })

        # Phase 4: ML Label + Neo4j
        phase4_config = PHASE_CONFIG[4]
        label_log = NewsCollectionLog.objects.filter(task_name='collect_ml_labels').order_by('-executed_at').first()
        neo4j_log = NewsCollectionLog.objects.filter(task_name='sync_news_to_neo4j').order_by('-executed_at').first()
        phase4_last_run = label_log.executed_at if label_log else None
        labeled_total = NewsArticle.objects.filter(ml_label_important__isnull=False).count()
        # Neo4j 가용성: 최근 neo4j 로그에서 errors=0이면 가용
        neo4j_available = False
        if neo4j_log:
            neo4j_available = (neo4j_log.errors == 0)
        phase4_window_logs = NewsCollectionLog.objects.filter(
            task_name__in=['collect_ml_labels', 'sync_news_to_neo4j'],
            executed_at__gte=now - timedelta(hours=26),
        ).aggregate(total_errors=Sum('errors'), total_runs=Count('id'))
        phase4_runs = phase4_window_logs['total_runs'] or 0
        phase4_errors = phase4_window_logs['total_errors'] or 0
        phase4_error_rate = phase4_errors / phase4_runs if phase4_runs > 0 else 0
        neo4j_last_run = neo4j_log.executed_at if neo4j_log else None
        phase4_neo4j_last_run = neo4j_last_run.isoformat() if neo4j_last_run else None
        phases.append({
            'phase': 4,
            'name': phase4_config['name'],
            'expected_interval_hours': phase4_config['expected_interval_hours'],
            'weekday_only': phase4_config['weekday_only'],
            'last_run': phase4_neo4j_last_run,  # PipelineStatusBar 호환
            'last_label_run': phase4_last_run.isoformat() if phase4_last_run else None,
            'last_neo4j_run': phase4_neo4j_last_run,
            'hours_since_last_run': round((now - phase4_last_run).total_seconds() / 3600, 2) if phase4_last_run else None,
            'status': _determine_status(phase4_config, phase4_last_run, phase4_error_rate),
            'labeled_total': labeled_total,
            'neo4j_available': neo4j_available,
        })

        # Phase 5: ML 학습 + Shadow Mode
        phase5_config = PHASE_CONFIG[5]
        deployed_model = MLModelHistory.objects.filter(
            deployment_status='deployed'
        ).order_by('-trained_at').first()
        latest_model = MLModelHistory.objects.order_by('-trained_at').first()
        phase5_last_run = latest_model.trained_at if latest_model else None
        phase5_error_rate = 0.0  # ML 학습 로그는 별도 태스크 로그 없음
        phases.append({
            'phase': 5,
            'name': phase5_config['name'],
            'expected_interval_hours': phase5_config['expected_interval_hours'],
            'weekday_only': phase5_config['weekday_only'],
            'last_run': phase5_last_run.isoformat() if phase5_last_run else None,
            'hours_since_last_run': round((now - phase5_last_run).total_seconds() / 3600, 2) if phase5_last_run else None,
            'status': _determine_status(phase5_config, phase5_last_run, phase5_error_rate),
            'deployed_version': deployed_model.model_version if deployed_model else None,
            'deployed_f1': deployed_model.f1_score if deployed_model else None,
            'deployment_status': deployed_model.deployment_status if deployed_model else None,
        })

        # Phase 6: LightGBM + 주간 리포트
        phase6_config = PHASE_CONFIG[6]
        lgbm_model = MLModelHistory.objects.filter(
            algorithm='lightgbm'
        ).order_by('-trained_at').first()
        phase6_last_run = lgbm_model.trained_at if lgbm_model else None
        phases.append({
            'phase': 6,
            'name': phase6_config['name'],
            'expected_interval_hours': phase6_config['expected_interval_hours'],
            'weekday_only': phase6_config['weekday_only'],
            'last_run': phase6_last_run.isoformat() if phase6_last_run else None,
            'hours_since_last_run': round((now - phase6_last_run).total_seconds() / 3600, 2) if phase6_last_run else None,
            'status': _determine_status(phase6_config, phase6_last_run, 0.0),
            'lightgbm_ready': lgbm_model is not None,
        })

        # ml_summary (labeled_total은 Phase 4 블록에서 이미 계산됨)
        ml_summary = {
            'deployed_version': deployed_model.model_version if deployed_model else None,
            'deployed_f1': deployed_model.f1_score if deployed_model else None,
            'deployment_status': deployed_model.deployment_status if deployed_model else None,
            'labeled_data_count': labeled_total,
            'ready_for_training': labeled_total >= 200,
        }

        # llm_summary
        llm_total_today = NewsArticle.objects.filter(
            llm_analyzed=True,
            updated_at__gte=today_start,
        ).count()
        kw_today = DailyNewsKeyword.objects.filter(date=now.astimezone(KST).date()).first()
        prompt_tokens_today = kw_today.prompt_tokens or 0 if kw_today else 0
        completion_tokens_today = kw_today.completion_tokens or 0 if kw_today else 0
        llm_summary = {
            'total_analyzed_today': llm_total_today,
            'prompt_tokens_today': prompt_tokens_today,
            'completion_tokens_today': completion_tokens_today,
            'error_rate_today': round(phase3_errors / max(llm_total_today + phase3_errors, 1), 3),
        }

        data = {
            'generated_at': now.isoformat(),
            'is_weekend_kst': is_weekend,
            'phases': phases,
            'ml_summary': ml_summary,
            'llm_summary': llm_summary,
        }

        cache.set(cache_key, data, 300)  # 5분 캐시
        return Response(data)

    @action(detail=False, methods=['get'], url_path='ml-trend', permission_classes=[IsAdminUser])
    def ml_trend(self, request):
        """
        ML 모델 F1 추이

        GET /api/v1/news/ml-trend/?weeks=12

        Query Parameters:
            - weeks: 조회 기간 (기본값: 12, 최대: 52)

        Returns:
            {weeks, history, latest_feature_importance, trend_summary}
        """
        try:
            weeks = min(int(request.query_params.get('weeks', 12)), 52)
        except (ValueError, TypeError):
            weeks = 12

        cache_key = f"news:ml_trend:{weeks}"
        cached_data = cache.get(cache_key)
        if cached_data:
            logger.info(f"Cache hit: {cache_key}")
            return Response(cached_data)

        cutoff = timezone.now() - timedelta(weeks=weeks)
        history_qs = MLModelHistory.objects.filter(
            trained_at__gte=cutoff
        ).order_by('trained_at')

        history = []
        for model in history_qs:
            history.append({
                'model_version': model.model_version,
                'trained_at': model.trained_at.isoformat(),
                'algorithm': model.algorithm,
                'f1_score': model.f1_score,
                'precision': model.precision,
                'recall': model.recall,
                'accuracy': model.accuracy,
                'training_samples': model.training_samples,
                'safety_gate_passed': model.safety_gate_passed,
                'deployment_status': model.deployment_status,
            })

        # latest feature importance
        latest_model = MLModelHistory.objects.order_by('-trained_at').first()
        latest_feature_importance = None
        if latest_model and latest_model.feature_importance:
            latest_feature_importance = latest_model.feature_importance

        # trend summary
        f1_scores = [m['f1_score'] for m in history if m['f1_score'] is not None]
        trend_summary = {
            'f1_direction': 'stable',
            'f1_change_total': 0.0,
            'avg_f1': 0.0,
            'consecutive_decline': False,
        }
        if len(f1_scores) >= 2:
            f1_change = round(f1_scores[-1] - f1_scores[0], 3)
            trend_summary['f1_change_total'] = f1_change
            trend_summary['avg_f1'] = round(sum(f1_scores) / len(f1_scores), 3)
            trend_summary['f1_direction'] = 'improving' if f1_change > 0.01 else ('declining' if f1_change < -0.01 else 'stable')
            # 연속 하락 감지 (최근 3개)
            if len(f1_scores) >= 3:
                recent3 = f1_scores[-3:]
                trend_summary['consecutive_decline'] = all(
                    recent3[i] > recent3[i + 1] for i in range(len(recent3) - 1)
                )

        data = {
            'weeks': weeks,
            'history': history,
            'latest_feature_importance': latest_feature_importance,
            'trend_summary': trend_summary,
        }

        cache.set(cache_key, data, 3600)  # 1시간 캐시
        return Response(data)

    @action(detail=False, methods=['get'], url_path='llm-usage', permission_classes=[IsAdminUser])
    def llm_usage(self, request):
        """
        LLM 토큰 사용량 집계

        GET /api/v1/news/llm-usage/?days=30

        Query Parameters:
            - days: 조회 기간 (기본값: 30)

        Returns:
            {period_days, keyword_extraction, deep_analysis}

        Note:
            키워드 추출 비용만 반영됩니다.
            Phase 3 심층 분석 비용은 미포함 (Phase B에서 추가 예정).
        """
        try:
            days = int(request.query_params.get('days', 30))
        except (ValueError, TypeError):
            days = 30

        cache_key = f"news:llm_usage:{days}"
        cached_data = cache.get(cache_key)
        if cached_data:
            logger.info(f"Cache hit: {cache_key}")
            return Response(cached_data)

        cutoff = timezone.now() - timedelta(days=days)
        kw_qs = DailyNewsKeyword.objects.filter(date__gte=cutoff.date()).order_by('date')

        daily = []
        for kw in kw_qs:
            prompt = kw.prompt_tokens or 0
            completion = kw.completion_tokens or 0
            daily.append({
                'date': str(kw.date),
                'status': kw.status,
                'prompt_tokens': prompt,
                'completion_tokens': completion,
                'total_tokens': prompt + completion,
                'generation_time_ms': kw.generation_time_ms or 0,
                'total_news_analyzed': kw.total_news_count,
            })

        totals_agg = kw_qs.aggregate(
            total_prompt=Sum('prompt_tokens'),
            total_completion=Sum('completion_tokens'),
            total_gen_time=Sum('generation_time_ms'),
        )
        success_days = kw_qs.filter(status='completed').count()
        failed_days = kw_qs.filter(status='failed').count()
        total_days = kw_qs.count()
        avg_gen_time = round(
            (totals_agg['total_gen_time'] or 0) / total_days, 0
        ) if total_days > 0 else 0

        totals = {
            'prompt_tokens': totals_agg['total_prompt'] or 0,
            'completion_tokens': totals_agg['total_completion'] or 0,
            'total_tokens': (totals_agg['total_prompt'] or 0) + (totals_agg['total_completion'] or 0),
            'success_days': success_days,
            'failed_days': failed_days,
            'avg_generation_time_ms': int(avg_gen_time),
        }

        # deep analysis 통계 (건수만, 토큰 미추적)
        now = timezone.now()
        today_start_kst = _kst_today_start()
        total_analyzed = NewsArticle.objects.filter(llm_analyzed=True).count()
        today_analyzed = NewsArticle.objects.filter(
            llm_analyzed=True,
            updated_at__gte=today_start_kst,
        ).count()
        pending_today = NewsArticle.objects.filter(
            importance_score__isnull=False,
            llm_analyzed=False,
        ).count()

        # Tier 분류 (llm_analysis.tier 필드 기반)
        tier_a = NewsArticle.objects.filter(
            llm_analyzed=True,
            llm_analysis__tier='A',
        ).count()
        tier_b = NewsArticle.objects.filter(
            llm_analyzed=True,
            llm_analysis__tier='B',
        ).count()
        tier_c = NewsArticle.objects.filter(
            llm_analyzed=True,
            llm_analysis__tier='C',
        ).count()

        data = {
            'period_days': days,
            'keyword_extraction': {
                'daily': daily,
                'totals': totals,
            },
            'deep_analysis': {
                'total_analyzed': total_analyzed,
                'today_analyzed': today_analyzed,
                'pending_today': pending_today,
                'tier_breakdown': {
                    'A': tier_a,
                    'B': tier_b,
                    'C': tier_c,
                },
                'coverage_warning': (
                    '키워드 추출 토큰만 집계됩니다. '
                    'Phase 3 심층 분석(전체 LLM 비용의 대부분)은 미포함 — Phase B에서 추가 예정'
                ),
            },
        }

        cache.set(cache_key, data, 3600)  # 1시간 캐시
        return Response(data)

    # ===== Phase B: Advanced Monitoring API =====

    @action(detail=False, methods=['get'], url_path='task-timeline', permission_classes=[IsAdminUser])
    def task_timeline(self, request):
        """
        24시간 태스크 실행 간트 차트 데이터

        GET /api/v1/news/task-timeline/?hours=24

        Query Parameters:
            - hours: 조회 기간 (기본값: 24, 최대: 72)

        Returns:
            {hours, timeline: [{task_name, provider, start, end, duration_sec, articles_new, errors, status}]}
        """
        try:
            hours = min(int(request.query_params.get('hours', 24)), 72)
        except (ValueError, TypeError):
            hours = 24

        cache_key = f"news:task_timeline:{hours}"
        cached_data = cache.get(cache_key)
        if cached_data:
            logger.info(f"Cache hit: {cache_key}")
            return Response(cached_data)

        cutoff = timezone.now() - timedelta(hours=hours)
        qs = NewsCollectionLog.objects.filter(
            executed_at__gte=cutoff
        ).order_by('executed_at')

        timeline = []
        for log in qs:
            start_dt = log.executed_at
            duration = log.duration_sec or 0.0
            end_dt = start_dt + timedelta(seconds=duration)

            if log.errors == 0:
                task_status = "ok"
            elif log.articles_new > 0:
                task_status = "warning"
            else:
                task_status = "error"

            timeline.append({
                'task_name': log.task_name,
                'provider': log.provider,
                'start': start_dt.isoformat(),
                'end': end_dt.isoformat(),
                'duration_sec': duration,
                'articles_new': log.articles_new,
                'errors': log.errors,
                'status': task_status,
            })

        data = {
            'hours': hours,
            'timeline': timeline,
        }

        cache.set(cache_key, data, 300)  # 5분 캐시
        return Response(data)

    @action(detail=False, methods=['get'], url_path='neo4j-status', permission_classes=[IsAdminUser])
    def neo4j_status(self, request):
        """
        Neo4j 동기화 상태 확인

        GET /api/v1/news/neo4j-status/

        Returns:
            {available, last_sync, synced_today, pending_sync, cleanup_last_run}
        """
        cache_key = "news:neo4j_status"
        cached_data = cache.get(cache_key)
        if cached_data:
            logger.info(f"Cache hit: {cache_key}")
            return Response(cached_data)

        # Neo4j 가용성 확인
        from news.services.news_neo4j_sync import NewsNeo4jSyncService
        sync_service = NewsNeo4jSyncService()
        available = sync_service.is_available()

        # last_sync: sync_news_to_neo4j 태스크 최신 로그
        sync_log = NewsCollectionLog.objects.filter(
            task_name='sync_news_to_neo4j'
        ).order_by('-executed_at').first()
        last_sync = sync_log.executed_at.isoformat() if sync_log else None

        # synced_today: 오늘(KST) sync 로그의 articles_new 합산
        today_start = _kst_today_start()
        synced_today = NewsCollectionLog.objects.filter(
            task_name='sync_news_to_neo4j',
            executed_at__gte=today_start,
        ).aggregate(total=Sum('articles_new'))['total'] or 0

        # pending_sync: 마지막 sync 이후 llm_analyzed 된 기사로 미동기화 건수 추정
        # (NewsArticle에 neo4j_synced 전용 필드 없음)
        if sync_log:
            pending_sync = NewsArticle.objects.filter(
                llm_analyzed=True,
                updated_at__gt=sync_log.executed_at,
            ).count()
        else:
            pending_sync = NewsArticle.objects.filter(llm_analyzed=True).count()

        # cleanup_last_run: cleanup 관련 로그
        cleanup_log = NewsCollectionLog.objects.filter(
            task_name__icontains='cleanup'
        ).order_by('-executed_at').first()
        cleanup_last_run = cleanup_log.executed_at.isoformat() if cleanup_log else None

        data = {
            'available': available,
            'last_sync': last_sync,
            'synced_today': synced_today,
            'pending_sync': pending_sync,
            'cleanup_last_run': cleanup_last_run,
        }

        cache.set(cache_key, data, 300)  # 5분 캐시
        return Response(data)

    @action(detail=False, methods=['get'], url_path='ml-rollback-preview', permission_classes=[IsAdminUser])
    def ml_rollback_preview(self, request):
        """
        현재 배포 모델 vs 롤백 대상(기본 가중치) 비교

        GET /api/v1/news/ml-rollback-preview/

        Returns:
            {current_deployed, rollback_target, default_weights, impact_warning}
        """
        from news.services.news_classifier import DEFAULT_WEIGHTS

        deployed = MLModelHistory.objects.filter(
            deployment_status='deployed'
        ).order_by('-trained_at').first()

        if not deployed:
            return Response(
                {'error': '현재 배포된 모델이 없습니다.'},
                status=status.HTTP_404_NOT_FOUND
            )

        data = {
            'current_deployed': {
                'model_version': deployed.model_version,
                'algorithm': deployed.algorithm,
                'f1_score': deployed.f1_score,
                'deployed_at': deployed.deployed_at.isoformat() if deployed.deployed_at else None,
                'smoothed_weights': deployed.smoothed_weights,
            },
            'rollback_target': 'DEFAULT_WEIGHTS (수동 가중치)',
            'default_weights': DEFAULT_WEIGHTS,
            'impact_warning': (
                '롤백 시 Engine C가 학습된 가중치 대신 기본 가중치를 사용합니다. '
                '다음 일요일 학습까지 수동 가중치로 분류됩니다.'
            ),
        }

        return Response(data)

    @action(detail=False, methods=['post'], url_path='ml-rollback', permission_classes=[IsAdminUser])
    def ml_rollback(self, request):
        """
        ML 모델 롤백 실행

        POST /api/v1/news/ml-rollback/
        Body: {"confirm": true}

        Returns:
            {status, rolled_back_version, fallback, rolled_back_at}
        """
        confirm = request.data.get('confirm')
        if confirm is not True:
            return Response(
                {'error': '롤백을 실행하려면 {"confirm": true}를 전송하세요.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        deployed = MLModelHistory.objects.filter(
            deployment_status='deployed'
        ).order_by('-trained_at').first()

        if not deployed:
            return Response(
                {'error': '현재 배포된 모델이 없습니다.'},
                status=status.HTTP_404_NOT_FOUND
            )

        from news.services.ml_production_manager import MLProductionManager
        manager = MLProductionManager()
        result = manager.rollback_model()

        rolled_back_at = timezone.now()

        data = {
            'status': result.get('status', 'rolled_back'),
            'rolled_back_version': result.get('rolled_back_version'),
            'fallback': result.get('fallback', 'manual_weights'),
            'rolled_back_at': rolled_back_at.isoformat(),
        }

        return Response(data)

    # ===== Phase C: Alert API =====

    @action(detail=False, methods=['get'], url_path='alerts', permission_classes=[IsAdminUser])
    def alerts(self, request):
        """
        파이프라인 알림 목록 조회

        GET /api/v1/news/alerts/

        Query Parameters:
            - resolved: true/false — 해결 여부 필터 (기본: 미해결만)
            - severity: high/medium/low/critical — 심각도 필터
            - trigger_type: 트리거 타입 필터
            - limit: 최대 개수 (기본 50, max 200)

        Returns:
            {total, unresolved_count, alerts: [...]}
        """
        resolved_param = request.query_params.get('resolved', 'false').lower()
        severity = request.query_params.get('severity')
        trigger_type = request.query_params.get('trigger_type')
        try:
            limit = min(int(request.query_params.get('limit', 50)), 200)
        except (ValueError, TypeError):
            limit = 50

        qs = AlertLog.objects.all()

        # resolved 필터 (기본: 미해결만)
        if resolved_param == 'true':
            qs = qs.filter(is_resolved=True)
        else:
            qs = qs.filter(is_resolved=False)

        if severity:
            qs = qs.filter(severity=severity)

        if trigger_type:
            qs = qs.filter(trigger_type=trigger_type)

        qs = qs.order_by('-created_at')

        total = qs.count()
        unresolved_count = AlertLog.objects.filter(is_resolved=False).count()

        alert_list = []
        for alert in qs[:limit]:
            alert_list.append({
                'id': alert.id,
                'trigger_type': alert.trigger_type,
                'trigger_type_display': alert.get_trigger_type_display(),
                'severity': alert.severity,
                'message': alert.message,
                'context': alert.context,
                'is_resolved': alert.is_resolved,
                'resolved_at': alert.resolved_at.isoformat() if alert.resolved_at else None,
                'acknowledged_by': alert.acknowledged_by,
                'created_at': alert.created_at.isoformat(),
            })

        return Response({
            'total': total,
            'unresolved_count': unresolved_count,
            'alerts': alert_list,
        })

    @action(detail=False, methods=['post'], url_path=r'alerts/(?P<alert_pk>\d+)/resolve', permission_classes=[IsAdminUser])
    def alerts_resolve(self, request, alert_pk=None):
        """
        알림 해결 처리

        POST /api/v1/news/alerts/<alert_pk>/resolve/
        Body: {"acknowledged_by": "admin"} (선택)

        Returns:
            {status, id, resolved_at}
        """
        try:
            alert = AlertLog.objects.get(pk=alert_pk)
        except AlertLog.DoesNotExist:
            return Response(
                {'error': '알림을 찾을 수 없습니다.'},
                status=status.HTTP_404_NOT_FOUND
            )

        if alert.is_resolved:
            return Response(
                {'error': '이미 해결된 알림입니다.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        alert.is_resolved = True
        alert.resolved_at = timezone.now()
        alert.acknowledged_by = request.data.get('acknowledged_by', '')
        alert.save(update_fields=['is_resolved', 'resolved_at', 'acknowledged_by', 'updated_at'])

        return Response({
            'status': 'resolved',
            'id': alert.id,
            'resolved_at': alert.resolved_at.isoformat(),
        })
