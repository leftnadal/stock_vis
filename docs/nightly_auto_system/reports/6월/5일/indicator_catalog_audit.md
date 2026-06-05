# 지표 카탈로그 동기화 감사 보고서

> 생성일: 2026-06-05
> 범위: `INDICATOR_CATALOG` 단일 소스(BE) ↔ FE 미러 ↔ keyword 룰 ↔ data_params 소비 경로
> 모드: **읽기 전용 감사** (코드 수정 없음)

## 검사 대상 파일

| 역할 | 파일 | 비고 |
|------|------|------|
| BE 정의 (단일 소스) | `thesis/services/prompt_builder.py` | `INDICATOR_CATALOG` 64개 + `INDICATOR_FREQUENCY` |
| BE 후처리 | `thesis/services/llm_postprocess.py` | `indicator_db_id` null 교정 |
| BE 키워드 매칭 | `thesis/services/indicator_matcher.py` | `KEYWORD_RULES` (name 기반, 11룰) |
| BE data_params 소비 | `thesis/tasks/eod_pipeline.py` | 실제 fetch dispatch (@infra 영역, 참조만) |
| BE symbol 주입 | `thesis/services/thesis_builder.py:1182` | 런타임 `data_params['symbol']` 보정 |
| FE 표시 + 추천 | `frontend/components/thesis/AddIndicatorSheet.tsx` | `INDICATOR_CATALOG` 미러 + `KEYWORD_INDICATOR_MAP` (id 기반, 26룰) |

---

## 요약 (동기화 상태)

| 항목 | 상태 | 핵심 발견 |
|------|------|-----------|
| **ID / name 동기화 (BE↔FE)** | 🟢 일치 | 64개 id·name 양쪽 완전 일치, 누락 0건 |
| **freq 동기화 (BE↔FE)** | 🟢 일치 | `INDICATOR_FREQUENCY` 64개 ↔ FE `freq` 전건 일치 |
| **category 분류 체계** | 🟡 비대칭 | BE 5종(상위) vs FE 17종(세분류) — 단일 소스 아님 (의도적이나 미문서화) |
| **description 미러** | 🔴 갭 | BE 64개 전부 보유, **FE는 description 필드 자체를 미러하지 않음** |
| **description 품질** | 🟢 양호 | 빈 값 0건, 10자 미만 0건 |
| **keyword 룰 (BE)** | 🟡 부분 | name 하드코딩 중복(11룰만, 53개 미커버), `EPS 추이` indicator_type 불일치 |
| **keyword 룰 BE↔FE 이중화** | 🔴 비대칭 | BE `KEYWORD_RULES`(name·11룰) vs FE `KEYWORD_INDICATOR_MAP`(id·26룰) 완전 별개 구현 |
| **data_params 형식** | 🔴 불일치 2건 | 기술적 지표 `indicator` 키 미소비 / 순매수 `metric` 미존재 필드 |

**종합**: id·name·freq 축은 견고하게 동기화됨. 그러나 (1) description이 FE로 전달되지 않고, (2) 키워드 매핑이 BE/FE 이중 구현되어 비대칭이며, (3) 기술적 지표·순매수 지표의 `data_params`가 실제 fetch 로직과 맞지 않아 잘못된 값이 수집되거나 수집 불가하다.

---

## BE ↔ FE 불일치 목록

### 1. ID / name — 불일치 없음 ✅

양쪽 모두 동일한 64개 지표(id·name 동일). BE에만 있거나 FE에만 있는 항목 **0건**.

```
공통 64개: 1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,20,21,22,23,24,25,26,
           30,31,32,33,34,35,36,37,38,39,40,41,42,43,44,45,46,47,
           50,51,52,53,54,55,56,57,58,60,61,62,63,64,65,66,67,68,69,70,71,72,73
```

### 2. category 분류 체계 — 비대칭 🟡

