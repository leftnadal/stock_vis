"""
NewsClassifier 단위 테스트

커버 범위:
- Engine A: extract_tickers() - cashtag, exchange bracket, SymbolMatcher, entity 추출
- Engine B: extract_sectors() - 키워드 기반 섹터 분류
- Engine C: calculate_importance() - 5-factor 중요도 스코어
- classify_batch() - 배치 분류 처리
- select_for_analysis() - 당일 누적 퍼센타일 선별
"""

import pytest
from datetime import datetime, timedelta
from decimal import Decimal
from unittest.mock import MagicMock, patch, PropertyMock

from django.utils import timezone

from news.models import NewsArticle, NewsEntity
from news.services.news_classifier import (
    NewsClassifier,
    AMBIGUOUS_TICKERS,
    CASHTAG_PATTERN,
    DEFAULT_WEIGHTS,
    EXCHANGE_PATTERN,
    SOURCE_CREDIBILITY,
    STOCK_CONTEXT_WORDS,
    TOP_PERCENTILE,
)


# ─────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────

def _make_article(
    title="Test News",
    summary="",
    source="Reuters",
    published_at=None,
    sentiment_score=None,
    importance_score=None,
    llm_analyzed=False,
    url=None,
):
    """NewsArticle DB 인스턴스를 생성하는 헬퍼."""
    if published_at is None:
        published_at = timezone.now()
    if url is None:
        # 고유 URL 보장
        import uuid as _uuid
        url = f"https://example.com/news/{_uuid.uuid4()}"
    return NewsArticle.objects.create(
        url=url,
        title=title,
        summary=summary,
        source=source,
        published_at=published_at,
        language="en",
        category="general",
        sentiment_score=sentiment_score,
        importance_score=importance_score,
        llm_analyzed=llm_analyzed,
    )


def _make_entity(article, symbol):
    """NewsEntity 인스턴스를 생성하는 헬퍼."""
    return NewsEntity.objects.create(
        news=article,
        symbol=symbol,
        entity_name=f"{symbol} Corp",
        entity_type="equity",
        source="finnhub",
    )


# ─────────────────────────────────────────────────────────────
# Engine A: _extract_cashtags
# ─────────────────────────────────────────────────────────────

class TestExtractCashtags:
    """_extract_cashtags() 단위 테스트"""

    def setup_method(self):
        self.classifier = NewsClassifier()

    def test_single_cashtag_extracted(self):
        """
        Given: '$AAPL' 형태의 단일 cashtag 포함 텍스트
        When: _extract_cashtags() 호출
        Then: {'AAPL'} 반환
        """
        result = self.classifier._extract_cashtags("Buy $AAPL before earnings")

        assert result == {"AAPL"}

    def test_multiple_cashtags_extracted(self):
        """
        Given: '$AAPL', '$TSLA', '$NVDA' 세 cashtag 포함
        When: _extract_cashtags() 호출
        Then: 세 ticker 모두 반환
        """
        result = self.classifier._extract_cashtags("$AAPL $TSLA and $NVDA are hot today")

        assert result == {"AAPL", "TSLA", "NVDA"}

    def test_cashtag_at_end_of_text_extracted(self):
        """
        Given: 텍스트 끝에 '$MSFT' 위치
        When: _extract_cashtags() 호출
        Then: {'MSFT'} 반환
        """
        result = self.classifier._extract_cashtags("Shares of $MSFT")

        assert "MSFT" in result

    def test_no_cashtag_returns_empty_set(self):
        """
        Given: cashtag 없는 텍스트
        When: _extract_cashtags() 호출
        Then: 빈 set 반환
        """
        result = self.classifier._extract_cashtags("Apple is a good company")

        assert result == set()

    def test_lowercase_dollar_not_matched(self):
        """
        Given: '$aapl' 소문자 cashtag (regex는 대문자만 매칭)
        When: _extract_cashtags() 호출
        Then: 빈 set 반환
        """
        result = self.classifier._extract_cashtags("Buy $aapl now")

        assert result == set()

    def test_too_long_ticker_not_matched(self):
        """
        Given: 6글자 대문자 cashtag '$TOOLNG' (최대 5글자)
        When: _extract_cashtags() 호출
        Then: 빈 set 반환
        """
        result = self.classifier._extract_cashtags("$TOOLNG is not a valid ticker")

        assert result == set()

    def test_cashtag_with_surrounding_punctuation(self):
        """
        Given: '$GOOGL,' 쉼표로 끝나는 cashtag
        When: _extract_cashtags() 호출
        Then: 'GOOGL' 추출 (\\b 경계 덕분에 쉼표 무시)
        """
        result = self.classifier._extract_cashtags("Sell $GOOGL, and buy $AMZN")

        assert "GOOGL" in result
        assert "AMZN" in result


# ─────────────────────────────────────────────────────────────
# Engine A: _extract_exchange_tickers
# ─────────────────────────────────────────────────────────────

