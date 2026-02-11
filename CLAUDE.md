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

### ETF Holdings (Chain Sight Phase 3)

- `GET /api/v1/serverless/etf/status` - ETF 수집 상태 조회
  - Query Params: `tier` (선택, 'sector' 또는 'theme')
- `POST /api/v1/serverless/etf/sync` - ETF Holdings 동기화
  - Body: `{"etf_symbol": "XLK"}` (선택, 없으면 전체)
- `POST /api/v1/serverless/etf/resolve-url` - 실패한 ETF URL 자동 복구
  - Body: `{"etf_symbol": "XLK"}` (선택, 없으면 전체 실패 ETF)
- `GET /api/v1/serverless/etf/<symbol>/holdings` - 특정 ETF Holdings
- `GET /api/v1/serverless/etf/stock/<symbol>/themes` - 종목의 테마 조회
- `GET /api/v1/serverless/etf/stock/<symbol>/peers` - ETF 동반 종목 조회
- `GET /api/v1/serverless/themes` - 전체 테마 목록
- `GET /api/v1/serverless/themes/<theme_id>/stocks` - 테마별 종목 조회
- `POST /api/v1/serverless/themes/refresh` - 테마 매치 갱신

### Supply Chain (Chain Sight Phase 4)

- `GET /api/v1/serverless/chain-sight/stock/<symbol>/supply-chain` - 공급망 조회
  - Response: `{"suppliers": [...], "customers": [...], "cached": true}`
- `POST /api/v1/serverless/chain-sight/stock/<symbol>/sync-supply-chain` - 공급망 동기화 트리거
  - Response: `{"status": "success", "customer_count": 2, "supplier_count": 1}`
- `GET /api/v1/serverless/chain-sight/stock/<symbol>/category/suppliers` - 공급사 카테고리
- `GET /api/v1/serverless/chain-sight/stock/<symbol>/category/customers` - 고객사 카테고리

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
  - `/stable/company-screener` - 종목 스크리닝 (market_cap, volume 등)
  - `/stable/key-metrics-ttm?symbol=AAPL` - 펀더멘탈 지표 (PE, ROE 등)
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
| **FMP Company Screener** | **300초** | **종목 스크리닝 결과** |
| **FMP Key Metrics TTM** | **3600초** | **펀더멘탈 지표 (PE/ROE)** |

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
14. **FMP Key Metrics TTM API 필드명 불일치**
    - 증상: Enhanced 스크리너에서 PE, ROE가 항상 None
    - 원인: FMP API 필드명이 직관적이지 않음
      - `peRatioTTM` 필드 존재 안 함 → `earningsYieldTTM` 사용 (역수 계산)
      - `roeTTM` 존재 안 함 → `returnOnEquityTTM` 사용 (decimal, 1.5 = 150%)
    - 해결: 정확한 필드명 사용 + 값 변환
    ```python
    # ❌ 잘못된 방법
    pe_ratio = m.get('peRatioTTM')  # None!
    roe = m.get('roeTTM')  # None!

    # ✅ 올바른 방법
    earnings_yield = m.get('earningsYieldTTM')
    pe_ratio = round(1 / earnings_yield, 2) if earnings_yield > 0 else None

    roe_decimal = m.get('returnOnEquityTTM')
    roe_percent = round(roe_decimal * 100, 2) if roe_decimal else None
    ```
    - 참고: FMP API 문서가 불완전하므로 실제 응답 확인 필수
15. **Market Movers 캐시 키 불일치**
    - 증상: 업데이트 버튼 클릭 후에도 데이터가 빈 배열로 반환됨
    - 원인: `sync_now`에서 `movers:{date}:{type}` 키를 삭제하지만, `market_movers_api`는 `movers_with_keywords:{date}:{type}` 키를 사용
    - 해결: `sync_now`에서 올바른 캐시 키 삭제
    ```python
    # ❌ 잘못된 방법 (캐시 키 불일치)
    cache_key = f'movers:{today}:{mover_type}'
    cache.delete(cache_key)

    # ✅ 올바른 방법 (API와 동일한 키 패턴)
    cache_key = f'movers_with_keywords:{today}:{mover_type}'
    cache.delete(cache_key)
    cache.delete(f'movers:{today}:{mover_type}')  # 하위 호환
    ```
    - 참고: 캐시 키 패턴은 읽기/쓰기/삭제 모두 일치해야 함
