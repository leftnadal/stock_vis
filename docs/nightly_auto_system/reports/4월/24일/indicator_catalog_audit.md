# 지표 카탈로그 동기화 감사 보고서

- 감사 일자: 2026-04-24
- 대상 파일
  - BE 정의: `thesis/services/prompt_builder.py` (`INDICATOR_CATALOG`)
  - BE 후처리: `thesis/services/llm_postprocess.py` (`normalize_llm_output`)
  - BE 매칭: `thesis/services/indicator_matcher.py` (`KEYWORD_RULES`, `match_*`)
  - FE 표시: `frontend/components/thesis/AddIndicatorSheet.tsx` (`INDICATOR_CATALOG`, `KEYWORD_INDICATOR_MAP`)
- 감사 모드: **Read-only**(코드 변경 없음)

---

## 요약 (동기화 상태)

| 항목 | 결과 | 비고 |
|------|------|------|
| 카탈로그 ID 집합 (BE ↔ FE) | **일치** | 양쪽 64개 동일 |
| 카탈로그 ID → 이름 | **부분 불일치** | 4건(id=6,7,30,54)에서 FE가 BE보다 축약 표기 |
| 카탈로그 ID → 업데이트 주기(`freq`) | **일치** | BE `INDICATOR_FREQUENCY`와 FE `freq` 동일 |
| 카테고리 구조 | **이질적** | BE 5개 상위 vs FE 17개 세부 — 설계상 의도 가능 |
| description 품질 | **양호** | 모든 64개에 description 존재, 최단 24자 |
| `KEYWORD_RULES`(BE) 고아 | **없음** | 전부 CATALOG 내 존재 |
| `KEYWORD_INDICATOR_MAP`(FE) 고아 | **없음** | 전부 CATALOG 내 존재 |
| BE ↔ FE 키워드 룰 커버리지 | **큰 격차** | BE 11개 그룹 vs FE 28개 그룹 — BE 누락 약 18개 |
| `data_params` 포맷 | **혼종** | 4종 포맷 공존(fmp symbol / fmp metric / fred / metrics / news) |
| FMP 필드명 실제성 | **일부 위험** | `revenueGrowthYoY`, `foreign_net_buy`, `institutional_net_buy` 표준 FMP 필드 아님 |

**핵심 리스크 Top 3**
1. BE `KEYWORD_RULES`가 FE 대비 크게 뒤처져 있어, LLM이 `indicator_db_id`를 빠뜨리고 전제 텍스트만 반환할 때 BE fallback 품질이 FE 추천 품질에 못 미친다.
2. BE catalog의 일부 `data_params.metric` 값이 실제 FMP 엔드포인트 필드와 다르다. 예: `revenueGrowthYoY`, `foreign_net_buy`, `institutional_net_buy`.
3. BE `INDICATOR_CATALOG`와 FE `INDICATOR_CATALOG`가 각각 하드코딩되어 있어, 카탈로그 변경 시 두 곳을 수동으로 동기화해야 한다(feedback_indicator_catalog_sync 메모리와 일치).

---

## BE ↔ FE 불일치 목록

### 1) ID 집합

- BE (`prompt_builder.py:14-294`) **64개**: 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 20, 21, 22, 23, 24, 25, 26, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 46, 47, 50, 51, 52, 53, 54, 55, 56, 57, 58, 60, 61, 62, 63, 64, 65, 66, 67, 68, 69, 70, 71, 72, 73
- FE (`AddIndicatorSheet.tsx:15-91`) **64개**: 위 집합과 동일

→ **동일**. BE-only / FE-only 지표 없음.

### 2) 동일 ID, 다른 이름 (사용자 표시 라벨 표류)

| id | BE 이름 (`prompt_builder.py`) | FE 이름 (`AddIndicatorSheet.tsx`) | 영향 |
|----|-------------------------------|-----------------------------------|------|
| 6 | `미국 기준금리 (Fed Funds Rate)` | `미국 기준금리` | FE에서 영문명 누락 — 프롬프트 표기와 UI 표기 차이 |
| 7 | `미국 10년 국채 금리` | `미국 10년 국채` | FE가 "금리" 생략 |
| 30 | `미국 2년 국채 금리` | `미국 2년 국채` | 동상 |
| 54 | `부채비율 (Debt/Equity)` | `부채비율 (D/E)` | 부기 표기 상이 |

