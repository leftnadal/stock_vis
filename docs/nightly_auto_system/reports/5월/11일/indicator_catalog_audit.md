# 지표 카탈로그 동기화 감사 보고서

- 감사일: 2026-05-11
- 모드: 읽기 전용 (코드 변경 없음)
- 감사 대상:
  - BE 정의: `thesis/services/prompt_builder.py` — `INDICATOR_CATALOG` (64개)
  - BE 후처리: `thesis/services/llm_postprocess.py` — `get_indicator_by_id` 기반 normalize
  - BE 키워드 룰: `thesis/services/indicator_matcher.py` — `KEYWORD_RULES` (11개 룰, name 기반)
  - BE Fetcher: `thesis/tasks/eod_pipeline.py` — `DATA_SOURCE_FETCHERS` (fmp/fred/news_sentiment/metrics)
  - FE 미러: `frontend/components/thesis/AddIndicatorSheet.tsx` — `INDICATOR_CATALOG` (64개), `KEYWORD_INDICATOR_MAP` (28개 룰, ID 기반)

---

## 요약 (동기화 상태)

| 항목 | 상태 | 비고 |
|---|---|---|
| BE ↔ FE ID 동기화 | ✅ OK | 양쪽 모두 동일한 64개 ID, 이름 일치 |
| description 품질 | ✅ OK | 64/64 항목에 description 존재, 모두 10자 이상 |
| BE keyword_rules 고아 | ✅ OK | 11개 룰 모두 카탈로그 name과 일치 |
| FE KEYWORD_INDICATOR_MAP 고아 | ✅ OK | 28개 룰의 모든 indicatorIds가 카탈로그에 존재 |
| BE ↔ FE keyword 룰 풍부도 | ⚠️ 비대칭 | BE 11개 vs FE 28개 (FE가 2.5배 풍부) |
| BE ↔ FE 카테고리 분류 | ⚠️ 비대칭 | BE 5종(`category` 필드) vs FE 17종(서브카테고리), 표시용 매핑이 별개 |
| data_params ↔ fetcher 일치 | ❌ 일부 불일치 | id 1·2(수급), id 10·40~47(기술적), id 11(센티먼트)에서 fetcher가 처리 불가 |
| FMP 인덱스/원자재 심볼 검증 | ⚠️ 미검증 | id 39 `DX-Y.NYB` 등 Yahoo 표기 — FMP 지원 여부 불명 |

---

## BE ↔ FE 불일치 목록

### 1) ID 일치성

- BE `INDICATOR_CATALOG` ID 집합:
  `{1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,20,21,22,23,24,25,26,30,31,32,33,34,35,36,37,38,39,40,41,42,43,44,45,46,47,50,51,52,53,54,55,56,57,58,60,61,62,63,64,65,66,67,68,69,70,71,72,73}` (64개)
- FE `INDICATOR_CATALOG` ID 집합: **동일** (64개)
- 결과: **BE만 있는 ID 없음 / FE만 있는 ID 없음**

### 2) Name 일치성

- 양쪽 모두 동일한 한국어 표기 사용 (예: `'EPS 추이'`, `'PER (주가수익비율)'`, `'미국 기준금리 (Fed Funds Rate)'`).
- 결과: **이름 불일치 없음**.

### 3) Frequency 일치성

- BE의 `INDICATOR_FREQUENCY` dict와 FE의 `freq` 필드를 ID별로 대조한 결과 모든 항목 일치.
  - 예: `6: '주간'` (BE) ↔ `{id:6, freq:'주간'}` (FE), `37: '주간'` 일치.
  - 예: `45~47 일간` 일치.

### 4) Category 표시 비대칭 (구조적 차이)

- BE `category` 필드: `market_data | macro | technical | fundamental | sentiment` (5종)
- FE `category` 필드: `수급 | 주요 지수 | 원자재 | 암호화폐 | 금리 | 환율/변동성 | 고용/성장 | 물가/주택 | 기술적 | 펀더멘털 | 재무 체질 | 밸류에이션 | 성장 | 운영 효율 | 이익 품질 | 주주환원 | 심리` (17종)
- 결과: **불일치는 아니나, FE는 BE 카테고리를 그대로 쓰지 않고 자체 분류**.
  - 영향: BE `CATEGORY_LABELS`와 프론트 카테고리 라벨이 서로 다른 분류 체계.
  - 위험: BE에서 카테고리 라벨이 변경되어도 FE에 자동 반영 안 됨 (양쪽에서 따로 관리해야 함).

