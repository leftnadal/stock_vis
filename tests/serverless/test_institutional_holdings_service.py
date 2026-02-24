"""
InstitutionalHoldingsService 테스트

SEC 13F 기관 보유 현황 수집 및 관계 생성 서비스를 검증합니다.

테스트 대상:
1. InstitutionalHolding 모델
2. InstitutionalHoldingsService
   - sync_institution(): 단일 기관 동기화
   - sync_all_institutions(): 전체 동기화
   - generate_held_by_same_fund(): 동일 펀드 보유 관계 생성
   - get_institution_holdings(): 기관 보유 현황 조회
   - get_stock_institutional_holders(): 종목별 기관 보유 조회
   - get_same_fund_peers(): 같은 펀드 보유 종목 조회
"""
import pytest
from datetime import date, datetime
from decimal import Decimal
from unittest.mock import Mock, patch, MagicMock
from dataclasses import dataclass

from serverless.models import InstitutionalHolding, StockRelationship
from serverless.services.institutional_holdings_service import InstitutionalHoldingsService


# ========================================
# Mock Data Classes
# ========================================

@dataclass
class MockFiling13F:
    """Mock 13F Filing metadata"""
    accession_number: str
    filing_date: date
    report_date: date
    info_table_document: str
    cik: str
    institution_name: str
    form_type: str = "13F-HR"


# ========================================
# Fixtures
# ========================================

@pytest.fixture
def service():
    """InstitutionalHoldingsService 인스턴스"""
    return InstitutionalHoldingsService()


@pytest.fixture
def mock_sec_client():
    """Mock SECEdgarClient"""
    mock = Mock()
    return mock


@pytest.fixture
def mock_cusip_mapper():
    """Mock CUSIPMapper"""
    mock = Mock()
    # 기본 매핑 설정
    mock.cusip_to_ticker.side_effect = lambda cusip: {
        '037833100': 'AAPL',
        '594918104': 'MSFT',
        '67066G104': 'NVDA',
        '88160R101': 'TSLA',
        '30303M102': 'META',
    }.get(cusip)
    return mock


@pytest.fixture
def sample_13f_filing():
    """샘플 13F 파일링 메타데이터"""
    return MockFiling13F(
        accession_number='0001067983-25-000001',
        filing_date=date(2025, 11, 14),
        report_date=date(2025, 9, 30),
        info_table_document='primary_doc.xml',
        cik='0001067983',
        institution_name='Berkshire Hathaway'
    )


@pytest.fixture
def sample_13f_holdings():
    """샘플 13F 보유 종목 데이터"""
    return [
        {
            'cusip': '037833100',
            'shares': 915560000,
            'value': 158000000,  # thousands
        },
        {
            'cusip': '594918104',
            'shares': 7000000,
            'value': 2800000,
        },
        {
            'cusip': '67066G104',
            'shares': 1200000,
            'value': 150000,
        },
        {
            'cusip': '88160R101',
            'shares': 500000,
            'value': 125000,
        },
        {
            'cusip': 'UNKNOWN123',  # 매핑 실패 케이스
            'shares': 1000,
            'value': 10,
        }
    ]


@pytest.fixture
def sample_previous_holdings():
    """이전 분기 보유 종목 (shares_change 계산용)"""
    return [
        {
            'cusip': '037833100',
            'shares': 900000000,  # 증가
        },
        {
            'cusip': '594918104',
            'shares': 8000000,  # 감소
        },
        {
            'cusip': '88160R101',
            'shares': 500000,  # 변동 없음
        },
        # NVDA는 신규 매수
    ]


# ========================================
# InstitutionalHolding 모델 테스트
# ========================================

