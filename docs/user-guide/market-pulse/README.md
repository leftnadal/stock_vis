# Market Pulse (시장 맥박)

> 거시경제 지표 및 시장 동향을 한눈에 파악하는 대시보드

## 📋 목차

1. [개요](#개요)
2. [Fear & Greed Index](#fear--greed-index)
3. [Interest Rates](#interest-rates)
4. [Global Markets](#global-markets)
5. [Market Movers](#market-movers)
6. [기술 아키텍처](#기술-아키텍처)
7. [코드 구성](#코드-구성)

---

## 개요

### 기능 정의

Market Pulse는 **거시경제 지표와 시장 심리**를 실시간으로 모니터링하는 대시보드입니다. 개별 종목 분석에 앞서 전체 시장의 방향성과 투자 환경을 파악할 수 있습니다.

### 목적

- **Top-Down 접근**: 거시 → 섹터 → 개별 종목 순서로 분석
- **리스크 관리**: 시장 과열/공포 구간 파악
- **타이밍 결정**: 금리 변화, 시장 방향성 기반 진입/청산 시점 결정
- **글로벌 상관관계**: 미국-한국 시장 간 동조화 파악

### 투자 지식

> **"Don't fight the Fed"** - 연준과 싸우지 마라

퀀트 투자자가 거시경제를 봐야 하는 이유:

1. **금리 사이클**: 금리 인상기 vs 인하기에 따라 선호 자산군 변화
   - 고금리: 성장주 ↓, 가치주/배당주 ↑
   - 저금리: 성장주 ↑, 채권 ↓

2. **시장 심리**: 공포 극단 → 저점 매수 기회, 탐욕 극단 → 차익실현 고려

3. **상관관계**: 글로벌 시장 간 리스크 온/오프 동조화
   - VIX 급등 → 모든 리스크 자산 동반 하락
   - 원/달러 환율 → 외국인 수급 파악

---

## Fear & Greed Index

### 기능 설명

CNN의 **공포/탐욕 지수**를 시각화합니다. 0~100 범위의 점수로 시장 심리를 계량화합니다.

### 지수 해석

| 점수 범위 | 상태 | 의미 | 투자 액션 |
|----------|------|------|----------|
| 0-25 | Extreme Fear | 극단적 공포 | 저점 매수 기회 탐색 |
| 25-45 | Fear | 공포 | 매수 관점 유지 |
| 45-55 | Neutral | 중립 | 시장 방향성 관찰 |
| 55-75 | Greed | 탐욕 | 익절 검토, 신규 매수 신중 |
| 75-100 | Extreme Greed | 극단적 탐욕 | 차익실현, 방어적 포지션 |

### 구성 요소 (7개)

1. **Price Momentum** (가격 모멘텀): S&P 500 vs 125일 이동평균
2. **Stock Price Strength** (주가 강도): 52주 신고가 vs 신저가 종목 수
3. **Stock Price Breadth** (시장 폭): NYSE 상승 종목 vs 하락 종목
4. **Put/Call Options** (옵션 비율): Put 대비 Call 거래량
5. **Market Volatility** (변동성): VIX vs 50일 평균
6. **Safe Haven Demand** (안전자산 수요): 주식 vs 채권 수익률
7. **Junk Bond Demand** (정크본드 수요): 투자등급 vs 하이일드 스프레드

### 데이터 소스

- **외부 API**: CNN Fear & Greed Index (웹 스크래핑 또는 대체 API)
- **업데이트 주기**: 일 1회

### API 엔드포인트

```bash
GET /api/v1/macro/fear-greed/
```

**Response:**
```json
{
  "value": 62,
  "label": "Greed",
  "updated_at": "2026-01-07T10:00:00Z",
  "components": [
    {"name": "Price Momentum", "value": 65, "label": "Greed"},
    {"name": "Stock Price Strength", "value": 58, "label": "Greed"},
    ...
  ]
}
```

### 코드 위치

- **Backend Model**: `macro/models.py` - `FearGreedIndex`
- **Backend View**: `macro/views.py` - `fear_greed_index_view()`
- **Frontend Component**: `frontend/components/market-pulse/FearGreedGauge.tsx`

---

## Interest Rates

### 기능 설명

**FRED API**를 통해 미국 주요 금리 데이터를 조회하고, **수익률 곡선(Yield Curve)**을 시각화합니다.

### 투자 지식: 수익률 곡선

**정상 곡선** (Normal Curve)
- 장기 금리 > 단기 금리
- 건강한 경제 성장 기대
- 은행 대출 활성화 → 경제 확장

**역전 곡선** (Inverted Curve)
- 단기 금리 > 장기 금리
- **경기 침체 예고 신호** (과거 정확도 높음)
- 10Y-2Y 스프레드가 -0.5% 이하 → 경기 침체 확률 80%+

**평탄 곡선** (Flat Curve)
- 단기 ≈ 장기
- 경기 불확실성, 전환기

### 주요 금리 지표

| 지표 | FRED 코드 | 의미 |
|------|----------|------|
| Fed Funds Rate | DFF | 연준 기준금리 (정책금리) |
| 2-Year Treasury | DGS2 | 2년물 국채 수익률 |
| 10-Year Treasury | DGS10 | 10년물 국채 수익률 (기준) |
| 30-Year Treasury | DGS30 | 30년물 국채 수익률 |
| 10Y-2Y Spread | T10Y2Y | 경기 침체 예측 지표 |

### 투자 전략

- **10Y-2Y 역전 발생**: 방어적 포트폴리오 전환 (유틸리티, 헬스케어)
- **금리 인상 사이클**: 은행주 ↑, 성장주 ↓
- **금리 인하 사이클**: 성장주 ↑, 채권 ↑

### 데이터 소스

- **외부 API**: FRED (Federal Reserve Economic Data)
- **인증**: `FRED_API_KEY` 환경 변수
- **업데이트 주기**: 영업일 기준 일 1회

### API 엔드포인트

```bash
GET /api/v1/macro/interest-rates/
```

**Response:**
```json
{
  "date": "2026-01-07",
  "rates": {
    "fed_funds": 5.25,
    "treasury_2y": 4.80,
    "treasury_10y": 4.50,
    "treasury_30y": 4.70
  },
  "spread_10y_2y": -0.30,
  "curve_type": "inverted"
}
```

### 코드 위치

- **Backend Model**: `macro/models.py` - `InterestRate`
- **Backend Service**: `macro/services/fred_client.py`
- **Frontend Component**: `frontend/components/market-pulse/YieldCurveChart.tsx`

---

## Global Markets

### 기능 설명

**yfinance API**를 통해 주요 지수, 섹터 ETF, 원자재, 외환 데이터를 조회합니다.

### 주요 지표

#### 1. 주요 지수
- **S&P 500** (^GSPC): 미국 대형주 500개
- **Dow Jones** (^DJI): 미국 우량주 30개
- **NASDAQ** (^IXIC): 기술주 중심

#### 2. 섹터 ETF (SPDR)
- **XLK**: Technology
- **XLF**: Financials
- **XLV**: Healthcare
- **XLE**: Energy
- **XLY**: Consumer Discretionary
- **XLP**: Consumer Staples
- 등 11개 섹터

#### 3. 원자재
- **Gold** (GC=F): 안전자산 수요
- **Crude Oil** (CL=F): 인플레이션 압력
- **Silver** (SI=F): 산업 수요

#### 4. 외환
- **USD/KRW** (KRW=X): 원/달러 환율
- **EUR/USD** (EURUSD=X): 달러 강도
- **USD/JPY** (JPY=X): 엔 캐리 트레이드

### 투자 지식: 섹터 로테이션

**경기 사이클별 강세 섹터**

| 사이클 | 섹터 | ETF | 특징 |
|--------|------|-----|------|
| 경기 회복 | Technology, Consumer Discretionary | XLK, XLY | 성장주 선호 |
| 경기 확장 | Industrials, Materials | XLI, XLB | 생산 활동 증가 |
| 경기 둔화 | Energy, Financials | XLE, XLF | 인플레이션 압력 |
| 경기 침체 | Healthcare, Consumer Staples, Utilities | XLV, XLP, XLU | 방어주 선호 |

### 데이터 소스

- **외부 API**: yfinance (Yahoo Finance)
- **특징**: 무료, Rate limit 없음
- **업데이트 주기**: 실시간 (15분 지연)

### API 엔드포인트

```bash
GET /api/v1/macro/global-markets/
```

**Response:**
```json
{
  "indices": {
    "^GSPC": {"price": 4800.50, "change": 1.2, "change_pct": 0.025},
    "^DJI": {"price": 38000.00, "change": 150.0, "change_pct": 0.004},
    "^IXIC": {"price": 15000.00, "change": 80.0, "change_pct": 0.005}
  },
  "sectors": {
    "XLK": {"price": 180.50, "change": 2.5, "change_pct": 0.014},
    ...
  },
  "commodities": {...},
  "forex": {...}
}
```

### 코드 위치

- **Backend Service**: `macro/services/yfinance_client.py`
- **Backend View**: `macro/views.py` - `global_markets_view()`
- **Frontend Component**: `frontend/components/market-pulse/GlobalMarketsGrid.tsx`

---

## Market Movers

### 기능 설명

**FMP API**를 통해 당일 **상승/하락/거래량 TOP 20 종목**을 조회하고, **5개 지표**를 계산하여 표시합니다.

### 5개 지표 시스템

#### Phase 1: 거래량 & 추세

**1. RVOL (Relative Volume)**
- **계산**: 당일 거래량 / 20일 평균 거래량
- **의미**: 평소보다 몇 배의 거래량이 발생했는가
- **해석**:
  - **2.0 이상**: 비정상적 관심도 (뉴스, 실적, 이벤트)
  - **1.5~2.0**: 높은 관심
  - **1.0 미만**: 평균 이하 (유동성 부족)

**2. Trend Strength (추세 강도)**
- **계산**: (종가 - 시가) / (고가 - 저가)
- **범위**: -1.0 ~ +1.0
- **해석**:
  - **+0.7 이상**: 강한 상승 추세 (시가 → 고가 마감)
  - **-0.7 이하**: 강한 하락 추세 (시가 → 저가 마감)
  - **0 전후**: 횡보 (방향성 없음)

#### Phase 2: 섹터 & 변동성

**3. Sector Alpha (섹터 알파)**
- **계산**: 종목 수익률 - 섹터 ETF 수익률
- **의미**: 섹터 평균 대비 초과 수익률
- **해석**:
  - **양수**: 섹터 평균보다 우수 (상대 강도)
  - **음수**: 섹터 평균보다 부진 (상대 약세)
  - **사용**: 섹터 내 종목 선별 (Long/Short)

**4. ETF Sync Rate (ETF 동행률)**
- **계산**: 피어슨 상관계수(종목 가격, 섹터 ETF 가격)
- **범위**: 0.0 ~ 1.0
- **해석**:
  - **0.8 이상**: 강한 동조 (섹터 베타 플레이)
  - **0.5~0.8**: 중간 (섹터 영향 받지만 개별성 있음)
  - **0.5 미만**: 독립적 움직임 (개별 이슈 주도)

**5. Volatility Percentile (변동성 백분위)**
- **계산**: 당일 변동성이 과거 20일 대비 몇 퍼센트 위치인가
- **범위**: 0 ~ 100
- **해석**:
  - **90 이상**: 매우 높은 변동성 (위험 또는 기회)
  - **50 전후**: 평균적 변동성
  - **10 이하**: 낮은 변동성 (횡보)

### 투자 전략 예시

**상승 종목 (Gainer) 필터링**

```python
# 조건: 강한 모멘텀 + 섹터 아웃퍼폼 + 높은 유동성
gainers = MarketMover.objects.filter(
    mover_type='gainers',
    rvol__gte=2.0,           # RVOL 2.0 이상
    trend_strength__gte=0.7, # 강한 상승 추세
    sector_alpha__gte=1.0,   # 섹터 대비 1% 이상 초과
    volatility_pct__lte=85   # 극단적 변동성 제외
)
```

**반전 종목 (Reversal) 탐색**

```python
# 조건: 과도한 하락 + 섹터는 견조 + 낮은 동행률
reversals = MarketMover.objects.filter(
    mover_type='losers',
    sector_alpha__lte=-2.0,  # 섹터 대비 2% 이상 underperform
    etf_sync_rate__lte=0.3,  # 섹터와 다른 움직임 (개별 이슈)
    rvol__gte=1.5            # 거래량 급증 (관심 집중)
)
```

### 데이터 소스

- **외부 API**: FMP (Financial Modeling Prep) Starter Plan
- **Rate Limit**: 10 calls/분, 250 calls/일
- **엔드포인트**:
  - `/stable/biggest-gainers` - 상승 TOP
  - `/stable/biggest-losers` - 하락 TOP
  - `/stable/most-actives` - 거래량 TOP
  - `/stable/quote?symbol=AAPL` - 실시간 시세 (volume 포함)
  - `/stable/historical-price-eod/full?symbol=AAPL` - OHLCV 히스토리
  - `/stable/profile?symbol=AAPL` - 섹터 정보

### API 엔드포인트

```bash
GET /api/v1/serverless/movers?type=gainers&date=2026-01-07
```

**Query Parameters:**
- `type`: 'gainers', 'losers', 'actives' (필수)
- `date`: YYYY-MM-DD (선택, 기본값: 오늘)

**Response:**
```json
{
  "success": true,
  "data": {
    "date": "2026-01-07",
    "type": "gainers",
    "count": 20,
    "movers": [
      {
        "rank": 1,
        "symbol": "ALMS",
        "company_name": "Allegro MicroSystems Inc",
        "price": "58.42",
        "change_percent": "342.80",
        "volume": 64919408,
        "rvol_display": "15.2x",
        "trend_display": "▼-0.76",
        "sector_alpha": "93.34",
        "sector_alpha_display": "+93.3%",
        "etf_sync_rate": "0.16",
        "etf_sync_display": "0.16",
        "volatility_pct": 95,
        "volatility_pct_display": "95"
      },
      ...
    ]
  }
}
```

### Celery Beat 자동 동기화

매일 **07:30 EST**에 자동으로 Market Movers 데이터를 동기화합니다.

```python
# config/settings.py
CELERY_BEAT_SCHEDULE = {
    'sync-market-movers': {
        'task': 'serverless.tasks.sync_daily_market_movers',
        'schedule': crontab(hour=7, minute=30),  # 매일 07:30 EST
        'options': {'expires': 3600}
    }
}
```

### 섹터 ETF 매핑

| 섹터 | ETF | 예시 종목 |
|------|-----|----------|
| Technology | XLK | AAPL, MSFT, NVDA |
| Financial Services | XLF | JPM, BAC, WFC |
| Healthcare | XLV | JNJ, UNH, PFE |
| Consumer Cyclical | XLY | AMZN, TSLA, HD |
| Industrials | XLI | BA, CAT, GE |
| Energy | XLE | XOM, CVX, COP |
| Utilities | XLU | NEE, DUK, SO |
| Consumer Defensive | XLP | PG, KO, WMT |
| Real Estate | XLRE | AMT, PLD, SPG |
| Basic Materials | XLB | LIN, APD, ECL |
| Communication Services | XLC | GOOG, META, DIS |

### 코드 위치

#### Backend
- **App**: `serverless/`
- **Models**: `serverless/models.py`
  - `MarketMover` - 메인 모델
  - `SectorETFMapping` - 섹터-ETF 매핑
  - `StockSectorInfo` - 종목 섹터 정보
- **Services**:
  - `serverless/services/fmp_client.py` - FMP API 클라이언트
  - `serverless/services/indicators.py` - 5개 지표 계산 로직 (순수 Python)
  - `serverless/services/data_sync.py` - 동기화 로직
- **Views**: `serverless/views.py` - REST API
- **Serializers**: `serverless/serializers.py`
- **Tasks**: `serverless/tasks.py` - Celery 태스크
- **Tests**: `tests/serverless/test_indicators.py` - 유닛 테스트 21개

#### Frontend
- **Types**: `frontend/types/market.ts` - `MarketMoverItem`
- **Service**: `frontend/services/serverlessService.ts`
- **Hook**: `frontend/hooks/useMarketMovers.ts`
- **Components**:
  - `frontend/components/market-pulse/MoverCard.tsx` - 개별 종목 카드
  - `frontend/components/market-pulse/MoversSection.tsx` - 탭 UI

---

## 기술 아키텍처

### 전체 데이터 흐름

```
┌──────────────┐
│ 외부 API     │
├──────────────┤
│ - FRED       │
│ - yfinance   │
│ - FMP        │
└──────┬───────┘
       │
       ▼
┌──────────────────────────────────┐
│ Django Backend (macro/ 앱)       │
│                                  │
│ ┌──────────────────────────────┐│
│ │ Service Layer                ││
│ │ - fred_client.py             ││
│ │ - yfinance_client.py         ││
│ └──────────────────────────────┘│
│              │                   │
│              ▼                   │
│ ┌──────────────────────────────┐│
│ │ Models (PostgreSQL)          ││
│ │ - FearGreedIndex             ││
│ │ - InterestRate               ││
│ │ - GlobalMarket               ││
│ └──────────────────────────────┘│
│              │                   │
│              ▼                   │
│ ┌──────────────────────────────┐│
│ │ Cache (Redis)                ││
│ │ TTL: 1시간                   ││
│ └──────────────────────────────┘│
│              │                   │
│              ▼                   │
│ ┌──────────────────────────────┐│
│ │ REST API Views               ││
│ │ - /api/v1/macro/pulse/       ││
│ └──────────────────────────────┘│
└───────────────┬──────────────────┘
                │
                ▼
┌──────────────────────────────────┐
│ Next.js Frontend                 │
│                                  │
│ ┌──────────────────────────────┐│
│ │ TanStack Query               ││
│ │ - useMarketPulse()           ││
│ └──────────────────────────────┘│
│              │                   │
│              ▼                   │
│ ┌──────────────────────────────┐│
│ │ Components                   ││
│ │ - FearGreedGauge             ││
│ │ - YieldCurveChart            ││
│ │ - GlobalMarketsGrid          ││
│ │ - MoversSection              ││
│ └──────────────────────────────┘│
└──────────────────────────────────┘
```

### Market Movers 아키텍처

```
FMP API (/stable/*)
    │
    ├─ biggest-gainers ────┐
    ├─ biggest-losers ─────┤
    └─ most-actives ───────┤
                           │
                           ▼
              MarketMoversSync
              (data_sync.py)
                           │
        ┌──────────────────┼──────────────────┐
        ▼                  ▼                  ▼
    FMP Quote      FMP Historical      FMP Profile
    (volume)         (20일 OHLC)        (섹터)
        │                  │                  │
        └──────────────────┴──────────────────┘
                           │
                           ▼
              IndicatorCalculator
              (순수 Python - AWS Lambda 전환 대비)
                           │
        ┌──────────────────┼──────────────────┐
        ▼                  ▼                  ▼
    Phase 1           Phase 2          Display
    RVOL, Trend    Alpha, Sync, Vol   2.5x, ▲0.83
        │                  │                  │
        └──────────────────┴──────────────────┘
                           │
                           ▼
                    PostgreSQL
                    (MarketMover)
                           │
                           ▼
                  REST API + Redis Cache
                           │
                           ▼
                   Frontend (MoverCard)
```

### 데이터베이스 스키마

#### macro 앱 (거시경제)

**FearGreedIndex**
```python
class FearGreedIndex(models.Model):
    date = models.DateField(unique=True, db_index=True)
    value = models.IntegerField()  # 0-100
    label = models.CharField(max_length=20)  # Fear, Greed 등
    components = models.JSONField(default=dict)  # 7개 구성 요소
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
```

**InterestRate**
```python
class InterestRate(models.Model):
    date = models.DateField(unique=True, db_index=True)
    fed_funds = models.DecimalField(max_digits=5, decimal_places=2, null=True)
    treasury_2y = models.DecimalField(max_digits=5, decimal_places=2, null=True)
    treasury_10y = models.DecimalField(max_digits=5, decimal_places=2, null=True)
    treasury_30y = models.DecimalField(max_digits=5, decimal_places=2, null=True)
    spread_10y_2y = models.DecimalField(max_digits=6, decimal_places=2, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
```

**GlobalMarket**
```python
class GlobalMarket(models.Model):
    symbol = models.CharField(max_length=20, db_index=True)
    category = models.CharField(max_length=20)  # index, sector, commodity, forex
    date = models.DateField(db_index=True)
    price = models.DecimalField(max_digits=12, decimal_places=2)
    change = models.DecimalField(max_digits=12, decimal_places=2)
    change_percent = models.DecimalField(max_digits=8, decimal_places=2)
    volume = models.BigIntegerField(null=True)

    class Meta:
        unique_together = [['symbol', 'date']]
```

#### serverless 앱 (Market Movers)

**MarketMover**
```python
class MarketMover(models.Model):
    date = models.DateField(db_index=True)
    mover_type = models.CharField(max_length=10)  # gainers, losers, actives
    rank = models.IntegerField()  # 1-20
    symbol = models.CharField(max_length=10, db_index=True)
    company_name = models.CharField(max_length=255)

    # 가격 정보
    price = models.DecimalField(max_digits=12, decimal_places=2)
    change_percent = models.DecimalField(max_digits=8, decimal_places=2)
    volume = models.BigIntegerField()

    # OHLC
    open_price = models.DecimalField(max_digits=12, decimal_places=2, null=True)
    high = models.DecimalField(max_digits=12, decimal_places=2, null=True)
    low = models.DecimalField(max_digits=12, decimal_places=2, null=True)

    # Phase 1 지표
    rvol = models.DecimalField(max_digits=8, decimal_places=2, null=True)
    rvol_display = models.CharField(max_length=20, null=True)
    trend_strength = models.DecimalField(max_digits=5, decimal_places=2, null=True)
    trend_display = models.CharField(max_length=20, null=True)

    # Phase 2 지표
    sector_alpha = models.DecimalField(max_digits=8, decimal_places=2, null=True)
    etf_sync_rate = models.DecimalField(max_digits=5, decimal_places=2, null=True)
    volatility_pct = models.IntegerField(null=True)

    # 메타데이터
    data_quality = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = [['date', 'mover_type', 'symbol']]
        ordering = ['date', 'mover_type', 'rank']
        indexes = [
            models.Index(fields=['date', 'mover_type']),
            models.Index(fields=['symbol', 'date']),
        ]
```

**SectorETFMapping**
```python
class SectorETFMapping(models.Model):
    sector = models.CharField(max_length=50, unique=True)  # Technology
    etf_symbol = models.CharField(max_length=10)  # XLK
    sector_name = models.CharField(max_length=100)  # Technology
    created_at = models.DateTimeField(auto_now_add=True)
```

**StockSectorInfo**
```python
class StockSectorInfo(models.Model):
    symbol = models.CharField(max_length=10, unique=True, db_index=True)
    sector = models.CharField(max_length=50, db_index=True)
    industry = models.CharField(max_length=100, null=True)
    updated_at = models.DateTimeField(auto_now=True)
```

**VolatilityBaseline**
```python
class VolatilityBaseline(models.Model):
    symbol = models.CharField(max_length=10, db_index=True)
    date = models.DateField()
    volatility = models.DecimalField(max_digits=8, decimal_places=4)
    percentile = models.IntegerField()  # 0-100
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [['symbol', 'date']]
```

#### 인덱스 전략

**조회 패턴별 최적화:**

1. **날짜별 조회** (가장 빈번)
   - `MarketMover`: `(date, mover_type)` 복합 인덱스
   - `InterestRate`, `FearGreedIndex`: `date` unique 인덱스

2. **종목별 조회**
   - `MarketMover`: `(symbol, date)` 복합 인덱스
   - `StockSectorInfo`: `symbol` unique 인덱스

3. **섹터별 조회**
   - `StockSectorInfo`: `sector` 인덱스

### 캐싱 전략

| 데이터 | TTL | 이유 |
|--------|-----|------|
| Fear & Greed | 3600초 (1시간) | 일 1회 업데이트 |
| Interest Rates | 3600초 (1시간) | 영업일 기준 일 1회 |
| Global Markets | 300초 (5분) | 실시간성 중요 |
| Market Movers | 300초 (5분) | FMP API 조회 |
| FMP Quote | 60초 (1분) | 실시간 시세 |
| FMP Historical | 3600초 (1시간) | 과거 데이터 |
| FMP Profile | 86400초 (24시간) | 섹터 정보 변경 드뭄 |

---

## 코드 구성

### Backend 디렉토리 구조

```
macro/
├── __init__.py
├── models.py                    # FearGreedIndex, InterestRate, GlobalMarket
├── views.py                     # REST API 엔드포인트
├── urls.py                      # URL 라우팅
├── serializers.py               # DRF Serializers
├── services/
│   ├── fred_client.py          # FRED API 클라이언트
│   └── yfinance_client.py      # yfinance 클라이언트
└── tasks.py                     # Celery 태스크 (예정)

serverless/
├── __init__.py
├── models.py                    # MarketMover, SectorETFMapping 등
├── views.py                     # Market Movers REST API
├── urls.py
├── serializers.py
├── services/
│   ├── fmp_client.py           # FMP API 클라이언트
│   ├── indicators.py           # 5개 지표 계산 (순수 Python)
│   └── data_sync.py            # 동기화 로직
└── tasks.py                     # Celery Beat 태스크
```

### Frontend 디렉토리 구조

```
frontend/
├── app/
│   └── market-pulse/
│       └── page.tsx             # Market Pulse 페이지
├── components/
│   └── market-pulse/
│       ├── FearGreedGauge.tsx
│       ├── YieldCurveChart.tsx
│       ├── GlobalMarketsGrid.tsx
│       ├── MoversSection.tsx
│       └── MoverCard.tsx        # 5개 지표 표시
├── hooks/
│   ├── useMarketPulse.ts
│   └── useMarketMovers.ts
├── services/
│   ├── marketService.ts
│   └── serverlessService.ts
└── types/
    └── market.ts                # MarketMoverItem 타입
```

---

## 퀀트 개발자를 위한 활용 팁

### 1. 거시 필터링 전략

```python
# 예: 금리 역전 시 방어적 포트폴리오 전환
latest_rates = InterestRate.objects.latest('date')
if latest_rates.spread_10y_2y < -0.5:
    # 경기 침체 임박 시그널
    # → Utilities (XLU), Healthcare (XLV) 비중 확대
    defensive_sectors = ['Utilities', 'Healthcare', 'Consumer Defensive']
```

### 2. Market Movers 백테스팅

```python
# 과거 데이터로 전략 검증
from serverless.models import MarketMover
from datetime import datetime, timedelta

# 최근 30일간 RVOL 2.0 이상 종목의 D+1 수익률
start_date = datetime.now() - timedelta(days=30)
high_rvol_stocks = MarketMover.objects.filter(
    date__gte=start_date,
    rvol__gte=2.0
).values('symbol', 'date', 'change_percent')

# D+1 수익률 계산 및 통계 분석
# ...
```

### 3. 섹터 로테이션 자동화

```python
# Fear & Greed + 금리 사이클 기반 섹터 선택
fear_greed = FearGreedIndex.objects.latest('date')
rates = InterestRate.objects.latest('date')

if fear_greed.value < 30 and rates.spread_10y_2y < 0:
    # 공포 + 경기 침체 우려 → 방어주
    target_sectors = ['XLU', 'XLV', 'XLP']
elif fear_greed.value > 70 and rates.fed_funds > 5.0:
    # 탐욕 + 고금리 → 차익실현
    action = 'reduce_exposure'
else:
    # 중립 → 성장주
    target_sectors = ['XLK', 'XLY']
```

### 4. API 활용 예시 (Python)

```python
import requests

# Market Movers 조회
response = requests.get('http://localhost:8000/api/v1/serverless/movers', params={
    'type': 'gainers',
    'date': '2026-01-07'
})
movers = response.json()['data']['movers']

# 필터링: RVOL 2.0 이상 + 섹터 알파 양수
filtered = [
    m for m in movers
    if float(m['rvol'].rstrip('x')) >= 2.0 and float(m['sector_alpha']) > 0
]

print(f"조건 충족 종목: {len(filtered)}개")
for stock in filtered[:5]:
    print(f"{stock['symbol']}: RVOL {stock['rvol_display']}, Alpha {stock['sector_alpha_display']}")
```

---

## 다음 단계

- [ ] **실시간 업데이트**: WebSocket을 통한 Market Movers 실시간 푸시
- [ ] **알림 시스템**: 특정 조건 충족 시 알림 (예: RVOL > 3.0)
- [ ] **백테스팅 모듈**: Market Movers 기반 전략 성과 시뮬레이션
- [ ] **ML 통합**: 5개 지표 기반 상승 확률 예측 모델

---

## 참고 자료

- [FRED API Documentation](https://fred.stlouisfed.org/docs/api/fred/)
- [FMP API Documentation](https://site.financialmodelingprep.com/developer/docs)
- [CNN Fear & Greed Index](https://edition.cnn.com/markets/fear-and-greed)
- [Investopedia - Yield Curve](https://www.investopedia.com/terms/y/yieldcurve.asp)
- [Investopedia - Sector Rotation](https://www.investopedia.com/terms/s/sectorrotation.asp)