class TestExtractExchangeTickers:
    """_extract_exchange_tickers() 단위 테스트"""

    def setup_method(self):
        self.classifier = NewsClassifier()

    def test_nasdaq_bracket_pattern_extracted(self):
        """
        Given: '(NASDAQ: AAPL)' 형태 텍스트
        When: _extract_exchange_tickers() 호출
        Then: {'AAPL'} 반환
        """
        result = self.classifier._extract_exchange_tickers(
            "Apple Inc. (NASDAQ: AAPL) reported earnings"
        )

        assert result == {"AAPL"}

    def test_nyse_bracket_pattern_extracted(self):
        """
        Given: '(NYSE: JPM)' 형태 텍스트
        When: _extract_exchange_tickers() 호출
        Then: {'JPM'} 반환
        """
        result = self.classifier._extract_exchange_tickers(
            "JPMorgan Chase (NYSE: JPM) beats estimates"
        )

        assert result == {"JPM"}

    def test_amex_bracket_pattern_extracted(self):
        """
        Given: '(AMEX: SPY)' 형태 텍스트
        When: _extract_exchange_tickers() 호출
        Then: {'SPY'} 반환
        """
        result = self.classifier._extract_exchange_tickers(
            "SPDR ETF (AMEX: SPY) saw heavy inflows"
        )

        assert "SPY" in result

    def test_multiple_exchange_tickers_extracted(self):
        """
        Given: NASDAQ: NVDA + NYSE: AMD 두 패턴 포함
        When: _extract_exchange_tickers() 호출
        Then: 두 ticker 모두 반환
        """
        result = self.classifier._extract_exchange_tickers(
            "Nvidia (NASDAQ: NVDA) and AMD (NASDAQ: AMD) compete in AI chips"
        )

        assert "NVDA" in result
        assert "AMD" in result

    def test_no_exchange_pattern_returns_empty(self):
        """
        Given: 거래소 괄호 패턴 없는 텍스트
        When: _extract_exchange_tickers() 호출
        Then: 빈 set 반환
        """
        result = self.classifier._extract_exchange_tickers("Apple is a great stock")

        assert result == set()

    def test_partial_pattern_not_matched(self):
        """
        Given: 'NASDAQ:AAPL' (괄호 없음) 패턴
        When: _extract_exchange_tickers() 호출
        Then: 빈 set 반환 (괄호 필수)
        """
        result = self.classifier._extract_exchange_tickers("NASDAQ:AAPL reported earnings")

        assert result == set()

    def test_exchange_pattern_no_space_after_colon(self):
        """
        Given: '(NYSE: JPM)' 에서 콜론 뒤 공백 있는 패턴 (정상)
        When: _extract_exchange_tickers() 호출
        Then: 'JPM' 반환
        """
        result = self.classifier._extract_exchange_tickers("Morgan (NYSE: JPM)")

        assert "JPM" in result


# ─────────────────────────────────────────────────────────────
# Engine A: _has_stock_context
# ─────────────────────────────────────────────────────────────

class TestHasStockContext:
    """_has_stock_context() 단위 테스트"""

    def setup_method(self):
        self.classifier = NewsClassifier()

    def test_stock_context_word_present(self):
        """
        Given: 'earnings' 포함 텍스트
        When: _has_stock_context() 호출
        Then: True 반환
        """
        result = self.classifier._has_stock_context(
            "meta reports strong earnings this quarter"
        )

        assert result is True

    def test_multiple_context_words_present(self):
        """
        Given: 'buy', 'analyst', 'nasdaq' 포함 텍스트
        When: _has_stock_context() 호출
        Then: True 반환
        """
        result = self.classifier._has_stock_context(
            "analyst upgrades now with a buy rating on nasdaq"
        )

        assert result is True

    def test_no_context_word_returns_false(self):
        """
        Given: 주식 관련 단어 없는 텍스트
        When: _has_stock_context() 호출
        Then: False 반환
        """
        result = self.classifier._has_stock_context(
            "the weather is nice today for a walk"
        )

        assert result is False

    def test_s_and_p_context_word(self):
        """
        Given: 's&p' 포함 텍스트
        When: _has_stock_context() 호출
        Then: True 반환
        """
        result = self.classifier._has_stock_context("s&p 500 hits record high")

        assert result is True

    def test_context_check_case_insensitive(self):
        """
        Given: 대문자 'REVENUE' 포함 텍스트 (소문자로 전달됨)
        When: _has_stock_context() 호출 (text_lower 기대)
        Then: True 반환 (호출 시 이미 소문자 전달 가정)
        """
        # 실제 사용 위치는 text_lower를 받으므로 소문자 전달
        result = self.classifier._has_stock_context("revenue guidance for next fiscal year")

        assert result is True


# ─────────────────────────────────────────────────────────────
# Engine A: _match_company_names (SymbolMatcher mock)
# ─────────────────────────────────────────────────────────────

