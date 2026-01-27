# CLAUDE.md - Stock-Vis

## 프로젝트 개요

**Stock-Vis**: AI 기반 투자 분석 플랫폼

- **Backend**: Django REST Framework + PostgreSQL
- **Frontend**: Next.js 14+ (TypeScript)
- **Async**: Celery + Redis
- **LLM**: Claude API (RAG 분석)

---

## 개발 환경 설정

### Backend

```bash
# 의존성 설치
poetry install

# 환경 변수 (.env 파일)
ALPHA_VANTAGE_API_KEY=your_key_here
FMP_API_KEY=your_fmp_key_here  # Market Movers용
DATABASE_URL=postgresql://user:password@localhost:5432/stock_vis

# 데이터베이스
createdb stock_vis
python manage.py migrate

# 서버 실행
python manage.py runserver
```

### Frontend

```bash
cd frontend
npm install
npm run dev        # 개발 서버
npm run build      # 프로덕션 빌드
```

### 비동기 작업 (Celery + Redis)

```bash
# Redis 시작
brew services start redis

# Celery Worker/Beat 실행
celery -A config worker -l info
celery -A config beat -l info
```

---

## 아키텍처

### 전체 구조

```
Frontend (Next.js) ──REST API──▶ Backend (Django)
                                      │
                    ┌─────────────────┼─────────────────┐
                    ▼                 ▼                 ▼
             Alpha Vantage      PostgreSQL        ML Models
               yfinance          (Data)           (예정)
```

### Backend 3계층 패턴

```
API Client → Processor → Service → Models/Views → REST API
```

- **Client**: 외부 API 통신 (Rate limiting, 에러 핸들링)
- **Processor**: 응답 데이터 변환 (snake_case 변환, 타입 처리)
- **Service**: 트랜잭션 관리, 데이터베이스 저장

### Django 앱 구조

| 앱 | 역할 | URL |
|----|------|-----|
| stocks | 주가, 재무제표 데이터 | `/api/v1/stocks/*` |
| users | 사용자, 포트폴리오 관리, Watchlist | `/api/v1/users/*` |
| analysis | 기술적 지표, 시장 분석 | `/api/v1/analysis/*` |
| macro | 거시경제 대시보드 (Market Pulse) | `/api/v1/macro/*` |
| **graph_analysis** | **그래프 온톨로지 상관관계 분석 (Phase 1)** | `/api/v1/graph/*` |
| rag_analysis | LLM 기반 분석 | `/api/v1/rag/*` |
| **serverless** | **Market Movers 지표 (AWS 전환 예정)** | `/api/v1/serverless/*` |

### 모델 관계

```
Stock (PK: symbol)
  ├── DailyPrice (FK: stock, unique: stock+date)
  ├── WeeklyPrice (FK: stock, unique: stock+date)
  ├── BalanceSheet (FK: stock, unique: stock+period_type+fiscal_year+fiscal_quarter)
  ├── IncomeStatement (FK: stock, unique: stock+period_type+fiscal_year+fiscal_quarter)
  └── CashFlowStatement (FK: stock, unique: stock+period_type+fiscal_year+fiscal_quarter)

User
  └── Watchlist (FK: user, unique: user+name)
        └── WatchlistItem (FK: watchlist+stock, unique: watchlist+stock)
              - target_entry_price: 목표 진입가
              - notes: 메모
              - position_order: 정렬 순서
```

---

## 주요 API 엔드포인트

### 주식 데이터

- `GET /api/v1/stocks/api/chart/<symbol>/` - 차트 데이터
- `GET /api/v1/stocks/api/overview/<symbol>/` - 기업 개요
- `GET /api/v1/stocks/api/balance-sheet/<symbol>/` - 재무상태표
- `GET /api/v1/stocks/api/income-statement/<symbol>/` - 손익계산서
- `GET /api/v1/stocks/api/cashflow/<symbol>/` - 현금흐름표
- `GET /api/v1/stocks/api/indicators/<symbol>/` - 기술적 지표

### Watchlist (관심종목)

- `GET /api/v1/users/watchlist/` - 관심종목 리스트 목록
- `POST /api/v1/users/watchlist/` - 관심종목 리스트 생성
- `GET /api/v1/users/watchlist/<id>/` - 관심종목 리스트 상세
- `PATCH /api/v1/users/watchlist/<id>/` - 관심종목 리스트 수정
- `DELETE /api/v1/users/watchlist/<id>/` - 관심종목 리스트 삭제
- `POST /api/v1/users/watchlist/<id>/add-stock/` - 종목 추가
- `GET /api/v1/users/watchlist/<id>/stocks/` - 종목 목록 + 실시간 가격
- `PATCH /api/v1/users/watchlist/<id>/stocks/<symbol>/` - 종목 설정 수정
- `DELETE /api/v1/users/watchlist/<id>/stocks/<symbol>/remove/` - 종목 제거