영향 범위
- `match_indicators_for_llm()`은 ID로 조회 후 CATALOG 이름을 결과에 채운다(`indicator_matcher.py:297`). FE가 같은 ID로 저장된 지표를 표시할 때는 FE 로컬 이름이 쓰이므로, 사용자가 "가설 빌더 LLM 출력"과 "지표 추가 시트"에서 같은 지표를 다른 라벨로 보게 된다.

### 3) 카테고리 구조

- BE (`CATEGORY_LABELS`): `market_data / macro / technical / fundamental / sentiment` (5개, LLM 프롬프트 그룹핑용)
- FE (`categoryOrder`): `수급 / 주요 지수 / 원자재 / 암호화폐 / 금리 / 환율/변동성 / 고용/성장 / 물가/주택 / 기술적 / 펀더멘털 / 재무 체질 / 밸류에이션 / 성장 / 운영 효율 / 이익 품질 / 주주환원 / 심리` (17개, UI 세부 그룹핑용)

→ 의도적 이질성으로 보이지만, BE가 카테고리를 프롬프트에 노출하므로 LLM은 거시/시장/기술/펀더/심리 5분류만 인식한다. FE가 보여주는 "재무 체질/밸류에이션/성장/운영 효율/이익 품질/주주환원"은 모두 BE에서는 `fundamental`로 묶인다. **불일치가 아니라 설계 격차**.

### 4) 업데이트 주기(`freq` vs `INDICATOR_FREQUENCY`)

전 64개 ID를 대조한 결과 불일치 없음. 예:
- id=6 `주간` ✓ / id=7 `일간` ✓ / id=34 `분기` ✓ / id=31 `월간` ✓ / id=37 `주간` ✓.

---

## description 품질

BE `INDICATOR_CATALOG` 64개 전부 `description` 필드를 가진다.

| 검사 | 결과 |
|------|------|
| 빈 description | **0건** |
| 10자 미만 | **0건** |
| 최단 description | id=14 `코스닥 지수` → `한국 중소형 성장주 시장 지수.` (15자) |
| 중복 description | 0건 (모두 상이) |

FE는 description을 보유하지 않고 `category`/`freq`만 표시한다. 즉, **BE description은 프롬프트(`build_indicator_block`)에는 쓰이지 않으며**(프롬프트에는 이름+주기만 노출), `get_indicator_description()` 경로를 통해서만 소비된다.

**검토 권장 포인트 (품질 이슈는 아님)**
- `get_indicator_description()`을 호출하는 경로가 현재 `thesis` 앱 내 어디에서 쓰이는지 점검 — 미사용이라면 dead path 가능성. (본 감사 범위 밖)

---

## keyword_rules 고아

### BE `KEYWORD_RULES` (`indicator_matcher.py:12-154`)

**지표 참조 방식**: 이름 문자열. 11개 그룹 전부 CATALOG에 존재.

| # | 대표 키워드 | 참조 이름 | CATALOG 존재 |
|---|-------------|----------|-------------|
| 1 | 외국인/순매수 | `외국인 순매수 추이` | ✓ (id:1) |
| 2 | 금리/연준 | `미국 기준금리 (Fed Funds Rate)`, `미국 10년 국채 금리` | ✓ (id:6, 7) |
| 3 | VIX/변동성 | `VIX (공포지수)` | ✓ (id:8) |
| 4 | 환율/달러 | `원/달러 환율` | ✓ (id:9) |
| 5 | RSI/MACD | `RSI (14일)` | ✓ (id:10) |
| 6 | 센티먼트/뉴스 | `뉴스 센티먼트` | ✓ (id:11) |
| 7 | 실적/EPS | `EPS 추이` | ✓ (id:5) |
| 8 | 기관 | `기관 순매수 추이` | ✓ (id:2) |
| 9 | S&P/나스닥 | `S&P 500` | ✓ (id:3) |
| 10 | 코스피 | `KOSPI 지수` | ✓ (id:4) |
| 11 | 선거/정치 | `VIX (공포지수)`, `KOSPI 지수` | ✓ (id:8, 4) |