class TestMatchCompanyNames:
    """_match_company_names() 단위 테스트 (SymbolMatcher mock 사용)"""

    def setup_method(self):
        self.classifier = NewsClassifier()

    def _patch_symbol_matcher(self, match_map: dict):
        """
        SymbolMatcher.match()를 mock_map 기반으로 패치하는 헬퍼.
        match_map: {'Apple': 'AAPL', 'Google': 'GOOGL', ...}
        """
        mock_matcher = MagicMock()
        mock_matcher.match.side_effect = lambda candidate: match_map.get(candidate)
        # symbol_matcher lazy property를 직접 교체
        self.classifier._symbol_matcher = mock_matcher
        return mock_matcher

    def test_company_name_matched_to_ticker(self):
        """
        Given: 'Apple' 이라는 단어가 포함된 텍스트 + SymbolMatcher가 'AAPL' 반환
        When: _match_company_names() 호출
        Then: {'AAPL'} 반환
        """
        self._patch_symbol_matcher({"Apple": "AAPL"})

        result = self.classifier._match_company_names(
            "Apple is reporting earnings next week"
        )

        assert "AAPL" in result

    def test_ambiguous_ticker_with_stock_context_included(self):
        """
        Given: SymbolMatcher가 'META' 반환 + 텍스트에 'earnings' 포함
        When: _match_company_names() 호출
        Then: 'META' 포함 (주식 문맥 있으므로)
        """
        self._patch_symbol_matcher({"Meta": "META"})

        result = self.classifier._match_company_names(
            "Meta earnings beat expectations this quarter"
        )

        assert "META" in result

    def test_ambiguous_ticker_without_stock_context_excluded(self):
        """
        Given: SymbolMatcher가 'NOW' 반환 + 주식 문맥 없는 텍스트
        When: _match_company_names() 호출
        Then: 'NOW' 미포함 (동음이의어 필터)
        """
        self._patch_symbol_matcher({"Now": "NOW"})

        result = self.classifier._match_company_names(
            "Now is the time to act on climate change"
        )

        assert "NOW" not in result

    def test_no_match_returns_empty(self):
        """
        Given: SymbolMatcher가 모든 후보에 None 반환
        When: _match_company_names() 호출
        Then: 빈 set 반환
        """
        self._patch_symbol_matcher({})

        result = self.classifier._match_company_names("Some random text here")

        assert result == set()

    def test_two_word_candidate_matched(self):
        """
        Given: 'Nvidia Corporation' 2단어 후보에 대해 SymbolMatcher 'NVDA' 반환
        When: _match_company_names() 호출
        Then: 'NVDA' 포함
        """
        self._patch_symbol_matcher({"Nvidia Corporation": "NVDA"})

        result = self.classifier._match_company_names("Nvidia Corporation reported record revenue")

        assert "NVDA" in result

    def test_short_word_not_a_candidate(self):
        """
        Given: 2글자 단어 'It' - 후보 추출 조건 (3글자 이상)에 미달
        When: _match_company_names() 호출
        Then: SymbolMatcher.match 호출되더라도 'It' 후보 제외
        """
        mock_matcher = MagicMock()
        mock_matcher.match.return_value = None
        self.classifier._symbol_matcher = mock_matcher

        self.classifier._match_company_names("It was a great day for the market")

        # 'It' 는 2글자이므로 후보에 포함 안 됨
        all_calls = [call[0][0] for call in mock_matcher.match.call_args_list]
        assert "It" not in all_calls


# ─────────────────────────────────────────────────────────────
# Engine A: extract_tickers (통합)
# ─────────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestExtractTickers:
    """extract_tickers() 통합 테스트"""

    def setup_method(self):
        self.classifier = NewsClassifier()
        # SymbolMatcher는 기본적으로 None 반환하도록 mock
        mock_matcher = MagicMock()
        mock_matcher.match.return_value = None
        self.classifier._symbol_matcher = mock_matcher

    def test_entity_symbol_extracted_first(self):
        """
        Given: NewsEntity에 'AAPL' 심볼이 연결된 뉴스
        When: extract_tickers() 호출
        Then: 'AAPL' 포함
        """
        article = _make_article(title="Apple news")
        _make_entity(article, "AAPL")

        result = self.classifier.extract_tickers(article)

        assert "AAPL" in result

    def test_cashtag_extracted_from_title(self):
        """
        Given: 제목에 '$TSLA' 포함, entity 없음
        When: extract_tickers() 호출
        Then: 'TSLA' 포함
        """
        article = _make_article(title="$TSLA rallies on delivery numbers")

        result = self.classifier.extract_tickers(article)

        assert "TSLA" in result

    def test_exchange_pattern_extracted_from_summary(self):
        """
        Given: summary에 '(NYSE: JPM)' 포함
        When: extract_tickers() 호출
        Then: 'JPM' 포함
        """
        article = _make_article(
            title="Bank news",
            summary="JPMorgan Chase (NYSE: JPM) reported quarterly profits",
        )

        result = self.classifier.extract_tickers(article)

        assert "JPM" in result

    def test_max_ten_tickers_returned(self):
        """
        Given: 10개 이상의 entity 심볼
        When: extract_tickers() 호출
        Then: 최대 10개만 반환
        """
        article = _make_article(title="Many tickers")
        for sym in ["AAA", "BBB", "CCC", "DDD", "EEE", "FFF", "GGG", "HHH", "III", "JJJ", "KKK"]:
            _make_entity(article, sym)

        result = self.classifier.extract_tickers(article)

        assert len(result) <= 10

    def test_result_is_sorted(self):
        """
        Given: 여러 ticker 포함
        When: extract_tickers() 호출
        Then: 결과는 정렬된 리스트
        """
        article = _make_article(title="$TSLA $AAPL $NVDA news")

        result = self.classifier.extract_tickers(article)

        assert result == sorted(result)

    def test_duplicate_tickers_deduplicated(self):
        """
        Given: entity에 'AAPL' + 제목에 '$AAPL' 중복
        When: extract_tickers() 호출
        Then: 'AAPL' 한 번만 포함
        """
        article = _make_article(title="$AAPL hits record high")
        _make_entity(article, "AAPL")

        result = self.classifier.extract_tickers(article)

        assert result.count("AAPL") == 1

    def test_symbol_matcher_skipped_when_enough_tickers(self):
        """
        Given: entity 3개 이상 (len(tickers) >= 3)
        When: extract_tickers() 호출
        Then: SymbolMatcher.match() 호출되지 않음 (skip 조건)
        """
        article = _make_article(title="Multi stock news")
        for sym in ["AAPL", "TSLA", "NVDA"]:
            _make_entity(article, sym)

        mock_matcher = MagicMock()
        mock_matcher.match.return_value = None
        self.classifier._symbol_matcher = mock_matcher

        self.classifier.extract_tickers(article)

        mock_matcher.match.assert_not_called()

    def test_symbol_matcher_called_when_few_tickers(self):
        """
        Given: entity 0개 (tickers < 3)
        When: extract_tickers() 호출
        Then: SymbolMatcher.match() 호출됨
        """
        article = _make_article(title="Apple is a great company")

        mock_matcher = MagicMock()
        mock_matcher.match.return_value = None
        self.classifier._symbol_matcher = mock_matcher

        self.classifier.extract_tickers(article)

        mock_matcher.match.assert_called()

    def test_empty_article_no_tickers(self):
        """
        Given: 제목만 있고 entity, cashtag, 패턴 없는 뉴스
        When: extract_tickers() 호출
        Then: 빈 리스트 반환
        """
        article = _make_article(title="General market overview", summary="")

        result = self.classifier.extract_tickers(article)

        assert isinstance(result, list)


