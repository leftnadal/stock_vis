"""
TickerMatcher 단위 테스트.

DB 접근은 @pytest.mark.django_db. rapidfuzz는 실제 사용 (순수 함수).
"""

import pytest
from unittest.mock import patch, MagicMock

from sec_pipeline.ticker_matcher import TickerMatcher


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def matcher():
    m = TickerMatcher()
    m._loaded = False
    m._stock_map = {}
    return m


# ---------------------------------------------------------------------------
# Tests: _clean_name
# ---------------------------------------------------------------------------

class TestCleanName:
    def test_removes_inc(self):
        assert TickerMatcher._clean_name('Apple Inc.') == 'apple'

    def test_removes_corporation(self):
        assert TickerMatcher._clean_name('Microsoft Corporation') == 'microsoft'

    def test_removes_corp(self):
        assert TickerMatcher._clean_name('Tesla Corp') == 'tesla'

    def test_removes_ltd(self):
        assert TickerMatcher._clean_name('Samsung Ltd.') == 'samsung'

    def test_removes_llc(self):
        assert TickerMatcher._clean_name('Acme LLC') == 'acme'

    def test_no_suffix(self):
        assert TickerMatcher._clean_name('Google') == 'google'

    def test_empty_string(self):
        assert TickerMatcher._clean_name('') == ''


# ---------------------------------------------------------------------------
# Tests: match (unit — DB mocked)
# ---------------------------------------------------------------------------

class TestMatch:
    def test_empty_name(self, matcher):
        ticker, method = matcher.match('')
        assert ticker is None
        assert method is None

    def test_short_name(self, matcher):
        ticker, method = matcher.match('A')
        assert ticker is None

    @patch.object(TickerMatcher, '_match_alias', return_value='AAPL')
    def test_alias_match(self, mock_alias, matcher):
        ticker, method = matcher.match('Apple Inc.')
        assert ticker == 'AAPL'
        assert method == 'alias'

    @patch.object(TickerMatcher, '_match_alias', return_value=None)
    @patch.object(TickerMatcher, '_ensure_loaded')
    @patch.object(TickerMatcher, '_match_exact', return_value='MSFT')
    def test_exact_match(self, mock_exact, mock_load, mock_alias, matcher):
        ticker, method = matcher.match('Microsoft')
        assert ticker == 'MSFT'
        assert method == 'exact'

    @patch.object(TickerMatcher, '_match_alias', return_value=None)
    @patch.object(TickerMatcher, '_ensure_loaded')
    @patch.object(TickerMatcher, '_match_exact', return_value=None)
    @patch.object(TickerMatcher, '_match_fuzzy', return_value=('TSLA', 92))
    def test_fuzzy_match(self, mock_fuzzy, mock_exact, mock_load, mock_alias, matcher):
        ticker, method = matcher.match('Tesla Motors')
        assert ticker == 'TSLA'
        assert method == 'fuzzy'

    @patch.object(TickerMatcher, '_match_alias', return_value=None)
    @patch.object(TickerMatcher, '_ensure_loaded')
    @patch.object(TickerMatcher, '_match_exact', return_value=None)
    @patch.object(TickerMatcher, '_match_fuzzy', return_value=(None, 40))
    def test_no_match(self, mock_fuzzy, mock_exact, mock_load, mock_alias, matcher):
        ticker, method = matcher.match('Some Random Company XYZ')
        assert ticker is None
        assert method is None


# ---------------------------------------------------------------------------
# Tests: _match_exact
# ---------------------------------------------------------------------------

class TestMatchExact:
    def test_exact_lowercase(self, matcher):
        matcher._stock_map = {'apple inc.': 'AAPL', 'microsoft': 'MSFT'}
        matcher._loaded = True
        assert matcher._match_exact('Apple Inc.') == 'AAPL'

    def test_cleaned_name_match(self, matcher):
        matcher._stock_map = {'apple': 'AAPL'}
        matcher._loaded = True
        assert matcher._match_exact('Apple Inc.') == 'AAPL'

    def test_no_match(self, matcher):
        matcher._stock_map = {'apple': 'AAPL'}
        matcher._loaded = True
        assert matcher._match_exact('Unknown Company') is None


# ---------------------------------------------------------------------------
# Tests: _match_fuzzy
# ---------------------------------------------------------------------------

class TestMatchFuzzy:
    def test_fuzzy_above_threshold(self, matcher):
        # _match_fuzzy iterates _stock_map as {name: symbol}
        matcher._stock_map = {
            'apple inc': 'AAPL',
            'microsoft corporation': 'MSFT',
        }
        matcher._loaded = True
        # "apple inc" 와 "apple inc." 는 거의 동일
        ticker, score = matcher._match_fuzzy('apple inc.', threshold=70)
        assert ticker == 'AAPL'
        assert score >= 70

    def test_fuzzy_below_threshold(self, matcher):
        matcher._stock_map = {'apple inc': 'AAPL'}
        matcher._loaded = True
        ticker, score = matcher._match_fuzzy('zzz completely different xyz', threshold=80)
        assert ticker is None