### Market Pulse (거시경제)

- `GET /api/v1/macro/pulse/` - 전체 대시보드
- `GET /api/v1/macro/fear-greed/` - 공포/탐욕 지수
- `GET /api/v1/macro/interest-rates/` - 금리/수익률 곡선
- `GET /api/v1/macro/global-markets/` - 글로벌 시장
- `POST /api/v1/macro/sync/` - 데이터 동기화 시작
- `GET /api/v1/macro/sync/status/` - 동기화 상태 확인

### Stock 동기화

- `POST /api/v1/stocks/api/sync/<symbol>/` - 수동 데이터 동기화
  - Body: `{"data_types": ["overview", "price"], "force": false}`
  - Response: `{"symbol": "AAPL", "status": "success", "synced": {...}}`
- `GET /api/v1/stocks/api/sync/<symbol>/` - 동기화 상태 조회
- API 응답에 `_meta` 필드 포함:
  ```json
  {"source": "db", "synced_at": "...", "freshness": "fresh", "can_sync": true}
  ```

### Market Movers (서버리스)

- `GET /api/v1/serverless/movers?type=gainers&date=2026-01-07` - Market Movers 조회 (키워드 포함)
  - Query Params:
    - `type`: 'gainers', 'losers', 'actives' (필수)
    - `date`: YYYY-MM-DD 형식 (선택, 기본값: 오늘)
  - Response: TOP 20 종목 + 5개 지표 + AI 키워드
    - **Phase 1 지표**: RVOL (거래량 배수), Trend Strength (추세 강도)
    - **Phase 2 지표**: Sector Alpha (섹터 초과수익), ETF Sync Rate (ETF 동행률), Volatility Percentile (변동성 백분위)
    - **Phase 2.5 키워드**: LLM 생성 3-5개 핵심 키워드 (예: ["AI 반도체 수요", "데이터센터 확장"])

---

## 코딩 규칙

### Backend

- 심볼 처리: `symbol.upper()` 필수
- 모델 조회: `get_object_or_404(Stock, symbol=symbol.upper())`
- Processor: 반드시 `return` 문 포함
- 기간 타입: `period_type='annual'` 또는 `'quarterly'`
- 가격 모델: `DailyPrice` 사용 (`HistoricalPrice` 없음)

### Frontend

- TypeScript strict mode
- 서버 상태: TanStack Query
- 클라이언트 상태: Zustand
- `'use client'` 필요한 컴포넌트만

### 비동기 (Celery)

- Rate limiting: Alpha Vantage 12초 간격
- 태스크 idempotent 구현
- 재시도: max_retries=3, exponential backoff

---

## 외부 API

### Alpha Vantage

- 무료 티어: 5 calls/분, 500 calls/일
- 요청 간 12초 대기 필수
- 응답: camelCase → Processor가 snake_case로 변환

### FMP (Financial Modeling Prep)

**Market Movers 전용 API**

- **플랜**: Starter Plan 사용
- **Rate Limit**: 10 calls/분, 250 calls/일
- **엔드포인트**: `/stable/*` 경로 사용 (Legacy `/api/v3/*` 더 이상 지원 안 함)
- **주요 API**:
  - `/stable/biggest-gainers` - 상승 TOP 종목
  - `/stable/biggest-losers` - 하락 TOP 종목
  - `/stable/most-actives` - 거래량 TOP 종목
  - `/stable/quote?symbol=AAPL` - 실시간 시세 (volume 포함)
  - `/stable/historical-price-eod/full?symbol=AAPL` - 히스토리 OHLCV
  - `/stable/profile?symbol=AAPL` - 기업 프로필 (섹터 정보)
- **캐싱**: Redis 5분~24시간 (엔드포인트별 상이)
- **섹터 ETF 매핑**:
  ```python
  SECTOR_ETF_MAP = {
      'Technology': 'XLK',
      'Financial Services': 'XLF',
      'Healthcare': 'XLV',
      'Consumer Cyclical': 'XLY',
      'Industrials': 'XLI',
      'Energy': 'XLE',
      # ... 총 11개 섹터
  }
  ```