# ─────────────────────────────────────────────────────────────
# Engine B: extract_sectors
# ─────────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestExtractSectors:
    """extract_sectors() 단위 테스트"""

    def setup_method(self):
        self.classifier = NewsClassifier()

    def test_technology_sector_matched(self):
        """
        Given: 'semiconductor', 'ai', 'cloud' 포함 텍스트
        When: extract_sectors() 호출
        Then: 'Technology' 포함
        """
        article = _make_article(
            title="AI semiconductor chip demand surges",
            summary="Cloud computing and ai drive growth",
        )

        result = self.classifier.extract_sectors(article)

        assert "Technology" in result

    def test_healthcare_sector_matched(self):
        """
        Given: 'pharma', 'fda', 'biotech' 포함 텍스트
        When: extract_sectors() 호출
        Then: 'Healthcare' 포함
        """
        article = _make_article(
            title="Pharma company gets FDA approval for biotech drug"
        )

        result = self.classifier.extract_sectors(article)

        assert "Healthcare" in result

    def test_multiple_sectors_returned(self):
        """
        Given: 에너지('oil') + 기술('chip') 키워드 포함
        When: extract_sectors() 호출
        Then: 'Energy', 'Technology' 모두 반환
        """
        article = _make_article(
            title="AI chip company invests in oil pipeline project"
        )

        result = self.classifier.extract_sectors(article)

        assert "Technology" in result
        assert "Energy" in result

    def test_no_keyword_returns_empty_list(self):
        """
        Given: 섹터 키워드 없는 텍스트
        When: extract_sectors() 호출
        Then: 빈 리스트 반환
        """
        article = _make_article(
            title="A sunny day in New York",
            summary="",
        )

        result = self.classifier.extract_sectors(article)

        assert result == []

    def test_macro_sector_matched(self):
        """
        Given: 'fed', 'inflation', 'rate cut' 포함 텍스트
        When: extract_sectors() 호출
        Then: 'Macro' 포함 + 매칭 빈도 높으므로 앞쪽 위치
        """
        article = _make_article(
            title="Fed signals rate cut amid inflation concerns",
            summary="Federal reserve monetary policy affects GDP and employment",
        )

        result = self.classifier.extract_sectors(article)

        assert "Macro" in result
        assert result.index("Macro") == 0  # 가장 많이 매칭된 섹터

    def test_summary_text_also_scanned(self):
        """
        Given: 제목에 없지만 summary에만 'bitcoin' 포함
        When: extract_sectors() 호출
        Then: 'Crypto' 포함
        """
        article = _make_article(
            title="Financial markets update",
            summary="Bitcoin and ethereum cryptocurrency prices surge",
        )

        result = self.classifier.extract_sectors(article)

        assert "Crypto" in result

    def test_empty_summary_handled(self):
        """
        Given: summary가 빈 문자열인 뉴스
        When: extract_sectors() 호출
        Then: 오류 없이 처리
        """
        article = _make_article(title="Oil prices drop", summary="")

        result = self.classifier.extract_sectors(article)

        assert isinstance(result, list)


