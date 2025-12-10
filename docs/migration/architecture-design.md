# FMP Migration Architecture Design

## 목차
1. [개요](#개요)
2. [현재 시스템 분석](#현재-시스템-분석)
3. [설계 원칙](#설계-원칙)
4. [API Provider 추상화 레이어](#api-provider-추상화-레이어)
5. [디렉토리 구조](#디렉토리-구조)
6. [Feature Flag 메커니즘](#feature-flag-메커니즘)
7. [캐싱 전략](#캐싱-전략)
8. [에러 핸들링 및 Fallback](#에러-핸들링-및-fallback)
9. [마이그레이션 로드맵](#마이그레이션-로드맵)
10. [테스트 전략](#테스트-전략)

---

## 개요

### 목적
Alpha Vantage에서 Financial Modeling Prep (FMP)로의 점진적 마이그레이션을 위한 API Provider 추상화 레이어를 설계합니다.

### 핵심 요구사항
- **기존 코드 호환성**: Django 모델 및 비즈니스 로직 변경 최소화
- **점진적 전환**: 엔드포인트별 개별 전환 가능
- **테스트 용이성**: Mock 및 Integration 테스트 지원
- **확장성**: 향후 다른 Provider 추가 가능
- **성능**: 캐싱 및 Rate Limiting 통합

---

## 현재 시스템 분석

### 3계층 아키텍처

```
┌─────────────────────────────────────────────────────────────┐
│                   Service Layer                             │
│  alphavantage_service.py                                    │
│  - update_stock_data()                                      │
│  - update_historical_prices()                               │
│  - update_financial_statements()                            │
│                                                             │
│  역할: Client + Processor + DB 조율                         │
└───────────────────┬─────────────────────────────────────────┘
                    │
        ┌───────────┴────────────┐
        │                        │
        ▼                        ▼
┌─────────────────┐     ┌─────────────────┐
│  Client Layer   │     │ Processor Layer │
│                 │     │                 │
│ alphavantage_   │     │ alphavantage_   │
│ client.py       │     │ processor.py    │
│                 │     │                 │
│ - HTTP 요청     │     │ - 데이터 변환   │
│ - Rate Limit    │     │ - 안전 변환     │
│ - 에러 핸들링   │     │   (_safe_*)     │
└─────────────────┘     └─────────────────┘
```

### 데이터 플로우
```
API Client → Raw JSON Response
    ↓
Processor → Normalized Dict (snake_case)
    ↓
Service → Django Model Instance
    ↓
Database (Stock, DailyPrice, BalanceSheet, etc.)
```

### 현재 시스템 분석

**강점**:
- 명확한 책임 분리 (Client/Processor/Service)
- 트랜잭션 관리 (`@transaction.atomic`)
- 중복 방지 (`update_or_create`)
- Rate Limiting (12초 간격)

**약점**:
- Alpha Vantage에 강하게 결합
- Provider 전환 시 전체 재작성 필요
- 테스트 시 실제 API 호출 필요
- 캐싱이 Service 외부에 위치 (stocks/views.py)

---

## 설계 원칙

### 1. 추상화 우선 (Abstraction First)
- 모든 데이터 제공자는 동일한 인터페이스 구현
- 비즈니스 로직은 구체적인 Provider에 의존하지 않음

### 2. 의존성 역전 (Dependency Inversion)
```python
# Before (나쁜 예)
service = AlphaVantageService()

# After (좋은 예)
provider = ProviderFactory.get_provider()  # 추상 타입 반환
service = StockService(provider)
```

### 3. 단일 책임 원칙 (Single Responsibility)
- **Provider**: 외부 API와의 통신만 담당
- **Service**: 비즈니스 로직 및 DB 저장
- **Cache**: 성능 최적화
- **Factory**: Provider 인스턴스 생성

### 4. 개방-폐쇄 원칙 (Open-Closed)
- 새 Provider 추가 시 기존 코드 수정 불필요
- 확장은 열려 있고, 수정은 닫혀 있음

---

## API Provider 추상화 레이어

### 1. 추상 기본 클래스 (Abstract Base Class)

```python
# API_request/providers/base.py

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from datetime import date, datetime
from decimal import Decimal

class StockDataProvider(ABC):
    """
    주식 데이터 제공자의 추상 인터페이스

    모든 Provider는 이 인터페이스를 구현해야 함.
    반환 형식은 Django 모델과 호환되는 정규화된 딕셔너리.
    """

    # ===== 실시간 가격 =====
    @abstractmethod
    def get_quote(self, symbol: str) -> Dict[str, Any]:
        """
        실시간 주가 조회

        Args:
            symbol: 주식 심볼 (예: "AAPL")

        Returns:
            Dict with keys: open_price, high_price, low_price,
                           real_time_price, volume, previous_close,
                           change, change_percent
        """
        pass

    # ===== 회사 정보 =====
    @abstractmethod
    def get_company_profile(self, symbol: str) -> Dict[str, Any]:
        """
        회사 기본 정보 조회

        Returns:
            Dict with keys: symbol, stock_name, description,
                           exchange, currency, sector, industry, etc.
        """
        pass

    # ===== 시계열 데이터 =====
    @abstractmethod
    def get_historical_daily(
        self,
        symbol: str,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        일별 시세 조회

        Returns:
            List of dicts with keys: date, open_price, high_price,
                                    low_price, close_price, volume
        """
        pass

    @abstractmethod
    def get_historical_weekly(
        self,
        symbol: str,
        start_date: Optional[date] = None,
        limit: int = 52
    ) -> List[Dict[str, Any]]:
        """
        주간 시세 조회

        Returns:
            List of dicts with keys: date, week_start_date, week_end_date,
                                    open_price, high_price, low_price,
                                    close_price, volume, average_volume
        """
        pass

    # ===== 재무제표 =====
    @abstractmethod
    def get_balance_sheet(
        self,
        symbol: str,
        period: str = 'annual',  # 'annual' or 'quarterly'
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """
        대차대조표 조회

        Returns:
            List of dicts with keys: reported_date, period_type,
                                    fiscal_year, fiscal_quarter,
                                    total_assets, total_liabilities, etc.
        """
        pass

    @abstractmethod
    def get_income_statement(
        self,
        symbol: str,
        period: str = 'annual',
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """
        손익계산서 조회

        Returns:
            List of dicts with keys: reported_date, period_type,
                                    total_revenue, net_income, etc.
        """
        pass

    @abstractmethod
    def get_cash_flow(
        self,
        symbol: str,
        period: str = 'annual',
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """
        현금흐름표 조회

        Returns:
            List of dicts with keys: reported_date, period_type,
                                    operating_cashflow, etc.
        """
        pass

    # ===== 검색 =====
    @abstractmethod
    def search_stocks(self, keywords: str) -> List[Dict[str, str]]:
        """
        종목 검색

        Returns:
            List of dicts with keys: symbol, name, exchange, type
        """
        pass

    # ===== 유틸리티 =====
    @abstractmethod
    def get_provider_name(self) -> str:
        """
        Provider 이름 반환 (로깅/디버깅용)

        Returns:
            str: "AlphaVantage" or "FMP"
        """
        pass

    @abstractmethod
    def get_rate_limit_info(self) -> Dict[str, Any]:
        """
        Rate Limit 정보 반환

        Returns:
            Dict with keys: requests_per_minute, requests_per_day,
                           delay_between_requests
        """
        pass
```

### 2. Alpha Vantage Provider 구현

```python
# API_request/providers/alphavantage/provider.py

import logging
from typing import Dict, Any, List, Optional
from datetime import date

from ..base import StockDataProvider
from .client import AlphaVantageClient
from .processor import AlphaVantageProcessor

logger = logging.getLogger(__name__)


class AlphaVantageProvider(StockDataProvider):
    """
    Alpha Vantage API Provider 구현

    기존 Client + Processor를 래핑하여 표준 인터페이스 제공
    """

    def __init__(self, api_key: str, request_delay: float = 12.0):
        self.client = AlphaVantageClient(api_key, request_delay)
        self.processor = AlphaVantageProcessor()

    def get_quote(self, symbol: str) -> Dict[str, Any]:
        """실시간 주가 조회"""
        raw_data = self.client.get_stock_quote(symbol)
        return self.processor.process_stock_quote(symbol, raw_data)

    def get_company_profile(self, symbol: str) -> Dict[str, Any]:
        """회사 기본 정보 조회"""
        raw_data = self.client.get_company_overview(symbol)
        return self.processor.process_company_overview(raw_data)

    def get_historical_daily(
        self,
        symbol: str,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """일별 시세 조회"""
        # Alpha Vantage는 limit을 직접 지원하지 않으므로
        # outputsize로 제어 (compact=100, full=20+ years)
        outputsize = "compact" if limit <= 100 else "full"
        raw_data = self.client.get_daily_stock_data(symbol, outputsize)
        processed_data = self.processor.process_daily_historical_prices(symbol, raw_data)

        # 날짜 필터링
        if start_date or end_date:
            processed_data = self._filter_by_date(processed_data, start_date, end_date)

        # Limit 적용
        return processed_data[:limit]

    def get_historical_weekly(
        self,
        symbol: str,
        start_date: Optional[date] = None,
        limit: int = 52
    ) -> List[Dict[str, Any]]:
        """주간 시세 조회"""
        raw_data = self.client.get_weekly_stock_data(symbol)
        processed_data = self.processor.process_weekly_historical_prices(symbol, raw_data)

        if start_date:
            processed_data = [d for d in processed_data if d['date'] >= start_date]

        return processed_data[:limit]

    def get_balance_sheet(
        self,
        symbol: str,
        period: str = 'annual',
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """대차대조표 조회"""
        raw_data = self.client.get_balance_sheet(symbol)
        processed_data = self.processor.process_balance_sheet(raw_data)

        # Period 필터링 ('annual' or 'quarterly')
        # Alpha Vantage processor는 period_type='annual' 또는 'quarter' 반환
        period_type_map = {'annual': 'annual', 'quarterly': 'quarter'}
        target_period = period_type_map.get(period, 'annual')

        filtered = [d for d in processed_data if d['period_type'] == target_period]
        return filtered[:limit]

    def get_income_statement(
        self,
        symbol: str,
        period: str = 'annual',
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """손익계산서 조회"""
        raw_data = self.client.get_income_statement(symbol)
        processed_data = self.processor.process_income_statement(raw_data)

        period_type_map = {'annual': 'annual', 'quarterly': 'quarter'}
        target_period = period_type_map.get(period, 'annual')

        filtered = [d for d in processed_data if d['period_type'] == target_period]
        return filtered[:limit]

    def get_cash_flow(
        self,
        symbol: str,
        period: str = 'annual',
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """현금흐름표 조회"""
        raw_data = self.client.get_cash_flow(symbol)
        processed_data = self.processor.process_cash_flow(raw_data)

        period_type_map = {'annual': 'annual', 'quarterly': 'quarter'}
        target_period = period_type_map.get(period, 'annual')

        filtered = [d for d in processed_data if d['period_type'] == target_period]
        return filtered[:limit]

    def search_stocks(self, keywords: str) -> List[Dict[str, str]]:
        """종목 검색"""
        raw_data = self.client.search_stocks(keywords)

        # Alpha Vantage 응답 형식 변환
        # [{"1. symbol": "AAPL", "2. name": "Apple Inc.", ...}]
        # → [{"symbol": "AAPL", "name": "Apple Inc.", ...}]
        return [
            {
                'symbol': item.get('1. symbol', ''),
                'name': item.get('2. name', ''),
                'exchange': item.get('4. region', ''),
                'type': item.get('3. type', '')
            }
            for item in raw_data
        ]

    def get_provider_name(self) -> str:
        return "AlphaVantage"

    def get_rate_limit_info(self) -> Dict[str, Any]:
        return {
            'requests_per_minute': 5,
            'requests_per_day': 500,
            'delay_between_requests': self.client.request_delay
        }

    # ===== Private Helpers =====
    def _filter_by_date(
        self,
        data: List[Dict[str, Any]],
        start_date: Optional[date],
        end_date: Optional[date]
    ) -> List[Dict[str, Any]]:
        """날짜 범위로 필터링"""
        if start_date:
            data = [d for d in data if d['date'] >= start_date]
        if end_date:
            data = [d for d in data if d['date'] <= end_date]
        return data
```

### 3. FMP Provider 구현 (스켈레톤)

```python
# API_request/providers/fmp/provider.py

import logging
from typing import Dict, Any, List, Optional
from datetime import date

from ..base import StockDataProvider
from .client import FMPClient
from .processor import FMPProcessor

logger = logging.getLogger(__name__)


class FMPProvider(StockDataProvider):
    """
    Financial Modeling Prep API Provider 구현
    """

    def __init__(self, api_key: str):
        self.client = FMPClient(api_key)
        self.processor = FMPProcessor()

    def get_quote(self, symbol: str) -> Dict[str, Any]:
        """
        FMP API: https://financialmodelingprep.com/api/v3/quote/{symbol}
        """
        raw_data = self.client.get_quote(symbol)
        return self.processor.process_quote(raw_data)

    def get_company_profile(self, symbol: str) -> Dict[str, Any]:
        """
        FMP API: https://financialmodelingprep.com/api/v3/profile/{symbol}
        """
        raw_data = self.client.get_company_profile(symbol)
        return self.processor.process_company_profile(raw_data)

    def get_historical_daily(
        self,
        symbol: str,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        FMP API: https://financialmodelingprep.com/api/v3/historical-price-full/{symbol}
        """
        raw_data = self.client.get_historical_daily(symbol, start_date, end_date)
        processed = self.processor.process_historical_daily(raw_data)
        return processed[:limit]

    # ... 나머지 메서드 구현 ...

    def get_provider_name(self) -> str:
        return "FMP"

    def get_rate_limit_info(self) -> Dict[str, Any]:
        # FMP 무료 티어: 250 calls/day
        # 유료 티어: 더 높은 제한
        return {
            'requests_per_minute': 60,  # 추정치
            'requests_per_day': 250,    # 무료 티어
            'delay_between_requests': 1.0  # Alpha Vantage보다 빠름
        }
```

---

## 디렉토리 구조

```
API_request/
├── __init__.py                    # Provider 패키지 초기화
├── provider_factory.py            # Feature Flag 기반 Provider 선택
├── stock_service.py               # Provider를 사용하는 통합 서비스
│
├── providers/                     # Provider 구현들
│   ├── __init__.py
│   ├── base.py                    # StockDataProvider 추상 클래스
│   │
│   ├── alphavantage/              # Alpha Vantage 구현
│   │   ├── __init__.py
│   │   ├── client.py              # HTTP 클라이언트 (기존 코드 이동)
│   │   ├── processor.py           # 데이터 변환 (기존 코드 이동)
│   │   └── provider.py            # StockDataProvider 구현
│   │
│   └── fmp/                       # FMP 구현
│       ├── __init__.py
│       ├── client.py              # FMP HTTP 클라이언트
│       ├── processor.py           # FMP 데이터 변환
│       └── provider.py            # StockDataProvider 구현
│
├── cache/                         # 캐싱 레이어
│   ├── __init__.py
│   ├── base.py                    # 캐시 추상 클래스
│   ├── redis_cache.py             # Redis 캐시 구현
│   └── memory_cache.py            # In-memory 캐시 (개발용)
│
└── legacy/                        # 레거시 코드 (마이그레이션 완료 후 삭제)
    ├── alphavantage_client.py     # 원본 보존
    ├── alphavantage_processor.py
    └── alphavantage_service.py
```

### 파일별 책임

| 파일 | 책임 | 의존성 |
|-----|------|--------|
| `base.py` | 추상 인터페이스 정의 | 없음 |
| `alphavantage/client.py` | Alpha Vantage HTTP 호출 | requests |
| `alphavantage/processor.py` | Alpha Vantage 응답 변환 | 없음 |
| `alphavantage/provider.py` | Provider 인터페이스 구현 | client, processor |
| `fmp/provider.py` | FMP Provider 구현 | client, processor |
| `provider_factory.py` | Provider 인스턴스 생성 | settings, providers |
| `stock_service.py` | 비즈니스 로직 + DB 저장 | base.StockDataProvider |

---

## Feature Flag 메커니즘

### 1. 환경 변수 기반 설정

```python
# config/settings.py

# ===== Stock Data Provider 설정 =====
STOCK_DATA_PROVIDER = os.getenv('STOCK_DATA_PROVIDER', 'alphavantage')  # 'alphavantage' or 'fmp'

# Provider별 API 키
ALPHA_VANTAGE_API_KEY = os.getenv('ALPHA_VANTAGE_API_KEY')
FMP_API_KEY = os.getenv('FMP_API_KEY')

# Feature Flag: 엔드포인트별 Provider 오버라이드
PROVIDER_OVERRIDES = {
    'quote': os.getenv('PROVIDER_QUOTE', STOCK_DATA_PROVIDER),
    'company_profile': os.getenv('PROVIDER_COMPANY_PROFILE', STOCK_DATA_PROVIDER),
    'historical_daily': os.getenv('PROVIDER_HISTORICAL_DAILY', STOCK_DATA_PROVIDER),
    'historical_weekly': os.getenv('PROVIDER_HISTORICAL_WEEKLY', STOCK_DATA_PROVIDER),
    'balance_sheet': os.getenv('PROVIDER_BALANCE_SHEET', STOCK_DATA_PROVIDER),
    'income_statement': os.getenv('PROVIDER_INCOME_STATEMENT', STOCK_DATA_PROVIDER),
    'cash_flow': os.getenv('PROVIDER_CASH_FLOW', STOCK_DATA_PROVIDER),
    'search': os.getenv('PROVIDER_SEARCH', STOCK_DATA_PROVIDER),
}

# Fallback 설정 (Primary Provider 실패 시)
ENABLE_PROVIDER_FALLBACK = os.getenv('ENABLE_PROVIDER_FALLBACK', 'true').lower() == 'true'
FALLBACK_PROVIDER = os.getenv('FALLBACK_PROVIDER', 'alphavantage')
```

### 2. Provider Factory

```python
# API_request/provider_factory.py

import logging
from typing import Optional
from django.conf import settings

from .providers.base import StockDataProvider
from .providers.alphavantage.provider import AlphaVantageProvider
from .providers.fmp.provider import FMPProvider

logger = logging.getLogger(__name__)


class ProviderFactory:
    """
    Feature Flag 기반 Provider 인스턴스 생성 팩토리
    """

    _instances = {}  # Provider 싱글톤 캐시

    @classmethod
    def get_provider(cls, endpoint: Optional[str] = None) -> StockDataProvider:
        """
        Feature Flag에 따라 적절한 Provider 반환

        Args:
            endpoint: 엔드포인트 이름 (예: 'quote', 'historical_daily')
                     None이면 기본 Provider 사용

        Returns:
            StockDataProvider 구현체
        """
        # 엔드포인트별 오버라이드 확인
        if endpoint and endpoint in settings.PROVIDER_OVERRIDES:
            provider_name = settings.PROVIDER_OVERRIDES[endpoint]
            logger.info(f"Endpoint '{endpoint}' using provider: {provider_name}")
        else:
            provider_name = settings.STOCK_DATA_PROVIDER

        # 싱글톤 캐시 확인
        if provider_name in cls._instances:
            return cls._instances[provider_name]

        # Provider 인스턴스 생성
        provider = cls._create_provider(provider_name)
        cls._instances[provider_name] = provider

        return provider

    @classmethod
    def get_fallback_provider(cls) -> Optional[StockDataProvider]:
        """
        Fallback Provider 반환 (Primary 실패 시 사용)
        """
        if not settings.ENABLE_PROVIDER_FALLBACK:
            return None

        fallback_name = settings.FALLBACK_PROVIDER

        # Primary와 동일하면 None 반환 (무한 재귀 방지)
        if fallback_name == settings.STOCK_DATA_PROVIDER:
            logger.warning("Fallback provider is same as primary, disabling fallback")
            return None

        if fallback_name in cls._instances:
            return cls._instances[fallback_name]

        provider = cls._create_provider(fallback_name)
        cls._instances[fallback_name] = provider

        return provider

    @classmethod
    def _create_provider(cls, provider_name: str) -> StockDataProvider:
        """
        Provider 이름으로 인스턴스 생성
        """
        if provider_name == 'alphavantage':
            if not settings.ALPHA_VANTAGE_API_KEY:
                raise ValueError("ALPHA_VANTAGE_API_KEY not configured")
            return AlphaVantageProvider(
                api_key=settings.ALPHA_VANTAGE_API_KEY,
                request_delay=12.0
            )

        elif provider_name == 'fmp':
            if not settings.FMP_API_KEY:
                raise ValueError("FMP_API_KEY not configured")
            return FMPProvider(api_key=settings.FMP_API_KEY)

        else:
            raise ValueError(f"Unknown provider: {provider_name}")

    @classmethod
    def clear_cache(cls):
        """싱글톤 캐시 초기화 (테스트용)"""
        cls._instances = {}
```

### 3. 통합 Service

```python
# API_request/stock_service.py

import logging
from typing import Dict, Any, List, Union, Optional
from datetime import date
from django.db import transaction

from .provider_factory import ProviderFactory
from .providers.base import StockDataProvider
from stocks.models import Stock, DailyPrice, WeeklyPrice, BalanceSheet, IncomeStatement, CashFlowStatement

logger = logging.getLogger(__name__)


class StockService:
    """
    Provider-agnostic 주식 데이터 서비스

    Provider 추상화를 통해 여러 데이터 소스를 통합 관리
    """

    def __init__(self, provider: Optional[StockDataProvider] = None):
        """
        Args:
            provider: 사용할 Provider (None이면 Factory에서 자동 선택)
        """
        self.provider = provider or ProviderFactory.get_provider()
        self.fallback_provider = ProviderFactory.get_fallback_provider()
        logger.info(f"StockService initialized with provider: {self.provider.get_provider_name()}")

    def update_stock_data(self, symbol: str) -> Stock:
        """
        주식 기본 정보 업데이트 (Overview + Quote)

        기존 AlphaVantageService.update_stock_data()와 동일한 시그니처
        """
        symbol = symbol.upper().strip()

        try:
            # 1. Company Profile 조회 (with fallback)
            logger.info(f"Fetching company profile for {symbol}")
            profile_data = self._call_with_fallback(
                'get_company_profile',
                symbol,
                endpoint='company_profile'
            )

            if not profile_data:
                # 기존 데이터 반환
                try:
                    stock = Stock.objects.get(symbol=symbol)
                    logger.warning(f"Could not fetch profile for {symbol}, using existing data")
                    return stock
                except Stock.DoesNotExist:
                    logger.error(f"Could not fetch profile for {symbol} and stock does not exist")
                    raise ValueError(f"Could not fetch stock data for {symbol}")

            # 2. Real-time Quote 조회
            try:
                logger.info(f"Fetching real-time quote for {symbol}")
                quote_data = self._call_with_fallback(
                    'get_quote',
                    symbol,
                    endpoint='quote'
                )

                if quote_data:
                    # 중복 키 제거 후 병합
                    price_updates = {k: v for k, v in quote_data.items() if k != 'symbol'}
                    profile_data.update(price_updates)

            except Exception as e:
                logger.error(f"Error fetching quote for {symbol}: {e}")
                # 실시간 가격 실패해도 프로필은 저장

            # 3. DB 저장
            with transaction.atomic():
                stock, created = Stock.objects.update_or_create(
                    symbol=symbol,
                    defaults=profile_data
                )

                action = "Created" if created else "Updated"
                logger.info(f"{action} stock: {symbol}")

                return stock

        except Exception as e:
            logger.error(f"Error updating stock data for {symbol}: {e}")
            raise

    def update_historical_prices(
        self,
        stock: Union[Stock, str],
        days: int = 100
    ) -> Dict[str, int]:
        """
        시계열 데이터 업데이트 (Daily + Weekly)
        """
        # Normalize stock input
        if isinstance(stock, str):
            symbol = stock.upper().strip()
            stock_obj = Stock.objects.get(symbol=symbol)
        else:
            stock_obj = stock
            symbol = stock_obj.symbol

        logger.info(f"Updating historical prices for {symbol} ({days} days)")

        results = {'daily': 0, 'weekly': 0}

        try:
            # 1. Daily prices
            logger.info(f"Fetching daily data for {symbol}")
            daily_data = self._call_with_fallback(
                'get_historical_daily',
                symbol,
                limit=days,
                endpoint='historical_daily'
            )

            if daily_data:
                results['daily'] = self._save_daily_prices(stock_obj, daily_data)
                logger.info(f"Updated {results['daily']} daily records for {symbol}")

            # 2. Weekly prices
            logger.info(f"Fetching weekly data for {symbol}")
            weekly_data = self._call_with_fallback(
                'get_historical_weekly',
                symbol,
                limit=52,
                endpoint='historical_weekly'
            )

            if weekly_data:
                results['weekly'] = self._save_weekly_prices(stock_obj, weekly_data)
                logger.info(f"Updated {results['weekly']} weekly records for {symbol}")

        except Exception as e:
            logger.error(f"Error updating historical prices for {symbol}: {e}")
            raise

        return results

    def update_financial_statements(self, stock: Union[Stock, str]) -> Dict[str, int]:
        """
        재무제표 업데이트 (Balance Sheet + Income + Cash Flow)
        """
        # Normalize stock input
        if isinstance(stock, str):
            symbol = stock.upper().strip()
            stock_obj = Stock.objects.get(symbol=symbol)
        else:
            stock_obj = stock
            symbol = stock_obj.symbol

        logger.info(f"Updating financial statements for {symbol}")

        results = {
            'balance_sheets': 0,
            'income_statements': 0,
            'cash_flows': 0,
        }

        try:
            # 1. Balance Sheet
            logger.info(f"Fetching balance sheet for {symbol}")
            balance_data = self._call_with_fallback(
                'get_balance_sheet',
                symbol,
                period='annual',
                limit=5,
                endpoint='balance_sheet'
            )

            if balance_data:
                results['balance_sheets'] = self._save_balance_sheets(stock_obj, balance_data)

            # 2. Income Statement
            logger.info(f"Fetching income statement for {symbol}")
            income_data = self._call_with_fallback(
                'get_income_statement',
                symbol,
                period='annual',
                limit=5,
                endpoint='income_statement'
            )

            if income_data:
                results['income_statements'] = self._save_income_statements(stock_obj, income_data)

            # 3. Cash Flow
            logger.info(f"Fetching cash flow for {symbol}")
            cash_flow_data = self._call_with_fallback(
                'get_cash_flow',
                symbol,
                period='annual',
                limit=5,
                endpoint='cash_flow'
            )

            if cash_flow_data:
                results['cash_flows'] = self._save_cash_flows(stock_obj, cash_flow_data)

            logger.info(f"Updated financial statements for {symbol}: {results}")

        except Exception as e:
            logger.error(f"Error updating financial statements for {symbol}: {e}")
            raise

        return results

    # ===== Private Helpers =====

    def _call_with_fallback(self, method_name: str, *args, endpoint: Optional[str] = None, **kwargs):
        """
        Primary Provider 호출 후 실패 시 Fallback Provider 시도
        """
        # Primary Provider 선택 (endpoint별 오버라이드 고려)
        primary_provider = ProviderFactory.get_provider(endpoint)

        try:
            method = getattr(primary_provider, method_name)
            return method(*args, **kwargs)

        except Exception as e:
            logger.error(f"Primary provider ({primary_provider.get_provider_name()}) failed: {e}")

            # Fallback 시도
            if self.fallback_provider:
                logger.info(f"Trying fallback provider: {self.fallback_provider.get_provider_name()}")
                try:
                    method = getattr(self.fallback_provider, method_name)
                    return method(*args, **kwargs)
                except Exception as fallback_error:
                    logger.error(f"Fallback provider also failed: {fallback_error}")
                    raise
            else:
                raise

    def _save_daily_prices(self, stock: Stock, price_data: List[Dict[str, Any]]) -> int:
        """일일 가격 데이터 배치 저장 (기존 로직 유지)"""
        saved_count = 0

        with transaction.atomic():
            for price_record in price_data:
                try:
                    price_record.pop('stock_symbol', None)

                    daily_price, created = DailyPrice.objects.update_or_create(
                        stock=stock,
                        date=price_record['date'],
                        defaults=price_record
                    )

                    if created:
                        saved_count += 1

                except Exception as e:
                    logger.error(f"Error saving daily price for {stock.symbol}: {e}")
                    continue

        return saved_count

    # _save_weekly_prices, _save_balance_sheets 등 동일한 패턴으로 구현
    # (기존 AlphaVantageService와 동일)
```

### 사용 예시

```python
# Before (Alpha Vantage 전용)
from API_request.alphavantage_service import AlphaVantageService

service = AlphaVantageService(api_key=settings.ALPHA_VANTAGE_API_KEY)
stock = service.update_stock_data('AAPL')

# After (Provider-agnostic)
from API_request.stock_service import StockService

service = StockService()  # Factory가 자동으로 Provider 선택
stock = service.update_stock_data('AAPL')
```

---

## 캐싱 전략

### 1. 캐싱 위치 결정

**현재 상황**:
- `stocks/views.py`에서 Django 기본 캐시 사용
- Provider 레벨에서는 캐싱 없음

**권장 접근법**: **Provider 외부 캐싱 (Decorator 패턴)**

**장점**:
- Provider 구현이 단순해짐 (캐싱 로직 불포함)
- 모든 Provider에 일관된 캐싱 적용
- 캐시 무효화 로직 중앙 관리

### 2. 캐시 추상화

```python
# API_request/cache/base.py

from abc import ABC, abstractmethod
from typing import Any, Optional, Callable
import hashlib
import json


class StockDataCache(ABC):
    """
    주식 데이터 캐싱 추상 클래스
    """

    @abstractmethod
    def get(self, key: str) -> Optional[Any]:
        """캐시 조회"""
        pass

    @abstractmethod
    def set(self, key: str, value: Any, timeout: int = 300):
        """캐시 저장"""
        pass

    @abstractmethod
    def delete(self, key: str):
        """캐시 삭제"""
        pass

    @abstractmethod
    def clear(self):
        """전체 캐시 삭제"""
        pass

    @staticmethod
    def generate_key(provider_name: str, method_name: str, *args, **kwargs) -> str:
        """
        캐시 키 생성 (충돌 방지)

        예: "alphavantage:get_quote:AAPL"
        """
        # 인자를 정렬 가능한 문자열로 변환
        args_str = json.dumps(args, sort_keys=True, default=str)
        kwargs_str = json.dumps(kwargs, sort_keys=True, default=str)

        # 해시 생성 (너무 긴 키 방지)
        combined = f"{provider_name}:{method_name}:{args_str}:{kwargs_str}"
        hash_suffix = hashlib.md5(combined.encode()).hexdigest()[:8]

        # 심볼이 있으면 키에 포함 (디버깅 편의)
        symbol = args[0] if args else kwargs.get('symbol', '')

        return f"{provider_name}:{method_name}:{symbol}:{hash_suffix}"
```

```python
# API_request/cache/redis_cache.py

import logging
from typing import Any, Optional
from django.core.cache import cache
import json

from .base import StockDataCache

logger = logging.getLogger(__name__)


class RedisStockCache(StockDataCache):
    """
    Redis 기반 캐시 구현
    """

    def __init__(self, prefix: str = 'stock_data'):
        self.prefix = prefix

    def get(self, key: str) -> Optional[Any]:
        """캐시 조회"""
        full_key = f"{self.prefix}:{key}"

        try:
            cached = cache.get(full_key)
            if cached:
                logger.debug(f"Cache hit: {full_key}")
                return json.loads(cached)
            else:
                logger.debug(f"Cache miss: {full_key}")
                return None

        except Exception as e:
            logger.error(f"Cache get error: {e}")
            return None

    def set(self, key: str, value: Any, timeout: int = 300):
        """캐시 저장"""
        full_key = f"{self.prefix}:{key}"

        try:
            serialized = json.dumps(value, default=str)
            cache.set(full_key, serialized, timeout)
            logger.debug(f"Cache set: {full_key} (timeout={timeout}s)")

        except Exception as e:
            logger.error(f"Cache set error: {e}")

    def delete(self, key: str):
        """캐시 삭제"""
        full_key = f"{self.prefix}:{key}"
        cache.delete(full_key)
        logger.debug(f"Cache deleted: {full_key}")

    def clear(self):
        """전체 캐시 삭제 (주의: Redis 전체가 아닌 prefix만)"""
        # Django cache는 prefix 기반 clear를 직접 지원하지 않음
        # 필요시 Redis 직접 접근 구현
        logger.warning("Cache clear not implemented for Redis (requires direct Redis access)")
```

### 3. 캐시 Decorator

```python
# API_request/cache/decorators.py

import logging
from functools import wraps
from typing import Callable

from .base import StockDataCache
from .redis_cache import RedisStockCache

logger = logging.getLogger(__name__)

# 전역 캐시 인스턴스
_cache_instance = RedisStockCache()


def cached_provider_call(timeout: int = 300):
    """
    Provider 메서드 호출 결과를 캐싱하는 데코레이터

    Args:
        timeout: 캐시 유효 시간 (초)

    Usage:
        @cached_provider_call(timeout=600)
        def get_company_profile(self, symbol: str):
            ...
    """
    def decorator(func: Callable):
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            # 캐시 키 생성
            provider_name = self.get_provider_name()
            cache_key = StockDataCache.generate_key(
                provider_name,
                func.__name__,
                *args,
                **kwargs
            )

            # 캐시 조회
            cached_value = _cache_instance.get(cache_key)
            if cached_value is not None:
                logger.info(f"Returning cached data for {cache_key}")
                return cached_value

            # 실제 API 호출
            logger.info(f"Cache miss, calling API: {cache_key}")
            result = func(self, *args, **kwargs)

            # 캐시 저장
            if result:  # 유효한 결과만 캐싱
                _cache_instance.set(cache_key, result, timeout)

            return result

        return wrapper
    return decorator
```

### 4. Provider에 캐싱 적용

```python
# API_request/providers/alphavantage/provider.py

from ...cache.decorators import cached_provider_call


class AlphaVantageProvider(StockDataProvider):

    @cached_provider_call(timeout=60)  # 1분 캐싱
    def get_quote(self, symbol: str) -> Dict[str, Any]:
        """실시간 주가 조회 (캐싱됨)"""
        raw_data = self.client.get_stock_quote(symbol)
        return self.processor.process_stock_quote(symbol, raw_data)

    @cached_provider_call(timeout=600)  # 10분 캐싱
    def get_company_profile(self, symbol: str) -> Dict[str, Any]:
        """회사 정보 조회 (캐싱됨)"""
        raw_data = self.client.get_company_overview(symbol)
        return self.processor.process_company_overview(raw_data)

    @cached_provider_call(timeout=3600)  # 1시간 캐싱
    def get_balance_sheet(self, symbol: str, period: str = 'annual', limit: int = 5):
        """재무제표 조회 (캐싱됨)"""
        # ... 기존 로직 ...
```

### 캐싱 타임아웃 권장값

| 데이터 타입 | Timeout | 이유 |
|-----------|---------|------|
| 실시간 주가 (Quote) | 60초 | 빠른 변동 |
| Company Profile | 600초 (10분) | 거의 변하지 않음 |
| 일일 시세 | 300초 (5분) | 시장 종료 후 변하지 않음 |
| 주간 시세 | 3600초 (1시간) | 주 단위 업데이트 |
| 재무제표 | 3600초 (1시간) | 분기/연간 업데이트 |
| 검색 | 1800초 (30분) | 자주 변하지 않음 |

---

## 에러 핸들링 및 Fallback

### 1. 에러 계층 구조

```python
# API_request/exceptions.py

class StockDataError(Exception):
    """기본 예외 클래스"""
    pass


class ProviderError(StockDataError):
    """Provider 관련 에러"""
    pass


class ProviderAPIError(ProviderError):
    """외부 API 호출 에러"""
    def __init__(self, provider: str, message: str, status_code: int = None):
        self.provider = provider
        self.status_code = status_code
        super().__init__(f"[{provider}] {message}")


class ProviderRateLimitError(ProviderAPIError):
    """Rate Limit 초과"""
    pass


class ProviderNotFoundError(ProviderError):
    """요청한 종목이 존재하지 않음"""
    pass


class ProviderDataFormatError(ProviderError):
    """응답 데이터 형식 오류"""
    pass
```

### 2. Fallback 전략

```python
# API_request/stock_service.py (확장)

class StockService:

    def _call_with_fallback(self, method_name: str, *args, endpoint: Optional[str] = None, **kwargs):
        """
        Primary Provider 호출 후 실패 시 Fallback 시도

        Fallback 조건:
        - API 호출 실패 (네트워크, 타임아웃)
        - Rate Limit 초과
        - 데이터 형식 오류

        Fallback 제외 조건:
        - 종목이 존재하지 않음 (ProviderNotFoundError)
        - 인증 실패 (API 키 오류)
        """
        primary_provider = ProviderFactory.get_provider(endpoint)

        try:
            method = getattr(primary_provider, method_name)
            result = method(*args, **kwargs)

            # 성공 로깅
            logger.info(f"✓ {primary_provider.get_provider_name()}.{method_name} succeeded")
            return result

        except ProviderNotFoundError:
            # 종목 없음 - Fallback 시도 않음
            logger.error(f"Symbol not found, no fallback")
            raise

        except (ProviderAPIError, ProviderRateLimitError, ProviderDataFormatError) as e:
            logger.error(f"✗ Primary provider failed: {e}")

            # Fallback 시도
            if self.fallback_provider:
                logger.info(f"→ Trying fallback: {self.fallback_provider.get_provider_name()}")

                try:
                    method = getattr(self.fallback_provider, method_name)
                    result = method(*args, **kwargs)

                    logger.info(f"✓ Fallback succeeded")
                    return result

                except Exception as fallback_error:
                    logger.error(f"✗ Fallback also failed: {fallback_error}")
                    raise  # 원래 예외 재발생

            else:
                logger.warning("No fallback provider configured")
                raise

        except Exception as e:
            # 예상하지 못한 에러
            logger.error(f"Unexpected error in {primary_provider.get_provider_name()}.{method_name}: {e}")
            raise
```

### 3. Circuit Breaker 패턴 (선택적)

Rate Limit 초과 시 일시적으로 Provider를 비활성화:

```python
# API_request/circuit_breaker.py

import time
from typing import Dict
from datetime import datetime, timedelta


class CircuitBreaker:
    """
    Circuit Breaker 패턴 구현

    - Closed: 정상 동작
    - Open: 에러 임계값 초과, 모든 요청 거부
    - Half-Open: 복구 시도 중
    """

    def __init__(self, failure_threshold: int = 5, timeout: int = 60):
        self.failure_threshold = failure_threshold
        self.timeout = timeout  # Open → Half-Open 전환 시간 (초)

        self.failure_count = 0
        self.last_failure_time = None
        self.state = 'closed'  # 'closed', 'open', 'half_open'

    def call(self, func, *args, **kwargs):
        """
        Circuit Breaker를 거쳐 함수 호출
        """
        if self.state == 'open':
            # Open 상태: 타임아웃 확인
            if self._should_attempt_reset():
                self.state = 'half_open'
            else:
                raise Exception(f"Circuit breaker is OPEN (too many failures)")

        try:
            result = func(*args, **kwargs)

            # 성공 시 리셋
            if self.state == 'half_open':
                self._reset()

            return result

        except Exception as e:
            self._record_failure()
            raise

    def _record_failure(self):
        """실패 기록"""
        self.failure_count += 1
        self.last_failure_time = datetime.now()

        if self.failure_count >= self.failure_threshold:
            self.state = 'open'
            print(f"Circuit breaker opened after {self.failure_count} failures")

    def _should_attempt_reset(self) -> bool:
        """타임아웃 경과 여부 확인"""
        if not self.last_failure_time:
            return False

        elapsed = (datetime.now() - self.last_failure_time).total_seconds()
        return elapsed >= self.timeout

    def _reset(self):
        """Circuit Breaker 리셋"""
        self.failure_count = 0
        self.last_failure_time = None
        self.state = 'closed'
        print("Circuit breaker reset to CLOSED")


# 사용 예시
# circuit_breaker = CircuitBreaker(failure_threshold=3, timeout=60)
# result = circuit_breaker.call(provider.get_quote, 'AAPL')
```

---

## 마이그레이션 로드맵

### Phase 1: 인프라 구축 (1주)

**목표**: Provider 추상화 레이어 구현

**작업**:
1. ✅ `providers/base.py` - 추상 인터페이스 정의
2. ✅ `providers/alphavantage/` - 기존 코드 래핑
3. ✅ `provider_factory.py` - Feature Flag 메커니즘
4. ✅ `stock_service.py` - Provider-agnostic 서비스
5. ✅ `cache/` - 캐싱 레이어 구현
6. ✅ `exceptions.py` - 에러 계층 정의

**검증**:
- 기존 `AlphaVantageService`와 동일하게 동작
- 단위 테스트 통과
- 기존 Django views에서 정상 작동

### Phase 2: FMP 구현 (2주)

**목표**: FMP Provider 완성 및 테스트

**작업**:
1. 🔨 `providers/fmp/client.py` - FMP API 클라이언트
2. 🔨 `providers/fmp/processor.py` - 데이터 변환 로직
3. 🔨 `providers/fmp/provider.py` - Provider 구현
4. 🔨 필드 매핑 문서 작성 (Alpha Vantage ↔ FMP)
5. 🔨 통합 테스트 (Sandbox 환경)

**검증**:
- FMP Provider만으로 전체 플로우 동작
- 데이터 일관성 검증 (Alpha Vantage vs FMP)
- 캐싱 및 Rate Limiting 정상 작동

### Phase 3: 점진적 전환 (2주)

**목표**: 엔드포인트별 순차 마이그레이션

**순서** (위험도 낮은 순):
1. ✅ 검색 (search_stocks) - 실시간성 낮음
2. ✅ 회사 정보 (get_company_profile) - 거의 변하지 않음
3. ✅ 재무제표 (balance_sheet, income, cash_flow) - 분기별 업데이트
4. ✅ 주간 시세 (get_historical_weekly)
5. ✅ 일일 시세 (get_historical_daily)
6. ⚠️ 실시간 주가 (get_quote) - 마지막 (가장 critical)

**각 단계마다**:
```bash
# .env 설정
PROVIDER_SEARCH=fmp
PROVIDER_COMPANY_PROFILE=alphavantage  # 아직 전환 안함
...

# 1주일 모니터링
- 에러율 확인
- 데이터 품질 검증
- 사용자 피드백 수집

# 문제 없으면 다음 엔드포인트 전환
```

### Phase 4: 완전 전환 및 정리 (1주)

**목표**: Alpha Vantage 의존성 제거

**작업**:
1. ✅ 모든 엔드포인트가 FMP 사용 확인
2. ✅ Fallback 설정 제거 또는 반대 방향으로 변경
3. 🗑️ `API_request/legacy/` 디렉토리 삭제
4. 📝 문서 업데이트 (CLAUDE.md, README)
5. 📝 팀 온보딩 자료 작성

### 롤백 계획

각 Phase에서 문제 발생 시:

```bash
# 긴급 롤백 (환경 변수만 변경)
STOCK_DATA_PROVIDER=alphavantage
ENABLE_PROVIDER_FALLBACK=false

# 코드 롤백 (Git)
git revert <commit-hash>

# 데이터 검증
python manage.py shell
>>> from API_request.stock_service import StockService
>>> service = StockService()
>>> service.provider.get_provider_name()
'AlphaVantage'  # 확인
```

---

## 테스트 전략

### 1. 단위 테스트 (Unit Tests)

```python
# tests/unit/test_providers.py

import pytest
from unittest.mock import Mock, patch
from API_request.providers.alphavantage.provider import AlphaVantageProvider


class TestAlphaVantageProvider:

    @pytest.fixture
    def provider(self):
        return AlphaVantageProvider(api_key='test_key')

    @patch('API_request.providers.alphavantage.client.AlphaVantageClient.get_stock_quote')
    def test_get_quote_success(self, mock_get_quote, provider):
        """실시간 주가 조회 성공 케이스"""
        # Given
        mock_get_quote.return_value = {
            "Global Quote": {
                "05. price": "150.25",
                "09. change": "2.50",
                "10. change percent": "1.69%"
            }
        }

        # When
        result = provider.get_quote('AAPL')

        # Then
        assert result['real_time_price'] == 150.25
        assert result['change'] == 2.50
        assert result['change_percent'] == "1.69%"
        mock_get_quote.assert_called_once_with('AAPL')

    @patch('API_request.providers.alphavantage.client.AlphaVantageClient.get_stock_quote')
    def test_get_quote_api_error(self, mock_get_quote, provider):
        """API 에러 처리"""
        # Given
        mock_get_quote.side_effect = Exception("API Error")

        # When/Then
        with pytest.raises(Exception):
            provider.get_quote('INVALID')
```

### 2. 통합 테스트 (Integration Tests)

```python
# tests/integration/test_stock_service.py

import pytest
from django.test import TestCase
from API_request.stock_service import StockService
from stocks.models import Stock


@pytest.mark.django_db
class TestStockServiceIntegration(TestCase):

    def setUp(self):
        self.service = StockService()

    def test_update_stock_data_creates_new_stock(self):
        """새 종목 생성 플로우"""
        # When
        stock = self.service.update_stock_data('AAPL')

        # Then
        assert stock.symbol == 'AAPL'
        assert stock.stock_name is not None
        assert Stock.objects.filter(symbol='AAPL').exists()

    def test_update_stock_data_updates_existing(self):
        """기존 종목 업데이트 플로우"""
        # Given
        existing = Stock.objects.create(symbol='AAPL', stock_name='Apple Inc.')

        # When
        updated = self.service.update_stock_data('AAPL')

        # Then
        assert updated.id == existing.id
        assert updated.last_updated > existing.created_at
```

### 3. Provider 비교 테스트

```python
# tests/integration/test_provider_consistency.py

import pytest
from API_request.providers.alphavantage.provider import AlphaVantageProvider
from API_request.providers.fmp.provider import FMPProvider


class TestProviderConsistency:
    """
    Alpha Vantage와 FMP 응답 일관성 검증
    """

    @pytest.fixture
    def av_provider(self):
        return AlphaVantageProvider(api_key='...')

    @pytest.fixture
    def fmp_provider(self):
        return FMPProvider(api_key='...')

    def test_quote_consistency(self, av_provider, fmp_provider):
        """실시간 주가 데이터 일관성 검증"""
        symbol = 'AAPL'

        # When
        av_result = av_provider.get_quote(symbol)
        fmp_result = fmp_provider.get_quote(symbol)

        # Then
        assert set(av_result.keys()) == set(fmp_result.keys()), "필드명이 일치해야 함"

        # 가격 차이 허용 범위 (실시간 데이터이므로 약간의 차이 가능)
        price_diff = abs(av_result['real_time_price'] - fmp_result['real_time_price'])
        assert price_diff < av_result['real_time_price'] * 0.01, "가격 차이 1% 이내"

    def test_company_profile_consistency(self, av_provider, fmp_provider):
        """회사 정보 일관성 검증"""
        symbol = 'AAPL'

        av_result = av_provider.get_company_profile(symbol)
        fmp_result = fmp_provider.get_company_profile(symbol)

        # 필수 필드 검증
        assert av_result['symbol'] == fmp_result['symbol']
        assert av_result['stock_name'] == fmp_result['stock_name']
        assert av_result['sector'] == fmp_result['sector']
```

### 4. Feature Flag 테스트

```python
# tests/unit/test_provider_factory.py

import pytest
from unittest.mock import patch
from API_request.provider_factory import ProviderFactory


class TestProviderFactory:

    def teardown_method(self):
        ProviderFactory.clear_cache()

    @patch('django.conf.settings.STOCK_DATA_PROVIDER', 'alphavantage')
    def test_get_default_provider_alphavantage(self):
        """기본 Provider: Alpha Vantage"""
        provider = ProviderFactory.get_provider()
        assert provider.get_provider_name() == 'AlphaVantage'

    @patch('django.conf.settings.STOCK_DATA_PROVIDER', 'fmp')
    def test_get_default_provider_fmp(self):
        """기본 Provider: FMP"""
        provider = ProviderFactory.get_provider()
        assert provider.get_provider_name() == 'FMP'

    @patch('django.conf.settings.PROVIDER_OVERRIDES', {'quote': 'fmp'})
    @patch('django.conf.settings.STOCK_DATA_PROVIDER', 'alphavantage')
    def test_endpoint_override(self):
        """엔드포인트별 오버라이드"""
        # 기본 Provider는 Alpha Vantage
        default_provider = ProviderFactory.get_provider()
        assert default_provider.get_provider_name() == 'AlphaVantage'

        # 'quote' 엔드포인트는 FMP 사용
        quote_provider = ProviderFactory.get_provider(endpoint='quote')
        assert quote_provider.get_provider_name() == 'FMP'
```

### 5. 성능 테스트 (Load Testing)

```python
# tests/performance/test_caching.py

import time
import pytest
from API_request.stock_service import StockService


class TestCachingPerformance:

    def test_cache_hit_improves_performance(self):
        """캐시 적중 시 성능 향상 확인"""
        service = StockService()
        symbol = 'AAPL'

        # 첫 호출 (캐시 미스)
        start = time.time()
        service.provider.get_quote(symbol)
        first_call_time = time.time() - start

        # 두 번째 호출 (캐시 히트)
        start = time.time()
        service.provider.get_quote(symbol)
        second_call_time = time.time() - start

        # 캐시 적중 시 최소 10배 빠름
        assert second_call_time < first_call_time * 0.1
```

### 테스트 커버리지 목표

| 계층 | 목표 커버리지 | 우선순위 |
|-----|--------------|---------|
| Provider 추상 클래스 | 100% | 높음 |
| Alpha Vantage Provider | 90% | 높음 |
| FMP Provider | 90% | 높음 |
| StockService | 85% | 높음 |
| ProviderFactory | 100% | 중간 |
| Cache Layer | 80% | 중간 |
| Circuit Breaker | 75% | 낮음 |

---

## 결론 및 권장사항

### 핵심 설계 결정

1. **추상화 우선**: `StockDataProvider` 인터페이스로 모든 Provider 통일
2. **외부 캐싱**: Provider 외부에서 Decorator 패턴으로 캐싱 적용
3. **Feature Flag**: 환경 변수 기반 엔드포인트별 전환 지원
4. **Fallback 지원**: Primary 실패 시 자동 Fallback (선택적)
5. **점진적 마이그레이션**: 위험도 낮은 엔드포인트부터 순차 전환

### 장점

- ✅ 기존 코드 변경 최소화 (Django 모델, 비즈니스 로직 유지)
- ✅ 테스트 용이성 (Mock Provider 주입 가능)
- ✅ 확장성 (새 Provider 추가 용이)
- ✅ 운영 안정성 (Fallback, Circuit Breaker)
- ✅ 성능 (통합 캐싱 레이어)

### 주의사항

1. **데이터 일관성**: Alpha Vantage와 FMP의 필드 매핑 정확히 검증 필요
2. **Rate Limit 관리**: 두 Provider의 제한이 다르므로 모니터링 필수
3. **비용**: FMP 유료 티어 전환 시 비용 검토 필요
4. **롤백 계획**: 각 Phase마다 롤백 가능한 상태 유지

### 다음 단계

1. @backend: FMP Client 및 Processor 구현
2. @qa: 통합 테스트 시나리오 작성
3. @infra: 환경 변수 설정 및 배포 스크립트 작성
4. 전체 팀: Phase 3 마이그레이션 모니터링 및 피드백

---

**작성자**: @qa-architect
**날짜**: 2025-12-08
**버전**: 1.0
