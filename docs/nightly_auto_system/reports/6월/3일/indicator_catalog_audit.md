# 지표 카탈로그 동기화 감사 보고서

> 생성일: 2026-06-03 · 모드: **읽기 전용 (코드 수정 없음)**
> 대상: `thesis/services/{prompt_builder,llm_postprocess,indicator_matcher}.py` ↔ `frontend/components/thesis/AddIndicatorSheet.tsx`

---

## 요약 (동기화 상태)

| 검사 항목 | 상태 | 비고 |
|----------|------|------|
| 카탈로그 항목 동기화 (id/name) | 🟢 **정합** | BE 64개 = FE 64개, id·name 1:1 일치 |
| 업데이트 주기 (freq) 동기화 | 🟢 **정합** | 64개 전건 일치 |
| 카테고리 체계 | 🟡 **구조 불일치** | BE 5종 vs FE 17종 (의도적 세분화로 추정, 단일 소스 아님) |
| description 필드 (BE) | 🟢 **양호** | 64개 전건 채워짐, 빈 값/10자 미만 0건 |
| description 미러링 (FE) | 🟡 **미반영** | FE는 description 자체를 보유/표시하지 않음 |
| BE `KEYWORD_RULES` 고아 | 🟢 **없음** | 참조 name 11종 전부 카탈로그 존재 |
| FE `KEYWORD_INDICATOR_MAP` 고아 | 🟢 **없음** | 참조 id 53종 전부 카탈로그 존재 |
| BE KEYWORD_RULES 인라인 메타 정합 | 🔴 **1건 불일치** | `EPS 추이` indicator_type 불일치 (아래) |
| 미참조(추천 불가) 지표 | 🟡 **11개** | 키워드 룰 없음 → 수동 탐색으로만 도달 |
| data_params 스케일 처리 | 🟠 **2건 누락 의심** | `dividendYieldTTM`, `operatingProfitMarginTTM` (#14 패턴) |
| data_params 심볼 포맷 | 🟠 **검증 필요** | FMP `^`-인덱스/`DX-Y.NYB`/한국지수 커버리지 |

**핵심 결론**: id/name/freq 1차 동기화는 **완벽**. 그러나 (1) BE 내부에서 카탈로그와 `KEYWORD_RULES`가 메타데이터를 **이중 정의**하여 1건 드리프트 발생, (2) data_params의 일부 비율 지표에 `scale_multiplier` 누락으로 **공통 버그 #14 재발 위험**이 잔존.

---

## BE ↔ FE 불일치 목록

### 1. 항목 집합 (id/name) — ✅ 완전 일치

- **BE**(`prompt_builder.py` `INDICATOR_CATALOG`): 64개
- **FE**(`AddIndicatorSheet.tsx` `INDICATOR_CATALOG`): 64개
- id 집합 동일: `1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,20~26,30~39,40~47,50~58,60~73`
- BE에만 있거나 FE에만 있는 항목: **0건**
- name 문자열도 64개 전건 동일 (예: `'외국인 순매수 추이'`, `'PER (주가수익비율)'` 등)

> 참고: CLAUDE.md 메모리의 "description 73개"는 **최대 id(73)** 를 가리키며, 실제 항목 수는 **64개**(id 비연속).

### 2. 카테고리 체계 — 🟡 구조 불일치 (단일 소스 아님)

| | 카테고리 |
|--|----------|
| **BE** (5종, `category` 필드) | `market_data`, `macro`, `technical`, `fundamental`, `sentiment` |
| **FE** (17종, `category` 필드) | `수급`, `주요 지수`, `원자재`, `암호화폐`, `금리`, `환율/변동성`, `고용/성장`, `물가/주택`, `기술적`, `펀더멘털`, `재무 체질`, `밸류에이션`, `성장`, `운영 효율`, `이익 품질`, `주주환원`, `심리` |

- FE 카테고리는 BE `category`에서 파생된 것이 아니라 **FE에서 독립 정의**된 표시용 그룹. BE의 `CATEGORY_LABELS`(5종)와도 무관.
- **리스크**: BE에서 어떤 지표의 `category`를 바꿔도 FE는 따라가지 않음. 반대도 동일. 두 곳을 수동 동기화해야 함.
- 현 시점 기능적 버그는 아님(FE가 자체 그룹으로 화면 렌더링) — **구조적 동기화 부채**로 분류.

### 3. description / data_source / data_params / support_direction — 🟡 FE 미러링 범위 제한

- FE `CatalogIndicator` 인터페이스 = `{ id, name, category, freq }` **4개 필드만** 보유.
- BE가 가진 `description`, `data_source`, `data_params`, `support_direction`은 FE에 **존재하지 않음**.
- 결과: `AddIndicatorSheet`는 지표 설명(description)을 사용자에게 노출하지 않으며, 추천 사유는 별도 `KEYWORD_INDICATOR_MAP[].reason`(FE 자체 정의 문자열)만 표시.
- 영향: 사용자가 지표 선택 시 BE에 정의된 풍부한 설명을 보지 못함. 콘텐츠 활용 손실(기능 결함은 아님).

---

## description 품질

대상: BE `INDICATOR_CATALOG` 64개 항목의 `description` 필드 (FE는 description 미보유)

| 점검 | 결과 |
|------|------|
| 빈(empty) description | **0건** |
| 10자 미만 description | **0건** (최단도 약 20자 이상) |
| 누락(키 없음) | **0건** — `test_llm_builder.py::test_indicator_catalog_has_all_fields`로 필드 존재 테스트 커버 |

- 모든 description이 "정의 + 투자적 함의" 2단 구조로 일관되게 작성됨.
  - 예: id 23 `'구리 선물 가격. 경기 선행지표로 "Dr. Copper"라 불림.'`
  - 예: id 6 `'연준 기준금리. 유동성과 할인율에 직접 영향. 금리 인상은 주식에 부정적.'`
- **품질 이슈 없음.** 단, 위 §3대로 이 자산이 FE로 전달되지 않는 것이 유일한 아쉬운 점.

---

## keyword_rules 고아

키워드 룰은 **BE·FE 두 곳에 독립적으로 존재**하며 서로 다른 식별 방식을 사용한다.

### 4-A. BE `indicator_matcher.py :: KEYWORD_RULES` (이름 기반, 10개 룰)

- 참조하는 지표 **name 11종 전부** 카탈로그에 존재 → **고아 규칙 0건**.
- 단, 각 룰이 `data_source`/`data_params`/`indicator_type`/`support_direction`을 **인라인 중복 정의**(카탈로그 값을 손으로 복제). 이 중 **1건 드리프트 발견**:

| 지표 | KEYWORD_RULES `indicator_type` | CATALOG `category` | 판정 |
|------|-------------------------------|--------------------|------|
| **EPS 추이** (id 5) | `'market_data'` (L95) | `'fundamental'` (L190) | 🔴 **불일치** |
| 나머지 10개 | 일치 | 일치 | 🟢 |

> `EPS 추이`는 카탈로그상 `fundamental`이나 KEYWORD_RULES 인라인 사본은 `market_data`로 남아 있음. 텍스트 폴백 경로(`match_by_keywords`)로 추천될 때 잘못된 타입이 전파될 수 있음. **이중 정의의 전형적 드리프트 사례.**

- 추가 관찰: `match_by_gemini()`는 코드상 존재하나 `match_indicators_for_llm()`에서는 **의도적으로 제외**(L306~307 주석: "카탈로그에 없는 환각 지표 생성 방지"). `match_indicators_for_premise()` 경로에서는 여전히 폴백으로 호출됨 → 이 경로는 카탈로그 외 환각 지표를 반환할 수 있음(메모리 `feedback_llm_indicator_hallucination`와 부분 상충, 경로별 정책 불일치).

### 4-B. FE `AddIndicatorSheet.tsx :: KEYWORD_INDICATOR_MAP` (id 기반, 29개 룰)

- 참조하는 지표 **id 53종 전부** 카탈로그에 존재 → **고아 id 0건**.

### 4-C. 키워드 룰이 한 번도 가리키지 않는 카탈로그 지표 — 🟡 11개

FE `KEYWORD_INDICATOR_MAP` 어느 룰에서도 참조되지 않아 **전제 기반 자동 추천이 불가능**(수동 탐색으로만 도달):

| id | 지표 | id | 지표 |
|----|------|----|------|
| 13 | 다우존스 | 43 | ATR (평균진폭) |
| 14 | 코스닥 지수 | 44 | OBV (거래량 누적) |
| 22 | 은 (Silver) | 45 | SMA 50일 |
| 38 | 달러/유로 환율 | 46 | SMA 200일 |
| 41 | 스토캐스틱 %K | 47 | EMA 12일 |
| 42 | 볼린저 밴드 %B | | |

> 기능상 치명적 아님(수동 추가 가능). 다만 기술적 지표 대부분(41~47)이 추천 동선에서 누락되어, "RSI/MACD" 키워드는 id 10·40만 추천하고 나머지 기술적 지표는 노출 기회가 적음.

### 4-D. BE ↔ FE 키워드 룰 자체의 비동기

- BE는 **10개 룰**(주로 거시/수급/실적), FE는 **29개 룰**(펀더멘털·밸류에이션·운영효율까지 세분화). 두 룰 셋은 키워드 구성·커버리지가 **상당히 다름**. 단일 소스가 아니라 각자 진화 중 → 추천 결과가 BE 경로(서버)와 FE 경로(클라이언트)에서 달라질 수 있음.

---

## data_params 형식

BE 카탈로그는 `data_source`별로 다음 형식을 사용:

| data_source | data_params 형식 | 예 |
|-------------|------------------|-----|
| `fmp` | `{'metric': ...}` / `{'symbol': ...}` / `{'indicator':..., 'period':...}` | `{'symbol':'^GSPC'}` |
| `fred` | `{'series_id': ...}` | `{'series_id':'FEDFUNDS'}` |
| `metrics` | `{'metric_code': ...}` (validation/metrics 시스템) | `{'metric_code':'roic'}` |
| `news_sentiment` | `{}` | — |

### 5-A. 이미 방어된 항목 (공통 버그 #14 회귀 방지 주석 존재) — 🟢

| id | 지표 | 처리 | 근거 |
|----|------|------|------|
| 50 | PER | `earningsYieldTTM` + `inverse: True` | FMP에 `peRatioTTM` 미존재, PER = 1/earningsYield |
| 52 | ROE | `returnOnEquityTTM` + `scale_multiplier: 100` | 0~1 → % 변환 |
| 53 | ROA | `returnOnAssetsTTM` + `scale_multiplier: 100` | 0~1 → % 변환 |
| 58 | 매출성장률 | `growthRevenue` + `endpoint:'financial-growth'` + `scale_multiplier:100` | key-metrics-ttm 표준 필드 아님 |

### 5-B. `scale_multiplier` 누락 의심 — 🟠 #14 패턴 재발 가능 (검증 필요)

ROE/ROA는 0~1 비율이라 `×100`을 붙였는데, **동일 성격의 다른 비율 지표는 누락**:

| id | 지표 | data_params | 우려 |
|----|------|-------------|------|
| 56 | 배당수익률 | `{'metric': 'dividendYieldTTM'}` | FMP `dividendYieldTTM`은 보통 0~1(예 0.015). `scale_multiplier` 없으면 `0.015`로 표기 → **1.5%가 아닌 0.015 노출** 위험 |
| 57 | 영업이익률 | `{'metric': 'operatingProfitMarginTTM'}` | 마찬가지로 0~1 비율. `scale_multiplier` 없음 → % 표기 깨질 수 있음 |

> ROE/ROA에는 `scale_multiplier:100`을 명시하면서 같은 마진/수익률 계열인 56·57에는 없는 것은 **비대칭**. 실측(FMP 응답 스케일) 확인 후 동일 처리 권장. (읽기 전용 감사이므로 수정하지 않음 — 차기 PR 후보)

### 5-C. 심볼/엔드포인트 포맷 — 🟠 FMP 커버리지 검증 필요

- **FMP `^`-prefix 인덱스**: `^GSPC`(id3), `^KS11`(id4), `^IXIC`(id12), `^DJI`(id13), `^KQ11`(id14), `^N225`(id15), `^HSI`(id16), `^VIX`(id8). FMP `/stable/`에서 일부 글로벌 인덱스(특히 **한국 `^KS11`/`^KQ11`**)는 Starter 플랜 커버리지가 불확실 → 실 호출 검증 필요.
- **FX 포맷 비일관**: id9 `'USDKRW'`(구분자 없음, fmp) vs id39 `'DX-Y.NYB'`(Yahoo 스타일, fmp) vs id38 `DEXUSEU`(fred). 같은 환율 계열인데 소스·포맷이 제각각. 특히 `DX-Y.NYB`는 FMP `/stable/` 미지원 가능성.
- **`metrics` 소스(id 60~73)**: `metric_code`가 `quarterly_metric_fetcher`/validation 시스템의 RATIO_METRICS 키와 일치해야 함. 14개 코드(`gross_margin`, `roic`, `ev_to_ebitda` 등) 자체 일관성은 양호하나, metrics 시스템 측 키 정의와의 교차 검증은 본 감사 범위(4개 파일) 밖 — 별도 확인 권장.

---

## 권장 후속 조치 (우선순위)

| 우선 | 항목 | 조치 |
|------|------|------|
| P0 | id 56·57 scale_multiplier | FMP 응답 스케일 실측 → 0~1이면 `scale_multiplier:100` 추가 (#14 재발 차단) |
| P1 | `EPS 추이` 타입 드리프트 | KEYWORD_RULES 인라인 `indicator_type`을 `fundamental`로 정정, 또는 인라인 메타 제거 후 카탈로그 참조로 단일화 |
| P1 | FMP 한국지수/`DX-Y.NYB` 커버리지 | `^KS11`/`^KQ11`/`DX-Y.NYB` 실 호출 검증, 미지원 시 대체 소스 |
| P2 | 카테고리 단일 소스화 | FE category를 BE `category`/contracts에서 파생하도록 codegen 또는 매핑 테이블 도입 |
| P2 | 미참조 11개 지표 | 기술적 지표(41~47) 등에 FE 키워드 룰 추가하여 추천 동선 확보 |
| P3 | description FE 노출 | 코드젠으로 description을 FE 카탈로그에 미러링 → 선택 UX에 설명 표시 |
| P3 | match_by_gemini 경로 정책 | `match_indicators_for_premise` 폴백도 카탈로그 검증 적용(환각 방지 정책 일관화) |

---

### 감사 대상 파일 (라인 기준)
- `thesis/services/prompt_builder.py:14-310` (INDICATOR_CATALOG), `:321-342` (INDICATOR_FREQUENCY)
- `thesis/services/indicator_matcher.py:12-154` (KEYWORD_RULES), `:271-329` (LLM 매칭)
- `thesis/services/llm_postprocess.py:82-95` (indicator_db_id 교정)
- `frontend/components/thesis/AddIndicatorSheet.tsx:15-91` (FE CATALOG), `:109-139` (KEYWORD_INDICATOR_MAP)

> 본 보고서는 읽기 전용 감사 결과이며 코드를 일절 변경하지 않았습니다.
