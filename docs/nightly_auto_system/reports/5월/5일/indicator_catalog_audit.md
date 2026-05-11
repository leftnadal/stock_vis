# 지표 카탈로그 동기화 감사 보고서

- **감사일**: 2026-05-06
- **감사자**: 야간 자동 감사 시스템 (read-only)
- **대상 파일**:
  - BE 정의: `thesis/services/prompt_builder.py:14-294` (INDICATOR_CATALOG, 64개)
  - BE 후처리: `thesis/services/llm_postprocess.py:82-89` (id 검증)
  - BE 매칭: `thesis/services/indicator_matcher.py:12-154` (KEYWORD_RULES, 11개 룰)
  - BE 페처: `thesis/tasks/eod_pipeline.py:25-194` (DATA_SOURCE_FETCHERS)
  - FE 표시: `frontend/components/thesis/AddIndicatorSheet.tsx:15-91` (INDICATOR_CATALOG, 64개) + `:109-139` (KEYWORD_INDICATOR_MAP, 28개 룰)

---

## 요약 (동기화 상태)

| 검사 항목 | 상태 | 비고 |
|-----------|------|------|
| BE ↔ FE id/이름 동기화 | ✅ 완전 일치 (64개) | 모든 id, 이름, 빈도 일치 |
| BE ↔ FE 카테고리 분류 | ⚠️ 구조 차이 | BE 5개 카테고리 / FE 17개 세분 카테고리 |
| BE description 품질 | ✅ 우수 (64/64 채워짐) | 빈 description 0개, 최소 14자 |
| FE description 필드 | ❌ 미구현 | FE 카탈로그에 description 필드 자체 없음 |
| KEYWORD_RULES (BE) ↔ CATALOG | ✅ 고아 룰 0개 | 11개 지표 모두 카탈로그 존재 |
| BE keyword_rules 커버리지 | 🔴 매우 부족 | 64개 중 11개(17%)만 커버 |
| BE ↔ FE keyword_rules 동기화 | 🔴 큰 격차 | BE 11개 룰 / FE 28개 룰 (FE가 2.5배 많음) |
| data_params ↔ FMP fetcher 형식 | 🔴 심각한 불일치 | TTM 메트릭이 quote 엔드포인트에서 조회 불가 |

**핵심 문제 3건**:
1. **fetcher 미스매치**: `peRatioTTM`, `returnOnEquityTTM` 등 TTM 메트릭 14개를 `data_source='fmp'`로 선언했으나 페처는 `get_quote()`만 호출 — 해당 필드는 항상 `None` 반환됨.
2. **한국 수급 데이터 미지원**: `foreign_net_buy`, `institutional_net_buy`는 FMP 표준 quote 응답에 없음.
3. **BE keyword_rules 커버리지 부족**: 카탈로그 64개 중 11개만 매칭 — 환각 방지(LLM fallback 차단)와 연결되어 LLM이 ID를 잘못 주면 매칭 자체가 안 됨.

---

## 1. 카탈로그 항목 동기화 (BE ↔ FE)

### 1.1 ID/이름/빈도 동기화 결과

| 검사 | BE | FE | 결과 |
|------|----|----|------|
| 항목 수 | 64 | 64 | ✅ 동일 |
| ID 집합 | {1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,20,21,22,23,24,25,26,30,31,32,33,34,35,36,37,38,39,40,41,42,43,44,45,46,47,50,51,52,53,54,55,56,57,58,60,61,62,63,64,65,66,67,68,69,70,71,72,73} | 동일 | ✅ 일치 |
| 이름 | (전체 일치) | (전체 일치) | ✅ 64/64 일치 |
| 빈도 (freq) | INDICATOR_FREQUENCY 매핑 | freq 필드 | ✅ 64/64 일치 |

**BE에만 있고 FE에 없는 항목**: 없음
**FE에만 있고 BE에 없는 항목**: 없음

### 1.2 카테고리 분류 차이 (구조적 불일치)

BE는 5개 광역 카테고리 (`market_data`, `macro`, `technical`, `fundamental`, `sentiment`)로 분류.
FE는 17개 세분 카테고리 (`수급`, `주요 지수`, `원자재`, `암호화폐`, `금리`, `환율/변동성`, `고용/성장`, `물가/주택`, `기술적`, `펀더멘털`, `재무 체질`, `밸류에이션`, `성장`, `운영 효율`, `이익 품질`, `주주환원`, `심리`)로 분류.

