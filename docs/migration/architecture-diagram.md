# FMP Migration Architecture Diagram

## 전체 시스템 아키텍처

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           Django Application Layer                          │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                     stocks/views.py (API Endpoints)                  │   │
│  │  - /api/v1/stocks/api/chart/<symbol>/                               │   │
│  │  - /api/v1/stocks/api/overview/<symbol>/                            │   │
│  │  - /api/v1/stocks/api/balance-sheet/<symbol>/                       │   │
│  └───────────────────────────────┬─────────────────────────────────────┘   │
│                                  │                                          │
│                                  ▼                                          │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                    API_request/stock_service.py                      │   │
│  │                     (Provider-Agnostic Service)                      │   │
│  │                                                                      │   │
│  │  + update_stock_data(symbol)                                        │   │
│  │  + update_historical_prices(symbol, days)                           │   │
│  │  + update_financial_statements(symbol)                              │   │
│  │  - _call_with_fallback(method, endpoint)                            │   │
│  └───────────────────────────────┬─────────────────────────────────────┘   │
│                                  │                                          │
│                                  ▼                                          │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │              API_request/provider_factory.py (Factory)               │   │
│  │                                                                      │   │
│  │  + get_provider(endpoint) → StockDataProvider                       │   │
│  │  + get_fallback_provider() → StockDataProvider                      │   │
│  │                                                                      │   │
│  │  Feature Flag 읽기:                                                 │   │
│  │   - STOCK_DATA_PROVIDER                                             │   │
│  │   - PROVIDER_OVERRIDES[endpoint]                                    │   │
│  │   - FALLBACK_PROVIDER                                               │   │
│  └───────┬─────────────────────────────────────────┬───────────────────┘   │
│          │                                         │                        │
│          ▼                                         ▼                        │
│  ┌──────────────────────────────┐       ┌──────────────────────────────┐   │
│  │  AlphaVantageProvider        │       │  FMPProvider                 │   │
│  │  (StockDataProvider 구현)    │       │  (StockDataProvider 구현)    │   │
│  │                              │       │                              │   │
│  │  @cached_provider_call       │       │  @cached_provider_call       │   │
│  │  + get_quote(symbol)         │       │  + get_quote(symbol)         │   │
│  │  + get_company_profile(...)  │       │  + get_company_profile(...)  │   │
│  │  + get_historical_daily(...) │       │  + get_historical_daily(...) │   │
│  │  + get_balance_sheet(...)    │       │  + get_balance_sheet(...)    │   │
│  └────────┬─────────────────────┘       └────────┬─────────────────────┘   │
│           │                                      │                         │
│           ▼                                      ▼                         │
│  ┌──────────────────────────────┐       ┌──────────────────────────────┐   │
│  │  AlphaVantageClient          │       │  FMPClient                   │   │
│  │  (HTTP 클라이언트)           │       │  (HTTP 클라이언트)           │   │
│  │                              │       │                              │   │
│  │  - _make_request(params)     │       │  - _make_request(endpoint)   │   │
│  │  - Rate Limiting (12초)      │       │  - Rate Limiting (1초)       │   │
│  │  + get_stock_quote(symbol)   │       │  + get_quote(symbol)         │   │
│  └────────┬─────────────────────┘       └────────┬─────────────────────┘   │
│           │                                      │                         │
│           ▼                                      ▼                         │
│  ┌──────────────────────────────┐       ┌──────────────────────────────┐   │
│  │  AlphaVantageProcessor       │       │  FMPProcessor                │   │
│  │  (데이터 변환)               │       │  (데이터 변환)               │   │
│  │                              │       │                              │   │
│  │  + process_stock_quote(...)  │       │  + process_quote(...)        │   │
│  │  + process_company_overview()│       │  + process_company_profile() │   │
│  │  + process_balance_sheet()   │       │  + process_balance_sheet()   │   │
│  │  - _safe_decimal(value)      │       │  - _safe_decimal(value)      │   │
│  └──────────────────────────────┘       └──────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘
                    │                                      │
                    ▼                                      ▼
        ┌────────────────────────┐           ┌────────────────────────┐
        │  Alpha Vantage API     │           │  FMP API               │
        │  https://www.alpha...  │           │  https://fmp.com/api/  │
        └────────────────────────┘           └────────────────────────┘
```

## 추상화 레이어 상세

```
┌────────────────────────────────────────────────────────────────────────┐
│                      StockDataProvider (추상 클래스)                    │
│                                                                        │
│  << interface >>                                                       │
│  + get_quote(symbol: str) → Dict[str, Any]                            │
│  + get_company_profile(symbol: str) → Dict[str, Any]                  │
│  + get_historical_daily(symbol, start, end, limit) → List[Dict]       │
│  + get_historical_weekly(symbol, start, limit) → List[Dict]           │
│  + get_balance_sheet(symbol, period, limit) → List[Dict]              │
│  + get_income_statement(symbol, period, limit) → List[Dict]           │
│  + get_cash_flow(symbol, period, limit) → List[Dict]                  │
│  + search_stocks(keywords: str) → List[Dict]                          │
│  + get_provider_name() → str                                          │
│  + get_rate_limit_info() → Dict[str, Any]                             │
└────────────────────────────────────────────────────────────────────────┘
                    ▲                                ▲
                    │                                │
                    │ implements                     │ implements
                    │                                │
        ┌───────────┴──────────┐         ┌──────────┴──────────┐
        │                      │         │                     │
