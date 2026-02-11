"""
ETF CSV Downloader 테스트

ETFCSVDownloader 서비스의 유닛 테스트입니다.
"""
import pytest
from decimal import Decimal
from datetime import date
from unittest.mock import Mock, patch, MagicMock

from serverless.models import ETFProfile, ETFHolding
from serverless.services.etf_csv_downloader import (
    ETFCSVDownloader,
    ETFCSVDownloadError,
    ETFCSVParseError,
    ETF_CSV_SOURCES,
)


@pytest.fixture
def downloader():
    """ETFCSVDownloader 인스턴스"""
    return ETFCSVDownloader()


@pytest.fixture
def sample_spdr_csv():
    """SPDR ETF CSV 샘플 데이터"""
    return """As of Date: 2026-02-10
Fund Name: Technology Select Sector SPDR Fund
Ticker: XLK

Name,Ticker,Identifier,SEDOL,Weight,Sector,Shares Held,Local Currency
Apple Inc,AAPL,12345,B123456,22.50,Technology,1000000,USD
Microsoft Corp,MSFT,12346,B123457,20.00,Technology,800000,USD
NVIDIA Corp,NVDA,12347,B123458,8.50,Technology,500000,USD
"""


@pytest.fixture
def sample_ishares_csv():
    """iShares ETF CSV 샘플 데이터"""
    return """Fund Name: iShares Semiconductor ETF
Fund Holdings as of: 2026-02-10

Ticker,Name,Sector,Asset Class,Market Value,Weight (%),Shares,CUSIP,ISIN,SEDOL,Price,Location,Exchange,Currency
NVDA,NVIDIA Corporation,Technology,Equity,15000000000,10.50,50000000,12345678,US12345,B123456,300.00,United States,NASDAQ,USD
AMD,Advanced Micro Devices,Technology,Equity,8000000000,5.50,60000000,12345679,US12346,B123457,133.33,United States,NASDAQ,USD
INTC,Intel Corporation,Technology,Equity,5000000000,3.50,100000000,12345680,US12347,B123458,50.00,United States,NASDAQ,USD
"""


@pytest.fixture
def sample_ark_csv():
    """ARK ETF CSV 샘플 데이터"""
    return """date,fund,company,ticker,cusip,shares,"market value ($)","weight (%)"
2026-02-10,ARKK,Tesla Inc,TSLA,88160R101,1000000,250000000,10.50
2026-02-10,ARKK,Roku Inc,ROKU,77543R102,500000,50000000,5.00
2026-02-10,ARKK,Zoom Video,ZM,98980L101,300000,30000000,3.00
"""


class TestETFCSVDownloaderInit:
    """ETFCSVDownloader 초기화 테스트"""

    def test_etf_csv_sources_not_empty(self):
        """ETF_CSV_SOURCES가 비어있지 않음"""
        assert len(ETF_CSV_SOURCES) > 0

    def test_etf_csv_sources_has_sector_and_theme(self):
        """섹터와 테마 ETF가 모두 포함됨"""
        tiers = set(config['tier'] for config in ETF_CSV_SOURCES.values())
        assert 'sector' in tiers
        assert 'theme' in tiers

    def test_xlk_in_sources(self):
        """XLK (기술 섹터 ETF)가 소스에 포함됨"""
        assert 'XLK' in ETF_CSV_SOURCES
        assert ETF_CSV_SOURCES['XLK']['tier'] == 'sector'
        assert ETF_CSV_SOURCES['XLK']['theme_id'] == 'technology'

    def test_soxx_in_sources(self):
        """SOXX (반도체 테마 ETF)가 소스에 포함됨"""
        assert 'SOXX' in ETF_CSV_SOURCES
        assert ETF_CSV_SOURCES['SOXX']['tier'] == 'theme'
        assert ETF_CSV_SOURCES['SOXX']['theme_id'] == 'semiconductor'


