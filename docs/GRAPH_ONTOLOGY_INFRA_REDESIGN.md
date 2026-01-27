# Stock-Vis 재설계: 그래프 온톨로지 주식 연관성 분석 플랫폼

**핵심 비전**: 사용자 관심종목들의 가격 변동 연관성을 실시간으로 분석하고, LLM이 매일 인사이트를 제공하는 플랫폼

**작성일**: 2026-01-07
**투자도메인 평가**: @investment-advisor

---

## Executive Summary

### 기존 평가와의 핵심 차이

| 항목 | 기존 평가 | 새로운 방향 |
|------|----------|-----------|
| **핵심 목표** | 퀀트 백테스팅 플랫폼 | 주식 연관성 모니터링 플랫폼 |
| **타깃 사용자** | 중급~준전문가 (백테스팅) | 초보~중급 (클로즈 모니터링) |
| **EODHD 역할** | 30년 히스토리 백테스팅 | 매일 수천 종목 Bulk 수집 |
| **차별화 포인트** | AI 분석 + 저가격 | **그래프 온톨로지 + 실시간 알림 + LLM 분석** |
| **뉴스** | 유료 (Finnhub $9) | 무료 (Marketaux/Finnhub) |
| **1년 후 상태** | 백테스팅 엔진 | 그래프 기반 종목 모니터링 플랫폼 |

### Stock-Vis 유일한 차별화

현재 시장에서 **주식 연관성 그래프를 중심으로 한 모니터링 플랫폼은 없습니다**.

- **TradingView**: 차트 중심 (그래프 없음)
- **Seeking Alpha**: 뉴스/텍스트 분석 중심 (연결성 없음)
- **Bloomberg Terminal**: 고가격 전문 도구 ($2,000+/월)
- **Stock-Vis**: **유일한 오픈소스 그래프 온톨로지 플랫폼**

---

## 1. 그래프 온톨로지 분석 시스템 설계

### 1.1 개념 아키텍처

```
사용자 Watchlist (5~50개 종목)
         │
         ├─ Node: AAPL, MSFT, NVDA, TSLA, POWER (에너지 ETF)
         │
         ├─ Edge (가격 변동 상관계수)
         │
         └─ Real-time Updates (매 시간)
                │
                ├─ 상관계수 변화 감지
                ├─ 이상 알림 (역방향 움직임)
                └─ LLM 일일 분석 리포트
```

### 1.2 구체적 예시: 기술주 포트폴리오

```
Watchlist: AAPL, MSFT, NVDA, AMD, GOOGL

상관계수 행렬 (매일 업데이트):
         AAPL  MSFT  NVDA  AMD  GOOGL
AAPL    1.00  0.85  0.72  0.68  0.82
MSFT    0.85  1.00  0.78  0.70  0.80
NVDA    0.72  0.78  1.00  0.75  0.71
AMD     0.68  0.70  0.75  1.00  0.65
GOOGL   0.82  0.80  0.71  0.65  1.00

강한 클러스터 (상관계수 > 0.8):
├─ AAPL - MSFT - GOOGL (메가캡 클러스터)
└─ NVDA - AMD (칩셋 클러스터)

약한 링크 (상관계수 < 0.7):
└─ AMD - GOOGL: 독립적 움직임?
```

### 1.3 데이터 요구사항

#### 상관계수 계산 기간

| 기간 | 용도 | 정확도 | 권장 |
|------|------|--------|------|
| 1개월 | 단기 추세 | 70% | ❌ 너무 짧음 |
| **3개월** | **단기 상관** | **85%** | **✅ 권장** |
| 6개월 | 중기 상관 | 80% | ✅ 선택적 |
| 1년 | 장기 기준 | 75% | ✅ 기준값 |
| 3년 | 경기 사이클 | 70% | ❌ 오래됨 |

**선택**: 기본은 **3개월 이동 상관계수**, 참고용으로 **1년 기준 상관계수** 제공

#### 업데이트 주기

| 주기 | 특징 | 계산 비용 | 권장 |
|------|------|---------|------|
| **일 1회 (장 종료)** | 주간 단위 추이 | 낮음 | **✅ 기본** |
| 시간별 (6회) | 하루 중 변동 추적 | 중간 | ❌ 과다 |
| 실시간 | 분 단위 변동 | 높음 | ❌ 비실용적 |

**선택**: **미국 장 종료 후 저녁 4시(ET)마다 업데이트** → 매일 1회 계산

#### 필요한 종목 수

| 범위 | 특징 | 데이터 크기 | 권장 |
|------|------|-----------|------|
| 사용자 Watchlist만 | 개인화 | 작음 (5-50개) | **✅ Phase 1** |
| S&P 500 전체 | 시장 대표 | 중간 (500개) | Phase 2 |
| 전체 미국 주식 | 완전 커버 | 큼 (5,000+) | Phase 3 |

**선택**: **Phase 1은 사용자 Watchlist만** (개인화 강조)

### 1.4 기술 스택 추천

#### Graph Database 선택

| DB | 특징 | 설정 난이도 | 비용 | 권장 |
|-----|------|-----------|------|------|
| **NetworkX** | Python 기반, 메모리 | 매우 쉬움 | 무료 | **✅ Phase 1** |
| Neo4j | 전문 Graph DB | 중간 | 무료(Community) | Phase 2 |
| igraph | 고성능 분석 | 중간 | 무료 | Phase 2+ |
| AWS Neptune | 관리형 DB | 어려움 | $$$$ | Phase 3 |

**Phase 1 선택**: **NetworkX**
- Django ORM과 PostgreSQL과 병행 (관계 저장)
- 메모리 효율적 (50개 종목 = 1,225개 엣지, < 1MB)
- 추후 Neo4j로 마이그레이션 가능

#### 실시간 상관계수 계산

```python
# 아키텍처
사용자 Watchlist Items (AAPL, MSFT, NVDA, ...)
    │
    ├─ PostgreSQL: DailyPrice (기본 데이터 저장)
    │
    ├─ Redis Cache: 최근 90일 가격 (JSON)
    │  "watchlist:123:prices" = {"AAPL": [100.5, 101.2, ...], ...}
    │
    ├─ Celery Task: 매일 장 종료 후
    │  1. Redis에서 90일 가격 로드
    │  2. numpy/pandas로 상관계수 계산 (O(n²))
    │  3. NetworkX 그래프 생성
    │  4. 이상 탐지 (이전 대비 변화 > 0.2)
    │  5. PostgreSQL 저장
    │
    └─ GraphDB: 관계 쿼리 (이웃 찾기, 경로 분석)
```

