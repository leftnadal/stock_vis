"""
sec_pipeline 보충 단위 테스트.

기존 test_*.py에서 누락된 영역 보강:
- merger.py (계 전체 신규)
- exceptions.py (계 전체 신규)
- collector / extractor / normalizer / ticker_matcher / models / quality_checks 보강

HTTP 요청 및 LLM 호출은 전부 mock — 실제 SEC EDGAR / Gemini 호출 절대 금지.
"""

import json
from datetime import date, timedelta
from unittest.mock import MagicMock, patch

import pytest
from django.utils import timezone

# ===========================================================================
# Helpers
# ===========================================================================

def _mock_response(json_data=None, text=None, status_code=200):
    resp = MagicMock()
    resp.status_code = status_code
    resp.raise_for_status = MagicMock()
    if json_data is not None:
        resp.json.return_value = json_data
    if text is not None:
        resp.text = text
    return resp


def _mock_genai_response(text):
    response = MagicMock()
    response.text = text
    response.usage_metadata = None  # 코어 provider 토큰 추출(int) 안전
    return response


# ===========================================================================
# 1. merger.py 신규 테스트 (9건)
# ===========================================================================

class TestMergeRelationship:
    """merger.merge_relationship 단위 테스트."""

    def test_more_specific_rel_type_wins(self):
        from services.sec_pipeline.merger import merge_relationship

        existing = {
            'rel_type': 'DEPENDS_ON',  # specificity=1
            'confidence': 0.5,
            'sources': ['llm_relation'],
        }
        new = {
            'rel_type': 'SUPPLIES_TO',  # specificity=5
            'confidence': 0.6,
            'source': 'sec_10k',
            'evidence_text': 'manufactures chips',
        }
        merged = merge_relationship(existing, new)
        assert merged['rel_type'] == 'SUPPLIES_TO'

    def test_less_specific_rel_type_does_not_overwrite(self):
        from services.sec_pipeline.merger import merge_relationship

        existing = {
            'rel_type': 'SUPPLIES_TO',  # specificity=5
            'confidence': 0.5,
            'sources': ['sec_10k'],
        }
        new = {
            'rel_type': 'DEPENDS_ON',  # specificity=1
            'confidence': 0.6,
            'source': 'llm_relation',
        }
        merged = merge_relationship(existing, new)
        assert merged['rel_type'] == 'SUPPLIES_TO'

    def test_sources_deduplicated_and_sorted(self):
        from services.sec_pipeline.merger import merge_relationship

        existing = {
            'rel_type': 'SUPPLIES_TO',
            'confidence': 0.5,
            'sources': ['sec_10k', 'llm_relation'],
        }
        new = {
            'rel_type': 'SUPPLIES_TO',
            'confidence': 0.5,
            'source': 'sec_10k',  # 중복
        }
        merged = merge_relationship(existing, new)
        assert merged['sources'] == sorted(['sec_10k', 'llm_relation'])

    def test_confidence_bounded_at_0_99(self):
        from services.sec_pipeline.merger import merge_relationship

        existing = {
            'rel_type': 'SUPPLIES_TO',
            'confidence': 0.98,
            'sources': ['sec_10k'],
        }
        new = {
            'rel_type': 'SUPPLIES_TO',
            'confidence': 0.99,
            'source': 'sec_10k',
        }
        merged = merge_relationship(existing, new)
        assert merged['confidence'] <= 0.99

    def test_confidence_boosted_upward(self):
        from services.sec_pipeline.merger import merge_relationship

        existing = {
            'rel_type': 'SUPPLIES_TO',
            'confidence': 0.5,
            'sources': ['sec_10k'],
        }
        new = {
            'rel_type': 'SUPPLIES_TO',
            'confidence': 0.8,
            'source': 'llm_relation',
        }
        merged = merge_relationship(existing, new)
        # boost 공식: 0.5 + (1-0.5) * 0.8 * 0.3 = 0.62
        assert merged['confidence'] > 0.5
        assert merged['confidence'] <= 0.99

    def test_evidence_text_appended_to_facets(self):
        from services.sec_pipeline.merger import merge_relationship

        existing = {
            'rel_type': 'SUPPLIES_TO',
            'confidence': 0.5,
            'sources': ['sec_10k'],
            'relation_facets': ['fact A'],
        }
        new = {
            'rel_type': 'SUPPLIES_TO',
            'confidence': 0.5,
            'source': 'sec_10k',
            'evidence_text': 'fact B',
        }
        merged = merge_relationship(existing, new)
        assert 'fact A' in merged['relation_facets']
        assert 'fact B' in merged['relation_facets']

    def test_evidence_text_dedup_in_facets(self):
        from services.sec_pipeline.merger import merge_relationship

        existing = {
            'rel_type': 'SUPPLIES_TO',
            'confidence': 0.5,
            'sources': ['sec_10k'],
            'relation_facets': ['fact A'],
        }
        new = {
            'rel_type': 'SUPPLIES_TO',
            'confidence': 0.5,
            'source': 'sec_10k',
            'evidence_text': 'fact A',  # 중복
        }
        merged = merge_relationship(existing, new)
        assert merged['relation_facets'].count('fact A') == 1

    def test_facets_capped_at_five(self):
        from services.sec_pipeline.merger import merge_relationship

        existing = {
            'rel_type': 'SUPPLIES_TO',
            'confidence': 0.5,
            'sources': ['sec_10k'],
            'relation_facets': ['f1', 'f2', 'f3', 'f4', 'f5'],
        }
        new = {
            'rel_type': 'SUPPLIES_TO',
            'confidence': 0.5,
            'source': 'sec_10k',
            'evidence_text': 'f6',
        }
        merged = merge_relationship(existing, new)
        assert len(merged['relation_facets']) == 5
        # 마지막 5개 (f2~f6)
        assert 'f6' in merged['relation_facets']
        assert 'f1' not in merged['relation_facets']