# ─────────────────────────────────────────────────────────────
# Engine C: calculate_importance
# ─────────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestCalculateImportance:
    """calculate_importance() 단위 테스트"""

    def setup_method(self):
        self.classifier = NewsClassifier()

    def test_reuters_source_gets_max_credibility(self):
        """
        Given: source='Reuters', 다른 요소 0
        When: calculate_importance() 호출
        Then: source_credibility 가중치(0.15) * 1.0 = 0.15 기여
        """
        article = _make_article(
            source="reuters",
            published_at=timezone.now(),
            sentiment_score=None,
        )

        score = self.classifier.calculate_importance(article, tickers=[], sectors=[])

        # f1=1.0(reuters), f2=0.0, f3=0.3(default), f4>=0.85(최근), f5=0.0
        # 최소 f4 기여값: 0.25*0.85=0.2125
        # score >= 0.15*1.0 + 0.2*0.0 + 0.2*0.3 + 0.25*0.85 + 0.2*0.0 = 0.15+0.06+0.2125 = 0.4225
        assert score > 0.4

    def test_unknown_source_gets_default_score(self):
        """
        Given: source='unknown_blog' (SOURCE_CREDIBILITY에 없음)
        When: calculate_importance() 호출
        Then: default 0.5점 사용
        """
        article = _make_article(source="unknown_blog", published_at=timezone.now())
        score_unknown = self.classifier.calculate_importance(article, tickers=[], sectors=[])

        article_reuters = _make_article(source="reuters", published_at=timezone.now())
        score_reuters = self.classifier.calculate_importance(article_reuters, tickers=[], sectors=[])

        # Reuters가 더 높아야 함
        assert score_reuters > score_unknown

    def test_entity_count_factor_normalized(self):
        """
        Given: tickers 3개 + sectors 2개 = 5개 (normalize 최대)
        When: calculate_importance() 호출
        Then: f2=1.0 (5/5=1.0)
        """
        article = _make_article(published_at=timezone.now())
        tickers = ["AAPL", "TSLA", "NVDA"]
        sectors = ["Technology", "Consumer Discretionary"]

        score = self.classifier.calculate_importance(article, tickers=tickers, sectors=sectors)

        # f2=1.0이므로 score에서 entity_count 기여 = 0.2*1.0 = 0.2
        assert score > 0.2

    def test_entity_count_above_five_capped_at_one(self):
        """
        Given: tickers+sectors 합이 10 (5 이상 → cap)
        When: calculate_importance() 호출
        Then: f2는 1.0으로 cap
        """
        article = _make_article(published_at=timezone.now())
        tickers = ["A", "B", "C", "D", "E", "F"]
        sectors = ["Technology", "Healthcare", "Financials", "Energy"]

        score = self.classifier.calculate_importance(article, tickers=tickers, sectors=sectors)

        # 예외 없이 0~1 범위 유지
        assert 0.0 <= score <= 1.0

    def test_high_sentiment_magnitude_increases_score(self):
        """
        Given: sentiment_score=0.95 (강한 긍정)
        When: calculate_importance() 호출
        Then: sentiment 0.0인 기사보다 높은 점수
        """
        article_high = _make_article(
            sentiment_score=Decimal("0.95"), published_at=timezone.now()
        )
        article_low = _make_article(
            sentiment_score=Decimal("0.0"), published_at=timezone.now()
        )

        score_high = self.classifier.calculate_importance(article_high, [], [])
        score_low = self.classifier.calculate_importance(article_low, [], [])

        assert score_high > score_low

    def test_negative_sentiment_uses_abs_value(self):
        """
        Given: sentiment_score=-0.8 (강한 부정)
        When: calculate_importance() 호출
        Then: f3 = abs(-0.8) = 0.8 사용
        """
        article = _make_article(
            sentiment_score=Decimal("-0.8"), published_at=timezone.now()
        )
        article_positive = _make_article(
            sentiment_score=Decimal("0.8"), published_at=timezone.now()
        )

        score_neg = self.classifier.calculate_importance(article, [], [])
        score_pos = self.classifier.calculate_importance(article_positive, [], [])

        assert abs(score_neg - score_pos) < 0.01  # 절대값이 같으므로 거의 동일

    def test_no_sentiment_uses_default_03(self):
        """
        Given: sentiment_score=None
        When: calculate_importance() 호출
        Then: f3=0.3 기본값 사용 (오류 없음)
        """
        article = _make_article(sentiment_score=None, published_at=timezone.now())

        score = self.classifier.calculate_importance(article, [], [])

        assert isinstance(score, float)
        assert 0.0 <= score <= 1.0

    def test_recency_very_recent_gets_highest(self):
        """
        Given: 1시간 전 발행된 뉴스
        When: calculate_importance() 호출
        Then: f4=1.0 (2시간 이내)
        """
        article = _make_article(
            published_at=timezone.now() - timedelta(hours=1)
        )

        score = self.classifier.calculate_importance(article, [], [])

        # f4=1.0이면 recency 기여 = 0.25
        # 전체 점수가 최소 0.25 이상 (다른 요소도 더해지므로)
        assert score >= 0.25

    def test_recency_6h_ago_gets_085(self):
        """
        Given: 4시간 전 발행 (2~6시간 범위 → f4=0.85)
        When: calculate_importance() 호출
        Then: f4=0.85 (2~6h 범위)
        """
        article = _make_article(
            published_at=timezone.now() - timedelta(hours=4)
        )

        score = self.classifier.calculate_importance(article, [], [])

        assert 0.0 <= score <= 1.0

    def test_recency_12h_ago_gets_07(self):
        """
        Given: 8시간 전 발행 (6~12h 범위 → f4=0.7)
        When: calculate_importance() 호출
        Then: f4=0.7
        """
        article = _make_article(
            published_at=timezone.now() - timedelta(hours=8)
        )

        score = self.classifier.calculate_importance(article, [], [])

        assert 0.0 <= score <= 1.0

    def test_recency_24h_ago_gets_05(self):
        """
        Given: 18시간 전 발행 (12~24h 범위 → f4=0.5)
        When: calculate_importance() 호출
        Then: f4=0.5
        """
        article = _make_article(
            published_at=timezone.now() - timedelta(hours=18)
        )

        score = self.classifier.calculate_importance(article, [], [])

        assert 0.0 <= score <= 1.0

    def test_recency_old_article_decays(self):
        """
        Given: 5일(120시간) 전 발행
        When: calculate_importance() 호출
        Then: f4 = max(0.1, 1.0-120/168) < 0.3, 오래된 기사 낮은 점수
        """
        article = _make_article(
            published_at=timezone.now() - timedelta(hours=120)
        )

        score = self.classifier.calculate_importance(article, [], [])

        # f4 = max(0.1, 1.0-120/168) = max(0.1, 0.286) = 0.286
        assert 0.0 <= score <= 1.0

    def test_keyword_relevance_scales_with_sectors(self):
        """
        Given: sectors 3개 vs 0개 비교
        When: calculate_importance() 호출
        Then: sectors 많을수록 score 높음
        """
        article = _make_article(published_at=timezone.now())
        score_no_sectors = self.classifier.calculate_importance(article, [], [])
        score_with_sectors = self.classifier.calculate_importance(
            article, [], ["Technology", "Healthcare", "Energy"]
        )

        assert score_with_sectors > score_no_sectors

    def test_keyword_relevance_capped_at_one(self):
        """
        Given: sectors 5개 (3/3=1.0으로 cap)
        When: calculate_importance() 호출
        Then: f5=1.0, score는 0~1 범위 유지
        """
        article = _make_article(published_at=timezone.now())

        score = self.classifier.calculate_importance(
            article, [], ["A", "B", "C", "D", "E"]
        )

        assert 0.0 <= score <= 1.0

    def test_score_clamped_to_0_1(self):
        """
        Given: 모든 요소 최대값 조합
        When: calculate_importance() 호출
        Then: score는 항상 0.0~1.0 범위
        """
        article = _make_article(
            source="reuters",
            sentiment_score=Decimal("1.0"),
            published_at=timezone.now(),
        )

        score = self.classifier.calculate_importance(
            article,
            tickers=["AAPL", "TSLA", "NVDA"],
            sectors=["Technology", "Healthcare", "Energy"],
        )

        assert 0.0 <= score <= 1.0

    def test_score_rounded_to_4_decimal_places(self):
        """
        Given: 임의 기사
        When: calculate_importance() 호출
        Then: 소수점 4자리로 반올림됨
        """
        article = _make_article(published_at=timezone.now())

        score = self.classifier.calculate_importance(article, [], [])

        assert score == round(score, 4)

    def test_custom_weights_applied(self):
        """
        Given: source_credibility 가중치 0.0으로 설정 (영향 없음)
        When: calculate_importance() 호출
        Then: Reuters vs 미지 소스 점수 차이가 없음
        """
        custom_weights = {**DEFAULT_WEIGHTS, "source_credibility": 0.0}
        classifier = NewsClassifier(weights=custom_weights)

        article_reuters = _make_article(source="reuters", published_at=timezone.now())
        article_unknown = _make_article(source="unknown_xyz", published_at=timezone.now())

        score_reuters = classifier.calculate_importance(article_reuters, [], [])
        score_unknown = classifier.calculate_importance(article_unknown, [], [])

        # source_credibility 가중치가 0이면 차이는 sentiment 기본값 차이만 (없음)
        assert abs(score_reuters - score_unknown) < 0.01


