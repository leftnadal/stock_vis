"""
SECFilingCollector 단위 테스트.

HTTP 요청은 전부 mock. 실제 SEC EDGAR 호출 절대 금지.
"""

import pytest
from unittest.mock import patch, MagicMock

from sec_pipeline.collector import SECFilingCollector


# ---------------------------------------------------------------------------
# Helpers / Fixtures
# ---------------------------------------------------------------------------

SAMPLE_TICKERS_JSON = {
    "0": {"cik_str": 320193, "ticker": "AAPL", "title": "Apple Inc."},
    "1": {"cik_str": 789019, "ticker": "MSFT", "title": "Microsoft Corp"},
}

SAMPLE_SUBMISSIONS_JSON = {
    "filings": {
        "recent": {
            "form": ["10-K", "10-Q", "8-K"],
            "accessionNumber": ["0000320193-23-000106", "acc-2", "acc-3"],
            "filingDate": ["2023-11-03", "2023-08-01", "2023-06-15"],
            "primaryDocument": ["aapl-20230930.htm", "q.htm", "8k.htm"],
        }
    }
}

SAMPLE_HTML = """
<html><body>
<h1>Table of Contents</h1>
<p>Item 1 ........ 5</p>
<p>Item 1A ....... 20</p>
<p>Item 7 ........ 40</p>

<h2>Item 1. Description of Business</h2>
<p>Apple Inc. designs, manufactures, and markets smartphones and personal computers.
The Company sells to consumers, small and mid-sized businesses, and governments worldwide.
Apple's supply chain relies on key suppliers including TSMC for semiconductor fabrication.
""" + "x " * 200 + """</p>

<h2>Item 1A. Risk Factors</h2>
<p>The Company's operations depend on component supply from third-party manufacturers.
""" + "y " * 200 + """</p>

<h2>Item 7. Management's Discussion and Analysis</h2>
<p>Revenue increased due to strong customer demand for iPhone and services.
The Company competes with Samsung, Google and other technology companies.
""" + "z " * 200 + """</p>

<h2>Item 8. Financial Statements</h2>
<p>See consolidated financial statements.</p>
</body></html>
"""


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
# Tests: _get_cik
# ---------------------------------------------------------------------------

class TestGetCik:
    @patch('sec_pipeline.collector.requests.get')
    @patch('sec_pipeline.collector.time.sleep')
    def test_cik_found(self, mock_sleep, mock_get, collector):
        mock_get.return_value = _mock_response(json_data=SAMPLE_TICKERS_JSON)
        cik = collector._get_cik('AAPL')
        assert cik == '0000320193'

    @patch('sec_pipeline.collector.requests.get')
    @patch('sec_pipeline.collector.time.sleep')
    def test_cik_not_found(self, mock_sleep, mock_get, collector):
        mock_get.return_value = _mock_response(json_data=SAMPLE_TICKERS_JSON)
        cik = collector._get_cik('ZZZZ')
        assert cik is None

    @patch('sec_pipeline.collector.requests.get')
    @patch('sec_pipeline.collector.time.sleep')
    def test_cik_cached(self, mock_sleep, mock_get, collector):
        collector._cik_cache['AAPL'] = '0000320193'
        cik = collector._get_cik('AAPL')
        assert cik == '0000320193'
        mock_get.assert_not_called()

    @patch('sec_pipeline.collector.requests.get')
    @patch('sec_pipeline.collector.time.sleep')
    def test_cik_request_error(self, mock_sleep, mock_get, collector):
        mock_get.side_effect = Exception("Network error")
        cik = collector._get_cik('AAPL')
        assert cik is None


# ---------------------------------------------------------------------------
# Tests: get_filing_metadata
# ---------------------------------------------------------------------------

class TestGetFilingMetadata:
    @patch('sec_pipeline.collector.requests.get')
    @patch('sec_pipeline.collector.time.sleep')
    def test_metadata_found(self, mock_sleep, mock_get, collector):
        collector._cik_cache['AAPL'] = '0000320193'
        mock_get.return_value = _mock_response(json_data=SAMPLE_SUBMISSIONS_JSON)

        result = collector.get_filing_metadata('aapl')
        assert result is not None
        assert result['symbol'] == 'AAPL'
        assert result['accession_no'] == '0000320193-23-000106'
        assert result['filing_date'] == '2023-11-03'
        assert 'final_link' in result

    @patch('sec_pipeline.collector.requests.get')
    @patch('sec_pipeline.collector.time.sleep')
    def test_metadata_no_10k(self, mock_sleep, mock_get, collector):
        collector._cik_cache['AAPL'] = '0000320193'
        no_10k = {
            "filings": {"recent": {
                "form": ["10-Q", "8-K"],
                "accessionNumber": ["acc-1", "acc-2"],
                "filingDate": ["2023-08-01", "2023-06-15"],
                "primaryDocument": ["q.htm", "8k.htm"],
            }}
        }
        mock_get.return_value = _mock_response(json_data=no_10k)

        result = collector.get_filing_metadata('AAPL')
        assert result is None

    def test_metadata_no_cik(self, collector):
        with patch.object(collector, '_get_cik', return_value=None):
            result = collector.get_filing_metadata('ZZZZ')
            assert result is None


