"""
Market Feed Service - AI 뉴스 브리핑 + 시장 컨텍스트

콜드 스타트 사용자에게 AI가 분석한 뉴스 키워드 + 관련 헤드라인 + 시장 데이터를 제공합니다.
"""

import logging
from datetime import datetime

from django.core.cache import cache
from django.utils import timezone

from news.models import DailyNewsKeyword, NewsArticle, NewsEntity

logger = logging.getLogger(__name__)


class MarketFeedService:
    """AI 뉴스 브리핑 + 시장 컨텍스트를 조합한 cold start 피드"""

    CACHE_TTL = 600  # 10분

    def get_feed(self) -> dict:
        today = timezone.now().date()
        cache_key = f"market_feed:{today}"

        cached = cache.get(cache_key)
        if cached:
            return cached

        # 1. 최신 완료된 키워드 조회 (fallback 포함)
        keyword_obj, is_fallback = self._get_latest_keywords()

        if not keyword_obj:
            return {
                'date': str(today),
                'is_fallback': True,
                'fallback_message': '아직 분석된 키워드가 없습니다',
                'briefing': {
                    'keywords': [],
                    'total_news_count': 0,
                    'llm_model': None,
                },
                'market_context': {
                    'top_sectors': [],
                    'hot_movers': [],
                },
            }

        best_date = keyword_obj.date
        keywords = keyword_obj.keywords or []

        # 2. Post-processing: 각 키워드에 뉴스 매칭
        enriched_keywords = self._enrich_keywords_with_news(keywords, best_date)

        # 3. 시장 컨텍스트 (optional)
        market_context = self._get_market_context()

        # 4. fallback 메시지
        fallback_message = None
        if is_fallback:
            fallback_message = f"{best_date.strftime('%Y-%m-%d')} 분석 결과 표시 중"

        result = {
            'date': str(best_date),
            'is_fallback': is_fallback,
            'fallback_message': fallback_message,
            'briefing': {
                'keywords': enriched_keywords,
                'total_news_count': keyword_obj.total_news_count,
                'llm_model': keyword_obj.llm_model,
            },
            'market_context': market_context,
        }

        # 캐시 저장
        cache.set(cache_key, result, self.CACHE_TTL)

        return result

    def _get_latest_keywords(self):
        """최신 완료된 키워드를 가져옴. 오늘 없으면 최근 거래일 데이터로 fallback."""
        today = timezone.now().date()
        kw = DailyNewsKeyword.objects.filter(date=today, status='completed').first()
        if kw:
            return kw, False

        # 최근 완료된 키워드로 fallback
        kw = DailyNewsKeyword.objects.filter(status='completed').order_by('-date').first()
        if kw:
            return kw, True
        return None, True

    def _enrich_keywords_with_news(self, keywords: list, best_date) -> list:
        """각 키워드의 related_symbols로 실제 뉴스를 매칭하여 headlines 추가"""
        start_dt = datetime.combine(best_date, datetime.min.time())
        end_dt = datetime.combine(best_date, datetime.max.time())

        if timezone.is_naive(start_dt):
            start_dt = timezone.make_aware(start_dt)
            end_dt = timezone.make_aware(end_dt)

        enriched = []
        for kw in keywords:
            symbols = kw.get('related_symbols', [])
            news_count = 0
            headlines = []

            if symbols:
                matching_news = NewsArticle.objects.filter(
                    entities__symbol__in=symbols,
                    published_at__gte=start_dt,
                    published_at__lte=end_dt,
                ).distinct().order_by('-published_at')[:3]

                # Count는 별도 쿼리 (슬라이스 이후 count 불가)
                news_count = NewsArticle.objects.filter(
                    entities__symbol__in=symbols,
                    published_at__gte=start_dt,
                    published_at__lte=end_dt,
                ).distinct().count()

                headlines = [
                    {'title': n.title, 'url': n.url}
                    for n in matching_news
                ]

            enriched.append({
                'text': kw.get('text', ''),
                'sentiment': kw.get('sentiment', 'neutral'),
                'related_symbols': symbols,
                'importance': kw.get('importance', 0.5),
                'reason': kw.get('reason', ''),
                'news_count': news_count,
                'headlines': headlines,
            })

        return enriched

    def _get_market_context(self) -> dict:
        """SectorPerformance, MarketMover에서 시장 컨텍스트 조회"""
        top_sectors = []
        hot_movers = []

        try:
            from serverless.models import SectorPerformance
            latest_sp = SectorPerformance.objects.order_by('-date').first()
            if latest_sp and latest_sp.data:
                sectors = latest_sp.data if isinstance(latest_sp.data, list) else []
                for s in sectors[:5]:
                    top_sectors.append({
                        'name': s.get('sector', ''),
                        'return_pct': float(s.get('changesPercentage', 0)),
                        'stock_count': 0,
                    })
        except Exception as e:
            logger.debug(f"SectorPerformance not available: {e}")

        try:
            from serverless.models import MarketMover
            from django.utils import timezone as tz
            from datetime import timedelta
            recent_date = tz.now().date() - timedelta(days=3)
            movers = MarketMover.objects.filter(
                date__gte=recent_date,
                category='gainers'
            ).order_by('-change_percent')[:5]

            for m in movers:
                hot_movers.append({
                    'symbol': m.symbol,
                    'company_name': m.company_name or m.symbol,
                    'change_percent': float(m.change_percent) if m.change_percent else 0,
                    'sector': '',
                })
        except Exception as e:
            logger.debug(f"MarketMover not available: {e}")

        return {
            'top_sectors': top_sectors,
            'hot_movers': hot_movers,
        }