class TestInstitutionalHoldingModel:
    """InstitutionalHolding 모델 검증"""

    @pytest.mark.django_db
    def test_create_institutional_holding(self):
        """기관 보유 현황 생성"""
        holding = InstitutionalHolding.objects.create(
            institution_cik='0001067983',
            institution_name='Berkshire Hathaway',
            filing_date=date(2025, 11, 14),
            report_date=date(2025, 9, 30),
            accession_number='0001067983-25-000001',
            stock_symbol='AAPL',
            shares=915560000,
            value_thousands=158000000,
            shares_change=15560000,
            position_change='increased'
        )

        assert holding.institution_cik == '0001067983'
        assert holding.institution_name == 'Berkshire Hathaway'
        assert holding.stock_symbol == 'AAPL'
        assert holding.shares == 915560000
        assert holding.value_thousands == 158000000
        assert holding.shares_change == 15560000
        assert holding.position_change == 'increased'

    @pytest.mark.django_db
    def test_unique_together_constraint(self):
        """unique_together 제약 조건 검증"""
        # 첫 번째 레코드
        InstitutionalHolding.objects.create(
            institution_cik='0001067983',
            institution_name='Berkshire Hathaway',
            filing_date=date(2025, 11, 14),
            report_date=date(2025, 9, 30),
            accession_number='0001067983-25-000001',
            stock_symbol='AAPL',
            shares=915560000,
            value_thousands=158000000
        )

        # 같은 institution_cik, stock_symbol, report_date는 중복 불가
        from django.db import IntegrityError
        with pytest.raises(IntegrityError):
            InstitutionalHolding.objects.create(
                institution_cik='0001067983',
                institution_name='Berkshire Hathaway',
                filing_date=date(2025, 11, 15),  # 다른 filing_date
                report_date=date(2025, 9, 30),  # 같은 report_date
                accession_number='0001067983-25-000002',
                stock_symbol='AAPL',  # 같은 symbol
                shares=900000000,
                value_thousands=150000000
            )

    @pytest.mark.django_db
    def test_str_representation(self):
        """__str__ 메서드 검증"""
        holding = InstitutionalHolding.objects.create(
            institution_cik='0001067983',
            institution_name='Berkshire Hathaway',
            filing_date=date(2025, 11, 14),
            report_date=date(2025, 9, 30),
            accession_number='0001067983-25-000001',
            stock_symbol='AAPL',
            shares=915560000,
            value_thousands=158000000
        )

        assert str(holding) == "Berkshire Hathaway: AAPL (915,560,000 shares)"

    @pytest.mark.django_db
    def test_position_change_choices(self):
        """POSITION_CHANGE_CHOICES 검증"""
        valid_choices = ['new', 'increased', 'decreased', 'sold_all', 'unchanged']

        for choice in valid_choices:
            holding = InstitutionalHolding.objects.create(
                institution_cik='0001067983',
                institution_name='Berkshire Hathaway',
                filing_date=date(2025, 11, 14),
                report_date=date(2025, 9, 30),
                accession_number=f'test-{choice}',
                stock_symbol=f'TEST{choice.upper()[:4]}',
                shares=1000000,
                value_thousands=100000,
                position_change=choice
            )
            assert holding.position_change == choice

    @pytest.mark.django_db
    def test_ordering(self):
        """ordering 검증: -report_date, institution_name"""
        InstitutionalHolding.objects.create(
            institution_cik='0001067983',
            institution_name='Berkshire Hathaway',
            filing_date=date(2025, 11, 14),
            report_date=date(2025, 9, 30),
            accession_number='test-1',
            stock_symbol='AAPL',
            shares=1000000,
            value_thousands=100000
        )

        InstitutionalHolding.objects.create(
            institution_cik='0001364742',
            institution_name='BlackRock',
            filing_date=date(2025, 11, 15),
            report_date=date(2025, 9, 30),
            accession_number='test-2',
            stock_symbol='AAPL',
            shares=2000000,
            value_thousands=200000
        )

        InstitutionalHolding.objects.create(
            institution_cik='0001067983',
            institution_name='Berkshire Hathaway',
            filing_date=date(2025, 8, 14),
            report_date=date(2025, 6, 30),
            accession_number='test-3',
            stock_symbol='AAPL',
            shares=900000,
            value_thousands=90000
        )

        holdings = list(InstitutionalHolding.objects.all())

        # 첫 번째: 최신 report_date (2025-09-30), 알파벳 순으로 Berkshire Hathaway
        assert holdings[0].report_date == date(2025, 9, 30)
        assert holdings[0].institution_name == 'Berkshire Hathaway'

        # 두 번째: 같은 report_date, 알파벳 순으로 BlackRock
        assert holdings[1].report_date == date(2025, 9, 30)
        assert holdings[1].institution_name == 'BlackRock'

        # 세 번째: 이전 report_date
        assert holdings[2].report_date == date(2025, 6, 30)


