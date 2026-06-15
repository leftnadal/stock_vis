# 지표 카탈로그 동기화 감사 보고서

- **생성일**: 2026-06-15
- **유형**: 읽기 전용 감사 (코드 수정 없음)
- **대상**:
  - BE 정의: `thesis/services/prompt_builder.py` (`INDICATOR_CATALOG`, `INDICATOR_FREQUENCY`)
  - BE 후처리: `thesis/services/llm_postprocess.py`
  - BE 매칭: `thesis/services/indicator_matcher.py` (`KEYWORD_RULES`)
  - BE 소비: `thesis/tasks/eod_pipeline.py` (`_fetch_*_value`)
  - FE 표시: `frontend/components/thesis/AddIndicatorSheet.tsx` (`INDICATOR_CATALOG`, `KEYWORD_INDICATOR_MAP`)

---

## 요약 (동기화 상태)

| 검사 항목 | 상태 | 비고 |
|----------|------|------|
| 1. BE ↔ FE 카탈로그 항목 (id/이름) | ✅ **완전 일치** | 양쪽 64개, id·이름 100% 동일 |
| 1-b. BE ↔ FE 업데이트 주기(freq) | ✅ **완전 일치** | 64개 전부 일치 |
| 1-c. 카테고리 라벨 체계 | ⚠️ 의도적 차이 | BE 5개(coarse) vs FE 17개(fine) — 표시 전용 |
| 2. description 품질 | ✅ **양호** | 64개 전부 존재, 최단 22자(≥10자) |
| 3. keyword_rules 고아 규칙 | ✅ 고아 0건 | 단, BE↔FE 룰 **비대칭** + EPS type 불일치 |
| 4. data_params 형식 ↔ 제공자 | ❌ **실데이터 누락 위험 다수** | 수급 2건 상시 None, 펀더멘털 TTM 엔드포인트 의심 |

**총평**: 사용자에게 노출되는 카탈로그(id/이름/주기)는 BE·FE가 완벽히 동기화되어 있고 description 품질도 양호하다. 그러나 **데이터 fetch 계층(`eod_pipeline.py`)에서 `data_params`와 실제 FMP 제공 필드 간 불일치가 다수 존재**하여, 일부 지표는 등록되더라도 값이 항상 `None`으로 떨어질 가능성이 높다. 이것이 이번 감사의 핵심 리스크다.

---

## BE ↔ FE 불일치 목록

### 1. 항목(id/이름) 대조 — 불일치 **0건**

BE `INDICATOR_CATALOG`(prompt_builder.py:14~310)와 FE `INDICATOR_CATALOG`(AddIndicatorSheet.tsx:15~91) 모두 동일한 **64개** id 집합을 가진다.

```
공통 id (64개):
1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,
20,21,22,23,24,25,26,30,31,32,33,34,35,36,37,38,39,40,
41,42,43,44,45,46,47,50,51,52,53,54,55,56,57,58,
60,61,62,63,64,65,66,67,68,69,70,71,72,73
```

- BE에만 있는 id: **없음**
- FE에만 있는 id: **없음**
- id별 `name` 문자열: **64개 전부 1:1 일치** (예: `'S&P 500'`, `'VIX (공포지수)'`, `'매출채권 회전일수 (DSO)'` 등 괄호·공백까지 동일)

### 2. 업데이트 주기(freq) 대조 — 불일치 **0건**

BE `INDICATOR_FREQUENCY`(prompt_builder.py:321~342)와 FE `freq` 필드를 id별로 전수 대조한 결과 64개 전부 일치. 특히 주의가 필요한 비(非)일간 항목도 모두 일치:

| id | 지표 | BE | FE |
|----|------|----|----|
| 6 | 미국 기준금리 | 주간 | 주간 ✅ |
| 37 | 30년 모기지 금리 | 주간 | 주간 ✅ |
| 34 | 실질 GDP | 분기 | 분기 ✅ |
| 31/32/33/35/36 | 실업률/NFP/CPI/산업생산/주택착공 | 월간 | 월간 ✅ |
| 5, 50~58, 60~73 | 펀더멘털 전체 | 분기 | 분기 ✅ |

### 3. 카테고리 체계 차이 (⚠️ 불일치는 아님, 설계 차이)

