"""
sec_pipeline 단위 테스트 신규 배치 (2026-05-20).

대상 모듈: collector, extractor, normalizer, ticker_matcher, models, quality_checks
HTTP/LLM 호출은 전부 mock. 실제 외부 호출 절대 금지.
"""

import json
from datetime import date, timedelta
from unittest.mock import MagicMock, patch

import pytest
from django.utils import timezone

# ---------------------------------------------------------------------------
# collector.py
# ---------------------------------------------------------------------------

class TestCollectorHelpers:
    """SECFilingCollector private helper methods."""

    def setup_method(self):
        from services.sec_pipeline.collector import SECFilingCollector
        self.collector = SECFilingCollector()
        self.collector._cik_cache.clear()

    def test_fiscal_year_q1_returns_previous_year(self):
        assert self.collector._fiscal_year_from_date('2024-02-15') == 2023

    def test_fiscal_year_q4_returns_same_year(self):
        assert self.collector._fiscal_year_from_date('2024-11-03') == 2024

    def test_fiscal_year_march_is_previous(self):
        assert self.collector._fiscal_year_from_date('2024-03-31') == 2023

    def test_fiscal_year_april_is_same(self):
        assert self.collector._fiscal_year_from_date('2024-04-01') == 2024

    def test_fiscal_year_invalid_format_returns_zero(self):
        assert self.collector._fiscal_year_from_date('not-a-date') == 0
        assert self.collector._fiscal_year_from_date('') == 0

    def test_fiscal_year_none_returns_zero(self):
        assert self.collector._fiscal_year_from_date(None) == 0

    def test_html_to_text_removes_script_and_style(self):
        html = '<html><script>alert(1)</script><style>p{color:red}</style><p>Hello</p></html>'
        text = self.collector._html_to_text(html)
        assert 'alert' not in text
        assert 'color:red' not in text
        assert 'Hello' in text

    def test_html_to_text_collapses_whitespace(self):
        html = '<p>A     B\t\tC</p>'
        text = self.collector._html_to_text(html)
        assert 'A B C' in text

    def test_remove_toc_strips_table_of_contents(self):
        text = "TABLE OF CONTENTS\nIndex stuff here\nItem 1. Business overview body text"
        result = self.collector._remove_toc(text)
        assert 'Item 1' in result
        assert 'Index stuff here' not in result

    def test_fail_result_structure(self):
        result = self.collector._fail_result('AAPL', 'because')
        assert result['status'] == 'failed'
        assert result['symbol'] == 'AAPL'
        assert result['sections'] == {'item_1': '', 'item_1a': '', 'item_7': ''}
        assert any('because' in w for w in result['warnings'])

    def test_fail_result_with_metadata(self):
        meta = {'accession_no': 'acc-1', 'filing_date': '2024-01-01',
                'fiscal_year': 2023, 'final_link': 'http://x'}
        result = self.collector._fail_result('MSFT', 'boom', meta)
        assert result['accession_no'] == 'acc-1'
        assert result['fiscal_year'] == 2023

    def test_fetch_filing_html_empty_link_returns_none(self):
        assert self.collector.fetch_filing_html('') is None
        assert self.collector.fetch_filing_html(None) is None

    @patch('services.sec_pipeline.collector.time.sleep')
    @patch('services.sec_pipeline.collector.requests.get')
    def test_fetch_filing_html_success(self, mock_get, mock_sleep):
        resp = MagicMock()
        resp.text = '<html>body</html>'
        resp.raise_for_status = MagicMock()
        mock_get.return_value = resp
        result = self.collector.fetch_filing_html('http://sec.gov/x.htm')
        assert result == '<html>body</html>'
        mock_get.assert_called_once()

    @patch('services.sec_pipeline.collector.time.sleep')
    @patch('services.sec_pipeline.collector.requests.get')
    def test_get_cik_handles_http_error_silently(self, mock_get, mock_sleep):
        import requests as requests_lib
        mock_get.side_effect = requests_lib.exceptions.RequestException("net down")
        assert self.collector._get_cik('AAPL') is None


# ---------------------------------------------------------------------------
# extractor.py
# ---------------------------------------------------------------------------

