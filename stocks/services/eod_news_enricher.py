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

    # confidence 순서 (시간적 인과성 보정에 사용)
    CONFIDENCE_ORDER = ['none', 'low', 'medium', 'high', 'very_high']

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

            # primary signal direction 추출
            signals = item.get('signals', [])
            signal_direction = signals[0].get('direction', 'neutral') if signals else 'neutral'

            news_context = self._find_news(
                symbol, sector, industry, target_date,
                signal_direction=signal_direction,
            )
            enriched_item = dict(item)
            enriched_item['news_context'] = news_context
            enriched.append(enriched_item)

        logger.info(
            f"[EODNewsEnricher] enrichment 완료: {len(enriched)}종목, "
            f"뉴스 매칭={sum(1 for e in enriched if e['news_context'].get('match_type') != 'none')}건"
        )
        return enriched

    def _find_news(
        self, symbol: str, sector: str, industry: str, target_date: date,
        signal_direction: str = 'neutral',
    ) -> dict:
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
            return self._build_news_dict(news, 'symbol_today', 'high', target_date, signal_direction)

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
            return self._build_news_dict(news, 'symbol_7d', 'medium', target_date, signal_direction)

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
            return self._build_news_dict(news, 'symbol_30d', 'low', target_date, signal_direction)

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
        signal_direction: str = 'neutral',
    ) -> dict:
        """
        StockNews 인스턴스를 news_context dict로 변환합니다.
        sentiment-시그널 방향 시간적 인과성 기반으로 confidence를 보정합니다.
        """
        published_date = news.published_at.date() if hasattr(news.published_at, 'date') else target_date
        age_days = (target_date - published_date).days

        adjusted_confidence = self._adjust_confidence(
            confidence, match_type, news, signal_direction,
        )

        return {
            'headline': news.headline or '',
            'summary': news.summary or '',
            'source': news.source or '',
            'url': news.url or '',
            'match_type': match_type,
            'confidence': adjusted_confidence,
            'age_days': age_days,
            'sentiment': news.sentiment or '',
            'published_at': news.published_at.isoformat() if news.published_at else '',
        }

    # sentiment 정규화 매핑: 다양한 형식 → positive/negative/neutral
    _SENTIMENT_MAP = {
        'positive': 'positive',
        'bullish': 'positive',
        'up': 'positive',
        '+': 'positive',
        '긍정': 'positive',
        'negative': 'negative',
        'bearish': 'negative',
        'down': 'negative',
        '-': 'negative',
        '부정': 'negative',
        'neutral': 'neutral',
        'mixed': 'neutral',
        '0': 'neutral',
        '중립': 'neutral',
    }

    @staticmethod
    def _normalize_sentiment(raw: str | None) -> str:
        """다양한 sentiment 형식을 positive/negative/neutral로 정규화합니다."""
        if not raw:
            return ''
        cleaned = raw.lower().strip()
        return EODNewsEnricher._SENTIMENT_MAP.get(cleaned, cleaned)

    def _adjust_confidence(
        self,
        base_confidence: str,
        match_type: str,
        news: 'StockNews',
        signal_direction: str,
    ) -> str:
        """
        뉴스 sentiment와 시그널 방향의 관계를 시간적 인과성 기반으로 보정합니다.

        - 당일 뉴스(symbol_today) + 방향 일치 → confidence 유지 (buy the rumor 리스크)
        - 당일 뉴스 + 방향 충돌 → confidence 하향 (반전 리스크)
        - 과거 뉴스(symbol_7d) + 방향 일치 → confidence 상향 (모멘텀 지속)
        - 과거 뉴스 + 방향 충돌 → confidence 하향
        """
        sentiment = self._normalize_sentiment(getattr(news, 'sentiment', ''))
        if not sentiment or signal_direction == 'neutral':
            return base_confidence

        directions_match = (
            (sentiment == 'positive' and signal_direction == 'bullish') or
            (sentiment == 'negative' and signal_direction == 'bearish')
        )
        directions_conflict = (
            (sentiment == 'positive' and signal_direction == 'bearish') or
            (sentiment == 'negative' and signal_direction == 'bullish')
        )

        def _shift(conf: str, delta: int) -> str:
            order = self.CONFIDENCE_ORDER
            idx = order.index(conf) if conf in order else 2
            return order[max(0, min(len(order) - 1, idx + delta))]

        if match_type == 'symbol_today':
            if directions_conflict:
                return _shift(base_confidence, -1)
            # 일치해도 올리지 않음 (buy the rumor 리스크)
            return base_confidence

        elif match_type == 'symbol_7d':
            if directions_match:
                return _shift(base_confidence, +1)
            if directions_conflict:
                return _shift(base_confidence, -1)

        return base_confidence

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
