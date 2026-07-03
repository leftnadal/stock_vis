"""
sec_pipeline 보강 단위 테스트 (30+).

기존 테스트와 중복되지 않는 케이스로 collector/extractor/normalizer/
ticker_matcher/quality_checks/models를 추가 검증한다.

- HTTP 요청은 모두 mock
- Gemini LLM 호출은 모두 mock
- 실제 SEC EDGAR 호출 절대 금지
"""

import json
from datetime import date, timedelta
from unittest.mock import MagicMock, patch

import pytest
from django.utils import timezone

# =============================================================================
# Collector — 보강 케이스
# =============================================================================

@pytest.fixture
def collector():
    from services.sec_pipeline.collector import SECFilingCollector
    c = SECFilingCollector()
    c._cik_cache.clear()
    return c


class TestCollectorCikPadding:
    """_get_cik가 다양한 자릿수의 cik_str를 10자리로 zero-pad 하는지."""

    @patch('services.sec_pipeline.collector.time.sleep')
    @patch('services.sec_pipeline.collector.requests.get')
    def test_short_cik_padded_to_10(self, mock_get, _sleep, collector):
        resp = MagicMock()
        resp.raise_for_status = MagicMock()
        resp.json.return_value = {
            "0": {"cik_str": 12345, "ticker": "XYZ", "title": "XYZ Co"},
        }
        mock_get.return_value = resp

        cik = collector._get_cik('XYZ')
        assert cik == '0000012345'
        assert len(cik) == 10

    @patch('services.sec_pipeline.collector.time.sleep')
    @patch('services.sec_pipeline.collector.requests.get')
    def test_full_length_cik_unchanged(self, mock_get, _sleep, collector):
        resp = MagicMock()
        resp.raise_for_status = MagicMock()
        resp.json.return_value = {
            "0": {"cik_str": 1234567890, "ticker": "BIG", "title": "Big Co"},
        }
        mock_get.return_value = resp

        cik = collector._get_cik('BIG')
        assert cik == '1234567890'

    @patch('services.sec_pipeline.collector.time.sleep')
    @patch('services.sec_pipeline.collector.requests.get')
    def test_ticker_case_insensitive_lookup(self, mock_get, _sleep, collector):
        resp = MagicMock()
        resp.raise_for_status = MagicMock()
        resp.json.return_value = {
            "0": {"cik_str": 320193, "ticker": "aapl", "title": "Apple Inc."},
        }
        mock_get.return_value = resp

        # _get_cik는 entry['ticker'].upper() == symbol 로 비교한다
        cik = collector._get_cik('AAPL')
        assert cik == '0000320193'


class TestCollectorFiscalYearBoundary:
    """fiscal_year 경계값 추가 검증 (1월~12월)."""

    def test_january_filing(self, collector):
        assert collector._fiscal_year_from_date('2024-01-15') == 2023

    def test_december_filing(self, collector):
        assert collector._fiscal_year_from_date('2024-12-31') == 2024

    def test_empty_string(self, collector):
        assert collector._fiscal_year_from_date('') == 0

    def test_malformed_date(self, collector):
        assert collector._fiscal_year_from_date('2024/05/01') == 0


class TestCollectorExtractSectionsPatterns:
    """SECTION_PATTERNS 클래스 상수 정합성."""

    def test_item_patterns_present(self, collector):
        from services.sec_pipeline.collector import SECFilingCollector
        assert 'item_1' in SECFilingCollector.SECTION_PATTERNS
        assert 'item_1a' in SECFilingCollector.SECTION_PATTERNS
        assert 'item_7' in SECFilingCollector.SECTION_PATTERNS
        assert 'item_8' in SECFilingCollector.SECTION_PATTERNS

    def test_each_section_has_multiple_alternatives(self, collector):
        from services.sec_pipeline.collector import SECFilingCollector
        for key, patterns in SECFilingCollector.SECTION_PATTERNS.items():
            assert isinstance(patterns, list)
            assert len(patterns) >= 1, f"{key} has no patterns"