┌───────────────────────┐  ┌──────────────────────┐  ┌──────────────────┐
│ AlphaVantageProvider  │  │   FMPProvider        │  │  Future Provider │
│                       │  │                      │  │  (확장 가능)     │
│ - client: AVClient    │  │ - client: FMPClient  │  │                  │
│ - processor: AVProc   │  │ - processor: FMPProc │  │  + ...           │
└───────────────────────┘  └──────────────────────┘  └──────────────────┘
```

## 캐싱 레이어 아키텍처

```
┌─────────────────────────────────────────────────────────────────────┐
│                         Cache Decorator                             │
│                    @cached_provider_call(timeout=300)               │
│                                                                     │
│  1. 캐시 키 생성: "alphavantage:get_quote:AAPL:abc123def"          │
│  2. Redis 조회: cache.get(key)                                     │
│  3. Cache Hit? → 즉시 반환                                         │
│  4. Cache Miss? → Provider 호출                                    │
│  5. 결과 캐싱: cache.set(key, result, timeout)                     │
│  6. 결과 반환                                                      │
└───────────────────────────┬─────────────────────────────────────────┘
                            │
                            ▼
        ┌──────────────────────────────────────────────┐
        │         RedisStockCache                      │
        │         (StockDataCache 구현)                │
        │                                              │
        │  + get(key) → Optional[Any]                  │
        │  + set(key, value, timeout)                  │
        │  + delete(key)                               │
        │  + clear()                                   │
        │  + generate_key(provider, method, args) → str│
        └──────────────────┬───────────────────────────┘
                           │
                           ▼
        ┌──────────────────────────────────────────────┐
        │          Django Cache Framework              │
        │          (Backend: Redis)                    │
        │                                              │
        │  CACHES = {                                  │
        │    'default': {                              │
        │      'BACKEND': 'django...RedisCache',       │
        │      'LOCATION': 'redis://127.0.0.1:6379/1' │
        │    }                                         │
        │  }                                           │
        └──────────────────┬───────────────────────────┘
                           │
                           ▼
                    ┌─────────────┐
                    │    Redis    │
                    │  (Port 6379)│
                    └─────────────┘
```

## Feature Flag 전환 메커니즘

```
                         사용자 요청
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    ProviderFactory.get_provider(endpoint)       │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
                ┌─────────────────────────┐
                │ endpoint 파라미터 있음? │
                └────────┬────────────────┘
                         │
                  Yes ◄──┴──► No
                   │            │
                   ▼            ▼
    ┌──────────────────────┐   ┌──────────────────────────┐
    │ PROVIDER_OVERRIDES   │   │ STOCK_DATA_PROVIDER      │
    │ [endpoint] 확인      │   │ (기본 Provider)          │
    └──────────┬───────────┘   └────────┬─────────────────┘
               │                        │
               └────────┬───────────────┘
                        ▼
            ┌────────────────────────┐
            │ Provider 이름 확인      │
            │ "alphavantage" or "fmp"│
            └────────┬───────────────┘
                     │
         ┌───────────┴───────────┐
         │                       │
         ▼                       ▼
┌─────────────────┐     ┌─────────────────┐
│ AlphaVantage    │     │ FMP             │
│ Provider 인스턴스│     │ Provider 인스턴스│
└─────────────────┘     └─────────────────┘

Example:
  endpoint='quote', PROVIDER_OVERRIDES={'quote': 'fmp'}
  → FMPProvider 반환

  endpoint='balance_sheet', STOCK_DATA_PROVIDER='alphavantage'
  → AlphaVantageProvider 반환