**예시 매핑 (id별)**:
| id | 이름 | BE category | FE category |
|----|------|-------------|-------------|
| 1 | 외국인 순매수 추이 | market_data | 수급 |
| 3 | S&P 500 | market_data | 주요 지수 |
| 20 | 금 (Gold) | market_data | 원자재 |
| 25 | 비트코인 (BTC) | market_data | 암호화폐 |
| 6 | 미국 기준금리 | macro | 금리 |
| 8 | VIX | macro | 환율/변동성 |
| 31 | 실업률 | macro | 고용/성장 |
| 33 | CPI | macro | 물가/주택 |
| 67 | EV/EBITDA | fundamental | 밸류에이션 |
| 69 | 영업이익 성장률 | fundamental | 성장 |
| 70 | DSO | fundamental | 운영 효율 |
| 72 | 발생액 비율 | fundamental | 이익 품질 |
| 73 | 순주주수익률 | fundamental | 주주환원 |

**영향도**: 낮음 (display 전용). 단, BE/FE에서 카테고리 기반 그룹핑/필터를 시도하면 결과가 달라짐.
**권장**: FE의 17개 세분 카테고리를 BE에 `subcategory` 필드로 추가하거나, FE를 `category` (광역) + `subcategory` (세분)의 2단 구조로 통일.

### 1.3 FE에 누락된 필드

FE `CatalogIndicator` 인터페이스는 `id`, `name`, `category`, `freq` 4개만 보유. BE에서 제공하는 다음 필드가 FE에 없음:
- `description` (모든 항목)
- `data_source` (실제 호출 경로)
- `data_params` (파라미터)
- `support_direction` (positive/negative — 추세 해석용)

**영향도**: 중간. 사용자가 지표 선택 시 description을 볼 수 없음(`AddIndicatorSheet`는 이름만 표시). 단, 다른 화면(`IndicatorCatalog` 등)에서 BE description을 별도로 fetch할 가능성 존재.

---

## 2. description 필드 품질

### 2.1 BE description 통계

- **총 항목**: 64개
- **빈 description**: 0개
- **10자 미만**: 0개
- **최소 길이**: 14자 (id=14 "코스닥 지수": "한국 중소형 성장주 시장 지수.")
- **최대 길이**: 약 50자
- **평균**: ~30자 추정

**품질 평가**: ✅ 양호. 모든 description이 한 문장으로 지표의 의미와 시장적 함의를 함께 담고 있음.

샘플:
- id=8 VIX: "S&P 500 옵션 내재변동성. 시장 공포와 불확실성 수준 측정." (32자)
- id=23 구리: "구리 선물 가격. 경기 선행지표로 \"Dr. Copper\"라 불림." (33자)
- id=72 발생액 비율: "순이익 대비 발생액 비율. 높을수록 이익의 현금 품질이 낮음." (32자)

### 2.2 FE description 부재

FE `CatalogIndicator` 타입에 `description` 필드 자체가 없음. `AddIndicatorSheet.tsx:218-261`의 `renderButton`은 `name`, `freq`만 표시.

→ BE의 잘 작성된 description이 실제 사용자 화면에 노출되지 않음.

**권장**: FE 카탈로그에 description을 추가하거나, BE에서 `/api/v1/thesis/indicators/catalog/`로 fetch하여 사용.

---

## 3. indicator_matcher.py의 keyword_rules

### 3.1 KEYWORD_RULES 구조

`thesis/services/indicator_matcher.py:12-154`. 11개 룰, 각 룰은 `keywords` 배열 + `indicators` 배열.

| 룰 # | 키워드 (대표) | 매칭 지표 (이름) | 카탈로그 id |
|------|-------------|-----------------|-------------|
| 1 | 외국인, foreign | 외국인 순매수 추이 | 1 |
| 2 | 금리, FOMC, fed | 미국 기준금리, 미국 10년 국채 금리 | 6, 7 |
| 3 | VIX, 공포, 변동성 | VIX (공포지수) | 8 |
| 4 | 환율, 달러, USD | 원/달러 환율 | 9 |
| 5 | RSI, MACD, 기술적 | RSI (14일) | 10 |
| 6 | 센티먼트, 뉴스, 심리 | 뉴스 센티먼트 | 11 |
| 7 | 실적, EPS, earnings | EPS 추이 | 5 |
| 8 | 기관, 연기금 | 기관 순매수 추이 | 2 |
| 9 | S&P, 나스닥, NASDAQ | S&P 500 | 3 |
| 10 | 코스피, KOSPI | KOSPI 지수 | 4 |
| 11 | 선거, 정치, 정책 | VIX, KOSPI 지수 | 8, 4 |