### yfinance (Yahoo Finance)

**사용처**: Market Pulse (거시경제 지표), Corporate Action 감지

**특징**: 무료, Rate limit 없음

```python
# 주요 심볼
INDEX_SYMBOLS = {'^GSPC': 'S&P 500', '^DJI': 'Dow Jones', '^IXIC': 'NASDAQ'}
SECTOR_ETFS = {'XLK': 'Technology', 'XLF': 'Financials', ...}
COMMODITIES = {'GC=F': 'Gold', 'CL=F': 'Crude Oil', ...}
FOREX = {'EURUSD=X': 'EUR/USD', 'KRW=X': 'USD/KRW', ...}

# Corporate Action 데이터
ticker.splits      # 주식분할/역분할 이력
ticker.dividends   # 배당 이력
ticker.fast_info.last_price  # 현재 가격
```

**주의사항**:
- Lazy import 필수 (`import yfinance as yf` - 사용 시점에 import)
- `ticker.splits`, `ticker.dividends`는 pandas Series (`.items()` 메서드 사용)
- `split.date()`로 날짜 변환 (pandas Timestamp → Python date)
- 에러 발생 시 로깅만 하고 None 반환 (메인 플로우 중단 안 함)

---

## 캐싱 전략

| 데이터 타입 | TTL | 비고 |
|-----------|-----|------|
| 차트 데이터 | 60초 | 실시간성 중요 |
| Overview | 600초 | 가격 + 기본 정보 |
| 재무제표 | 3600초 | 분기/연간 업데이트 |
| 거시경제 지표 | 3600초 | FRED 데이터 |
| Watchlist 목록 | 300초 | 사용자별 캐시 키 |
| Watchlist 종목 | 60초 | 실시간 가격 포함 |
| **Market Movers 리스트** | **300초** | **FMP Gainers/Losers/Actives** |
| **FMP Quote** | **60초** | **실시간 시세** |
| **FMP Historical** | **3600초** | **OHLCV 히스토리** |
| **FMP Profile** | **86400초** | **섹터 정보 (24시간)** |

---

## 자주 발생하는 버그

1. Processor 메서드에서 return문 누락
2. `DailyPrice` 대신 `HistoricalPrice` 사용
3. 심볼에 `.upper()` 호출 누락
4. Alpha Vantage None/빈 값 처리 누락
5. N+1 쿼리 문제 (select_related/prefetch_related 미사용)
6. **SSE Async Loop 충돌**: Django ASGI(Daphne)에서 동기 뷰 내 `asyncio.new_event_loop()` 사용 시 연결 끊김
   - 증상: "Application instance took too long to shut down" 에러, 요청 pending
   - 해결: 비동기 이벤트를 먼저 수집 후 동기적으로 yield하거나, 완전한 async 뷰 사용
7. **FMP API volume 데이터 누락**: `/stable/biggest-gainers` 응답에 `volume` 필드 없음
   - 증상: RVOL이 0.00x로 계산됨
   - 해결: `item.get('volume')` 대신 `quote.get('volume')` 사용
   - 참고: Market Movers 엔드포인트는 volume 미제공, Quote API에서 별도 조회 필요
8. **Celery Worker에서 async LLM 호출 금지**
   - 증상: "Event loop is closed" 에러, LLM 호출 실패
   - 원인: Celery Worker는 자체 이벤트 루프를 관리, async 코드와 충돌
   - 해결: `genai.Client`의 동기 API 직접 사용 (async 대신)
   ```python
   # ❌ 잘못된 방법
   async def call_llm():
       return await async_client.generate(...)

   # ✅ 올바른 방법
   def call_llm():
       return sync_client.models.generate_content(...)
   ```
9. **LLM max_output_tokens 부족으로 JSON 잘림**
   - 증상: "Unterminated string" JSON 파싱 에러
   - 원인: 한국어 응답은 토큰 소비가 많아 출력이 중간에 잘림
   - 해결: max_output_tokens 충분히 설정 (800 → 1200) + regex 복구 로직
   ```python
   # JSON 잘림 복구
   pattern = r'"([^"]+)"'
   matches = re.findall(pattern, text)
   if len(matches) >= 2:
       return matches[:5]  # 부분 복구
   ```
