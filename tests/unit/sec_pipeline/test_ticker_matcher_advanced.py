"""
TickerMatcher 추가 단위 테스트.

기존 test_ticker_matcher.py에서 누락된 영역:
- _match_alias (CompanyAlias 테이블 조회 — context_sector 우선/범용 fallback)
- _ensure_loaded (Stock 캐시 로드, idempotent)
- _get_fuzzy_candidates (top_k, threshold 필터)
- match_with_queue (성공: target_company 업데이트, 실패: 큐 적재 + occurrence_count 증가)

DB 접근 필요 — @pytest.mark.django_db.
"""

import pytest
from unittest.mock import patch, MagicMock

from sec_pipeline.ticker_matcher import TickerMatcher


@pytest.fixture
def matcher():
    m = TickerMatcher()
    m._loaded = False
    m._stock_map = {}
    return m


# ---------------------------------------------------------------------------
# Tests: _match_alias
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestMatchAlias:
    def test_alias_with_sector_match(self, matcher):
        from sec_pipeline.models import CompanyAlias
        CompanyAlias.objects.create(
            alias='Taiwan Semi', ticker='TSM',
            context_sector='Technology', source='manual_seed',
        )
        result = matcher._match_alias('Taiwan Semi', 'Technology')
        assert result == 'TSM'

    def test_alias_falls_back_to_generic(self, matcher):
        """sector-specific alias 없으면 context_sector='' 항목 조회."""
        from sec_pipeline.models import CompanyAlias
        CompanyAlias.objects.create(
            alias='Samsung', ticker='SSNLF', context_sector='',
            source='manual_seed',
        )
        # context_sector를 줘도 generic으로 fallback
        result = matcher._match_alias('Samsung', 'Technology')
        assert result == 'SSNLF'

    def test_alias_case_insensitive(self, matcher):
        from sec_pipeline.models import CompanyAlias
        CompanyAlias.objects.create(
            alias='Taiwan Semi', ticker='TSM', context_sector='',
        )
        result = matcher._match_alias('taiwan semi', '')
        assert result == 'TSM'

    def test_alias_no_match_returns_none(self, matcher):
        result = matcher._match_alias('Unknown Co', 'Technology')
        assert result is None


# ---------------------------------------------------------------------------
# Tests: _ensure_loaded
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestEnsureLoaded:
    def test_loads_stocks_into_map(self, matcher):
        from stocks.models import Stock
        Stock.objects.create(symbol='AAPL', stock_name='Apple Inc.')
        Stock.objects.create(symbol='MSFT', stock_name='Microsoft Corporation')

        matcher._ensure_loaded()
        assert matcher._loaded is True
        # name 기반 lookup이 가능해야 함
        assert 'apple inc.' in matcher._stock_map
        assert matcher._stock_map['apple inc.'] == 'AAPL'

    def test_loads_only_once(self, matcher):
        from stocks.models import Stock
        Stock.objects.create(symbol='AAPL', stock_name='Apple Inc.')
        matcher._ensure_loaded()
        # 두 번째 호출은 캐시 사용
        Stock.objects.create(symbol='MSFT', stock_name='Microsoft')
        matcher._ensure_loaded()
        # 첫 호출 이후 추가된 MSFT는 반영되지 않아야 함 (idempotent)
        assert 'microsoft' not in matcher._stock_map


# ---------------------------------------------------------------------------
# Tests: _get_fuzzy_candidates
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestGetFuzzyCandidates:
    def test_returns_top_candidates(self, matcher):
        from stocks.models import Stock
        Stock.objects.create(symbol='AAPL', stock_name='Apple Inc.')
        Stock.objects.create(symbol='MSFT', stock_name='Microsoft')

        candidates = matcher._get_fuzzy_candidates('Apple', top_k=3)
        # 후보는 score 내림차순 정렬됨
        assert len(candidates) >= 1
        tickers = [c['ticker'] for c in candidates]
        assert 'AAPL' in tickers
        # 각 항목 구조 확인
        for c in candidates:
            assert 'ticker' in c
            assert 'name' in c
            assert 'score' in c
            assert 0 <= c['score'] <= 1

    def test_filters_below_score_50(self, matcher):
        from stocks.models import Stock
        Stock.objects.create(symbol='ZZZZ', stock_name='Completely Different Name')
        candidates = matcher._get_fuzzy_candidates('Apple', top_k=5)
        # score>=50 필터로 ZZZZ는 제외되어야 함
        assert all(c['ticker'] != 'ZZZZ' for c in candidates)

    def test_top_k_limit(self, matcher):
        from stocks.models import Stock
        for i in range(10):
            Stock.objects.create(symbol=f'TST{i}', stock_name=f'Apple {i}')
        candidates = matcher._get_fuzzy_candidates('Apple', top_k=3)
        assert len(candidates) <= 3