# ========================================
# sync_institution() 테스트
# ========================================

class TestSyncInstitution:
    """sync_institution() 메서드 테스트"""

    @pytest.mark.django_db
    def test_sync_institution_success(
        self,
        sample_13f_filing,
        sample_13f_holdings,
        sample_previous_holdings
    ):
        """단일 기관 동기화 성공"""
        # Mock 설정
        mock_sec = Mock()
        mock_sec.get_13f_filings.return_value = [sample_13f_filing, Mock()]  # latest + previous

        # Previous holdings 설정
        prev_filing = Mock()
        mock_sec.download_13f_holdings.side_effect = [
            sample_13f_holdings,  # 최신
            sample_previous_holdings  # 이전
        ]

        mock_cusip = Mock()
        mock_cusip.cusip_to_ticker.side_effect = lambda cusip: {
            '037833100': 'AAPL',
            '594918104': 'MSFT',
            '67066G104': 'NVDA',
            '88160R101': 'TSLA',
        }.get(cusip)

        # 서비스 실행 (Mock 주입)
        service = InstitutionalHoldingsService()
        service.sec_client = mock_sec
        service.cusip_mapper = mock_cusip

        result = service.sync_institution('0001067983', 'Berkshire Hathaway')

        # 결과 검증
        assert result['institution'] == 'Berkshire Hathaway'
        assert result['filing_date'] == '2025-11-14'
        assert result['holdings_count'] == 4  # 4개 매핑 성공
        assert result['mapped'] == 4
        assert result['unmapped'] == 1  # UNKNOWN123

        # DB 검증
        holdings = InstitutionalHolding.objects.filter(institution_cik='0001067983')
        assert holdings.count() == 4

        # AAPL 검증 (증가)
        aapl = holdings.get(stock_symbol='AAPL')
        assert aapl.shares == 915560000
        assert aapl.shares_change == 15560000  # 915560000 - 900000000
        assert aapl.position_change == 'increased'

        # MSFT 검증 (감소)
        msft = holdings.get(stock_symbol='MSFT')
        assert msft.shares == 7000000
        assert msft.shares_change == -1000000  # 7000000 - 8000000
        assert msft.position_change == 'decreased'

        # NVDA 검증 (신규)
        nvda = holdings.get(stock_symbol='NVDA')
        assert nvda.shares == 1200000
        assert nvda.position_change == 'new'

        # TSLA 검증 (변동 없음)
        tsla = holdings.get(stock_symbol='TSLA')
        assert tsla.shares == 500000
        assert tsla.shares_change == 0
        assert tsla.position_change == 'unchanged'

    @pytest.mark.django_db
    def test_sync_institution_no_filings(self):
        """13F 파일링 없는 경우"""
        mock_sec = Mock()
        mock_sec.get_13f_filings.return_value = []

        mock_cusip = Mock()

        service = InstitutionalHoldingsService()
        service.sec_client = mock_sec
        service.cusip_mapper = mock_cusip

        result = service.sync_institution('0000000000', 'Unknown Institution')

        assert result['institution'] == 'Unknown Institution'
        assert result['holdings_count'] == 0
        assert result['mapped'] == 0
        assert result['unmapped'] == 0

    @pytest.mark.django_db
    def test_sync_institution_no_holdings(self, sample_13f_filing):
        """보유 종목 없는 경우"""
        mock_sec = Mock()
        mock_sec.get_13f_filings.return_value = [sample_13f_filing]
        mock_sec.download_13f_holdings.return_value = []

        mock_cusip = Mock()

        service = InstitutionalHoldingsService()
        service.sec_client = mock_sec
        service.cusip_mapper = mock_cusip

        result = service.sync_institution('0001067983', 'Berkshire Hathaway')

        assert result['institution'] == 'Berkshire Hathaway'
        assert result['filing_date'] == '2025-11-14'
        assert result['holdings_count'] == 0

    @pytest.mark.django_db
    def test_sync_institution_symbol_upper(
        self,
        sample_13f_filing,
        sample_13f_holdings
    ):
        """symbol.upper() 규칙 검증"""
        mock_sec = Mock()
        mock_sec.get_13f_filings.return_value = [sample_13f_filing]
        mock_sec.download_13f_holdings.return_value = sample_13f_holdings

        mock_cusip = Mock()
        # 소문자 ticker 반환
        mock_cusip.cusip_to_ticker.side_effect = lambda cusip: {
            '037833100': 'aapl',  # lowercase
        }.get(cusip)

        service = InstitutionalHoldingsService()
        service.sec_client = mock_sec
        service.cusip_mapper = mock_cusip

        result = service.sync_institution('0001067983', 'Berkshire Hathaway')

        assert result['holdings_count'] == 1

        # DB에 저장된 symbol은 대문자여야 함
        holding = InstitutionalHolding.objects.get(institution_cik='0001067983')
        assert holding.stock_symbol == 'AAPL'