### 3.2 고아 규칙 (orphan rules) 검사

**KEYWORD_RULES → CATALOG**: 모든 11개 룰의 indicator 이름이 CATALOG에 존재함. ✅ 고아 룰 0개.

검증 코드: `indicator_matcher.py:332-338`의 `_find_in_catalog()`가 이름 기반으로 카탈로그를 조회하여 보장.

### 3.3 카탈로그 커버리지 부족 (역방향)

CATALOG의 64개 지표 중 KEYWORD_RULES에서 참조되는 것은 **11개(17%)**뿐. 53개(83%)는 키워드 매칭이 불가능.

**커버되지 않는 카테고리**:
- 시장 지수: NASDAQ(12), 다우존스(13), 코스닥(14), 니케이(15), 항셍(16) — 5개 중 0개 커버
- 원자재: 금(20), 원유(21), 은(22), 구리(23), 천연가스(24) — 5개 중 0개 커버
- 암호화폐: BTC(25), ETH(26) — 2개 중 0개 커버
- 추가 금리: 2년(30), 모기지(37) — 2개 중 0개 커버
- 추가 환율: 달러/유로(38), DXY(39) — 2개 중 0개 커버
- 거시 고용/성장: 31~36 — 6개 중 0개 커버
- 추가 기술적: 41~47 — 7개 중 0개 커버
- 추가 펀더멘털 (50~58, 60~73): 24개 중 1개(EPS=5)만 커버

**영향도**: **높음**.
- `match_indicators_for_llm()` 흐름(`indicator_matcher.py:271-329`)은 LLM이 잘못된 `indicator_db_id`를 줬을 때 `match_by_keywords` fallback에 의존.
- 그러나 BE keyword_rules가 좁기 때문에 fallback이 실패하면 빈 결과 반환 → 환각 차단의 안전망이 약함.

### 3.4 BE ↔ FE keyword_rules 동기화

FE `KEYWORD_INDICATOR_MAP` (`AddIndicatorSheet.tsx:109-139`)은 28개 룰로 BE의 11개보다 풍부. 다만 FE만 구현된 룰이 많아 동일한 키워드 입력에서 BE/FE 추천 결과가 달라짐.

| 영역 | BE 룰 수 | FE 룰 수 | 격차 |
|------|---------|---------|------|
| 외국인/기관 수급 | 2 | 2 | 동일 |
| 금리 | 1 | 1 | 동일 |
| VIX/변동성 | 1 | 1 | 동일 |
| 환율/달러 | 1 | 1 | 동일 |
| 미국 시장 (S&P/NASDAQ) | 1 (S&P 500만) | 1 (S&P 500 + NASDAQ) | FE가 NASDAQ까지 커버 |
| 한국 시장 | 1 | 1 | 동일 |
| 원자재 (유가/금/구리/가스) | 0 | 4 | FE만 |
| 암호화폐 | 0 | 1 | FE만 |
| 기술적 (RSI/MACD) | 1 | 1 | 동일 |
| 실적 (EPS/PER 등) | 1 (EPS만) | 1 (7개 지표 매핑) | FE가 광범위 |
| 밸류에이션 (PER/PBR/EV) | 0 | 1 | FE만 |
| 수익성 (ROE/ROIC) | 0 | 1 | FE만 |
| 부채/유동성 | 0 | 1 | FE만 |
| 배당/자사주/FCF | 0 | 1 | FE만 |
| 운영 효율/이익 품질 | 0 | 2 | FE만 |
| 인플레/CPI | 0 | 1 | FE만 |
| 고용/실업 | 0 | 1 | FE만 |
| GDP/성장 | 0 | 1 | FE만 |
| 주택/모기지 | 0 | 1 | FE만 |
| 뉴스/심리 | 1 | 1 | 동일 |
| 반도체/테크/AI | 0 | 1 | FE만 |
| 중국/홍콩 | 0 | 1 | FE만 |
| 일본/엔화 | 0 | 1 | FE만 |
| 광고/플랫폼 | 0 | 1 | FE만 |
| 정치/선거 | 1 | 0 | BE만 |

