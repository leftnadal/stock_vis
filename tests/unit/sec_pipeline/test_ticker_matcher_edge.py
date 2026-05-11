"""
TickerMatcher 추가 엣지 케이스 테스트.

기존 test_ticker_matcher.py / test_ticker_matcher_advanced.py 에서 누락된 영역:
- _clean_name 의 PLC / Limited / Group / S.A. / N.V. / Company 접미사
- match: short_name 시 method=None 반환
- _match_alias: context_sector specific 이 generic 보다 우선
- _ensure_loaded: stock_name 이 None 인 Stock 은 스킵

DB 접근 필요 — @pytest.mark.django_db.
"""

import pytest
from unittest.mock import patch

from sec_pipeline.ticker_matcher import TickerMatcher


@pytest.fixture
def matcher():
    m = TickerMatcher()
    m._loaded = False
    m._stock_map = {}
    return m


# ---------------------------------------------------------------------------
# Tests: _clean_name — 추가 접미사
# ---------------------------------------------------------------------------

class TestCleanNameSuffixes:
    def test_removes_plc(self):
        assert TickerMatcher._clean_name('BP PLC') == 'bp'

    def test_removes_limited(self):
        assert TickerMatcher._clean_name('Acme Limited') == 'acme'

    def test_removes_group(self):
        assert TickerMatcher._clean_name('Alibaba Group') == 'alibaba'

    def test_removes_company(self):
        assert TickerMatcher._clean_name('3M Company') == '3m'

    def test_removes_sa(self):
        assert TickerMatcher._clean_name('Sanofi S.A.') == 'sanofi'

    def test_removes_nv(self):
        assert TickerMatcher._clean_name('Philips N.V.') == 'philips'

    def test_case_insensitive_inc_match(self):
        """대소문자 무관하게 INC 접미사 제거."""
        assert TickerMatcher._clean_name('Apple INC.') == 'apple'

    def test_handles_comma_before_suffix(self):
        """', Inc.' 형태도 정상 제거."""
        assert TickerMatcher._clean_name('Apple, Inc.') == 'apple'


# ---------------------------------------------------------------------------
# Tests: match — short name & 1-character name
# ---------------------------------------------------------------------------

class TestMatchShortName:
    def test_one_char_name_returns_none(self, matcher):
        """1글자 회사명은 매칭 시도 안 함."""
        ticker, method = matcher.match('X')
        assert ticker is None
        assert method is None

    def test_whitespace_only_name_returns_none(self, matcher):
        """공백만 있는 이름은 strip 후 빈 문자열, 즉 매칭 안 됨.

        Note: '' 는 len < 2 분기에 걸려 early return,
              ' ' 는 strip 후 빈 문자열이 되어 다음 단계 진입.
              따라서 mocking 없이도 안전하게 None 반환 확인.
        """
        # 매칭 단계가 호출되지 않도록 모킹
        with patch.object(TickerMatcher, '_match_alias', return_value=None), \
             patch.object(TickerMatcher, '_ensure_loaded'), \
             patch.object(TickerMatcher, '_match_exact', return_value=None), \
             patch.object(TickerMatcher, '_match_fuzzy', return_value=(None, 0)):
            ticker, method = matcher.match('   ')
            assert ticker is None


# ---------------------------------------------------------------------------
# Tests: _match_alias — sector specific 우선
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestMatchAliasPriority:
    def test_sector_specific_wins_over_generic(self, matcher):
        """동일 alias 가 sector-specific 과 generic 둘 다 있으면 sector-specific 이 선택."""
        from sec_pipeline.models import CompanyAlias
        CompanyAlias.objects.create(
            alias='Apex', ticker='APX_GENERIC', context_sector='',
        )
        CompanyAlias.objects.create(
            alias='Apex', ticker='APX_TECH', context_sector='Technology',
        )
        result = matcher._match_alias('Apex', 'Technology')
        assert result == 'APX_TECH'

    def test_unrelated_sector_falls_back_to_generic(self, matcher):
        """sector specific 이 매칭 안 되면 generic 으로 fallback."""
        from sec_pipeline.models import CompanyAlias
        CompanyAlias.objects.create(
            alias='Apex', ticker='APX_GENERIC', context_sector='',
        )
        CompanyAlias.objects.create(
            alias='Apex', ticker='APX_TECH', context_sector='Technology',
        )
        # Healthcare 섹터는 등록되어있지 않음 → generic 사용
        result = matcher._match_alias('Apex', 'Healthcare')
        assert result == 'APX_GENERIC'


# ---------------------------------------------------------------------------
# Tests: _ensure_loaded — name 이 None / 빈 문자열인 Stock
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestEnsureLoadedNullName:
    def test_skips_stock_without_name(self, matcher):
        """stock_name 이 빈 문자열인 Stock 은 _stock_map 에 추가되지 않는다."""
        from stocks.models import Stock
        Stock.objects.create(symbol='ZZZ', stock_name='')
        Stock.objects.create(symbol='AAPL', stock_name='Apple Inc.')

        matcher._ensure_loaded()
        # ZZZ (이름 없음) 는 stock_map 에 없어야 함
        assert all(v != 'ZZZ' for v in matcher._stock_map.values())
        assert any(v == 'AAPL' for v in matcher._stock_map.values())


# ---------------------------------------------------------------------------
# Tests: _get_fuzzy_candidates — 추가
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestGetFuzzyCandidatesEdge:
    def test_empty_stock_table_returns_empty(self, matcher):
        """Stock 테이블이 비어있으면 빈 후보 리스트 반환."""
        result = matcher._get_fuzzy_candidates('Apple', top_k=5)
        assert result == []

    def test_score_normalized_0_to_1(self, matcher):
        """모든 후보의 score 는 0~1 범위."""
        from stocks.models import Stock
        Stock.objects.create(symbol='AAPL', stock_name='Apple Inc.')
        result = matcher._get_fuzzy_candidates('Apple', top_k=5)
        for c in result:
            assert 0.0 <= c['score'] <= 1.0
