"""
뉴스 API Views
"""

import logging
from datetime import timedelta

from django.utils import timezone
from decimal import Decimal

from django.db.models import Count, Avg, Q
from django.core.cache import cache
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import AllowAny, IsAuthenticated

from ..models import NewsArticle, NewsEntity, SentimentHistory, DailyNewsKeyword
from ..services import NewsAggregatorService
from .serializers import (
    NewsArticleListSerializer,
    NewsArticleDetailSerializer,
    SentimentHistorySerializer,
    SentimentSummarySerializer,
    TrendingStockSerializer
)

logger = logging.getLogger(__name__)


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