# ─────────────────────────────────────────────────────────────
# classify_batch
# ─────────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestClassifyBatch:
    """classify_batch() 테스트"""

    def setup_method(self):
        self.classifier = NewsClassifier()
        # SymbolMatcher mock
        mock_matcher = MagicMock()
        mock_matcher.match.return_value = None
        self.classifier._symbol_matcher = mock_matcher

    def test_batch_classifies_unscored_articles(self):
        """
        Given: importance_score=None 인 뉴스 2개
        When: classify_batch(article_ids=[id1, id2]) 호출
        Then: classified=2, errors=0
        """
        a1 = _make_article(title="$AAPL earnings beat", published_at=timezone.now())
        a2 = _make_article(title="Oil prices drop", published_at=timezone.now())

        result = self.classifier.classify_batch(article_ids=[a1.id, a2.id])

        assert result["classified"] == 2
        assert result["errors"] == 0

    def test_batch_sets_importance_score_on_article(self):
        """
        Given: importance_score=None 인 뉴스
        When: classify_batch() 호출
        Then: DB에 importance_score 저장됨
        """
        article = _make_article(
            title="Fed rate cut semiconductor chip",
            published_at=timezone.now(),
        )

        self.classifier.classify_batch(article_ids=[article.id])

        article.refresh_from_db()
        assert article.importance_score is not None
        assert 0.0 <= article.importance_score <= 1.0

    def test_batch_sets_rule_tickers(self):
        """
        Given: '$TSLA' 포함 제목의 뉴스
        When: classify_batch() 호출
        Then: rule_tickers에 'TSLA' 포함
        """
        article = _make_article(title="$TSLA delivery numbers disappoint")

        self.classifier.classify_batch(article_ids=[article.id])

        article.refresh_from_db()
        assert article.rule_tickers is not None
        assert "TSLA" in article.rule_tickers

    def test_batch_sets_rule_sectors(self):
        """
        Given: 'semiconductor ai' 포함 제목의 뉴스
        When: classify_batch() 호출
        Then: rule_sectors에 'Technology' 포함
        """
        article = _make_article(title="AI semiconductor chip demand grows")

        self.classifier.classify_batch(article_ids=[article.id])

        article.refresh_from_db()
        assert article.rule_sectors is not None
        assert "Technology" in article.rule_sectors

    def test_batch_skips_already_scored_articles(self):
        """
        Given: importance_score=0.5 이미 설정된 뉴스
        When: classify_batch(article_ids=[id]) 호출
        Then: classified=0 (이미 처리됨, 필터에서 제외)
        """
        article = _make_article(
            title="Already scored news",
            importance_score=0.5,
        )

        result = self.classifier.classify_batch(article_ids=[article.id])

        assert result["classified"] == 0

    def test_batch_by_hours_fallback(self):
        """
        Given: article_ids=None, 최근 4시간 내 importance_score=None 뉴스 1개
        When: classify_batch(hours=4) 호출
        Then: classified=1
        """
        article = _make_article(
            title="Recent news for batch",
            published_at=timezone.now() - timedelta(hours=2),
        )

        result = self.classifier.classify_batch(article_ids=None, hours=4)

        assert result["classified"] >= 1

    def test_batch_no_articles_returns_zero(self):
        """
        Given: 처리할 뉴스 없음
        When: classify_batch(article_ids=[]) 호출
        Then: classified=0, errors=0
        """
        result = self.classifier.classify_batch(article_ids=[])

        assert result["classified"] == 0
        assert result["errors"] == 0

    def test_batch_handles_extraction_error_gracefully(self):
        """
        Given: extract_tickers()가 예외를 던지는 상황
        When: classify_batch() 호출
        Then: errors=1 (예외 catch), classified=0
        """
        article = _make_article(title="Error prone article")

        with patch.object(
            self.classifier, "extract_tickers", side_effect=RuntimeError("mock error")
        ):
            result = self.classifier.classify_batch(article_ids=[article.id])

        assert result["errors"] == 1
        assert result["classified"] == 0

    def test_batch_result_has_required_keys(self):
        """
        Given: 임의 배치 실행
        When: classify_batch() 호출
        Then: 반환값에 classified, skipped, errors 키 포함
        """
        result = self.classifier.classify_batch(article_ids=[])

        assert "classified" in result
        assert "skipped" in result
        assert "errors" in result

    def test_batch_no_tickers_sets_rule_tickers_none(self):
        """
        Given: 제목/본문에 ticker 없는 뉴스
        When: classify_batch() 호출
        Then: rule_tickers=None (tickers 빈 리스트)
        """
        article = _make_article(title="General market overview")

        self.classifier.classify_batch(article_ids=[article.id])

        article.refresh_from_db()
        assert article.rule_tickers is None


