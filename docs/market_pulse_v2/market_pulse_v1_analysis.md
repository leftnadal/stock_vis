# Market Pulse v1 전체 분석 — v2 업그레이드 계획용

> 작성일: 2026-04-19
> 목적: 다른 AI 에이전트들과 상의하여 Market Pulse v2를 설계하기 위한 현행 시스템 완전 분석

---

## 1. 제품 개요

**Market Pulse**는 투자자가 개별 종목 분석에 앞서 **전체 시장의 방향성과 투자 환경**을 파악하는 거시경제 대시보드이다.

### 핵심 철학
- **Top-Down 접근**: 거시경제 → 섹터 → 개별 종목 순서로 투자 판단
- **"Don't fight the Fed"**: 금리/유동성 환경이 개별 종목보다 중요
- **교육적 투자**: 초급~고급 3단계 설명으로 투자 리터러시 향상

### 현재 5개 섹션 구성

| # | 섹션 | 데이터 소스 | 갱신 주기 |
|---|------|-----------|----------|
| 0 | Market Movers (급등/급락) | FMP + Celery | 5분 |
| 1 | Fear & Greed + Yield Curve | FRED (VIX, 국채) | 1분 (캐시 60초) |
| 2 | Economic Indicators (CPI, 고용) | FRED | 1시간 (캐시 86400초) |
| 3 | Global Markets (지수/섹터/환율/상품) | FMP | 5분 (캐시 60초) |
| 4 | Economic Calendar | FMP (현재 비활성) | 일 1회 |

---

## 2. 백엔드 구조

### 2.1 디렉토리 구조

```
macro/
├── models/
│   ├── indicators.py          # EconomicIndicator, IndicatorValue, MarketIndex, MarketIndexPrice, EconomicEvent
│   └── relationships.py       # SectorIndicatorRelation, IndicatorCorrelation + seed 함수
├── services/
│   ├── macro_service.py       # MacroEconomicService (통합 서비스)
│   ├── fred_client.py         # FREDClient (경제 지표)
│   └── fmp_client.py          # FMPClient (시장 지수/섹터/환율/상품)
├── constants/
│   └── insights.py            # FEAR_GREED_RULES, YIELD_CURVE_RULES, VIX_RULES 등
├── views.py                   # 10개 View (8 GET + 1 POST + 1 GET status)
├── serializers.py             # 8개 Serializer
├── tasks.py                   # 5개 Celery 태스크
├── urls.py                    # 10개 URL 패턴
├── admin.py
└── migrations/
```

### 2.2 모델 구조

#### EconomicIndicator (거시경제 지표 메타데이터)
```
PK: code (CharField 50) — FRED 시리즈 ID (예: GDP, UNRATE, FEDFUNDS, VIXCLS)
Fields:
  - name, name_ko, description
  - category: growth | inflation | employment | interest_rate | volatility | sentiment | housing | trade
  - data_source: fred | fmp | calculated
  - update_frequency: realtime | daily | weekly | monthly | quarterly | yearly
  - unit, decimal_places, display_order, is_active
  - cache_ttl (초): 실시간=60, 일간=3600, 월간=86400
  - last_updated
```

#### IndicatorValue (시계열 데이터)
```
FK: indicator → EconomicIndicator (CASCADE)
Fields: date, value (Decimal 20,6), period, is_preliminary, revision_date
Indexes: (indicator, -date), (-date)
Unique: (indicator, date)
```

#### MarketIndex (시장 지수 메타데이터)
```
PK: symbol (CharField 20) — SPX, NDX, VIX, DXY 등
Fields: name, name_ko, category (us_equity|global_equity|volatility|currency|commodity|bond|sector), fmp_symbol
```

#### MarketIndexPrice (지수 가격)
```
FK: index → MarketIndex (CASCADE)
Fields: date, open, high, low, close, volume, change, change_percent
Indexes: (index, -date)
Unique: (index, date)
```

#### EconomicEvent (경제 캘린더)
```
Fields: event_id (unique), title, title_ko, event_date, event_time
  - importance: critical | high | medium | low
  - country, previous_value, forecast_value, actual_value
  - related_indicator (FK → EconomicIndicator, SET_NULL)
Properties: is_past, surprise (actual - forecast 계산)
```

#### SectorIndicatorRelation (지표-섹터 영향)
```
FK: indicator → EconomicIndicator
Fields: sector_code, sector_name, sector_name_ko
  - impact_direction: positive | negative | neutral | mixed
  - impact_strength: high | medium | low
  - condition_type: rising | falling | high | low | any
  - condition_threshold, rationale, rationale_ko
Unique: (indicator, sector_code, condition_type)
```

#### IndicatorCorrelation (지표 간 상관관계)
```
FK: indicator_a, indicator_b → EconomicIndicator
Fields: correlation_type (positive|negative|leading|lagging)
  - correlation_coefficient (-1~+1)
  - lead_lag_days, calculation_period_days (기본 252일)
```