10. **Celery 비동기 태스크 완료 전 onSuccess 호출**
    - 증상: mutation.onSuccess에서 데이터 재조회해도 결과 없음
    - 원인: onSuccess는 API 요청 완료 시점, Celery 태스크 완료 시점 아님
    - 해결: setTimeout으로 예상 완료 시간 후 재조회 또는 폴링
    ```typescript
    onSuccess: (data) => {
      const delayMs = stockCount * 6000; // 종목당 6초
      setTimeout(() => fetchKeywords(), delayMs);
    }
    ```
11. **프론트엔드 string[] vs Keyword[] 타입 불일치**
    - 증상: "Each child should have unique key" 또는 undefined 에러
    - 원인: API가 `string[]` 반환, 컴포넌트가 `Keyword[]` 기대
    - 해결: 정규화 함수로 타입 변환
    ```typescript
    function normalizeKeywords(keywords: string[] | Keyword[]): Keyword[] {
      if (typeof keywords[0] === 'string') {
        return keywords.map((text, i) => ({ id: `kw-${i}`, text, ... }));
      }
      return keywords;
    }
    ```
12. **React 컴포넌트 undefined props 접근**
    - 증상: "undefined is not an object (evaluating 'colors.bg')"
    - 원인: optional 필드가 undefined일 때 객체 속성 접근
    - 해결: 기본값 폴백 패턴 사용
    ```typescript
    const colors = CATEGORY_COLORS[keyword.category] || DEFAULT_COLORS;
    ```
13. **yfinance pandas Series 타입 불일치**
    - 증상: "AttributeError: 'Series' object has no attribute 'date'"
    - 원인: `ticker.splits`, `ticker.dividends`는 pandas Series (Timestamp 인덱스)
    - 해결: `.items()` 메서드로 반복, `timestamp.date()`로 변환
    ```python
    # ❌ 잘못된 방법
    for split_date in ticker.splits:
        date_obj = split_date.date()  # 에러!

    # ✅ 올바른 방법
    for split_timestamp, ratio in ticker.splits.items():
        date_obj = split_timestamp.date()
    ```

---

## Market Movers 5개 지표 시스템

### 지표 설명

| 지표 | 계산 방식 | 해석 | Phase |
|------|----------|------|-------|
| **RVOL** | 당일 거래량 / 20일 평균 | 2.0 이상: 비정상적 관심도<br>1.5~2.0: 높은 관심<br>1.0 미만: 평균 이하 | Phase 1 |
| **Trend Strength** | (종가-시가) / (고가-저가) | +0.7 이상: 강한 상승<br>-0.7 이하: 강한 하락<br>0 전후: 횡보 | Phase 1 |
| **Sector Alpha** | 종목 수익률 - 섹터 ETF 수익률 | 양수: 섹터 평균 초과<br>음수: 섹터 평균 미달 | Phase 2 |
| **ETF Sync Rate** | 피어슨 상관계수(종목, 섹터 ETF) | 0.8 이상: 강한 동조<br>0.5~0.8: 중간<br>0.5 미만: 독립적 움직임 | Phase 2 |
| **Volatility %ile** | 당일 변동성의 백분위 (0-100) | 90 이상: 매우 높은 변동성<br>50 전후: 평균<br>10 이하: 낮은 변동성 | Phase 2 |

### Market Movers 아키텍처

```
FMP API (/stable/*)
    │
    ├─ biggest-gainers ────┐
    ├─ biggest-losers ─────┤
    └─ most-actives ───────┤
                           │
                           ▼
              MarketMoversSync (data_sync.py)
                           │
        ┌──────────────────┼──────────────────┐
        ▼                  ▼                  ▼
    FMP Quote      FMP Historical      FMP Profile
    (volume)         (20일 OHLC)        (섹터 정보)
        │                  │                  │
        └──────────────────┴──────────────────┘
                           │
                           ▼
              IndicatorCalculator (순수 Python)
                           │
        ┌──────────────────┼──────────────────┐
        ▼                  ▼                  ▼
    Phase 1 지표      Phase 2 지표      Display 포맷
    (RVOL, Trend)   (Alpha, Sync, Vol)  (2.5x, ▲0.83 등)
        │                  │                  │
        └──────────────────┴──────────────────┘
                           │
                           ▼
                    PostgreSQL (MarketMover 모델)
                           │
                           ▼
                  REST API (/api/v1/serverless/movers)
                           │
                           ▼
                Frontend (MoverCard 컴포넌트)
```

### Celery Beat 스케줄

```python
CELERY_BEAT_SCHEDULE = {
    'sync-market-movers': {
        'task': 'serverless.tasks.sync_daily_market_movers',
        'schedule': crontab(hour=7, minute=30),  # 매일 07:30 EST
        'options': {'expires': 3600}  # 1시간 후 만료
    }
}
```