| | BE (`prompt_builder.py`) | FE (`AddIndicatorSheet.tsx`) |
|---|---|---|
| 분류 수 | 5종 | 17종 |
| 값 | `market_data`, `macro`, `technical`, `fundamental`, `sentiment` | `수급`, `주요 지수`, `원자재`, `암호화폐`, `금리`, `환율/변동성`, `고용/성장`, `물가/주택`, `기술적`, `펀더멘털`, `재무 체질`, `밸류에이션`, `성장`, `운영 효율`, `이익 품질`, `주주환원`, `심리` |

- FE는 BE의 `market_data`를 `수급/주요 지수/원자재/암호화폐`로, `fundamental`을 `펀더멘털/재무 체질/밸류에이션/성장/운영 효율/이익 품질/주주환원`으로 자체 재분류.
- 두 분류 체계는 **별도로 하드코딩**되어 있어 한쪽 변경 시 자동 반영 안 됨.
- 영향: 기능 버그는 아니나, 신규 지표 추가 시 BE category·FE category·`categoryOrder` 배열 3곳을 수동 동기화해야 함.

### 3. description 필드 — FE 미러 누락 🔴

- BE: 64개 전 항목에 `description` 보유 (1~2문장, 투자 의미 설명).
- FE `CatalogIndicator` 인터페이스: `{ id, name, category, freq }` — **`description` 필드 없음**.
- 영향: 지표 추가 시트(AddIndicatorSheet)에서 사용자가 지표의 의미·해석을 볼 수 없음. BE는 고품질 설명을 보유하나 FE 사용자에게 전달되지 않는 **콘텐츠 손실**.
- 참고: 메모리 `feedback_indicator_catalog_sync` ("지표 카탈로그 3곳 분산 미러, 동시 업데이트 필수")의 연장선.

### 4. freq 동기화 — 일치 ✅

`INDICATOR_FREQUENCY`(id별 dict)와 FE 인라인 `freq` 전건 대조 — 불일치 0건. (예: id 6 주간, id 7 일간, id 34 분기, id 37 주간 등 모두 일치.)
단, 두 소스가 **물리적으로 분리**(BE는 별도 dict, FE는 인라인)되어 있어 향후 drift 위험 존재.

---

## description 품질

| 검사 | 결과 |
|------|------|
| 빈 description (`''`) | **0건** |
| 10자 미만 description | **0건** |
| 누락(`description` 키 없음) | **0건** |

- 최단 description 예시: id 4 KOSPI `"한국 유가증권시장 전체 종목 시가총액 가중 지수."` (약 24자) — 충분.
- 전 항목이 "지표 정의 + 투자 해석" 2단 구조로 일관성 높음. **품질 양호, 조치 불필요.**
- 단, 위 BE↔FE §3 참조: 품질은 좋으나 FE로 미전달.

---

## keyword_rules 고아

### BE `KEYWORD_RULES` (`indicator_matcher.py`)

- **고아 규칙(카탈로그에 없는 지표를 가리키는 룰): 0건.** 11개 룰이 참조하는 모든 `name`이 카탈로그에 존재.
- 단, 구조적 이슈 3건:

| # | 이슈 | 상세 |
|---|------|------|
| K-1 | **PK 미사용 (name 하드코딩)** | `KEYWORD_RULES`는 `indicator_db_id` 없이 `name` 문자열로 지표를 정의. `match_indicators_for_llm` → `_find_in_catalog(name)`이 **이름 정확 일치**로 재조회. 카탈로그 `name` 1글자만 바뀌어도 매칭이 조용히 끊김(고아화). |
| K-2 | **메타 불일치 (`EPS 추이`)** | `KEYWORD_RULES`의 `EPS 추이`는 `indicator_type='market_data'`. 카탈로그 id 5는 `category='fundamental'`. 동일 지표의 분류가 두 소스에서 상충. |
| K-3 | **커버리지 협소** | 11개 룰이 카탈로그 64개 중 **11개 name만** 커버. 원자재·암호화폐·재무 체질(60~73)·기술 지표 상세(41~47) 등은 `match_by_keywords`로 도달 불가 → LLM PK 매칭 실패 시 자동 추천에서 누락. |

### FE `KEYWORD_INDICATOR_MAP` (`AddIndicatorSheet.tsx`)