@pytest.mark.django_db
class TestCalculateEdgeDqs:
    """merger.calculate_edge_dqs DB 통합 테스트."""

    def test_no_evidence_returns_zero(self):
        from services.sec_pipeline.merger import calculate_edge_dqs

        result = calculate_edge_dqs('AAPL', 'TSM')
        assert result['source_count'] == 0
        assert result['source_types'] == []
        assert result['_dqs_total'] == 0

    def test_dqs_keys_separate_internal_and_user(self):
        """원칙 6: 내부용(_*) 키와 사용자용 키 분리."""
        from services.sec_pipeline.merger import calculate_edge_dqs

        result = calculate_edge_dqs('AAPL', 'TSM')
        internal_keys = {'_sufficiency', '_diversity', '_reliability', '_dqs_total'}
        user_keys = {'source_count', 'source_types'}
        assert internal_keys.issubset(result.keys())
        assert user_keys.issubset(result.keys())


# ===========================================================================
# 2. exceptions.py 신규 테스트 (5건)
# ===========================================================================

class TestExceptions:
    """sec_pipeline.exceptions 5개 예외 클래스 계층 검증."""

    def test_filing_collection_error_is_exception(self):
        from services.sec_pipeline.exceptions import FilingCollectionError
        assert issubclass(FilingCollectionError, Exception)

    def test_fmp_api_error_inherits_base(self):
        from services.sec_pipeline.exceptions import FilingCollectionError, FMPApiError
        assert issubclass(FMPApiError, FilingCollectionError)

    def test_sec_fetch_error_inherits_base(self):
        from services.sec_pipeline.exceptions import FilingCollectionError, SECFetchError
        assert issubclass(SECFetchError, FilingCollectionError)

    def test_section_extraction_error_inherits_base(self):
        from services.sec_pipeline.exceptions import (
            FilingCollectionError,
            SectionExtractionError,
        )
        assert issubclass(SectionExtractionError, FilingCollectionError)

    def test_llm_extraction_error_raisable_with_message(self):
        from services.sec_pipeline.exceptions import LLMExtractionError

        with pytest.raises(LLMExtractionError) as exc_info:
            raise LLMExtractionError('Gemini timeout')
        assert 'Gemini timeout' in str(exc_info.value)


# ===========================================================================
# 3. collector 보강 (4건)
# ===========================================================================

@pytest.fixture
def collector():
    from services.sec_pipeline.collector import SECFilingCollector
    c = SECFilingCollector()
    c._cik_cache.clear()
    return c