### 2.3 API 엔드포인트 (10개)

| 메서드 | 경로 | View | 설명 |
|--------|------|------|------|
| GET | `/api/v1/macro/pulse/` | MarketPulseView | 전체 대시보드 (통합) |
| GET | `/api/v1/macro/fear-greed/` | FearGreedIndexView | 공포/탐욕 지수 |
| GET | `/api/v1/macro/interest-rates/` | InterestRatesView | 금리 & 수익률 곡선 |
| GET | `/api/v1/macro/inflation/` | InflationDashboardView | 인플레이션 & 고용 |
| GET | `/api/v1/macro/global-markets/` | GlobalMarketsView | 글로벌 시장 |
| GET | `/api/v1/macro/calendar/?days=7&importance=high` | EconomicCalendarView | 경제 캘린더 |
| GET | `/api/v1/macro/vix/` | VIXView | VIX 단일 지표 |
| GET | `/api/v1/macro/sectors/` | SectorPerformanceView | 섹터 성과 |
| POST | `/api/v1/macro/sync/` | DataSyncView | 동기화 트리거 |
| GET | `/api/v1/macro/sync/status/` | SyncStatusView | 동기화 상태 |

**인증**: 모든 View가 `permission_classes = [AllowAny]` — 인증 불필요

### 2.4 서비스 레이어

#### MacroEconomicService
```python
class MacroEconomicService:
    CACHE_TTL = {
        'realtime': 60,          # VIX, 지수
        'daily': 3600,           # 금리, 환율
        'monthly': 86400,        # CPI, 고용
        'quarterly': 86400 * 7,  # GDP
    }

    # 대시보드 데이터 조회 (5개 메서드)
    get_fear_greed_index()           → Fear/Greed 계산 (VIX 50% + Spread 30% + Momentum 20%)
    get_interest_rates_dashboard()   → 금리 + 7개 만기 수익률 곡선
    get_inflation_dashboard()        → CPI, Core CPI, PCE, 실업률, NFP, GDP
    get_global_markets_dashboard()   → 지수 + 섹터 + 환율 + 상품 + DXY + VIX
    get_economic_calendar()          → 날짜별 이벤트 그룹핑
    get_market_pulse_dashboard()     → 위 5개 통합 반환

    # 데이터 동기화 (4개 메서드)
    sync_indicator_values(code)      → FRED → DB 저장
    sync_all_indicators()            → 8개 FRED 시리즈 전체 동기화
    sync_market_indices()            → FMP → MarketIndexPrice 저장
    sync_global_markets()            → 섹터/환율/상품 동기화
    sync_economic_calendar()         → **현재 비활성 (FMP 403)**
```

#### FREDClient
```python
class FREDClient:
    BASE_URL = "https://api.stlouisfed.org/fred"
    # Rate Limit: 분당 120회
    # 19개 시리즈 코드 정의 (금리 5, 인플레이션 4, 고용 4, 성장 2, 변동성 2, 통화 2)

    get_vix()                → VIX 최신값 + level 판정
    get_yield_spread()       → 10Y-2Y 스프레드 + status
    get_interest_rates()     → FEDFUNDS, DGS2, DGS10, DGS30, T10Y2Y
    get_inflation_data()     → CPI, Core CPI, PCE + YoY 변화율 계산
    get_employment_data()    → 실업률, NFP, Initial Claims
    get_gdp_growth()         → Real GDP + QoQ 성장률
    get_series_observations() → 범용 시리즈 데이터 조회
```

#### FMPClient
```python
class FMPClient:
    BASE_URL = "https://financialmodelingprep.com"
    # Starter Plan: 250 calls/일, /stable/* 경로만

    INDEX_SYMBOLS: SPY, DIA, QQQ, IWM (ETF로 대체)
    SECTOR_ETFS: XLK, XLF, XLV, XLE, XLI, XLP, XLY, XLU, XLRE, XLB, XLC (11개)
    COMMODITIES: GCUSD(금), SIUSD(은), CLUSD(유), NGUSD(가스)
    FOREX: EURUSD, USDJPY, GBPUSD, USDCNY, USDKRW

    get_market_indices()      → 4개 지수 ETF 시세
    get_sector_performance()  → 11개 섹터 ETF 성과
    get_forex_rates()         → 5개 환율 쌍
    get_commodities()         → 4개 원자재
    get_dollar_index()        → DXY
    get_all_market_quotes()   → 위 전체 통합 조회
    get_economic_calendar()   → 경제 이벤트
```

### 2.5 Celery 태스크 (5개)

