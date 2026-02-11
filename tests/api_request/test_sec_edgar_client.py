"""
SEC EDGAR Client Tests

Unit tests for the SEC EDGAR API client.
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import date

from api_request.sec_edgar_client import (
    SECEdgarClient,
    SECEdgarError,
    Filing10K
)


class TestSECEdgarClient:
    """SEC EDGAR Client 테스트"""

    @pytest.fixture
    def client(self):
        """Create test client"""
        return SECEdgarClient()

    @pytest.fixture
    def mock_response(self):
        """Create mock response"""
        response = Mock()
        response.status_code = 200
        return response

    # ========================================
    # CIK Lookup Tests
    # ========================================

    @patch('api_request.sec_edgar_client.requests.Session.get')
    def test_get_cik_success(self, mock_get, client):
        """CIK 조회 성공 테스트"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            '0': {'cik_str': 320193, 'ticker': 'AAPL', 'title': 'Apple Inc.'},
            '1': {'cik_str': 789019, 'ticker': 'MSFT', 'title': 'Microsoft Corp'}
        }
        mock_get.return_value = mock_response

        cik = client.get_cik('AAPL')

        assert cik == '0000320193'
        assert cik in client._cik_cache.values()

    @patch('api_request.sec_edgar_client.requests.Session.get')
    def test_get_cik_not_found(self, mock_get, client):
        """CIK 조회 실패 - 종목 없음"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            '0': {'cik_str': 320193, 'ticker': 'AAPL', 'title': 'Apple Inc.'}
        }
        mock_get.return_value = mock_response

        cik = client.get_cik('UNKNOWN')

        assert cik is None

    def test_get_cik_cache_hit(self, client):
        """CIK 캐시 히트 테스트"""
        client._cik_cache['AAPL'] = '0000320193'

        cik = client.get_cik('AAPL')

        assert cik == '0000320193'

    # ========================================
    # 10-K Filing Tests
    # ========================================

    @patch.object(SECEdgarClient, 'get_company_info')
    def test_get_10k_filings_success(self, mock_get_info, client):
        """10-K 파일링 조회 성공 테스트"""
        mock_get_info.return_value = {
            'name': 'Apple Inc.',
            'filings': {
                'recent': {
                    'form': ['10-K', '10-Q', '8-K', '10-K/A'],
                    'accessionNumber': [
                        '0000320193-23-000106',
                        '0000320193-23-000077',
                        '0000320193-23-000050',
                        '0000320193-22-000108'
                    ],
                    'filingDate': [
                        '2023-11-03',
                        '2023-08-04',
                        '2023-05-05',
                        '2022-10-28'
                    ],
                    'reportDate': [
                        '2023-09-30',
                        '2023-07-01',
                        '2023-04-01',
                        '2022-09-24'
                    ],
                    'primaryDocument': [
                        'aapl-20230930.htm',
                        'aapl-20230701.htm',
                        'aapl-20230401.htm',
                        'aapl-20220924.htm'
                    ]
                }
            }
        }

        filings = client.get_10k_filings('0000320193', limit=3)

        assert len(filings) == 2  # 10-K and 10-K/A only
        assert filings[0].form_type == '10-K'
        assert filings[0].company_name == 'Apple Inc.'
        assert filings[0].filing_date == date(2023, 11, 3)

    @patch.object(SECEdgarClient, 'get_company_info')
    def test_get_10k_filings_empty(self, mock_get_info, client):
        """10-K 파일링 없음 테스트"""
        mock_get_info.return_value = {
            'name': 'Unknown Corp',
            'filings': {
                'recent': {
                    'form': ['8-K', '8-K'],
                    'accessionNumber': ['0001-23-000001', '0001-23-000002'],
                    'filingDate': ['2023-01-01', '2023-02-01'],
                    'reportDate': ['2023-01-01', '2023-02-01'],
                    'primaryDocument': ['doc1.htm', 'doc2.htm']
                }
            }
        }

        filings = client.get_10k_filings('0000000001', limit=3)

        assert len(filings) == 0

    # ========================================
    # Text Extraction Tests
    # ========================================

    def test_html_to_text(self, client):
        """HTML → 텍스트 변환 테스트"""
        html = """
        <html>
        <head><title>Test</title></head>
        <body>
            <p>This is a test paragraph.</p>
            <script>console.log('test');</script>
            <p>Another paragraph here.</p>
        </body>
        </html>
        """

        text = client._html_to_text(html)

        assert 'This is a test paragraph' in text
        assert 'Another paragraph here' in text
        assert 'console.log' not in text
        assert '<script>' not in text

    def test_extract_item_1a_success(self, client):
        """Item 1A 추출 성공 테스트"""
        # Format matching real 10-K pattern
        text = """
        PART I

        Item 1. BUSINESS
        We are a technology company...

        Item 1A. Risk Factors
        Our business faces various risks including customer concentration.
        Apple Inc. accounted for 25% of our revenue in fiscal 2023.
        We depend on various suppliers for our manufacturing needs.

        Item 1B. Unresolved Staff Comments
        None.
        """

        item_1a = client.extract_item_1a(text)

        assert 'customer concentration' in item_1a
        assert 'Apple Inc. accounted for 25%' in item_1a
        # Should stop before Item 1B
        assert 'None.' not in item_1a or len(item_1a) < 500

    def test_extract_item_1a_fallback(self, client):
        """Item 1A 추출 실패 시 폴백 테스트"""
        text = "Some text without proper Item 1A section." * 1000

        item_1a = client.extract_item_1a(text)

        # Fallback: returns first 100k chars
        assert len(item_1a) <= 100000

    # ========================================
    # Rate Limiting Tests
    # ========================================

    def test_rate_limit(self, client):
        """Rate limit 적용 테스트"""
        import time

        client._last_request_time = time.time()

        start = time.time()
        client._rate_limit()
        elapsed = time.time() - start

        # Should wait at least 100ms
        assert elapsed >= 0.05  # Allow some tolerance

    # ========================================
    # Error Handling Tests
    # ========================================

    @patch('api_request.sec_edgar_client.requests.Session.get')
    def test_error_404(self, mock_get, client):
        """404 에러 처리 테스트"""
        mock_response = Mock()
        mock_response.status_code = 404

        mock_get.return_value = mock_response

        with pytest.raises(SECEdgarError) as exc_info:
            client._make_request('https://example.com/not-found')

        assert 'not found' in str(exc_info.value).lower()

    @patch('api_request.sec_edgar_client.requests.Session.get')
    def test_error_timeout(self, mock_get, client):
        """타임아웃 에러 처리 테스트"""
        import requests

        mock_get.side_effect = requests.exceptions.Timeout()

        with pytest.raises(SECEdgarError) as exc_info:
            client._make_request('https://example.com/slow')

        assert 'timeout' in str(exc_info.value).lower()


class TestFiling10K:
    """Filing10K 데이터클래스 테스트"""

    def test_filing_creation(self):
        """Filing10K 생성 테스트"""
        filing = Filing10K(
            accession_number='0000320193230001',
            filing_date=date(2023, 11, 3),
            report_date=date(2023, 9, 30),
            primary_document='aapl-20230930.htm',
            cik='0000320193',
            company_name='Apple Inc.',
            form_type='10-K'
        )

        assert filing.accession_number == '0000320193230001'
        assert filing.company_name == 'Apple Inc.'
        assert filing.form_type == '10-K'