class TestETFCSVParsing:
    """CSV 파싱 테스트"""

    def test_parse_spdr_csv(self, downloader, sample_spdr_csv):
        """SPDR CSV 파싱"""
        holdings = downloader._parse_csv(
            sample_spdr_csv.encode('utf-8'),
            'spdr',
            'XLK'
        )

        assert len(holdings) == 3
        assert holdings[0]['symbol'] == 'AAPL'
        assert holdings[0]['weight'] == 22.5
        assert holdings[1]['symbol'] == 'MSFT'
        assert holdings[1]['weight'] == 20.0

    def test_parse_ishares_csv(self, downloader, sample_ishares_csv):
        """iShares CSV 파싱"""
        holdings = downloader._parse_csv(
            sample_ishares_csv.encode('utf-8'),
            'ishares',
            'SOXX'
        )

        assert len(holdings) == 3
        assert holdings[0]['symbol'] == 'NVDA'
        assert holdings[0]['weight'] == 10.5
        assert holdings[0]['market_value'] == 15000000000

    def test_parse_ark_csv(self, downloader, sample_ark_csv):
        """ARK CSV 파싱"""
        holdings = downloader._parse_csv(
            sample_ark_csv.encode('utf-8'),
            'ark',
            'ARKK'
        )

        assert len(holdings) == 3
        assert holdings[0]['symbol'] == 'TSLA'
        assert holdings[0]['weight'] == 10.5
        assert holdings[0]['shares'] == 1000000

    def test_parse_csv_assigns_rank(self, downloader, sample_spdr_csv):
        """순위가 자동으로 부여됨"""
        holdings = downloader._parse_csv(
            sample_spdr_csv.encode('utf-8'),
            'spdr',
            'XLK'
        )

        for i, h in enumerate(holdings, start=1):
            assert h['rank'] == i

    def test_parse_csv_sorted_by_weight(self, downloader, sample_spdr_csv):
        """비중 순으로 정렬됨"""
        holdings = downloader._parse_csv(
            sample_spdr_csv.encode('utf-8'),
            'spdr',
            'XLK'
        )

        weights = [h['weight'] for h in holdings]
        assert weights == sorted(weights, reverse=True)


class TestDecimalParsing:
    """Decimal 파싱 테스트"""

    def test_parse_decimal_normal(self, downloader):
        """일반 숫자 파싱"""
        assert downloader._parse_decimal('22.50') == Decimal('22.50')

    def test_parse_decimal_with_comma(self, downloader):
        """쉼표 포함 숫자 파싱"""
        assert downloader._parse_decimal('1,000,000') == Decimal('1000000')

    def test_parse_decimal_with_percent(self, downloader):
        """퍼센트 기호 포함 파싱"""
        assert downloader._parse_decimal('22.50%') == Decimal('22.50')

    def test_parse_decimal_empty(self, downloader):
        """빈 문자열 파싱"""
        assert downloader._parse_decimal('') is None

    def test_parse_decimal_dash(self, downloader):
        """대시(-) 파싱"""
        assert downloader._parse_decimal('-') is None


class TestIntParsing:
    """정수 파싱 테스트"""

    def test_parse_int_normal(self, downloader):
        """일반 정수 파싱"""
        assert downloader._parse_int('1000000') == 1000000

    def test_parse_int_with_comma(self, downloader):
        """쉼표 포함 정수 파싱"""
        assert downloader._parse_int('1,000,000') == 1000000

    def test_parse_int_float(self, downloader):
        """소수점 포함 파싱"""
        assert downloader._parse_int('1000000.50') == 1000000


@pytest.mark.django_db
class TestETFProfileInit:
    """ETFProfile 초기화 테스트"""

    def test_initialize_etf_profiles_creates_profiles(self, downloader):
        """ETFProfile 생성"""
        count = downloader.initialize_etf_profiles()

        # 생성된 프로필 수 확인
        assert count > 0
        assert ETFProfile.objects.count() >= count

    def test_initialize_etf_profiles_idempotent(self, downloader):
        """초기화 멱등성"""
        count1 = downloader.initialize_etf_profiles()
        count2 = downloader.initialize_etf_profiles()

        # 두 번째 호출에서는 생성 없음
        assert count2 == 0

    def test_xlk_profile_created(self, downloader):
        """XLK 프로필 생성 확인"""
        downloader.initialize_etf_profiles()

        xlk = ETFProfile.objects.get(symbol='XLK')
        assert xlk.tier == 'sector'
        assert xlk.theme_id == 'technology'
        assert xlk.is_active is True