### Corporate Action 감지 시스템

**개요**: 가격 변동 ±50% 이상 시 주식분할/역분할/배당을 자동 감지

| 컴포넌트 | 역할 |
|---------|------|
| **CorporateActionService** | yfinance로 Corporate Action 감지 |
| **CorporateAction 모델** | 이벤트 이력 저장 |
| **MarketMover 필드** | has_corporate_action, corporate_action_type, corporate_action_display |

**감지 조건**:
- **주식분할**: ratio < 1 (예: 0.5 → 2:1 분할)
- **역분할**: ratio > 1 (예: 28.0 → 1:28 역분할)
- **특별배당**: 배당 수익률 5% 이상
- **LOOKBACK_DAYS**: 최근 7일 이내 이벤트만 체크

**예시 (GRI Bio 역분할)**:
```json
{
  "symbol": "GRI",
  "change_percent": 2772.0,
  "has_corporate_action": true,
  "corporate_action_type": "reverse_split",
  "corporate_action_display": "1:28 역분할"
}
```

**테스트**: `tests/serverless/test_corporate_action_service.py` (12개 테스트)

---

## AI 키워드 생성 시스템 (Phase 2.5)

### 개요

Market Movers 및 Screener 종목에 대해 LLM 기반 핵심 키워드를 생성하는 시스템.
Gemini 2.5 Flash 사용, Celery 비동기 파이프라인으로 처리.

### 아키텍처

```
프론트엔드 (AI 키워드 버튼)
        │
        ▼
REST API (trigger_keyword_generation)
        │
        ▼
Celery 파이프라인 (collect → generate → save)
        │
        ├─ KeywordDataCollector (뉴스 수집)
        │     ├─ Marketaux API (우선)
        │     └─ Finnhub API (폴백)
        │
        └─ KeywordGenerationService (LLM 호출)
              └─ Gemini 2.5 Flash (동기 API)
        │
        ▼
StockKeyword 모델 (PostgreSQL)
        │
        ▼
프론트엔드 (KeywordList 컴포넌트)
```

### API 엔드포인트

```bash
# Market Movers용
POST /api/v1/serverless/keywords/generate-all
     Body: {"type": "gainers", "date": "2026-01-26"}

# Screener용
POST /api/v1/serverless/keywords/generate-screener
     Body: {"stocks": [{"symbol": "AAPL", "company_name": "...", "sector": "..."}]}

# 키워드 조회
GET  /api/v1/serverless/keywords/<symbol>?date=2026-01-26
POST /api/v1/serverless/keywords/batch
     Body: {"symbols": ["AAPL", "MSFT"], "date": "2026-01-26"}
```

### StockKeyword 모델

```python
{
    symbol: CharField(max_length=10),
    date: DateField,
    company_name: CharField,
    keywords: JSONField,  # ["AI 수요 증가", "실적 호조", "목표가 상향"]
    status: CharField,    # 'pending', 'completed', 'failed'
    error_message: TextField,
    llm_model: CharField,  # 'gemini-2.5-flash'
    generation_time_ms: IntegerField,
    prompt_tokens: IntegerField,
    completion_tokens: IntegerField,
    expires_at: DateTimeField  # 7일 후 만료
}
```

### LLM 프롬프트 설계

```python
SYSTEM_PROMPT = """
규칙:
- 정확히 3개 키워드만 반환
- 각 키워드는 15자 이내로 짧게
- 반드시 완전한 JSON 배열 형식

예시: ["AI 수요 증가", "실적 호조", "목표가 상향"]
"""
```

### 폴백 키워드

LLM 호출 실패 시 기본 키워드 사용:
```python
FALLBACK_KEYWORDS = {
    'gainers': ["급등", "거래량 증가", "모멘텀"],
    'losers': ["급락", "매도 압력", "조정"],
    'actives': ["거래량 급증", "변동성", "투자자 관심"],
    'screener': ["분석 대상", "투자 검토", "모니터링"],
}
```

### Rate Limit 대응

| Provider | Rate Limit | 대응 |
|----------|------------|------|
| Marketaux | 100/일, 15분 간격 | 5초 이상 대기 시 Finnhub 폴백 |
| Finnhub | 60/분, 1초 간격 | 기본 폴백 provider |
| Gemini Free | 15 RPM, 1500 RPD | 지수 백오프 재시도 |