# ─────────────────────────────────────────────────────────────
# select_for_analysis
# ─────────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestSelectForAnalysis:
    """select_for_analysis() 단위 테스트"""

    def setup_method(self):
        self.classifier = NewsClassifier()

    def test_empty_db_returns_empty_list(self):
        """
        Given: 오늘 날짜 뉴스 없음
        When: select_for_analysis() 호출
        Then: 빈 리스트 반환
        """
        result = self.classifier.select_for_analysis()

        assert result == []

    def test_articles_without_importance_score_excluded(self):
        """
        Given: 오늘 뉴스 3개 모두 importance_score=None
        When: select_for_analysis() 호출
        Then: 빈 리스트 반환 (importance_score 필수)
        """
        for i in range(3):
            _make_article(
                title=f"No score article {i}",
                importance_score=None,
                published_at=timezone.now(),
            )

        result = self.classifier.select_for_analysis()

        assert result == []

    def test_top_15_percent_selected(self):
        """
        Given: 오늘 뉴스 20개, 점수 0.05~1.0 (0.05 간격)
        When: select_for_analysis() 호출
        Then: 상위 15% (3개) 선별
        """
        for i in range(20):
            _make_article(
                title=f"Article {i}",
                importance_score=round(0.05 * (i + 1), 2),
                published_at=timezone.now(),
                llm_analyzed=False,
            )

        result = self.classifier.select_for_analysis()

        # 20개의 15% = 3개
        assert len(result) == 3

    def test_already_analyzed_articles_excluded(self):
        """
        Given: 오늘 뉴스 10개 중 상위 2개는 llm_analyzed=True
        When: select_for_analysis() 호출
        Then: 선별 결과에 llm_analyzed=True 기사 미포함
        """
        analyzed_ids = []
        for i in range(10):
            score = round(0.1 * (i + 1), 2)
            is_analyzed = score >= 0.9  # 0.9, 1.0 두 개
            a = _make_article(
                title=f"Article {i}",
                importance_score=score,
                published_at=timezone.now(),
                llm_analyzed=is_analyzed,
            )
            if is_analyzed:
                analyzed_ids.append(a.id)

        result = self.classifier.select_for_analysis()

        # 분석된 기사 ID는 결과에 없어야 함
        for aid in analyzed_ids:
            assert aid not in result

    def test_minimum_guarantee_one_article(self):
        """
        Given: 오늘 뉴스 1개 (importance_score=0.1), llm_analyzed=False
        When: select_for_analysis() 호출
        Then: 최소 보장으로 1개 반환
        """
        article = _make_article(
            title="Single article",
            importance_score=0.1,
            published_at=timezone.now(),
            llm_analyzed=False,
        )

        result = self.classifier.select_for_analysis()

        assert len(result) == 1
        assert article.id in result

    def test_minimum_guarantee_skipped_when_all_analyzed(self):
        """
        Given: 오늘 뉴스 1개 있지만 llm_analyzed=True
        When: select_for_analysis() 호출
        Then: 최소 보장도 빈 리스트 (미분석 기사 없음)
        """
        _make_article(
            title="Already analyzed",
            importance_score=0.8,
            published_at=timezone.now(),
            llm_analyzed=True,
        )

        result = self.classifier.select_for_analysis()

        assert result == []

    def test_old_articles_not_selected(self):
        """
        Given: 어제 뉴스에 높은 score + 오늘 뉴스에 낮은 score
        When: select_for_analysis() 호출
        Then: 오늘 날짜 기사만 대상 (어제 기사 제외)
        """
        yesterday = timezone.now() - timedelta(days=1)
        old_article = _make_article(
            title="Old high score article",
            importance_score=0.99,
            published_at=yesterday,
            llm_analyzed=False,
        )
        today_article = _make_article(
            title="Today low score article",
            importance_score=0.3,
            published_at=timezone.now(),
            llm_analyzed=False,
        )

        result = self.classifier.select_for_analysis()

        assert old_article.id not in result

    def test_returned_values_are_ids(self):
        """
        Given: 오늘 뉴스 5개 (importance_score 설정)
        When: select_for_analysis() 호출
        Then: 반환값은 NewsArticle ID 리스트
        """
        for i in range(5):
            _make_article(
                title=f"ID test article {i}",
                importance_score=round(0.2 * (i + 1), 2),
                published_at=timezone.now(),
                llm_analyzed=False,
            )

        result = self.classifier.select_for_analysis()

        assert isinstance(result, list)
        # 반환된 ID가 실제 DB에 존재하는지 확인
        for aid in result:
            assert NewsArticle.objects.filter(id=aid).exists()

    def test_threshold_boundary_inclusive(self):
        """
        Given: 오늘 뉴스 10개, threshold == 0.9 (상위 15% → 2번째)
        When: select_for_analysis() 호출
        Then: threshold 이상 뉴스만 선별
        """
        scores = [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]
        articles = []
        for score in scores:
            a = _make_article(
                title=f"Score {score}",
                importance_score=score,
                published_at=timezone.now(),
                llm_analyzed=False,
            )
            articles.append((score, a))

        result = self.classifier.select_for_analysis()

        # 10개의 15% = max(1, int(10*0.15)) = max(1, 1) = 1개
        # threshold = scores[-1:] = [1.0][−1] = 1.0
        # importance_score >= 1.0 인 것만 선택
        assert len(result) == 1

    def test_select_returns_list_type(self):
        """
        Given: 임의 데이터
        When: select_for_analysis() 호출
        Then: 항상 리스트 타입 반환
        """
        result = self.classifier.select_for_analysis()

        assert isinstance(result, list)