### 5) 카테고리 메타데이터 차이

- BE는 항목마다 `support_direction`, `data_source`, `data_params`, `description`을 보유.
- FE 미러는 `id, name, category, freq`만 보유. **support_direction/data_source/data_params/description은 미러링 안 됨.**
- 영향: FE에서 지표 호버/툴팁으로 설명을 보여주려면 별도 API 호출 또는 `INDICATOR_CATALOG` 확장 필요.

---

## description 품질

### 빈 description

- 검사 결과: **0건**. 64/64 항목에 비어있지 않은 description 존재.

### 너무 짧은 description (< 10자)

- 검사 결과: **0건**.
- 가장 짧은 항목 후보:
  - id 14 `코스닥 지수`: `'한국 중소형 성장주 시장 지수.'` (14자)
  - id 13 `다우존스`: `'미국 우량 대형주 30개 가격 가중 지수. 전통 산업 대표.'` (30자)
- 가장 긴 항목: 대부분 30~50자, 일관성 있음.

### 권고

- description은 양호. 다만 FE 미러에는 description이 미러링되지 않아 사용자가 FE에서 지표 의미를 확인할 수 없음. (구조적 한계)

---

## keyword_rules 고아

### BE `KEYWORD_RULES` (indicator_matcher.py, name 기반)

총 11개 룰. 각 룰의 `indicators[].name`이 `INDICATOR_CATALOG`에 존재하는지 검증:

| 룰 # | 매핑된 indicator name | 카탈로그 매칭 | 비고 |
|---|---|---|---|
| 1 | 외국인 순매수 추이 | ✅ id:1 | |
| 2 | 미국 기준금리 (Fed Funds Rate), 미국 10년 국채 금리 | ✅ id:6, id:7 | |
| 3 | VIX (공포지수) | ✅ id:8 | |
| 4 | 원/달러 환율 | ✅ id:9 | |
| 5 | RSI (14일) | ✅ id:10 | |
| 6 | 뉴스 센티먼트 | ✅ id:11 | |
| 7 | EPS 추이 | ✅ id:5 | |
| 8 | 기관 순매수 추이 | ✅ id:2 | |
| 9 | S&P 500 | ✅ id:3 | |
| 10 | KOSPI 지수 | ✅ id:4 | |
| 11 (선거/정치/정책) | VIX (공포지수), KOSPI 지수 | ✅ id:8, id:4 (재사용) | |

- **고아 룰: 0건**. 모든 name이 카탈로그에 존재.
- **카탈로그에서 keyword_rules 미커버: 53/64개** (예: 모든 펀더멘털 60~73, 기술적 40~47, 원자재 20~24, 환율 38·39 등).
  - 의미: 키워드 매칭 fallback이 다수 지표를 커버하지 못함 → LLM의 `indicator_db_id` 직접 추천에 의존.
- **취약점**: `KEYWORD_RULES`는 ID가 아닌 name 기반으로 메타(data_source/data_params/support_direction)를 자체 정의. 즉 카탈로그가 수정되면 `KEYWORD_RULES`의 메타가 표류(stale)할 위험.
  - 예: id:6 `'미국 기준금리 (Fed Funds Rate)'`의 `data_params`는 카탈로그=`{'series_id':'FEDFUNDS'}`와 KEYWORD_RULES=`{'series_id':'FEDFUNDS'}` 일치 (현재 OK).
  - 예: id:9 카탈로그 `support_direction='negative'` vs KEYWORD_RULES도 `'negative'` 일치.
  - 그러나 의도치 않은 분기 발생 가능: 두 곳에서 따로 관리되는 구조는 회귀 위험.

### FE `KEYWORD_INDICATOR_MAP` (AddIndicatorSheet.tsx, ID 기반)

총 28개 룰. 각 룰의 `indicatorIds[]`가 `INDICATOR_CATALOG`에 존재하는지 검증:

- 사용 ID 합집합: `{1,2,3,4,5,6,7,8,9,10,11,12,15,16,20,21,23,24,25,26,30,31,32,33,34,35,36,37,39,40,50,51,52,53,54,55,56,57,58,60,61,62,63,64,65,66,67,68,69,70,71,72,73}` — 모두 카탈로그에 존재.
- **고아 ID: 0건**.
- **카탈로그에서 KEYWORD_INDICATOR_MAP 미커버: id 13(다우존스), id 14(코스닥), id 22(은), id 38(달러/유로), id 41~47(스토캐스틱~EMA)** 등 일부.
  - 의미: FE 사이드에서 일부 기술적 지표(스토캐스틱·볼린저·ATR·OBV·SMA·EMA)와 일부 지수(다우/코스닥/은/달러유로)는 키워드 추천에서 빠짐.