class TestCollectorFetchEmptyAndNone:
    """fetch_filing_html(None/'') → None (조기 반환)."""

    def test_empty_link_does_not_call_requests(self, collector):
        with patch('services.sec_pipeline.collector.requests.get') as mock_get:
            assert collector.fetch_filing_html('') is None
            mock_get.assert_not_called()

    def test_none_link_does_not_call_requests(self, collector):
        with patch('services.sec_pipeline.collector.requests.get') as mock_get:
            assert collector.fetch_filing_html(None) is None
            mock_get.assert_not_called()


# =============================================================================
# Normalizer — 보강 케이스
# =============================================================================

class TestNormalizerMaxParagraphs:
    """filter_paragraphs의 max_paragraphs 캡."""

    def test_max_paragraphs_caps_output(self):
        from services.sec_pipeline.normalizer import filter_paragraphs

        # 20개 문단, 각 문단마다 키워드 1개 hit
        paragraphs = [
            f"This paragraph mentions supplier number {i}. " + "x" * 80
            for i in range(20)
        ]
        text = '\n'.join(paragraphs)
        result = filter_paragraphs(text, max_paragraphs=5)
        assert len(result) <= 5

    def test_returns_empty_when_no_keywords(self):
        from services.sec_pipeline.normalizer import filter_paragraphs

        text = ("Lorem ipsum dolor sit amet, consectetur adipiscing elit. "
                "Some random paragraph " * 5)
        result = filter_paragraphs(text)
        assert result == []

    def test_orders_by_hit_count_descending(self):
        from services.sec_pipeline.normalizer import filter_paragraphs

        high_hits = ("Our supplier and customer rely on third-party "
                     "manufacturers competing for raw material") + " " + "x" * 60
        low_hits = "We have one supplier mentioned. " + "y" * 80
        text = f"{low_hits}\n{high_hits}"
        result = filter_paragraphs(text)
        # high_hits가 먼저 (히트 수 더 많음)
        assert result[0] == high_hits.strip()

    def test_short_paragraphs_filtered_below_50_chars(self):
        from services.sec_pipeline.normalizer import filter_paragraphs

        short = "supplier here"  # < 50 chars, contains keyword
        long_p = ("Our supplier and customer rely on third-party "
                  "manufacturers procuring components") + " " + "x" * 30
        text = f"{short}\n{long_p}"
        result = filter_paragraphs(text)
        # short는 50자 미만 → 제외
        assert short not in result


class TestNormalizerCleanText:
    """_clean_text의 numeric entity, 빈 줄 다중 처리."""

    def test_removes_numeric_html_entities(self):
        from services.sec_pipeline.normalizer import _clean_text
        result = _clean_text("Hello &#8217; World &#160; foo")
        assert '&#8217;' not in result
        assert '&#160;' not in result

    def test_strips_leading_trailing_whitespace(self):
        from services.sec_pipeline.normalizer import _clean_text
        result = _clean_text("   \n\n  content here  \n\n   ")
        assert result.startswith('content')
        assert result.endswith('here')

    def test_collapses_4_or_more_newlines(self):
        from services.sec_pipeline.normalizer import _clean_text
        result = _clean_text("line1\n\n\n\n\nline2")
        # 3개 이상 → 2개로 축약
        assert '\n\n\n' not in result


class TestNormalizerKeywordsConst:
    """SUPPLY_CHAIN_KEYWORDS 상수 정합성."""

    def test_keywords_is_nonempty_list(self):
        from services.sec_pipeline.normalizer import SUPPLY_CHAIN_KEYWORDS
        assert isinstance(SUPPLY_CHAIN_KEYWORDS, list)
        assert len(SUPPLY_CHAIN_KEYWORDS) > 10

    def test_keywords_contain_supplier_customer(self):
        from services.sec_pipeline.normalizer import SUPPLY_CHAIN_KEYWORDS
        assert 'supplier' in SUPPLY_CHAIN_KEYWORDS
        assert 'customer' in SUPPLY_CHAIN_KEYWORDS


# =============================================================================
# Ticker Matcher — 보강 케이스
# =============================================================================

@pytest.fixture
def matcher():
    from services.sec_pipeline.ticker_matcher import TickerMatcher
    m = TickerMatcher()
    m._loaded = False
    m._stock_map = {}
    return m


