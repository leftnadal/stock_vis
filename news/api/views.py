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

from ..models import NewsArticle, NewsEntity, SentimentHistory
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