**영향도**: 중간~높음.
- 동일 전제 텍스트("부채비율이 낮아진다")를 입력해도 BE는 매칭 실패 → LLM에 의존, FE는 사전 매칭 가능.
- 사용자 화면(FE 추천 패널)과 백엔드 자동 매칭(전제 등록 시 자동 추천) 결과가 일관되지 않음.

**권장**: 단일 진실 소스(SSOT)로 통일. BE에 keyword_rules를 확장하거나, 양쪽이 공통 contract 파일을 import하도록 변경.

---

## 4. data_params 형식 (실 데이터 제공자와 불일치)

### 4.1 fetcher 흐름 요약

`thesis/tasks/eod_pipeline.py:188-194`의 `fetch_indicator_value()` → `DATA_SOURCE_FETCHERS[data_source]()` 분기:

- `fmp` → `_fetch_fmp_value()` → `FMPClient.get_quote(symbol)` 호출 후 `value_map`을 통해 필드 추출
- `fred` → `_fetch_fred_value()` → `FREDClient.get_latest_value(series_id)`
- `news_sentiment` → `_fetch_news_sentiment_value()` → DB 조회 (NewsArticle.entities__symbol)
- `metrics` → `_fetch_metrics_value()` → `fetch_quarterly_metric(symbol, metric_code)` (분기 데이터)

### 4.2 FMP `value_map` 한계 (`eod_pipeline.py:53-65`)

```python
value_map = {
    'price': 'price', 'change_percent': 'changesPercentage', 'volume': 'volume',
    'pe': 'pe', 'eps': 'eps', 'market_cap': 'marketCap',
    'previous_close': 'previousClose', 'day_high': 'dayHigh', 'day_low': 'dayLow',
}
field = value_map.get(metric, metric)  # 매핑 실패 시 metric 그대로 사용
raw_value = quote.get(field)
```

`get_quote()`는 stable/quote 엔드포인트를 호출 → `price`, `marketCap`, `pe`, `eps` 등 기본 quote 필드만 제공.

### 4.3 FMP TTM 메트릭 미스매치 (🔴 심각)

CATALOG에 다음 14개 항목이 `data_source='fmp'`로 선언되었으나, FMP `quote` 엔드포인트에는 해당 필드가 없음:

| id | 이름 | 선언된 metric | quote 응답 여부 | 실제 endpoint 필요 |
|----|------|--------------|----------------|------------------|
| 50 | PER | `peRatioTTM` | ❌ (quote는 `pe` 사용) | `key-metrics-ttm` |
| 51 | PBR | `pbRatioTTM` | ❌ | `key-metrics-ttm` |
| 52 | ROE | `returnOnEquityTTM` | ❌ | `key-metrics-ttm` (×100 변환) |
| 53 | ROA | `returnOnAssetsTTM` | ❌ | `key-metrics-ttm` (×100 변환) |
| 54 | 부채비율 | `debtToEquityTTM` | ❌ | `key-metrics-ttm` |
| 55 | FCF | `freeCashFlowTTM` | ❌ | `key-metrics-ttm` |
| 56 | 배당수익률 | `dividendYieldTTM` | ❌ | `key-metrics-ttm` (×100 변환) |
| 57 | 영업이익률 | `operatingProfitMarginTTM` | ❌ | `ratios-ttm` |
| 58 | 매출성장률 | `revenueGrowthYoY` | ❌ | `financial-growth` |
| 5 | EPS 추이 | `eps` | ✅ (quote의 eps) | (분기 추이 X, 현재값만) |

**현재 실제 동작**: `quote.get('peRatioTTM')` → `None` 반환 → 모든 TTM 펀더멘털 지표가 항상 빈 값.

**관련 버그 메모** (CLAUDE.md 버그 14): "FMP Key Metrics 필드명 불일치 — `earningsYieldTTM` 역수 = PE, `returnOnEquityTTM` * 100 = ROE". 즉, `key-metrics-ttm` 엔드포인트를 별도 호출하고 변환 처리가 필요한데, 현재 페처는 미구현.

### 4.4 한국 시장 수급 데이터 미스매치 (🔴 심각)