class TestGeminiExtractor:
    """GeminiExtractor — LLM 호출은 전부 mock."""

    def setup_method(self):
        from services.sec_pipeline.extractor import GeminiExtractor
        self.extractor = GeminiExtractor()

    def test_extract_supply_chain_empty_paragraphs(self):
        result = self.extractor.extract_supply_chain('AAPL', 'Apple', [])
        assert result == {'relationships': []}

    def test_extract_business_model_empty_paragraphs(self):
        result = self.extractor.extract_business_model('AAPL', 'Apple', [])
        assert result == {}

    def test_extract_supply_chain_success(self):
        fake_client = MagicMock()
        fake_resp = MagicMock()
        fake_resp.text = json.dumps({'relationships': [
            {'target_company_name': 'TSMC', 'relationship_type': 'SUPPLIES_TO'}
        ]})
        fake_client.models.generate_content.return_value = fake_resp
        self.extractor._client = fake_client

        with patch('google.genai.types') as mock_types:
            mock_types.GenerateContentConfig = MagicMock()
            mock_types.ThinkingConfig = MagicMock()
            result = self.extractor.extract_supply_chain(
                'AAPL', 'Apple', ['Apple sources chips from TSMC.']
            )
        assert 'relationships' in result
        assert len(result['relationships']) == 1

    def test_extract_supply_chain_missing_relationships_key(self):
        fake_client = MagicMock()
        fake_resp = MagicMock()
        fake_resp.text = json.dumps({'other_field': []})
        fake_client.models.generate_content.return_value = fake_resp
        self.extractor._client = fake_client

        with patch('google.genai.types') as mock_types:
            mock_types.GenerateContentConfig = MagicMock()
            mock_types.ThinkingConfig = MagicMock()
            result = self.extractor.extract_supply_chain(
                'AAPL', 'Apple', ['paragraph']
            )
        assert result == {'relationships': []}

    def test_extract_supply_chain_json_decode_error(self):
        fake_client = MagicMock()
        fake_resp = MagicMock()
        fake_resp.text = 'not valid json {{{'
        fake_client.models.generate_content.return_value = fake_resp
        self.extractor._client = fake_client

        with patch('google.genai.types') as mock_types:
            mock_types.GenerateContentConfig = MagicMock()
            mock_types.ThinkingConfig = MagicMock()
            result = self.extractor.extract_supply_chain(
                'AAPL', 'Apple', ['paragraph']
            )
        assert result['relationships'] == []
        assert 'error' in result

    def test_extract_business_model_success(self):
        fake_client = MagicMock()
        fake_resp = MagicMock()
        fake_resp.text = json.dumps({
            'direct_customer_contact': {'value': 'direct', 'evidence_text': 'x', 'confidence': 0.9}
        })
        fake_client.models.generate_content.return_value = fake_resp
        self.extractor._client = fake_client

        with patch('google.genai.types') as mock_types:
            mock_types.GenerateContentConfig = MagicMock()
            mock_types.ThinkingConfig = MagicMock()
            result = self.extractor.extract_business_model(
                'AAPL', 'Apple', ['paragraph about direct sales']
            )
        assert 'direct_customer_contact' in result

    def test_extract_business_model_json_error_returns_error_field(self):
        fake_client = MagicMock()
        fake_resp = MagicMock()
        fake_resp.text = 'broken {'
        fake_client.models.generate_content.return_value = fake_resp
        self.extractor._client = fake_client

        with patch('google.genai.types') as mock_types:
            mock_types.GenerateContentConfig = MagicMock()
            mock_types.ThinkingConfig = MagicMock()
            result = self.extractor.extract_business_model(
                'AAPL', 'Apple', ['paragraph']
            )
        assert 'error' in result


# ---------------------------------------------------------------------------
# normalizer.py
# ---------------------------------------------------------------------------