# ========================================
# sync_all_institutions() 테스트
# ========================================

class TestSyncAllInstitutions:
    """sync_all_institutions() 메서드 테스트"""

    @pytest.mark.django_db
    def test_sync_all_institutions_success(self):
        """전체 기관 동기화 성공"""
        service = InstitutionalHoldingsService()

        # Mock SEC client와 CUSIP mapper 주입
        mock_sec = Mock()
        mock_cusip = Mock()
        service.sec_client = mock_sec
        service.cusip_mapper = mock_cusip

        # sync_institution을 mock으로 교체
        original_sync = service.sync_institution
        call_count = [0]

        def mock_sync_institution(cik, name):
            call_count[0] += 1
            # 대부분 성공, 일부 실패
            if call_count[0] % 5 == 0:
                return {'holdings_count': 0}  # 실패
            else:
                return {'holdings_count': 30 + call_count[0]}  # 성공

        service.sync_institution = mock_sync_institution

        result = service.sync_all_institutions()

        assert result['total_institutions'] == len(service.KEY_INSTITUTIONS)
        assert result['success'] > 0
        assert result['failed'] >= 0
        assert result['total_holdings'] > 0

    @pytest.mark.django_db
    def test_sync_all_institutions_no_sec_client(self):
        """SEC client 없는 경우"""
        service = InstitutionalHoldingsService()
        service.sec_client = None

        result = service.sync_all_institutions()

        assert result['total_institutions'] == 0
        assert result['success'] == 0
        assert result['failed'] == 0
        assert result['total_holdings'] == 0


# ========================================
# generate_held_by_same_fund() 테스트
# ========================================

