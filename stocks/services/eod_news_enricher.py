"""
EOD News Enricher (Step 4)

tagged_signals에 news_context를 추가합니다.
StockNews 모델에서 5단계 계층적 매칭으로 뉴스를 연결합니다.
"""

import logging
from datetime import date, timedelta

from django.utils import timezone

from stocks.models import StockNews, Stock

logger = logging.getLogger(__name__)


class EODNewsEnricher:
    """
    시그널 태깅 결과에 뉴스 컨텍스트를 추가하는 enricher.

    5단계 계층적 매칭 (상위 우선순위에서 찾으면 즉시 반환):
    1. symbol_today: 종목 심볼 매칭 + 당일 뉴스
    2. symbol_7d: 종목 심볼 매칭 + 7일 이내
    3. symbol_30d: 종목 심볼 매칭 + 30일 이내
    4. industry_7d: industry 매칭 + 7일 이내
    5. profile: Stock 모델에서 기업 기본 정보 팩트 요약
    """

    def enrich(self, tagged_signals: list[dict], target_date: date) -> list[dict]:
        """
        tagged_signals 각 항목에 news_context 필드를 추가합니다.

        Args:
            tagged_signals: EODSignalTagger.tag_signals() 반환값
            target_date: 파이프라인 실행 기준 날짜

        Returns:
            tagged_signals와 동일한 구조에 'news_context' 키 추가
        """
        enriched = []
        for item in tagged_signals:
            symbol = item.get('stock_id', '')
            sector = item.get('sector', '')
            industry = item.get('industry', '')

            news_context = self._find_news(symbol, sector, industry, target_date)
            enriched_item = dict(item)
            enriched_item['news_context'] = news_context
            enriched.append(enriched_item)

        logger.info(
            f"[EODNewsEnricher] enrichment 완료: {len(enriched)}종목, "
            f"뉴스 매칭={sum(1 for e in enriched if e['news_context'].get('match_type') != 'none')}건"
        )
        return enriched

    def _find_news(self, symbol: str, sector: str, industry: str, target_date: date) -> dict:
        """
        5단계 계층적 매칭으로 최적의 뉴스 컨텍스트를 반환합니다.
        각 단계에서 찾으면 즉시 반환합니다.

        Returns:
            {
                'headline': str,
                'source': str,
                'url': str,
                'match_type': str,  # 'symbol_today' | 'symbol_7d' | 'symbol_30d' | 'industry_7d' | 'profile' | 'none'
                'confidence': str,  # 'high' | 'medium' | 'low' | 'info'
                'age_days': int,
            }
        """
        # 1단계: symbol 매칭 + 당일 뉴스
        today_start = timezone.datetime.combine(target_date, timezone.datetime.min.time())
        today_end = timezone.datetime.combine(target_date, timezone.datetime.max.time())
        if timezone.is_naive(today_start):
            import pytz
            today_start = timezone.make_aware(today_start, pytz.UTC)
            today_end = timezone.make_aware(today_end, pytz.UTC)

        news = (
            StockNews.objects.filter(
                symbol=symbol,
                published_at__date=target_date,
            )
            .order_by('-published_at')
            .first()
        )
        if news:
            return self._build_news_dict(news, 'symbol_today', 'high', target_date)

        # 2단계: symbol 매칭 + 7일 이내
        cutoff_7d = target_date - timedelta(days=7)
        news = (
            StockNews.objects.filter(
                symbol=symbol,
                published_at__date__gte=cutoff_7d,
                published_at__date__lte=target_date,
            )
            .order_by('-published_at')
            .first()
        )
        if news:
            return self._build_news_dict(news, 'symbol_7d', 'medium', target_date)

        # 3단계: symbol 매칭 + 30일 이내
        cutoff_30d = target_date - timedelta(days=30)
        news = (
            StockNews.objects.filter(
                symbol=symbol,
                published_at__date__gte=cutoff_30d,
                published_at__date__lte=target_date,
            )
            .order_by('-published_at')
            .first()
        )
        if news:
            return self._build_news_dict(news, 'symbol_30d', 'low', target_date)

        # 4단계: industry 매칭 + 7일 이내
        if industry:
            news = (
                StockNews.objects.filter(
                    industry=industry,
                    published_at__date__gte=cutoff_7d,
                    published_at__date__lte=target_date,
                )
                .order_by('-published_at')
                .first()
            )
            if news:
                return self._build_news_dict(news, 'industry_7d', 'context', target_date)

        # 5단계: Stock 프로필 fallback
        profile = self._build_profile_fallback(symbol)
        if profile:
            return profile

        return {
            'headline': '',
            'source': '',
            'url': '',
            'match_type': 'none',
            'confidence': 'none',
            'age_days': 0,
        }

    def _build_news_dict(
        self,
        news: 'StockNews',
        match_type: str,
        confidence: str,
        target_date: date,
    ) -> dict:
        """
        StockNews 인스턴스를 news_context dict로 변환합니다.
        """
        published_date = news.published_at.date() if hasattr(news.published_at, 'date') else target_date
        age_days = (target_date - published_date).days

        return {
            'headline': news.headline or '',
            'summary': news.summary or '',
            'source': news.source or '',
            'url': news.url or '',
            'match_type': match_type,
            'confidence': confidence,
            'age_days': age_days,
            'sentiment': news.sentiment or '',
            'published_at': news.published_at.isoformat() if news.published_at else '',
        }

    def _build_profile_fallback(self, symbol: str) -> dict:
        """
        Stock 모델에서 기업 기본 정보를 팩트 요약으로 반환합니다.
        뉴스가 전혀 없는 경우의 최후 fallback.
        """
        stock = Stock.objects.filter(symbol=symbol).first()
        if stock:
            parts = []
            if stock.stock_name:
                parts.append(stock.stock_name)
            if stock.sector:
                parts.append(f"섹터: {stock.sector}")
            if stock.market_capitalization:
                cap_b = float(stock.market_capitalization) / 1e9
                parts.append(f"시총 ${cap_b:.0f}B")
            return {
                'headline': ' | '.join(parts),
                'summary': stock.description[:200] if stock.description else '',
                'source': 'profile',
                'url': stock.official_site or '',
                'match_type': 'profile',
                'confidence': 'info',
                'age_days': 0,
                'sentiment': '',
                'published_at': '',
            }
        return {}
