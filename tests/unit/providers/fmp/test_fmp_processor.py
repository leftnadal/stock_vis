"""
FMP Processor Unit Tests

FMP API 응답 데이터를 Django 모델 호환 형식으로 변환하는 로직 테스트
"""

import pytest
from datetime import date
from decimal import Decimal


class TestFMPProcessorQuote:
    """실시간 주가 데이터 변환 테스트"""

    @pytest.fixture
    def processor(self):
        """
        FMP Processor 인스턴스
        TODO: 실제 구현 후 import 경로 수정
        """
        # from API_request.providers.fmp.processor import FMPProcessor
        # return FMPProcessor()
        pytest.skip("FMP Processor not implemented yet")

    def test_process_quote_valid_data(self, processor, sample_quote_data):
        """
        Given: 유효한 FMP Quote 응답
        When: process_quote() 호출
        Then: Django 모델 호환 형식으로 변환
        """
        # When
        result = processor.process_quote(sample_quote_data)

        # Then
        assert result['symbol'] == 'AAPL'
        assert result['real_time_price'] == Decimal('150.25')
        assert result['change'] == Decimal('2.50')
        assert result['change_percent'] == '1.69%'
        assert result['open_price'] == Decimal('149.50')
        assert result['high_price'] == Decimal('151.00')
        assert result['low_price'] == Decimal('148.00')
        assert result['volume'] == 50000000
        assert result['previous_close'] == Decimal('148.00')

    def test_process_quote_missing_fields(self, processor):
        """
        Given: 일부 필드 누락된 응답
        When: process_quote() 호출
        Then: 안전하게 기본값으로 처리
        """
        # Given
        incomplete_data = [{
            "symbol": "AAPL",
            "price": 150.25
            # 다른 필드 누락
        }]

        # When
        result = processor.process_quote(incomplete_data)

        # Then
        assert result['symbol'] == 'AAPL'
        assert result['real_time_price'] == Decimal('150.25')
        assert result['change'] == Decimal('0')  # 기본값
        assert result['volume'] == 0  # 기본값

    def test_process_quote_none_values(self, processor):
        """
        Given: None 값 포함 응답
        When: process_quote() 호출
        Then: None을 안전하게 기본값으로 변환
        """
        # Given
        data_with_none = [{
            "symbol": "AAPL",
            "price": None,
            "change": None,
            "volume": None
        }]

        # When
        result = processor.process_quote(data_with_none)

        # Then
        assert result['real_time_price'] == Decimal('0')
        assert result['change'] == Decimal('0')
        assert result['volume'] == 0

    def test_process_quote_invalid_decimal(self, processor):
        """
        Given: 숫자로 변환 불가능한 값
        When: process_quote() 호출
        Then: 기본값으로 처리 (에러 발생 안함)
        """
        # Given
        invalid_data = [{
            "symbol": "AAPL",
            "price": "not_a_number",
            "change": "invalid"
        }]

        # When
        result = processor.process_quote(invalid_data)

        # Then
        assert result['real_time_price'] == Decimal('0')
        assert result['change'] == Decimal('0')


class TestFMPProcessorCompanyProfile:
    """회사 정보 데이터 변환 테스트"""

    @pytest.fixture
    def processor(self):
        pytest.skip("FMP Processor not implemented yet")

    def test_process_profile_valid_data(self, processor, sample_profile_data):
        """
        Given: 유효한 FMP Company Profile 응답
        When: process_company_profile() 호출
        Then: Django Stock 모델 호환 형식으로 변환
        """
        # When
        result = processor.process_company_profile(sample_profile_data)

        # Then
        assert result['symbol'] == 'AAPL'
        assert result['stock_name'] == 'Apple Inc.'
        assert result['sector'] == 'Technology'
        assert result['industry'] == 'Consumer Electronics'
        assert result['exchange'] == 'NASDAQ'
        assert result['currency'] == 'USD'
        assert result['market_capitalization'] == Decimal('2500000000000')

    def test_process_profile_empty_description(self, processor):
        """
        Given: description 필드가 비어있는 응답
        When: process_company_profile() 호출
        Then: 빈 문자열로 처리
        """
        # Given
        data = [{
            "symbol": "AAPL",
            "companyName": "Apple Inc.",
            "description": ""
        }]

        # When
        result = processor.process_company_profile(data)

        # Then
        assert result['description'] == ''