| id | 이름 | metric | 문제 |
|----|------|--------|------|
| 1 | 외국인 순매수 추이 | `foreign_net_buy` | FMP quote에 없음. FMP는 미국 시장 위주. |
| 2 | 기관 순매수 추이 | `institutional_net_buy` | 동일 |

`get_quote()`에 symbol 파라미터가 없어 (`eod_pipeline.py:32`의 `params.get('symbol')` → `None`) **즉시 None 반환** (`eod_pipeline.py:35-37`의 워닝 후 `return None, None`). → 항상 빈 값.

**해결 방향**: KRX 또는 다른 데이터 소스 추가 필요(예: Naver Finance, KIS API 등) + 페처에 신규 분기.

### 4.5 FMP 기술적 지표 — 메트릭 키 누락

| id | 이름 | data_params | 문제 |
|----|------|-------------|------|
| 10 | RSI | `{indicator: 'RSI', period: 14}` | `value_map`에 없고 quote도 indicator 미지원 |
| 40 | MACD | `{indicator: 'MACD', fast: 12, slow: 26, signal: 9}` | 동일 |
| 41 | 스토캐스틱 %K | `{indicator: 'stochastic', period: 14}` | 동일 |
| 42 | 볼린저 밴드 %B | `{indicator: 'bollinger', period: 20}` | 동일 |
| 43 | ATR | `{indicator: 'ATR', period: 14}` | 동일 |
| 44 | OBV | `{indicator: 'OBV'}` | 동일 |
| 45 | SMA 50 | `{indicator: 'SMA', period: 50}` | 동일 |
| 46 | SMA 200 | `{indicator: 'SMA', period: 200}` | 동일 |
| 47 | EMA 12 | `{indicator: 'EMA', period: 12}` | 동일 |

페처는 `params.get('symbol')`이 없으면 즉시 `None` 반환. 따라서 위 9개 모두 **항상 None** 반환.

**필요한 endpoint**: FMP `technical-indicator/{period}/{symbol}?type=...` 또는 자체 계산 (`analysis` 앱 활용).

### 4.6 시장 지수/원자재/암호화폐 — symbol 형식 검증

다음 항목들은 페처가 `quote.get(field)`로 `field=metric` 그대로 사용. metric 누락 시 default `'price'`. 이 경우는 정상 동작 가능성 있으나 symbol 형식이 FMP 규약과 일치해야 함.

| id | 이름 | symbol | FMP 규약 호환성 |
|----|------|--------|------------------|
| 3 | S&P 500 | `^GSPC` | ✅ FMP indices는 `%5E` 인코딩 필요할 수 있음 |
| 4 | KOSPI | `^KS11` | ⚠️ FMP에서 한국 지수 지원 제한적 |
| 12 | NASDAQ | `^IXIC` | ✅ |
| 13 | 다우 | `^DJI` | ✅ |
| 14 | 코스닥 | `^KQ11` | ⚠️ FMP 비표준 |
| 15 | 니케이 | `^N225` | ✅ |
| 16 | 항셍 | `^HSI` | ✅ |
| 20 | 금 | `GCUSD` | ✅ FMP 상품 코드 |
| 21 | 원유 | `CLUSD` | ✅ |
| 22 | 은 | `SIUSD` | ✅ |
| 23 | 구리 | `HGUSD` | ✅ |
| 24 | 천연가스 | `NGUSD` | ✅ |
| 25 | BTC | `BTCUSD` | ✅ |
| 26 | ETH | `ETHUSD` | ✅ |
| 8 | VIX | `^VIX` | ✅ |
| 9 | USD/KRW | `USDKRW` | ✅ FMP forex |
| 39 | DXY | `DX-Y.NYB` | ⚠️ Yahoo 코드. FMP는 `DXY` 또는 `^DXY` 필요 가능성 |

**검증 필요**: 현재 FMP API 문서 기준 `DX-Y.NYB`, `^KS11`, `^KQ11` 호환성.

### 4.7 FRED 시리즈 ID 검증 (✅ 일관)

