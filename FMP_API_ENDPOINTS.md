# FMP API 엔드포인트 목록

## Fundamentals API (기업 펀더멘털 데이터)

### 1. 핵심 재무 지표
- **URL**: `GET /api/v1/stocks/api/fundamentals/key-metrics/{symbol}/`
- **Query Parameters**:
  - `period`: 'annual' (연간, 기본값) 또는 'quarter' (분기)
  - `limit`: 반환할 기간 수 (기본값: 5, 최대: 40)
- **Response**: P/E, P/B, ROE, ROA, Debt/Equity 등

### 2. 재무 비율
- **URL**: `GET /api/v1/stocks/api/fundamentals/ratios/{symbol}/`
- **Query Parameters**:
  - `period`: 'annual' (연간, 기본값) 또는 'quarter' (분기)
  - `limit`: 반환할 기간 수 (기본값: 5, 최대: 40)
- **Response**: 유동비율, 당좌비율, 부채비율 등

### 3. DCF 분석
- **URL**: `GET /api/v1/stocks/api/fundamentals/dcf/{symbol}/`
- **Response**: 적정 주가, 현재가 대비 할인/프리미엄 등

### 4. 투자 등급
- **URL**: `GET /api/v1/stocks/api/fundamentals/rating/{symbol}/`
- **Response**: Buy/Sell/Hold 등급, 점수

### 5. 전체 펀더멘털 데이터 (한 번에 조회)
- **URL**: `GET /api/v1/stocks/api/fundamentals/all/{symbol}/`
- **Query Parameters**:
  - `period`: 'annual' (연간, 기본값) 또는 'quarter' (분기)
- **Response**: key_metrics, ratios, dcf, rating 전체

---

## Stock Screener API (조건별 종목 검색)

### 1. 조건별 종목 검색
- **URL**: `GET /api/v1/stocks/api/screener/`
- **Query Parameters**:
  - `market_cap_more_than`: 최소 시가총액 (USD)
  - `market_cap_lower_than`: 최대 시가총액 (USD)
  - `price_more_than`: 최소 주가 (USD)
  - `price_lower_than`: 최대 주가 (USD)
  - `beta_more_than`: 최소 베타
  - `beta_lower_than`: 최대 베타
  - `volume_more_than`: 최소 거래량
  - `volume_lower_than`: 최대 거래량
  - `dividend_more_than`: 최소 배당률 (%)
  - `dividend_lower_than`: 최대 배당률 (%)
  - `is_etf`: ETF 여부 (true/false)
  - `is_actively_trading`: 활성 거래 종목만 (true/false, 기본값: true)
  - `sector`: 섹터 필터 (예: Technology, Healthcare)
  - `industry`: 산업 필터
  - `exchange`: 거래소 필터 (NYSE, NASDAQ, AMEX 등)
  - `limit`: 반환할 종목 수 (기본값: 100, 최대: 1000)

### 2. 대형주 스크리너
- **URL**: `GET /api/v1/stocks/api/screener/large-cap/`
- **Query Parameters**:
  - `limit`: 반환할 종목 수 (기본값: 50)
- **필터**: 시가총액 100억 달러 이상

### 3. 고배당주 스크리너
- **URL**: `GET /api/v1/stocks/api/screener/high-dividend/`
- **Query Parameters**:
  - `min_dividend`: 최소 배당률 (%, 기본값: 3.0)
  - `limit`: 반환할 종목 수 (기본값: 50)

### 4. 섹터별 종목 스크리너
- **URL**: `GET /api/v1/stocks/api/screener/sector/{sector}/`
- **Path Parameters**:
  - `sector`: 섹터명 (예: Technology, Healthcare, Financials)
- **Query Parameters**:
  - `limit`: 반환할 종목 수 (기본값: 100)

### 5. 저변동성 종목 스크리너
- **URL**: `GET /api/v1/stocks/api/screener/low-beta/`
- **Query Parameters**:
  - `max_beta`: 최대 베타 (기본값: 0.8)
  - `limit`: 반환할 종목 수 (기본값: 50)

### 6. 거래소별 종목 스크리너
- **URL**: `GET /api/v1/stocks/api/screener/exchange/{exchange}/`
- **Path Parameters**:
  - `exchange`: 거래소 코드 (NYSE, NASDAQ, AMEX 등)
- **Query Parameters**:
  - `limit`: 반환할 종목 수 (기본값: 100)

---

## Exchange Quotes API (실시간 시세)

### 1. 주요 지수 시세
- **URL**: `GET /api/v1/stocks/api/quotes/index/`
- **Response**: 주요 지수 리스트 (S&P 500, NASDAQ, Dow Jones 등)

### 2. 개별 종목 실시간 시세
- **URL**: `GET /api/v1/stocks/api/quotes/{symbol}/`
- **Response**: 가격, 변동률, 거래량, 시가총액 등

### 3. 여러 종목 일괄 시세 조회
- **URL**: `POST /api/v1/stocks/api/quotes/batch/`
- **Request Body**:
  ```json
  {
    "symbols": ["AAPL", "MSFT", "GOOGL"]
  }
  ```
- **Response**: 여러 종목 시세 리스트 (최대 100개)

### 4. 주요 3대 지수
- **URL**: `GET /api/v1/stocks/api/quotes/major-indices/`
- **Response**: S&P 500, NASDAQ, Dow Jones 시세

### 5. 섹터 성과
- **URL**: `GET /api/v1/stocks/api/quotes/sector-performance/`
- **Response**: 섹터 ETF 시세 리스트 (XLK, XLF, XLV 등)

---

## 캐싱 전략

| API 유형 | TTL | 비고 |
|----------|-----|------|
| Fundamentals (Key Metrics, Ratios, DCF, Rating) | 600초 (10분) | 재무 데이터는 자주 변경되지 않음 |
| Stock Screener | 300초 (5분) | 검색 조건별 캐싱 |
| Exchange Quotes | 60초 (1분) | 실시간 시세 데이터 |

---

## 인증

- 모든 엔드포인트는 `IsAuthenticated` 권한 필요
- JWT 토큰을 Header에 포함: `Authorization: Bearer <token>`

---

## 에러 응답 형식

```json
{
  "error": "에러 메시지"
}
```

**HTTP Status Codes**:
- `400`: Bad Request (파라미터 오류)
- `404`: Not Found (데이터 없음)
- `503`: Service Unavailable (외부 API 오류)

---

## 성공 응답 형식

```json
{
  "success": true,
  "data": { ... },
  "meta": {
    "symbol": "AAPL",
    "timestamp": "2025-12-17T10:30:00"
  }
}
```