| 태스크 | 주기 | 역할 |
|--------|------|------|
| `update_economic_indicators` | 매시간 | FRED 7개 시리즈 동기화 + 캐시 무효화, max_retries=3 |
| `update_market_indices` | 시장시간 5분마다 | FMP 전체 시세 → MarketIndexPrice 저장, max_retries=3 |
| `update_economic_calendar` | 매일 1회 | FMP 캘린더 → EconomicEvent 저장 |
| `refresh_market_pulse_cache` | 시장시간 1분마다 | 캐시 삭제 후 재생성 |
| `cleanup_old_data` | 매주 일요일 | 1년 이전 지표/가격 + 30일 이전 이벤트 삭제 |

### 2.6 캐싱 전략

```
Backend Redis Cache:
  macro:fear_greed_index        → 60초 TTL
  macro:interest_rates_dashboard → 3600초 TTL
  macro:inflation_dashboard      → 86400초 TTL
  macro:global_markets_dashboard → 60초 TTL
  macro:economic_calendar:*      → 3600초 TTL
  macro:market_pulse_full        → 60초 TTL (전체 대시보드)
  macro:sync_status              → 300초 TTL (동기화 상태)
  macro:sync_progress            → 300초 TTL (동기화 진행률)
```

### 2.7 데이터 동기화 흐름

```
POST /api/v1/macro/sync/
  → DataSyncView
    → threading.Thread(target=_run_data_sync)  ← ⚠️ Celery 미사용!
      → Step 1: sync_all_indicators() (FRED)
      → Step 2: sync_market_indices() (FMP)
      → Step 3: sync_global_markets() (FMP)
      → Step 4: sync_economic_calendar() (비활성)
      → cache.set(SYNC_STATUS_KEY, 'completed')
```

### 2.8 인사이트 규칙 시스템 (constants/insights.py)

```python
INSIGHT_RULES = {
    "fear_greed": FEAR_GREED_RULES,     # 5단계: extreme_fear~extreme_greed (0-100)
    "yield_curve": YIELD_CURVE_RULES,    # 4단계: inverted, flattening, normal, steep
    "rate_impact": RATE_IMPACT_RULES,    # 5단계: falling_fast ~ rising_fast + 섹터별 영향
    "calendar_importance": CALENDAR_IMPORTANCE_RULES,  # 3단계: critical, high, medium
    "vix": VIX_RULES                     # 4단계: low~extreme_high
}

Fear & Greed 계산:
  index = VIX_score * 0.5 + spread_score * 0.3 + market_momentum * 0.2
  (VIX가 높으면 공포, 스프레드 역전이면 공포, 모멘텀은 기본 50)
```

---

## 3. 프론트엔드 구조

### 3.1 파일 맵

```
frontend/
├── app/market-pulse/page.tsx              ← 진입점 (294줄)
├── components/
│   ├── macro/                             ← 거시경제 섹션
│   │   ├── FearGreedGauge.tsx             ← SVG 반원 게이지
│   │   ├── YieldCurveChart.tsx            ← Recharts LineChart
│   │   ├── EconomicIndicators.tsx         ← 4칸 그리드 (CPI, 실업률 등)
│   │   ├── GlobalMarketsCard.tsx          ← 4열 (지수/글로벌/환율/상품)
│   │   └── index.ts                       ← barrel export
│   ├── market-pulse/                      ← Market Movers 섹션
│   │   ├── MarketMoversSection.tsx         ← 개별 키워드 조회
│   │   ├── MarketMoversSectionOptimized.tsx ← 배치 키워드 (N+1 회피)
│   │   ├── MoverCard.tsx                  ← 종목 카드 (memo)
│   │   ├── MoverCardWithBatchKeywords.tsx  ← 배치 최적화 카드
│   │   └── MarketNewsSection.tsx          ← ⚠️ 미구현
│   ├── keywords/
│   │   ├── KeywordList.tsx                ← 키워드 목록 (memo)
│   │   └── KeywordTag.tsx                 ← 개별 키워드 태그
│   └── common/
│       └── CorporateActionBadge.tsx       ← 기업 액션 배지
├── hooks/
│   ├── useMarketPulse.ts                  ← 대시보드 데이터 (localStorage 캐시)
│   ├── useMarketMovers.ts                 ← 급등/급락 데이터
│   └── useKeywords.ts                     ← 키워드 개별/배치 조회
├── services/
│   ├── macroService.ts                    ← macro API 클라이언트
│   ├── serverlessService.ts               ← Market Movers API
│   └── keywordService.ts                  ← 키워드 API
├── types/
│   ├── macro.ts                           ← 거시경제 타입 (203줄, 20개 인터페이스)
│   └── market.ts                          ← Market Movers 타입
└── constants/
    └── education.ts                       ← 3단계 교육 콘텐츠
```

### 3.2 컴포넌트 트리