| id | 이름 | series_id | FRED 표준 |
|----|------|-----------|-----------|
| 6 | Fed Funds Rate | `FEDFUNDS` | ✅ |
| 7 | 10년 국채 | `DGS10` | ✅ |
| 30 | 2년 국채 | `DGS2` | ✅ |
| 31 | 실업률 | `UNRATE` | ✅ |
| 32 | NFP | `PAYEMS` | ✅ |
| 33 | CPI | `CPIAUCSL` | ✅ |
| 34 | GDP | `GDPC1` | ✅ |
| 35 | 산업생산 | `INDPRO` | ✅ |
| 36 | 주택착공 | `HOUST` | ✅ |
| 37 | 모기지 | `MORTGAGE30US` | ✅ |
| 38 | EUR/USD | `DEXUSEU` | ✅ |

11개 FRED 항목 전부 표준 series_id 사용. ✅ 페처 흐름 정상.

### 4.8 metrics (분기 재무) data_source — 별도 페처

| id 범위 | 데이터 소스 | metric_code 예시 | 페처 흐름 |
|---------|-------------|------------------|-----------|
| 60~73 (14개) | `metrics` | `gross_margin`, `roic`, `current_ratio`, `dso`, `accruals_ratio` 등 | `fetch_quarterly_metric(symbol, metric_code)` |

`metrics` 페처는 분기 데이터 fetcher를 호출. 코드 경로: `thesis/services/quarterly_metric_fetcher.py`. metric_code 일관성은 quarterly_metric_fetcher.py 내부 코드 정의와 매칭되어야 함 (별도 감사 권장).

---

## 5. 기타 발견사항

### 5.1 llm_postprocess의 id 검증

`thesis/services/llm_postprocess.py:82-89`:
```python
for ind in p.get('recommended_indicators', []):
    db_id = ind.get('indicator_db_id')
    if db_id is not None and get_indicator_by_id(db_id) is None:
        logger.info(f"indicator_db_id {db_id} not in catalog, nullified")
        ind['indicator_db_id'] = None
```

LLM이 환각으로 카탈로그 외 ID를 반환하면 None으로 무력화. ✅ 정상 동작.

### 5.2 indicator_matcher의 match_by_gemini는 의도적으로 비활성

`indicator_matcher.py:306-307`:
```python
# 2순위: PK 매칭 실패 시 키워드 룰 매칭만 사용
# (match_by_gemini fallback은 카탈로그에 없는 환각 지표를 생성하므로 제외)
```

→ 카탈로그 외 지표 생성 위험 차단 정책 일관 준수. ✅ memory `feedback_llm_indicator_hallucination.md`와 일치.

### 5.3 description 비어있는 경우 처리

`prompt_builder.py:335-345`의 `get_indicator_description()`은 정확 매칭 실패 시 접두사 매칭 → 그래도 없으면 빈 문자열 반환. 안전하게 처리.

---

## 권장 우선순위

1. **🔴 P0 — FMP TTM 메트릭 페처 구현**: 14개 펀더멘털 지표가 모두 None을 반환 중. `_fetch_fmp_value()`에 `key-metrics-ttm`/`ratios-ttm` endpoint 분기 추가 + 단위 변환(×100) 처리.
2. **🔴 P0 — 한국 수급 데이터 페처 추가**: id 1, 2(외국인/기관 순매수)는 별도 데이터 소스가 필요. KRX 또는 대체 API 도입 결정.
3. **🔴 P1 — FMP 기술 지표 페처 구현**: id 10, 40-47의 9개 지표는 별도 endpoint 또는 `analysis` 앱 데이터 활용.
4. **🟡 P2 — BE keyword_rules 확장**: FE의 28개 룰을 BE로 가져와 SSOT로 통일. 64개 카탈로그의 약 80% 커버 목표.
5. **🟡 P2 — FE 카탈로그 description 노출**: BE description을 `AddIndicatorSheet`에서 표시(툴팁 또는 보조 텍스트).
6. **🟢 P3 — 카테고리 구조 일치**: BE에 `subcategory` 필드 추가하여 FE의 17개 분류와 정합.

---

## 체크리스트 (다음 감사 시)

- [ ] FMP `key-metrics-ttm` 페처 통합 여부 확인
- [ ] `quarterly_metric_fetcher.py`의 metric_code 매핑 검증 (14개 metrics 항목)
- [ ] DXY symbol(`DX-Y.NYB`)이 FMP에서 정상 응답하는지 실측
- [ ] BE keyword_rules와 FE KEYWORD_INDICATOR_MAP을 contract 파일로 통합 가능 여부 검토
- [ ] FE에 description 노출 작업 PR 진척도

---

**감사 종료 시각**: 2026-05-06 (자동 감사 사이클)