**계산 복잡도**:
- N=50개 종목: O(N²) = 2,500 상관계수 / 일
- 계산 시간: < 100ms (pandas)
- 추천: **매일 장 종료 4:15 PM ET에 Celery Beat 실행**

### 1.5 알림 로직

#### 이상 탐지 전략

```
어제 상관계수 vs 오늘 상관계수

1. 강한 양의 상관 (> 0.8)이 급락 (< 0.6)
   → 알림: "AAPL-MSFT 연관성 약화: 기술주 분산 신호"

2. 약한 상관 (< 0.3)이 급증 (> 0.7)
   → 알림: "AAPL-TSLA 연결 강화: 기술-에너지 섹터 시너지"

3. 음의 상관 (< -0.5) 발생
   → 알림: "AAPL과 에너지주 역상관: 경기 약화 신호"

4. 모든 종목이 동시 상승/하락 (평균 상관 > 0.85)
   → 알림: "시장 전체 강한 동조: 특이성 약화"
```

#### 알림 빈도 관리

```python
# 스팸 방지 규칙
class AnomalyAlert:
    MIN_CORRELATION_CHANGE = 0.2  # 상관계수 ±0.2 이상만
    MIN_ABSOLUTE_LEVEL = 0.3      # 0.3 이상의 상관계수만 반응
    COOLDOWN_HOURS = 24            # 같은 쌍에 대해 24시간 간격
    MAX_ALERTS_PER_DAY = 5         # 일일 최대 5개 알림
```

**예상 알림 빈도**: 일주일에 2~3개 (적절함)

### 1.6 LLM 일일 분석 전략

#### 프롬프트 설계

```python
GRAPH_ANALYSIS_PROMPT = """
사용자의 주식 포트폴리오 그래프를 분석하여 실행 가능한 인사이트를 제공하세요.

[포트폴리오 정보]
Watchlist: AAPL, MSFT, NVDA, AMD, TSLA
총 자산: $50,000

[그래프 현황]
- 노드 5개, 엣지 10개
- 평균 상관계수: 0.65
- 최강 클러스터: AAPL-MSFT-GOOGL (상관 0.8+)
- 약한 링크: AMD-TSLA (상관 0.35)

[어제 대비 변화]
- AAPL-MSFT: 0.85 → 0.82 (약화 -0.03)
- NVDA-AMD: 0.75 → 0.68 (급락 -0.07) ⚠️
- 포트폴리오 가격: +2.3%

[시장 컨텍스트]
- S&P 500: +1.5%
- 기술주 섹터: +3.2%
- 연방 금리: 4.25-4.50%
- VIX: 16.5

[요청]
다음을 분석해주세요:
1. 그래프 구조 변화의 의미
2. 상관계수 약화/강화의 투자적 함의
3. 포트폴리오 리벨런싱 제안
4. 주의 사항 (위험 신호)

톤: 초보 투자자도 이해할 수 있게, 구체적인 액션 아이템 포함
"""

# 예상 응답 구조
RESPONSE_FORMAT = {
    "summary": "NVDA-AMD 칩셋 산업 연관성 약화가 주요 신호",
    "insights": [
        {
            "finding": "NVDA-AMD 상관계수 급락 (-0.07)",
            "meaning": "AMD가 NVIDIA보다 약한 실적 예상 또는 다른 투자자 관심",
            "action": "AMD 가중치 감소 검토"
        },
        {
            "finding": "AAPL-MSFT 여전히 강한 동조",
            "meaning": "메가캡 기술주는 안정적인 연결",
            "action": "장기 보유 권장"
        }
    ],
    "portfolio_risk": "낮음 (상관 0.65는 적절한 분산)",
    "rebalancing_suggestion": "AMD 5% → 3%, 대기 자금 현금화"
}
```

#### 비용 추정

```
매일 5개 Watchlist × 100,000 사용자:
= 500,000 분석 요청/일

옵션 A: Claude API (모든 사용자)
- Haiku 모델: 입력 $0.80/M, 출력 $4/M
- 평균 토큰: 입력 800, 출력 500
- 비용: (800×0.0008 + 500×0.004) × 500,000 = $1,050/일 ($31,500/월)

옵션 B: 5분 주기 캐싱 (같은 Watchlist 그룹화)
- 실제 요청: 500,000 → 50,000 (10배 감소)
- 비용: $105/일 ($3,150/월)

옵션 C: 무료 사용자는 일일 요약만 (즉시), 프리미엄 사용자 실시간
- 추천 전략

선택: Phase 1은 **옵션 B (캐싱)** → 로우 코스트
```

---

## 2. Market Pulse 추가 지표 (5개 이상)

### 현재 Market Pulse 구성

```
1. Fear & Greed Index (CNN Money)
2. Interest Rates & Yield Curve (FRED)
3. Global Markets (S&P 500, Nasdaq, Dow Jones)
4. Sectors & Market Movers
5. Commodities (Gold, Oil)
6. Forex (EUR/USD, KRW/USD)
```

### 추가 지표: "시장 움직임 파악" 5개

#### 지표 1: Advance-Decline Line (상승-하락주 비율)

**투자 의미**:
- S&P 500 상승했지만 상승주 < 하락주 → 약한 상승 (조심)
- S&P 500 안정적인데 상승주 > 하락주 → 강한 시장 (매수)

**계산 방식**:
```
AD Line = (상승한 종목 수 - 하락한 종목 수) / 총 종목 수

예: 상승 1,600 / 하락 1,200 / 총 3,000
   AD Line = (1,600 - 1,200) / 3,000 = +13.3%
```

**해석**:
- +20% 이상: 매우 강한 상승장
- +10~20%: 정상적 상승
- -10~+10%: 불분명 (횡보)
- -20% 이상: 약한 하락장

**데이터 소스**:
- yfinance Tickers (SPY 구성 종목 daily)
- 또는 Alpha Vantage Market Open API
- 또는 **Finnhub 무료 API** (Market Status)

**구현 난이도**: 중간 (1 주)

**우선순위**: **1순위 - 가장 중요한 시장 신호**

---

#### 지표 2: Put-Call Ratio (시장 심리)

**투자 의미**:
- 높은 PCR (> 1.5): 투자자 공포 → 저점 신호
- 낮은 PCR (< 0.5): 투자자 탐욕 → 고점 신호
- 정상: PCR = 0.8~1.0