### 구조적 비대칭

- BE keyword_rules와 FE keyword 룰은 **별개의 데이터**로 관리됨.
  - BE: 11개 룰, name + 자체 메타.
  - FE: 28개 룰, ID + reason 텍스트.
- 한쪽에서 키워드 룰을 추가/수정해도 다른 쪽에 자동 반영되지 않음.
- 권고: 단일 소스(예: BE에 `KEYWORD_RULES_BY_ID` 도입 + contracts 노출, FE는 mirror) 정립이 향후 작업으로 필요.

---

## data_params 형식

### 데이터 소스별 fetcher 기대값 (`thesis/tasks/eod_pipeline.py`)

| data_source | fetcher | 필수 키 | 처리 분기 |
|---|---|---|---|
| `fmp` | `_fetch_fmp_value` | `symbol` (없으면 thesis.target fallback) | `metric.endswith('TTM')` → key-metrics-ttm; `endpoint=='financial-growth'` → financial-growth; 그 외 → `/stable/quote` + `value_map` 매핑 |
| `fred` | `_fetch_fred_value` | `series_id` | FRED `get_latest_value` |
| `news_sentiment` | `_fetch_news_sentiment_value` | `symbol` | `NewsArticle.entities__symbol=...` 평균 |
| `metrics` | `_fetch_metrics_value` | `metric_code` (+ symbol 또는 thesis.target) | `quarterly_metric_fetcher.fetch_quarterly_metric` |
| `manual`, `custom` | (없음) | — | 스킵 |

`_fetch_fmp_value`의 `value_map` 키: `price | change_percent | volume | pe | eps | market_cap | previous_close | day_high | day_low` (그 외는 metric을 그대로 quote 키로 사용).

### 카탈로그 ↔ fetcher 불일치 분석