### 프론트엔드 컴포넌트

- **KeywordTag**: 개별 키워드 태그 (색상, 툴팁)
- **KeywordList**: 키워드 목록 (로딩, 에러, 빈 상태 처리)
- **normalizeKeywords()**: string[] → Keyword[] 변환

### 성능 지표

- 종목당 키워드 생성: 약 6초
- 50개 종목 배치: 약 5분
- max_output_tokens: 1200 (한국어 지원)

### 테스트 커버리지

- **파일**: `tests/serverless/test_indicators.py`
- **테스트 수**: 21개
- **커버리지**: 100% (21/21 passed)
- **테스트 대상**:
  - Phase 1 지표 계산 (6개)
  - Phase 2 지표 계산 (9개)
  - Display 포맷터 (5개)
  - Edge cases (데이터 부족, 0 나누기 등)

---

## Graph Analysis (그래프 온톨로지) - Phase 1

### 개요

주식 간 가격 변동 상관관계를 그래프 네트워크로 분석하는 시스템. 사용자 Watchlist의 종목들을 노드로, 상관계수를 엣지로 표현하여 실시간 모니터링.

### 핵심 개념

| 개념 | 설명 | 기술 |
|------|------|------|
| **Node** | Watchlist 내 각 종목 | Stock 모델 |
| **Edge** | 두 종목 간 상관계수 | CorrelationEdge 모델 |
| **Correlation** | 3개월 가격 변동 상관성 | Pearson correlation (pandas) |
| **Anomaly** | ±0.2 이상 상관계수 변화 | AnomalyDetector |
| **Graph** | NetworkX 네트워크 그래프 | NetworkX library |

### 계산 파라미터

```python
DEFAULT_PERIOD_DAYS = 90  # 3개월 rolling window
MIN_DATA_POINTS = 20  # 최소 20일 데이터 필요
ANOMALY_THRESHOLD = 0.2  # ±0.2 변화 감지
MAX_ALERTS_PER_DAY = 5  # 일일 최대 알림 5개
COOLDOWN_HOURS = 24  # 동일 페어 24시간 쿨다운
```

### 데이터베이스 모델

**CorrelationMatrix** - 전체 상관계수 행렬
```python
{
    watchlist: FK(Watchlist),
    date: DateField,
    matrix_data: JSONField,  # {AAPL: {MSFT: 0.85, GOOGL: 0.72}}
    stock_count: Integer,
    calculation_period: Integer (default: 90)
}
```

**CorrelationEdge** - 개별 상관관계
```python
{
    watchlist: FK(Watchlist),
    stock_a: FK(Stock),
    stock_b: FK(Stock),
    date: DateField,
    correlation: Decimal(-1.0 ~ 1.0),
    previous_correlation: Decimal,
    correlation_change: Decimal,
    is_anomaly: Boolean
}
```

**CorrelationAnomaly** - 이상 패턴
```python
{
    watchlist: FK(Watchlist),
    edge: FK(CorrelationEdge),
    date: DateField,
    anomaly_type: Choice('divergence', 'convergence', 'reversal'),
    previous_correlation: Decimal,
    current_correlation: Decimal,
    change_magnitude: Decimal,
    alerted: Boolean,
    dismissed: Boolean
}
```

**PriceCache** - 가격 데이터 캐싱
```python
{
    stock: FK(Stock),
    date: DateField,
    prices: JSONField,  # 90일 가격 [{date, close}]
    period_days: Integer (default: 90)
}
```

**GraphMetadata** - 계산 메타데이터
```python
{
    watchlist: FK(Watchlist),
    date: DateField,
    stock_count: Integer,
    edge_count: Integer,
    anomaly_count: Integer,
    calculation_time_ms: Integer,
    status: Choice('pending', 'processing', 'completed', 'failed')
}
```

### Services

**CorrelationCalculator** (`graph_analysis/services/correlation_calculator.py`)
- 3개월 rolling correlation 계산
- NetworkX 그래프 생성
- 가격 데이터 캐싱 (PostgreSQL + Redis)
- 평균 계산 시간: < 100ms (50개 종목)

```python
from graph_analysis.services import CorrelationCalculator

# Usage
calculator = CorrelationCalculator(watchlist, period_days=90)
matrix = calculator.calculate_correlation_matrix()
graph = calculator.build_network_graph()
```