class TestFMPProcessorBalanceSheet:
    """대차대조표 데이터 변환 테스트"""

    @pytest.fixture
    def processor(self):
        pytest.skip("FMP Processor not implemented yet")

    def test_process_balance_sheet_quarterly(self, processor, sample_balance_sheet_data):
        """
        Given: FMP Balance Sheet 응답 (분기별)
        When: process_balance_sheet() 호출
        Then: Django BalanceSheet 모델 호환 형식으로 변환
        """
        # When
        result = processor.process_balance_sheet(sample_balance_sheet_data)

        # Then
        assert len(result) == 1
        balance = result[0]

        assert balance['reported_date'] == date(2024, 9, 30)
        assert balance['period_type'] == 'quarterly'
        assert balance['fiscal_year'] == 2024
        assert balance['fiscal_quarter'] == 'Q4'
        assert balance['total_assets'] == Decimal('364980000000')
        assert balance['total_liabilities'] == Decimal('279414000000')
        assert balance['total_equity'] == Decimal('85566000000')

    def test_process_balance_sheet_annual(self, processor):
        """
        Given: 연간 Balance Sheet 응답
        When: process_balance_sheet() 호출
        Then: period_type='annual', fiscal_quarter=None
        """
        # Given
        annual_data = [{
            "date": "2024-09-30",
            "symbol": "AAPL",
            "period": "FY",  # Full Year
            "calendarYear": "2024",
            "totalAssets": 364980000000
        }]

        # When
        result = processor.process_balance_sheet(annual_data)

        # Then
        assert result[0]['period_type'] == 'annual'
        assert result[0]['fiscal_quarter'] is None

    def test_process_balance_sheet_multiple_periods(self, processor):
        """
        Given: 여러 기간의 Balance Sheet 데이터
        When: process_balance_sheet() 호출
        Then: 모든 기간 데이터 변환
        """
        # Given
        multi_period_data = [
            {"date": "2024-09-30", "symbol": "AAPL", "period": "Q4", "calendarYear": "2024"},
            {"date": "2024-06-30", "symbol": "AAPL", "period": "Q3", "calendarYear": "2024"},
            {"date": "2024-03-31", "symbol": "AAPL", "period": "Q2", "calendarYear": "2024"},
        ]

        # When
        result = processor.process_balance_sheet(multi_period_data)

        # Then
        assert len(result) == 3
        assert result[0]['fiscal_quarter'] == 'Q4'
        assert result[1]['fiscal_quarter'] == 'Q3'
        assert result[2]['fiscal_quarter'] == 'Q2'


class TestFMPProcessorHelperMethods:
    """헬퍼 메서드 테스트 (_safe_decimal, _safe_int 등)"""

    @pytest.fixture
    def processor(self):
        pytest.skip("FMP Processor not implemented yet")

    def test_safe_decimal_valid_number(self, processor):
        """
        Given: 유효한 숫자 문자열
        When: _safe_decimal() 호출
        Then: Decimal로 변환
        """
        # When
        result = processor._safe_decimal("150.25")

        # Then
        assert result == Decimal('150.25')

    def test_safe_decimal_none_value(self, processor):
        """
        Given: None 값
        When: _safe_decimal() 호출
        Then: Decimal('0') 반환
        """
        # When
        result = processor._safe_decimal(None)

        # Then
        assert result == Decimal('0')

    def test_safe_decimal_empty_string(self, processor):
        """
        Given: 빈 문자열
        When: _safe_decimal() 호출
        Then: Decimal('0') 반환
        """
        # When
        result = processor._safe_decimal("")

        # Then
        assert result == Decimal('0')

    def test_safe_decimal_invalid_string(self, processor):
        """
        Given: 숫자로 변환 불가능한 문자열
        When: _safe_decimal() 호출
        Then: Decimal('0') 반환 (에러 발생 안함)
        """
        # When
        result = processor._safe_decimal("not_a_number")

        # Then
        assert result == Decimal('0')

    def test_safe_int_valid_number(self, processor):
        """
        Given: 유효한 정수 문자열
        When: _safe_int() 호출
        Then: int로 변환
        """
        # When
        result = processor._safe_int("50000000")

        # Then
        assert result == 50000000

    def test_safe_int_none_value(self, processor):
        """
        Given: None 값
        When: _safe_int() 호출
        Then: 0 반환
        """
        # When
        result = processor._safe_int(None)

        # Then
        assert result == 0

    def test_safe_date_valid_iso_format(self, processor):
        """
        Given: ISO 형식 날짜 문자열
        When: _safe_date() 호출
        Then: date 객체로 변환
        """
        # When
        result = processor._safe_date("2024-09-30")

        # Then
        assert result == date(2024, 9, 30)

    def test_safe_date_none_value(self, processor):
        """
        Given: None 값
        When: _safe_date() 호출
        Then: None 반환
        """
        # When
        result = processor._safe_date(None)

        # Then
        assert result is None

    def test_safe_date_invalid_format(self, processor):
        """
        Given: 잘못된 날짜 형식
        When: _safe_date() 호출
        Then: None 반환 (에러 발생 안함)
        """
        # When
        result = processor._safe_date("invalid_date")

        # Then
        assert result is None


# ===== 마커 설정 =====
pytestmark = pytest.mark.unit