16. **ETF CSV 다운로드 실패 (SPDR XLSX)**
    - 증상: SPDR ETF (XLK, XLV 등) CSV 파싱 실패, 0개 holdings
    - 원인: SPDR은 CSV가 아닌 XLSX 형식 반환
    - 해결: openpyxl로 XLSX 파싱, Content-Type 자동 감지
    ```python
    # XLSX 감지 및 파싱
    if content[:4] == b'PK\x03\x04':  # ZIP 시그니처 = XLSX
        return self._parse_xlsx(content, parser_type, etf_symbol)
    ```
17. **ETF XLSX iter_rows 소비 문제**
    - 증상: XLSX 파싱 시 0개 holdings 반환
    - 원인: `ws.iter_rows()`는 제너레이터, 헤더 검색 시 소비됨
    - 해결: `list(ws.iter_rows(values_only=True))`로 미리 변환
    ```python
    # ❌ 잘못된 방법
    for row in ws.iter_rows():  # 제너레이터 소비
        if 'Ticker' in row: break
    for row in ws.iter_rows():  # 이미 소비됨!

    # ✅ 올바른 방법
    all_rows = list(ws.iter_rows(values_only=True))
    for row in all_rows:
        # 안전하게 반복 가능
    ```
18. **ETF Holdings 중복 키 제약 위반**
    - 증상: "duplicate key value violates unique constraint" (ICLN 등)
    - 원인: 동일 종목이 CSV에 2회 등장 (다른 클래스)
    - 해결: 중복 ticker 감지 후 weight 합산
    ```python
    seen = {}
    for h in holdings:
        if h['symbol'] in seen:
            seen[h['symbol']]['weight'] += h['weight']
        else:
            seen[h['symbol']] = h
    ```