# ---------------------------------------------------------------------------
# Tests: fetch_filing_html
# ---------------------------------------------------------------------------

class TestFetchFilingHtml:
    @patch('sec_pipeline.collector.requests.get')
    @patch('sec_pipeline.collector.time.sleep')
    def test_fetch_success(self, mock_sleep, mock_get, collector):
        mock_get.return_value = _mock_response(text='<html>test</html>')
        html = collector.fetch_filing_html('https://sec.gov/test.htm')
        assert html == '<html>test</html>'

    def test_fetch_empty_link(self, collector):
        assert collector.fetch_filing_html('') is None
        assert collector.fetch_filing_html(None) is None

    @patch('sec_pipeline.collector.requests.get')
    @patch('sec_pipeline.collector.time.sleep')
    def test_fetch_error_raises(self, mock_sleep, mock_get, collector):
        import requests as req
        mock_get.side_effect = req.exceptions.RequestException("timeout")
        with pytest.raises(req.exceptions.RequestException):
            collector.fetch_filing_html('https://sec.gov/test.htm')


# ---------------------------------------------------------------------------
# Tests: _fiscal_year_from_date
# ---------------------------------------------------------------------------

class TestFiscalYear:
    def test_q4_filing(self, collector):
        assert collector._fiscal_year_from_date('2023-11-03') == 2023

    def test_q1_filing_returns_previous_year(self, collector):
        assert collector._fiscal_year_from_date('2024-02-15') == 2023

    def test_march_filing_returns_previous_year(self, collector):
        assert collector._fiscal_year_from_date('2024-03-31') == 2023

    def test_april_filing_returns_same_year(self, collector):
        assert collector._fiscal_year_from_date('2024-04-01') == 2024

    def test_invalid_date(self, collector):
        assert collector._fiscal_year_from_date('not-a-date') == 0

    def test_none_date(self, collector):
        assert collector._fiscal_year_from_date(None) == 0


# ---------------------------------------------------------------------------
# Tests: _html_to_text
# ---------------------------------------------------------------------------

class TestHtmlToText:
    def test_strips_tags(self, collector):
        html = '<p>Hello <b>World</b></p>'
        text = collector._html_to_text(html)
        assert 'Hello' in text
        assert 'World' in text
        assert '<b>' not in text

    def test_removes_script_style(self, collector):
        html = '<script>var x=1;</script><style>.a{}</style><p>Content</p>'
        text = collector._html_to_text(html)
        assert 'var x' not in text
        assert 'Content' in text


# ---------------------------------------------------------------------------
# Tests: extract_sections
# ---------------------------------------------------------------------------

class TestExtractSections:
    def test_extracts_all_sections(self, collector):
        sections = collector.extract_sections(SAMPLE_HTML)
        assert 'item_1' in sections
        assert 'item_1a' in sections
        assert 'item_7' in sections

    def test_empty_html(self, collector):
        sections = collector.extract_sections('<html><body></body></html>')
        assert sections['item_1'] == ''
        assert sections['item_1a'] == ''
        assert sections['item_7'] == ''


# ---------------------------------------------------------------------------
# Tests: _fail_result
# ---------------------------------------------------------------------------

class TestFailResult:
    def test_fail_without_metadata(self, collector):
        result = collector._fail_result('AAPL', 'test error')
        assert result['symbol'] == 'AAPL'
        assert result['status'] == 'failed'
        assert 'FAIL: test error' in result['warnings']
        assert result['accession_no'] == ''

    def test_fail_with_metadata(self, collector):
        meta = {'accession_no': 'acc-1', 'filing_date': '2023-01-01',
                'fiscal_year': 2022, 'final_link': 'http://test'}
        result = collector._fail_result('AAPL', 'reason', meta)
        assert result['accession_no'] == 'acc-1'
        assert result['fiscal_year'] == 2022
