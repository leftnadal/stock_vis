"""
SECFilingCollector 추가 엣지 케이스 테스트.

기존 test_collector.py / test_collector_advanced.py 에서 누락된 영역:
- 10-K/A (amended) 폼 인식
- get_filing_metadata 의 RequestException 재발생
- _html_to_text 가 연속된 줄바꿈을 합치는지
- extract_sections 가 다중 후보 중 가장 긴 것을 선택하는지
- collect() 의 fallback 성공 경로 (FAIL → fallback success)
- SECTION_PATTERNS 구조 검증

HTTP 요청은 전부 mock. 실제 SEC EDGAR 호출 절대 금지.
"""

from unittest.mock import MagicMock, patch

import pytest
import requests as req

from services.sec_pipeline.collector import SECFilingCollector


@pytest.fixture
def collector():
    c = SECFilingCollector()
    c._cik_cache.clear()
    return c


def _mock_response(json_data=None, text=None, status_code=200):
    resp = MagicMock()
    resp.status_code = status_code
    resp.raise_for_status = MagicMock()
    if json_data is not None:
        resp.json.return_value = json_data
    if text is not None:
        resp.text = text
    return resp


# ---------------------------------------------------------------------------
# Tests: get_filing_metadata — 추가 경로
# ---------------------------------------------------------------------------

class TestGetFilingMetadataEdge:
    @patch('services.sec_pipeline.collector.requests.get')
    @patch('services.sec_pipeline.collector.time.sleep')
    def test_recognizes_10k_amended_form(self, mock_sleep, mock_get, collector):
        """10-K/A (amended) 폼도 10-K 와 동일하게 처리된다."""
        collector._cik_cache['AAPL'] = '0000320193'
        amended_data = {
            "filings": {"recent": {
                "form": ["8-K", "10-K/A", "10-Q"],
                "accessionNumber": ["acc-1", "acc-amended", "acc-3"],
                "filingDate": ["2023-12-01", "2023-11-15", "2023-08-01"],
                "primaryDocument": ["8k.htm", "aapl-amended.htm", "q.htm"],
            }}
        }
        mock_get.return_value = _mock_response(json_data=amended_data)

        result = collector.get_filing_metadata('AAPL')
        assert result is not None
        assert result['accession_no'] == 'acc-amended'
        assert 'aapl-amended.htm' in result['final_link']

    @patch('services.sec_pipeline.collector.requests.get')
    @patch('services.sec_pipeline.collector.time.sleep')
    def test_request_exception_reraises(self, mock_sleep, mock_get, collector):
        """submissions API 요청 실패 시 RequestException 이 전파된다."""
        collector._cik_cache['AAPL'] = '0000320193'
        mock_get.side_effect = req.exceptions.ConnectionError("network down")
        with pytest.raises(req.exceptions.RequestException):
            collector.get_filing_metadata('AAPL')

    @patch('services.sec_pipeline.collector.requests.get')
    @patch('services.sec_pipeline.collector.time.sleep')
    def test_final_link_strips_leading_zeros_from_cik(self, mock_sleep, mock_get, collector):
        """final_link 의 CIK 구간은 lstrip('0') 결과를 사용한다."""
        collector._cik_cache['AAPL'] = '0000320193'
        data = {
            "filings": {"recent": {
                "form": ["10-K"],
                "accessionNumber": ["0000320193-23-000106"],
                "filingDate": ["2023-11-03"],
                "primaryDocument": ["x.htm"],
            }}
        }
        mock_get.return_value = _mock_response(json_data=data)
        result = collector.get_filing_metadata('AAPL')
        # zero-padded CIK 가 아닌 잘린 형태가 URL에 사용됨
        assert '/320193/' in result['final_link']
        assert '/0000320193/' not in result['final_link']

    @patch('services.sec_pipeline.collector.requests.get')
    @patch('services.sec_pipeline.collector.time.sleep')
    def test_accession_no_in_url_has_dashes_removed(self, mock_sleep, mock_get, collector):
        """final_link 의 accession 구간은 '-' 없이 사용된다."""
        collector._cik_cache['AAPL'] = '0000320193'
        data = {
            "filings": {"recent": {
                "form": ["10-K"],
                "accessionNumber": ["0000320193-23-000106"],
                "filingDate": ["2023-11-03"],
                "primaryDocument": ["x.htm"],
            }}
        }
        mock_get.return_value = _mock_response(json_data=data)
        result = collector.get_filing_metadata('AAPL')
        assert '000032019323000106' in result['final_link']


# ---------------------------------------------------------------------------
# Tests: _html_to_text — 추가 케이스
# ---------------------------------------------------------------------------

class TestHtmlToTextEdge:
    def test_collapses_consecutive_newlines(self, collector):
        """\\n\\n\\n+ → \\n\\n 로 정리."""
        html = '<p>a</p>' + ('<br/>' * 10) + '<p>b</p>'
        text = collector._html_to_text(html)
        # 연속된 줄바꿈은 최대 2개로 줄어듦
        assert '\n\n\n' not in text

    def test_collapses_horizontal_whitespace(self, collector):
        """다중 공백/탭 → 단일 공백."""
        html = '<p>hello\t\t\t   world</p>'
        text = collector._html_to_text(html)
        # tab/multiple-space 정리됨
        assert '\t\t' not in text
        assert '   ' not in text

    def test_returns_stripped_text(self, collector):
        """선행/후행 공백 제거."""
        html = '   <p>content</p>   '
        text = collector._html_to_text(html)
        assert text == text.strip()