**AnomalyDetector** (`graph_analysis/services/anomaly_detector.py`)
- ±0.2 변화 감지
- 3가지 anomaly 타입 분류:
  - **Divergence**: 상관계수 약화
  - **Convergence**: 상관계수 강화
  - **Reversal**: 부호 변경 (positive ↔ negative)
- 24시간 쿨다운 로직
- 일일 최대 5개 알림

```python
from graph_analysis.services import AnomalyDetector

# Usage
detector = AnomalyDetector(watchlist, detection_date=today)
anomalies = detector.detect_anomalies()
pending_alerts = detector.get_pending_alerts()
```

### API 엔드포인트 (예정)

```bash
GET  /api/v1/graph/{watchlist_id}/correlation-matrix/  # 상관계수 행렬
GET  /api/v1/graph/{watchlist_id}/anomalies/           # 이상 패턴
GET  /api/v1/graph/{watchlist_id}/network/             # NetworkX 그래프 (JSON)
POST /api/v1/graph/{watchlist_id}/calculate/           # 수동 계산 트리거
```

### Celery 태스크 (예정)

```python
# config/celery.py 스케줄 추가
from celery.schedules import crontab

CELERYBEAT_SCHEDULE = {
    'compute-daily-correlations': {
        'task': 'graph_analysis.tasks.compute_all_correlations',
        'schedule': crontab(hour=16, minute=15),  # 16:15 ET (장 종료 후)
        'options': {'expires': 3600}
    }
}
```

### 상관계수 해석

| 값 | 강도 | 의미 |
|----|------|------|
| 0.8 ~ 1.0 | Very Strong | 거의 동일한 움직임 |
| 0.6 ~ 0.8 | Strong | 강한 동조 |
| 0.4 ~ 0.6 | Moderate | 중간 수준 관련성 |
| 0.2 ~ 0.4 | Weak | 약한 관련성 |
| -0.2 ~ 0.2 | Very Weak | 관련성 없음 |
| -0.4 ~ -0.2 | Weak Negative | 약한 역관계 |
| -1.0 ~ -0.4 | Negative | 역관계 |

### Phase 1 목표 (6주)

- ✅ Week 1-2: PostgreSQL 스키마, Django 모델, migrations
- ✅ Week 1-2: NetworkX 상관계수 계산 엔진
- ⏳ Week 3-4: REST API 엔드포인트, Frontend 그래프 시각화 (D3.js)
- ⏳ Week 5-6: 이상 감지 알림, 테스트 작성 (단위/통합)

### 외부 API

**EODHD Historical Data** (`api_request/eodhd_client.py`)
- Bulk EOD API: 5,000+ US 종목 일괄 다운로드
- Cost: $19.99/월 (Basic Plan)
- No rate limits
- CSV (GZIP) 포맷
- 30초~2분 (bulk download)

```python
from api_request.eodhd_client import EODHDClient

client = EODHDClient()
# Bulk download all US stocks
bulk_data = client.get_bulk_eod_data(exchange='US', date=today)
# Returns: [{symbol, date, open, high, low, close, volume}, ...]
```

### 참고 문서

- Phase 1 설계: `docs/GRAPH_ONTOLOGY_INFRA_REDESIGN.md`
- 데이터 인프라 평가: `docs/DATA_INFRASTRUCTURE_ROADMAP_EVALUATION.md`

---

## 멀티에이전트 시스템

### 에이전트 담당 영역

| 에이전트 | 담당 영역 |
|---------|----------|
| @backend | stocks/, users/, analysis/, API_request/, **serverless/** |
| @frontend | frontend/ 전체 |
| @rag-llm | rag_analysis/ 전체 |
| @infra | */tasks.py, */consumers.py, config/, docker/ |
| @qa | tests/, docs/ |
| @investment-advisor | 투자 도메인 콘텐츠 |

**참고**: serverless/ 앱은 백엔드 에이전트가 담당하지만, AWS Lambda 전환 시 인프라 에이전트와 협업 필요

### 워크플로우

1. Orchestrator가 작업 분배 미리보기 제공
2. 사용자 확인 후 에이전트 순차 호출
3. 에이전트 완료/도움 요청 시 사용자가 조율

---

## RAG Analysis (AI 분석) - Phase 3

### 파이프라인 버전

| 버전 | 설명 | API 파라미터 |
|------|------|-------------|
| lite | 기존 바구니 기반 | `?pipeline=lite` |
| v2 | RAG 기반 (Entity + Hybrid Search) | `?pipeline=v2` |
| **final** | **Phase 3 통합 (권장)** | `?pipeline=final` |

### AnalysisPipelineFinal 스테이지