- **BE**: 5개 coarse 카테고리 — `market_data / macro / technical / fundamental / sentiment` (LLM 프롬프트 그룹핑용, `CATEGORY_LABELS` prompt_builder.py:312)
- **FE**: 17개 fine 카테고리 — `수급 / 주요 지수 / 원자재 / 암호화폐 / 금리 / 환율/변동성 / 고용/성장 / 물가/주택 / 기술적 / 펀더멘털 / 재무 체질 / 밸류에이션 / 성장 / 운영 효율 / 이익 품질 / 주주환원 / 심리` (UI 그룹핑용, AddIndicatorSheet.tsx:211)

→ 표시 목적이 달라 의도된 차이이나, **단일 소스가 아니므로** 항목 추가 시 두 분류 체계를 동시에 갱신해야 하는 유지보수 부담이 있다. (MEMORY: `feedback_indicator_catalog_sync` — "3곳 분산 미러, 동시 업데이트 필수"와 동일 맥락)

### 4. FE가 보유하지 않는 BE 필드

FE 미러는 `{id, name, category, freq}`만 가진다. BE의 `data_source`, `data_params`, `support_direction`, `description`은 FE에 없음 → **FE는 표시 전용 서브셋**이므로 description/data_params 품질은 순수 BE 책임. (정상 설계)

---

## description 품질

**BE 64개 항목 전부 `description` 보유, 빈 값·10자 미만 0건.** 품질 양호.

- 최단 description (그래도 ≥10자, 한글 기준):
  - id 4 `KOSPI 지수`: "한국 유가증권시장 전체 종목 시가총액 가중 지수." (24자)
  - id 14 `코스닥 지수`: "한국 중소형 성장주 시장 지수." (16자)
  - id 22 `은 (Silver)`: "은 현물 가격(USD/oz). 산업 수요와 안전자산 이중 역할." (충분)
- 조회 함수 `get_indicator_description()`(prompt_builder.py:351)은 접두사 매칭을 지원하여 `"EPS 추이 (META)"` 같은 심볼 접미 케이스도 description을 반환 → 견고함.
- **참고**: FE에는 description 필드 자체가 없어 사용자에게 지표 설명이 노출되지 않는다. (현재 UI는 이름+주기 칩만 표시) — 품질 이슈는 아니나 UX 개선 여지.

---

## keyword_rules 고아

### 고아 규칙 — **0건**

- **BE `KEYWORD_RULES`** (indicator_matcher.py:12~154): 규칙은 `name` 문자열로 카탈로그를 참조. 참조하는 11개 이름(`외국인 순매수 추이`, `미국 기준금리 (Fed Funds Rate)`, `미국 10년 국채 금리`, `VIX (공포지수)`, `원/달러 환율`, `RSI (14일)`, `뉴스 센티먼트`, `EPS 추이`, `기관 순매수 추이`, `S&P 500`, `KOSPI 지수`)이 모두 `INDICATOR_CATALOG`에 존재 → 고아 없음. `_find_in_catalog()`(indicator_matcher.py:332)로 최종 검증까지 수행.
- **FE `KEYWORD_INDICATOR_MAP`** (AddIndicatorSheet.tsx:109~139): `indicatorIds`로 참조. 참조 id 전부(1,2,3,4,6,7,8,9,10,11,12,15,16,20,21,23,24,25,26,30,31,32,33,34,35,36,37,39,40,50,51,52,53,54,55,56,57,58,60,61,62,63,64,65,66,67,68,69,70,71,72,73)가 카탈로그에 존재 → 고아 없음.

### 발견된 이슈

**(P2) ① EPS `indicator_type` 불일치**
`KEYWORD_RULES`의 `EPS 추이` 항목은 `indicator_type: 'market_data'`(indicator_matcher.py:95)로 지정되어 있으나, 카탈로그의 동일 지표(id 5)는 `category: 'fundamental'`(prompt_builder.py:190). 키워드 fallback 경로로 매칭될 때 잘못된 카테고리가 따라붙을 수 있음.