19. **프론트엔드 API URL 중복 (/api/v1/api/v1)**
    - 증상: ETF 동기화 등 API 호출 시 404 에러
    - 원인: `.env`에 `NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1` 설정되어 있는데, 코드에서 `${API_BASE}/api/v1/...` 사용
    - 해결: 코드에서 중복 `/api/v1` 제거
    ```typescript
    // ❌ 잘못된 방법 (URL 중복)
    const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
    const url = `${API_BASE}/api/v1/serverless/etf/sync`;
    // 결과: http://localhost:8000/api/v1/api/v1/serverless/etf/sync

    // ✅ 올바른 방법
    const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';
    const url = `${API_BASE}/serverless/etf/sync`;
    // 결과: http://localhost:8000/api/v1/serverless/etf/sync
    ```
    - 참고: `.env` 파일과 코드의 URL 패턴 일관성 확인 필수

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
    },
    'sync-etf-holdings': {
        'task': 'serverless.tasks.sync_etf_holdings',
        'schedule': crontab(hour=6, minute=0, day_of_week=1),  # 매주 월요일 06:00 EST
        'options': {'expires': 3600}  # 1시간 후 만료
        # 실패 시 이메일 알림: goid545@naver.com, jinie545@gmail.com
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

## News-based Stock Insights (뉴스 기반 종목 인사이트)

### 개요

뉴스에서 언급된 종목을 팩트(사실) 중심으로 정리하여 보여주는 시스템.
"추천", "점수" 같은 주관적 표현 대신 뉴스 언급 횟수, 감성 분포, 시장 데이터를 표시.

### 핵심 원칙

| 제거 | 보여줄 것 |
|------|----------|
| 추천 점수, Score | 뉴스 언급 횟수 |
| 강한 추천, 약한 추천 | 감성 분포 (긍정/부정/중립) |
| 주관적 판단 | 키워드별 뉴스 헤드라인 |
| - | 시장 데이터 (52주 범위, MA, 밸류에이션) |

### 아키텍처

```
NewsEntity (PostgreSQL)
        │
        ▼
NewsBasedStockInsights (Service)
        │
        ├─ 뉴스 언급 수집 (symbol별)
        ├─ 감성 분포 계산 (positive/negative/neutral)
        ├─ 키워드 매칭 (DailyKeyword 연결)
        └─ 시장 데이터 조회 (Stock 모델)
        │
        ▼
REST API (/api/v1/news/insights/)
        │
        ▼
Frontend Components
        ├─ NewsHighlightedStocks (컨테이너)
        ├─ StockInsightCard (개별 종목)
        ├─ SentimentBar (감성 분포 차트)
        ├─ KeywordMentionList (키워드 + 뉴스)
        └─ MarketDataBadge (시장 데이터)
```

### API 엔드포인트

```bash
GET /api/v1/news/insights/?date=2026-02-06&limit=10&include_market_data=true
```

**응답 예시**:
```json
{
  "date": "2026-02-06",
  "insights": [
    {
      "symbol": "NVDA",
      "company_name": "NVIDIA Corporation",
      "total_news_count": 5,
      "sentiment_distribution": {
        "positive": 3,
        "negative": 1,
        "neutral": 1,
        "total": 5
      },
      "keyword_mentions": [
        {
          "keyword": "AI 투자 확대",
          "sentiment": "positive",
          "news_headline": "NVIDIA AI chip revenue surges 220%",
          "news_source": "Marketaux",
          "published_at": "2026-02-06T10:30:00Z"
        }
      ],
      "market_data": {
        "price_position": {
          "current_price": 856.50,
          "week_52_high": 974.00,
          "week_52_low": 473.20,
          "distance_from_52w_high": -12.1,
          "distance_from_52w_low": 81.0
        },
        "valuation": {
          "pe_ratio": 65.2,
          "roe": 123.5,
          "analyst_upside": 15.3
        },
        "analyst_ratings": {
          "buy": 45,
          "hold": 8,
          "sell": 2
        }
      }
    }
  ],
  "total_keywords": 12,
  "computation_time_ms": 45
}
```

### 주요 파일

| 파일 | 역할 |
|------|------|
| `news/services/stock_insights.py` | 팩트 기반 인사이트 서비스 |
| `news/api/views.py` | `/insights/` 엔드포인트 |
| `frontend/types/news.ts` | StockInsight, SentimentDistribution 타입 |
| `frontend/components/news/NewsHighlightedStocks.tsx` | 인사이트 컨테이너 |
| `frontend/components/news/StockInsightCard.tsx` | 개별 종목 카드 |
| `frontend/components/news/SentimentBar.tsx` | 감성 분포 바 |
| `frontend/components/news/MarketDataBadge.tsx` | 시장 데이터 배지 |

### 용어 변경

| 기존 | 변경 |
|------|------|
| AI 추천 종목 | 뉴스 언급 종목 |
| StockRecommendations | NewsHighlightedStocks |
| RecommendationCard | StockInsightCard |
| 추천 점수 | (제거) |

---

## Chain Sight DNA (연관 종목 발견) - Phase 2.2

### 개요

스크리너 결과에서 연관 종목을 발견하는 시스템. 3가지 방식으로 관련 종목을 찾아 투자 아이디어를 확장합니다.

### 연관 종목 발견 방식

| 방식 | 설명 | 알고리즘 |
|------|------|----------|
| **섹터 피어** | 같은 섹터의 유사 종목 | 동일 섹터 + 펀더멘탈 유사도 계산 |
| **펀더멘탈 유사** | PER, ROE, 시가총액 유사 | 평균 메트릭 ±20% 범위 |
| **AI 인사이트** | LLM 기반 관계 설명 (옵션) | Gemini 2.5 Flash (예정) |

### API 엔드포인트

```bash
POST /api/v1/serverless/screener/chain-sight
{
    "symbols": ["AAPL", "MSFT", "NVDA"],
    "filters": {
        "market_cap_min": 1000000000,
        "pe_ratio_max": 30,
        "roe_min": 20
    },
    "limit": 10,
    "use_ai": false
}
```

### 응답 형식

```json
{
    "success": true,
    "data": {
        "sector_peers": [
            {
                "symbol": "GOOGL",
                "company_name": "Alphabet Inc.",
                "reason": "동일 Technology 섹터 유사 기업",
                "similarity": 0.85,
                "metrics": {
                    "sector": "Technology",
                    "pe": 28.0,
                    "roe": 25.0,
                    "market_cap": 1800000000000
                }
            }
        ],
        "fundamental_similar": [...],
        "ai_insights": "이 종목들은 AI 반도체 수요 증가의 수혜 기업입니다...",
        "chains_count": 10,
        "metadata": {
            "original_count": 3,
            "filters": {...},
            "computation_time_ms": 150,
            "use_ai": false
        }
    }
}
```

### 유사도 계산 로직

**펀더멘탈 유사도** (0.0 ~ 1.0):
- PER 유사도: `1 - abs(stock_pe - avg_pe) / avg_pe`
- ROE 유사도: `1 - abs(stock_roe - avg_roe) / avg_roe`
- 시가총액 유사도: `1 - abs(stock_mc - avg_mc) / avg_mc`
- 이익률 유사도: `1 - abs(stock_pm - avg_pm) / avg_pm`
- **최종 유사도**: 4개 지표 평균

**임계값**:
- 섹터 피어: 유사도 순으로 정렬 (제한 없음)
- 펀더멘탈 유사: 유사도 0.5 이상만 반환

### 캐싱 전략

- **Cache Key**: 종목 심볼 + 필터 조건 해시
- **TTL**: 1시간
- **효과**: 동일 조건 재조회 시 즉시 반환

### 테스트 커버리지

- **파일**: `tests/serverless/test_chain_sight_service.py`
- **테스트 수**: 13개
- **커버리지**: 100% (13/13 passed, 1 skipped)
- **테스트 대상**:
  - 평균 메트릭 계산 (3개)
  - 펀더멘탈 유사도 계산 (4개)
  - 캐시 키 생성 (2개)
  - 빈 결과 처리 (1개)
  - 섹터 피어 유사도 (1개)
  - AI 인사이트 생성 (2개)

### FMP API 사용

| 엔드포인트 | 용도 | 캐시 TTL |
|----------|------|----------|
| `/stable/company-screener` | 섹터별 종목 조회 | 5분 |
| `/stable/profile` | 종목 프로필 (섹터/산업) | 24시간 |

### 성능 지표

- 평균 처리 시간: 150ms (캐시 미스 시)
- 최대 연관 종목 수: 각 카테고리별 5개 (기본)
- 최대 원본 종목 수: 50개

---

## Chain Sight Phase 3: ETF Holdings 자동화

### 개요

ETF Holdings 기반 테마 관계를 자동 수집하여 "숨겨진 보석" 중소형주 발견을 지원하는 시스템.
운용사 공식 CSV/XLSX에서 직접 다운로드하여 비용 $0.

### ETF 자동화 현황

| Tier | 자동화 | 수동 필요 | 총 |
|------|--------|----------|-----|
| Tier 1 (섹터) | 11개 | 0개 | 11개 |
| Tier 2 (테마) | 4개 | 6개 | 10개 |
| **합계** | **15개** | **6개** | **21개** |

### 운용사별 파서

| 운용사 | 파서 | 형식 | ETF 예시 |
|--------|------|------|---------|
| State Street (SPDR) | `spdr` | XLSX | XLK, XLV, XLF 등 |
| iShares | `ishares` | CSV | SOXX |
| GlobalX | `globalx` | CSV | BOTZ, LIT |
| ARK Invest | `ark` | CSV | ARKK, ARKG (수동) |
| Invesco | `invesco` | CSV | TAN, KWEB (수동) |

### 수동 수집이 필요한 ETF

| ETF | 이유 | 운용사 링크 |
|-----|------|------------|
| ARKK, ARKG | Cloudflare 차단 | [ark-funds.com](https://ark-funds.com) |
| TAN, KWEB | 403 Forbidden | [invesco.com](https://www.invesco.com/us/financial-products/etfs/) |
| HACK | 서버 연결 실패 | - |
| BETZ | PDF만 제공 | - |

### 수동 수집 명령어

```bash
# ARK ETF 수동 임포트
python manage.py import_etf_csv ARKK /path/to/ARKK_holdings.csv --parser ark

# iShares ETF 수동 임포트
python manage.py import_etf_csv TAN /path/to/TAN_holdings.csv --parser ishares

# 파서 자동 감지
python manage.py import_etf_csv KWEB /path/to/holdings.csv --parser auto
```

### Celery 자동화 스케줄

| 태스크 | 스케줄 | 설명 |
|--------|--------|------|
| `sync_etf_holdings` | 매주 월요일 06:00 EST | 전체 ETF 자동 수집 |
| `send_etf_sync_failure_email` | 수집 후 | 실패 목록 이메일 발송 |

**이메일 수신자**: goid545@naver.com, jinie545@gmail.com

### Chain Sight 전용 페이지

**URL**: `/chain-sight`

| 기능 | 설명 |
|------|------|
| 전체 수집 | 모든 ETF Holdings 한 번에 수집 |
| URL 복구 | 실패한 ETF의 CSV URL 자동 복구 |
| 개별 수집 | ETF별 개별 수집 버튼 |
| 상태 대시보드 | 전체/완료/대기/실패 통계 |
| 수동 수집 안내 | ARKK 등 수동 필요 ETF 가이드 |

### 주요 파일

| 파일 | 역할 |
|------|------|
| `serverless/services/etf_csv_downloader.py` | CSV/XLSX 다운로드 및 파싱 |
| `serverless/tasks.py` | Celery 태스크 (sync_etf_holdings) |
| `serverless/management/commands/import_etf_csv.py` | 수동 임포트 커맨드 |
| `frontend/app/chain-sight/page.tsx` | Chain Sight 전용 페이지 |
| `frontend/components/chain-sight/ETFCollectionPanel.tsx` | 수집 UI 컴포넌트 |

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

- Phase 1 설계: `docs/architecture/GRAPH_ONTOLOGY_INFRA_REDESIGN.md`
- 데이터 인프라 평가: `docs/architecture/DATA_INFRASTRUCTURE_ROADMAP_EVALUATION.md`

---

## Investment Thesis Builder (Phase 2.3)

### 개요

스크리너 결과를 바탕으로 LLM이 투자 테제를 자동 생성하는 시스템.
Gemini 2.5 Flash 사용, 동기 API 호출 (Celery 호환).

### 아키텍처

```
스크리너 결과 (종목 + 필터)
        │
        ▼
ThesisBuilder (서비스)
        │
        ├─ Prompt 구성 (System + User)
        │     - 필터 조건 → 투자 기준 변환
        │     - 종목 데이터 요약
        │
        ├─ Gemini 2.5 Flash 호출 (동기)
        │     - MAX_TOKENS: 2000
        │     - TEMPERATURE: 0.5
        │
        └─ 응답 파싱 (JSON)
              - title, summary, key_metrics
              - top_picks, risks, rationale
        │
        ▼
InvestmentThesis 모델 (PostgreSQL)
        │
        ├─ share_code 자동 생성 (8자 UUID)
        ├─ generation_time_ms 기록
        └─ view_count, save_count 추적
        │
        ▼
REST API (/api/v1/serverless/thesis/*)
```

### InvestmentThesis 모델

```python
{
    user: FK(User),  # nullable
    title: CharField(200),  # "저평가 고수익 기술주"
    summary: TextField,  # 1-2문장 요약
    filters_snapshot: JSONField,  # 적용된 필터
    preset_ids: JSONField,  # 사용된 프리셋 IDs
    key_metrics: JSONField,  # ["PER < 15", "ROE > 20%"]
    top_picks: JSONField,  # ["AAPL", "MSFT", ...]
    risks: JSONField,  # ["금리 상승 리스크", ...]
    rationale: TextField,  # 투자 근거 상세
    llm_model: CharField(50),  # "gemini-2.5-flash"
    generation_time_ms: IntegerField,
    is_public: BooleanField,
    share_code: CharField(20, unique=True),  # 공유 URL용
    view_count: IntegerField,
    save_count: IntegerField,
}
```

### API 엔드포인트

```bash
# 테제 생성
POST /api/v1/serverless/thesis/generate
     Body: {"stocks": [...], "filters": {...}, "user_notes": "", "preset_ids": []}
     Response: InvestmentThesis 객체

# 테제 조회
GET  /api/v1/serverless/thesis/{thesis_id}
     Response: InvestmentThesis 객체 (view_count +1)

# 내 테제 목록
GET  /api/v1/serverless/thesis?limit=10
     Response: {"count": 5, "theses": [...]}

# 공유 테제 조회
GET  /api/v1/serverless/thesis/shared/{share_code}
     Response: InvestmentThesis 객체 (is_public 확인)
```

### LLM 프롬프트 설계

**System Prompt**:
- 역할: 전문 투자 분석가
- 작성 원칙: 간결성, 구체성, 균형 (리스크 포함), 실행 가능성
- 출력 형식: JSON (title, summary, key_metrics, top_picks, risks, rationale)

**User Prompt**:
- 적용된 필터 조건 (읽기 쉬운 형태로 포맷팅)
- 선별된 종목 (최대 20개 표시)
  - symbol, company_name, sector
  - 주요 지표: PER, ROE, Market Cap, Change %
- 사용자 추가 메모 (선택)

### 폴백 전략

LLM 호출 실패 시 `create_fallback_thesis()` 함수 사용:
- title: "스크리너 결과 분석"
- summary: 종목 수 표시, 필터 검토 권장
- key_metrics: 필터 조건을 문자열로 변환
- top_picks: 상위 5개 종목
- risks: ["자동 생성 실패로 기본 테제 생성됨"]
- llm_model: "fallback"

### 비용 추정

- 시스템 프롬프트: 1800 토큰
- 필터당 입력: 30 토큰
- 종목당 입력: 50 토큰 (최대 20개)
- 출력: 800 토큰
- **총 토큰**: 약 3600 토큰 (50개 종목 기준)
- **비용**: ~$0.005 USD/테제

### 특징

- **동기 API 호출**: `client.models.generate_content()` (async 없음, Celery 호환)
- **share_code 자동 생성**: 8자 UUID (예: "A3F8K2J9")
- **조회수 추적**: view_count 자동 증가
- **비공개 테제**: is_public=False 시 소유자만 조회 가능
- **JSON 파싱 복구**: 응답 파싱 실패 시 폴백 테제 생성

### 사용 예시

```python
from serverless.services.thesis_builder import ThesisBuilder

# 테제 생성
builder = ThesisBuilder(language='ko')
thesis = builder.build_thesis(
    stocks=[
        {'symbol': 'AAPL', 'company_name': 'Apple Inc.', 'pe_ratio': 28, 'roe': 147, ...},
        # ... more stocks
    ],
    filters={'pe_max': 20, 'roe_min': 15, 'sector': 'Technology'},
    user=request.user,
    user_notes="AI 관련 종목 선호"
)

print(thesis.title)  # "저평가 고수익 기술주"
print(thesis.share_code)  # "A3F8K2J9"
print(thesis.top_picks)  # ["AAPL", "MSFT", "GOOGL", "META", "NVDA"]
```

---

## Enhanced Screener Service (Phase 2.4)

### 개요

FMP API가 직접 지원하지 않는 펀더멘탈 필터(PE, ROE, EPS Growth 등)를 위해
2단계 필터링을 수행하는 서비스.

### 문제 해결

**문제**: 프리셋 "시총>0.5B, EPS>20" 선택 시 "시가총액>1B"만 적용됨
- FMP `/stable/company-screener`가 PE/ROE/EPS Growth 필터 미지원
- 응답에 펀더멘탈 필드 자체가 없음

**해결**: 2단계 필터링 + 온디맨드 API 호출
1. FMP 스크리너로 1차 필터링 (market_cap, volume 등)
2. FMP `/stable/key-metrics-ttm`으로 펀더멘탈 데이터 조회
3. 클라이언트 사이드 2차 필터링

### 프리셋 타입 분리

| 타입 | 설명 | 필터 예시 |
|------|------|----------|
| **instant** | FMP 직접 지원 | market_cap, volume, sector, dividend |
| **enhanced** | 추가 API 필요 | PE, ROE, EPS Growth, D/E Ratio |

### FMP Key Metrics TTM API 필드 매핑

```python
# ⚠️ 주의: FMP API 필드명이 직관적이지 않음!
# PE Ratio: earningsYieldTTM의 역수 (1 / earningsYieldTTM)
# ROE: returnOnEquityTTM (decimal, 1.5 = 150%)

FMP_METRICS_FIELD_MAP = {
    'pe_ratio': 'earningsYieldTTM',      # 역수 계산 필요!
    'roe': 'returnOnEquityTTM',          # * 100 변환 필요
    'roa': 'returnOnAssetsTTM',          # * 100 변환 필요
    'current_ratio': 'currentRatioTTM',
    'debt_equity': 'debtToEquityTTM',
    'profit_margin': 'netProfitMarginTTM',  # * 100 변환 필요
}
```

### 변환 로직

```python
# PE Ratio: 1 / earningsYield
earnings_yield = m.get('earningsYieldTTM')
pe_ratio = round(1 / earnings_yield, 2) if earnings_yield > 0 else None

# ROE: decimal → percentage (1.5994 → 159.94%)
roe_decimal = m.get('returnOnEquityTTM')
roe_percent = round(roe_decimal * 100, 2) if roe_decimal else None
```

### API 엔드포인트

```bash
# Enhanced 필터 자동 감지
GET /api/v1/serverless/screener/?market_cap_min=1e9&pe_ratio_max=20&roe_min=15

# 응답
{
  "results": [...],
  "count": 5,
  "is_enhanced": true,
  "filters_applied": {
    "fmp": ["marketCapMoreThan"],
    "enhanced": ["pe_ratio_max", "roe_min"],
    "client": []
  }
}
```

### 테스트 커버리지

- **파일**: `tests/serverless/test_enhanced_screener_service.py`
- **테스트 수**: 14개
- **커버리지**: 100%

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
- ✅ **Screener Upgrade (Phase 2)**
  - ✅ **Phase 2.1: 프리셋 공유 시스템**: share_code 기반 URL 공유, 트렌딩 프리셋, 복사 기능
  - ✅ **Phase 2.2: Chain Sight DNA**: 연관 종목 발견 (섹터 피어, 펀더멘탈 유사, AI 인사이트)
  - ✅ **Phase 2.3: 투자 테제 빌더**: LLM 기반 투자 논리 자동 생성, 공유 코드, 폴백 전략
  - ✅ **Phase 2.4: 프리셋-필터 완벽 동기화**: 2단계 필터링, Enhanced 프리셋 타입, FMP Key Metrics TTM
- ✅ **Chain Sight Stock (개별 종목 연관 탐색)**
  - ✅ **모델**: StockRelationship (PEER_OF, SAME_INDUSTRY, CO_MENTIONED), CategoryCache
  - ✅ **서비스**: RelationshipService, CategoryGenerator, ChainSightStockService
  - ✅ **API 엔드포인트**: `/chain-sight/stock/{symbol}`, `/chain-sight/stock/{symbol}/category/{id}`
  - ✅ **Frontend**: ChainSightExplorer, CategorySelector, RelatedStockGrid, AIInsightPanel
  - ✅ **Celery 태스크**: 일일 관계 동기화 (05:00 EST), 캐시 정리 (06:00 EST)
- ✅ **Chain Sight Phase 3: ETF Holdings**
  - ✅ **모델**: ETFProfile, ETFHolding, ThemeMatch
  - ✅ **서비스**: ETFCSVDownloader, ThemeMatchingService
  - ✅ **ETF Tier 시스템**: Tier 1 (섹터 ETF 11개), Tier 2 (테마 ETF 10개)
  - ✅ **테마 매칭**: Tier A (high), Tier B (medium), Tier B+ 승격 로직
  - ✅ **API 엔드포인트**: `/etf/status`, `/etf/sync`, `/etf/resolve-url`, `/themes`, `/themes/{id}/stocks`
  - ✅ **Neo4j 확장**: ETF, Theme 노드, HELD_BY, HAS_THEME 관계
  - ✅ **Frontend**: ETFCollectionPanel, Chain Sight 전용 페이지 (`/chain-sight`)
  - ✅ **자동 수집**: 15/21 ETF (SPDR, iShares, GlobalX)
  - ✅ **XLSX 파싱**: openpyxl로 SPDR XLSX 자동 변환
  - ✅ **Celery Beat 스케줄**: 매주 월요일 06:00 EST 자동 수집
  - ✅ **이메일 알림**: 실패 ETF 목록 자동 발송 (goid545@naver.com, jinie545@gmail.com)
  - ✅ **수동 수집 커맨드**: `python manage.py import_etf_csv {SYMBOL} /path/to/holdings.csv`
  - ✅ **수동 필요 ETF**: ARKK, ARKG (Cloudflare), TAN, KWEB (403), HACK, BETZ (PDF)
  - ✅ **유닛 테스트**: 58개 테스트 (100% 통과)
- ✅ **Chain Sight Neo4j 온톨로지**
  - ✅ **Neo4jChainSightService**: 노드/관계 CRUD, N-depth 그래프 탐색
  - ✅ **Neo4j 우선, PostgreSQL fallback**: ChainSightStockService에서 하이브리드 조회
  - ✅ **그래프 API**: `/chain-sight/graph/{symbol}`, `/chain-sight/graph/stats`
  - ✅ **마이그레이션 커맨드**: `python manage.py migrate_chain_sight_to_neo4j --all`
  - ✅ **유닛 테스트**: 19개 테스트 (18 passed, 1 skipped)
- ✅ **Chain Sight Phase 4: Supply Chain (공급망)**
  - ✅ **SEC EDGAR Client**: CIK 조회, 10-K 다운로드, Item 1A 추출 (`api_request/sec_edgar_client.py`)
  - ✅ **Supply Chain Parser**: Regex 패턴 기반 고객/공급사 추출 (`serverless/services/supply_chain_parser.py`)
  - ✅ **Supply Chain Service**: 동기화 파이프라인, PostgreSQL + Neo4j 저장 (`serverless/services/supply_chain_service.py`)
  - ✅ **관계 타입**: SUPPLIED_BY, CUSTOMER_OF (StockRelationship 모델)
  - ✅ **신뢰도 계산**: high (10%+ 매출), medium-high (qualifier), medium (단순 언급)
  - ✅ **카테고리 확장**: suppliers, customers (CategoryGenerator)
  - ✅ **Celery Beat 스케줄**: 매월 15일 03:00 EST 배치 동기화
  - ✅ **유닛 테스트**: 54개 테스트 (SEC EDGAR Client 12개, Parser 24개, Service 18개)
- ⏳ **Chain Sight 로드맵** (상세: `docs/features/chain-sight/CHAIN_SIGHT_ROADMAP.md`)
  - ⏳ **Phase 2**: 프론트엔드 그래프 시각화 (react-force-graph)
  - ✅ **Phase 4**: Supply Chain (SUPPLIED_BY, CUSTOMER_OF) - SEC 10-K 파싱
  - ⏳ **Phase 5**: Gemini LLM 관계 추출 (~$5/월)
  - ⏳ **Phase 6**: 뉴스 자연 축적 + 사용자 행동 Edge Weight ($0)
  - ⏳ **Phase 7**: Insider/Institution (HELD_BY_SAME_FUND) - SEC 13F
  - ⏳ **Phase 8**: Regulatory + Patent Network - SEC 8-K, USPTO
- ⏳ ML/DL 모델 통합

---

## 로깅

- 로그 파일: `stocks.log`
- 사용법: `logger = logging.getLogger(__name__)`

---

## 문서화 워크플로우

### 플랜 모드 문서화 규칙

**모든 구현 계획은 docs 폴더에 문서화**:

1. **플랜 모드 진입 시**: 해당 기능의 설계 문서를 적절한 폴더에 생성
2. **구현 완료 후**: 문서 업데이트 및 CLAUDE.md 반영

### docs 폴더 구조

```
docs/
├── architecture/          # 시스템 아키텍처, 설계 문서
├── features/              # 기능별 설계 및 구현 가이드
│   ├── chain-sight/
│   ├── screener/
│   ├── market-movers/
│   ├── keywords/
│   ├── news/
│   ├── stock-sync/
│   ├── empty-basket/
│   └── watchlist/
├── infrastructure/        # 인프라, AWS, 배포 문서
│   ├── aws/
│   └── serverless/
├── testing/               # 테스트 전략, QA 리포트
│   └── qa-reports/
├── bug-reports/           # 버그 리포트
├── user-guide/            # 사용자 가이드
├── ai-analysis/           # AI 분석 설계
├── migration/             # API 마이그레이션
└── misc/                  # 기타 문서
```

### 문서 업데이트 트리거

| 상황 | 업데이트 대상 |
|------|-------------|
| 새 기능 구현 | `docs/features/{기능}/` + CLAUDE.md "구현 완료 기능" |
| 아키텍처 변경 | `docs/architecture/` + CLAUDE.md 해당 섹션 |
| API 추가/변경 | CLAUDE.md "주요 API 엔드포인트" |
| 버그 수정 | `docs/bug-reports/` + CLAUDE.md "자주 발생하는 버그" |
| 사용자 기능 | `docs/user-guide/` 해당 섹션 |

### 문서 네이밍 규칙

- **설계 문서**: `UPPER_SNAKE_CASE.md` (예: `SCREENER_UPGRADE_PLAN.md`)
- **가이드 문서**: `lower-kebab-case.md` (예: `testing-guide.md`)
- **폴더**: `lower-kebab-case`

### 문서 목차

전체 문서 목록: [docs/README.md](docs/README.md)