```
MarketPulsePage
└── AuthGuard
    └── MarketPulseContent
        ├── Header (sticky top-0)
        │   ├── Sync Status Badge (running/completed/idle)
        │   ├── StaleIndicator (업데이트 경과 시간)
        │   ├── "동기화" 버튼 (POST /sync/)
        │   └── "새로고침" 버튼 (refetch)
        │
        ├── Section 0: MarketMoversSection (독립 훅)
        │   ├── Tab Navigation (gainers/losers/actives)
        │   └── MoverCard Grid (3열)
        │       ├── 순위 + 심볼 + 회사명
        │       ├── 5개 지표 (RVOL, 추세강도, 섹터알파, ETF동행률, 변동성백분위)
        │       ├── 가격 + 변동률 배지
        │       ├── KeywordList (AI 키워드 3개)
        │       └── CorporateActionBadge
        │
        ├── Section 1: Fear & Greed + Yield Curve (lg:grid-cols-3)
        │   ├── FearGreedGauge (col-span-1)
        │   │   ├── SVG 반원 게이지 (gradient: 빨강→주황→회색→초록)
        │   │   ├── 바늘 (0-100 → -90°~90° 회전)
        │   │   ├── 상태 배지 + 메시지 + action_hint
        │   │   └── <details> 교육 콘텐츠
        │   └── YieldCurveChart (col-span-2)
        │       ├── Recharts LineChart (7개 만기)
        │       ├── ReferenceLine (기준금리)
        │       ├── Status Banner (inverted/normal/steep)
        │       ├── Key Rates Summary (3칸)
        │       └── <details> 교육 콘텐츠
        │
        ├── Section 2: EconomicIndicators
        │   ├── 4칸 그리드 (CPI, Core CPI, 실업률, NFP)
        │   │   ├── 상태 배지 (조건부 색상)
        │   │   └── 목표 대비 표시 (CPI → Fed target 2%)
        │   └── GDP 섹션 (optional)
        │
        ├── Section 3: GlobalMarketsCard
        │   ├── 4열 (US지수, 글로벌지수, 환율, 상품)
        │   ├── VIX 변동성 레벨 (색상 4단계)
        │   └── 섹터 성과 칩 (변동률 정렬)
        │
        ├── Section 4: Economic Calendar
        │   ├── 날짜별 그룹화 (최대 5일)
        │   ├── 이벤트별 Impact 인디케이터 (dot 색상)
        │   └── Actual/Estimate/Previous 값
        │
        └── Footer (고지사항 + 마지막 업데이트)
```

### 3.3 데이터 흐름 & 캐싱

```
┌─────────────────────────────────────────────┐
│ useMarketPulse()                            │
│                                             │
│ 1. localStorage 캐시 확인 (30분 TTL)          │
│    └─ 있으면 placeholderData로 즉시 렌더링      │
│                                             │
│ 2. TanStack Query 실행                       │
│    ├─ staleTime: 5분                         │
│    ├─ gcTime: 30분                           │
│    ├─ refetchInterval: 60초 (자동 갱신)        │
│    └─ queryFn: macroService.getMarketPulse() │
│         └─ GET /api/v1/macro/pulse/          │
│              └─ Backend Redis Cache (60초)    │
│                   └─ FRED API / FMP API      │
│                                             │
│ 3. 새 데이터 → localStorage 저장              │
└─────────────────────────────────────────────┘

┌─────────────────────────────────────────────┐
│ useMarketMovers(type, date?)   (독립 훅)     │
│                                             │
│ TanStack Query                              │
│ ├─ staleTime: 5분                           │
│ ├─ refetchInterval: 5분                     │
│ └─ GET /api/v1/serverless/movers?type=...   │
│      └─ 별도 앱 (serverless/)                │
└─────────────────────────────────────────────┘

┌─────────────────────────────────────────────┐
│ useSyncStatus(enabled)                      │
│                                             │
│ ├─ enabled=true일 때만 활성                   │
│ ├─ running 상태: 2초마다 폴링                  │
│ └─ completed: 3초 후 비활성화                  │
└─────────────────────────────────────────────┘
```

### 3.4 반응형 & 스타일링

- **프레임워크**: Tailwind CSS
- **그리드**: `grid-cols-1 md:grid-cols-2 lg:grid-cols-3`
- **다크모드**: `dark:` prefix 전체 적용
- **차트**: Recharts (YieldCurveChart), SVG 직접 그리기 (FearGreedGauge)
- **아이콘**: Lucide React
- **둥근 모서리**: `rounded-xl` (11px)
- **그림자**: `shadow-sm`
- **Tooltip**: CSS group-hover 패턴 (커스텀)

### 3.5 성능 최적화

| 기법 | 적용 위치 | 설명 |
|------|----------|------|
| `React.memo` | MoverCard, KeywordList | props 변경 시에만 리렌더링 |
| `useMemo` | KeywordList 내부 | 키워드 정규화 캐싱 |
| localStorage 캐시 | useMarketPulse | 30분 TTL, 즉시 렌더링 |
| 배치 쿼리 | useBatchKeywords | N+1 방지 (POST /keywords/batch) |
| 조건부 폴링 | useSyncStatus | running 상태일 때만 2초 간격 |
| 독립 훅 | MarketMovers | 메인 대시보드와 별도 fetch |