class TestTickerMatcherCleanNameExtra:
    """_clean_name의 다양한 접미사."""

    def test_removes_plc(self):
        from services.sec_pipeline.ticker_matcher import TickerMatcher
        assert TickerMatcher._clean_name('BP PLC') == 'bp'

    def test_removes_sa(self):
        from services.sec_pipeline.ticker_matcher import TickerMatcher
        assert TickerMatcher._clean_name('LVMH S.A.') == 'lvmh'

    def test_removes_company(self):
        from services.sec_pipeline.ticker_matcher import TickerMatcher
        assert TickerMatcher._clean_name('The Boeing Company') == 'the boeing'

    def test_removes_group(self):
        from services.sec_pipeline.ticker_matcher import TickerMatcher
        assert TickerMatcher._clean_name('Volkswagen Group') == 'volkswagen'

    def test_handles_comma_before_suffix(self):
        from services.sec_pipeline.ticker_matcher import TickerMatcher
        assert TickerMatcher._clean_name('Apple, Inc.') == 'apple'


@pytest.mark.django_db
class TestTickerMatcherAliasContext:
    """CompanyAlias의 context_sector 우선/범용 fallback."""

    def test_sector_specific_alias_wins(self, matcher):
        from services.sec_pipeline.models import CompanyAlias

        CompanyAlias.objects.create(
            alias='Apple', ticker='AAPL',
            context_sector='Technology', source='manual_seed',
        )
        CompanyAlias.objects.create(
            alias='Apple', ticker='OTHER',
            context_sector='', source='manual_seed',
        )
        ticker, method = matcher.match('Apple', context_sector='Technology')
        assert ticker == 'AAPL'
        assert method == 'alias'

    def test_falls_back_to_generic_alias(self, matcher):
        from services.sec_pipeline.models import CompanyAlias

        CompanyAlias.objects.create(
            alias='Cisco', ticker='CSCO',
            context_sector='', source='manual_seed',
        )
        # 다른 sector로 검색해도 generic으로 매칭됨
        ticker, method = matcher.match('Cisco', context_sector='Healthcare')
        assert ticker == 'CSCO'
        assert method == 'alias'

    def test_alias_case_insensitive(self, matcher):
        from services.sec_pipeline.models import CompanyAlias

        CompanyAlias.objects.create(
            alias='NVIDIA', ticker='NVDA',
            context_sector='', source='manual_seed',
        )
        ticker = matcher._match_alias('nvidia', '')
        assert ticker == 'NVDA'


@pytest.mark.django_db
class TestTickerMatcherMatchWithQueue:
    """match_with_queue 실패 경로: 큐 적재 + occurrence_count 증가."""

    def test_unmatched_creates_queue_entry(self, matcher):
        from packages.shared.stocks.models import Stock
        from services.sec_pipeline.models import (
            RawDocumentStore,
            SupplyChainEvidence,
            UnmatchedCompanyQueue,
        )

        stock = Stock.objects.create(
            symbol='AAPL', stock_name='Apple Inc.', sector='Technology',
        )
        doc = RawDocumentStore.objects.create(
            symbol=stock,
            accession_no='acc-q1',
            filing_date=date(2024, 1, 1),
            fiscal_year=2023,
            final_link='https://sec.gov/x',
        )
        ev = SupplyChainEvidence.objects.create(
            source_document=doc,
            source_company=stock,
            target_company_name='Mystery Co',
            relationship_type='SUPPLIES_TO',
            evidence_text='evidence',
            system_confidence=0.3,
        )

        ticker, method = matcher.match_with_queue(
            'Mystery Unknown Co XYZ', ev, doc, 'AAPL',
        )
        assert ticker is None
        assert method is None
        assert UnmatchedCompanyQueue.objects.filter(
            raw_company_name='Mystery Unknown Co XYZ',
        ).exists()

    def test_second_occurrence_increments_count(self, matcher):
        from packages.shared.stocks.models import Stock
        from services.sec_pipeline.models import (
            RawDocumentStore,
            SupplyChainEvidence,
            UnmatchedCompanyQueue,
        )

        stock = Stock.objects.create(
            symbol='MSFT', stock_name='Microsoft', sector='Technology',
        )
        doc = RawDocumentStore.objects.create(
            symbol=stock,
            accession_no='acc-q2',
            filing_date=date(2024, 2, 1),
            fiscal_year=2023,
            final_link='https://sec.gov/y',
        )
        ev = SupplyChainEvidence.objects.create(
            source_document=doc,
            source_company=stock,
            target_company_name='Foo',
            relationship_type='SUPPLIES_TO',
            evidence_text='ev',
            system_confidence=0.1,
        )

        matcher.match_with_queue('Phantom Vendor Inc', ev, doc, 'MSFT')
        matcher.match_with_queue('Phantom Vendor Inc', ev, doc, 'MSFT')

        entry = UnmatchedCompanyQueue.objects.get(
            raw_company_name='Phantom Vendor Inc',
        )
        assert entry.occurrence_count == 2