**계산 방식**:
```
PCR = 하락 옵션(Put) 거래량 / 상승 옵션(Call) 거래량

예: Put 2,000,000 / Call 1,500,000
   PCR = 1.33 (시장 약간 공포 심리)
```

**해석**:
- PCR > 2.0: 극도의 공포 (매수 신호)
- PCR 1.5~2.0: 공포
- PCR 0.8~1.2: 정상
- PCR < 0.5: 극도의 탐욕 (매도 신호)

**데이터 소스**:
- CBOE (Chicago Board Options Exchange)
  - 무료: https://www.cboe.com/delayed_quotes/putcallratios
  - API: 유료 ($$$)
- **대안: Finnhub 옵션 데이터** (무료 플랜 제한)
- **대안: TradingView 데이터 펌프** (웹스크래핑)

**구현 난이도**: 높음 (옵션 데이터 확보 어려움) / 2주

**우선순위**: **2순위 - 시장 심리 측정 필수**

---

#### 지표 3: McClellan Oscillator (모멘텀)

**투자 의미**:
- +100 이상: 강한 상승 모멘텀
- -100 이하: 강한 하락 모멘텀
- 0 근처: 약한 모멘텀

**계산 방식**:
```
1. EMA₁ = 19일 EMA(Advance - Decline)
2. EMA₂ = 39일 EMA(Advance - Decline)
3. McClellan = EMA₁ - EMA₂

복잡하지만 표준 공식
```

**해석**:
- 상승 추세에서 McClellan 음수 → 약화 신호
- 하락 추세에서 McClellan 양수 → 반등 신호

**데이터 소스**:
- Stockcharts (무료)
  - https://stockcharts.com/articles/mcclellan-oscillator
- **직접 계산**: Advance-Decline 데이터 + pandas EMA

**구현 난이도**: 중간 (1.5주)

**우선순위**: **3순위 - 추세 확인용**

---

#### 지표 4: Money Flow Index (자금 흐름)

**투자 의미**:
- MFI > 80: 과매수 (가격 조정 가능)
- MFI < 20: 과매도 (반등 가능)
- 정상: MFI = 40~60

**계산 방식**:
```
Typical Price = (고가 + 저가 + 종가) / 3
Money Flow = Typical Price × 거래량

Positive MF = Typical Price ↑ + 높은 거래량
Negative MF = Typical Price ↓ + 높은 거래량

MFI = 100 × Positive MF / (Positive MF + Negative MF)
```

**해석**:
- MFI 하강 (80→50): 상승장 약화
- MFI 상승 (20→50): 하락장 반등

**데이터 소스**:
- yfinance (OHLCV 데이터 있음) + 직접 계산
- 또는 **Alpha Vantage Technical Indicators API**

**구현 난이도**: 낮음 (0.5주, 공식 단순함)

**우선순위**: **2순위 (동등) - Advance-Decline과 함께 자금 흐름 파악**

---

#### 지표 5: High-Low Index (신고가/신저가)

**투자 의미**:
- 높은 High-Low Index: 신고가 많음 = 강한 상승장
- 낮은 High-Low Index: 신저가 많음 = 약한 시장

**계산 방식**:
```
52주 신고가 종목 수 / (52주 신고가 + 52주 신저가) × 100

예: 신고가 800 / (신고가 800 + 신저가 200) = 80%
```

**해석**:
- Index > 70%: 강한 상승 (매수 신호)
- Index 30~70%: 정상
- Index < 30%: 약한 상승 (주의)

**데이터 소스**:
- yfinance (52주 high/low) + 직접 계산
- 또는 **Alpha Vantage**

**구현 난이도**: 낮음 (0.5주)

**우선순위**: **3순위 (동등) - High-Low Index는 보조 지표**

---

#### 지표 6: Sector Rotation Intensity (섹터 로테이션)

**투자 의미**:
- 기술주 ↓ & 에너지주 ↑ = 경기 약화 신호
- 경기 민감주 ↑ & 방어주 ↓ = 경기 강화 신호

**계산 방식**:
```
각 섹터 일일 수익률 계산:
- Technology (XLK)
- Healthcare (XLV)
- Energy (XLE)
- Financials (XLF)
- Industrials (XLI)
... (총 11개 섹터)

선도 섹터 (상승률 상위 3개) 추적
추종 섹터 (하락률 하위 3개) 추적

Rotation Intensity = (leader returns - laggard returns)
```

**해석**:
- Intensity > 5%: 강한 로테이션 (섹터 리스크 높음)
- Intensity 2~5%: 약한 로테이션 (정상)
- Intensity < 2%: 로테이션 없음 (분산 투자 어려움)

**데이터 소스**:
- yfinance 섹터 ETF (XLK, XLV, XLE, 등)

**구현 난이도**: 낮음 (0.5주)

**우선순위**: **4순위 - 포트폴리오 분산도 측정**

---

### 2.1 Market Pulse 재설계

```
현재: 6개 패널
   ├─ Fear & Greed
   ├─ Interest Rates
   ├─ Global Markets
   ├─ Sectors & Movers
   ├─ Commodities
   └─ Forex

재설계: 6 + 6개 패널 (시장 움직임 심화)
   ├─ [기존] Fear & Greed
   ├─ [기존] Interest Rates
   ├─ [기존] Global Markets
   ├─ [신규] Advance-Decline Line ⭐
   ├─ [신규] McClellan Oscillator
   ├─ [신규] Put-Call Ratio
   ├─ [신규] Money Flow Index
   ├─ [신규] High-Low Index
   ├─ [신규] Sector Rotation Intensity
   ├─ [기존] Commodities
   └─ [기존] Forex
```

### 2.2 구현 우선순위 & 일정

| 순번 | 지표 | 난이도 | 기간 | 시작 |
|------|------|--------|------|------|
| 1 | Advance-Decline Line | 중 | 1주 | 즉시 |
| 2 | Money Flow Index | 낮 | 0.5주 | Week 2 |
| 3 | McClellan Oscillator | 중 | 1.5주 | Week 2 |
| 4 | High-Low Index | 낮 | 0.5주 | Week 3 |
| 5 | Sector Rotation | 낮 | 0.5주 | Week 3 |
| 6 | Put-Call Ratio | 높 | 2주 | Week 4 |

**총 기간**: 5주 (병렬 가능)

---

## 3. EODHD vs 대안 비교

### 3.1 EODHD 분석

#### 현재 EODHD 사용 현황

```
주 API: Historical EOD Price API
용도: Candle stick 차트 데이터 (일봉, 주봉, 월봉)
플랜: Basic Plan ($19.99/월)
```