class TestGenerateHeldBySameFund:
    """generate_held_by_same_fund() 메서드 테스트"""

    @pytest.mark.django_db
    def test_generate_held_by_same_fund_success(self):
        """동일 펀드 보유 관계 생성 성공"""
        # 3개 기관, 3개 종목 설정
        report_date = date(2025, 9, 30)

        # Berkshire: AAPL, MSFT
        InstitutionalHolding.objects.create(
            institution_cik='0001067983',
            institution_name='Berkshire Hathaway',
            filing_date=date(2025, 11, 14),
            report_date=report_date,
            accession_number='test-1',
            stock_symbol='AAPL',
            shares=915560000,
            value_thousands=158000000
        )
        InstitutionalHolding.objects.create(
            institution_cik='0001067983',
            institution_name='Berkshire Hathaway',
            filing_date=date(2025, 11, 14),
            report_date=report_date,
            accession_number='test-1',
            stock_symbol='MSFT',
            shares=7000000,
            value_thousands=2800000
        )

        # BlackRock: AAPL, MSFT, NVDA
        InstitutionalHolding.objects.create(
            institution_cik='0001364742',
            institution_name='BlackRock',
            filing_date=date(2025, 11, 15),
            report_date=report_date,
            accession_number='test-2',
            stock_symbol='AAPL',
            shares=500000000,
            value_thousands=85000000
        )
        InstitutionalHolding.objects.create(
            institution_cik='0001364742',
            institution_name='BlackRock',
            filing_date=date(2025, 11, 15),
            report_date=report_date,
            accession_number='test-2',
            stock_symbol='MSFT',
            shares=8000000,
            value_thousands=3200000
        )
        InstitutionalHolding.objects.create(
            institution_cik='0001364742',
            institution_name='BlackRock',
            filing_date=date(2025, 11, 15),
            report_date=report_date,
            accession_number='test-2',
            stock_symbol='NVDA',
            shares=2000000,
            value_thousands=250000
        )

        # Vanguard: AAPL, MSFT, NVDA
        InstitutionalHolding.objects.create(
            institution_cik='0001166559',
            institution_name='Vanguard Group',
            filing_date=date(2025, 11, 16),
            report_date=report_date,
            accession_number='test-3',
            stock_symbol='AAPL',
            shares=600000000,
            value_thousands=102000000
        )
        InstitutionalHolding.objects.create(
            institution_cik='0001166559',
            institution_name='Vanguard Group',
            filing_date=date(2025, 11, 16),
            report_date=report_date,
            accession_number='test-3',
            stock_symbol='MSFT',
            shares=9000000,
            value_thousands=3600000
        )
        InstitutionalHolding.objects.create(
            institution_cik='0001166559',
            institution_name='Vanguard Group',
            filing_date=date(2025, 11, 16),
            report_date=report_date,
            accession_number='test-3',
            stock_symbol='NVDA',
            shares=3000000,
            value_thousands=375000
        )

        # 관계 생성 (min_shared_institutions=3)
        service = InstitutionalHoldingsService()
        count = service.generate_held_by_same_fund(min_shared_institutions=3)

        # AAPL-MSFT: 3개 기관 공통 (Berkshire, BlackRock, Vanguard)
        # AAPL-NVDA: 2개 기관 공통 (BlackRock, Vanguard) -> 제외
        # MSFT-NVDA: 2개 기관 공통 (BlackRock, Vanguard) -> 제외
        assert count == 1  # AAPL <-> MSFT 양방향 = 1 pair

        # 관계 검증 (양방향)
        aapl_to_msft = StockRelationship.objects.get(
            source_symbol='AAPL',
            target_symbol='MSFT',
            relationship_type='HELD_BY_SAME_FUND'
        )
        assert aapl_to_msft.strength > 0
        assert aapl_to_msft.source_provider == 'sec_13f'
        assert aapl_to_msft.context['shared_count'] == 3
        assert aapl_to_msft.context['total_institutions'] == 3
        assert len(aapl_to_msft.context['shared_institutions']) == 3

        msft_to_aapl = StockRelationship.objects.get(
            source_symbol='MSFT',
            target_symbol='AAPL',
            relationship_type='HELD_BY_SAME_FUND'
        )
        assert msft_to_aapl.strength == aapl_to_msft.strength

    @pytest.mark.django_db
    def test_generate_held_by_same_fund_no_data(self):
        """보유 현황 데이터 없는 경우"""
        service = InstitutionalHoldingsService()
        count = service.generate_held_by_same_fund()

        assert count == 0

    @pytest.mark.django_db
    def test_generate_held_by_same_fund_min_threshold(self):
        """min_shared_institutions 임계값 검증"""
        report_date = date(2025, 9, 30)

        # 2개 기관, 2개 종목
        InstitutionalHolding.objects.create(
            institution_cik='0001067983',
            institution_name='Berkshire Hathaway',
            filing_date=date(2025, 11, 14),
            report_date=report_date,
            accession_number='test-1',
            stock_symbol='AAPL',
            shares=915560000,
            value_thousands=158000000
        )
        InstitutionalHolding.objects.create(
            institution_cik='0001067983',
            institution_name='Berkshire Hathaway',
            filing_date=date(2025, 11, 14),
            report_date=report_date,
            accession_number='test-1',
            stock_symbol='MSFT',
            shares=7000000,
            value_thousands=2800000
        )

        InstitutionalHolding.objects.create(
            institution_cik='0001364742',
            institution_name='BlackRock',
            filing_date=date(2025, 11, 15),
            report_date=report_date,
            accession_number='test-2',
            stock_symbol='AAPL',
            shares=500000000,
            value_thousands=85000000
        )
        InstitutionalHolding.objects.create(
            institution_cik='0001364742',
            institution_name='BlackRock',
            filing_date=date(2025, 11, 15),
            report_date=report_date,
            accession_number='test-2',
            stock_symbol='MSFT',
            shares=8000000,
            value_thousands=3200000
        )

        service = InstitutionalHoldingsService()

        # min=3이면 관계 생성 안 됨 (2개 기관만 있음)
        count_min3 = service.generate_held_by_same_fund(min_shared_institutions=3)
        assert count_min3 == 0

        # min=2이면 관계 생성됨
        count_min2 = service.generate_held_by_same_fund(min_shared_institutions=2)
        assert count_min2 == 1