**(P2) ② BE ↔ FE 키워드 룰 비대칭 (커버리지 격차)**
- BE `KEYWORD_RULES`: 11개 룰, 11개 지표만 커버. id 기반이 아닌 **이름 문자열** 참조 → 카탈로그 이름이 바뀌면 **조용히 매칭 실패**.
- FE `KEYWORD_INDICATOR_MAP`: 26개 룰, 60+ 지표 커버. **id 기반** 참조 + 점수(score) 정렬까지 구현.
- 결과: 동일 전제 텍스트라도 BE 자동매칭과 FE 추천 결과가 크게 다를 수 있음. (예: "유가/구리/배당/ROIC/CPI/고용" 등은 FE만 매칭, BE는 LLM의 `indicator_db_id` PK에 의존)
- 단, BE는 PK 우선 2단계(`match_indicators_for_llm`, indicator_matcher.py:271) 설계라 키워드는 fallback일 뿐이므로 치명적이진 않음.

**(P3) ③ BE 룰 내부 키워드 ↔ 매핑 지표 불일치**
`KEYWORD_RULES`의 `S&P 500` 룰(indicator_matcher.py:111)은 키워드에 `'나스닥','NASDAQ','다우','DOW'`를 포함하지만 매핑 지표는 `S&P 500`(id 3) 하나뿐 → 나스닥/다우 키워드가 NASDAQ(12)·다우존스(13)를 끌어오지 못함. (FE는 `나스닥→[3,12]`로 처리)

---

## data_params 형식

`eod_pipeline.py`의 `fetch_indicator_value()`(261행) → `DATA_SOURCE_FETCHERS`(253행) 경로를 기준으로 `data_params` 형식과 실제 제공자 응답을 대조.

### ❌ (P1) 수급 지표 2건 — **상시 `None` 반환 위험**

| id | 지표 | data_params | 문제 |
|----|------|-------------|------|
| 1 | 외국인 순매수 추이 | `{'metric': 'foreign_net_buy'}` | FMP `/stable/quote`에 `foreign_net_buy` 필드 **없음** |
| 2 | 기관 순매수 추이 | `{'metric': 'institutional_net_buy'}` | FMP `/stable/quote`에 `institutional_net_buy` 필드 **없음** |

`_fetch_fmp_value`(eod_pipeline.py:81)에서 metric이 `TTM`로 끝나지 않고 endpoint도 없으므로 quote 분기로 진입 → `value_map`(128행)에 키 없음 → `quote.get('foreign_net_buy')` → `None`. FMP 무료/Starter Plan은 외국인·기관 순매수 데이터를 제공하지 않음. **두 지표는 등록돼도 항상 값 없음.** (이름이 `market_data`로 가장 기본 지표처럼 보여 사용자 혼란 가능)

### ⚠️ (P1) 펀더멘털 TTM 비율 — **엔드포인트 불일치 의심**

`_fetch_fmp_ttm_or_growth`(eod_pipeline.py:46)는 metric이 `TTM`로 끝나면 **무조건 `/stable/key-metrics-ttm`만** 호출(70행). 그러나 아래 필드들은 FMP stable 스키마상 `/stable/ratios-ttm`에 위치하는 항목이 다수 → key-metrics-ttm 응답에 키가 없으면 `data[0].get(metric)`이 `None`.