| ID | name | data_source | data_params | fetcher 기대 | 평가 |
|---|---|---|---|---|---|
| **1** | 외국인 순매수 추이 | fmp | `{'metric':'foreign_net_buy'}` | `/stable/quote`에 `foreign_net_buy` 필드 없음 | ❌ **불일치**: FMP `/stable/quote`는 외국인 순매수를 제공하지 않음. 별도 엔드포인트/소스 필요 |
| **2** | 기관 순매수 추이 | fmp | `{'metric':'institutional_net_buy'}` | 동일 | ❌ **불일치**: FMP `/stable/quote`에 해당 필드 없음 |
| **10** | RSI (14일) | fmp | `{'indicator':'RSI','period':14}` | `_fetch_fmp_value`는 `metric` 키만 인식, `indicator` 키는 무시 → metric='price' 기본값으로 fallback | ❌ **불일치**: 기술적 지표 fetcher 분기 없음 |
| **40** | MACD | fmp | `{'indicator':'MACD','fast':12,...}` | 동일 | ❌ **불일치** |
| **41~47** | 스토캐스틱/볼린저/ATR/OBV/SMA50/SMA200/EMA12 | fmp | `{'indicator':...,'period':...}` | 동일 | ❌ **불일치**: id 41~47도 모두 indicator 키 미인식 |
| **11** | 뉴스 센티먼트 | news_sentiment | `{}` (빈 dict) | `params.get('symbol')` 필수, 없으면 None 반환 | ❌ **불일치**: 카탈로그가 빈 params를 정의했으나 fetcher는 symbol 필수. thesis.target fallback도 없음 |
| 3·4·12·13·14·15·16 (주요 지수) | fmp | `{'symbol':'^GSPC'}` 등 | `/stable/quote` | ⚠️ **미검증**: 지수 심볼(^GSPC, ^KS11, ^IXIC, ^DJI, ^KQ11, ^N225, ^HSI)이 FMP `/stable/quote`에서 정상 반환되는지 확인 필요 |
| 20·21·22·23·24 (원자재) | fmp | `{'symbol':'GCUSD'}` 등 | `/stable/quote` | ⚠️ **미검증**: FMP 원자재 심볼(GCUSD/CLUSD/SIUSD/HGUSD/NGUSD) 지원 여부 확인 필요 |
| 25·26 (BTC/ETH) | fmp | `{'symbol':'BTCUSD'}` | `/stable/quote` | ⚠️ **미검증** |
| 8 (VIX) | fmp | `{'symbol':'^VIX'}` | `/stable/quote` | ⚠️ **미검증** |
| 9 (USDKRW) | fmp | `{'symbol':'USDKRW'}` | `/stable/quote` | ⚠️ **미검증** (환율 심볼) |
| **39** | 달러 인덱스 (DXY) | fmp | `{'symbol':'DX-Y.NYB'}` | `/stable/quote` | ❌ **불일치 가능성 높음**: `DX-Y.NYB`는 Yahoo Finance 표기, FMP는 통상 `DX=F` 또는 `DXY` 사용 |
| 5 (EPS), 50~58 (PER/PBR/ROE/...) | fmp | TTM metric + `inverse`/`scale_multiplier`/`endpoint` 메타 | `_fetch_fmp_ttm_or_growth` + `_apply_value_postprocess` | ✅ **일치** (audit P0 #11 대응 완료) |
| 6·7·30·31·32·33·34·35·36·37·38 (FRED) | fred | `{'series_id':...}` | `_fetch_fred_value` | ✅ **일치** |
| 60~73 (재무 체질) | metrics | `{'metric_code':...}` | `_fetch_metrics_value` (quarterly_metric_fetcher) | ✅ **일치** |

### 요약

- **명백한 불일치(8건)**:
  - id 1, 2: FMP 수급 데이터를 `/stable/quote`에서 페치 불가.
  - id 10, 40~47 (총 9개 기술적 지표): `_fetch_fmp_value`에 `indicator` 키 분기 없음. **즉 카탈로그에 등록되어 있으나 실제 EOD 파이프라인에서 값을 가져오지 못한다.**
  - id 11: 빈 `data_params`로 인해 symbol 없음, 페치 실패.
- **검증 필요(미확정)**:
  - FMP `/stable/quote`가 인덱스(`^GSPC`,`^VIX`...), 원자재(`GCUSD`...), 통화(`USDKRW`), 암호화폐(`BTCUSD`)를 지원하는지 실측 필요.
  - id 39 `DX-Y.NYB`는 FMP 표기와 다른 가능성 큼.
- **일치(잘 동작)**:
  - 펀더멘털 5/50~58 (TTM/financial-growth 분기 + 후처리).
  - FRED 6/7/30~37 및 31~36/38.
  - 재무 체질 60~73 (metrics 소스).

### 권고 (감사 발견사항 — 보고만, 코드 수정 없음)

1. **기술적 지표(10, 40~47) 9개**: fetcher 분기 추가 또는 카탈로그에서 보류 표시. 현재 사용자가 이 지표를 선택하면 EOD 파이프라인에서 값이 갱신되지 않을 가능성.
2. **수급(1, 2)**: 별도 FMP 엔드포인트(예: `/stable/institutional-ownership`, `/stable/insider-trading`) 또는 다른 소스 필요. 현재 `/stable/quote`로는 매핑 불가.
3. **뉴스 센티먼트(11)**: `data_params: {}` 대신 `{'symbol': '<thesis target에서 채움>'}` 또는 fetcher에서 thesis.target fallback 추가.
4. **달러 인덱스(39)**: FMP가 `DX-Y.NYB`를 지원하는지 실측 후, 미지원이면 FRED `DTWEXBGS`(Broad Dollar Index) 등으로 교체 검토.
5. **단일 소스 정립**: `KEYWORD_RULES`(BE name 기반)와 `KEYWORD_INDICATOR_MAP`(FE ID 기반)을 단일 ID-기반 소스로 통합 권고. 현재 두 곳에서 따로 관리되어 표류 위험.

---

## 부록: 검증 데이터

- BE `INDICATOR_CATALOG` 항목 수: 64 (`thesis/services/prompt_builder.py:14`)
- FE `INDICATOR_CATALOG` 항목 수: 64 (`frontend/components/thesis/AddIndicatorSheet.tsx:15`)
- BE `INDICATOR_FREQUENCY` 매핑 수: 64
- BE `KEYWORD_RULES` 룰 수: 11 (`thesis/services/indicator_matcher.py:12`)
- FE `KEYWORD_INDICATOR_MAP` 룰 수: 28 (`frontend/components/thesis/AddIndicatorSheet.tsx:109`)
- `data_source` 별 카탈로그 분포:
  - `fmp`: 시장 데이터/펀더멘털(TTM)/기술적 — 약 38건
  - `fred`: 거시경제(금리/물가/고용/성장/환율) — 11건
  - `news_sentiment`: 1건
  - `metrics`: 재무 체질(60~73) — 14건