# ========================================
# get_institution_holdings() 테스트
# ========================================

class TestGetInstitutionHoldings:
    """get_institution_holdings() 메서드 테스트"""

    @pytest.mark.django_db
    def test_get_institution_holdings_success(self):
        """기관 보유 현황 조회 성공"""
        report_date = date(2025, 9, 30)

        InstitutionalHolding.objects.create(
            institution_cik='0001067983',
            institution_name='Berkshire Hathaway',
            filing_date=date(2025, 11, 14),
            report_date=report_date,
            accession_number='test-1',
            stock_symbol='AAPL',
            shares=915560000,
            value_thousands=158000000,
            shares_change=15560000,
            position_change='increased'
        )
        InstitutionalHolding.objects.create(
            institution_cik='0001067983',
            institution_name='Berkshire Hathaway',
            filing_date=date(2025, 11, 14),
            report_date=report_date,
            accession_number='test-1',
            stock_symbol='MSFT',
            shares=7000000,
            value_thousands=2800000,
            shares_change=-1000000,
            position_change='decreased'
        )

        service = InstitutionalHoldingsService()
        holdings = service.get_institution_holdings('0001067983')

        assert len(holdings) == 2

        # value_thousands 기준 정렬 (AAPL > MSFT)
        assert holdings[0]['symbol'] == 'AAPL'
        assert holdings[0]['shares'] == 915560000
        assert holdings[0]['value_thousands'] == 158000000
        assert holdings[0]['shares_change'] == 15560000
        assert holdings[0]['position_change'] == 'increased'
        assert holdings[0]['report_date'] == '2025-09-30'

        assert holdings[1]['symbol'] == 'MSFT'

    @pytest.mark.django_db
    def test_get_institution_holdings_no_data(self):
        """보유 현황 없는 경우"""
        service = InstitutionalHoldingsService()
        holdings = service.get_institution_holdings('0000000000')

        assert holdings == []

    @pytest.mark.django_db
    def test_get_institution_holdings_latest_only(self):
        """최신 report_date만 조회"""
        # 이전 분기
        InstitutionalHolding.objects.create(
            institution_cik='0001067983',
            institution_name='Berkshire Hathaway',
            filing_date=date(2025, 8, 14),
            report_date=date(2025, 6, 30),
            accession_number='test-old',
            stock_symbol='AAPL',
            shares=900000000,
            value_thousands=150000000
        )

        # 최신 분기
        InstitutionalHolding.objects.create(
            institution_cik='0001067983',
            institution_name='Berkshire Hathaway',
            filing_date=date(2025, 11, 14),
            report_date=date(2025, 9, 30),
            accession_number='test-new',
            stock_symbol='AAPL',
            shares=915560000,
            value_thousands=158000000
        )

        service = InstitutionalHoldingsService()
        holdings = service.get_institution_holdings('0001067983')

        # 최신만 반환
        assert len(holdings) == 1
        assert holdings[0]['shares'] == 915560000
        assert holdings[0]['report_date'] == '2025-09-30'


# ========================================
# get_stock_institutional_holders() 테스트
# ========================================