---

## 4. 데이터 구조 요약

### 4.1 DB 테이블 관계도

```
EconomicIndicator (PK: code)
├── IndicatorValue (FK, CASCADE) — 시계열 데이터
├── SectorIndicatorRelation (FK, CASCADE) — 섹터별 영향
├── IndicatorCorrelation (FK, CASCADE) — 지표 간 상관관계
└── EconomicEvent (FK, SET_NULL) — 관련 이벤트

MarketIndex (PK: symbol)
└── MarketIndexPrice (FK, CASCADE) — 일별 가격
```

### 4.2 외부 데이터 소스

| 소스 | 프로토콜 | Rate Limit | 비용 | 수집 대상 |
|------|---------|-----------|------|----------|
| FRED | REST API | 120/분, 무제한/일 | 무료 | 경제 지표 19종 |
| FMP | REST (/stable/*) | 250/일 | Starter $29/월 | 지수/섹터/환율/상품/캘린더 |

### 4.3 FRED 수집 지표 (19종)

| 카테고리 | 코드 | 이름 |
|---------|------|------|
| 금리 | FEDFUNDS | 기준금리 |
| 금리 | DGS2, DGS10, DGS30 | 2/10/30년 국채 |
| 금리 | T10Y2Y | 장단기 금리차 |
| 인플레이션 | CPIAUCSL, CPILFESL | CPI, Core CPI |
| 인플레이션 | PCEPI, PCEPILFE | PCE, Core PCE |
| 고용 | UNRATE | 실업률 |
| 고용 | PAYEMS | 비농업 고용 |
| 고용 | ICSA | 신규 실업수당 청구 |
| 고용 | CIVPART | 경제활동참가율 |
| 성장 | GDP, GDPC1 | 명목/실질 GDP |
| 변동성 | VIXCLS | VIX |
| 변동성 | BAMLH0A0HYM2 | High Yield 스프레드 |
| 통화 | M2SL | M2 통화량 |
| 통화 | DTWEXBGS | 무역가중 달러지수 |

### 4.4 FMP 수집 심볼 (25종)

| 카테고리 | 심볼 | 이름 |
|---------|------|------|
| 지수 ETF | SPY, DIA, QQQ, IWM | S&P500, Dow, Nasdaq, Russell |
| 섹터 ETF | XLK, XLF, XLV, XLE, XLI, XLP, XLY, XLU, XLRE, XLB, XLC | 11개 섹터 |
| 상품 | GCUSD, SIUSD, CLUSD, NGUSD | 금, 은, 원유, 천연가스 |
| 환율 | EURUSD, USDJPY, GBPUSD, USDCNY, USDKRW | 5개 통화쌍 |
| 기타 | DXY | 달러 인덱스 |

---

## 5. UI/UX 관점 — 사용자에게 주는 의미

### 5.1 사용자 여정 (현재)

```
1. 로그인 → 메인 화면 → "Market Pulse" 클릭
2. 첫 진입: 데이터 없음 → 자동 동기화 트리거 (4단계)
3. 동기화 중: 프로그레스 표시 (헤더에 메시지)
4. 데이터 로드: 5개 섹션 순차적 렌더링
5. 사용자 행동:
   - Market Movers 탭 전환 (gainers/losers/actives)
   - 교육 콘텐츠 펼침 (<details>)
   - 새로고침 또는 수동 동기화
6. 자동 갱신: 60초마다 (백그라운드)
```

### 5.2 각 섹션이 사용자에게 전달하는 투자 시그널

| 섹션 | 투자 시그널 | 실제 행동 |
|------|-----------|----------|
| Fear & Greed | "지금 시장이 공포인가, 탐욕인가?" | 극단적 공포 → 분할 매수 검토, 극단적 탐욕 → 신규 매수 자제 |
| Yield Curve | "경기 침체 가능성은?" | 역전 → 12-18개월 후 침체 대비, 정상 → 경기 확장 |
| Economic Indicators | "실물 경제는 어떤가?" | CPI > 2% → 금리 인상 지속, 실업률 상승 → 방어적 포트폴리오 |
| Global Markets | "오늘 시장 흐름은?" | 섹터 로테이션 확인, 달러 강세/약세, 안전자산 흐름 |
| Market Movers | "어떤 종목이 비정상적으로 움직이나?" | RVOL > 3.0 → 비정상 관심, Corporate Action 확인 |

### 5.3 교육 콘텐츠 구조

```
각 섹션의 <details> collapsible:
├── 초급: "이 지표가 뭔가요?" (비유 중심)
├── 중급: "어떻게 해석하나요?" (지표 해석법)
└── 고급: "역사적 맥락은?" (통계/사례)
```

---

## 6. 현 시스템의 좋은 점

### 6.1 아키텍처

| # | 좋은 점 | 설명 |
|---|--------|------|
| 1 | **서비스 레이어 분리** | FREDClient, FMPClient, MacroEconomicService 3계층이 깔끔 |
| 2 | **다단계 캐싱** | Redis (BE 60초~7일) + localStorage (FE 30분) + TanStack Query (5분 stale) |
| 3 | **인사이트 규칙 시스템** | insights.py에 모든 투자 해석 규칙이 상수로 정의 → 일관된 UX |
| 4 | **독립 섹션 로딩** | 한 섹션 실패해도 나머지 섹션은 정상 작동 |
| 5 | **교육 콘텐츠 통합** | 3단계 난이도별 설명이 대시보드에 내장 |
| 6 | **동기화 UX** | 프로그레스 표시 + 자동 리페치 + 완료 알림 |
| 7 | **타입 안전성** | TypeScript strict + 20개 인터페이스로 API 응답 완전 타입화 |
| 8 | **Seed 데이터** | 금리-섹터 관계가 seed_sector_relations()로 코드화 |
| 9 | **Rate Limit 보호** | FRED: rate_limiter + exponential backoff, FMP: request_delay |
| 10 | **성능 최적화** | memo, useMemo, 배치 쿼리, 조건부 폴링 |

### 6.2 도메인 설계

- Fear & Greed 계산 공식이 VIX + Yield Spread + Momentum 3개 요소로 구성
- 수익률 곡선 4단계 해석 (inverted/flattening/normal/steep)
- 금리 변화의 섹터별 영향이 DB 모델로 정의 (SectorIndicatorRelation)
- 지표 간 상관관계 모델 존재 (IndicatorCorrelation) — 선행/후행 관계 포함

---

## 7. 현 시스템의 문제점 및 개선 필요 사항

### 7.1 아키텍처 문제 (Critical)

| # | 문제 | 심각도 | 설명 |
|---|------|--------|------|
| 1 | **동기화가 threading.Thread 사용** | HIGH | DataSyncView에서 Celery 대신 `threading.Thread(daemon=True)` 사용. 프로세스 종료 시 동기화 중단, 재시도 없음, 에러 추적 불가 |
| 2 | **전체 API가 AllowAny** | HIGH | 10개 View 모두 인증 불필요. 외부에서 무제한 접근 가능 → Rate Limit 악용 위험 |
| 3 | **Fear & Greed 계산 너무 단순** | MEDIUM | 3개 요소(VIX, Spread, Momentum)만 사용. CNN Fear & Greed는 7개 지표 사용. market_momentum이 항상 기본값 50 |
| 4 | **경제 캘린더 비활성** | MEDIUM | `sync_economic_calendar()`가 FMP 403으로 비활성. Section 4가 항상 빈 상태 |
| 5 | **Serializer가 DictField 남용** | LOW | MarketPulseResponseSerializer 등이 전부 DictField → API 스키마 자동 문서화 불가 |

### 7.2 데이터 문제

| # | 문제 | 심각도 | 설명 |
|---|------|--------|------|
| 6 | **글로벌 지수 비어있음** | HIGH | `global_indices: {}` — FTSE, Nikkei, Hang Seng 데이터 수집 안 됨. FMP Starter Plan 한계 |
| 7 | **ETF로 지수 대체** | MEDIUM | S&P500을 SPY ETF로 대체. ETF 가격 ≠ 지수 값 (SPY ≈ S&P500/10). 사용자 혼동 가능 |
| 8 | **1년 이상 데이터 삭제** | MEDIUM | cleanup_old_data()가 365일 이전 데이터 삭제 → 장기 트렌드 분석 불가 |
| 9 | **GDP 데이터 누락 가능** | LOW | get_gdp_growth()의 GDPC1이 분기별 업데이트 → 대부분의 시간에 stale 데이터 |
| 10 | **SectorIndicatorRelation 미활용** | LOW | DB 모델과 seed 함수가 있지만, 어떤 View에서도 조회하지 않음 |
| 11 | **IndicatorCorrelation 미활용** | LOW | 상관관계 모델이 있지만 데이터 입력/활용 없음 |

### 7.3 프론트엔드 문제

| # | 문제 | 심각도 | 설명 |
|---|------|--------|------|
| 12 | **MarketNewsSection 미구현** | MEDIUM | 코드에 import 주석 처리됨. 뉴스 섹션 빈 상태 |
| 13 | **Date.now() hydration 위험** | MEDIUM | StaleIndicator에서 `Date.now()` 사용 — SSR/CSR 불일치 가능 (Bug #24) |
| 14 | **중복 컴포넌트** | LOW | MarketMoversSection + MarketMoversSectionOptimized, MoverCard + MoverCardWithBatchKeywords — 동일 기능 2벌 |
| 15 | **경제 캘린더 인라인** | LOW | Section 4가 page.tsx에 직접 작성됨 (별도 컴포넌트 없음) |
| 16 | **반응형 부족** | LOW | 모바일에서 GlobalMarketsCard 4열이 스크롤 필요 |

### 7.4 UX 문제

| # | 문제 | 심각도 | 설명 |
|---|------|--------|------|
| 17 | **첫 진입 시 빈 화면** | HIGH | 데이터 없으면 5개 섹션 모두 스켈레톤 → 동기화 완료까지 30초+ 대기 |
| 18 | **섹션 간 연결성 없음** | MEDIUM | Fear & Greed가 "공포"인데 "어떤 종목이 기회인지" 연결 없음 |
| 19 | **액션 부재** | MEDIUM | "분할 매수 검토"라는 action_hint가 있지만 실제 매수/워치리스트 연결 없음 |
| 20 | **히스토리 없음** | MEDIUM | 현재값만 표시. "지난주 대비", "지난달 대비" 추세 없음 |
| 21 | **개인화 없음** | LOW | 모든 사용자에게 동일한 대시보드. 관심 섹터/지표 커스텀 불가 |
| 22 | **알림 없음** | LOW | VIX 30 초과, 수익률 곡선 역전 등 중요 이벤트 알림 없음 |

---

## 8. v2 업그레이드 시 고려해야 할 핵심 질문

### 8.1 제품 방향성

1. **Market Pulse의 정체성**: 단순 대시보드인가, 투자 의사결정 도구인가?
2. **타겟 사용자**: 초보 투자자? 중급? 전문가? → 교육 콘텐츠 깊이 결정
3. **다른 기능과의 연결**: Thesis Control, Validation, Chain Sight와 어떻게 연동?
4. **실시간성 수준**: 현재 60초 갱신이 충분한가? WebSocket 필요한가?

### 8.2 데이터 확장

1. **글로벌 지수 데이터**: FMP Starter Plan으로 FTSE/Nikkei 가능한가? yfinance 대안?
2. **Fear & Greed 고도화**: CNN 7개 지표(Stock Price Momentum, Stock Price Strength, Stock Price Breadth, Put/Call Ratio, Junk Bond Demand, Market Volatility, Safe Haven Demand) 중 어디까지?
3. **히스토리 차트**: 각 지표의 시계열 차트 추가 범위 (1주? 1달? 1년?)
4. **경제 캘린더 대안**: FMP 403 해결 방법 (다른 API? 수동 입력? 무료 소스?)

### 8.3 기술 개선

1. **동기화**: threading → Celery 전환? 또는 별도 워커?
2. **인증**: AllowAny 유지할 것인가? 최소한 throttle?
3. **API 스키마**: DictField → 구조화된 Serializer? drf-spectacular 대응?
4. **중복 컴포넌트 정리**: Optimized 버전만 남기고 기존 삭제?
5. **SSR vs CSR**: Next.js 서버 컴포넌트 활용 가능한 섹션?

### 8.4 UX 개선

1. **빈 화면 문제**: 기본 데이터 seed? 첫 방문 온보딩?
2. **섹션 간 네러티브**: "오늘의 시장 요약"을 LLM으로 생성?
3. **액션 연결**: "이 상황에서 추천 종목" → Screener/Thesis 연결?
4. **개인화**: 관심 섹터 핀, 커스텀 지표 추가?
5. **알림 시스템**: VIX spike, 수익률 역전 등 push notification?

---

## 9. 핵심 파일 경로 참조

### Backend
```
macro/models/indicators.py          — 5개 모델 정의
macro/models/relationships.py       — 2개 관계 모델 + seed 함수
macro/services/macro_service.py     — 통합 서비스 (588줄)
macro/services/fred_client.py       — FRED API (19개 시리즈)
macro/services/fmp_client.py        — FMP API (25개 심볼)
macro/constants/insights.py         — 인사이트 규칙 5종 (459줄)
macro/views.py                      — 10개 View (411줄)
macro/serializers.py                — 8개 Serializer (134줄)
macro/tasks.py                      — 5개 Celery 태스크 (261줄)
macro/urls.py                       — 10개 URL 패턴
```

### Frontend
```
frontend/app/market-pulse/page.tsx         — 메인 페이지 (294줄)
frontend/components/macro/                  — 거시경제 컴포넌트 4개
frontend/components/market-pulse/           — Market Movers 컴포넌트 5개
frontend/hooks/useMarketPulse.ts            — 대시보드 훅 (145줄)
frontend/types/macro.ts                     — 타입 정의 (203줄)
frontend/services/macroService.ts           — API 클라이언트
```

### 관련 앱 (Market Movers)
```
serverless/services/market_movers.py        — 급등/급락 수집
serverless/services/keyword_data_collector.py — AI 키워드 생성
```

---

## 10. 부록: API 응답 형태 예시

### GET /api/v1/macro/pulse/ 응답 구조
```json
{
  "fear_greed": {
    "value": 62,
    "rule_key": "greed",
    "label": "탐욕",
    "label_en": "Greed",
    "color": "#16A34A",
    "bg_color": "#F0FDF4",
    "message": "투자 심리가 낙관적입니다...",
    "action_hint": "이익 실현 검토",
    "vix": { "value": 18.5, "level": "normal", "date": "2026-04-18" },
    "yield_spread": { "spread": -0.30, "status": "inverted", "date": "2026-04-18" },
    "last_updated": "2026-04-19T10:00:00Z"
  },
  "interest_rates": {
    "fed_funds_rate": 5.33,
    "treasury_2y": 4.72,
    "treasury_10y": 4.42,
    "yield_spread": { "spread": -0.30, "status": "inverted", "date": "..." },
    "yield_curve_status": { "rule_key": "inverted", "label": "역전", "message": "...", "historical_note": "..." },
    "yield_curve_data": [
      { "maturity": "3M", "rate": 5.38 },
      { "maturity": "2Y", "rate": 4.72 },
      { "maturity": "10Y", "rate": 4.42 },
      { "maturity": "30Y", "rate": 4.58 }
    ],
    "last_updated": "..."
  },
  "economy": {
    "inflation": { "cpi_yoy": 3.2, "core_cpi_yoy": 3.8, "pce_yoy": 2.7, "fed_target": 2.0 },
    "employment": { "unemployment_rate": 3.9, "nfp_change": 175000, "initial_claims": 215000 },
    "gdp": { "real_gdp": 22345.6, "qoq_growth": 1.6, "annualized_growth": 2.8, "date": "2026-01-01" },
    "last_updated": "..."
  },
  "global_markets": {
    "indices": {
      "sp500": { "name": "S&P 500 (SPY)", "price": 520.45, "change": 3.21, "change_percent": 0.62 },
      "nasdaq": { "name": "NASDAQ 100 (QQQ)", "price": 445.30, "change": -1.50, "change_percent": -0.34 },
      "dow": { "name": "Dow Jones (DIA)", "price": 392.10, "change": 1.85, "change_percent": 0.47 },
      "russell2000": null
    },
    "global_indices": {},
    "sectors": {
      "sectors": {
        "XLK": { "name": "Technology", "price": 210.5, "change_percent": 0.85 },
        "XLF": { "name": "Financials", "price": 42.3, "change_percent": -0.12 }
      },
      "best_performer": ["XLK", { "name": "Technology", "price": 210.5, "change_percent": 0.85 }],
      "worst_performer": ["XLE", { "name": "Energy", "price": 88.1, "change_percent": -1.2 }]
    },
    "forex": {
      "USDKRW": { "name": "USD/KRW", "price": 1365.50, "change": 2.30, "change_percent": 0.17 }
    },
    "commodities": {
      "GCUSD": { "name": "Gold", "price": 2345.60, "change": 12.40, "change_percent": 0.53 }
    },
    "dxy": { "value": 104.25, "change": 0.15, "change_percent": 0.14 },
    "vix": { "value": 18.5, "level": "normal", "date": "2026-04-18" },
    "last_updated": "..."
  },
  "calendar": {
    "events_by_date": {
      "2026-04-22": [
        { "time": "08:30", "event": "Chicago Fed Nat Activity Index", "country": "US", "impact": "Medium", "actual": null, "previous": "0.05", "estimate": "0.10" }
      ]
    },
    "total_count": 12,
    "from_date": "2026-04-19",
    "to_date": "2026-04-26",
    "last_updated": "..."
  },
  "last_updated": "2026-04-19T10:00:00Z"
}
```

---

## 11. Market Movers 5개 지표 상세

Market Movers는 별도 앱(serverless/)이지만 Market Pulse 페이지에 통합되어 있으므로 함께 분석.

| 지표 | 계산 | 의미 | 임계값 |
|------|------|------|--------|
| **RVOL** (상대 거래량) | 당일 거래량 / 20일 평균 | 비정상적 관심도 | > 2.0 주의, > 3.0 이상 |
| **Trend Strength** (추세 강도) | (종가-시가) / (고가-저가) | 방향성 강도 | 0.5+ 강한 추세 |
| **Sector Alpha** (섹터 알파) | 종목 수익률 - 섹터 ETF 수익률 | 섹터 대비 초과 수익 | > 2%p 유의미 |
| **ETF Sync Rate** (동행률) | 피어슨 상관계수 | 시장 동조 여부 | < 0.3 독립적 움직임 |
| **Volatility %ile** (변동성 백분위) | 20일 기준 백분위 | 현재 변동성 수준 | > 90 극단적 |

---

*이 문서는 Market Pulse v2 설계 회의에서 현행 시스템의 기준선(baseline)으로 사용됩니다.*
*다른 AI 에이전트(@frontend, @backend, @investment-advisor, @UI-UX-designer)와 상의 시 이 문서를 참조하세요.*
