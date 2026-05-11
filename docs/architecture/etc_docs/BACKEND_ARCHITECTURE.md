# Backend Architecture Overview

> 마지막 업데이트: 2026-02-27

Stock-Vis 백엔드는 Django REST Framework 기반의 AI 투자 분석 플랫폼입니다.

---

## 기술 스택

| 구분 | 기술 |
|------|------|
| Framework | Django 5.1.7 + DRF |
| Database | PostgreSQL (stock_vis) |
| Cache/Broker | Redis (캐시: db1, Celery: db0) |
| Task Queue | Celery + django-celery-beat |
| Graph DB | Neo4j (Chain Sight 온톨로지) |
| LLM | Gemini 2.5 Flash (키워드, RAG, 뉴스 분석) |
| Auth | JWT (SimpleJWT) + Session fallback |

---

## 앱 구조 (9개 Django Apps)

```
stock_vis/
├── config/              # Django 설정, Celery, URL 라우팅
├── api_request/         # 외부 API 클라이언트 (Alpha Vantage, FMP, SEC)
├── stocks/              # 핵심 - 주가, 재무제표, EOD 시그널
├── users/               # 인증, 포트폴리오, 워치리스트
├── analysis/            # 기술적 지표 (RSI, MACD, BB)
├── news/                # 뉴스 수집, 감성 분석, Intelligence Pipeline v3
├── macro/               # 거시경제 (Market Pulse, FRED, Fear & Greed)
├── graph_analysis/      # 상관관계 분석, 이상치 탐지
├── rag_analysis/        # LLM RAG 분석 (DataBasket, 채팅)
├── serverless/          # Market Movers, Screener, Chain Sight, ETF
├── tests/               # pytest 테스트
└── frontend/            # Next.js 16 (별도 프로젝트)
```

---

## 앱별 상세

### 1. stocks (핵심 앱)

주가, 재무제표, EOD 시그널 파이프라인을 담당하는 메인 앱.

**모델**

| 모델 | PK/Unique | 역할 |
|------|-----------|------|
| `Stock` | symbol | 종목 마스터 (가격, 재무비율, 애널리스트 등) |
| `DailyPrice` | (stock, date) | 일별 OHLCV |
| `WeeklyPrice` | (stock, date) | 주간 OHLCV |
| `BalanceSheet` | (stock, period_type, fiscal_year, fiscal_quarter) | 대차대조표 |
| `IncomeStatement` | (stock, period_type, fiscal_year, fiscal_quarter) | 손익계산서 |
| `CashFlowStatement` | (stock, period_type, fiscal_year, fiscal_quarter) | 현금흐름표 |
| `SP500Constituent` | symbol | S&P 500 구성종목 |
| `StockOverviewKo` | stock (1:1) | LLM 한글 기업 개요 |
| `EODSignal` | (stock, date) | 일별 시그널 (14종) |
| `EODDashboardSnapshot` | date | Baked JSON 스냅샷 |
| `SignalAccuracy` | (stock, signal_date, signal_tag) | 시그널 정확도 추적 |
| `PipelineLog` | run_id | 파이프라인 실행 로그 |

**서비스 (stocks/services/)**

| 파일 | 역할 |
|------|------|
| `eod_pipeline.py` | 8단계 EOD 파이프라인 오케스트레이터 |
| `eod_signal_calculator.py` | 14개 시그널 벡터 연산 (pandas) |
| `eod_signal_tagger.py` | 시그널 태깅 + primary/sub_tag 결정 |
| `eod_json_baker.py` | Atomic Write로 JSON 파일 생성 → frontend/public/static/signals/ |
| `eod_news_enricher.py` | 5단계 계층적 뉴스 매칭 |
| `korean_overview_service.py` | Gemini로 한글 기업 개요 생성 |
| `sp500_eod_service.py` | S&P 500 EOD 가격 수집 |
| `fmp_fundamentals_service.py` | FMP 재무 데이터 수집 |

**EOD 시그널 (14개)**

| ID | 이름 | 카테고리 |
|----|------|---------|
| P1 | 연속 상승/하락 | momentum |
| P2 | 수익률 상위 | momentum |
| P3 | 갭 감지 | momentum |
| P4 | 장대양봉/음봉 | momentum |
| P5 | 52주 신고가 근접 | breakout |
| P7 | 저가 대비 반등률 | reversal |
| V1 | 거래량 폭발 | volume |
| PV1 | 가격-거래량 효율성 | volume |
| PV2 | 매집 의심 | volume |
| MA1 | 골든/데드크로스 | technical |
| T1 | RSI 과매도/과매수 | technical |
| S1 | 섹터 상대 강도 | relation |
| S2 | 섹터 소외주 | relation |
| S4 | 폭락장 생존자 | relation |