class TestNormalizer:
    """normalize_section_all + filter_paragraphs."""

    def test_normalize_section_all_concats_item_1_and_7(self):
        from services.sec_pipeline.normalizer import normalize_section_all
        sections = {
            'item_1': 'Business overview text.',
            'item_1a': 'Risk factors text.',
            'item_7': 'MD&A text.',
        }
        result = normalize_section_all(sections)
        assert 'Business overview text.' in result
        assert 'MD&A text.' in result
        # Track A는 item_1a 제외
        assert 'Risk factors' not in result

    def test_normalize_section_all_empty_sections(self):
        from services.sec_pipeline.normalizer import normalize_section_all
        assert normalize_section_all({}) == ''
        assert normalize_section_all({'item_1': '', 'item_7': ''}) == ''

    def test_clean_text_removes_html_entities(self):
        from services.sec_pipeline.normalizer import _clean_text
        text = 'Hello&nbsp;world&amp;more&#160;text'
        result = _clean_text(text)
        assert '&nbsp;' not in result
        assert '&amp;' not in result
        assert '&#160;' not in result
        assert 'Hello' in result and 'world' in result

    def test_clean_text_collapses_excess_blank_lines(self):
        from services.sec_pipeline.normalizer import _clean_text
        text = 'A\n\n\n\n\nB'
        result = _clean_text(text)
        assert '\n\n\n' not in result

    def test_filter_paragraphs_picks_keyword_hit_lines(self):
        from services.sec_pipeline.normalizer import filter_paragraphs
        text = (
            "Our key supplier relationships are critical to operations and growth strategy.\n"
            "The weather has been quite nice this year in the northern regions of the world.\n"
            "We compete with multiple competitors in the global semiconductor market segments.\n"
        )
        result = filter_paragraphs(text, max_paragraphs=5)
        assert len(result) >= 1
        # 키워드 없는 단락은 제외
        assert not any('weather' in p for p in result)

    def test_filter_paragraphs_drops_short_paragraphs(self):
        from services.sec_pipeline.normalizer import filter_paragraphs
        # 50자 미만이라 모두 제외되어야 함
        text = "supplier short\ncustomer brief\ncontract too short to keep"
        assert filter_paragraphs(text) == []

    def test_filter_paragraphs_respects_max(self):
        from services.sec_pipeline.normalizer import filter_paragraphs
        lines = []
        for i in range(20):
            lines.append(
                f"Paragraph {i}: our supplier customer partnership "
                f"contract OEM joint venture distributor reseller relationship "
                f"with key partners and the wider supply chain ecosystem details."
            )
        text = '\n'.join(lines)
        result = filter_paragraphs(text, max_paragraphs=3)
        assert len(result) <= 3

    def test_filter_paragraphs_dedups_by_prefix(self):
        from services.sec_pipeline.normalizer import filter_paragraphs
        # 동일한 첫 200자 → 중복 제거되어야 함
        base = "Our supplier and customer relationships in the global supply chain " * 5
        text = f"{base}\n{base}"
        result = filter_paragraphs(text)
        assert len(result) == 1


# ---------------------------------------------------------------------------
# ticker_matcher.py
# ---------------------------------------------------------------------------

class TestTickerMatcherHelpers:
    """순수 함수 테스트 (DB 없이)."""

    def test_clean_name_removes_inc(self):
        from services.sec_pipeline.ticker_matcher import TickerMatcher
        assert TickerMatcher._clean_name('Apple Inc.') == 'apple'
        assert TickerMatcher._clean_name('Apple Inc') == 'apple'

    def test_clean_name_removes_corp(self):
        from services.sec_pipeline.ticker_matcher import TickerMatcher
        assert TickerMatcher._clean_name('Microsoft Corp') == 'microsoft'
        assert TickerMatcher._clean_name('Microsoft Corporation') == 'microsoft'

    def test_clean_name_removes_ltd_and_llc(self):
        from services.sec_pipeline.ticker_matcher import TickerMatcher
        assert TickerMatcher._clean_name('Foo Ltd.') == 'foo'
        assert TickerMatcher._clean_name('Bar LLC') == 'bar'

    def test_clean_name_returns_lowercase(self):
        from services.sec_pipeline.ticker_matcher import TickerMatcher
        result = TickerMatcher._clean_name('TESLA, Inc.')
        assert result == 'tesla'