- id 기반 26개 룰. 참조하는 모든 `indicatorIds`가 카탈로그에 존재 — **고아 0건**.
- 키워드 룰에서 미참조되는 지표(전체 목록에선 선택 가능하나 전제 기반 추천엔 안 뜸): id 13(다우존스), 14(코스닥), 22(은), 38(달러/유로), 42·43·44·45·46·47(기술 지표 상세) 등.

### 🔴 핵심: BE/FE 키워드 매핑 이중 구현

| | BE `KEYWORD_RULES` | FE `KEYWORD_INDICATOR_MAP` |
|---|---|---|
| 키 방식 | **name 문자열** | **id 정수** |
| 룰 수 | 11 | 26 |
| 반환 | 지표 dict(name·data_source·params 중복) | id + reason |
| 사용처 | `match_indicators_for_premise` (서버 추천) | `findRelatedIndicators` (클라이언트 추천) |

- 동일한 "전제 텍스트 → 관련 지표" 기능이 **서로 다른 키워드 사전·다른 키 체계**로 BE/FE에 중복 구현됨.
- 같은 전제를 입력해도 BE 추천과 FE 추천 결과가 다를 수 있음(사전 비대칭).
- K-1과 결합 시: BE는 name으로, FE는 id로 동일 지표를 가리켜 유지보수 시 양쪽을 별개로 갱신해야 함.

---

## data_params 형식

eod_pipeline.py의 실제 fetch dispatch(`DATA_SOURCE_FETCHERS`: `fmp`/`fred`/`news_sentiment`/`metrics`)와 카탈로그 `data_params`를 대조했다.

### 🟢 정상 소비 (형식 일치)

| 그룹 | data_params | 소비 경로 | 비고 |
|------|-------------|-----------|------|
| 지수/원자재/환율/암호화폐 (3,4,12,13,14,15,16,20~26,8,9,39) | `{'symbol': '^GSPC'}` 등 | `_fetch_fmp_value` → `/stable/quote` price | 정상 |
| FRED 거시 (6,7,30,37,38,31,32,34,35,33,36) | `{'series_id': 'FEDFUNDS'}` | `_fetch_fred_value` → series_id | 정상 |
| TTM 펀더멘털 (50,51,52,53,54,55,56,57) | `{'metric': '...TTM'}` (+ inverse/scale) | `_fetch_fmp_ttm_or_growth` + `_apply_value_postprocess` | **common-bugs #14 회귀 방지 정확 구현** ✅ |
| 매출성장률 (58) | `{'metric':'growthRevenue','endpoint':'financial-growth','scale_multiplier':100}` | financial-growth 분기 | 정상 |
| EPS (5) | `{'metric': 'eps'}` | quote value_map `eps` | 정상 |
| 재무 체질 (60~73) | `{'metric_code': 'gross_margin'}` 등 | `_fetch_metrics_value` → `fetch_quarterly_metric` | 정상 |

> `inverse`/`scale_multiplier`/`endpoint`/`audit_note` 메타는 `_apply_value_postprocess`가 정확히 처리. PER=1/earningsYield, ROE×100 등 #14 패턴 방어가 코드·카탈로그 양쪽에 정합하게 박혀 있음.

### 🔴 형식 불일치 (수집 오류 / 불가)

| # | 지표 | data_params | 소비 경로 실제 동작 | 문제 |
|---|------|-------------|---------------------|------|
| **D-1** | **기술적 지표 10,40,41,42,43,44,45,46,47** | `{'indicator':'RSI','period':14}` 등 | `data_source='fmp'` → `_fetch_fmp_value`는 **`indicator`/`period` 키를 전혀 읽지 않음**. `metric` 미존재 → 기본값 `'price'` → `/stable/quote`의 **현재가** 반환 | **RSI/MACD 등을 요청했는데 종가(price)가 저장됨**. 기술 지표는 별도 엔드포인트(예: `/stable/technical-indicators`)가 필요하나 fetcher에 분기 없음. 가장 심각. |
| **D-2** | **외국인/기관 순매수 1,2** | `{'metric':'foreign_net_buy'}` / `{'metric':'institutional_net_buy'}` | TTM 아님·value_map 없음 → `field='foreign_net_buy'` → `quote.get('foreign_net_buy')` = **None** (FMP /stable/quote에 해당 필드 없음) | 항상 `null_value`. 게다가 한국 종목 수급은 FMP가 제공하지 않아 데이터 소스 자체가 부재. **수집 불가**. |

