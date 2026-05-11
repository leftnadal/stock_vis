"""
SECFilingCollector 추가 단위 테스트.

기존 test_collector.py에서 누락된 영역:
- _remove_toc (TOC 제거)
- _find_section_candidates (후보 수집/길이 필터)
- extract_sections_fallback (edgartools fallback)
- collect() 통합 파이프라인 happy path / failure path

HTTP 요청은 전부 mock. 실제 SEC EDGAR 호출 절대 금지.
"""

import sys
import pytest
from unittest.mock import patch, MagicMock

from sec_pipeline.collector import SECFilingCollector


@pytest.fixture
def collector():
    c = SECFilingCollector()
    c._cik_cache.clear()
    return c


# ---------------------------------------------------------------------------
# Tests: _remove_toc
# ---------------------------------------------------------------------------

class TestRemoveToc:
    def test_removes_table_of_contents_block(self, collector):
        text = (
            "TABLE OF CONTENTS\n"
            "Item 1 ........... 5\n"
            "Item 1A .......... 20\n"
            "Item 7 ........... 40\n"
            "Item 1. Description of Business\n"
            "Real content body."
        )
        result = collector._remove_toc(text)
        # ToC 블록은 제거되고 본문 헤딩만 남아야 함
        assert 'Description of Business' in result
        # 첫 번째 ToC 라인은 제거됨
        assert 'TABLE OF CONTENTS\n' not in result

    def test_removes_index_block(self, collector):
        text = (
            "INDEX\n"
            "Item 1 ............. 5\n"
            "Item 1. Description of Business\n"
            "Body text."
        )
        result = collector._remove_toc(text)
        assert 'Description of Business' in result
        assert result.count('INDEX') == 0

    def test_no_toc_unchanged(self, collector):
        text = "Item 1. Business Overview\nApple designs phones."
        result = collector._remove_toc(text)
        assert 'Apple designs phones.' in result


# ---------------------------------------------------------------------------
# Tests: _find_section_candidates
# ---------------------------------------------------------------------------

class TestFindSectionCandidates:
    def test_candidate_extracted_when_long_enough(self, collector):
        body = "x " * 200  # 400자 → 200자 임계 통과
        text = (
            f"Item 1. Description of Business\n{body}"
            "Item 1A. Risk Factors\nrisk content here."
        )
        candidates = collector._find_section_candidates(text, 'item_1')
        assert len(candidates) >= 1
        # candidate는 헤딩부터 다음 섹션 직전까지
        assert 'Description of Business' in candidates[0]

    def test_short_candidate_filtered(self, collector):
        # 200자 미만 후보는 제외돼야 함
        text = "Item 1. short\nItem 1A. Risk Factors"
        candidates = collector._find_section_candidates(text, 'item_1')
        assert candidates == []

    def test_no_match_returns_empty(self, collector):
        text = "Random text without any item heading. " * 30
        candidates = collector._find_section_candidates(text, 'item_1')
        assert candidates == []


# ---------------------------------------------------------------------------
# Tests: extract_sections_fallback
# ---------------------------------------------------------------------------

class TestExtractSectionsFallback:
    def test_returns_none_when_edgartools_missing(self, collector, monkeypatch):
        # edgartools 임포트 실패 시 None 반환 (ImportError 처리)
        monkeypatch.setitem(sys.modules, 'edgartools', None)
        result = collector.extract_sections_fallback('AAPL')
        assert result is None


# ---------------------------------------------------------------------------
# Tests: collect() 통합 파이프라인
# ---------------------------------------------------------------------------

class TestCollectPipeline:
    def test_collect_returns_failed_when_no_metadata(self, collector):
        with patch.object(collector, 'get_filing_metadata', return_value=None):
            result = collector.collect('ZZZZ')
            assert result['status'] == 'failed'
            assert result['symbol'] == 'ZZZZ'
            assert any('No filing metadata' in w for w in result['warnings'])

    def test_collect_returns_failed_when_html_fetch_fails(self, collector):
        meta = {
            'symbol': 'AAPL',
            'accession_no': 'acc-1',
            'filing_date': '2023-11-03',
            'fiscal_year': 2023,
            'final_link': 'https://sec.gov/test',
        }
        with patch.object(collector, 'get_filing_metadata', return_value=meta), \
             patch.object(collector, 'fetch_filing_html', return_value=None):
            result = collector.collect('AAPL')
            assert result['status'] == 'failed'
            assert result['accession_no'] == 'acc-1'

    def test_collect_success_path(self, collector):
        """metadata + html + 섹션 모두 정상이면 success/partial 반환."""
        meta = {
            'symbol': 'AAPL',
            'accession_no': 'acc-2',
            'filing_date': '2023-11-03',
            'fiscal_year': 2023,
            'final_link': 'https://sec.gov/test',
        }
        sections = {
            'item_1': 'Apple Inc. designs phones. ' * 30,
            'item_1a': 'Risk factors include supply chain. ' * 30,
            'item_7': "Management's Discussion. " * 30,
        }
        with patch.object(collector, 'get_filing_metadata', return_value=meta), \
             patch.object(collector, 'fetch_filing_html', return_value='<html>x</html>'), \
             patch.object(collector, 'extract_sections', return_value=sections), \
             patch('sec_pipeline.collector.validate_extracted_sections',
                   return_value=(sections, [])):
            result = collector.collect('AAPL')
            assert result['symbol'] == 'AAPL'
            assert result['status'] == 'success'
            assert result['extraction_method'] == 'regex'
            assert result['sections']['item_1'].startswith('Apple Inc.')

    def test_collect_partial_when_validation_fails_no_fallback(self, collector):
        """검증 FAIL이지만 fallback이 없으면 partial로 떨어짐."""
        meta = {
            'symbol': 'AAPL',
            'accession_no': 'acc-3',
            'filing_date': '2023-11-03',
            'fiscal_year': 2023,
            'final_link': 'https://sec.gov/test',
        }
        sections = {'item_1': 'short', 'item_1a': '', 'item_7': ''}
        validated = {'item_1': 'short', 'item_1a': '', 'item_7': ''}
        warnings = ['FAIL: section heading not found']
        with patch.object(collector, 'get_filing_metadata', return_value=meta), \
             patch.object(collector, 'fetch_filing_html', return_value='<html>x</html>'), \
             patch.object(collector, 'extract_sections', return_value=sections), \
             patch.object(collector, 'extract_sections_fallback', return_value=None), \
             patch('sec_pipeline.collector.validate_extracted_sections',
                   return_value=(validated, warnings)):
            result = collector.collect('AAPL')
            # item_1만 있으므로 partial 또는 failed
            assert result['status'] in ('partial', 'failed')
            assert any('FAIL' in w for w in result['warnings'])