@pytest.mark.django_db
class TestTickerMatcherMatch:
    """match() 메서드 — DB 캐시 사용."""

    def test_match_empty_name_returns_none(self):
        from services.sec_pipeline.ticker_matcher import TickerMatcher
        matcher = TickerMatcher()
        assert matcher.match('') == (None, None)

    def test_match_too_short_name_returns_none(self):
        from services.sec_pipeline.ticker_matcher import TickerMatcher
        matcher = TickerMatcher()
        assert matcher.match('A') == (None, None)

    def test_match_exact_stock_name(self):
        from packages.shared.stocks.models import Stock
        from services.sec_pipeline.ticker_matcher import TickerMatcher
        Stock.objects.create(symbol='AAPL', stock_name='Apple Inc.')
        matcher = TickerMatcher()
        ticker, method = matcher.match('Apple Inc.')
        assert ticker == 'AAPL'
        assert method == 'exact'

    def test_match_exact_case_insensitive(self):
        from packages.shared.stocks.models import Stock
        from services.sec_pipeline.ticker_matcher import TickerMatcher
        Stock.objects.create(symbol='MSFT', stock_name='Microsoft Corporation')
        matcher = TickerMatcher()
        ticker, method = matcher.match('microsoft corporation')
        assert ticker == 'MSFT'

    def test_match_alias_takes_priority(self):
        from packages.shared.stocks.models import Stock
        from services.sec_pipeline.models import CompanyAlias
        from services.sec_pipeline.ticker_matcher import TickerMatcher

        Stock.objects.create(symbol='TSMC', stock_name='Taiwan Semiconductor')
        CompanyAlias.objects.create(
            alias='TSMC', ticker='TSMC', context_sector='', source='manual_seed'
        )
        matcher = TickerMatcher()
        ticker, method = matcher.match('TSMC')
        assert ticker == 'TSMC'
        assert method == 'alias'

    def test_match_alias_context_sector_specific(self):
        from services.sec_pipeline.models import CompanyAlias
        from services.sec_pipeline.ticker_matcher import TickerMatcher

        CompanyAlias.objects.create(
            alias='Delta', ticker='DAL', context_sector='Industrials',
        )
        CompanyAlias.objects.create(
            alias='Delta', ticker='DLTR', context_sector='Consumer',
        )
        matcher = TickerMatcher()
        ticker, _ = matcher.match('Delta', context_sector='Industrials')
        assert ticker == 'DAL'

    def test_match_fuzzy_matches_close_enough(self):
        from packages.shared.stocks.models import Stock
        from services.sec_pipeline.ticker_matcher import TickerMatcher
        Stock.objects.create(symbol='NVDA', stock_name='NVIDIA Corporation')
        matcher = TickerMatcher()
        ticker, method = matcher.match('NVIDIA Corp')
        # alias 없이 exact 또는 fuzzy로 매칭되어야 함
        assert ticker == 'NVDA'
        assert method in ('exact', 'fuzzy')

    def test_match_no_match_returns_none(self):
        from services.sec_pipeline.ticker_matcher import TickerMatcher
        matcher = TickerMatcher()
        ticker, method = matcher.match('Completely Unknown Company XYZ 12345')
        assert ticker is None
        assert method is None