---

### 2. users (인증/포트폴리오)

**모델**

| 모델 | 역할 |
|------|------|
| `User` | AbstractUser 확장 (user_name, nick_name, favorite_stock M2M) |
| `Portfolio` | 보유 종목 (수량, 평균가, 목표가, 손절가) |
| `Watchlist` | 관심 목록 |
| `WatchlistItem` | 관심 종목 (목표 진입가, 메모) |
| `UserInterest` | 사용자 관심 테마/섹터 (뉴스 개인화용) |

**인증**: JWT (Access 60분, Refresh 7일, Rotation + Blacklist)

---

### 3. news (뉴스 Intelligence Pipeline)

**모델**

| 모델 | 역할 |
|------|------|
| `NewsArticle` | 뉴스 기사 (UUID PK, 감성점수, 중요도) |
| `NewsEntity` | 뉴스-종목 연결 (M:N) |
| `SentimentHistory` | 일별 감성 집계 |
| `DailyNewsKeyword` | AI 키워드 (Gemini 생성) |
| `NewsAutoCategory` | 자동 수집 카테고리 |
| `ImportanceModel` | ML 모델 버전 관리 |
| `MLWeeklyReport` | ML 주간 리포트 |

**Intelligence Pipeline v3 (3단계)**

```
Stage 1: Rule Engine (Engine C)
  → importance_score, rule_sectors, rule_tickers

Stage 2: LLM Deep Analysis (Gemini 2.5 Flash)
  → 방향성, 영향 종목, 중요도 재평가

Stage 3: ML Label Collection
  → 24시간 후 시장 반응 라벨링 → 모델 학습
```

**뉴스 소스**: Finnhub (주), Marketaux (보조)

---

### 4. macro (거시경제 / Market Pulse)

**모델**

| 모델 | 역할 |
|------|------|
| `EconomicIndicator` | 경제지표 마스터 (코드, 카테고리, 소스) |
| `IndicatorValue` | 지표 시계열 데이터 |
| `MarketIndex` | 주요 시장 지수 |

**카테고리**: growth, inflation, employment, interest_rate, volatility, sentiment, housing, trade

**데이터 소스**: FRED API + FMP API

---

### 5. serverless (Market Movers, Screener, Chain Sight)

가장 많은 API 엔드포인트를 보유한 앱 (60+ endpoints).

**모델**

| 모델 | 역할 |
|------|------|
| `MarketMover` | 일별 상승/하락/거래량 상위 종목 |
| `SectorETFMapping` | 섹터 → ETF 매핑 |
| `StockSectorInfo` | 종목 → 섹터 매핑 |
| `VolatilityBaseline` | 변동성 백분위 기준 |
| `ScreenerPreset` | 스크리너 프리셋 |
| `ScreenerAlert` | 스크리너 알림 |
| `InvestmentThesis` | 투자 테제 (AI 생성) |
| `ETFHolding` | ETF 보유종목 |
| `ThemeMatch` | 테마-종목 매칭 |
| `SupplyChainRelation` | 공급망 관계 |
| `LLMRelation` | LLM 추출 관계 |
| `InstitutionalHolding` | 기관 보유 (13F) |

**Chain Sight 6개 레이어**

| 레이어 | 데이터 소스 |
|--------|-----------|
| ETF Holdings | SPDR, iShares CSV 파싱 |
| Supply Chain | FMP API |
| LLM Relations | Gemini 뉴스 분석 |
| Institutional Holdings | SEC 13F |
| Regulatory | SEC Filing 기반 |
| Patent Network | 특허 네트워크 |

---

### 6. rag_analysis (RAG 분석)

**모델**

| 모델 | 역할 |
|------|------|
| `DataBasket` | 분석 데이터 바구니 (최대 15개 아이템) |
| `BasketItem` | 바구니 아이템 (주식, 뉴스, 재무 등 9종) |
| `AnalysisSession` | 분석 세션 |
| `ConversationMessage` | 대화 메시지 |

**분석 흐름**: DataBasket 구성 → Session 생성 → SSE 스트리밍 채팅 (Gemini)

---

### 7. graph_analysis (상관관계)

**모델**

| 모델 | 역할 |
|------|------|
| `CorrelationMatrix` | 워치리스트 기반 상관행렬 |
| `CorrelationEdge` | 종목 쌍별 상관계수 |
| `CorrelationAnomaly` | 상관관계 이상 탐지 (±0.2 변동) |
| `PriceCache` | 90일 가격 캐시 |
| `GraphMetadata` | 계산 메타데이터 |