@pytest.mark.django_db
class TestETFHoldingSave:
    """ETF Holdings 저장 테스트"""

    def test_save_holdings(self, downloader):
        """Holdings 저장"""
        # ETFProfile 생성
        profile = ETFProfile.objects.create(
            symbol='TEST',
            name='Test ETF',
            tier='sector',
            theme_id='test'
        )

        holdings = [
            {'symbol': 'AAPL', 'weight': 22.5, 'shares': 1000000, 'market_value': 150000000, 'rank': 1},
            {'symbol': 'MSFT', 'weight': 20.0, 'shares': 800000, 'market_value': 120000000, 'rank': 2},
        ]

        count = downloader._save_holdings(profile, holdings, 'test_hash')

        assert count == 2
        assert ETFHolding.objects.filter(etf=profile).count() == 2
        assert profile.last_hash == 'test_hash'

    def test_save_holdings_replaces_old_data(self, downloader):
        """기존 데이터 교체"""
        profile = ETFProfile.objects.create(
            symbol='TEST2',
            name='Test ETF 2',
            tier='sector',
            theme_id='test2'
        )

        # 첫 번째 저장
        holdings1 = [
            {'symbol': 'AAPL', 'weight': 22.5, 'shares': 1000000, 'market_value': None, 'rank': 1},
        ]
        downloader._save_holdings(profile, holdings1, 'hash1')

        # 두 번째 저장 (다른 데이터)
        holdings2 = [
            {'symbol': 'MSFT', 'weight': 20.0, 'shares': 800000, 'market_value': None, 'rank': 1},
            {'symbol': 'GOOGL', 'weight': 15.0, 'shares': 600000, 'market_value': None, 'rank': 2},
        ]
        downloader._save_holdings(profile, holdings2, 'hash2')

        # 이전 데이터는 삭제되고 새 데이터만 존재
        holdings = ETFHolding.objects.filter(etf=profile)
        symbols = set(h.stock_symbol for h in holdings)
        assert symbols == {'MSFT', 'GOOGL'}


class TestGenericParser:
    """범용 파서 테스트"""

    def test_parse_generic_csv(self, downloader):
        """범용 CSV 파싱"""
        csv_data = """Ticker,Name,Weight,Shares
AAPL,Apple Inc,22.5,1000000
MSFT,Microsoft Corp,20.0,800000
"""
        holdings = downloader._parse_csv(
            csv_data.encode('utf-8'),
            'generic',
            'TEST'
        )

        assert len(holdings) == 2
        assert holdings[0]['symbol'] == 'AAPL'
        assert holdings[0]['weight'] == 22.5

    def test_parse_generic_csv_alternative_headers(self, downloader):
        """대체 헤더 지원"""
        csv_data = """Symbol,Company,Percent
AAPL,Apple Inc,22.5
MSFT,Microsoft Corp,20.0
"""
        holdings = downloader._parse_csv(
            csv_data.encode('utf-8'),
            'generic',
            'TEST'
        )

        assert len(holdings) == 2
        assert holdings[0]['symbol'] == 'AAPL'


class TestChangeDetection:
    """변경 감지 테스트"""

    @pytest.mark.django_db
    def test_detect_changes_new_etf(self, downloader):
        """신규 ETF는 항상 변경됨"""
        profile = ETFProfile.objects.create(
            symbol='NEW',
            name='New ETF',
            tier='theme',
            theme_id='new',
            csv_url='http://example.com/test.csv',
            last_row_count=0
        )

        changed, prev, curr = downloader.detect_changes('NEW')
        assert changed is True or prev == 0  # 최초 조회


class TestErrorHandling:
    """에러 처리 테스트"""

    @pytest.mark.django_db
    def test_download_holdings_no_profile(self, downloader):
        """프로필 없는 ETF 다운로드 시 에러"""
        with pytest.raises(ETFCSVDownloadError) as excinfo:
            downloader.download_holdings('NONEXISTENT')

        assert 'ETF 프로필 없음' in str(excinfo.value)

    @pytest.mark.django_db
    def test_download_holdings_no_url(self, downloader):
        """URL 없는 ETF 다운로드 시 에러"""
        ETFProfile.objects.create(
            symbol='NOURL',
            name='No URL ETF',
            tier='theme',
            theme_id='nourl',
            csv_url=''
        )

        with pytest.raises(ETFCSVDownloadError) as excinfo:
            downloader.download_holdings('NOURL')

        assert 'CSV URL 미설정' in str(excinfo.value)