class TestGetStockInstitutionalHolders:
    """get_stock_institutional_holders() 메서드 테스트"""

    @pytest.mark.django_db
    def test_get_stock_institutional_holders_success(self):
        """종목별 기관 보유 조회 성공"""
        report_date = date(2025, 9, 30)

        InstitutionalHolding.objects.create(
            institution_cik='0001067983',
            institution_name='Berkshire Hathaway',
            filing_date=date(2025, 11, 14),
            report_date=report_date,
            accession_number='test-1',
            stock_symbol='AAPL',
            shares=915560000,
            value_thousands=158000000
        )
        InstitutionalHolding.objects.create(
            institution_cik='0001364742',
            institution_name='BlackRock',
            filing_date=date(2025, 11, 15),
            report_date=report_date,
            accession_number='test-2',
            stock_symbol='AAPL',
            shares=500000000,
            value_thousands=85000000
        )

        service = InstitutionalHoldingsService()
        holders = service.get_stock_institutional_holders('AAPL')

        assert len(holders) == 2

        # value_thousands 기준 정렬 (Berkshire > BlackRock)
        assert holders[0]['institution_name'] == 'Berkshire Hathaway'
        assert holders[0]['institution_cik'] == '0001067983'
        assert holders[0]['shares'] == 915560000
        assert holders[0]['value_thousands'] == 158000000
        assert holders[0]['filing_date'] == '2025-11-14'
        assert holders[0]['report_date'] == '2025-09-30'

        assert holders[1]['institution_name'] == 'BlackRock'

    @pytest.mark.django_db
    def test_get_stock_institutional_holders_symbol_upper(self):
        """symbol.upper() 규칙 검증"""
        report_date = date(2025, 9, 30)

        InstitutionalHolding.objects.create(
            institution_cik='0001067983',
            institution_name='Berkshire Hathaway',
            filing_date=date(2025, 11, 14),
            report_date=report_date,
            accession_number='test-1',
            stock_symbol='AAPL',
            shares=915560000,
            value_thousands=158000000
        )

        service = InstitutionalHoldingsService()

        # 소문자로 조회해도 동작
        holders = service.get_stock_institutional_holders('aapl')
        assert len(holders) == 1

    @pytest.mark.django_db
    def test_get_stock_institutional_holders_no_data(self):
        """보유 기관 없는 경우"""
        service = InstitutionalHoldingsService()
        holders = service.get_stock_institutional_holders('UNKNOWN')

        assert holders == []


# ========================================
# get_same_fund_peers() 테스트
# ========================================

class TestGetSameFundPeers:
    """get_same_fund_peers() 메서드 테스트"""

    @pytest.mark.django_db
    def test_get_same_fund_peers_success(self):
        """같은 펀드 보유 종목 조회 성공"""
        # AAPL -> MSFT 관계
        StockRelationship.objects.create(
            source_symbol='AAPL',
            target_symbol='MSFT',
            relationship_type='HELD_BY_SAME_FUND',
            strength=Decimal('0.85'),
            source_provider='sec_13f',
            context={
                'shared_institutions': ['Berkshire Hathaway', 'BlackRock', 'Vanguard Group'],
                'shared_count': 3,
                'total_institutions': 4,
                'report_date': '2025-09-30'
            }
        )

        # AAPL -> NVDA 관계
        StockRelationship.objects.create(
            source_symbol='AAPL',
            target_symbol='NVDA',
            relationship_type='HELD_BY_SAME_FUND',
            strength=Decimal('0.60'),
            source_provider='sec_13f',
            context={
                'shared_institutions': ['BlackRock', 'Vanguard Group'],
                'shared_count': 2,
                'total_institutions': 5,
                'report_date': '2025-09-30'
            }
        )

        service = InstitutionalHoldingsService()
        peers = service.get_same_fund_peers('AAPL', limit=10)

        assert len(peers) == 2

        # strength 기준 정렬 (MSFT > NVDA)
        assert peers[0]['symbol'] == 'MSFT'
        assert peers[0]['strength'] == 0.85
        assert peers[0]['shared_count'] == 3
        assert peers[0]['total_institutions'] == 4
        assert len(peers[0]['shared_institutions']) == 3
        assert peers[0]['report_date'] == '2025-09-30'

        assert peers[1]['symbol'] == 'NVDA'
        assert peers[1]['strength'] == 0.60

    @pytest.mark.django_db
    def test_get_same_fund_peers_limit(self):
        """limit 파라미터 검증"""
        # 5개 관계 생성
        for i in range(5):
            StockRelationship.objects.create(
                source_symbol='AAPL',
                target_symbol=f'TEST{i}',
                relationship_type='HELD_BY_SAME_FUND',
                strength=Decimal(str(0.5 + i * 0.1)),
                source_provider='sec_13f',
                context={'shared_count': i + 1}
            )

        service = InstitutionalHoldingsService()
        peers = service.get_same_fund_peers('AAPL', limit=3)

        # 상위 3개만 반환
        assert len(peers) == 3

    @pytest.mark.django_db
    def test_get_same_fund_peers_symbol_upper(self):
        """symbol.upper() 규칙 검증"""
        StockRelationship.objects.create(
            source_symbol='AAPL',
            target_symbol='MSFT',
            relationship_type='HELD_BY_SAME_FUND',
            strength=Decimal('0.85'),
            source_provider='sec_13f',
            context={'shared_count': 3}
        )

        service = InstitutionalHoldingsService()

        # 소문자로 조회해도 동작
        peers = service.get_same_fund_peers('aapl', limit=10)
        assert len(peers) == 1

    @pytest.mark.django_db
    def test_get_same_fund_peers_no_relationships(self):
        """관계 없는 경우"""
        service = InstitutionalHoldingsService()
        peers = service.get_same_fund_peers('UNKNOWN', limit=10)

        assert peers == []


