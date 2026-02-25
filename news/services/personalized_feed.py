"""
Personalized Feed Service - 사용자 맞춤 뉴스 피드

우선순위 캐스케이드:
1. 포트폴리오 심볼 -> 해당 종목 뉴스
2. 관심종목(Watchlist) 심볼 -> 해당 종목 뉴스
3. 명시적 관심사 -> NewsCollectionCategory -> 뉴스
4. Fallback -> MarketFeedService.get_feed()
"""

import logging
from datetime import timedelta

from django.utils import timezone

from news.models import NewsArticle

logger = logging.getLogger(__name__)


class PersonalizedFeedService:
    """사용자 맞춤 뉴스 피드 서비스"""

    def get_feed(self, user) -> dict:
        from_date = timezone.now() - timedelta(days=3)
        articles = []
        source_type = 'market_feed'  # default

        # 1. 포트폴리오 심볼
        portfolio_symbols = self._get_portfolio_symbols(user)
        if portfolio_symbols:
            portfolio_news = self._get_news_for_symbols(portfolio_symbols, from_date, limit=8)
            if portfolio_news:
                articles.extend(portfolio_news)
                source_type = 'portfolio'

        # 2. Watchlist 심볼
        watchlist_symbols = self._get_watchlist_symbols(user)
        remaining = max(0, 14 - len(articles))
        if watchlist_symbols and remaining > 0:
            # 포트폴리오에서 이미 가져온 심볼 제외
            new_symbols = [s for s in watchlist_symbols if s not in portfolio_symbols]
            if new_symbols:
                watchlist_news = self._get_news_for_symbols(new_symbols, from_date, limit=min(6, remaining))
                articles.extend(watchlist_news)
                if not portfolio_symbols:
                    source_type = 'watchlist'

        # 3. 명시적 관심사
        remaining = max(0, 14 - len(articles))
        if remaining > 0:
            interest_symbols = self._get_interest_symbols(user)
            all_existing = set(portfolio_symbols + watchlist_symbols)
            new_symbols = [s for s in interest_symbols if s not in all_existing]
            if new_symbols:
                interest_news = self._get_news_for_symbols(new_symbols, from_date, limit=min(6, remaining))
                articles.extend(interest_news)
                if not portfolio_symbols and not watchlist_symbols:
                    source_type = 'interests'

        # 4. Fallback
        if not articles:
            from .market_feed import MarketFeedService
            return {
                'source_type': 'market_feed',
                'personalized': False,
                'feed': MarketFeedService().get_feed(),
            }

        # 중복 제거
        seen_ids = set()
        unique_articles = []
        for a in articles:
            if a['id'] not in seen_ids:
                seen_ids.add(a['id'])
                unique_articles.append(a)

        return {
            'source_type': source_type,
            'personalized': True,
            'articles': unique_articles[:14],
            'symbols_used': {
                'portfolio': portfolio_symbols[:5],
                'watchlist': watchlist_symbols[:5],
            },
        }

    def _get_portfolio_symbols(self, user) -> list:
        from users.models import Portfolio
        return list(
            Portfolio.objects.filter(user=user)
            .values_list('stock__symbol', flat=True)
        )

    def _get_watchlist_symbols(self, user) -> list:
        from users.models import WatchlistItem
        return list(
            WatchlistItem.objects.filter(watchlist__user=user)
            .values_list('stock__symbol', flat=True)
            .distinct()
        )

    def _get_interest_symbols(self, user) -> list:
        from users.models import UserInterest
        from news.models import NewsCollectionCategory

        symbols = []
        interests = UserInterest.objects.filter(user=user)
        for interest in interests:
            if interest.auto_category_id:
                try:
                    cat = NewsCollectionCategory.objects.get(id=interest.auto_category_id)
                    symbols.extend(cat.resolve_symbols()[:5])
                except NewsCollectionCategory.DoesNotExist:
                    pass
        return list(set(symbols))

    def _get_news_for_symbols(self, symbols: list, from_date, limit: int = 8) -> list:
        articles = NewsArticle.objects.filter(
            entities__symbol__in=symbols,
            published_at__gte=from_date,
        ).distinct().order_by('-published_at')[:limit]

        return [
            {
                'id': str(a.id),
                'title': a.title,
                'url': a.url,
                'source': a.source,
                'published_at': a.published_at.isoformat(),
                'sentiment_score': float(a.sentiment_score) if a.sentiment_score else None,
                'symbols': list(a.entities.values_list('symbol', flat=True)[:5]),
            }
            for a in articles
        ]