# ---------------------------------------------------------------------------
# Tests: match_with_queue
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestMatchWithQueue:
    def test_success_updates_evidence(self, matcher):
        """매칭 성공 시 evidence.target_company 업데이트 + neo4j_dirty=True."""
        from datetime import date
        from stocks.models import Stock
        from sec_pipeline.models import RawDocumentStore, SupplyChainEvidence

        source = Stock.objects.create(symbol='AAPL', stock_name='Apple Inc.', sector='Technology')
        target = Stock.objects.create(symbol='TSM', stock_name='Taiwan Semiconductor')
        doc = RawDocumentStore.objects.create(
            symbol=source, accession_no='acc-mwq-1',
            filing_date=date(2023, 11, 1), fiscal_year=2023,
            final_link='https://sec.gov/x',
        )
        evidence = SupplyChainEvidence.objects.create(
            source_document=doc, source_company=source,
            target_company=None, target_company_name='Taiwan Semiconductor',
            relationship_type='SUPPLIES_TO',
            evidence_text='TSMC manufactures chips.',
            neo4j_dirty=False,
        )
        with patch.object(TickerMatcher, 'match', return_value=('TSM', 'alias')):
            ticker, method = matcher.match_with_queue(
                'Taiwan Semiconductor', evidence, doc, 'AAPL'
            )
        assert ticker == 'TSM'
        assert method == 'alias'
        evidence.refresh_from_db()
        assert evidence.target_company_id == target.symbol
        assert evidence.neo4j_dirty is True

    def test_failure_creates_queue_entry(self, matcher):
        from datetime import date
        from stocks.models import Stock
        from sec_pipeline.models import (
            RawDocumentStore, SupplyChainEvidence, UnmatchedCompanyQueue,
        )

        source = Stock.objects.create(symbol='AAPL', stock_name='Apple Inc.', sector='Technology')
        doc = RawDocumentStore.objects.create(
            symbol=source, accession_no='acc-mwq-2',
            filing_date=date(2023, 11, 1), fiscal_year=2023,
            final_link='https://sec.gov/y',
        )
        evidence = SupplyChainEvidence.objects.create(
            source_document=doc, source_company=source,
            target_company_name='Random Unknown Co',
            relationship_type='DEPENDS_ON', evidence_text='ev',
        )
        with patch.object(TickerMatcher, 'match', return_value=(None, None)), \
             patch.object(TickerMatcher, '_get_fuzzy_candidates', return_value=[]):
            ticker, method = matcher.match_with_queue(
                'Random Unknown Co', evidence, doc, 'AAPL'
            )
        assert ticker is None
        entry = UnmatchedCompanyQueue.objects.get(raw_company_name='Random Unknown Co')
        assert entry.source_symbol == 'AAPL'
        assert entry.status == 'pending'
        assert 'Technology' in entry.source_sectors

    def test_duplicate_unmatched_increments_count(self, matcher):
        from datetime import date
        from stocks.models import Stock
        from sec_pipeline.models import (
            RawDocumentStore, SupplyChainEvidence, UnmatchedCompanyQueue,
        )

        source = Stock.objects.create(symbol='AAPL', stock_name='Apple Inc.', sector='Technology')
        doc = RawDocumentStore.objects.create(
            symbol=source, accession_no='acc-mwq-3',
            filing_date=date(2023, 11, 1), fiscal_year=2023,
            final_link='https://sec.gov/z',
        )
        evidence = SupplyChainEvidence.objects.create(
            source_document=doc, source_company=source,
            target_company_name='Dup Co',
            relationship_type='DEPENDS_ON', evidence_text='ev',
        )
        # 기존 큐 항목
        UnmatchedCompanyQueue.objects.create(
            raw_company_name='Dup Co', source_symbol='MSFT',
            occurrence_count=2, source_sectors=['Software'], status='pending',
        )

        with patch.object(TickerMatcher, 'match', return_value=(None, None)), \
             patch.object(TickerMatcher, '_get_fuzzy_candidates', return_value=[]):
            matcher.match_with_queue('Dup Co', evidence, doc, 'AAPL')

        entry = UnmatchedCompanyQueue.objects.get(raw_company_name='Dup Co')
        assert entry.occurrence_count == 3
        # 새 sector 'Technology'가 누적되어야 함
        assert 'Technology' in entry.source_sectors
        assert 'Software' in entry.source_sectors