→ **고아 규칙 0건**. 단, `'MACD'`, `'이동평균'`, `'MA'` 키워드가 RSI만 매칭하고 실제 MACD(id:40), SMA(id:45/46), EMA(id:47) 카탈로그 엔트리에는 매핑되지 않는다(**커버리지 누락**).

### FE `KEYWORD_INDICATOR_MAP` (`AddIndicatorSheet.tsx:109-139`)

**지표 참조 방식**: 숫자 ID. 28개 그룹 전부 유효한 카탈로그 ID 참조.

| 검사 | 결과 |
|------|------|
| CATALOG에 없는 ID 참조 | **0건** |
| 중복 키워드 그룹 | 0건 |
| 존재하는 ID이지만 카테고리가 상이 | — (FE 카테고리 기준 매칭이므로 해당 없음) |

### 커버리지 격차 (BE가 FE 대비 누락한 키워드 그룹)

BE `KEYWORD_RULES`에 없고 FE `KEYWORD_INDICATOR_MAP`에만 있는 그룹:

| FE 키워드 | 매핑 지표 ID | BE 누락 영향 |
|-----------|------------|------------|
| 유가/원유/WTI | 21 | BE는 "원유" 관련 전제에서 지표 추천 실패 |
| 금/Gold/안전자산 | 20 | 동상 |
| 구리/Dr. Copper | 23 | 동상 |
| 천연가스/LNG | 24 | 동상 |
| 비트코인/암호화폐 | 25, 26 | 동상 |
| PER/PBR/밸류에이션 | 50, 51, 67, 68 | 밸류에이션 전제 추천 불가 |
| ROE/ROA/수익성 | 52, 53, 57, 62, 60, 61 | 수익성 전제 추천 불가 |
| 부채/레버리지/유동성 | 54, 63, 64, 65 | 재무건전성 전제 추천 불가 |
| 배당/FCF/주주환원 | 55, 56, 66, 68, 73 | 현금흐름/환원 전제 추천 불가 |
| 회전율/효율/재고 | 70, 71 | 운영 효율 전제 추천 불가 |
| 이익 품질/발생액 | 72, 66 | 회계 품질 전제 추천 불가 |
| 인플레/CPI/물가 | 33 | CPI 전제 추천 불가 |
| 고용/실업/NFP | 31, 32 | 고용지표 전제 추천 불가 |
| GDP/성장/산업생산 | 34, 35 | 거시 성장 전제 추천 불가 |
| 주택/부동산/모기지 | 36, 37 | 동상 |
| 반도체/테크/AI/NVIDIA | 12, 3 | — (지수만 매핑이라 우선순위 낮음) |
| 중국/항셍 | 16 | 동상 |
| 일본/니케이 | 15 | 동상 |
| 광고/디지털/플랫폼 | 3, 12 | 동상 |

→ **BE 키워드 커버리지가 약 18개 그룹 부족**. 이는 `match_indicators_for_premise()`의 fallback 품질에 직접 영향.

운영상 의미: 현재 `match_indicators_for_llm()`은 1순위로 LLM이 `indicator_db_id`를 정확히 지정한 경우만 신뢰하고, 누락 시 `match_by_keywords()`만 사용한다(`indicator_matcher.py:307`에서 `match_by_gemini`는 고의적으로 제외). 따라서 BE 키워드 룰이 빈약할수록 "LLM이 ID를 빠뜨린 전제"는 지표 없이 통과한다.

### 추가 관찰

- BE 키워드 `'MACD'`, `'이동평균'`, `'MA'`가 `RSI (14일)`만 추천하도록 매핑되어 있다(`indicator_matcher.py:68-77`). MACD·SMA·EMA 엔트리가 CATALOG에 존재하므로(id:40, 45, 46, 47), 키워드가 실제 해당 지표를 가리키도록 매핑되지 않은 **의미적 고아**에 가깝다.

---

## data_params 형식

### BE 실제 포맷 분류