class TestCollectorSupplementary:
    """기존 test_collector*.py에서 누락된 시나리오."""

    def test_extract_sections_returns_required_keys(self, collector):
        """extract_sections는 무조건 3개 키를 반환해야 한다."""
        sections = collector.extract_sections('<html></html>')
        assert set(sections.keys()) == {'item_1', 'item_1a', 'item_7'}

    def test_html_to_text_returns_string(self, collector):
        """_html_to_text는 어떤 입력에 대해서도 str을 반환."""
        result = collector._html_to_text('<p>plain</p>')
        assert isinstance(result, str)
        assert 'plain' in result

    @patch('services.sec_pipeline.collector.requests.get')
    @patch('services.sec_pipeline.collector.time.sleep')
    def test_metadata_iterates_filings_until_10k(self, mock_sleep, mock_get, collector):
        """10-K가 두 번째 항목에 있으면 정상적으로 찾아내야 한다."""
        collector._cik_cache['AAPL'] = '0000320193'
        data = {
            "filings": {"recent": {
                "form": ["10-Q", "10-K", "8-K"],
                "accessionNumber": ["acc-q", "acc-10k", "acc-8k"],
                "filingDate": ["2024-08-01", "2023-11-03", "2023-06-15"],
                "primaryDocument": ["q.htm", "10k.htm", "8k.htm"],
            }}
        }
        mock_get.return_value = _mock_response(json_data=data)

        result = collector.get_filing_metadata('AAPL')
        assert result is not None
        assert result['accession_no'] == 'acc-10k'

    def test_section_patterns_has_item_8_for_end_marker(self, collector):
        """item_7 종료 검출용으로 item_8 패턴이 필요하다."""
        assert 'item_8' in collector.SECTION_PATTERNS
        assert len(collector.SECTION_PATTERNS['item_8']) > 0


# ===========================================================================
# 4. extractor 보강 (3건)
# ===========================================================================

@pytest.fixture
def extractor():
    from services.sec_pipeline.extractor import GeminiExtractor
    return GeminiExtractor()


class TestExtractorSupplementary:
    """기존 test_extractor*.py 보강.

    슬라이스 ④: genai 직접호출 → shared/llm complete() 경유로 이관됨. mock seam도
    `GeminiExtractor._get_client`(제거됨) → `google.genai.Client`(코어 provider 생성)로 이동.
    generic 예외는 코어 provider `_classify`가 LLMError 하위로 재분류 후 재전파될 수 있어
    (예: msg에 'quota' → LLMRateLimitError) 예외 전파 의도는 보존하되 타입을 실동작에 맞춘다.
    """

    def test_supply_chain_generic_exception_reraises(self, extractor, settings):
        """JSONDecodeError 이외의 예외는 re-raise되어야 한다 (Celery retry용).

        'quota exceeded'는 코어 provider `_classify`가 LLMRateLimitError로 재분류하므로
        extractor의 `except Exception: raise`가 그 타입을 그대로 올린다(전파 의도 보존).
        """
        from packages.shared.llm.types import LLMRateLimitError

        settings.GEMINI_API_KEY = "fake-key"
        patcher = patch("google.genai.Client")
        mock_cls = patcher.start()
        mock_cls.return_value.models.generate_content.side_effect = RuntimeError(
            'quota exceeded'
        )
        try:
            with pytest.raises(LLMRateLimitError, match='quota exceeded'):
                extractor.extract_supply_chain('AAPL', 'Apple Inc.', ['some text'])
        finally:
            patcher.stop()

    def test_business_model_generic_exception_reraises(self, extractor, settings):
        """BM extractor도 동일하게 generic exception은 re-raise.

        'network'는 `_classify` 규칙에 안 걸려 원본 ConnectionError가 그대로 전파된다.
        """
        settings.GEMINI_API_KEY = "fake-key"
        patcher = patch("google.genai.Client")
        mock_cls = patcher.start()
        mock_cls.return_value.models.generate_content.side_effect = ConnectionError(
            'network'
        )
        try:
            with pytest.raises(ConnectionError, match='network'):
                extractor.extract_business_model('AAPL', 'Apple', ['some text'])
        finally:
            patcher.stop()

    def test_supply_chain_returns_empty_when_relationships_is_empty_list(
        self, extractor, settings,
    ):
        """LLM이 빈 리스트 반환해도 형식이 맞으면 그대로 반환."""
        settings.GEMINI_API_KEY = "fake-key"
        patcher = patch("google.genai.Client")
        mock_cls = patcher.start()
        mock_cls.return_value.models.generate_content.return_value = (
            _mock_genai_response(json.dumps({'relationships': []}))
        )
        try:
            result = extractor.extract_supply_chain('AAPL', 'Apple Inc.', ['text'])
        finally:
            patcher.stop()
        assert result == {'relationships': []}