| id | 지표 | metric | 검증 필요 |
|----|------|--------|----------|
| 50 | PER | `earningsYieldTTM` (inverse) | key-metrics-ttm 존재 가능성 높음 — OK 추정 |
| 51 | PBR | `pbRatioTTM` | ratios-ttm 계열 의심 |
| 52 | ROE | `returnOnEquityTTM` (×100) | ratios-ttm 계열 의심 (#14 회귀 주의) |
| 53 | ROA | `returnOnAssetsTTM` (×100) | ratios-ttm 계열 의심 |
| 54 | 부채비율 | `debtToEquityTTM` | ratios-ttm 계열 의심 |
| 56 | 배당수익률 | `dividendYieldTTM` | ratios-ttm 계열 의심 |
| 57 | 영업이익률 | `operatingProfitMarginTTM` | ratios-ttm 계열 의심 |
| 55 | FCF | `freeCashFlowTTM` | key-metrics-ttm 존재 가능성 — OK 추정 |

> **주의**: 본 감사는 읽기 전용이라 FMP 실 응답을 호출 검증하지 않았다. 위 "의심" 항목은 FMP `/stable/key-metrics-ttm` vs `/stable/ratios-ttm` 실 스키마 대조가 필요하다. common-bugs #14(FMP Key Metrics 필드명 불일치)와 동일 계열 리스크이며, 코드 주석(prompt_builder.py:194~243)도 이 위험을 이미 인지하고 있다. **확정 단정 아님 — 실 API 1회 검증 권장.**

### ⚠️ (P2) 지수/환율 심볼 형식 — **FMP 미지원 의심**

`metric` 기본값이 `'price'`라 quote 분기에서 `client.get_quote(symbol)` 호출. 아래 심볼은 Yahoo 스타일이라 FMP가 동일 표기를 받지 않을 수 있음:

| id | 지표 | symbol | 비고 |
|----|------|--------|------|
| 4 | KOSPI 지수 | `^KS11` | FMP 한국 지수 지원 여부 불확실 |
| 14 | 코스닥 지수 | `^KQ11` | 동일 |
| 39 | 달러 인덱스(DXY) | `DX-Y.NYB` | Yahoo 표기 — FMP는 보통 미지원 |
| 9 | 원/달러 환율 | `USDKRW` | FMP forex 표기 검증 필요 |

→ 미지원 시 `get_quote`가 빈 응답 → `None`. (반면 `^GSPC`,`^IXIC`,`^DJI`,`^VIX` 및 원자재 `GCUSD/CLUSD/...`, 크립토 `BTCUSD/ETHUSD`는 FMP가 지원하는 표준 표기로 추정 — OK)

### ✅ 정상 처리 확인된 형식

- **FRED** (`series_id`): id 6/7/30/37/31/32/33/34/35/36/38 → `_fetch_fred_value`(157행)가 `series_id`로 정상 조회. 형식 일치.
- **metrics** (`metric_code`): id 60~73 → `_fetch_metrics_value`(230행)가 `fetch_quarterly_metric(symbol, metric_code)`로 위임. validation/metrics 시스템과 정합. 형식 일치.
- **news_sentiment**: id 11 → `_fetch_news_sentiment_value`(199행). 단 `data_params={}`(symbol 없음)이라 207행에서 항상 "symbol 없음" 경고 후 `None` — **단, 펀더멘털/기술 지표처럼 thesis target fallback이 없어** 뉴스 센티먼트는 symbol 주입 경로가 별도 필요. (P2: id 11도 현재 형식상 값 못 받을 수 있음)
- **후처리 메타** (`inverse`, `scale_multiplier`, `endpoint`): `_apply_value_postprocess`(25행)가 정상 구현 — PER 역수, ROE/ROA ×100, financial-growth 분기까지 코드상 정상 처리됨.

---

## 권고 (우선순위)

| 우선 | 항목 | 조치 (수정은 별도 PR) |
|------|------|----------------------|
| P1 | id 1,2 수급 지표 상시 None | FMP 미제공 → 데이터 소스 재지정 또는 카탈로그에서 비활성/숨김 |
| P1 | 펀더멘털 TTM 엔드포인트 | `/stable/key-metrics-ttm` vs `/stable/ratios-ttm` 실 응답 1회 검증 후 metric별 endpoint 힌트 분기 |
| P2 | id 4,14,39,9 심볼 형식 | FMP 지원 표기 확인, 미지원 시 FRED(DXY=`DTWEXBGS` 등)·대체 소스로 |
| P2 | id 11 뉴스 센티먼트 symbol 미주입 | thesis target fallback 추가 필요 (현재 다른 fetcher와 달리 fallback 없음) |
| P2 | EPS `indicator_type` 불일치 | KEYWORD_RULES `EPS 추이`를 `fundamental`로 정정 |
| P2 | BE↔FE 키워드 룰 비대칭 | BE `KEYWORD_RULES`도 id 기반으로 전환 + 커버리지 확대 검토 |
| P3 | 카탈로그 3중 미러 유지보수 | 단일 소스(DB/JSON) 마이그레이션 검토 (prompt_builder.py:11~12 주석에 이미 예고됨) |

---

*감사 방법: 정적 코드 분석(읽기 전용). FMP/FRED 실 API 호출 검증은 수행하지 않음 — "의심" 표기 항목은 별도 실 응답 대조 필요.*