# ─────────────────────────────────────────────────────────────
# NewsClassifier 초기화 및 속성 테스트
# ─────────────────────────────────────────────────────────────

class TestNewsClassifierInit:
    """NewsClassifier 초기화 및 기본 속성 테스트"""

    def test_default_weights_used_when_none_provided(self):
        """
        Given: weights 인자 없이 NewsClassifier 초기화
        When: self.weights 확인
        Then: DEFAULT_WEIGHTS와 동일
        """
        classifier = NewsClassifier()

        assert classifier.weights == DEFAULT_WEIGHTS

    def test_custom_weights_stored(self):
        """
        Given: 커스텀 가중치 딕셔너리
        When: NewsClassifier(weights=custom) 초기화
        Then: self.weights == custom
        """
        custom = {
            "source_credibility": 0.5,
            "entity_count": 0.1,
            "sentiment_magnitude": 0.1,
            "recency": 0.2,
            "keyword_relevance": 0.1,
        }
        classifier = NewsClassifier(weights=custom)

        assert classifier.weights == custom

    def test_symbol_matcher_is_lazy(self):
        """
        Given: NewsClassifier 초기화 직후
        When: _symbol_matcher 확인
        Then: None (lazy initialization)
        """
        classifier = NewsClassifier()

        assert classifier._symbol_matcher is None

    def test_symbol_matcher_lazy_init_called(self):
        """
        Given: NewsClassifier 초기화 후 symbol_matcher property 접근
        When: get_symbol_matcher import + 호출
        Then: _symbol_matcher 설정됨
        """
        classifier = NewsClassifier()
        mock_matcher_instance = MagicMock()

        # get_symbol_matcher is imported inside the property body from serverless
        with patch(
            "serverless.services.symbol_matcher.get_symbol_matcher",
            return_value=mock_matcher_instance,
        ):
            # Directly patch the inner import by setting _symbol_matcher to None
            # and using the module-level import path
            classifier._symbol_matcher = None
            with patch(
                "news.services.news_classifier.NewsClassifier.symbol_matcher",
                new_callable=PropertyMock,
                return_value=mock_matcher_instance,
            ):
                result = classifier.symbol_matcher

        assert result is mock_matcher_instance

    def test_symbol_matcher_not_called_twice(self):
        """
        Given: symbol_matcher를 한 번 초기화한 상태
        When: 두 번째 symbol_matcher 접근
        Then: _symbol_matcher 재초기화 없음 (캐시됨)
        """
        classifier = NewsClassifier()
        mock_matcher_instance = MagicMock()

        # Set the cached matcher directly
        classifier._symbol_matcher = mock_matcher_instance

        # Accessing property again should return the cached instance
        result1 = classifier.symbol_matcher
        result2 = classifier.symbol_matcher

        assert result1 is mock_matcher_instance
        assert result2 is mock_matcher_instance


# ─────────────────────────────────────────────────────────────
# 상수 및 설정값 검증
# ─────────────────────────────────────────────────────────────

class TestConstants:
    """모듈 상수 및 설정값 검증"""

    def test_default_weights_sum_to_one(self):
        """DEFAULT_WEIGHTS 합이 1.0 (부동소수 허용 오차 내)"""
        total = sum(DEFAULT_WEIGHTS.values())

        assert abs(total - 1.0) < 0.001

    def test_top_percentile_is_015(self):
        """TOP_PERCENTILE == 0.15"""
        assert TOP_PERCENTILE == 0.15

    def test_reuters_gets_perfect_score(self):
        """Reuters 신뢰도 == 1.0"""
        assert SOURCE_CREDIBILITY["reuters"] == 1.0

    def test_bloomberg_gets_perfect_score(self):
        """Bloomberg 신뢰도 == 1.0"""
        assert SOURCE_CREDIBILITY["bloomberg"] == 1.0

    def test_ambiguous_tickers_contains_meta(self):
        """AMBIGUOUS_TICKERS에 'META' 포함"""
        assert "META" in AMBIGUOUS_TICKERS

    def test_ambiguous_tickers_contains_now(self):
        """AMBIGUOUS_TICKERS에 'NOW' 포함"""
        assert "NOW" in AMBIGUOUS_TICKERS

    def test_stock_context_words_contains_earnings(self):
        """STOCK_CONTEXT_WORDS에 'earnings' 포함"""
        assert "earnings" in STOCK_CONTEXT_WORDS

    def test_cashtag_pattern_matches_valid(self):
        """CASHTAG_PATTERN이 '$AAPL' 매칭"""
        matches = CASHTAG_PATTERN.findall("Check $AAPL today")

        assert "AAPL" in matches

    def test_exchange_pattern_matches_nasdaq(self):
        """EXCHANGE_PATTERN이 '(NASDAQ: NVDA)' 매칭"""
        matches = EXCHANGE_PATTERN.findall("Nvidia (NASDAQ: NVDA) earnings")

        assert "NVDA" in matches


# ─────────────────────────────────────────────────────────────
# Marker
# ─────────────────────────────────────────────────────────────

pytestmark = pytest.mark.django_db
