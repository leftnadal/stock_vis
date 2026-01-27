"""
Data Validator

Provider 응답 데이터의 필수 필드, 데이터 타입, 값 범위를 검증하는 유틸리티
"""

from typing import Dict, Any, List
from decimal import Decimal
from datetime import date


class DataValidator:
    """Provider 응답 데이터 검증"""

    # 필수 필드 정의
    REQUIRED_FIELDS = {
        'quote': [
            'symbol', 'real_time_price', 'change', 'change_percent',
            'open_price', 'high_price', 'low_price', 'volume', 'previous_close'
        ],
        'company_profile': [
            'symbol', 'stock_name', 'sector', 'industry',
            'exchange', 'currency', 'market_capitalization'
        ],
        'daily_price': [
            'date', 'open_price', 'high_price', 'low_price',
            'close_price', 'volume'
        ],
        'weekly_price': [
            'date', 'week_start_date', 'week_end_date',
            'open_price', 'high_price', 'low_price',
            'close_price', 'volume'
        ],
        'balance_sheet': [
            'reported_date', 'period_type', 'fiscal_year', 'fiscal_quarter',
            'total_assets', 'total_liabilities', 'total_equity'
        ],
        'income_statement': [
            'reported_date', 'period_type', 'fiscal_year', 'fiscal_quarter',
            'total_revenue', 'net_income', 'gross_profit'
        ],
        'cash_flow': [
            'reported_date', 'period_type', 'fiscal_year', 'fiscal_quarter',
            'operating_cashflow', 'capital_expenditure', 'free_cash_flow'
        ]
    }

    @classmethod
    def validate_required_fields(cls, data: Dict[str, Any], data_type: str) -> List[str]:
        """
        필수 필드 누락 검증

        Args:
            data: 검증할 데이터
            data_type: 데이터 타입 ('quote', 'company_profile', 'balance_sheet' 등)

        Returns:
            List[str]: 누락된 필드명 리스트 (빈 리스트 = 모두 존재)
        """
        required = cls.REQUIRED_FIELDS.get(data_type, [])
        missing = []

        for field in required:
            if field not in data or data[field] is None:
                missing.append(field)

        return missing

    @classmethod
    def validate_data_types(cls, data: Dict[str, Any]) -> Dict[str, str]:
        """
        데이터 타입 검증

        Args:
            data: 검증할 데이터

        Returns:
            Dict[str, str]: {필드명: 에러 메시지} (빈 딕셔너리 = 모두 정상)
        """
        errors = {}

        # Decimal 필드 검증
        decimal_fields = [
            'real_time_price', 'change', 'open_price', 'high_price', 'low_price',
            'close_price', 'market_capitalization', 'total_assets', 'total_liabilities',
            'total_equity', 'total_revenue', 'net_income', 'gross_profit',
            'operating_cashflow', 'capital_expenditure', 'free_cash_flow',
            'pe_ratio', 'eps', 'book_value', 'dividend_per_share'
        ]

        for field in decimal_fields:
            if field in data and data[field] is not None:
                value = data[field]
                if not isinstance(value, (Decimal, int, float)):
                    errors[field] = f"Expected Decimal/numeric, got {type(value).__name__}"

        # Integer 필드 검증
        integer_fields = ['volume', 'fiscal_year', 'shares_outstanding']

        for field in integer_fields:
            if field in data and data[field] is not None:
                value = data[field]
                if not isinstance(value, int):
                    # 문자열에서 변환 가능한지 확인
                    try:
                        int(value)
                    except (ValueError, TypeError):
                        errors[field] = f"Expected int, got {type(value).__name__}"

        # Date 필드 검증
        date_fields = ['date', 'reported_date', 'latest_quarter', 'week_start_date', 'week_end_date']

        for field in date_fields:
            if field in data and data[field] is not None:
                value = data[field]
                if not isinstance(value, date):
                    errors[field] = f"Expected date, got {type(value).__name__}"

        return errors

    @classmethod
    def validate_value_ranges(cls, data: Dict[str, Any]) -> Dict[str, str]:
        """
        값 범위 검증

        Args:
            data: 검증할 데이터

        Returns:
            Dict[str, str]: {필드명: 에러 메시지} (빈 딕셔너리 = 모두 정상)
        """
        errors = {}

        # 양수 필드 검증
        positive_fields = [
            'real_time_price', 'open_price', 'high_price', 'low_price', 'close_price',
            'volume', 'market_capitalization', 'total_assets', 'shares_outstanding'
        ]

        for field in positive_fields:
            if field in data and data[field] is not None:
                value = data[field]
                if isinstance(value, (Decimal, int, float)) and value < 0:
                    errors[field] = f"Expected positive value, got {value}"

        # 퍼센트 필드 검증 (-100% ~ +1000%)
        percent_fields = [
            'change_percent', 'profit_margin', 'operating_margin_ttm',
            'return_on_assets_ttm', 'return_on_equity_ttm',
            'quarterly_earnings_growth_yoy', 'quarterly_revenue_growth_yoy'
        ]

        for field in percent_fields:
            if field in data and data[field] is not None:
                value = data[field]

                # 문자열 형식 처리 (예: "1.69%")
                if isinstance(value, str):
                    value_str = value.replace('%', '').strip()
                    try:
                        numeric_value = float(value_str)
                        # 일부 성장률은 100% 초과 가능 (최대 1000%)
                        if not -100 <= numeric_value <= 1000:
                            errors[field] = f"Percentage out of range: {value}"
                    except ValueError:
                        errors[field] = f"Invalid percentage format: {value}"

        # Period Type 검증
        if 'period_type' in data and data['period_type'] is not None:
            valid_periods = ['annual', 'quarterly', 'quarter']  # 'quarter'는 Alpha Vantage 호환
            if data['period_type'] not in valid_periods:
                errors['period_type'] = f"Invalid period_type: {data['period_type']}"

        # Fiscal Quarter 검증
        if 'fiscal_quarter' in data and data['fiscal_quarter'] is not None:
            valid_quarters = ['Q1', 'Q2', 'Q3', 'Q4']
            if data['fiscal_quarter'] not in valid_quarters:
                errors['fiscal_quarter'] = f"Invalid fiscal_quarter: {data['fiscal_quarter']}"

        return errors

    @classmethod
    def validate_all(cls, data: Dict[str, Any], data_type: str) -> Dict[str, Any]:
        """
        모든 검증 수행

        Args:
            data: 검증할 데이터
            data_type: 데이터 타입

        Returns:
            Dict[str, Any]: {
                'is_valid': bool,
                'missing_fields': List[str],
                'type_errors': Dict[str, str],
                'range_errors': Dict[str, str]
            }
        """
        missing_fields = cls.validate_required_fields(data, data_type)
        type_errors = cls.validate_data_types(data)
        range_errors = cls.validate_value_ranges(data)

        is_valid = not (missing_fields or type_errors or range_errors)

        return {
            'is_valid': is_valid,
            'missing_fields': missing_fields,
            'type_errors': type_errors,
            'range_errors': range_errors
        }
