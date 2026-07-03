"""
sec_pipeline 추가 단위 테스트 — 기존 19개 파일에서 누락된 시나리오 보완.

타겟 영역:
- collector.extract_sections_fallback (edgartools 동작 mock — success/exception/no-filing/KeyError)
- collector 의 collect() partial 상태 분기
- extractor 의 thinking_budget=0 및 빈 API 키
- normalizer 의 track 파라미터 명시 호출
- ticker_matcher.match_with_queue 의 source-symbol 미존재 + target 미존재 분기
- models 의 JSONField 영속화, choices 유효값
- quality_checks 의 healthy 상태 / hours_back 변경 / rounding
- validators 의 길이 WARN / 부분 헤딩

HTTP 요청과 Gemini 호출은 전부 mock.
"""

import json
import sys
from datetime import date, timedelta
from unittest.mock import MagicMock, patch

import pytest
from django.utils import timezone

from services.sec_pipeline.collector import SECFilingCollector
from services.sec_pipeline.extractor import GeminiExtractor
from services.sec_pipeline.normalizer import (
    _clean_text,
    filter_paragraphs,
    normalize_section_all,
)
from services.sec_pipeline.ticker_matcher import TickerMatcher
from services.sec_pipeline.validators import (
    MAX_SECTION_LENGTH,
    _check_item_order,
    validate_extracted_sections,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def collector():
    c = SECFilingCollector()
    c._cik_cache.clear()
    return c


@pytest.fixture
def extractor():
    return GeminiExtractor()


@pytest.fixture
def matcher():
    m = TickerMatcher()
    m._loaded = False
    m._stock_map = {}
    return m


def _mock_genai_response(text):
    response = MagicMock()
    response.text = text
    response.usage_metadata = None  # 코어 provider 토큰 추출(int) 안전
    return response


def _patch_genai_client(text):
    """google.genai.Client를 patch해 generate_content가 주어진 text를 반환.

    슬라이스 ④: complete() → gemini provider → genai.Client(api_key).models.generate_content
    경로를 가로챈다(구 GeminiExtractor._get_client seam 대체).
    """
    patcher = patch("google.genai.Client")
    mock_cls = patcher.start()
    mock_cls.return_value.models.generate_content.return_value = _mock_genai_response(text)
    return patcher, mock_cls


# ===========================================================================
# Collector — extract_sections_fallback 동작 시나리오
# ===========================================================================

class TestExtractSectionsFallbackBehavior:
    """edgartools 가 설치된 가상의 시나리오를 mock 으로 재현."""

    def test_fallback_success_with_mocked_edgartools(self, collector):
        """edgartools.Company → filing.document 가 dict-like 일 때 섹션 추출."""
        fake_doc = {
            'Item 1': 'Apple business description.',
            'Item 1A': 'Apple risk factors.',
            'Item 7': "Apple MD&A.",
        }
        fake_filing = MagicMock()
        fake_filing.document = fake_doc

        fake_filings_collection = MagicMock()
        fake_filings_collection.latest.return_value = fake_filing

        fake_company = MagicMock()
        fake_company.get_filings.return_value = fake_filings_collection

        fake_module = MagicMock()
        fake_module.Company.return_value = fake_company

        with patch.dict(sys.modules, {'edgartools': fake_module}):
            result = collector.extract_sections_fallback('AAPL')

        assert result is not None
        assert result['item_1'] == 'Apple business description.'
        assert result['item_1a'] == 'Apple risk factors.'
        assert result['item_7'] == "Apple MD&A."

    def test_fallback_returns_none_when_no_filing(self, collector):
        """edgartools 가 filing 을 못 찾으면 None 반환."""
        fake_filings_collection = MagicMock()
        fake_filings_collection.latest.return_value = None

        fake_company = MagicMock()
        fake_company.get_filings.return_value = fake_filings_collection

        fake_module = MagicMock()
        fake_module.Company.return_value = fake_company

        with patch.dict(sys.modules, {'edgartools': fake_module}):
            result = collector.extract_sections_fallback('AAPL')

        assert result is None

    def test_fallback_handles_keyerror_per_section(self, collector):
        """document[Item X] 가 KeyError 던지면 해당 섹션만 빈 문자열로 처리."""
        class _Doc:
            def __getitem__(self, key):
                if key == 'Item 1':
                    return 'Business text.'
                raise KeyError(key)

        fake_filing = MagicMock()
        fake_filing.document = _Doc()

        fake_filings_collection = MagicMock()
        fake_filings_collection.latest.return_value = fake_filing

        fake_company = MagicMock()
        fake_company.get_filings.return_value = fake_filings_collection

        fake_module = MagicMock()
        fake_module.Company.return_value = fake_company

        with patch.dict(sys.modules, {'edgartools': fake_module}):
            result = collector.extract_sections_fallback('AAPL')

        assert result is not None
        assert result['item_1'] == 'Business text.'
        # KeyError 가 발생한 섹션은 빈 문자열
        assert result['item_1a'] == ''
        assert result['item_7'] == ''

    def test_fallback_generic_exception_returns_none(self, collector):
        """Company() 가 알 수 없는 예외를 던지면 None 반환 (warning 로그)."""
        fake_module = MagicMock()
        fake_module.Company.side_effect = RuntimeError("network broken")

        with patch.dict(sys.modules, {'edgartools': fake_module}):
            result = collector.extract_sections_fallback('AAPL')

        assert result is None


# ===========================================================================
# Collector — _get_cik 캐시 / collect() partial 분기
# ===========================================================================

class TestCikCacheSharedAcrossInstances:
    def test_cik_cache_is_class_level(self):
        """_cik_cache 는 클래스 레벨이라 새 인스턴스도 캐시 공유."""
        c1 = SECFilingCollector()
        c1._cik_cache.clear()
        c1._cik_cache['AAPL'] = '0000320193'

        c2 = SECFilingCollector()
        # c2 는 별도 인스턴스지만 클래스 캐시 공유
        with patch('services.sec_pipeline.collector.requests.get') as mock_get:
            cik = c2._get_cik('AAPL')
            assert cik == '0000320193'
            mock_get.assert_not_called()


class TestCollectPartialStatus:
    def test_collect_marks_partial_when_only_two_sections(self, collector):
        """3 섹션 중 2개만 있고 FAIL 없으면 partial."""
        meta = {
            'symbol': 'AAPL',
            'accession_no': 'acc-partial',
            'filing_date': '2023-11-03',
            'fiscal_year': 2023,
            'final_link': 'https://sec.gov/x',
        }
        sections = {
            'item_1': 'Item 1. Business desc ' + ('a ' * 1500),
            'item_1a': '',
            'item_7': "Item 7. MD&A " + ('b ' * 1500),
        }
        with patch.object(collector, 'get_filing_metadata', return_value=meta), \
             patch.object(collector, 'fetch_filing_html', return_value='<html/>'), \
             patch.object(collector, 'extract_sections', return_value=sections), \
             patch('services.sec_pipeline.collector.validate_extracted_sections',
                   return_value=(sections, [])):
            result = collector.collect('AAPL')
        # 비어있지 않은 섹션 = 2 (item_1, item_7) → partial
        assert result['status'] == 'partial'

    def test_collect_uppercases_symbol_in_output(self, collector):
        """입력 symbol 이 소문자여도 결과에 대문자로 반영."""
        meta = {
            'symbol': 'AAPL',
            'accession_no': 'acc-up',
            'filing_date': '2023-11-03',
            'fiscal_year': 2023,
            'final_link': 'https://sec.gov/x',
        }
        sections = {'item_1': 'a' * 1000, 'item_1a': 'b' * 1000, 'item_7': 'c' * 1000}
        with patch.object(collector, 'get_filing_metadata', return_value=meta), \
             patch.object(collector, 'fetch_filing_html', return_value='<html/>'), \
             patch.object(collector, 'extract_sections', return_value=sections), \
             patch('services.sec_pipeline.collector.validate_extracted_sections',
                   return_value=(sections, [])):
            result = collector.collect('aapl')  # 소문자 입력
        assert result['symbol'] == 'AAPL'


class TestSectionPatternsRegexCompile:
    def test_all_patterns_are_valid_regex(self, collector):
        """SECTION_PATTERNS 의 모든 패턴이 컴파일 가능."""
        import re as re_mod
        for key, patterns in collector.SECTION_PATTERNS.items():
            for pat in patterns:
                # 컴파일 실패 시 re.error 가 발생
                re_mod.compile(pat)


# ===========================================================================
# Extractor — thinking_budget / 빈 API 키
# ===========================================================================

class TestExtractorThinkingBudget:
    def test_thinking_budget_is_zero(self, extractor, settings):
        """thinking_config.thinking_budget=0 으로 호출되어 빠른 응답."""
        settings.GEMINI_API_KEY = "fake-key"
        patcher, mock_cls = _patch_genai_client('{}')
        try:
            extractor.extract_business_model('AAPL', 'Apple Inc.', ['text'])
            # complete() → gemini provider → genai.Client().models.generate_content
            kwargs = mock_cls.return_value.models.generate_content.call_args.kwargs
        finally:
            patcher.stop()
        config = kwargs['config']
        # provider GenerateContentConfig 에 extra(thinking_config) 보존
        assert getattr(config.thinking_config, 'thinking_budget', None) == 0
        # temperature·response_mime_type 보존, max_output_tokens 미설정(현행 재현)
        assert config.temperature == 0.1
        assert config.response_mime_type == 'application/json'
        assert getattr(config, 'max_output_tokens', None) is None
        # contents=prompt 불변(prompt 자체는 변환 없이 전달)
        assert kwargs['contents'] is not None


class TestExtractorEmptyApiKey:
    def test_empty_string_api_key_raises(self, extractor):
        """API 키가 빈 문자열인 경우 falsy 체크에 걸려 ValueError.

        슬라이스 ④: 구 _get_client → _ensure_api_key 로 rename(키 조기 검증 동작 보존).
        """
        with patch('services.sec_pipeline.extractor.settings') as mock_settings:
            mock_settings.GEMINI_API_KEY = ''
            with pytest.raises(ValueError, match="GEMINI_API_KEY"):
                extractor._ensure_api_key()


class TestExtractSupplyChainEmptyRelationships:
    def test_empty_relationships_array_preserved(self, extractor, settings):
        """LLM 이 {relationships: []} 반환하면 빈 리스트 그대로 보존."""
        settings.GEMINI_API_KEY = "fake-key"
        patcher, _ = _patch_genai_client(json.dumps({'relationships': []}))
        try:
            result = extractor.extract_supply_chain('AAPL', 'Apple Inc.', ['filler text'])
        finally:
            patcher.stop()
        assert result == {'relationships': []}


# ===========================================================================
# Normalizer — track 파라미터 명시 / 추가 케이스
# ===========================================================================

class TestNormalizerTrackParam:
    def test_filter_paragraphs_explicit_track(self):
        """track='supply_chain' 명시 호출도 동일 결과."""
        text = "Our supplier provides raw material to our factory. " + "x " * 30
        result_default = filter_paragraphs(text)
        result_explicit = filter_paragraphs(text, track='supply_chain')
        assert result_default == result_explicit

    def test_normalize_section_excludes_item_1a(self):
        """Track A 는 Item 1 + 7 만 사용 (Item 1A 제외)."""
        sections = {
            'item_1': 'BUSINESS_AAA',
            'item_1a': 'RISK_BBB',
            'item_7': 'MDA_CCC',
        }
        result = normalize_section_all(sections)
        assert 'BUSINESS_AAA' in result
        assert 'MDA_CCC' in result
        assert 'RISK_BBB' not in result


class TestCleanTextExtraCases:
    def test_clean_text_collapses_tabs(self):
        """탭 문자도 다중 공백 정리 대상."""
        text = 'hello\t\t\tworld'
        result = _clean_text(text)
        assert '\t\t' not in result

    def test_clean_text_preserves_single_newline(self):
        """단일 \\n 은 보존 (문단 구분 의미)."""
        text = 'line1\nline2'
        result = _clean_text(text)
        assert 'line1\nline2' in result


# ===========================================================================
# TickerMatcher — match_with_queue 분기
# ===========================================================================

@pytest.mark.django_db
class TestMatchWithQueueExtra:
    def test_source_symbol_without_stock_uses_empty_sector(self, matcher):
        """source_symbol 에 해당하는 Stock 이 없으면 context_sector='' 로 매칭."""
        from packages.shared.stocks.models import Stock
        from services.sec_pipeline.models import (
            RawDocumentStore,
            SupplyChainEvidence,
            UnmatchedCompanyQueue,
        )

        # source Stock 없음 — match() 가 호출될 때 context_sector='' 가 전달
        source_stock = Stock.objects.create(symbol='ZZZ', stock_name='ZZ Co')
        doc = RawDocumentStore.objects.create(
            symbol=source_stock, accession_no='acc-mwq-noskip',
            filing_date=date(2023, 11, 1), fiscal_year=2023,
            final_link='https://sec.gov/no-src',
        )
        evidence = SupplyChainEvidence.objects.create(
            source_document=doc, source_company=source_stock,
            target_company_name='Anonymous Co',
            relationship_type='DEPENDS_ON', evidence_text='ev',
        )

        with patch.object(TickerMatcher, 'match', return_value=(None, None)) as m, \
             patch.object(TickerMatcher, '_get_fuzzy_candidates', return_value=[]):
            matcher.match_with_queue(
                'Anonymous Co', evidence, doc, 'UNKNOWN_SYMBOL'
            )
        # 'UNKNOWN_SYMBOL' 는 Stock 에 없으므로 sector='' 가 전달됨
        m.assert_called_once_with('Anonymous Co', '')
        # 큐에 적재되었고 source_sectors 는 빈 리스트
        entry = UnmatchedCompanyQueue.objects.get(raw_company_name='Anonymous Co')
        assert entry.source_sectors == []

    def test_match_succeeds_but_target_stock_missing(self, matcher):
        """match() 가 ticker 반환했지만 Stock 테이블에 없으면 evidence 업데이트 스킵."""
        from packages.shared.stocks.models import Stock
        from services.sec_pipeline.models import RawDocumentStore, SupplyChainEvidence

        source_stock = Stock.objects.create(symbol='AAPL', stock_name='Apple Inc.')
        doc = RawDocumentStore.objects.create(
            symbol=source_stock, accession_no='acc-mwq-no-target',
            filing_date=date(2023, 11, 1), fiscal_year=2023,
            final_link='https://sec.gov/no-target',
        )
        evidence = SupplyChainEvidence.objects.create(
            source_document=doc, source_company=source_stock,
            target_company_name='Ghost Co',
            relationship_type='SUPPLIES_TO', evidence_text='ev',
            neo4j_dirty=False,
        )
        # match() 는 ticker 반환하지만 Stock 에는 없음
        with patch.object(TickerMatcher, 'match', return_value=('GHOST', 'fuzzy')):
            ticker, method = matcher.match_with_queue(
                'Ghost Co', evidence, doc, 'AAPL'
            )
        assert ticker == 'GHOST'
        assert method == 'fuzzy'
        evidence.refresh_from_db()
        # target_company 업데이트 시도가 있었으나 Stock 가 없어 변경되지 않음
        assert evidence.target_company is None
        # neo4j_dirty 도 그대로 False (업데이트 스킵)
        assert evidence.neo4j_dirty is False


@pytest.mark.django_db
class TestMatchAliasExplicitEmptySector:
    def test_alias_empty_sector_param_uses_generic(self, matcher):
        """context_sector='' 명시 호출도 generic alias 매칭."""
        from services.sec_pipeline.models import CompanyAlias
        CompanyAlias.objects.create(
            alias='OnlyGeneric', ticker='OG', context_sector='',
        )
        result = matcher._match_alias('OnlyGeneric', '')
        assert result == 'OG'


@pytest.mark.django_db
class TestGetFuzzyCandidatesSortedDesc:
    def test_candidates_sorted_by_score_desc(self, matcher):
        """후보는 score 내림차순으로 반환."""
        from packages.shared.stocks.models import Stock
        Stock.objects.create(symbol='AAPL', stock_name='Apple Inc.')
        Stock.objects.create(symbol='APP2', stock_name='Apple Computer')
        candidates = matcher._get_fuzzy_candidates('Apple Inc', top_k=5)
        if len(candidates) >= 2:
            for i in range(len(candidates) - 1):
                assert candidates[i]['score'] >= candidates[i + 1]['score']


# ===========================================================================
# Models — JSONField, choices 유효값, 추가 필드
# ===========================================================================

@pytest.mark.django_db
class TestRawDocumentStoreWarnings:
    def test_warnings_jsonfield_persists_list(self):
        """warnings JSONField 에 리스트가 영속화."""
        from packages.shared.stocks.models import Stock
        from services.sec_pipeline.models import RawDocumentStore

        stock = Stock.objects.create(symbol='AAPL', stock_name='Apple Inc.')
        doc = RawDocumentStore.objects.create(
            symbol=stock, accession_no='acc-warn-1',
            filing_date=date(2023, 11, 1), fiscal_year=2023,
            final_link='https://sec.gov/w',
            warnings=['WARN: short section', 'FAIL: missing heading'],
        )
        doc.refresh_from_db()
        assert doc.warnings == ['WARN: short section', 'FAIL: missing heading']


@pytest.mark.django_db
class TestFilingProcessLogDuration:
    def test_duration_seconds_stores_float(self):
        """duration_seconds 필드는 float 저장 가능."""
        from services.sec_pipeline.models import FilingProcessLog
        log = FilingProcessLog.objects.create(
            symbol='AAPL', stage='sec_fetch', status='success',
            duration_seconds=12.345,
        )
        log.refresh_from_db()
        assert log.duration_seconds == pytest.approx(12.345)

    def test_status_retrying_and_skipped_valid(self):
        """retrying / skipped 도 STATUS_CHOICES 에 포함."""
        from services.sec_pipeline.models import FilingProcessLog
        retry = FilingProcessLog.objects.create(
            symbol='AAPL', stage='sec_fetch', status='retrying',
        )
        skip = FilingProcessLog.objects.create(
            symbol='AAPL', stage='neo4j_sync', status='skipped',
        )
        assert retry.status == 'retrying'
        assert skip.status == 'skipped'


@pytest.mark.django_db
class TestBusinessModelEvidenceFieldChoices:
    def test_all_5_field_names_valid(self):
        """BusinessModelEvidence.field_name 의 5개 choice 모두 유효."""
        from packages.shared.stocks.models import Stock
        from services.sec_pipeline.models import (
            BusinessModelEvidence,
            BusinessModelSnapshot,
            RawDocumentStore,
        )

        stock = Stock.objects.create(symbol='X', stock_name='X Co')
        doc = RawDocumentStore.objects.create(
            symbol=stock, accession_no='acc-bme-f1',
            filing_date=date(2023, 1, 1), fiscal_year=2022,
            final_link='https://sec.gov/x',
        )
        snap = BusinessModelSnapshot.objects.create(
            symbol=stock, source_document=doc, as_of_date=date(2023, 1, 1),
        )
        valid_fields = [
            'direct_customer_contact', 'contract_model',
            'recurring_revenue_signal', 'channel_dependency',
            'customer_concentration',
        ]
        for field in valid_fields:
            BusinessModelEvidence.objects.create(
                snapshot=snap, field_name=field,
                evidence_text=f'ev for {field}',
            )
        assert BusinessModelEvidence.objects.filter(snapshot=snap).count() == 5


@pytest.mark.django_db
class TestUnmatchedQueueResolvedTicker:
    def test_resolved_ticker_writable(self):
        from services.sec_pipeline.models import UnmatchedCompanyQueue
        entry = UnmatchedCompanyQueue.objects.create(
            raw_company_name='Resolved Co', source_symbol='AAPL',
        )
        entry.resolved_ticker = 'RES'
        entry.status = 'matched'
        entry.save()
        entry.refresh_from_db()
        assert entry.resolved_ticker == 'RES'
        assert entry.status == 'matched'

    def test_status_choices_extra_values(self):
        """duplicate / skipped status 도 STATUS_CHOICES 에 포함."""
        from services.sec_pipeline.models import UnmatchedCompanyQueue
        dup = UnmatchedCompanyQueue.objects.create(
            raw_company_name='Dup', source_symbol='X', status='duplicate',
        )
        sk = UnmatchedCompanyQueue.objects.create(
            raw_company_name='Skip', source_symbol='X', status='skipped',
        )
        assert dup.status == 'duplicate'
        assert sk.status == 'skipped'


@pytest.mark.django_db
class TestPipelineReportCrossInsights:
    def test_cross_insights_text_field(self):
        """cross_insights 텍스트 필드에 LLM 분석 결과 저장."""
        from services.sec_pipeline.models import PipelineIntelligenceReport
        report = PipelineIntelligenceReport.objects.create(
            report_date=date(2023, 12, 1),
            severity='warning',
            cross_insights='High failure rate correlates with low confidence.',
            recommended_actions=[{'action': 'check API key', 'priority': 'high'}],
        )
        report.refresh_from_db()
        assert 'failure rate' in report.cross_insights
        assert isinstance(report.recommended_actions, list)
        assert report.recommended_actions[0]['action'] == 'check API key'


@pytest.mark.django_db
class TestSupplyChainEvidenceHighGrade:
    def test_confidence_grade_high_persists(self):
        """confidence_grade='high' 정상 저장."""
        from packages.shared.stocks.models import Stock
        from services.sec_pipeline.models import RawDocumentStore, SupplyChainEvidence

        stock = Stock.objects.create(symbol='HG', stock_name='HG Co')
        doc = RawDocumentStore.objects.create(
            symbol=stock, accession_no='acc-hg-1',
            filing_date=date(2023, 11, 1), fiscal_year=2023,
            final_link='https://sec.gov/hg',
        )
        ev = SupplyChainEvidence.objects.create(
            source_document=doc, source_company=stock,
            target_company_name='Y Co', relationship_type='COMPETES_WITH',
            evidence_text='ev', system_confidence=0.95,
            confidence_grade='high',
        )
        ev.refresh_from_db()
        assert ev.confidence_grade == 'high'


# ===========================================================================
# QualityChecks — healthy / rounding / hours_back / 분기
# ===========================================================================

@pytest.fixture
def stock(db):
    from packages.shared.stocks.models import Stock
    return Stock.objects.create(symbol='AAPL', stock_name='Apple Inc.')


@pytest.fixture
def doc(stock):
    from services.sec_pipeline.models import RawDocumentStore
    return RawDocumentStore.objects.create(
        symbol=stock, accession_no='acc-qcx-001',
        filing_date=date(2023, 11, 1), fiscal_year=2023,
        final_link='https://sec.gov/qcx', status='success',
    )


@pytest.mark.django_db
class TestQualityChecksHealthy:
    def test_partial_only_no_failure_rate_alert(self, stock):
        """status='partial' 만 있을 때 실패율 알림 없음 (failed 만 카운트)."""
        from services.sec_pipeline.models import RawDocumentStore
        from services.sec_pipeline.quality_checks import run_post_batch_quality_checks

        for i in range(5):
            RawDocumentStore.objects.create(
                symbol=stock, accession_no=f'acc-p-{i}',
                filing_date=date(2023, 11, 1), fiscal_year=2023,
                final_link=f'https://sec.gov/p{i}',
                status='partial',
            )
        alerts = run_post_batch_quality_checks(hours_back=24)
        assert not any('실패율' in a for a in alerts)

    def test_high_match_rate_no_alert(self, stock, doc):
        """매칭률 >= 30% 면 매칭률 알림 없음."""
        from services.sec_pipeline.models import SupplyChainEvidence
        from services.sec_pipeline.quality_checks import run_post_batch_quality_checks

        # 4 matched / 4 unmatched = 50%
        for i in range(4):
            SupplyChainEvidence.objects.create(
                source_document=doc, source_company=stock,
                target_company=stock, target_company_name=f'M{i}',
                relationship_type='SUPPLIES_TO', evidence_text='ev',
                system_confidence=0.9,
            )
        for i in range(4):
            SupplyChainEvidence.objects.create(
                source_document=doc, source_company=stock,
                target_company=None, target_company_name=f'U{i}',
                relationship_type='SUPPLIES_TO', evidence_text='ev',
                system_confidence=0.9,
            )
        alerts = run_post_batch_quality_checks(hours_back=24)
        assert not any('매칭률' in a for a in alerts)


@pytest.mark.django_db
class TestQualityChecksHoursBackParam:
    def test_smaller_window_excludes_older_records(self, stock):
        """hours_back=1 이면 24시간 전 데이터는 제외."""
        from services.sec_pipeline.models import RawDocumentStore
        from services.sec_pipeline.quality_checks import run_post_batch_quality_checks

        old = RawDocumentStore.objects.create(
            symbol=stock, accession_no='acc-recent-fail',
            filing_date=date(2023, 11, 1), fiscal_year=2023,
            final_link='https://sec.gov/recent', status='failed',
        )
        RawDocumentStore.objects.filter(pk=old.pk).update(
            collected_at=timezone.now() - timedelta(hours=2)
        )
        alerts = run_post_batch_quality_checks(hours_back=1)
        # 1시간 윈도우 밖이므로 알림 없음
        assert not any('실패율' in a for a in alerts)


@pytest.mark.django_db
class TestDashboardStatsRounding:
    def test_avg_confidence_rounded_to_three_decimals(self, stock, doc):
        """avg_confidence 가 소수점 3자리로 반올림."""
        from services.sec_pipeline.models import SupplyChainEvidence
        from services.sec_pipeline.quality_checks import get_dashboard_stats

        # 평균 = 0.333333... → 반올림하면 0.333
        for v in (0.3, 0.3, 0.4):
            SupplyChainEvidence.objects.create(
                source_document=doc, source_company=stock,
                target_company=stock, target_company_name='X',
                relationship_type='SUPPLIES_TO', evidence_text='ev',
                system_confidence=v,
            )
        result = get_dashboard_stats()
        # 소수점 3자리 반올림 결과
        assert result['track_a']['avg_confidence'] == round(
            (0.3 + 0.3 + 0.4) / 3, 3
        )


@pytest.mark.django_db
class TestDashboardStatsEmptyQueue:
    def test_dashboard_returns_zero_when_no_queue(self):
        """UnmatchedCompanyQueue 가 비어있으면 모든 카운트 0."""
        from services.sec_pipeline.quality_checks import get_dashboard_stats
        result = get_dashboard_stats()
        assert result['matching']['queue_pending'] == 0
        assert result['matching']['queue_matched'] == 0
        assert result['matching']['queue_not_public'] == 0
        assert result['matching']['queue_person'] == 0
        assert result['matching']['queue_total'] == 0


# ===========================================================================
# Validators — 길이 WARN / 부분 헤딩
# ===========================================================================

class TestValidatorsLengthWarning:
    def test_very_long_section_triggers_warn(self):
        """MAX_SECTION_LENGTH 초과 시 WARN 발생."""
        long_text = 'Item 1. Description of Business\n' + ('a ' * (MAX_SECTION_LENGTH // 2 + 1000))
        sections = {
            'item_1': long_text,
            'item_1a': '',
            'item_7': '',
        }
        full_text = (
            "Item 1 Description of Business\n"
            "Item 7 Management Discussion\n"
        )
        _, warnings = validate_extracted_sections(sections, full_text)
        assert any('unusually long' in w for w in warnings)


class TestCheckItemOrderPartialPresence:
    def test_only_item_7_skips_order_check(self):
        """item_1 없이 item_7 만 있으면 순서 검증 스킵 (빈 문자열 반환)."""
        text = "Item 7 Management Discussion\n" + ('a ' * 100)
        assert _check_item_order(text) == ''

    def test_item_1_and_8_correct_order(self):
        """item_1 → item_8 만 있고 순서 맞으면 빈 문자열."""
        text = (
            "Item 1 Description of Business\n"
            + ('a ' * 100)
            + "Item 7 MD&A\n"
            + ('b ' * 50)
            + "Item 8 Financial Statements\n"
        )
        assert _check_item_order(text) == ''