| 포맷 | `data_source` | 예시 | 개수(대략) |
|------|---------------|------|-----------|
| A. FMP 심볼 | `fmp` | `{'symbol': '^GSPC'}`, `{'symbol': 'GCUSD'}`, `{'symbol': 'USDKRW'}`, `{'symbol': 'DX-Y.NYB'}` | 14 |
| B. FMP 수급/펀더 metric | `fmp` | `{'metric': 'foreign_net_buy'}`, `{'metric': 'eps'}`, `{'metric': 'peRatioTTM'}`, `{'metric': 'revenueGrowthYoY'}` | 13 |
| C. FMP 기술적 indicator | `fmp` | `{'indicator': 'RSI', 'period': 14}`, `{'indicator': 'MACD', 'fast': 12, 'slow': 26, 'signal': 9}` | 9 |
| D. FRED 시리즈 | `fred` | `{'series_id': 'FEDFUNDS'}`, `{'series_id': 'DGS10'}`, `{'series_id': 'CPIAUCSL'}` | 12 |
| E. 내부 metrics | `metrics` | `{'metric_code': 'gross_margin'}`, `{'metric_code': 'roic'}` | 14 |
| F. 뉴스 센티먼트 | `news_sentiment` | `{}` | 1 |
| G. FMP 환율(ticker 직결) | `fmp` | `{'symbol': 'USDKRW'}` | (A에 포함) |

→ **총 6종 포맷 혼재**. `fmp` 하나 안에서도 `symbol` / `metric` / `indicator` 3가지 키를 쓴다. 데이터 제공자 계층(가상 `FmpClient`/`FredClient`/metrics 서비스)이 `data_source` 분기 후 다시 내부 키를 분기 해석해야 한다.

### 실제 제공자와의 형식 일치성 점검