# ---------------------------------------------------------------------------
# models.py
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestModelStrAndDefaults:

    def test_company_alias_str_with_sector(self):
        from services.sec_pipeline.models import CompanyAlias
        alias = CompanyAlias.objects.create(
            alias='Foo', ticker='FOO', context_sector='Tech',
        )
        s = str(alias)
        assert 'Foo' in s and 'FOO' in s and 'Tech' in s

    def test_company_alias_str_without_sector(self):
        from services.sec_pipeline.models import CompanyAlias
        alias = CompanyAlias.objects.create(alias='Bar', ticker='BAR')
        s = str(alias)
        assert 'Bar' in s and 'BAR' in s
        assert '[' not in s

    def test_unmatched_queue_str_and_defaults(self):
        from services.sec_pipeline.models import UnmatchedCompanyQueue
        q = UnmatchedCompanyQueue.objects.create(
            raw_company_name='Foo Bar Ltd',
            source_symbol='AAPL',
        )
        assert q.occurrence_count == 1
        assert q.status == 'pending'
        assert q.fuzzy_candidates == []
        assert q.source_sectors == []
        assert 'Foo Bar Ltd' in str(q)
        assert 'pending' in str(q)

    def test_filing_process_log_str(self):
        from services.sec_pipeline.models import FilingProcessLog
        log = FilingProcessLog.objects.create(
            symbol='AAPL', stage='sec_fetch', status='success',
        )
        s = str(log)
        assert 'AAPL' in s and 'sec_fetch' in s and 'success' in s

    def test_supply_chain_evidence_str(self):
        from packages.shared.stocks.models import Stock
        from services.sec_pipeline.models import RawDocumentStore, SupplyChainEvidence
        stock = Stock.objects.create(symbol='AAPL', stock_name='Apple Inc.')
        doc = RawDocumentStore.objects.create(
            symbol=stock, accession_no='acc-x-001',
            filing_date=date(2024, 1, 15), fiscal_year=2023,
            final_link='http://sec.gov/x',
        )
        ev = SupplyChainEvidence.objects.create(
            source_document=doc, source_company=stock,
            target_company_name='TSMC',
            relationship_type='SUPPLIES_TO', evidence_text='evidence',
        )
        s = str(ev)
        assert 'TSMC' in s and 'SUPPLIES_TO' in s

    def test_supply_chain_evidence_defaults(self):
        from packages.shared.stocks.models import Stock
        from services.sec_pipeline.models import RawDocumentStore, SupplyChainEvidence
        stock = Stock.objects.create(symbol='NVDA', stock_name='NVIDIA')
        doc = RawDocumentStore.objects.create(
            symbol=stock, accession_no='acc-x-002',
            filing_date=date(2024, 1, 15), fiscal_year=2023,
            final_link='http://sec.gov/x',
        )
        ev = SupplyChainEvidence.objects.create(
            source_document=doc, source_company=stock,
            target_company_name='Foo',
            relationship_type='PARTNER_WITH', evidence_text='ev',
        )
        # 핵심 기본값
        assert ev.neo4j_dirty is True
        assert ev.target_company is None
        assert ev.system_confidence == 0.0
        assert ev.confidence_grade == 'low'
        assert ev.prompt_version == 'v1'

    def test_business_model_snapshot_str_and_defaults(self):
        from packages.shared.stocks.models import Stock
        from services.sec_pipeline.models import BusinessModelSnapshot, RawDocumentStore
        stock = Stock.objects.create(symbol='SHOP', stock_name='Shopify')
        doc = RawDocumentStore.objects.create(
            symbol=stock, accession_no='acc-y-001',
            filing_date=date(2024, 2, 1), fiscal_year=2023,
            final_link='http://sec.gov/y',
        )
        snap = BusinessModelSnapshot.objects.create(
            symbol=stock, source_document=doc, as_of_date=date(2024, 2, 1),
        )
        assert snap.direct_customer_contact == 'unknown'
        assert snap.confidence_grade == 'low'
        assert 'SHOP' in str(snap)

    def test_pipeline_intelligence_report_str(self):
        from services.sec_pipeline.models import PipelineIntelligenceReport
        rep = PipelineIntelligenceReport.objects.create(
            report_date=date(2024, 4, 1), severity='warning',
        )
        s = str(rep)
        assert '2024-04-01' in s
        assert 'warning' in s