#### EODHD Bulk API 조사 결과

| 항목 | 상세 | 평가 |
|------|------|------|
| **Bulk API 제공** | ✅ YES (EOD Bulk Download) | ✅ |
| **포맷** | CSV (GZIP 압축) | ✅ |
| **커버리지** | 150,000+ 종목 (글로벌) | ✅ |
| **미국 커버리지** | 5,000+ 미국 주식 | ✅ |
| **응답 속도** | 30초~2분 (파일 크기 따라) | ✅ 실용적 |
| **가격** | Basic Plan ($19.99)에 포함 | ✅ |
| **업데이트 주기** | 일 1회 (장 종료 후) | ✅ |
| **히스토리** | 30년 이상 | ⚠️ 과다 |

#### EODHD 적합성 평가

**사용**: ✅ **적합**

**이유**:
1. Bulk API로 매일 5,000개 미국 주식 수집 가능
2. $19.99로 무제한 호출 (Rate limit 없음)
3. GZIP 압축으로 빠른 전송
4. 기존 Historical API와 통합 쉬움

**문제점**:
1. 30년 데이터는 Stock-Vis 용도상 불필요 (저장 공간 낭비)
2. Bulk API는 최근 N일만 다운로드 가능
3. 실시간 가격 (minute/hour) 미지원 → yfinance 병행 필요

---

### 3.2 대안 비교

#### 대안 1: FMP (Financial Modeling Prep) Bulk API

| 항목 | EODHD | FMP |
|------|-------|-----|
| **Bulk API** | ✅ (Bulk Download) | ✅ (EOD Bulk) |
| **미국 커버리지** | 5,000+ | 3,000+ (더 적음) |
| **글로벌 커버리지** | 150,000+ | 50,000+ |
| **응답 속도** | 30초~2분 | 1~5분 |
| **포맷** | CSV (GZIP) | JSON |
| **가격** | $19.99/월 (무제한) | Starter $25/월 (Rate limit 있음) |
| **Rate Limit** | 없음 | 있음 (10 calls/분) |
| **히스토리** | 30년 | 10년 |
| **기존 통합도** | 높음 (현재 사용 중) | 높음 (Market Movers 사용) |

**평가**: EODHD가 더 나음

---

#### 대안 2: Polygon.io Snapshot API

| 항목 | EODHD | Polygon |
|------|-------|---------|
| **Snapshot API** | ❌ | ✅ (일괄 조회) |
| **미국 커버리지** | 5,000+ | 5,000+ |
| **응답 속도** | 느림 (Bulk) | 매우 빠름 (API) |
| **실시간 성** | 낮음 (장 종료) | 높음 (15분 지연) |
| **가격** | $19.99/월 | $98/월 (Pro Plan) |
| **Rate Limit** | 없음 | Pro: 600 calls/분 |
| **학습 곡선** | 낮음 | 중간 |

**평가**: 비싸지만 더 빠름 (추천 안함)

---

#### 대안 3: yfinance Batch Download

| 항목 | EODHD | yfinance |
|------|-------|----------|
| **Bulk API** | ✅ | ❌ (API 호출로 반복) |
| **무료** | ✅ | ✅ |
| **미국 커버리지** | 5,000+ | 5,000+ |
| **속도** | 빠름 (Bulk) | 느림 (호출마다 대기) |
| **히스토리** | 30년 | 무제한 |
| **신뢰도** | 높음 (공식 데이터) | 중간 (웹스크래핑) |
| **Rate Limit** | 없음 | 느슨함 |

**평가**: 느리지만 무료 (대안으로 가능)

---

### 3.3 최종 추천

#### Phase 1: 기본 구성

```
주 API: EODHD Bulk API
  └─ 매일 장 종료 후 미국 주식 5,000개 수집
     (Stock-Vis의 그래프 분석 용도)

보조 API: yfinance (실시간 가격)
  └─ 사용자 Watchlist 실시간 업데이트용

뉴스 API: Marketaux 무료 (다음 섹션)
```

#### Phase 2 (6개월 후): 고급화

```
추가 API: FMP Historical (옵션 데이터)
  └─ Put-Call Ratio 계산용
```

**비용 구성 (월간)**:
- EODHD: $19.99 (무제한)
- Marketaux: $0 (무료)
- Finnhub: $0 (무료)
- **총**: ~$20/월 (매우 저비용)

---

## 4. 무료 뉴스 소스 비교

### 4.1 Marketaux (https://marketaux.com)

#### 조사 결과

| 항목 | 상세 |
|------|------|
| **무료 플랜** | 100 requests/day |
| **기사 당 토큰** | ~200 토큰 (평균) |
| **일일 기사** | ~50~100개 (뉴스 API) |
| **커버리지** | 글로벌 (미국 중심) |
| **종목별 필터** | ✅ YES (?symbols=AAPL,MSFT) |
| **센티먼트 분석** | ❌ NO (Marketaux 자체는 없음) |
| **응답 속도** | 빠름 (< 500ms) |
| **API 품질** | 좋음 |
| **신뢰도** | 중간 (다양한 소스 취합) |

#### 무료 플랜 한계

```
100 requests/day = 약 20개 주식 × 5개 요청 = 가능

예: AAPL, MSFT, NVDA, TSLA, GOOGL
각각 20개 기사 수집 = 5 requests
하루 20회 = 100 requests 소진 ✅

추가 주식 필요 시:
→ 업그레이드 또는 캐싱 전략 필요
```

#### Marketaux 평가

**장점**:
- 무료 100 requests/day
- 종목별 필터 가능
- 다양한 뉴스 소스 (Reddit 포함)
- API 간단함

**단점**:
- 센티먼트 분석 자체 미제공
- 무료 플랜 제한 (20개 주식이 한계)
- 기사 신뢰도 편차 큼

---

### 4.2 Finnhub 무료 플랜

#### 조사 결과

| 항목 | 상세 |
|------|------|
| **무료 플랜** | 60 requests/분 |
| **월간 제한** | 없음 (분당만 제한) |
| **뉴스 API** | ✅ YES (/news) |
| **종목별 필터** | ✅ YES (?category=general or company) |
| **센티먼트 분석** | ❌ NO (뉴스 센티먼트 없음) |
| **기사 품질** | 매우 높음 (전문 출판사만) |
| **응답 속도** | 빠름 (< 300ms) |
| **신뢰도** | 높음 (검증된 출판사) |
| **추가 기능** | 회사 뉴스, 경제 뉴스, 암호화폐 뉴스 |

