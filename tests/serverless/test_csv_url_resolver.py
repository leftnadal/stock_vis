"""
CSV URL Resolver 테스트

CSVURLResolver 서비스의 유닛 테스트입니다.
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from decimal import Decimal

from serverless.services.csv_url_resolver import (
    CSVURLResolver,
    CSVURLResolverError,
    FUND_MANAGER_CONFIG,
    get_csv_url_resolver,
)
from serverless.models import ETFProfile


@pytest.fixture
def resolver():
    """CSVURLResolver 인스턴스 (LLM 없이)"""
    with patch.object(CSVURLResolver, '__init__', lambda self: None):
        r = CSVURLResolver()
        r.client = MagicMock()
        r._llm_client = None
        return r


@pytest.fixture
def resolver_with_llm():
    """CSVURLResolver 인스턴스 (LLM 포함)"""
    with patch.object(CSVURLResolver, '__init__', lambda self: None):
        r = CSVURLResolver()
        r.client = MagicMock()
        r._llm_client = MagicMock()
        return r


class TestFundManagerConfig:
    """운용사 설정 테스트"""

    def test_config_has_major_fund_managers(self):
        """주요 운용사 설정 포함"""
        assert 'spdr' in FUND_MANAGER_CONFIG
        assert 'ishares' in FUND_MANAGER_CONFIG
        assert 'ark' in FUND_MANAGER_CONFIG

    def test_spdr_config_structure(self):
        """SPDR 설정 구조"""
        config = FUND_MANAGER_CONFIG['spdr']
        assert 'name' in config
        assert 'base_url' in config
        assert 'holdings_page_template' in config
        assert 'csv_patterns' in config
        assert len(config['csv_patterns']) > 0

    def test_ishares_has_product_id_map(self):
        """iShares product ID 매핑"""
        config = FUND_MANAGER_CONFIG['ishares']
        assert 'product_id_map' in config
        assert 'SOXX' in config['product_id_map']
        assert 'ICLN' in config['product_id_map']

    def test_ark_has_fund_code_map(self):
        """ARK fund code 매핑"""
        config = FUND_MANAGER_CONFIG['ark']
        assert 'fund_code_map' in config
        assert 'ARKK' in config['fund_code_map']
        assert 'ARKG' in config['fund_code_map']


class TestBuildHoldingsPageUrl:
    """Holdings 페이지 URL 생성 테스트"""

    def test_spdr_url(self, resolver):
        """SPDR URL 생성"""
        config = FUND_MANAGER_CONFIG['spdr']
        url = resolver._build_holdings_page_url('XLK', 'spdr', config)

        assert 'ssga.com' in url
        assert 'XLK' in url or 'xlk' in url

    def test_ishares_url_with_product_id(self, resolver):
        """iShares URL 생성 (product ID 사용)"""
        config = FUND_MANAGER_CONFIG['ishares']
        url = resolver._build_holdings_page_url('SOXX', 'ishares', config)

        assert 'ishares.com' in url
        assert '239705' in url  # SOXX product ID

    def test_ark_url(self, resolver):
        """ARK URL 생성"""
        config = FUND_MANAGER_CONFIG['ark']
        url = resolver._build_holdings_page_url('ARKK', 'ark', config)

        assert 'ark-funds.com' in url
        assert 'arkk' in url.lower()


class TestPatternMatching:
    """패턴 매칭 테스트"""

    def test_find_spdr_xlsx_url(self, resolver):
        """SPDR XLSX 링크 찾기"""
        html = '''
        <html>
        <a href="/us/en/etfs/library-content/products/fund-data/etfs/us/holdings-daily-us-en-xlk.xlsx">
            Download Holdings
        </a>
        </html>
        '''
        config = FUND_MANAGER_CONFIG['spdr']

        url = resolver._find_csv_url_by_pattern(html, 'XLK', config)

        assert url is not None
        assert 'holdings' in url.lower()
        assert 'xlsx' in url.lower()

    def test_find_ishares_csv_url(self, resolver):
        """iShares CSV 링크 찾기"""
        html = '''
        <html>
        <a href="/us/products/239705/ishares-phlx-semiconductor-etf/1467271812596.ajax?fileType=csv&fileName=SOXX_holdings">
            Download CSV
        </a>
        </html>
        '''
        config = FUND_MANAGER_CONFIG['ishares']

        url = resolver._find_csv_url_by_pattern(html, 'SOXX', config)

        assert url is not None
        assert 'fileType=csv' in url

    def test_find_ark_csv_url(self, resolver):
        """ARK CSV 링크 찾기"""
        html = '''
        <html>
        <a href="https://ark-funds.com/wp-content/uploads/funds-etf-csv/ARK_INNOVATION_ETF_ARKK_HOLDINGS.csv">
            Download Holdings
        </a>
        </html>
        '''
        config = FUND_MANAGER_CONFIG['ark']

        url = resolver._find_csv_url_by_pattern(html, 'ARKK', config)

        assert url is not None
        assert 'ARK' in url
        assert 'HOLDINGS.csv' in url

    def test_relative_url_converted_to_absolute(self, resolver):
        """상대 경로가 절대 경로로 변환됨"""
        html = '''
        <a href="/downloads/holdings.csv">Download</a>
        '''
        config = {
            'base_url': 'https://example.com',
            'csv_patterns': [r'href=["\']([^"\']*\.csv)["\']'],
        }

        url = resolver._find_csv_url_by_pattern(html, 'TEST', config)

        assert url is not None
        assert url.startswith('https://example.com')

    def test_html_entities_decoded(self, resolver):
        """HTML 엔티티 디코딩"""
        html = '''
        <a href="https://example.com/data?type=csv&amp;date=2026">Download</a>
        '''
        config = {
            'base_url': 'https://example.com',
            'csv_patterns': [r'href=["\']([^"\']*type=csv[^"\']*)["\']'],
        }

        url = resolver._find_csv_url_by_pattern(html, 'TEST', config)

        assert url is not None
        assert '&amp;' not in url
        assert '&date=2026' in url

    def test_no_match_returns_none(self, resolver):
        """매칭 없으면 None 반환"""
        html = '<html><body>No download links</body></html>'
        config = FUND_MANAGER_CONFIG['spdr']

        url = resolver._find_csv_url_by_pattern(html, 'XLK', config)

        assert url is None


class TestHtmlCleaning:
    """HTML 정리 테스트"""

    def test_removes_script_tags(self, resolver):
        """스크립트 태그 제거"""
        html = '''
        <html>
        <script>alert("test");</script>
        <a href="holdings.csv">Download</a>
        </html>
        '''

        cleaned = resolver._clean_html_for_llm(html)

        assert '<script>' not in cleaned
        assert 'alert' not in cleaned

    def test_removes_style_tags(self, resolver):
        """스타일 태그 제거"""
        html = '''
        <html>
        <style>.btn { color: red; }</style>
        <a href="holdings.csv" class="btn">Download</a>
        </html>
        '''

        cleaned = resolver._clean_html_for_llm(html)

        assert '<style>' not in cleaned
        assert 'color: red' not in cleaned

    def test_keeps_download_links(self, resolver):
        """다운로드 링크는 유지"""
        html = '''
        <html>
        <a href="other.html">Other</a>
        <a href="download/holdings.csv">Download CSV</a>
        <a href="export.xlsx">Export</a>
        </html>
        '''

        cleaned = resolver._clean_html_for_llm(html)

        assert 'holdings.csv' in cleaned
        assert 'export.xlsx' in cleaned


class TestUrlValidation:
    """URL 검증 테스트"""

    def test_valid_csv_url(self, resolver):
        """유효한 CSV URL"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {'Content-Type': 'text/csv'}
        resolver.client.head.return_value = mock_response

        config = {'content_type_check': ['text/csv']}

        result = resolver._validate_csv_url('https://example.com/data.csv', config)

        assert result is True

    def test_invalid_status_code(self, resolver):
        """404 상태 코드"""
        mock_response = MagicMock()
        mock_response.status_code = 404
        resolver.client.head.return_value = mock_response

        config = {'content_type_check': ['text/csv']}

        result = resolver._validate_csv_url('https://example.com/data.csv', config)

        assert result is False

    def test_xlsx_extension_accepted(self, resolver):
        """XLSX 확장자 허용"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {'Content-Type': 'application/octet-stream'}  # 일반 바이너리
        resolver.client.head.return_value = mock_response

        config = {'content_type_check': ['text/csv']}

        result = resolver._validate_csv_url('https://example.com/data.xlsx', config)

        assert result is True  # 확장자가 xlsx면 OK


class TestLLMAnalysis:
    """LLM 분석 테스트"""

    def test_llm_finds_url(self, resolver_with_llm):
        """LLM이 URL 찾음"""
        # LLM 응답 모킹
        mock_response = MagicMock()
        mock_response.text = 'https://example.com/holdings.csv'
        resolver_with_llm._llm_client.models.generate_content.return_value = mock_response

        html = '<html><a href="https://example.com/holdings.csv">Download</a></html>'
        config = FUND_MANAGER_CONFIG['spdr']

        url = resolver_with_llm._find_csv_url_by_llm(html, 'XLK', 'spdr', config)

        assert url == 'https://example.com/holdings.csv'

    def test_llm_not_found(self, resolver_with_llm):
        """LLM이 URL 못 찾음"""
        mock_response = MagicMock()
        mock_response.text = 'NOT_FOUND'
        resolver_with_llm._llm_client.models.generate_content.return_value = mock_response

        html = '<html>No links</html>'
        config = FUND_MANAGER_CONFIG['spdr']

        url = resolver_with_llm._find_csv_url_by_llm(html, 'XLK', 'spdr', config)

        assert url is None

    def test_llm_extracts_url_from_text(self, resolver_with_llm):
        """LLM 응답에서 URL 추출"""
        mock_response = MagicMock()
        mock_response.text = 'The CSV URL is https://example.com/data.csv and here is more text.'
        resolver_with_llm._llm_client.models.generate_content.return_value = mock_response

        html = '<html></html>'
        config = FUND_MANAGER_CONFIG['spdr']

        url = resolver_with_llm._find_csv_url_by_llm(html, 'XLK', 'spdr', config)

        assert url == 'https://example.com/data.csv'

    def test_no_llm_client_returns_none(self, resolver):
        """LLM 클라이언트 없으면 None"""
        html = '<html></html>'
        config = FUND_MANAGER_CONFIG['spdr']

        url = resolver._find_csv_url_by_llm(html, 'XLK', 'spdr', config)

        assert url is None


@pytest.mark.django_db
class TestResolveAndUpdate:
    """resolve_and_update 테스트"""

    def test_updates_profile_on_success(self, resolver):
        """성공 시 프로필 업데이트"""
        # ETFProfile 생성
        profile = ETFProfile.objects.create(
            symbol='TEST',
            name='Test ETF',
            tier='sector',
            theme_id='test',
            parser_type='spdr',
            csv_url='https://old-url.com/data.csv'
        )

        # resolve_csv_url 모킹
        with patch.object(resolver, 'resolve_csv_url', return_value='https://new-url.com/data.csv'):
            success, result = resolver.resolve_and_update('TEST')

        assert success is True
        assert 'new-url.com' in result

        # DB 확인
        profile.refresh_from_db()
        assert profile.csv_url == 'https://new-url.com/data.csv'
        assert 'URL 자동 복구됨' in profile.last_error

    def test_returns_false_on_failure(self, resolver):
        """실패 시 False 반환"""
        ETFProfile.objects.create(
            symbol='TEST2',
            name='Test ETF 2',
            tier='sector',
            theme_id='test2',
            parser_type='spdr',
            csv_url='https://old-url.com/data.csv'
        )

        with patch.object(resolver, 'resolve_csv_url', return_value=None):
            success, result = resolver.resolve_and_update('TEST2')

        assert success is False
        assert 'URL 복구 실패' in result

    def test_profile_not_found(self, resolver):
        """프로필 없음"""
        success, result = resolver.resolve_and_update('NONEXISTENT')

        assert success is False
        assert 'ETF 프로필 없음' in result


class TestSingleton:
    """싱글톤 테스트"""

    def test_get_csv_url_resolver_returns_same_instance(self):
        """싱글톤 인스턴스 반환"""
        # 기존 인스턴스 초기화
        import serverless.services.csv_url_resolver as module
        module._resolver_instance = None

        resolver1 = get_csv_url_resolver()
        resolver2 = get_csv_url_resolver()

        assert resolver1 is resolver2


class TestIntegration:
    """통합 테스트"""

    def test_full_resolution_flow(self, resolver):
        """전체 복구 플로우"""
        # HTML 페이지 응답 모킹
        html_response = MagicMock()
        html_response.text = '''
        <html>
        <a href="https://www.ssga.com/holdings-daily-us-en-xlk.xlsx">Download Holdings</a>
        </html>
        '''

        # HEAD 요청 응답 모킹 (URL 검증)
        head_response = MagicMock()
        head_response.status_code = 200
        head_response.headers = {'Content-Type': 'application/vnd.openxmlformats'}

        resolver.client.get.return_value = html_response
        resolver.client.head.return_value = head_response

        url = resolver.resolve_csv_url(
            etf_symbol='XLK',
            parser_type='spdr',
            current_url='https://old-url.com/data.csv'
        )

        assert url is not None
        assert 'holdings' in url.lower()