# =============================================================================
# Quality Checks — 보강 케이스
# =============================================================================

@pytest.mark.django_db
class TestDashboardStatsStructure:
    """get_dashboard_stats가 4개 섹션 dict를 반환."""

    def test_empty_db_returns_zero_counts(self):
        from services.sec_pipeline.quality_checks import get_dashboard_stats
        stats = get_dashboard_stats()

        assert set(stats.keys()) == {'collection', 'track_a', 'track_b', 'matching'}
        assert stats['collection']['total'] == 0
        assert stats['track_a']['total_evidences'] == 0
        assert stats['track_b']['total_snapshots'] == 0
        assert stats['matching']['queue_total'] == 0

    def test_collection_counts_by_status(self):
        from packages.shared.stocks.models import Stock
        from services.sec_pipeline.models import RawDocumentStore
        from services.sec_pipeline.quality_checks import get_dashboard_stats

        stock = Stock.objects.create(symbol='DSH', stock_name='Dash Inc')
        for i, status in enumerate(['success', 'success', 'partial', 'failed']):
            RawDocumentStore.objects.create(
                symbol=stock,
                accession_no=f'acc-dsh-{i}',
                filing_date=date(2024, 1, 1) + timedelta(days=i),
                fiscal_year=2023,
                final_link=f'https://sec.gov/{i}',
                status=status,
            )

        stats = get_dashboard_stats()
        assert stats['collection']['total'] == 4
        assert stats['collection']['success'] == 2
        assert stats['collection']['partial'] == 1
        assert stats['collection']['failed'] == 1


@pytest.mark.django_db
class TestQualityChecksAlerts:
    """run_post_batch_quality_checks 알림 임계값."""

    def test_no_alerts_under_thresholds(self):
        from services.sec_pipeline.quality_checks import run_post_batch_quality_checks
        alerts = run_post_batch_quality_checks(hours_back=24)
        assert alerts == []

    def test_neo4j_dirty_backlog_alert(self):
        from packages.shared.stocks.models import Stock
        from services.sec_pipeline.models import RawDocumentStore, SupplyChainEvidence
        from services.sec_pipeline.quality_checks import run_post_batch_quality_checks

        src = Stock.objects.create(symbol='SRC', stock_name='Source')
        tgt = Stock.objects.create(symbol='TGT', stock_name='Target')
        doc = RawDocumentStore.objects.create(
            symbol=src,
            accession_no='acc-dirty-1',
            filing_date=date(2024, 5, 1),
            fiscal_year=2023,
            final_link='https://sec.gov/d',
        )
        # 51개 dirty + target 있음
        for i in range(51):
            SupplyChainEvidence.objects.create(
                source_document=doc,
                source_company=src,
                target_company=tgt,
                target_company_name='Target',
                relationship_type='SUPPLIES_TO',
                evidence_text=f'ev-{i}',
                system_confidence=0.8,
                neo4j_dirty=True,
            )

        alerts = run_post_batch_quality_checks(hours_back=24)
        assert any('Neo4j dirty' in a for a in alerts)

    def test_pending_queue_alert(self):
        from services.sec_pipeline.models import UnmatchedCompanyQueue
        from services.sec_pipeline.quality_checks import run_post_batch_quality_checks

        # 101개 pending → 100건 초과 알림
        for i in range(101):
            UnmatchedCompanyQueue.objects.create(
                raw_company_name=f'Pending Co {i}',
                source_symbol='AAPL',
                status='pending',
            )

        alerts = run_post_batch_quality_checks(hours_back=24)
        assert any('미매칭 큐' in a for a in alerts)


# =============================================================================
# Models — 보강 케이스
# =============================================================================