# ===========================================================================
# 5. normalizer 보강 (3건)
# ===========================================================================

class TestNormalizerSupplementary:
    """기존 test_normalizer*.py 보강."""

    def test_filter_paragraphs_respects_max_one(self):
        """max_paragraphs=1이면 정확히 1개만 반환."""
        from services.sec_pipeline.normalizer import filter_paragraphs

        text = '\n'.join([
            f"Paragraph {i}: our supplier provides raw material and components. " + "x " * 30
            for i in range(5)
        ])
        result = filter_paragraphs(text, max_paragraphs=1)
        assert len(result) == 1

    def test_filter_paragraphs_case_insensitive_keyword_match(self):
        from services.sec_pipeline.normalizer import filter_paragraphs

        text = (
            "Our SUPPLIER provides CRITICAL COMPONENTS and RAW MATERIAL via our DISTRIBUTOR. "
            + "x " * 30
        )
        result = filter_paragraphs(text)
        assert len(result) >= 1
        assert 'SUPPLIER' in result[0]

    def test_normalize_section_all_strips_per_section(self):
        from services.sec_pipeline.normalizer import normalize_section_all

        sections = {
            'item_1': '   leading and trailing spaces   ',
            'item_7': '\n\n\n\nmany newlines\n\n\n\n',
        }
        result = normalize_section_all(sections)
        # _clean_text가 trim + 연속 newline 정리
        assert result.startswith('leading')
        assert '\n\n\n' not in result


# ===========================================================================
# 6. ticker_matcher 보강 (4건)
# ===========================================================================

@pytest.fixture
def matcher():
    from services.sec_pipeline.ticker_matcher import TickerMatcher
    m = TickerMatcher()
    m._loaded = False
    m._stock_map = {}
    return m


class TestTickerMatcherSupplementary:
    """기존 test_ticker_matcher*.py 보강."""

    def test_clean_name_with_plc_suffix(self):
        from services.sec_pipeline.ticker_matcher import TickerMatcher
        assert TickerMatcher._clean_name('BP PLC') == 'bp'

    def test_clean_name_with_ag_suffix(self):
        from services.sec_pipeline.ticker_matcher import TickerMatcher
        assert TickerMatcher._clean_name('Siemens AG') == 'siemens'

    def test_match_returns_tuple_of_two(self, matcher):
        """반환 형식이 항상 (ticker_or_none, method_or_none)인지 보장."""
        ticker, method = matcher.match('')
        assert ticker is None
        assert method is None

    @pytest.mark.django_db
    def test_match_with_queue_creates_pending_entry_when_unmatched(self, matcher):
        """매칭 실패 시 UnmatchedCompanyQueue에 pending 적재."""
        from packages.shared.stocks.models import Stock
        from services.sec_pipeline.models import (
            RawDocumentStore,
            SupplyChainEvidence,
            UnmatchedCompanyQueue,
        )

        source = Stock.objects.create(symbol='AAPL', stock_name='Apple Inc.', sector='Technology')
        doc = RawDocumentStore.objects.create(
            symbol=source, accession_no='acc-tmq-1',
            filing_date=date(2023, 11, 1), fiscal_year=2023,
            final_link='https://sec.gov/aapl',
        )
        evidence = SupplyChainEvidence.objects.create(
            source_document=doc, source_company=source,
            target_company_name='Totally Unknown Corp XYZ',
            relationship_type='SUPPLIES_TO',
            evidence_text='ev',
        )

        with patch.object(matcher, '_ensure_loaded'):
            ticker, method = matcher.match_with_queue(
                'Totally Unknown Corp XYZ', evidence, doc, 'AAPL',
            )

        assert ticker is None
        assert UnmatchedCompanyQueue.objects.filter(
            raw_company_name='Totally Unknown Corp XYZ', status='pending',
        ).exists()


# ===========================================================================
# 7. models 보강 (4건)
# ===========================================================================

