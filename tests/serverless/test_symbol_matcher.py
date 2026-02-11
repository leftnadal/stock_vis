"""
SymbolMatcher Tests (Phase 5)

회사명 → 티커 심볼 매칭 서비스 테스트
"""
import pytest
from unittest.mock import patch, MagicMock
from serverless.services.symbol_matcher import (
    SymbolMatcher,
    get_symbol_matcher,
)


class TestSymbolMatcher:
    """SymbolMatcher 테스트"""

    @pytest.fixture
    def matcher(self):
        """SymbolMatcher 인스턴스"""
        return SymbolMatcher()

    # ========================================
    # Hardcoded Mapping Tests
    # ========================================

    def test_match_apple(self, matcher):
        """Apple 매칭"""
        assert matcher.match("Apple") == "AAPL"
        assert matcher.match("apple") == "AAPL"
        assert matcher.match("Apple Inc.") == "AAPL"
        assert matcher.match("APPLE INC") == "AAPL"

    def test_match_microsoft(self, matcher):
        """Microsoft 매칭"""
        assert matcher.match("Microsoft") == "MSFT"
        assert matcher.match("Microsoft Corp") == "MSFT"
        assert matcher.match("Microsoft Corporation") == "MSFT"

    def test_match_google(self, matcher):
        """Google/Alphabet 매칭"""
        assert matcher.match("Google") == "GOOGL"
        assert matcher.match("Alphabet") == "GOOGL"
        assert matcher.match("Alphabet Inc") == "GOOGL"

    def test_match_amazon(self, matcher):
        """Amazon 매칭"""
        assert matcher.match("Amazon") == "AMZN"
        # Amazon.com 형태는 정규화 후 매칭
        assert matcher.match("Amazon Inc") == "AMZN"

    def test_match_meta(self, matcher):
        """Meta/Facebook 매칭"""
        assert matcher.match("Meta") == "META"
        assert matcher.match("Meta Platforms") == "META"
        assert matcher.match("Facebook") == "META"

    def test_match_nvidia(self, matcher):
        """NVIDIA 매칭"""
        assert matcher.match("NVIDIA") == "NVDA"
        assert matcher.match("nvidia") == "NVDA"
        assert matcher.match("Nvidia Corp") == "NVDA"

    def test_match_tesla(self, matcher):
        """Tesla 매칭"""
        assert matcher.match("Tesla") == "TSLA"
        assert matcher.match("Tesla Inc") == "TSLA"
        assert matcher.match("Tesla Motors") == "TSLA"

    def test_match_tsmc(self, matcher):
        """TSMC 매칭"""
        assert matcher.match("TSMC") == "TSM"
        assert matcher.match("Taiwan Semiconductor") == "TSM"
        assert matcher.match("Taiwan Semiconductor Manufacturing") == "TSM"

    def test_match_finance(self, matcher):
        """금융 회사 매칭"""
        assert matcher.match("JPMorgan") == "JPM"
        assert matcher.match("JP Morgan") == "JPM"
        assert matcher.match("Goldman Sachs") == "GS"
        assert matcher.match("Bank of America") == "BAC"

    def test_match_pharma(self, matcher):
        """제약 회사 매칭"""
        assert matcher.match("Pfizer") == "PFE"
        assert matcher.match("Moderna") == "MRNA"
        assert matcher.match("Eli Lilly") == "LLY"

    def test_match_gaming(self, matcher):
        """게임 회사 매칭"""
        assert matcher.match("Activision") == "ATVI"
        assert matcher.match("Activision Blizzard") == "ATVI"
        assert matcher.match("Electronic Arts") == "EA"

    # ========================================
    # Normalization Tests
    # ========================================

    def test_normalize_suffix_removal(self, matcher):
        """접미사 제거 테스트"""
        # Inc., Corp., Ltd. 등 제거
        normalized = matcher._normalize_name("Apple Inc.")
        assert 'inc' not in normalized

        normalized = matcher._normalize_name("Microsoft Corporation")
        assert 'corporation' not in normalized

    def test_normalize_case_insensitive(self, matcher):
        """대소문자 무시"""
        assert matcher._normalize_name("APPLE") == matcher._normalize_name("apple")
        assert matcher._normalize_name("Microsoft") == matcher._normalize_name("MICROSOFT")

    def test_normalize_whitespace(self, matcher):
        """공백 정리"""
        normalized = matcher._normalize_name("  Apple   Inc  ")
        assert '  ' not in normalized
        assert normalized.strip() == normalized

    # ========================================
    # Edge Cases
    # ========================================

    def test_match_empty(self, matcher):
        """빈 문자열"""
        assert matcher.match("") is None
        assert matcher.match(None) is None

    def test_match_short(self, matcher):
        """너무 짧은 문자열"""
        assert matcher.match("A") is None

    def test_match_unknown(self, matcher):
        """알 수 없는 회사"""
        # 캐시를 건드리지 않도록 mock 사용
        with patch.object(matcher, '_match_from_db_exact', return_value=None):
            with patch.object(matcher, '_match_from_db_partial', return_value=None):
                # 하드코딩에 없고 DB에도 없는 경우
                result = matcher.match("UnknownCompanyXYZ123")
                # 캐시에 __NOT_FOUND__ 저장되어 None 반환
                assert result is None

    # ========================================
    # Batch Match Tests
    # ========================================

    def test_match_batch(self, matcher):
        """배치 매칭 테스트"""
        companies = ["Apple", "Microsoft", "NVIDIA"]
        results = matcher.match_batch(companies)

        assert results["Apple"] == "AAPL"
        assert results["Microsoft"] == "MSFT"
        assert results["NVIDIA"] == "NVDA"

    def test_match_batch_partial(self, matcher):
        """부분 매칭 배치 테스트"""
        companies = ["Apple", "UnknownCompany123"]

        with patch.object(matcher, '_match_from_db_exact', return_value=None):
            with patch.object(matcher, '_match_from_db_partial', return_value=None):
                results = matcher.match_batch(companies)

        assert results["Apple"] == "AAPL"
        assert results["UnknownCompany123"] is None

    def test_match_batch_empty(self, matcher):
        """빈 배치"""
        results = matcher.match_batch([])
        assert results == {}

    # ========================================
    # Confidence Tests
    # ========================================

    @pytest.mark.skip(reason="Stock model schema varies")
    @pytest.mark.django_db
    def test_get_match_confidence_db_hit(self, matcher):
        """DB에 있는 종목의 신뢰도"""
        pass

    def test_get_match_confidence_no_db(self, matcher):
        """DB에 없는 종목의 신뢰도"""
        from stocks.models import Stock
        with patch.object(Stock.objects, 'get') as mock_get:
            mock_get.side_effect = Stock.DoesNotExist()
            confidence = matcher.get_match_confidence("Unknown", "XXX")
            assert confidence == 0.5

    # ========================================
    # Singleton Tests
    # ========================================

    def test_singleton(self):
        """싱글톤 인스턴스 테스트"""
        matcher1 = get_symbol_matcher()
        matcher2 = get_symbol_matcher()
        assert matcher1 is matcher2


class TestSymbolMatcherDB:
    """DB 연동 테스트 (pytest.mark.django_db 필요)"""

    @pytest.fixture
    def matcher(self):
        return SymbolMatcher()

    @pytest.mark.skip(reason="Stock model schema varies - company_name field used")
    @pytest.mark.django_db
    def test_match_from_db_exact(self, matcher):
        """DB 정확 매칭"""
        pass

    @pytest.mark.skip(reason="Stock model schema varies - company_name field used")
    @pytest.mark.django_db
    def test_match_from_db_ticker_input(self, matcher):
        """티커 심볼 입력시 직접 매칭"""
        pass

    @pytest.mark.skip(reason="Stock model schema varies - company_name field used")
    @pytest.mark.django_db
    def test_match_from_db_partial(self, matcher):
        """DB 부분 매칭"""
        pass
