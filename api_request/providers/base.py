# api_request/providers/base.py
"""
Stock Data Provider 추상화 레이어

모든 데이터 제공자(Alpha Vantage, FMP 등)가 구현해야 할 공통 인터페이스를 정의합니다.
이를 통해 provider를 쉽게 교체하거나 fallback 메커니즘을 구현할 수 있습니다.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, date
from decimal import Decimal
from enum import Enum
from typing import Dict, Any, Optional, List, Union, TypeVar, Generic
import logging

logger = logging.getLogger(__name__)


class ProviderError(Exception):
    """Provider 관련 기본 예외"""
    pass


class RateLimitError(ProviderError):
    """API Rate Limit 초과 예외"""
    def __init__(self, provider: str, retry_after: Optional[int] = None):
        self.provider = provider
        self.retry_after = retry_after
        message = f"{provider} rate limit exceeded"
        if retry_after:
            message += f". Retry after {retry_after} seconds"
        super().__init__(message)


class DataNotFoundError(ProviderError):
    """데이터를 찾을 수 없는 경우 예외"""
    def __init__(self, symbol: str, data_type: str):
        self.symbol = symbol
        self.data_type = data_type
        super().__init__(f"{data_type} not found for symbol: {symbol}")


class ProviderUnavailableError(ProviderError):
    """Provider 서비스 불가 예외"""
    def __init__(self, provider: str, reason: str = ""):
        self.provider = provider
        self.reason = reason
        message = f"{provider} is currently unavailable"
        if reason:
            message += f": {reason}"
        super().__init__(message)


class PeriodType(Enum):
    """재무제표 기간 타입"""
    ANNUAL = "annual"
    QUARTERLY = "quarterly"


class OutputSize(Enum):
    """가격 데이터 출력 크기"""
    COMPACT = "compact"  # 최근 100개
    FULL = "full"  # 전체 데이터


@dataclass
class ProviderResponse(Generic[TypeVar('T')]):
    """
    Provider 응답 래퍼

    모든 provider 메서드는 이 형식으로 응답을 반환합니다.
    성공/실패 여부, 데이터, 메타정보를 포함합니다.
    """
    success: bool
    data: Optional[Any] = None
    error: Optional[str] = None
    error_code: Optional[str] = None
    provider: str = ""
    cached: bool = False
    timestamp: datetime = field(default_factory=datetime.now)
    meta: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def success_response(cls, data: Any, provider: str, cached: bool = False,
                         meta: Optional[Dict[str, Any]] = None) -> 'ProviderResponse':
        """성공 응답 생성"""
        return cls(
            success=True,
            data=data,
            provider=provider,
            cached=cached,
            meta=meta or {}
        )

    @classmethod
    def error_response(cls, error: str, provider: str,
                       error_code: Optional[str] = None) -> 'ProviderResponse':
        """에러 응답 생성"""
        return cls(
            success=False,
            error=error,
            error_code=error_code,
            provider=provider
        )


# ============================================================
# 정규화된 데이터 모델
# Provider별로 다른 필드명을 통일된 형식으로 변환
# ============================================================

@dataclass
class NormalizedQuote:
    """정규화된 실시간 시세 데이터"""
    symbol: str
    price: Decimal
    open: Optional[Decimal] = None
    high: Optional[Decimal] = None
    low: Optional[Decimal] = None
    volume: Optional[int] = None
    previous_close: Optional[Decimal] = None
    change: Optional[Decimal] = None
    change_percent: Optional[Decimal] = None
    latest_trading_day: Optional[date] = None
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class NormalizedCompanyProfile:
    """정규화된 회사 프로필 데이터"""
    symbol: str
    name: str
    description: Optional[str] = None
    exchange: Optional[str] = None
    currency: Optional[str] = None
    country: Optional[str] = None
    sector: Optional[str] = None
    industry: Optional[str] = None
    market_cap: Optional[Decimal] = None
    pe_ratio: Optional[Decimal] = None
    beta: Optional[Decimal] = None
    dividend_yield: Optional[Decimal] = None
    eps: Optional[Decimal] = None
    high_52week: Optional[Decimal] = None
    low_52week: Optional[Decimal] = None
    moving_avg_50: Optional[Decimal] = None
    moving_avg_200: Optional[Decimal] = None
    shares_outstanding: Optional[int] = None
    website: Optional[str] = None
    ceo: Optional[str] = None
    full_time_employees: Optional[int] = None
    ipo_date: Optional[date] = None


@dataclass
class NormalizedPriceData:
    """정규화된 가격 데이터 (일별/주별)"""
    date: date
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: int
    adjusted_close: Optional[Decimal] = None
    dividend_amount: Optional[Decimal] = None
    split_coefficient: Optional[Decimal] = None


@dataclass
class NormalizedFinancialStatement:
    """정규화된 재무제표 기본 구조"""
    symbol: str
    fiscal_date_ending: date
    reported_currency: str
    period_type: PeriodType
    fiscal_year: Optional[int] = None
    fiscal_quarter: Optional[int] = None


@dataclass
class NormalizedBalanceSheet(NormalizedFinancialStatement):
    """정규화된 대차대조표"""
    # 자산
    total_assets: Optional[Decimal] = None
    current_assets: Optional[Decimal] = None
    cash_and_equivalents: Optional[Decimal] = None
    short_term_investments: Optional[Decimal] = None
    inventory: Optional[Decimal] = None
    accounts_receivable: Optional[Decimal] = None
    non_current_assets: Optional[Decimal] = None
    property_plant_equipment: Optional[Decimal] = None
    goodwill: Optional[Decimal] = None
    intangible_assets: Optional[Decimal] = None

    # 부채
    total_liabilities: Optional[Decimal] = None
    current_liabilities: Optional[Decimal] = None
    accounts_payable: Optional[Decimal] = None
    short_term_debt: Optional[Decimal] = None
    long_term_debt: Optional[Decimal] = None

    # 자본
    total_shareholder_equity: Optional[Decimal] = None
    retained_earnings: Optional[Decimal] = None
    common_stock: Optional[Decimal] = None
    treasury_stock: Optional[Decimal] = None


@dataclass
class NormalizedIncomeStatement(NormalizedFinancialStatement):
    """정규화된 손익계산서"""
    total_revenue: Optional[Decimal] = None
    cost_of_revenue: Optional[Decimal] = None
    gross_profit: Optional[Decimal] = None
    operating_expenses: Optional[Decimal] = None
    operating_income: Optional[Decimal] = None
    interest_expense: Optional[Decimal] = None
    income_before_tax: Optional[Decimal] = None
    income_tax_expense: Optional[Decimal] = None
    net_income: Optional[Decimal] = None
    ebitda: Optional[Decimal] = None
    eps: Optional[Decimal] = None
    eps_diluted: Optional[Decimal] = None
    weighted_avg_shares: Optional[int] = None
    weighted_avg_shares_diluted: Optional[int] = None


@dataclass
class NormalizedCashFlow(NormalizedFinancialStatement):
    """정규화된 현금흐름표"""
    # 영업활동
    operating_cash_flow: Optional[Decimal] = None
    net_income: Optional[Decimal] = None
    depreciation: Optional[Decimal] = None
    changes_in_receivables: Optional[Decimal] = None
    changes_in_inventory: Optional[Decimal] = None

    # 투자활동
    investing_cash_flow: Optional[Decimal] = None
    capital_expenditures: Optional[Decimal] = None
    investments: Optional[Decimal] = None

    # 재무활동
    financing_cash_flow: Optional[Decimal] = None
    dividends_paid: Optional[Decimal] = None
    stock_repurchased: Optional[Decimal] = None
    debt_repayment: Optional[Decimal] = None

    # 순 현금 변동
    net_change_in_cash: Optional[Decimal] = None
    free_cash_flow: Optional[Decimal] = None


@dataclass
class NormalizedSearchResult:
    """정규화된 종목 검색 결과"""
    symbol: str
    name: str
    type: Optional[str] = None  # Equity, ETF, etc.
    exchange: Optional[str] = None
    currency: Optional[str] = None
    match_score: Optional[float] = None


# ============================================================
# Abstract Base Class
# ============================================================

class StockDataProvider(ABC):
    """
    주식 데이터 제공자 추상 기본 클래스

    모든 데이터 제공자(Alpha Vantage, FMP 등)는 이 클래스를 상속받아
    필요한 메서드를 구현해야 합니다.

    주요 설계 원칙:
    1. 모든 메서드는 ProviderResponse를 반환
    2. 내부 에러는 catch하여 error_response로 변환
    3. 정규화된 데이터 모델 사용으로 provider 간 호환성 보장
    """

    # Provider 식별자 (서브클래스에서 오버라이드)
    PROVIDER_NAME: str = "base"

    # Rate Limiting 설정
    RATE_LIMIT_CALLS: int = 5  # 분당 호출 수
    RATE_LIMIT_DAILY: int = 500  # 일일 호출 수
    REQUEST_DELAY: float = 12.0  # 요청 간 대기 시간(초)

    def __init__(self, api_key: str):
        """
        Args:
            api_key: API 인증 키
        """
        self.api_key = api_key
        self._validate_api_key()

    def _validate_api_key(self) -> None:
        """API 키 유효성 검사"""
        if not self.api_key:
            raise ValueError(f"{self.PROVIDER_NAME} API key is required")

    # ============================================================
    # 필수 구현 메서드 (Abstract Methods)
    # ============================================================

    @abstractmethod
    def get_quote(self, symbol: str) -> ProviderResponse[NormalizedQuote]:
        """
        실시간 시세 조회

        Args:
            symbol: 주식 심볼 (예: "AAPL")

        Returns:
            ProviderResponse[NormalizedQuote]: 정규화된 시세 데이터
        """
        pass

    @abstractmethod
    def get_company_profile(self, symbol: str) -> ProviderResponse[NormalizedCompanyProfile]:
        """
        회사 프로필 조회

        Args:
            symbol: 주식 심볼

        Returns:
            ProviderResponse[NormalizedCompanyProfile]: 정규화된 회사 정보
        """
        pass

    @abstractmethod
    def get_daily_prices(
        self,
        symbol: str,
        output_size: OutputSize = OutputSize.COMPACT
    ) -> ProviderResponse[List[NormalizedPriceData]]:
        """
        일별 가격 데이터 조회

        Args:
            symbol: 주식 심볼
            output_size: 데이터 크기 (COMPACT: 100개, FULL: 전체)

        Returns:
            ProviderResponse[List[NormalizedPriceData]]: 일별 가격 리스트
        """
        pass

    @abstractmethod
    def get_weekly_prices(
        self,
        symbol: str
    ) -> ProviderResponse[List[NormalizedPriceData]]:
        """
        주별 가격 데이터 조회

        Args:
            symbol: 주식 심볼

        Returns:
            ProviderResponse[List[NormalizedPriceData]]: 주별 가격 리스트
        """
        pass

    @abstractmethod
    def get_balance_sheet(
        self,
        symbol: str,
        period: PeriodType = PeriodType.ANNUAL
    ) -> ProviderResponse[List[NormalizedBalanceSheet]]:
        """
        대차대조표 조회

        Args:
            symbol: 주식 심볼
            period: 기간 타입 (ANNUAL/QUARTERLY)

        Returns:
            ProviderResponse[List[NormalizedBalanceSheet]]: 대차대조표 리스트
        """
        pass

    @abstractmethod
    def get_income_statement(
        self,
        symbol: str,
        period: PeriodType = PeriodType.ANNUAL
    ) -> ProviderResponse[List[NormalizedIncomeStatement]]:
        """
        손익계산서 조회

        Args:
            symbol: 주식 심볼
            period: 기간 타입 (ANNUAL/QUARTERLY)

        Returns:
            ProviderResponse[List[NormalizedIncomeStatement]]: 손익계산서 리스트
        """
        pass

    @abstractmethod
    def get_cash_flow(
        self,
        symbol: str,
        period: PeriodType = PeriodType.ANNUAL
    ) -> ProviderResponse[List[NormalizedCashFlow]]:
        """
        현금흐름표 조회

        Args:
            symbol: 주식 심볼
            period: 기간 타입 (ANNUAL/QUARTERLY)

        Returns:
            ProviderResponse[List[NormalizedCashFlow]]: 현금흐름표 리스트
        """
        pass

    @abstractmethod
    def search_symbols(
        self,
        keywords: str
    ) -> ProviderResponse[List[NormalizedSearchResult]]:
        """
        종목 검색

        Args:
            keywords: 검색 키워드

        Returns:
            ProviderResponse[List[NormalizedSearchResult]]: 검색 결과 리스트
        """
        pass

    # ============================================================
    # 선택적 구현 메서드 (기본 구현 제공)
    # ============================================================

    def get_sector_performance(self) -> ProviderResponse[Dict[str, Any]]:
        """
        섹터 성과 조회 (선택적 구현)

        Returns:
            ProviderResponse[Dict[str, Any]]: 섹터별 성과 데이터
        """
        return ProviderResponse.error_response(
            error="Sector performance not supported by this provider",
            provider=self.PROVIDER_NAME,
            error_code="NOT_SUPPORTED"
        )

    def get_technical_indicators(
        self,
        symbol: str,
        indicator: str,
        **kwargs
    ) -> ProviderResponse[Dict[str, Any]]:
        """
        기술적 지표 조회 (선택적 구현)

        Args:
            symbol: 주식 심볼
            indicator: 지표 타입 (RSI, MACD, etc.)
            **kwargs: 추가 파라미터

        Returns:
            ProviderResponse[Dict[str, Any]]: 기술적 지표 데이터
        """
        return ProviderResponse.error_response(
            error=f"Technical indicator {indicator} not supported by this provider",
            provider=self.PROVIDER_NAME,
            error_code="NOT_SUPPORTED"
        )

    # ============================================================
    # 유틸리티 메서드
    # ============================================================

    def is_available(self) -> bool:
        """
        Provider 서비스 가용성 체크

        Returns:
            bool: 서비스 사용 가능 여부
        """
        return True

    def get_rate_limit_status(self) -> Dict[str, Any]:
        """
        현재 Rate Limit 상태 조회

        Returns:
            Dict[str, Any]: Rate limit 상태 정보
        """
        return {
            "provider": self.PROVIDER_NAME,
            "calls_per_minute": self.RATE_LIMIT_CALLS,
            "daily_limit": self.RATE_LIMIT_DAILY,
            "request_delay": self.REQUEST_DELAY
        }

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}(provider={self.PROVIDER_NAME})>"