**상태**: 모델/서비스 완료, API(urls.py) 미구현

---

### 8. analysis (기술적 지표)

`stocks/indicators.py`의 `TechnicalIndicators` 클래스 활용.

**지표**: RSI, MACD, Bollinger Bands, Stochastic, ATR, OBV, SMA/EMA

---

### 9. api_request (외부 API 클라이언트)

모델 없음. 순수 서비스 레이어.

| 클라이언트 | 대상 API | Rate Limit |
|-----------|---------|------------|
| `AlphaVantageService` | 주가, 재무제표 | 5/분 (12초 대기) |
| `FMPClient` | 재무비율, 밸류에이션 | 10/분, `/stable/*` 경로만 |
| `FREDClient` | 경제지표 | - |
| `SECEdgarClient` | 13F 기관 보유 | - |
| `EODHDClient` | 과거 주가 | - |
| `FinnhubProvider` | 뉴스 (주) | 60/분 |
| `MarketauxProvider` | 뉴스 (보조) | 100/일 |

---

## API 엔드포인트 요약

| 앱 | Base URL | 엔드포인트 수 | 주요 기능 |
|----|----------|-------------|----------|
| stocks | `/api/v1/stocks/` | ~40 | 주가, 차트, 재무제표, EOD, 스크리너 |
| users | `/api/v1/users/` | ~25 | 인증, 포트폴리오, 워치리스트 |
| news | `/api/v1/news/` | ~20 | 뉴스 목록, 감성분석, 키워드, 인사이트 |
| macro | `/api/v1/macro/` | ~10 | Market Pulse, VIX, 금리, 인플레이션 |
| rag | `/api/v1/rag/` | ~18 | DataBasket, 세션, 채팅, 모니터링 |
| serverless | `/api/v1/serverless/` | ~60 | Movers, Screener, Chain Sight, Admin |
| **합계** | | **~173** | |

---

## Celery 태스크 스케줄 (40+)

### 실시간 (장중 5분 간격)
| 태스크 | 주기 | 앱 |
|--------|------|-----|
| `update_realtime_prices` | 5분 | stocks |
| `update_market_indices` | 5분 | macro |
| `refresh_market_pulse_cache` | 1분 | macro |
| `check_screener_alerts` | 15분 | serverless |

### 일별 (장 마감 후)
| 태스크 | 시간 (ET) | 앱 |
|--------|----------|-----|
| `update_daily_prices` | 17:00 | stocks |
| `sync_sp500_eod_prices` | 18:00 | stocks |
| `run_eod_pipeline` | 18:30 | stocks |
| `backfill_signal_accuracy` | 19:00 | stocks |
| `collect_daily_news` | 06:00 | news |
| `collect_market_news` | 12:00, 18:00 | news |
| `extract_daily_news_keywords` | 08:00 | news |
| `classify_news_batch` | 2시간마다 | news |
| `analyze_news_deep` | 2시간마다 | news |
| `sync_news_to_neo4j` | 2시간마다 | news |
| `collect_ml_labels` | 19:00 | news |
| `sync_daily_market_movers` | 07:30 | serverless |
| `keyword_generation_pipeline` | 08:00 | serverless |
| `calculate_daily_market_breadth` | 16:30 | serverless |
| `calculate_daily_sector_heatmap` | 16:35 | serverless |

### 주간
| 태스크 | 시간 | 앱 |
|--------|------|-----|
| `aggregate_weekly_prices` | 토 01:00 | stocks |
| `train_importance_model` | 일 03:00 | news |
| `generate_shadow_report` | 일 03:30 | news |
| `check_auto_deploy` | 일 04:00 | news |
| `generate_weekly_ml_report` | 일 04:15 | news |
| `sync_etf_holdings` | 월 06:00 | serverless |
| `scan_regulatory_relationships` | 월 04:00 | serverless |

### 월간
| 태스크 | 시간 | 앱 |
|--------|------|-----|
| `sync_sp500_constituents` | 1일 02:00 | stocks |
| `bulk_generate_korean_overviews` | 1일 03:00 | stocks |
| `sync_sp500_financials` | 매일 20:00 (101개/일) | stocks |
| `sync_supply_chain_batch` | 15일 03:00 | serverless |
| `sync_institutional_holdings` | 16일 04:00 | serverless |
| `build_patent_network` | 1일 04:30 | serverless |

---

## 설정 (config/)

### 데이터베이스
```
Engine: PostgreSQL
Name: stock_vis
Host: localhost:5432
```