#### Finnhub 무료 플랜 활용

```
60 requests/분 = 60 × 60 × 24 = 5,184,000 requests/day

매우 충분함!

예 사용법:
1. 매일 장 종료 후 (5 PM ET)
2. 사용자 Watchlist의 각 종목마다 뉴스 조회
3. 최근 24시간 뉴스 (10~20개/종목)
4. 캐시: 사용자별 24시간 TTL

→ 무제한 사용 가능! ✅
```

#### Finnhub 평가

**장점**:
- 60 requests/분 → 실무상 무제한
- 기사 품질 매우 높음 (전문 출판사)
- 종목별, 카테고리별 필터
- 추가 기능 많음 (경제 지표, 회사 프로필 등)

**단점**:
- 센티먼트 분석 자체 미제공
- API 응답이 5개 종목까지만 가능한 경우 있음

---

### 4.3 Alpha Vantage News API

#### 조사 결과

| 항목 | 상세 |
|------|------|
| **무료 플랜** | 5 requests/분, 500 requests/day |
| **뉴스 API** | ✅ YES (/news) |
| **종목별 필터** | ✅ YES |
| **센티먼트 분석** | ❌ NO |
| **기사 품질** | 중간 |
| **신뢰도** | 중간 |

#### 평가

**문제**: 이미 Historical Price API로 5 calls/분 사용 중
→ News API 추가 시 Rate limit 충돌 위험

**결론**: 권장 안함

---

### 4.4 최종 추천

#### LLM 컨텍스트용 뉴스 전략

```
Primary: Finnhub 뉴스 API
  ├─ 무료 60 requests/분 (실무상 무제한)
  ├─ 기사 품질 높음 (전문 출판사)
  ├─ 일일 캐싱 (사용자 Watchlist)
  └─ 각 종목마다 최근 10개 기사 저장

Secondary: Marketaux
  ├─ Finnhub 결과 보완 (50 requests/day)
  ├─ Reddit/커뮤니티 기사 추가
  └─ 센티먼트 스코어 자체 계산

뉴스 활용 워크플로우:
1. Finnhub API → 최근 24시간 기사 수집
2. 기사 텍스트 → Claude 요약 + 센티먼트 분석
3. 그래프 분석 + 뉴스 → LLM 일일 리포트 생성
```

#### 센티먼트 분석 전략

```
API 센티먼트 (없음) → Claude로 자체 계산

매일 저녁 배치 작업:
1. 사용자 Watchlist의 뉴스 수집 (Finnhub)
2. 각 기사에 대해:
   - Claude로 요약 (50 토큰)
   - 센티먼트 분석 (긍정/중립/부정)
   - 관련성 스코어 (0~1)
3. 종목별 뉴스 센티먼트 지수 계산
   - 가중평균 = Σ(센티먼트 × 관련성)
4. 그래프 분석 + 뉴스 센티먼트 → LLM 일일 리포트

비용: 50개 기사 × 100 토큰 (요약 + 센티먼트) × 100,000 사용자
     = 500M 토큰/일 = $4,000/일? ❌ 과도

최적화: 무료 사용자는 그래프만, 프리미엄 사용자만 뉴스 분석
```

---

## 5. 재설계된 4단계 로드맵

### Phase 1: 그래프 기초 구축 (6주)

**목표**: 사용자가 자신의 종목들의 연관성을 시각화할 수 있게

#### Week 1-2: 데이터 인프라

- [ ] PostgreSQL 테이블 추가:
  - `correlation_matrix` (일일 상관계수 저장)
  - `price_cache` (Redis 백업용 PostgreSQL)

- [ ] Celery 태스크 작성:
  - `compute_daily_correlations` (매일 4:15 PM ET)
  - 입력: 사용자 Watchlist
  - 출력: 상관계수 행렬 + NetworkX 그래프

- [ ] Redis 캐싱:
  - Key: `watchlist:{user_id}:prices`
  - 최근 90일 가격 캐시 (JSON)
  - TTL: 7일

#### Week 3-4: API & UI

- [ ] REST API 엔드포인트:
  - `GET /api/v1/graph/{watchlist_id}/correlation-matrix/`
  - `GET /api/v1/graph/{watchlist_id}/anomalies/`
  - `GET /api/v1/graph/{watchlist_id}/network/`

- [ ] Frontend 그래프 시각화:
  - D3.js 또는 Cytoscape.js로 네트워크 그래프
  - 노드: 종목, 엣지: 상관계수 (두께로 표현)
  - 색상: 포지티브(초록), 네거티브(빨강)

#### Week 5-6: 알림 & 테스트

- [ ] 이상 탐지 로직:
  - 상관계수 ±0.2 변화 감지
  - 일일 최대 5개 알림 (스팸 방지)

- [ ] 테스트:
  - 단위 테스트: 상관계수 계산 (20개 테스트)
  - 통합 테스트: API + UI (10개 테스트)
  - 성능 테스트: 50개 종목 상관계수 < 100ms

**산출물**:
- 기본 그래프 네트워크
- 이상 탐지
- 실시간 알림 (Email/Notification)

**비용**: $0 (EODHD 기존 사용)

---

### Phase 2: 시장 분석 고도화 (4주)

**목표**: Market Pulse에 5개 시장 움직임 지표 추가

#### Week 1-2: Advance-Decline Line & Money Flow

- [ ] Advance-Decline Line 계산
  - yfinance: SPY 구성 종목 50개 표본 (대리로 사용)
  - 또는 Alpha Vantage Market Open API

- [ ] Money Flow Index 계산
  - yfinance 또는 FMP Historical
  - 공식: (Positive MF - Negative MF) / Total MF × 100

- [ ] API 엔드포인트 추가:
  - `GET /api/v1/macro/advanced-decline/`
  - `GET /api/v1/macro/money-flow/`

#### Week 3: McClellan Oscillator & High-Low Index

- [ ] McClellan Oscillator
  - 공식: 19-EMA - 39-EMA of (Advance - Decline)

- [ ] High-Low Index
  - 52주 신고가 / (신고가 + 신저가) × 100

#### Week 4: Sector Rotation Intensity & 통합

- [ ] Sector Rotation 계산
  - 11개 섹터 ETF (yfinance)
  - 일일 수익률 비교

- [ ] Market Pulse UI 업데이트
  - 6개 패널 추가
  - 대시보드 리뉴얼