@pytest.mark.django_db
class TestModelsSupplementary:
    """기존 test_models*.py 보강."""

    def test_filing_process_log_str_format(self):
        from services.sec_pipeline.models import FilingProcessLog

        log = FilingProcessLog.objects.create(
            symbol='AAPL', stage='sec_fetch', status='success',
        )
        s = str(log)
        assert 'AAPL' in s
        assert 'sec_fetch' in s
        assert 'success' in s

    def test_unmatched_company_queue_str_with_count(self):
        from services.sec_pipeline.models import UnmatchedCompanyQueue

        entry = UnmatchedCompanyQueue.objects.create(
            raw_company_name='Foundry Asia', source_symbol='AAPL',
            occurrence_count=7,
        )
        s = str(entry)
        assert 'Foundry Asia' in s
        assert '7' in s

    def test_company_alias_with_country_does_not_violate_unique(self):
        """unique_together=(alias, context_sector) 이므로 country는 다르고 sector 같으면 충돌."""
        from django.db import IntegrityError, transaction

        from services.sec_pipeline.models import CompanyAlias

        CompanyAlias.objects.create(
            alias='Acme', ticker='ACM1',
            context_sector='Technology', context_country='US',
        )
        with pytest.raises(IntegrityError):
            with transaction.atomic():
                CompanyAlias.objects.create(
                    alias='Acme', ticker='ACM2',
                    context_sector='Technology',  # 동일
                    context_country='UK',  # 다름 — unique key에 미포함
                )

    def test_supply_chain_evidence_cascade_on_document_delete(self):
        """RawDocumentStore 삭제 시 SupplyChainEvidence도 cascade."""
        from packages.shared.stocks.models import Stock
        from services.sec_pipeline.models import RawDocumentStore, SupplyChainEvidence

        stock = Stock.objects.create(symbol='AAPL', stock_name='Apple Inc.')
        doc = RawDocumentStore.objects.create(
            symbol=stock, accession_no='acc-csc-1',
            filing_date=date(2023, 11, 1), fiscal_year=2023,
            final_link='https://sec.gov/csc',
        )
        SupplyChainEvidence.objects.create(
            source_document=doc, source_company=stock,
            target_company_name='Cascade Target',
            relationship_type='SUPPLIES_TO',
            evidence_text='ev',
        )
        assert SupplyChainEvidence.objects.count() == 1
        doc.delete()
        assert SupplyChainEvidence.objects.count() == 0


# ===========================================================================
# 8. quality_checks 보강 (4건)
# ===========================================================================

@pytest.fixture
def qc_stock(db):
    from packages.shared.stocks.models import Stock
    return Stock.objects.create(symbol='QC1', stock_name='QC One')


@pytest.fixture
def qc_doc(qc_stock):
    from services.sec_pipeline.models import RawDocumentStore
    return RawDocumentStore.objects.create(
        symbol=qc_stock, accession_no='acc-qcs-001',
        filing_date=date(2023, 11, 1), fiscal_year=2023,
        final_link='https://sec.gov/qcs', status='success',
    )