# ---------------------------------------------------------------------------
# quality_checks.py
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestQualityChecksFresh:

    def test_empty_db_no_alerts(self):
        from services.sec_pipeline.quality_checks import run_post_batch_quality_checks
        alerts = run_post_batch_quality_checks(hours_back=24)
        assert alerts == []

    def test_dashboard_stats_zero_state(self):
        from services.sec_pipeline.quality_checks import get_dashboard_stats
        stats = get_dashboard_stats()
        assert stats['collection']['total'] == 0
        assert stats['track_a']['total_evidences'] == 0
        assert stats['track_a']['avg_confidence'] == 0
        assert stats['track_b']['total_snapshots'] == 0
        assert stats['matching']['queue_total'] == 0

    def test_high_collection_failure_rate_triggers_alert(self):
        from packages.shared.stocks.models import Stock
        from services.sec_pipeline.models import RawDocumentStore
        from services.sec_pipeline.quality_checks import run_post_batch_quality_checks

        stock = Stock.objects.create(symbol='AAPL', stock_name='Apple')
        # 5건 중 3건 failed → 60% > 20% 임계
        for i in range(5):
            RawDocumentStore.objects.create(
                symbol=stock,
                accession_no=f'acc-fail-{i}',
                filing_date=date(2024, 1, 1),
                fiscal_year=2023,
                final_link=f'http://sec.gov/{i}',
                status='failed' if i < 3 else 'success',
            )
        alerts = run_post_batch_quality_checks(hours_back=24)
        assert any('수집 실패율' in a for a in alerts)

    def test_unmatched_queue_overflow_triggers_alert(self):
        from services.sec_pipeline.models import UnmatchedCompanyQueue
        from services.sec_pipeline.quality_checks import run_post_batch_quality_checks

        for i in range(101):
            UnmatchedCompanyQueue.objects.create(
                raw_company_name=f'Co{i}', source_symbol='AAPL', status='pending',
            )
        alerts = run_post_batch_quality_checks(hours_back=24)
        assert any('미매칭 큐 적체' in a for a in alerts)

    def test_low_match_rate_triggers_alert(self):
        from packages.shared.stocks.models import Stock
        from services.sec_pipeline.models import RawDocumentStore, SupplyChainEvidence
        from services.sec_pipeline.quality_checks import run_post_batch_quality_checks

        stock = Stock.objects.create(symbol='AAPL', stock_name='Apple')
        doc = RawDocumentStore.objects.create(
            symbol=stock, accession_no='acc-mr-1',
            filing_date=date(2024, 1, 1), fiscal_year=2023,
            final_link='http://sec.gov/mr',
        )
        # 10건 모두 target_company None → 매칭률 0%
        for i in range(10):
            SupplyChainEvidence.objects.create(
                source_document=doc, source_company=stock,
                target_company_name=f'NotPublic{i}',
                relationship_type='SUPPLIES_TO',
                evidence_text='ev', system_confidence=0.7,
            )
        alerts = run_post_batch_quality_checks(hours_back=24)
        assert any('매칭률' in a for a in alerts)

    def test_low_confidence_triggers_alert(self):
        from packages.shared.stocks.models import Stock
        from services.sec_pipeline.models import RawDocumentStore, SupplyChainEvidence
        from services.sec_pipeline.quality_checks import run_post_batch_quality_checks

        stock = Stock.objects.create(symbol='AAPL', stock_name='Apple')
        target = Stock.objects.create(symbol='TGT', stock_name='Target Co')
        doc = RawDocumentStore.objects.create(
            symbol=stock, accession_no='acc-cf-1',
            filing_date=date(2024, 1, 1), fiscal_year=2023,
            final_link='http://sec.gov/cf',
        )
        # 매칭은 다 됐지만 confidence 낮음
        for i in range(5):
            SupplyChainEvidence.objects.create(
                source_document=doc, source_company=stock,
                target_company=target,
                target_company_name='Target Co',
                relationship_type='SUPPLIES_TO',
                evidence_text='ev', system_confidence=0.2,
            )
        alerts = run_post_batch_quality_checks(hours_back=24)
        assert any('confidence' in a for a in alerts)

    def test_dashboard_stats_populated_counts(self):
        from packages.shared.stocks.models import Stock
        from services.sec_pipeline.models import (
            BusinessModelSnapshot,
            RawDocumentStore,
            SupplyChainEvidence,
            UnmatchedCompanyQueue,
        )
        from services.sec_pipeline.quality_checks import get_dashboard_stats

        stock = Stock.objects.create(symbol='AAPL', stock_name='Apple')
        doc = RawDocumentStore.objects.create(
            symbol=stock, accession_no='acc-ds-1',
            filing_date=date(2024, 1, 1), fiscal_year=2023,
            final_link='http://sec.gov/ds', status='success',
        )
        RawDocumentStore.objects.create(
            symbol=stock, accession_no='acc-ds-2',
            filing_date=date(2024, 1, 2), fiscal_year=2023,
            final_link='http://sec.gov/ds2', status='partial',
        )
        SupplyChainEvidence.objects.create(
            source_document=doc, source_company=stock,
            target_company_name='X', relationship_type='SUPPLIES_TO',
            evidence_text='ev', system_confidence=0.8,
        )
        BusinessModelSnapshot.objects.create(
            symbol=stock, source_document=doc, as_of_date=date(2024, 1, 1),
            confidence_grade='high',
        )
        UnmatchedCompanyQueue.objects.create(
            raw_company_name='X', source_symbol='AAPL', status='pending',
        )
        stats = get_dashboard_stats()
        assert stats['collection']['total'] == 2
        assert stats['collection']['success'] == 1
        assert stats['collection']['partial'] == 1
        assert stats['track_a']['total_evidences'] == 1
        assert stats['track_b']['total_snapshots'] == 1
        assert stats['track_b']['high_grade'] == 1
        assert stats['matching']['queue_pending'] == 1