```

## Fallback 메커니즘

```
                      API 호출 시작
                           │
                           ▼
        ┌──────────────────────────────────────┐
        │  Primary Provider 선택               │
        │  (ProviderFactory.get_provider())    │
        └──────────────┬───────────────────────┘
                       │
                       ▼
        ┌──────────────────────────────────────┐
        │  Primary Provider 호출               │
        │  provider.get_quote('AAPL')          │
        └──────────────┬───────────────────────┘
                       │
             ┌─────────┴─────────┐
             │                   │
        성공  │                   │  실패
             ▼                   ▼
    ┌─────────────┐      ┌──────────────────────────┐
    │  결과 반환  │      │  Exception 종류 확인     │
    └─────────────┘      └──────────┬───────────────┘
                                    │
                ┌───────────────────┼───────────────────┐
                │                   │                   │
                ▼                   ▼                   ▼
        ProviderNotFound    ProviderAPIError    ProviderRateLimit
        (종목 없음)         (API 에러)          (Rate Limit 초과)
                │                   │                   │
                │                   └─────────┬─────────┘
                │                             │
                ▼                             ▼
        ┌─────────────┐          ┌────────────────────────────┐
        │ 즉시 예외   │          │ Fallback 활성화 여부 확인  │
        │ 발생 (재시도│          │ ENABLE_PROVIDER_FALLBACK   │
        │ 하지 않음)  │          └────────────┬───────────────┘
        └─────────────┘                       │
                                    ┌─────────┴─────────┐
                                    │                   │
                              Enabled                Disabled
                                    │                   │
                                    ▼                   ▼
                    ┌───────────────────────┐   ┌─────────────┐
                    │ Fallback Provider 호출│   │ 예외 발생   │
                    │ (예: AlphaVantage)    │   └─────────────┘
                    └───────────┬───────────┘
                                │
                      ┌─────────┴─────────┐
                      │                   │
                 성공  │                   │  실패
                      ▼                   ▼
              ┌─────────────┐     ┌─────────────┐
              │  결과 반환  │     │ 최종 예외   │
              │ (Fallback OK)│    │  발생       │
              └─────────────┘     └─────────────┘

Fallback 조건:
  ✓ ProviderAPIError (API 호출 실패)
  ✓ ProviderRateLimitError (Rate Limit 초과)
  ✓ ProviderDataFormatError (응답 형식 오류)

Fallback 제외:
  ✗ ProviderNotFoundError (종목이 존재하지 않음)
  ✗ AuthenticationError (API 키 오류)
```

## 데이터 플로우 (예시: 실시간 주가 조회)

```
1. 사용자 요청
   GET /api/v1/stocks/api/overview/AAPL/

2. Django View
   stocks/views.py:StockOverviewAPIView
   │
   └─→ service = StockService()
       stock_data = service.update_stock_data('AAPL')

3. StockService
   API_request/stock_service.py
   │
   ├─→ provider = ProviderFactory.get_provider(endpoint='company_profile')
   │   # Feature Flag 확인: PROVIDER_COMPANY_PROFILE=fmp
   │   # → FMPProvider 반환
   │
   └─→ profile_data = self._call_with_fallback('get_company_profile', 'AAPL')

4. Cache Check
   @cached_provider_call(timeout=600)
   │
   ├─→ Cache Key: "fmp:get_company_profile:AAPL:abc123"
   ├─→ Redis.get(key)
   │
   └─→ Cache Miss → Provider 호출 계속

5. FMPProvider
   providers/fmp/provider.py
   │
   ├─→ raw_data = self.client.get_company_profile('AAPL')
   │   # HTTP GET: https://fmp.com/api/v3/profile/AAPL
   │
   └─→ return self.processor.process_company_profile(raw_data)

6. FMPClient
   providers/fmp/client.py
   │
   ├─→ Rate Limiting 체크 (1초 간격)
   ├─→ requests.get(url, params={'apikey': API_KEY})
   └─→ return response.json()

7. FMPProcessor
   providers/fmp/processor.py
   │
   └─→ {
         'symbol': 'AAPL',
         'stock_name': 'Apple Inc.',
         'sector': 'Technology',
         'market_capitalization': 2500000000000,
         ...
       }

8. Cache Save
   cache.set(key, result, timeout=600)

9. StockService - DB 저장
   Stock.objects.update_or_create(
     symbol='AAPL',
     defaults=profile_data
   )

10. Response
    {
      "symbol": "AAPL",
      "stock_name": "Apple Inc.",
      "real_time_price": 178.45,
      ...
    }
```

## 점진적 마이그레이션 단계별 다이어그램

### Phase 1: Alpha Vantage Only (현재)

```
View → AlphaVantageService → AlphaVantageClient → Alpha Vantage API
                            → AlphaVantageProcessor
```

### Phase 2: 추상화 레이어 구축 (Week 1)

```
View → StockService → ProviderFactory → AlphaVantageProvider → AV API
                                      → FMPProvider (구현 중)
```

### Phase 3: 부분 전환 (Week 3-4)

```
                    ┌→ AlphaVantageProvider (quote, daily) → AV API
View → StockService─┤
                    └→ FMPProvider (search, profile, financial) → FMP API
```

### Phase 4: 완전 전환 (Week 5)

```
View → StockService → ProviderFactory → FMPProvider → FMP API
                                      → AlphaVantageProvider (Fallback)
```

### Phase 5: 레거시 제거 (Week 6)

```
View → StockService → ProviderFactory → FMPProvider → FMP API
```

---

**Created**: 2025-12-08
**Author**: @qa-architect
**Purpose**: Visual reference for FMP migration architecture