# ========================================
# 통합 시나리오 테스트
# ========================================

class TestIntegrationScenarios:
    """통합 시나리오 테스트"""

    @pytest.mark.django_db
    def test_full_workflow(self):
        """전체 워크플로우: 동기화 -> 관계 생성 -> 조회"""
        # 1. 동기화 Mock 설정
        report_date = date(2025, 9, 30)
        filing = MockFiling13F(
            accession_number='0001067983-25-000001',
            filing_date=date(2025, 11, 14),
            report_date=report_date,
            info_table_document='primary_doc.xml',
            cik='0001067983',
            institution_name='Berkshire Hathaway'
        )

        holdings = [
            {'cusip': '037833100', 'shares': 915560000, 'value': 158000000},
            {'cusip': '594918104', 'shares': 7000000, 'value': 2800000},
        ]

        mock_sec = Mock()
        mock_sec.get_13f_filings.return_value = [filing]
        mock_sec.download_13f_holdings.return_value = holdings

        mock_cusip = Mock()
        mock_cusip.cusip_to_ticker.side_effect = lambda cusip: {
            '037833100': 'AAPL',
            '594918104': 'MSFT',
        }.get(cusip)

        # 2. 동기화 실행
        service = InstitutionalHoldingsService()
        service.sec_client = mock_sec
        service.cusip_mapper = mock_cusip

        sync_result = service.sync_institution('0001067983', 'Berkshire Hathaway')

        assert sync_result['holdings_count'] == 2

        # 3. 조회 테스트
        institution_holdings = service.get_institution_holdings('0001067983')
        assert len(institution_holdings) == 2

        aapl_holders = service.get_stock_institutional_holders('AAPL')
        assert len(aapl_holders) == 1
        assert aapl_holders[0]['institution_name'] == 'Berkshire Hathaway'

        # 4. 두 번째 기관 동기화 (관계 생성을 위해)
        filing2 = MockFiling13F(
            accession_number='0001364742-25-000001',
            filing_date=date(2025, 11, 15),
            report_date=report_date,
            info_table_document='primary_doc.xml',
            cik='0001364742',
            institution_name='BlackRock'
        )

        holdings2 = [
            {'cusip': '037833100', 'shares': 500000000, 'value': 85000000},
            {'cusip': '594918104', 'shares': 8000000, 'value': 3200000},
        ]

        mock_sec.get_13f_filings.return_value = [filing2]
        mock_sec.download_13f_holdings.return_value = holdings2

        service.sync_institution('0001364742', 'BlackRock')

        # 5. 관계 생성
        relationship_count = service.generate_held_by_same_fund(min_shared_institutions=2)
        assert relationship_count == 1  # AAPL <-> MSFT

        # 6. 관계 조회
        aapl_peers = service.get_same_fund_peers('AAPL')
        assert len(aapl_peers) == 1
        assert aapl_peers[0]['symbol'] == 'MSFT'
        assert aapl_peers[0]['shared_count'] == 2