@pytest.mark.django_db
class TestModelMetaSettings:
    """모델 Meta 설정 확인 (db_table, ordering, get_latest_by, indexes)."""

    def test_raw_document_store_db_table(self):
        from services.sec_pipeline.models import RawDocumentStore
        assert RawDocumentStore._meta.db_table == 'sec_raw_document_store'

    def test_supply_chain_evidence_indexes(self):
        from services.sec_pipeline.models import SupplyChainEvidence
        index_fields = [
            tuple(idx.fields) for idx in SupplyChainEvidence._meta.indexes
        ]
        # neo4j_dirty 인덱스가 있어야 한다 (큐 조회 성능)
        assert any('neo4j_dirty' in fields for fields in index_fields)

    def test_business_model_snapshot_get_latest_by(self):
        from services.sec_pipeline.models import BusinessModelSnapshot
        # ordering이 -as_of_date여야 하며 get_latest_by는 as_of_date
        assert BusinessModelSnapshot._meta.get_latest_by == 'as_of_date'

    def test_company_alias_verbose_name_plural(self):
        from services.sec_pipeline.models import CompanyAlias
        assert CompanyAlias._meta.verbose_name_plural == 'Company aliases'

    def test_unmatched_queue_ordering_by_count_desc(self):
        from services.sec_pipeline.models import UnmatchedCompanyQueue
        assert UnmatchedCompanyQueue._meta.ordering == ['-occurrence_count']


@pytest.mark.django_db
class TestBusinessModelEvidenceCascade:
    """BusinessModelEvidence는 snapshot 삭제 시 함께 삭제."""

    def test_cascade_delete(self):
        from packages.shared.stocks.models import Stock
        from services.sec_pipeline.models import (
            BusinessModelEvidence,
            BusinessModelSnapshot,
            RawDocumentStore,
        )

        stock = Stock.objects.create(symbol='CSC', stock_name='Cascade Co')
        doc = RawDocumentStore.objects.create(
            symbol=stock,
            accession_no='acc-csc',
            filing_date=date(2024, 1, 1),
            fiscal_year=2023,
            final_link='https://sec.gov/c',
        )
        snap = BusinessModelSnapshot.objects.create(
            symbol=stock,
            source_document=doc,
            as_of_date=date(2024, 1, 1),
            direct_customer_contact='direct',
        )
        BusinessModelEvidence.objects.create(
            snapshot=snap,
            field_name='direct_customer_contact',
            evidence_text='evidence text',
            confidence=0.9,
        )

        assert BusinessModelEvidence.objects.count() == 1
        snap.delete()
        assert BusinessModelEvidence.objects.count() == 0


@pytest.mark.django_db
class TestFilingProcessLogOrdering:
    """FilingProcessLog는 -started_at 내림차순으로 정렬."""

    def test_ordering_desc_by_started_at(self):
        from services.sec_pipeline.models import FilingProcessLog

        for stage in ['fmp_metadata', 'sec_fetch', 'section_extract']:
            FilingProcessLog.objects.create(
                symbol='AAPL', stage=stage, status='success',
            )
        logs = list(FilingProcessLog.objects.all())
        # 가장 마지막에 생성된 게 첫 번째
        assert logs[0].stage == 'section_extract'
        assert logs[-1].stage == 'fmp_metadata'


# =============================================================================
# Extractor — 보강 케이스 (LLM은 전부 mock)
#
# 슬라이스 ④: extractor가 genai 직접호출 → shared/llm complete() 경유로 이관됨.
# 따라서 mock seam도 `GeminiExtractor._get_client`(제거됨) → `google.genai.Client`
# (코어 gemini provider가 생성)로 이동. 파싱·에러·조기반환 검증 의도는 그대로(행위 보존).
# 참고: tests/unit/sec_pipeline/test_extractor.py 의 동일 패턴.
# =============================================================================

@pytest.fixture
def extractor():
    from services.sec_pipeline.extractor import GeminiExtractor
    return GeminiExtractor()


@pytest.fixture(autouse=True)
def _gemini_key(settings):
    # complete()의 gemini provider(_resolve_api_key) + extractor._ensure_api_key 둘 다 키 필요.
    settings.GEMINI_API_KEY = "fake-key"