@pytest.mark.django_db
class TestQualityChecksSupplementary:
    """기존 test_quality_checks*.py 보강."""

    def test_low_failure_rate_no_alert(self, qc_stock):
        """실패율 ≤ 20%면 알림 없음."""
        from services.sec_pipeline.models import RawDocumentStore
        from services.sec_pipeline.quality_checks import run_post_batch_quality_checks

        for i in range(10):
            RawDocumentStore.objects.create(
                symbol=qc_stock, accession_no=f'acc-ok-{i}',
                filing_date=date(2023, 11, 1), fiscal_year=2023,
                final_link=f'https://sec.gov/ok{i}', status='success',
            )
        RawDocumentStore.objects.create(
            symbol=qc_stock, accession_no='acc-fail-1',
            filing_date=date(2023, 11, 1), fiscal_year=2023,
            final_link='https://sec.gov/fail', status='failed',
        )
        # 1/11 = ~9% < 20%
        alerts = run_post_batch_quality_checks(hours_back=24)
        assert not any('실패율' in a for a in alerts)

    def test_old_records_outside_window_ignored(self, qc_stock):
        """hours_back 윈도우 밖의 레코드는 무시되어야 한다."""
        from services.sec_pipeline.models import RawDocumentStore
        from services.sec_pipeline.quality_checks import run_post_batch_quality_checks

        old_doc = RawDocumentStore.objects.create(
            symbol=qc_stock, accession_no='acc-old-1',
            filing_date=date(2020, 1, 1), fiscal_year=2019,
            final_link='https://sec.gov/old', status='failed',
        )
        # collected_at은 auto_now_add라 강제 변경
        RawDocumentStore.objects.filter(pk=old_doc.pk).update(
            collected_at=timezone.now() - timedelta(hours=48),
        )

        alerts = run_post_batch_quality_checks(hours_back=24)
        # 24시간 전 레코드는 윈도우 밖 → 카운트 안됨 → 알림 없음
        assert not any('실패율' in a for a in alerts)

    def test_dashboard_stats_avg_confidence_rounded(self, qc_stock, qc_doc):
        """avg_confidence는 3자리로 반올림."""
        from services.sec_pipeline.models import SupplyChainEvidence
        from services.sec_pipeline.quality_checks import get_dashboard_stats

        SupplyChainEvidence.objects.create(
            source_document=qc_doc, source_company=qc_stock,
            target_company=qc_stock, target_company_name='X',
            relationship_type='SUPPLIES_TO',
            evidence_text='ev', system_confidence=0.123456789,
        )
        result = get_dashboard_stats()
        avg = result['track_a']['avg_confidence']
        # round(..., 3)
        assert avg == round(0.123456789, 3)

    def test_dashboard_stats_neo4j_pending_excludes_unmatched(self, qc_stock, qc_doc):
        """neo4j_pending = dirty=True AND target IS NOT NULL — unmatched는 제외."""
        from services.sec_pipeline.models import SupplyChainEvidence
        from services.sec_pipeline.quality_checks import get_dashboard_stats

        # matched + dirty=True → pending에 포함
        SupplyChainEvidence.objects.create(
            source_document=qc_doc, source_company=qc_stock,
            target_company=qc_stock, target_company_name='M',
            relationship_type='SUPPLIES_TO',
            evidence_text='ev', neo4j_dirty=True,
        )
        # unmatched + dirty=True → pending에서 제외
        SupplyChainEvidence.objects.create(
            source_document=qc_doc, source_company=qc_stock,
            target_company=None, target_company_name='U',
            relationship_type='SUPPLIES_TO',
            evidence_text='ev', neo4j_dirty=True,
        )
        result = get_dashboard_stats()
        assert result['track_a']['neo4j_pending'] == 1


# ===========================================================================
# 9. validators 보강 (3건)
# ===========================================================================

class TestValidatorsSupplementary:
    """기존 test_validators*.py 보강."""

    def test_empty_sections_with_valid_full_text_no_warnings(self):
        """모든 섹션이 비어있으면 길이 경고도 없어야 한다 (continue)."""
        from services.sec_pipeline.validators import validate_extracted_sections

        full_text = (
            "Item 1. Business overview.\n"
            "Item 1A. Risk factors.\n"
            "Item 7. MD&A.\n"
            "Item 8. Financial statements.\n"
        )
        sections = {'item_1': '', 'item_1a': '', 'item_7': ''}
        validated, warnings = validate_extracted_sections(sections, full_text)
        # 빈 섹션은 길이 검증 스킵
        for w in warnings:
            assert 'WARN: item_1 too short' not in w
            assert 'WARN: item_1a too short' not in w
            assert 'WARN: item_7 too short' not in w

    def test_missing_item_1_in_full_text_skips_order_check(self):
        """item_1 또는 item_7이 원문에 없으면 순서 검증 스킵."""
        from services.sec_pipeline.validators import validate_extracted_sections

        # item_1 없음 → 순서 검증 스킵
        full_text = "Item 7. MD&A discussion." + " content" * 200
        sections = {
            'item_1': '',
            'item_1a': '',
            'item_7': 'Item 7. MD&A discussion.' + ' content' * 200,
        }
        validated, warnings = validate_extracted_sections(sections, full_text)
        # 순서 위반 FAIL이 없어야 함
        order_fails = [w for w in warnings if 'order violation' in w]
        assert order_fails == []

    def test_section_within_expected_range_no_length_warning(self):
        """EXPECTED_MIN_LENGTH 이상 길이는 warn 없음."""
        from services.sec_pipeline.validators import (
            EXPECTED_MIN_LENGTH,
            validate_extracted_sections,
        )

        long_text = (
            'Item 1. Description of Business. '
            + ('Apple supplies many products to consumers worldwide. ' * 200)
        )
        assert len(long_text) >= EXPECTED_MIN_LENGTH

        full_text = long_text + '\n\nItem 7. MD&A. ' + ('details. ' * 100)
        sections = {
            'item_1': long_text,
            'item_1a': '',
            'item_7': '',
        }
        validated, warnings = validate_extracted_sections(sections, full_text)
        for w in warnings:
            assert 'WARN: item_1' not in w