아래는 **도메인 지식과 CLAUDE.md에 기록된 알려진 버그(#14 FMP Key Metrics 필드명)** 를 기준으로 한 정적 검토 결과다. 실제 API 호출 로그/응답까지 대조하지는 않았다.

**A. FMP 심볼 (`data_params.symbol`)** — 14건
- `^GSPC`, `^KS11`, `^IXIC`, `^DJI`, `^KQ11`, `^N225`, `^HSI`, `^VIX` — FMP `/stable/quote` 호환 ✓
- `GCUSD`, `CLUSD`, `SIUSD`, `HGUSD`, `NGUSD` — FMP 원자재 상품 티커 규약 ✓
- `BTCUSD`, `ETHUSD` — FMP 암호화폐 티커 ✓
- `USDKRW` — FMP FX 티커 ✓
- `DX-Y.NYB` (id:39 달러 인덱스) — **주의**: FMP에서 달러 인덱스를 `DXY` 또는 `=USD` 계열로 표기하는 경우가 있음. 실제 `GET /stable/quote?symbol=DX-Y.NYB`가 404/빈 응답을 반환할 수 있어 호출 로그 확인 필요.

**B. FMP metric (`data_params.metric`)** — 13건
- `foreign_net_buy` (id:1), `institutional_net_buy` (id:2) — **표준 FMP 필드 아님**. FMP는 한국 수급 데이터를 제공하지 않는다. 외부 소스 매핑 또는 자체 계산 파이프라인이 전제되어야 하며, `data_source: 'fmp'`라는 태깅이 오해를 유발한다.
- `eps` (id:5) — FMP는 `eps` 또는 `epsTTM` 모두 상황별로 등장. 정확한 엔드포인트 명세 필요.
- `peRatioTTM`, `pbRatioTTM`, `returnOnEquityTTM`, `returnOnAssetsTTM`, `debtToEquityTTM`, `freeCashFlowTTM`, `dividendYieldTTM`, `operatingProfitMarginTTM` — FMP `/stable/key-metrics-ttm` 표준 필드. CLAUDE.md 알려진 버그 #14 참고(`returnOnEquityTTM`은 *100 필요, `earningsYieldTTM`의 역수가 PE).
- `revenueGrowthYoY` (id:58) — **표준 FMP 필드 아님**. FMP는 `/stable/income-statement-growth`의 `growthRevenue` 또는 `financial-growth`의 `revenueGrowth`를 제공. "YoY"는 계산 속성이다. 데이터 제공자 계층에서 별도 매핑/계산이 필요.

**C. FMP indicator (`data_params.indicator`)** — 9건
- `RSI`, `MACD`, `stochastic`, `bollinger`, `ATR`, `OBV`, `SMA`, `EMA` — FMP `/stable/technical-indicators/*` 엔드포인트 군과 이름 매핑 필요.
- `stochastic` 값은 FMP 쪽에서는 `stochasticoscillator` 또는 `stoch`로 표기되는 경우가 있어, 제공자 클라이언트의 소문자 정규화가 전제되어야 한다. 표기 계약이 명문화돼 있지 않으면 위험.
- `bollinger`(id:42) — FMP에서 정확한 키는 `bb` 또는 `bollingerbands`이며 `%B`는 파생 계산. 단일 파라미터 표기 대비 실제 제공자 응답과의 간극이 가장 큰 축.

**D. FRED (`data_params.series_id`)** — 12건
- `FEDFUNDS`, `DGS10`, `DGS2`, `MORTGAGE30US`, `UNRATE`, `PAYEMS`, `GDPC1`, `INDPRO`, `CPIAUCSL`, `HOUST`, `DEXUSEU` — 모두 실제 FRED series ID. ✓
- 포맷 일관성 높음, 위험 낮음.

**E. metrics (`data_params.metric_code`)** — 14건
- `gross_margin`, `net_margin`, `roic`, `current_ratio`, `interest_coverage`, `net_debt_to_ebitda`, `fcf_margin`, `ev_to_ebitda`, `fcf_yield`, `operating_income_growth`, `dso`, `asset_turnover`, `accruals_ratio`, `net_shareholder_yield` — 내부 `metrics` 앱의 지표 코드. 실제 `metrics/*`에 동일 코드가 정의돼 있는지 별도 교차 검증이 필요(본 감사 범위 밖, @backend가 `metrics` 앱 정의와 대조 권장).

**F. news_sentiment** — 1건(id:11)
- `data_params: {}` — 정의상 파라미터 없음. 소비자가 기본 계산 규칙을 알고 있어야 한다는 점에서 **암묵적 계약** 존재.

### FE 측 data_params

FE `INDICATOR_CATALOG`에는 `data_params`가 없고 `(id, name, category, freq)`만 유지한다. 즉, BE-FE 간 `data_params` 불일치 자체는 발생할 수 없으며, **BE-제공자 간 불일치**가 유일한 위험축이다.

### 결론 (data_params)

| 카테고리 | 상태 |
|---------|------|
| FMP 심볼 | 대체로 정확 (id:39 `DX-Y.NYB` 확인 필요) |
| FMP metric (수급 2개) | `foreign_net_buy`/`institutional_net_buy`는 FMP 표준 아님 — 제공자 계층 매핑 필수, 오해 유발 |
| FMP metric (펀더 9개) | FMP key-metrics-ttm과 대체로 일치, 단 `revenueGrowthYoY`는 계산 필드 |
| FMP indicator (기술) | FMP 실제 키와의 매핑 규약이 명문화돼야 함 (`stochastic`, `bollinger`) |
| FRED | 일치, 위험 낮음 |
| metrics | 내부 코드와 교차 검증 필요 |
| news_sentiment | 암묵적 계약 |

---

## 부록: 참고 위치

- BE 카탈로그: `thesis/services/prompt_builder.py:14-294`
- BE 주기표: `thesis/services/prompt_builder.py:305-326`
- BE description 조회: `thesis/services/prompt_builder.py:332-345`
- BE 카탈로그 검증(후처리): `thesis/services/llm_postprocess.py:82-94`
- BE 키워드 룰: `thesis/services/indicator_matcher.py:12-154`
- BE LLM 매칭(PK 우선): `thesis/services/indicator_matcher.py:271-329`
- FE 카탈로그: `frontend/components/thesis/AddIndicatorSheet.tsx:15-91`
- FE 주기 스타일: `frontend/components/thesis/AddIndicatorSheet.tsx:95-100`
- FE 키워드 맵: `frontend/components/thesis/AddIndicatorSheet.tsx:109-139`
- FE 카테고리 순서: `frontend/components/thesis/AddIndicatorSheet.tsx:211-216`

> 본 보고서는 읽기 전용 감사이며 소스 파일을 수정하지 않았다.