| Stage | 컴포넌트 | 역할 |
|-------|---------|------|
| 0 | Semantic Cache | 유사 질문 캐시 (SIMILARITY=0.85) |
| 1 | Complexity Classifier | 질문 복잡도 분류 |
| 2 | Token Budget Manager | 토큰 예산 할당 |
| 3 | Adaptive LLM | 복잡도 기반 모델 선택 |
| 4 | Cost Tracker | 비용 추적 및 로깅 |

### 복잡도별 설정

| 복잡도 | max_tokens | context 예산 |
|--------|------------|-------------|
| simple | 800 | 400 |
| moderate | 1500 | 800 |
| complex | 2500 | 1500 |

### 모니터링 API

```bash
GET /api/v1/rag/monitoring/usage/?hours=24   # 사용량 통계
GET /api/v1/rag/monitoring/cost/             # 비용 요약
GET /api/v1/rag/monitoring/cache/            # 캐시 통계
```

---

## 구현 완료 기능

- ✅ JWT 인증 시스템
- ✅ 포트폴리오 CRUD
- ✅ 기술적 지표 (RSI, MACD, Bollinger Bands 등)
- ✅ Alpha Vantage API 통합
- ✅ WebSocket 실시간 통신
- ✅ Celery 비동기 태스크
- ✅ Redis 캐싱
- ✅ 차트 UX (Nice Numbers, 색상 테마, 반응형)
- ✅ Market Pulse 거시경제 대시보드
- ✅ yfinance 글로벌 시장 데이터
- ✅ Watchlist 관심종목 관리 (목표가, 메모, 실시간 가격)
- ✅ RAG Analysis Phase 3 (Semantic Cache, Cost Optimization)
- ✅ **Market Movers (Phase 1 + Phase 2 + Phase 2.5 + Phase 2.6)**
  - ✅ **5개 지표 시스템**: RVOL, Trend Strength, Sector Alpha, ETF Sync Rate, Volatility Percentile
  - ✅ **FMP API 통합**: Gainers/Losers/Actives TOP 20
  - ✅ **Celery Beat 스케줄**: 매일 07:30 EST 자동 동기화
  - ✅ **유닛 테스트**: 21개 테스트 (100% 통과)
  - ✅ **AI 키워드 생성 (Phase 2.5)**: Gemini 2.5 Flash 기반 3개 핵심 키워드
  - ✅ **Corporate Action 감지 (Phase 2.6)**: yfinance 기반 주식분할/역분할/배당 자동 감지
  - ⏳ **Phase 3: AWS Lambda 전환** (보류)
- ✅ **AI 키워드 시스템**
  - ✅ **Backend**: StockKeyword 모델, KeywordGenerationService, Celery 파이프라인
  - ✅ **Frontend**: KeywordTag/KeywordList 컴포넌트, Market Movers/Screener 통합
  - ✅ **Rate Limit 대응**: Marketaux → Finnhub 폴백, Gemini 지수 백오프
  - ✅ **JSON 복구**: 잘린 LLM 응답 regex 복구
- ✅ **Graph Analysis (Phase 1 Week 1-2)**
  - ✅ **PostgreSQL 스키마**: CorrelationMatrix, CorrelationEdge, CorrelationAnomaly, PriceCache, GraphMetadata
  - ✅ **NetworkX 상관계수 계산 엔진**: 3개월 rolling window, ±0.2 anomaly detection
  - ✅ **EODHD API Client**: Bulk EOD data download (5,000+ US stocks)
  - ✅ **Services**: CorrelationCalculator, AnomalyDetector
  - ⏳ **REST API 엔드포인트**: Week 3-4 예정
  - ⏳ **Frontend 그래프 시각화 (D3.js)**: Week 3-4 예정
- ✅ **Stock Auto Sync System**
  - ✅ **자동 저장**: 외부 API 응답 DB 자동 저장 (StockSyncService)
  - ✅ **Rate Limiter**: Redis 기반 FMP/Alpha Vantage 호출 제한
  - ✅ **_meta 응답**: 데이터 소스/신선도/동기화 시간 정보 포함
  - ✅ **Frontend 훅**: useStockData (TanStack Query), useDataSync
  - ✅ **공통 컴포넌트**: DataLoadingState, DataSourceBadge, CorporateActionBadge
- ⏳ ML/DL 모델 통합

---

## 로깅

- 로그 파일: `stocks.log`
- 사용법: `logger = logging.getLogger(__name__)`