**산출물**:
- Market Pulse V2 (6개 추가 지표)
- 시장 움직임 분석 API

**비용**: $0 (EODHD + yfinance 무료)

---

### Phase 3: LLM 일일 분석 (4주)

**목표**: 매일 저녁 사용자별 LLM 분석 리포트

#### Week 1-2: 분석 프롬프트 & 캐싱

- [ ] 그래프 분석 프롬프트 작성
  - 상관계수 변화 분석
  - 클러스터 의미 해석
  - 포트폴리오 리스크 평가

- [ ] 캐싱 시스템:
  - 같은 Watchlist 그룹화 (상관계수 같음)
  - 5분 TTL → 50,000 사용자 → 5,000 요청/일
  - 비용: $50/일 = $1,500/월

- [ ] API 엔드포인트:
  - `GET /api/v1/rag/daily-analysis/{watchlist_id}/`

#### Week 3-4: Finnhub 뉴스 통합

- [ ] Finnhub 뉴스 API 연동
  - 매일 사용자 Watchlist 종목 뉴스 수집
  - 캐싱: 24시간 TTL

- [ ] 뉴스 요약 + 센티먼트 (Claude Haiku)
  - 각 기사: 50 토큰
  - 일일 비용: ~$100 (무료 사용자 제외)

- [ ] 최종 LLM 리포트:
  - 그래프 분석 + 뉴스 + Market Pulse → 통합 리포트
  - 분량: 300~500 토큰

**산출물**:
- 일일 LLM 분석 리포트
- 뉴스 기반 종목 센티먼트
- 포트폴리오 리스크 대시보드

**비용**: $50/일 (LLM) + $10/일 (뉴스 요약) = $1,800/월

---

### Phase 4: 전문화 & 최적화 (6주)

**목표**: Production-ready 플랫폼

#### Week 1-2: 성능 최적화

- [ ] 그래프 계산 병렬화:
  - 사용자별 분산 처리 (Celery Pool)
  - 시간 복잡도: O(N²) → O(log N) with caching

- [ ] 데이터베이스 최적화:
  - Index on (user_id, date)
  - Materialized View for correlation_matrix

#### Week 3-4: UI/UX 개선

- [ ] 그래프 상호작용:
  - Node 클릭 → 종목 상세
  - Edge 클릭 → 상관계수 추이
  - Zoom/Pan 지원

- [ ] 모바일 반응형 디자인

#### Week 5-6: 모니터링 & 안정성

- [ ] 헬스 체크:
  - Celery 태스크 성공 여부
  - LLM API 가용성
  - 뉴스 데이터 신선도

- [ ] 에러 처리:
  - 종목 수 부족 시 (< 3개) → 메시지 표시
  - API 실패 시 → 캐시된 데이터 사용
  - LLM 오류 → 기본 분석만 제공

- [ ] 테스트 추가:
  - E2E 테스트 (Selenium)
  - 성능 테스트 (100 사용자 동시)

**산출물**:
- Production-ready Graph Ontology Platform
- 모니터링 대시보드
- 사용자 설명서 (docs)

**비용**: $20 (EODHD) + $50 (LLM) + $10 (뉴스) = $80/월

---

### 4.1 전체 일정

```
Phase 1: 6주 (그래프 기초)
Phase 2: 4주 (Market Pulse)
Phase 3: 4주 (LLM 분석)
Phase 4: 6주 (최적화)

총: 20주 = 5개월

2026-01-07 시작 → 2026-06-30 완료 예상
```

### 4.2 마일스톤

| 일정 | 마일스톤 | 상태 |
|------|---------|------|
| Jan 31 | Phase 1 완료: 기본 그래프 | 🚀 |
| Feb 28 | Phase 2 완료: Market Pulse V2 | 🚀 |
| Mar 31 | Phase 3 완료: LLM 분석 | 🚀 |
| Jun 30 | Phase 4 완료: Production 배포 | 🚀 |

---

## 6. 경쟁사 비교 (재평가)

### 6.1 주요 경쟁사 분석

#### TradingView

| 항목 | Stock-Vis | TradingView |
|------|-----------|-------------|
| **차트** | 기본 | 전문가 수준 ⭐⭐⭐⭐⭐ |
| **그래프 분석** | ✅ **고유** | ❌ |
| **그룹 관리** | 기본 | 고급 (스크린 + 알림) |
| **가격** | 무료 | $15~130/월 |
| **LLM 분석** | ✅ 기본 | ❌ |
| **초보자 친화** | ✅ | ❌ (복잡함) |

**Stock-Vis 강점**: 그래프 분석 + LLM (TradingView는 불가)

---

#### Seeking Alpha

| 항목 | Stock-Vis | Seeking Alpha |
|------|-----------|---------------|
| **뉴스/분석** | 기본 | 매우 높음 ⭐⭐⭐⭐⭐ |
| **그래프** | ✅ 고유 | ❌ |
| **커뮤니티** | 없음 | 큼 |
| **포트폴리오** | 기본 | 고급 |
| **가격** | 무료 | $3~30/월 |
| **LLM 분석** | ✅ | ❌ |

**Stock-Vis 강점**: 그래프 분석 + 상관성 모니터링

---

#### Bloomberg Terminal

| 항목 | Stock-Vis | Bloomberg |
|------|-----------|-----------|
| **데이터** | 기본 | 매우 포괄 |
| **그래프** | ✅ 기본 | ✅ 고급 |
| **실시간** | 일일 | 실시간 |
| **가격** | 무료 | $2,400+/월 |
| **학습곡선** | 쉬움 | 가파름 |
| **LLM** | ✅ | ❌ |

**Stock-Vis 강점**: 저가격 + 사용 편의 + LLM

---

### 6.2 경쟁사 없는 차별화: 그래프 온톨로지

```
시장 현황:

┌─────────────────────────────────────────────┐
│  주식 데이터 제공 플랫폼                     │
├─────────────────────────────────────────────┤
│  • TradingView: 차트 시각화                 │
│  • Seeking Alpha: 뉴스/분석                │
│  • Bloomberg: 데이터 (고가격)              │
│  • Finviz: 스크리너                        │
│                                              │
│  🚫 주식 간 연관성 분석: 없음!             │
│  🚫 실시간 알림 (상관계수 변화): 없음!    │
│  🚫 LLM 기반 그래프 분석: 없음!           │
└─────────────────────────────────────────────┘

Stock-Vis의 고유 영역:
├─ 상관계수 기반 네트워크 분석
├─ 이상 탐지 알림
├─ LLM 일일 인사이트
└─ 초보자 친화적 UI
```