# ---------------------------------------------------------------------------
# Tests: extract_sections — longest scoring
# ---------------------------------------------------------------------------

class TestExtractSectionsLongest:
    def test_picks_longest_candidate(self, collector):
        """동일 섹션의 여러 후보 중 가장 긴 것을 채택."""
        # Item 1 이 두 번 등장하지만 다음 섹션(Item 1A)이 한 번만 등장
        # → 첫 번째 후보는 짧고, 두 번째는 다음 Item 1A 까지로 길어진다
        short_body = 'x ' * 110  # ~220 chars
        long_body = 'y ' * 1000  # ~2000 chars
        text = f"""
        <html><body>
        Item 1. Description of Business
        {short_body}
        Item 1. Description of Business
        {long_body}
        Item 1A. Risk Factors
        Some risks here.
        </body></html>
        """
        sections = collector.extract_sections(text)
        # 가장 긴 후보가 선택되었는지 확인 (long_body 가 포함됨)
        assert 'y y' in sections['item_1']


# ---------------------------------------------------------------------------
# Tests: SECTION_PATTERNS 구조
# ---------------------------------------------------------------------------

class TestSectionPatterns:
    def test_section_patterns_has_required_keys(self, collector):
        """item_1, item_1a, item_7, item_8 키가 모두 존재."""
        for key in ('item_1', 'item_1a', 'item_7', 'item_8'):
            assert key in collector.SECTION_PATTERNS
            assert isinstance(collector.SECTION_PATTERNS[key], list)
            assert len(collector.SECTION_PATTERNS[key]) > 0


# ---------------------------------------------------------------------------
# Tests: collect() — fallback recovery 경로
# ---------------------------------------------------------------------------

class TestCollectFallbackRecovery:
    def test_fallback_succeeds_after_regex_fail(self, collector):
        """regex 결과가 FAIL 검증이고 fallback 이 성공하면 fallback 결과를 사용."""
        meta = {
            'symbol': 'AAPL',
            'accession_no': 'acc-fb-1',
            'filing_date': '2023-11-03',
            'fiscal_year': 2023,
            'final_link': 'https://sec.gov/test',
        }
        regex_sections = {'item_1': '', 'item_1a': '', 'item_7': ''}
        fallback_sections = {
            'item_1': 'Item 1. ' + ('a ' * 2000),
            'item_1a': 'Item 1A. ' + ('b ' * 2000),
            'item_7': "Item 7. Management's Discussion " + ('c ' * 2000),
        }

        # validator: 첫 호출은 FAIL, 두 번째 호출(fallback)은 통과
        call_count = {'n': 0}

        def fake_validator(sections, full_text):
            call_count['n'] += 1
            if call_count['n'] == 1:
                return sections, ['FAIL: regex extraction broken']
            return sections, []

        with patch.object(collector, 'get_filing_metadata', return_value=meta), \
             patch.object(collector, 'fetch_filing_html',
                          return_value='<html>x</html>'), \
             patch.object(collector, 'extract_sections',
                          return_value=regex_sections), \
             patch.object(collector, 'extract_sections_fallback',
                          return_value=fallback_sections), \
             patch('services.sec_pipeline.collector.validate_extracted_sections',
                   side_effect=fake_validator):
            result = collector.collect('AAPL')

        assert result['extraction_method'] == 'edgartools_fallback'
        # fallback 성공 시 sections 가 fallback 결과로 채워짐
        assert result['sections']['item_1'].startswith('Item 1.')

    def test_fallback_also_fails_keeps_regex(self, collector):
        """fallback 도 FAIL 이면 regex 결과를 유지 (validated_sections 그대로)."""
        meta = {
            'symbol': 'AAPL',
            'accession_no': 'acc-fb-2',
            'filing_date': '2023-11-03',
            'fiscal_year': 2023,
            'final_link': 'https://sec.gov/test',
        }
        regex_sections = {'item_1': 'short', 'item_1a': '', 'item_7': ''}

        def fake_validator(sections, full_text):
            return sections, ['FAIL: heading not found']

        with patch.object(collector, 'get_filing_metadata', return_value=meta), \
             patch.object(collector, 'fetch_filing_html',
                          return_value='<html>x</html>'), \
             patch.object(collector, 'extract_sections',
                          return_value=regex_sections), \
             patch.object(collector, 'extract_sections_fallback',
                          return_value={'item_1': 'x', 'item_1a': '', 'item_7': ''}), \
             patch('services.sec_pipeline.collector.validate_extracted_sections',
                   side_effect=fake_validator):
            result = collector.collect('AAPL')

        # fallback FAIL → extraction_method 그대로 regex
        assert result['extraction_method'] == 'regex'


# ---------------------------------------------------------------------------
# Tests: _fail_result — accession_no/metadata 키 보존
# ---------------------------------------------------------------------------

class TestFailResultKeys:
    def test_fail_result_keeps_all_expected_keys(self, collector):
        """_fail_result 반환에 표준 키가 모두 존재."""
        result = collector._fail_result('AAPL', 'reason')
        for key in ('symbol', 'accession_no', 'filing_date', 'fiscal_year',
                    'final_link', 'sections', 'status', 'extraction_method',
                    'warnings'):
            assert key in result
        assert set(result['sections'].keys()) == {'item_1', 'item_1a', 'item_7'}
