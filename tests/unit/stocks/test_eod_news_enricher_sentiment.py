"""
EODNewsEnricher sentiment-시그널 방향 보정 단위 테스트.

시간적 인과성 기반 confidence 보정 로직을 검증합니다.
"""

import pytest
from unittest.mock import MagicMock
from stocks.services.eod_news_enricher import EODNewsEnricher


class TestAdjustConfidence:
    """_adjust_confidence 메서드 단위 테스트."""

    def setup_method(self):
        self.enricher = EODNewsEnricher()

    def _make_news(self, sentiment=''):
        """Mock StockNews 객체 생성."""
        news = MagicMock()
        news.sentiment = sentiment
        return news

    # === symbol_today 테스트 ===

    def test_symbol_today_conflict_downgrades(self):
        """당일 뉴스 + 방향 충돌 → confidence 한 단계 하향."""
        news = self._make_news('positive')
        result = self.enricher._adjust_confidence(
            'high', 'symbol_today', news, 'bearish'
        )
        assert result == 'medium'

    def test_symbol_today_match_no_change(self):
        """당일 뉴스 + 방향 일치 → confidence 유지 (buy the rumor 리스크)."""
        news = self._make_news('positive')
        result = self.enricher._adjust_confidence(
            'high', 'symbol_today', news, 'bullish'
        )
        assert result == 'high'  # 올리지 않음

    def test_symbol_today_neutral_signal_no_change(self):
        """당일 뉴스 + neutral 시그널 → 보정 없음."""
        news = self._make_news('positive')
        result = self.enricher._adjust_confidence(
            'high', 'symbol_today', news, 'neutral'
        )
        assert result == 'high'

    def test_symbol_today_no_sentiment_no_change(self):
        """당일 뉴스 + sentiment 없음 → 보정 없음."""
        news = self._make_news('')
        result = self.enricher._adjust_confidence(
            'high', 'symbol_today', news, 'bullish'
        )
        assert result == 'high'

    # === symbol_7d 테스트 ===

    def test_symbol_7d_match_upgrades(self):
        """과거 뉴스(7일) + 방향 일치 → confidence 한 단계 상향."""
        news = self._make_news('positive')
        result = self.enricher._adjust_confidence(
            'medium', 'symbol_7d', news, 'bullish'
        )
        assert result == 'high'

    def test_symbol_7d_conflict_downgrades(self):
        """과거 뉴스(7일) + 방향 충돌 → confidence 한 단계 하향."""
        news = self._make_news('negative')
        result = self.enricher._adjust_confidence(
            'medium', 'symbol_7d', news, 'bullish'
        )
        assert result == 'low'

    def test_symbol_7d_negative_bearish_match_upgrades(self):
        """과거 뉴스(7일) negative + bearish 시그널 → 방향 일치 → 상향."""
        news = self._make_news('negative')
        result = self.enricher._adjust_confidence(
            'medium', 'symbol_7d', news, 'bearish'
        )
        assert result == 'high'

    def test_symbol_7d_positive_bearish_conflict_downgrades(self):
        """과거 뉴스(7일) positive + bearish 시그널 → 충돌 → 하향."""
        news = self._make_news('positive')
        result = self.enricher._adjust_confidence(
            'medium', 'symbol_7d', news, 'bearish'
        )
        assert result == 'low'

    # === 경계값 테스트 ===

    def test_upgrade_capped_at_very_high(self):
        """confidence 상한선: very_high 초과 불가."""
        news = self._make_news('positive')
        result = self.enricher._adjust_confidence(
            'very_high', 'symbol_7d', news, 'bullish'
        )
        assert result == 'very_high'

    def test_downgrade_floored_at_none(self):
        """confidence 하한선: none 미만 불가."""
        news = self._make_news('positive')
        result = self.enricher._adjust_confidence(
            'none', 'symbol_today', news, 'bearish'
        )
        assert result == 'none'

    def test_high_upgrade_to_very_high(self):
        """high → very_high 상향 가능."""
        news = self._make_news('negative')
        result = self.enricher._adjust_confidence(
            'high', 'symbol_7d', news, 'bearish'
        )
        assert result == 'very_high'

    # === 기타 match_type 테스트 ===

    def test_symbol_30d_no_adjustment(self):
        """symbol_30d → 보정 없음 (symbol_today, symbol_7d만 보정)."""
        news = self._make_news('positive')
        result = self.enricher._adjust_confidence(
            'low', 'symbol_30d', news, 'bullish'
        )
        assert result == 'low'

    def test_industry_7d_no_adjustment(self):
        """industry_7d → 보정 없음."""
        news = self._make_news('positive')
        result = self.enricher._adjust_confidence(
            'medium', 'industry_7d', news, 'bullish'
        )
        assert result == 'medium'

    # === sentiment 정규화 테스트 ===

    def test_uppercase_sentiment_normalized(self):
        """대문자 sentiment도 정규화되어 처리."""
        news = self._make_news('Positive')
        result = self.enricher._adjust_confidence(
            'high', 'symbol_today', news, 'bearish'
        )
        assert result == 'medium'

    def test_whitespace_sentiment_normalized(self):
        """공백 포함 sentiment도 정규화."""
        news = self._make_news('  positive  ')
        result = self.enricher._adjust_confidence(
            'high', 'symbol_today', news, 'bearish'
        )
        assert result == 'medium'


class TestNormalizeSentiment:
    """_normalize_sentiment 정규화 매핑 테스트."""

    def test_positive_variants(self):
        """다양한 positive 형식 → 'positive'."""
        for raw in ['positive', 'Positive', 'bullish', 'up', '+', '긍정']:
            assert EODNewsEnricher._normalize_sentiment(raw) == 'positive'

    def test_negative_variants(self):
        """다양한 negative 형식 → 'negative'."""
        for raw in ['negative', 'Negative', 'bearish', 'down', '-', '부정']:
            assert EODNewsEnricher._normalize_sentiment(raw) == 'negative'

    def test_neutral_variants(self):
        """다양한 neutral 형식 → 'neutral'."""
        for raw in ['neutral', 'mixed', '0', '중립']:
            assert EODNewsEnricher._normalize_sentiment(raw) == 'neutral'

    def test_empty_and_none(self):
        """빈 문자열/None → 빈 문자열."""
        assert EODNewsEnricher._normalize_sentiment('') == ''
        assert EODNewsEnricher._normalize_sentiment(None) == ''

    def test_unknown_passthrough(self):
        """매핑에 없는 값 → 소문자 그대로 반환."""
        assert EODNewsEnricher._normalize_sentiment('very_positive') == 'very_positive'

    def test_bullish_sentiment_triggers_match(self):
        """'bullish' sentiment → 'positive'로 정규화 → bullish 시그널과 일치."""
        enricher = EODNewsEnricher()
        news = MagicMock()
        news.sentiment = 'bullish'
        result = enricher._adjust_confidence('medium', 'symbol_7d', news, 'bullish')
        assert result == 'high'  # positive + bullish = match → 상향

    def test_bearish_sentiment_triggers_match(self):
        """'bearish' sentiment → 'negative'로 정규화 → bearish 시그널과 일치."""
        enricher = EODNewsEnricher()
        news = MagicMock()
        news.sentiment = 'bearish'
        result = enricher._adjust_confidence('medium', 'symbol_7d', news, 'bearish')
        assert result == 'high'  # negative + bearish = match → 상향