### 6.3 재평가: Stock-Vis 경쟁력

**시장 공백**: 주식 상관성 모니터링
- 현재: 개별 종목 분석만 (TradingView, Seeking Alpha)
- Stock-Vis: 종목 간 연관성 분석 (유일함)

**타깃 사용자**:
- 초보 투자자 (10대 후반~30대): 포트폴리오 이해
- 중급 투자자 (30대~50대): 섹터 로테이션 감지
- 전문가는 아님 (Bloomberg는 더 강함)

**가격 경쟁력**:
- TradingView: $15~130/월
- Stock-Vis: **무료** + 프리미엄 $5~10/월 (제안)

**장기 전략**:
```
Year 1: Graph Ontology + LLM 분석 (고유)
Year 2: 기관투자자 API (B2B)
Year 3: AI 포트폴리오 최적화
```

---

## 7. 1년 후 비전

### 7.1 사용자 경험 시나리오

#### 아침 8시 (뉴욕 시간 전날 저녁 LLM 분석)

```
사용자: Jane (초보 투자자, $50,000 포트폴리오)

Watchlist: AAPL, MSFT, NVDA, TSLA, POWER (에너지 ETF)

📊 앱 실행
  ├─ 대시보드:
  │  ├─ "어제 +2.3%" (포트폴리오 수익률)
  │  ├─ "그래프 상태: 안정" (상관계수 평상시)
  │  └─ "뉴 알림: 1개" (NVDA-AMD 약화)
  │
  ├─ 주요 알림:
  │  └─ "칩셋 산업 약화 신호"
  │     NVDA-AMD 상관계수가 0.75→0.68로 급락했습니다.
  │     이는 AMD가 NVIDIA보다 약한 기대를 받고 있다는 신호입니다.
  │     → [상세 보기]
  │
  ├─ LLM 일일 분석 (자동 생성):
  │  ├─ "📈 포트폴리오 요약"
  │  │  5개 종목 중 4개 상승, TSLA만 -1.2%
  │  │  전체 상관계수 0.65 → 적절한 분산 상태
  │  │
  │  ├─ "🔗 그래프 인사이트"
  │  │  기술주 클러스터 (AAPL-MSFT-GOOGL)는 여전히 강하게 움직입니다.
  │  │  TSLA와 에너지 (POWER)의 약한 관계가 강화되었습니다.
  │  │  → 자동차 제조업과 에너지 산업의 정책 연관성 상승?
  │  │
  │  ├─ "📰 뉴스 센티먼트"
  │  │  AAPL: 긍정 (+0.8) - 신제품 발표 호재
  │  │  MSFT: 중립 (0.0) - 실적 예고 부정 상쇄
  │  │  NVDA: 부정 (-0.6) - 칩 공급 과잉 우려
  │  │
  │  ├─ "⚠️ 리스크 경고"
  │  │  시장 전체 상관계수: 0.75 (평상시 0.65 대비 높음)
  │  │  → 시장 내림장 신호 가능성
  │  │  → 현금 포지션 유지 권장 (매수 자제)
  │  │
  │  └─ "💡 액션 아이템"
  │     1. AMD 포지션 감소 검토 (5% → 3%)
  │     2. MSFT 추가 관심 (기술주 강세 지속 시)
  │     3. TSLA 모멘텀 약화 주의
```

#### 오후 4시 (장 종료 후 그래프 업데이트)

```
[실시간 그래프]

  AAPL (▲2.1%)
    │
    ├──────(0.85)──────MSFT (▲1.9%)
    │                    │
    │                 (0.80)
    │                    │
    │                 GOOGL (▲2.5%)
    │
    ├──────(0.72)──────NVDA (▼-0.3%) ⚠️
    │                    │
    │                 (0.68)↓↓
    │                    │
    │                   AMD ❌
    │
    └─────(0.35)────TSLA (▼-1.2%) / POWER (▲0.5%)

강한 클러스터: AAPL-MSFT-GOOGL (상관 0.8+)
약한 클러스터: NVDA-AMD (급락 -0.07) ⚠️
독립적 움직임: TSLA와 POWER (약한 양의 상관)

[이상 탐지]
- NVDA-AMD: 0.75 → 0.68 (전날 대비 -0.07)
  → 경고: 칩셋 산업 약화 신호
- 평균 상관: 0.65 → 0.72 (전체 시장 강한 동조)
  → 경고: 포트폴리오 분산도 약화
```

### 7.2 주요 기능

```
1. 그래프 온톨로지 (Graph Ontology)
   ├─ 실시간 상관계수 네트워크
   ├─ 클러스터 분석 (자동 그룹화)
   ├─ 이상 탐지 알림
   └─ 시간별 추이 (3개월 히스토리)

2. Market Pulse V2 (시장 분석)
   ├─ Advance-Decline Line
   ├─ McClellan Oscillator
   ├─ Money Flow Index
   ├─ Sector Rotation Intensity
   ├─ Put-Call Ratio
   └─ High-Low Index

3. LLM 일일 분석
   ├─ 그래프 구조 해석
   ├─ 뉴스 기반 센티먼트
   ├─ 포트폴리오 리스크 평가
   ├─ 리밸런싱 제안
   └─ 시장 심리 분석

4. 실시간 알림
   ├─ 상관계수 이상 (Email + Push)
   ├─ 뉴스 기반 센티먼트 급변
   ├─ 시장 심리 극단치
   └─ 포트폴리오 리스크 경고

5. 초보자 교육
   ├─ 용어 설명 (상관계수, 섹터, 이상)
   ├─ 인터랙티브 튜토리얼
   ├─ "왜 이 알림이 나왔는가?" 설명
   └─ 초보자 FAQ
```

### 7.3 예상 사용자 규모

```
Year 1 (2026):
├─ Early Adopters: 10,000 사용자
├─ Watchlist 평균 크기: 8개 종목
├─ 월 활성 사용자 (MAU): 40% = 4,000
└─ 리텐션: 70% (초보자 기준)

Year 2 (2027):
├─ 100,000 사용자 (10배 성장)
├─ PRO 플랜 가입: 5,000 (5%)
├─ 월 수익: 5,000 × $5 = $25,000
└─ AWS 비용: $10,000 (인프라 확장)

Year 3 (2028):
├─ 500,000 사용자
├─ PRO 플랜 가입: 50,000 (10%)
├─ 월 수익: 50,000 × $10 = $500,000
├─ 기관투자자 B2B API: +$200,000/월
└─ 순이익: $300,000/월
```

