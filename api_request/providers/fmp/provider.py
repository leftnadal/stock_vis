# api_request/providers/fmp/provider.py
"""
FMP (Financial Modeling Prep) Provider

FMP API를 사용하여 StockDataProvider 인터페이스를 구현합니다.

주요 장점:
- 재무제표 데이터 품질이 우수
- 회사 프로필 상세 정보
- 낮은 Rate Limit (250/day) 지만 배치 API 지원
"""

import logging
import os
from typing import List, Dict, Any

from ..base import (
    StockDataProvider,
    ProviderResponse,
    RateLimitError,
    PeriodType,
    OutputSize,
    NormalizedQuote,
    NormalizedCompanyProfile,
    NormalizedPriceData,
    NormalizedBalanceSheet,
    NormalizedIncomeStatement,
    NormalizedCashFlow,
    NormalizedSearchResult,
)
from .client import FMPClient, FMPRateLimitError, FMPClientError
from .processor import FMPProcessor

logger = logging.getLogger(__name__)


class FMPProvider(StockDataProvider):
    """
    FMP API Provider

    Financial Modeling Prep API를 활용한 주식 데이터 제공자
    """

    PROVIDER_NAME = "fmp"
    RATE_LIMIT_CALLS = 10  # 분당 (무료 티어 기준)
    RATE_LIMIT_DAILY = 250  # 일일 250회
    REQUEST_DELAY = 0.5  # Alpha Vantage보다 관대

    def __init__(self, api_key: str = None):
        """
        Args:
            api_key: FMP API 키 (없으면 환경변수에서 로드)
        """
        api_key = api_key or os.getenv("FMP_API_KEY", "")
        super().__init__(api_key)
        self._client = FMPClient(api_key=api_key)
        self._processor = FMPProcessor()

    def get_quote(self, symbol: str) -> ProviderResponse[NormalizedQuote]:
        """실시간 시세 조회"""
        try:
            symbol = symbol.upper()
            raw_data = self._client.get_quote(symbol)

            if not raw_data:
                return ProviderResponse.error_response(
                    error=f"No quote data found for {symbol}",
                    provider=self.PROVIDER_NAME,
                    error_code="DATA_NOT_FOUND"
                )

            normalized = self._processor.process_quote(symbol, raw_data)

            if not normalized:
                return ProviderResponse.error_response(
                    error=f"Failed to process quote data for {symbol}",
                    provider=self.PROVIDER_NAME,
                    error_code="PROCESSING_ERROR"
                )

            return ProviderResponse.success_response(
                data=normalized,
                provider=self.PROVIDER_NAME
            )

        except FMPRateLimitError:
            raise RateLimitError(self.PROVIDER_NAME)
        except Exception as e:
            logger.error(f"FMP get_quote error for {symbol}: {e}")
            return ProviderResponse.error_response(
                error=str(e),
                provider=self.PROVIDER_NAME,
                error_code="API_ERROR"
            )

    def get_company_profile(self, symbol: str) -> ProviderResponse[NormalizedCompanyProfile]:
        """회사 프로필 조회"""
        try:
            symbol = symbol.upper()
            raw_data = self._client.get_company_profile(symbol)

            if not raw_data:
                return ProviderResponse.error_response(
                    error=f"No company profile found for {symbol}",
                    provider=self.PROVIDER_NAME,
                    error_code="DATA_NOT_FOUND"
                )

            normalized = self._processor.process_company_profile(raw_data)

            if not normalized:
                return ProviderResponse.error_response(
                    error=f"Failed to process company profile for {symbol}",
                    provider=self.PROVIDER_NAME,
                    error_code="PROCESSING_ERROR"
                )

            return ProviderResponse.success_response(
                data=normalized,
                provider=self.PROVIDER_NAME
            )

        except FMPRateLimitError:
            raise RateLimitError(self.PROVIDER_NAME)
        except Exception as e:
            logger.error(f"FMP get_company_profile error for {symbol}: {e}")
            return ProviderResponse.error_response(
                error=str(e),
                provider=self.PROVIDER_NAME,
                error_code="API_ERROR"
            )

    def get_daily_prices(
        self,
        symbol: str,
        output_size: OutputSize = OutputSize.COMPACT
    ) -> ProviderResponse[List[NormalizedPriceData]]:
        """일별 가격 데이터 조회"""
        try:
            symbol = symbol.upper()

            # FMP는 from/to 날짜로 조회
            # COMPACT: 최근 100일, FULL: 전체
            from_date = None
            if output_size == OutputSize.COMPACT:
                from datetime import datetime, timedelta
                from_date = (datetime.now() - timedelta(days=150)).strftime("%Y-%m-%d")

            raw_data = self._client.get_historical_price(
                symbol,
                from_date=from_date
            )

            if not raw_data:
                return ProviderResponse.error_response(
                    error=f"No daily price data found for {symbol}",
                    provider=self.PROVIDER_NAME,
                    error_code="DATA_NOT_FOUND"
                )

            prices = self._processor.process_historical_prices(symbol, raw_data)

            return ProviderResponse.success_response(
                data=prices,
                provider=self.PROVIDER_NAME,
                meta={"count": len(prices)}
            )

        except FMPRateLimitError:
            raise RateLimitError(self.PROVIDER_NAME)
        except Exception as e:
            logger.error(f"FMP get_daily_prices error for {symbol}: {e}")
            return ProviderResponse.error_response(
                error=str(e),
                provider=self.PROVIDER_NAME,
                error_code="API_ERROR"
            )

    def get_weekly_prices(self, symbol: str) -> ProviderResponse[List[NormalizedPriceData]]:
        """
        주별 가격 데이터 조회

        참고: FMP는 별도 weekly endpoint가 없어 daily 데이터를 주 단위로 집계
        """
        try:
            symbol = symbol.upper()

            # 일별 데이터 조회 후 주별로 집계
            raw_data = self._client.get_historical_price(symbol)

            if not raw_data:
                return ProviderResponse.error_response(
                    error=f"No price data found for {symbol}",
                    provider=self.PROVIDER_NAME,
                    error_code="DATA_NOT_FOUND"
                )

            # 일별 데이터를 주별로 집계
            daily_prices = self._processor.process_historical_prices(symbol, raw_data)
            weekly_prices = self._aggregate_to_weekly(daily_prices)

            return ProviderResponse.success_response(
                data=weekly_prices,
                provider=self.PROVIDER_NAME,
                meta={"count": len(weekly_prices)}
            )

        except FMPRateLimitError:
            raise RateLimitError(self.PROVIDER_NAME)
        except Exception as e:
            logger.error(f"FMP get_weekly_prices error for {symbol}: {e}")
            return ProviderResponse.error_response(
                error=str(e),
                provider=self.PROVIDER_NAME,
                error_code="API_ERROR"
            )

    def get_balance_sheet(
        self,
        symbol: str,
        period: PeriodType = PeriodType.ANNUAL
    ) -> ProviderResponse[List[NormalizedBalanceSheet]]:
        """대차대조표 조회"""
        try:
            symbol = symbol.upper()
            period_str = "annual" if period == PeriodType.ANNUAL else "quarter"

            raw_data = self._client.get_balance_sheet(symbol, period=period_str)

            if not raw_data:
                return ProviderResponse.error_response(
                    error=f"No balance sheet data found for {symbol}",
                    provider=self.PROVIDER_NAME,
                    error_code="DATA_NOT_FOUND"
                )

            balance_sheets = self._processor.process_balance_sheet(
                symbol, raw_data, period
            )

            return ProviderResponse.success_response(
                data=balance_sheets,
                provider=self.PROVIDER_NAME,
                meta={"count": len(balance_sheets), "period": period.value}
            )

        except FMPRateLimitError:
            raise RateLimitError(self.PROVIDER_NAME)
        except Exception as e:
            logger.error(f"FMP get_balance_sheet error for {symbol}: {e}")
            return ProviderResponse.error_response(
                error=str(e),
                provider=self.PROVIDER_NAME,
                error_code="API_ERROR"
            )

    def get_income_statement(
        self,
        symbol: str,
        period: PeriodType = PeriodType.ANNUAL
    ) -> ProviderResponse[List[NormalizedIncomeStatement]]:
        """손익계산서 조회"""
        try:
            symbol = symbol.upper()
            period_str = "annual" if period == PeriodType.ANNUAL else "quarter"

            raw_data = self._client.get_income_statement(symbol, period=period_str)

            if not raw_data:
                return ProviderResponse.error_response(
                    error=f"No income statement data found for {symbol}",
                    provider=self.PROVIDER_NAME,
                    error_code="DATA_NOT_FOUND"
                )

            statements = self._processor.process_income_statement(
                symbol, raw_data, period
            )

            return ProviderResponse.success_response(
                data=statements,
                provider=self.PROVIDER_NAME,
                meta={"count": len(statements), "period": period.value}
            )

        except FMPRateLimitError:
            raise RateLimitError(self.PROVIDER_NAME)
        except Exception as e:
            logger.error(f"FMP get_income_statement error for {symbol}: {e}")
            return ProviderResponse.error_response(
                error=str(e),
                provider=self.PROVIDER_NAME,
                error_code="API_ERROR"
            )

    def get_cash_flow(
        self,
        symbol: str,
        period: PeriodType = PeriodType.ANNUAL
    ) -> ProviderResponse[List[NormalizedCashFlow]]:
        """현금흐름표 조회"""
        try:
            symbol = symbol.upper()
            period_str = "annual" if period == PeriodType.ANNUAL else "quarter"

            raw_data = self._client.get_cash_flow(symbol, period=period_str)

            if not raw_data:
                return ProviderResponse.error_response(
                    error=f"No cash flow data found for {symbol}",
                    provider=self.PROVIDER_NAME,
                    error_code="DATA_NOT_FOUND"
                )

            cash_flows = self._processor.process_cash_flow(
                symbol, raw_data, period
            )

            return ProviderResponse.success_response(
                data=cash_flows,
                provider=self.PROVIDER_NAME,
                meta={"count": len(cash_flows), "period": period.value}
            )

        except FMPRateLimitError:
            raise RateLimitError(self.PROVIDER_NAME)
        except Exception as e:
            logger.error(f"FMP get_cash_flow error for {symbol}: {e}")
            return ProviderResponse.error_response(
                error=str(e),
                provider=self.PROVIDER_NAME,
                error_code="API_ERROR"
            )

    def search_symbols(self, keywords: str) -> ProviderResponse[List[NormalizedSearchResult]]:
        """종목 검색"""
        try:
            # 심볼 검색과 이름 검색 모두 시도
            symbol_results = self._client.search_ticker(keywords)
            name_results = self._client.search_name(keywords)

            # 결과 병합 (중복 제거)
            seen_symbols = set()
            all_results = []

            for item in symbol_results + name_results:
                symbol = item.get("symbol", "")
                if symbol and symbol not in seen_symbols:
                    seen_symbols.add(symbol)
                    all_results.append(item)

            results = self._processor.process_search_results(all_results)

            return ProviderResponse.success_response(
                data=results,
                provider=self.PROVIDER_NAME,
                meta={"count": len(results)}
            )

        except FMPRateLimitError:
            raise RateLimitError(self.PROVIDER_NAME)
        except Exception as e:
            logger.error(f"FMP search_symbols error for '{keywords}': {e}")
            return ProviderResponse.error_response(
                error=str(e),
                provider=self.PROVIDER_NAME,
                error_code="API_ERROR"
            )

    def get_sector_performance(self) -> ProviderResponse[Dict[str, Any]]:
        """섹터 성과 조회"""
        try:
            raw_data = self._client.get_sector_performance()

            if not raw_data:
                return ProviderResponse.error_response(
                    error="No sector performance data found",
                    provider=self.PROVIDER_NAME,
                    error_code="DATA_NOT_FOUND"
                )

            # 섹터별로 정리
            sector_data = {}
            for item in raw_data:
                sector = item.get("sector", "Unknown")
                sector_data[sector] = {
                    "change_percent": item.get("changesPercentage"),
                }

            return ProviderResponse.success_response(
                data=sector_data,
                provider=self.PROVIDER_NAME
            )

        except FMPRateLimitError:
            raise RateLimitError(self.PROVIDER_NAME)
        except Exception as e:
            logger.error(f"FMP get_sector_performance error: {e}")
            return ProviderResponse.error_response(
                error=str(e),
                provider=self.PROVIDER_NAME,
                error_code="API_ERROR"
            )

    def get_rate_limit_status(self) -> Dict[str, Any]:
        """현재 Rate Limit 상태"""
        base_status = super().get_rate_limit_status()
        client_status = self._client.get_rate_limit_status()
        return {**base_status, **client_status}

    # ============================================================
    # 헬퍼 메서드
    # ============================================================

    def _aggregate_to_weekly(
        self,
        daily_prices: List[NormalizedPriceData]
    ) -> List[NormalizedPriceData]:
        """
        일별 데이터를 주별로 집계

        각 주의 마지막 거래일 데이터를 사용하고,
        OHLC는 주간 범위로 계산
        """
        if not daily_prices:
            return []

        from collections import defaultdict

        # ISO 주차로 그룹화
        weekly_groups = defaultdict(list)
        for price in daily_prices:
            iso_year, iso_week, _ = price.date.isocalendar()
            key = (iso_year, iso_week)
            weekly_groups[key].append(price)

        weekly_prices = []
        for (year, week), prices in sorted(weekly_groups.items(), reverse=True):
            if not prices:
                continue

            # 주간 범위 계산
            prices_sorted = sorted(prices, key=lambda x: x.date)

            weekly = NormalizedPriceData(
                date=prices_sorted[-1].date,  # 주의 마지막 거래일
                open=prices_sorted[0].open,   # 주의 첫 거래일 시가
                high=max(p.high for p in prices if p.high),
                low=min(p.low for p in prices if p.low),
                close=prices_sorted[-1].close,  # 주의 마지막 거래일 종가
                volume=sum(p.volume for p in prices if p.volume),
                adjusted_close=prices_sorted[-1].adjusted_close,
            )
            weekly_prices.append(weekly)

        return weekly_prices