### 🟡 런타임 보정에 의존 (카탈로그 단독으로는 불완전)

| # | 지표 | data_params | 동작 |
|---|------|-------------|------|
| D-3 | 뉴스 센티먼트 (11) | `{}` (빈 dict) | `_fetch_news_sentiment_value`는 `symbol` 필요. 카탈로그엔 없음 → `thesis_builder.py:1182`가 인스턴스 생성 시 `data_params['symbol']=target`을 주입해야만 동작. 카탈로그 정의만으로는 항상 None. |
| D-4 | 펀더멘털 fmp (50~58 등) | symbol 없음 | 동일하게 thesis target → symbol fallback(`_fetch_fmp_value` 내 `thesis.target`) 또는 builder 주입에 의존. 설계상 의도된 동작이나, 카탈로그 `data_params`만 보면 symbol 누락처럼 보임(문서화 필요). |

> D-3·D-4는 `thesis_builder`의 symbol 주입 로직(`if target_sym and 'symbol' not in data_params`) 덕에 런타임엔 채워질 수 있음. 단 D-1(`indicator` 키)·D-2(미존재 metric)는 어떤 주입으로도 보정되지 않음.

---

## 권고 (참고용 — 본 보고서는 수정 미수행)

우선순위 순. 각 항목은 담당 에이전트 영역 표기.

1. **[P0·@infra/@backend] D-1 기술적 지표 fetch 분기 부재** — 9개 기술 지표가 현재가를 RSI 값으로 오기록. `eod_pipeline`에 `indicator`/`period` 키 처리(technical-indicators 엔드포인트) 분기 추가, 또는 카탈로그에서 기술 지표를 `manual`/`custom`으로 표기해 잘못된 수집 차단.
2. **[P0·@backend] D-2 순매수 지표 데이터 소스 부재** — id 1·2는 FMP로 수집 불가. 데이터 소스 확보 전까지 `data_source`를 `manual`로 두거나 카탈로그에서 보류 표기.
3. **[P1·@backend] K-2 `EPS 추이` indicator_type 정합** — `KEYWORD_RULES`의 `market_data` → 카탈로그 `fundamental`로 통일.
4. **[P1·@backend/@frontend] keyword 매핑 이중화 해소** — BE name 기반·FE id 기반 두 사전을 단일 소스(id 기반 contract)로 통합, 또는 `contracts/`에 키워드 룰 스펙 신설.
5. **[P2·@frontend] description FE 미러** — `CatalogIndicator`에 `description` 추가하여 지표 시트에 노출(BE 콘텐츠 활용).
6. **[P2·@backend] category·freq 단일 소스화** — BE 카탈로그를 codegen 소스로 삼아 FE 미러를 자동 생성(메모리 `feedback_indicator_catalog_sync` 3곳 분산 미러 근본 해소).

---

## 부록: 검증 방법

- BE 카탈로그: `prompt_builder.py:14-310` 전수 파싱 (64항목).
- FE 미러: `AddIndicatorSheet.tsx:15-91` 전수 대조.
- freq: `INDICATOR_FREQUENCY`(`prompt_builder.py:321-342`) ↔ FE `freq` 키별 대조.
- keyword: `KEYWORD_RULES`(`indicator_matcher.py:12-154`) name → 카탈로그 name 역참조 / FE `KEYWORD_INDICATOR_MAP`(`AddIndicatorSheet.tsx:109-139`) id → 카탈로그 id 역참조.
- data_params: `eod_pipeline.py:46-267` fetch dispatch 4종 ↔ 카탈로그 `data_params` 키별 소비 여부 추적.