### 캐시
```
Backend: Redis
Location: redis://127.0.0.1:6379/1
```

### Celery
```
Broker: redis://localhost:6379/0
Result Backend: django-db
Timezone: America/New_York
Scheduler: django_celery_beat.schedulers:DatabaseScheduler
```

### JWT
```
Access Token: 60분
Refresh Token: 7일
Rotation: True
Blacklist After Rotation: True
```

### 외부 API 키 (.env)
```
ALPHA_VANTAGE_API_KEY   # 주가, 재무제표
FMP_API_KEY             # 재무비율, 거시경제
GEMINI_API_KEY          # LLM (키워드, RAG, 뉴스 분석, 한글 개요)
FINNHUB_API_KEY         # 뉴스 (주)
MARKETAUX_API_KEY       # 뉴스 (보조)
FRED_API_KEY            # 경제지표
NEO4J_URI/USERNAME/PASSWORD  # Graph DB
```

---

## 아키텍처 패턴

### 3계층 구조
```
API Client (api_request/)
  → Processor (데이터 변환/검증)
    → Service (비즈니스 로직)
      → Models (DB)
        → Views (API 응답)
          → Serializers (직렬화)
```

### 핵심 규칙
- `symbol.upper()` 필수
- Processor에 `return` 문 필수
- Celery 태스크: idempotent, max_retries=3
- LLM 호출: Celery에서 동기 API만 사용
- FMP: `/stable/*` 경로만 사용
- 가격 모델: `DailyPrice` (HistoricalPrice 없음)

### EOD 파이프라인 흐름
```
Stage 1: Ingest + Quality Check
Stage 2: Hard Filter (volume >= 100K, dollar_volume >= $500K)
Stage 3: Calculate (벡터 연산, VIX 레짐 분기)
Stage 4: Tag + 중복 정리
Stage 5: News Enrich (5단계 계층 매칭)
Stage 6: DB Upsert (bulk_create, 멱등)
Stage 7: JSON Bake (Atomic Directory Swap)
Stage 8: Accuracy Backfill
Stage 9: Health Check
```

### News Intelligence Pipeline v3
```
Rule Engine (Engine C)
  → 중요도 점수, 관련 섹터/종목 추출

LLM Analysis (Gemini)
  → 방향성, 영향도, 연쇄 논리 분석

ML Learning
  → 24h 후 시장 반응 라벨 → 모델 학습
  → Shadow Mode → Production Mode 전환
  → LightGBM 자동 승격
```

---

## 데이터 흐름도

```
[외부 API]
  Alpha Vantage ──→ stocks/  ──→ DailyPrice, Stock
  FMP           ──→ stocks/  ──→ BalanceSheet, IncomeStatement, CashFlow
                ──→ macro/   ──→ EconomicIndicator, IndicatorValue
  FRED          ──→ macro/   ──→ EconomicIndicator, IndicatorValue
  Finnhub       ──→ news/    ──→ NewsArticle, NewsEntity
  SEC 13F       ──→ serverless/ → InstitutionalHolding

[내부 처리]
  EOD Pipeline  ──→ stocks/  ──→ EODSignal → JSON Bake → frontend/public/
  News Pipeline ──→ news/    ──→ Rule → LLM → ML → Neo4j
  RAG           ──→ rag/     ──→ DataBasket → Gemini → SSE Stream
  Chain Sight   ──→ serverless/ → ETF + Supply + LLM + 13F → Neo4j

[프론트엔드]
  Next.js ←── REST API (DRF)
          ←── Static JSON (EOD Dashboard)
          ←── SSE Stream (RAG Chat)
```

---

## 모델 관계도 (주요)

```
Stock (PK: symbol)
  ├── DailyPrice (FK)
  ├── WeeklyPrice (FK)
  ├── BalanceSheet (FK)
  ├── IncomeStatement (FK)
  ├── CashFlowStatement (FK)
  ├── StockOverviewKo (1:1)
  ├── EODSignal (FK)
  ├── SignalAccuracy (FK)
  ├── Portfolio (FK via User)
  ├── WatchlistItem (FK via Watchlist)
  └── NewsEntity (FK via NewsArticle)

User (PK: id)
  ├── Portfolio (FK)
  ├── Watchlist (FK)
  │   └── WatchlistItem (FK)
  ├── UserInterest (FK)
  ├── DataBasket (FK)
  │   └── BasketItem (FK)
  └── AnalysisSession (FK)

NewsArticle (PK: UUID)
  └── NewsEntity (FK, M:N with Stock)
```