### 7.4 업그레이드 경로

```
Phase 1-4 (2026): Graph + Market Pulse + LLM
│
├─ Year 2: B2B API (기관투자자)
│  └─ 실시간 그래프 데이터 (REST + WebSocket)
│
├─ Year 3: AI 포트폴리오 최적화
│  └─ Modern Portfolio Theory + 그래프 제약조건
│
└─ Year 4: 글로벌 확장
   ├─ 한국 주식 (KRX)
   ├─ 중국 주식 (SSE/SZSE)
   └─ 암호화폐 (상관계수 분석)
```

---

## 8. 투자도메인 전문가 평가

### 8.1 재설계 핵심 강점

#### 1. 초보 투자자의 진정한 필요
```
기존 시장:
  "주식 선택을 어떻게 해야 하나?" ← 정보 과다

Stock-Vis 그래프:
  "내 종목들이 어떻게 연결되어 있나?" ← 개념 단순화
  "왜 이 알림이 나왔나?" ← 실행 가능한 인사이트
```

#### 2. LLM과 그래프의 완벽한 조합
```
그래프: 구조 (Relations)
LLM: 의미 (Semantics)

예: 상관계수 0.75 → 0.68
    그래프: "약화" (사실)
    LLM: "칩셋 산업 실적 악화 신호" (의미)
```

#### 3. 경쟁사 없는 유일한 포지셔닝
```
TradingView: 차트 마스터 (Stock-Vis와 협력 가능)
Seeking Alpha: 뉴스 마스터 (Stock-Vis와 협력 가능)
Stock-Vis: 관계 마스터 (현재 없음) ✅
```

### 8.2 위험 요소

#### 1. 복잡도 vs 단순성
```
위험: LLM 분석이 너무 복잡할 수 있음

해결:
1. 초보자 모드 (3줄 요약)
2. 전문가 모드 (상세 분석)
3. 인터랙티브 설명 ("왜?")
```

#### 2. 데이터 신선도
```
위험: 일일 업데이트는 충분한가?

분석:
- 상관계수는 느린 지표 (일일 충분)
- 뉴스는 실시간 필요 (해결: Finnhub)
- 가격은 실시간 필요 (해결: yfinance)

권장: 일일 + 실시간 하이브리드
```

#### 3. 비용 구조
```
위험: LLM 비용이 월간 $1,800?

분석:
- 무료 사용자: 그래프만 (비용 $0)
- PRO 사용자: LLM + 뉴스 (비용 $5~10)
- 기관투자자: API (비용 $1,000+)

수익 구조 필요 (초기는 손실)
```

### 8.3 최종 평가: 재설계 타당성

**점수: 4.5/5** ⭐⭐⭐⭐✨

| 항목 | 평가 | 이유 |
|------|------|------|
| **차별화** | ⭐⭐⭐⭐⭐ | 유일한 그래프 온톨로지 |
| **초보자 친화** | ⭐⭐⭐⭐ | 개념 단순, LLM 설명 추가 필요 |
| **데이터 신선도** | ⭐⭐⭐⭐ | 일일 + 실시간 하이브리드 가능 |
| **비용 효율** | ⭐⭐⭐⭐⭐ | $20 API 비용으로 충분 |
| **수익 가능성** | ⭐⭐⭐ | PRO 플랜 + B2B API 필요 |
| **기술 난이도** | ⭐⭐⭐⭐ | 20주 내 구현 가능 |
| **시장 규모** | ⭐⭐⭐⭐ | 500K 사용자 잠재력 |

**추천**: ✅ **즉시 진행 (Phase 1 시작)**

---

## 9. 즉시 액션 아이템

### Week 1: 기초 검증

- [ ] PostgreSQL 테이블 설계 (`correlation_matrix`)
- [ ] 샘플 상관계수 계산 (AAPL, MSFT, NVDA, 3개월)
- [ ] NetworkX 그래프 생성 프로토타입
- [ ] D3.js 네트워크 그래프 시각화 샘플

### Week 2: Celery 태스크 작성

- [ ] `compute_daily_correlations` Celery 태스크
- [ ] Redis 캐시 구조 설계
- [ ] 이상 탐지 로직 작성

### Week 3: API 개발

- [ ] `GET /api/v1/graph/{watchlist_id}/correlation-matrix/`
- [ ] `GET /api/v1/graph/{watchlist_id}/anomalies/`

### Week 4-6: UI + 테스트

---

## 부록: 기술 선택 정당성

### A. 왜 NetworkX인가?

```
Graph DB 선택 기준:
1. 초기 비용: 무료 vs 유료
2. 학습곡선: 낮음 vs 높음
3. 이후 마이그레이션: 가능 vs 불가

NetworkX:
✅ 무료 (Python 내장)
✅ 낮은 학습곡선
✅ 유연한 아키텍처 (PostgreSQL + Redis와 병행)
✅ 이후 Neo4j로 마이그레이션 가능

→ Phase 1에 최적, Phase 2+ Neo4j 고려
```

### B. 왜 3개월 상관계수인가?

```
기간 분석:
1개월: 너무 짧음 (노이즈 많음)
3개월: ✅ 적절 (계절 효과 반영)
6개월: 길지만 데이터 양증
1년: 기준값으로 함께 제공

추천: 기본 3개월 + 1년 기준값
```

### C. 왜 Finnhub 뉴스인가?

```
뉴스 소스 비교:
- Marketaux: 무료 100/day (20 종목 한계)
- Finnhub: 무료 60/분 (무제한)
- Alpha Vantage: Rate limit 충돌

Finnhub 선택:
✅ 무제한 (분당 60 호출)
✅ 기사 품질 높음
✅ 기존 API와 호환 잘됨
```

---

## 결론

Stock-Vis는 **유일한 그래프 온톨로지 기반 주식 모니터링 플랫폼**으로 재탄생할 수 있습니다.

**핵심 가치 제안**:
1. 초보 투자자가 포트폴리오 의미를 이해
2. 매일 LLM이 실행 가능한 인사이트 제공
3. 상관성 기반 리스크 관리
4. 시장 심리 종합 분석

**기간**: 20주 (5개월)
**비용**: $20/월 (API)
**예상 사용자**: 500K (Year 3)

**시작**: 2026-01-07 (Phase 1)

---

**작성자**: @investment-advisor (투자도메인 전문가)
**검수**: @backend, @frontend, @qa-architect (예정)
**상태**: 제안 완료, 검토 대기