def _mock_genai_response(text):
    """genai generate_content 응답 mock. text + usage_metadata=None(코어 provider 토큰 추출 안전)."""
    response = MagicMock()
    response.text = text
    response.usage_metadata = None
    return response


def _patch_genai_client(text):
    """google.genai.Client patch — generate_content가 주어진 text를 반환.

    complete() → gemini provider → genai.Client(api_key).models.generate_content 경로를 가로챈다.
    호출자는 try/finally로 patcher.stop() 책임.
    """
    patcher = patch("google.genai.Client")
    mock_cls = patcher.start()
    mock_cls.return_value.models.generate_content.return_value = _mock_genai_response(text)
    return patcher, mock_cls


class TestExtractorEmptyInputs:
    """빈 입력은 LLM 호출 없이 즉시 반환 (genai.Client 미생성)."""

    def test_supply_chain_empty_list_returns_empty(self, extractor):
        patcher, mock_cls = _patch_genai_client('{}')
        try:
            result = extractor.extract_supply_chain('AAPL', 'Apple Inc', [])
            assert result == {'relationships': []}
            mock_cls.assert_not_called()
        finally:
            patcher.stop()

    def test_business_model_empty_list_returns_empty(self, extractor):
        patcher, mock_cls = _patch_genai_client('{}')
        try:
            result = extractor.extract_business_model('AAPL', 'Apple Inc', [])
            assert result == {}
            mock_cls.assert_not_called()
        finally:
            patcher.stop()


class TestExtractorMissingRelationshipsKey:
    """LLM이 'relationships' 키를 누락하면 빈 리스트로 보정."""

    def test_missing_key_defaults_to_empty(self, extractor):
        patcher, _ = _patch_genai_client(json.dumps({'something_else': []}))
        try:
            result = extractor.extract_supply_chain(
                'AAPL', 'Apple Inc', ['paragraph with supplier mention'],
            )
            assert result == {'relationships': []}
        finally:
            patcher.stop()


class TestExtractorJsonError:
    """LLM이 invalid JSON 반환 시 error 키 포함."""

    def test_supply_chain_json_error_returns_error(self, extractor):
        patcher, _ = _patch_genai_client('not valid json {')
        try:
            result = extractor.extract_supply_chain(
                'AAPL', 'Apple Inc', ['paragraph'],
            )
            assert result['relationships'] == []
            assert 'error' in result
            assert 'JSON parse' in result['error']
        finally:
            patcher.stop()

    def test_business_model_json_error_returns_error(self, extractor):
        patcher, _ = _patch_genai_client('broken { json')
        try:
            result = extractor.extract_business_model(
                'AAPL', 'Apple Inc', ['paragraph'],
            )
            assert 'error' in result
            assert 'JSON parse' in result['error']
        finally:
            patcher.stop()


class TestExtractorGenerateContentCall:
    """generate_content 호출 인자: contents=prompt(불변), config=provider GenerateContentConfig.

    구 TestExtractorClientReuse(_get_client 캐싱)를 대체. 슬라이스 ④에서 client 캐싱은
    extractor에서 제거되고 코어 gemini provider가 호출마다 genai.Client를 생성한다.
    따라서 캐싱 검증 대신, complete() 경유 후에도 생성 config가 보존되는지 검증한다.
    """

    def test_supply_chain_passes_prompt_and_config(self, extractor):
        from google.genai import types as gtypes

        patcher, mock_cls = _patch_genai_client(json.dumps({'relationships': []}))
        try:
            extractor.extract_supply_chain(
                'AAPL', 'Apple Inc', ['paragraph with supplier mention'],
            )
            call = mock_cls.return_value.models.generate_content.call_args
            # contents=prompt (불변 — 프롬프트는 그대로 전달)
            prompt_arg = call.kwargs['contents']
            assert 'AAPL' in prompt_arg
            assert 'paragraph with supplier mention' in prompt_arg
            # config = provider GenerateContentConfig (response_mime_type/temperature/thinking 보존)
            config = call.kwargs['config']
            assert isinstance(config, gtypes.GenerateContentConfig)
            assert config.response_mime_type == 'application/json'
            assert config.temperature == 0.1
            assert config.thinking_config is not None
            # max_output_tokens 미설정 (Gemini는 폴백 없음 — 현행 재현)
            assert config.max_output_tokens is None
        finally:
            patcher.stop()
