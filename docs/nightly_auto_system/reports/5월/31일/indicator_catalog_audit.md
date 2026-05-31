# 지표 카탈로그 동기화 감사 보고서

- **감사 일자**: 2026-05-31
- **감사 범위**: 읽기 전용 (코드 수정 없음)
- **대상 파일**:
  - BE 정의: `thesis/services/prompt_builder.py` (`INDICATOR_CATALOG`, `INDICATOR_FREQUENCY`)
  - BE 후처리: `thesis/services/llm_postprocess.py`
  - BE 매칭: `thesis/services/indicator_matcher.py` (`KEYWORD_RULES`)
  - BE 소비: `thesis/tasks/eod_pipeline.py`, `thesis/serializers/indicator_serializers.py`
  - FE 표시/매칭: `frontend/components/thesis/AddIndicatorSheet.tsx` (`INDICATOR_CATALOG`, `KEYWORD_INDICATOR_MAP`)
  - FE 보조: `frontend/components/thesis/indicators/AddIndicatorSheet.tsx` (AI 추천 전용, 카탈로그 미보유)

---

## 요약 (동기화 상태)

| 검사 항목 | 상태 | 비고 |
|---|---|---|
| BE ↔ FE 카탈로그 항목 (id+name) | ✅ 정상 | 64/64 완전 일치, 불일치 0건 |
| 업데이트 주기(frequency) 동기화 | ✅ 정상 | BE `INDICATOR_FREQUENCY` ↔ FE `freq` 전건 일치 |
| 카테고리 분류 체계 | ⚠️ 의도된 차이 | BE 5개 대분류 vs FE 17개 세분류 (UI용, 1:1 아님) |
| description 품질 | ✅ 정상 | BE 64/64 존재·비어있음 0·10자 미만 0. FE는 description 필드 미보유(설계) |
| BE `KEYWORD_RULES` 고아 규칙 | ✅ 없음 | 11개 규칙 전부 카탈로그에 매칭 |
| BE `KEYWORD_RULES` 커버리지 | 🔴 심각 | 64개 중 **11개만** 키워드 폴백 가능 (53개 사각지대) |
| FE `KEYWORD_INDICATOR_MAP` 고아 규칙 | ✅ 없음 | 참조 id 전부 카탈로그 존재 |
| BE ↔ FE 키워드 룰 동기화 | 🔴 심각 | 별개 시스템, 커버리지 11 vs 53으로 발산 |
| data_params 키 화이트리스트 | ✅ 정상 | 카탈로그 사용 키 전부 `ALLOWED_DATA_PARAM_KEYS` 포함 |
| data_params ↔ FMP 형식 | 🔴/⚠️ 위험 | 수급 2건 FMP 조회 불가(HIGH), TTM 필드명·지수 심볼 다수 검증 필요(MEDIUM) |

**총평**: 카탈로그 본체(id·name·frequency)는 BE↔FE 완벽 동기화 상태이며 description 품질도 결함 없음. **그러나 (1) 키워드 추천 룰이 BE/FE 이중 구현 + 커버리지 발산, (2) 일부 지표의 data_params가 실제 FMP 엔드포인트와 구조적으로 맞지 않아 항상 `None` 반환** — 두 영역이 실질적 위험 요소.

---

## BE ↔ FE 불일치 목록

### 카탈로그 항목 (id + name)

- **BE `INDICATOR_CATALOG`**: 64개 (`prompt_builder.py:14-310`)
- **FE `INDICATOR_CATALOG`**: 64개 (`AddIndicatorSheet.tsx:15-91`)
- **id 집합 비교**: 완전 일치 — BE에만 있거나 FE에만 있는 id **0건**
- **name 비교**: id별 name 문자열 전건 일치 (예: id50 `PER (주가수익비율)`, id58 `매출성장률 (YoY)`, id73 `순주주수익률` 모두 동일)

> 결론: **항목 동기화는 완전(64/64)**. 과거 #11/#14 audit 이후 양측이 잘 정렬됨.

### frequency 동기화

BE `INDICATOR_FREQUENCY`(`prompt_builder.py:321-342`)의 일간/주간/월간/분기 ↔ FE `freq` 필드 전건 일치.
샘플 검증: id6 주간/주간, id7 일간/일간, id37 주간/주간, id34 분기/분기, id31 월간/월간, id5 분기/분기 — 불일치 없음.

### 카테고리 분류 (의도된 차이, 결함 아님)

| 측 | 분류 체계 | 값 |
|---|---|---|
| BE `category` | 5개 대분류 | `market_data` / `macro` / `technical` / `fundamental` / `sentiment` |
| FE `category` | 17개 세분류 | `수급` / `주요 지수` / `원자재` / `암호화폐` / `금리` / `환율/변동성` / `고용/성장` / `물가/주택` / `기술적` / `펀더멘털` / `재무 체질` / `밸류에이션` / `성장` / `운영 효율` / `이익 품질` / `주주환원` / `심리` |

- FE는 UI 그룹핑을 위해 더 잘게 쪼갬 (display 전용, 로직에 미사용).
- ⚠️ **주의**: 두 분류는 공유 taxonomy가 없으므로, 향후 category 기반 로직이 생기면 동기화 비용 발생. 현재는 무해.

### FE 카탈로그의 필드 축소 (설계상)

FE `CatalogIndicator` 인터페이스는 `{ id, name, category, freq }` 만 보유. BE의 `data_source` / `data_params` / `support_direction` / `description`은 **FE에 미러되지 않음**.
- → FE는 표시 전용이므로 적절. data_params 동기화 부담 없음.
- → 단, **description은 BE에만 존재**. 사용자에게 지표 설명을 노출하려면 별도 API/필드 필요 (현재 root `AddIndicatorSheet`는 description 미표시, freq 칩만 표시).

### 두 개의 FE `AddIndicatorSheet` 컴포넌트 (혼동 주의)

| 경로 | 역할 | 사용처 | 카탈로그 |
|---|---|---|---|
| `components/thesis/AddIndicatorSheet.tsx` (307줄) | 인라인 카탈로그 + 키워드 추천 + 수동 선택 | `app/thesis/new/page.tsx` | 보유(64개) |
| `components/thesis/indicators/AddIndicatorSheet.tsx` (83줄) | 서버 AI 추천(`RecommendedIndicator`) 표시 | `app/thesis/[thesisId]/indicators/page.tsx` | 미보유 |

- 동명(同名) 컴포넌트 2개가 공존. 둘 다 live. 카탈로그 동기화 대상은 **root 버전만** 해당.
- ⚠️ 향후 카탈로그 변경 시 어느 쪽을 만지는지 혼동 위험.

---

## description 품질

### BE (`prompt_builder.py`)

- **총 64개 전부 `description` 보유** — 누락 0건.
- **빈 문자열 0건.**
- **10자 미만 0건** (최단: id14 코스닥 `한국 중소형 성장주 시장 지수.` 15자).
- 품질 양호 — 대부분 "정의 + 투자적 의미" 2문장 구조.

| 점검 | 결과 |
|---|---|
| 빈 description | 0건 ✅ |
| 10자 미만 | 0건 ✅ |
| 누락(키 없음) | 0건 ✅ |

`get_indicator_description()`(`prompt_builder.py:351-361`)이 접두사 매칭(예: `EPS 추이 (META)`)까지 지원 — 견고.

### FE

- FE 카탈로그에는 `description` 필드 자체가 없음(설계). → "품질 미달" 대상 아님.
- AI 추천 경로(`indicators/AddIndicatorSheet` → `RecommendCard`)는 서버가 내려준 `RecommendedIndicator.reason`을 표시하므로 카탈로그 description과 무관.

> 결론: **description 품질 결함 없음.**

---

## keyword_rules 고아

키워드 룰은 **BE와 FE에 각각 별개로 존재**하며, 참조 방식·커버리지가 크게 다름.

### BE `KEYWORD_RULES` (`indicator_matcher.py:12-154`)

- 11개 규칙, 지표를 **이름(name)** 으로 참조.
- **고아 규칙: 0건** — 모든 규칙의 지표 name이 카탈로그에 존재.
- **커버리지: 64개 중 11개만** (id 1,2,3,4,5,6,7,8,9,10,11 = 초기 저(低)id 세트).
  - `match_by_keywords()`가 추천할 수 있는 지표는 이 11개로 한정.
  - 확장된 53개(id 12~73의 지수·원자재·암호화폐·금리·고용·물가·기술적 9종·펀더멘털 24종)는 **키워드 폴백으로 도달 불가**. LLM의 `indicator_db_id` PK 매칭(`match_indicators_for_llm`)으로만 추천됨.

  🔴 **사각지대**: LLM이 PK를 못 채우고 키워드 폴백으로 떨어지면, 확장 지표 전부가 추천 후보에서 빠짐.

- ⚠️ **메타데이터 드리프트 1건**: EPS 룰(`indicator_matcher.py:90-98`)의 `indicator_type='market_data'` — 카탈로그 id5 EPS의 `category='fundamental'`과 불일치.
  - 영향 경미: `match_indicators_for_llm`이 `_find_in_catalog(name)`으로 카탈로그 항목을 재해석하므로 최종 저장값은 보정됨. 그러나 소스 데이터의 일관성 결함.

### FE `KEYWORD_INDICATOR_MAP` (`AddIndicatorSheet.tsx:109-139`)

- 29개 규칙, 지표를 **id** 로 참조.
- **고아 규칙: 0건** — 참조 id 전부 카탈로그에 존재 (13,14,22,38,41~47 제외한 ~53개 id 참조).
- **커버리지: 64개 중 53개** — "전제 관련 추천"에서 추천되지 않는 11개:
  - id13 다우존스, id14 코스닥, id22 은(Silver), id38 달러/유로, id41 스토캐스틱, id42 볼린저, id43 ATR, id44 OBV, id45 SMA50, id46 SMA200, id47 EMA12
  - → 전체 카탈로그 목록에는 노출되므로 **수동 추가는 가능**. 자동 추천만 누락.

### BE ↔ FE 키워드 룰 동기화

🔴 **두 시스템이 독립적이며 발산**:

| | BE `KEYWORD_RULES` | FE `KEYWORD_INDICATOR_MAP` |
|---|---|---|
| 참조 방식 | name 기반 | id 기반 |
| 규칙 수 | 11 | 29 |
| 지표 커버리지 | 11 / 64 | 53 / 64 |
| 다중 매핑 | 일부(금리·정치) | 다수(실적→7개 등) |

- 같은 "키워드→지표" 의도를 두 곳에서 따로 관리 → 한쪽 수정 시 타쪽 누락 위험.
- 동일 사용자 입력에 대해 BE 폴백 추천과 FE 추천이 **서로 다른 결과**를 낼 수 있음.

> 권고(수정 아님, 후속 과제): BE `KEYWORD_RULES`를 FE 수준(id 기반·확장 커버리지)으로 끌어올리거나, 단일 소스(예: 카탈로그에 keyword 필드 통합 후 BE/FE 생성)로 통일. `feedback_indicator_catalog_sync` 메모리(3곳 분산 미러)와 정확히 같은 리스크.

---

## data_params 형식

### 구조 개요

`data_params`는 `data_source`별로 형태가 다른 polymorphic dict. 소비처는 `thesis/tasks/eod_pipeline.py`의 `DATA_SOURCE_FETCHERS` 분기.

| data_source | data_params 형태 | 소비 엔드포인트 |
|---|---|---|
| `fmp` (symbol) | `{'symbol': '^GSPC'}` | `/stable/historical-price-eod/light` |
| `fmp` (metric) | `{'metric': 'returnOnEquityTTM', 'scale_multiplier': 100, ...}` | `/stable/key-metrics-ttm` (또는 `endpoint` 지정 시 분기) |
| `fmp` (technical) | `{'indicator': 'RSI', 'period': 14}` | (별도 처리) |
| `fred` | `{'series_id': 'FEDFUNDS'}` | `api.stlouisfed.org/.../observations` |
| `news_sentiment` | `{}` (+ target_symbol) | 내부 |
| `metrics` | `{'metric_code': 'gross_margin'}` | `quarterly_metric_fetcher` |

### 화이트리스트 정합성 ✅

`indicator_serializers.py`의 `ALLOWED_DATA_PARAM_KEYS`에 카탈로그가 사용하는 키(`symbol/metric/series_id/indicator/period/fast/slow/signal/metric_code/inverse/scale_multiplier/endpoint/audit_note`)가 **전부 포함**. data_params **키 드리프트 없음**.

### 🔴 HIGH — FMP 조회가 구조적으로 불가능한 2건

`_fetch_fmp_value()`(`eod_pipeline.py:82-154`)는 `metric`이 `TTM`로 끝나거나 `endpoint=='financial-growth'`면 `key-metrics-ttm`/`financial-growth` 분기, 그 외에는 `/stable/quote` 분기(`value_map`)로 처리. quote 분기에서 `value_map`에 없는 metric은 `field = metric` 그대로 `quote.get(field)` → 응답에 없는 필드명이면 항상 `None`:

| id | 지표 | data_params | 문제 |
|---|---|---|---|
| 1 | 외국인 순매수 추이 | `{'metric': 'foreign_net_buy'}` | quote 분기 진입, `value_map`에 키 없음 → `quote.get('foreign_net_buy')` → FMP(미국 제공자)는 한국식 외국인 일별 순매수 미제공 → 항상 None |
| 2 | 기관 순매수 추이 | `{'metric': 'institutional_net_buy'}` | 동일. `quote.get('institutional_net_buy')` → 미제공 → 항상 None |

> 영향: id1/id2는 데이터 출처 자체가 부재(별도 KR 수급 소스 필요). EOD 파이프라인에서 값을 채울 수 없음.
>
> **정정 노트**: id5 EPS(`{'metric':'eps'}`)는 위험 아님 — `value_map['eps']='eps'`(`eod_pipeline.py:133`)로 `/stable/quote`의 `eps` 필드를 정상 조회. symbol 미지정 시 `thesis.target`으로 폴백(`eod_pipeline.py:98-101`).

### ⚠️ MEDIUM — 검증 필요한 FMP 펀더멘털 필드명 (#14 재발 패턴)

카탈로그가 `audit_note`로 이미 처리한 항목(✅ 방어됨):
- id50 PER `earningsYieldTTM`+`inverse` / id52 ROE `returnOnEquityTTM`×100 / id53 ROA `returnOnAssetsTTM`×100 / id58 매출성장률 `growthRevenue`@`financial-growth`×100

`audit_note` 없이 `*TTM` 필드명을 그대로 쓰는 항목 — FMP `/stable/key-metrics-ttm` 실제 응답 필드명과 대조 권장(읽기 전용 감사라 live 호출 미수행):

| id | 지표 | metric | 비고 |
|---|---|---|---|
| 51 | PBR | `pbRatioTTM` | key-metrics-ttm vs ratios-ttm 필드명 확인 필요 |
| 54 | 부채비율 | `debtToEquityTTM` | 〃 |
| 55 | 잉여현금흐름 | `freeCashFlowTTM` | 〃 (금액 단위) |
| 56 | 배당수익률 | `dividendYieldTTM` | 0~1 스케일 여부(×100 필요?) 확인 |
| 57 | 영업이익률 | `operatingProfitMarginTTM` | 0~1 스케일 여부 확인 |

> 이들이 응답에 없으면 #14처럼 조용히 None 반환. `audit_note`로 명시 표기 권장.

### ⚠️ MEDIUM — 지수/통화 심볼 형식

`_fetch_fmp()` symbol 분기는 `/stable/historical-price-eod/light?symbol=...` 사용. 아래 심볼은 FMP Starter 플랜 지원 여부/형식 확인 필요:

- 미국 지수 `^GSPC`/`^IXIC`/`^DJI`, VIX `^VIX` — FMP 인덱스가 프리미엄(402, 버그 #23)일 수 있음
- 한국/아시아 지수 `^KS11`(KOSPI)/`^KQ11`(코스닥)/`^N225`/`^HSI` — FMP 지원 범위 밖일 가능성
- 달러 인덱스 `DX-Y.NYB` (id39) — **Yahoo Finance 형식**. FMP는 다른 심볼 체계 사용 가능 → 형식 불일치 의심

> 읽기 전용이라 실제 응답 미확인. 위 심볼들은 별도 live 검증(또는 `historical-price-eod/light` 응답 샘플 확인) 후 형식 교정 여부 판단 필요.

### FE 측 data_params

FE 카탈로그는 data_params 미보유 → BE↔FE data_params 동기화 이슈 **없음**.

---

## 부록: 후처리 안전망 (참고)

`llm_postprocess.normalize_llm_output()`(`llm_postprocess.py:82-95`)은 LLM이 반환한 `indicator_db_id`가 카탈로그에 없으면 `None`으로 교정 + 로그. `match_indicators_for_llm`(`indicator_matcher.py:271-329`)은 `match_by_gemini` 환각 폴백을 의도적으로 제외하고 키워드 룰만 사용 — 카탈로그 외 지표 생성 차단(메모리 `feedback_llm_indicator_hallucination`과 일치). → 카탈로그 무결성 방어선은 견고.

---

## 권고 요약 (우선순위)

| 순위 | 항목 | 조치 방향 (※ 본 감사는 수정 미수행) |
|---|---|---|
| P0 | id1/id2 수급 지표 | FMP로는 조회 불가 — KR 수급 데이터 소스 별도 확보 또는 카탈로그에서 비활성/표기 |
| P1 | BE↔FE 키워드 룰 발산 | 단일 소스화 또는 BE `KEYWORD_RULES` 커버리지 확장(11→53) |
| P1 | MEDIUM TTM 필드명 5건 | FMP 응답 대조 후 `audit_note`/스케일 보정 명시 |
| P2 | DXY/지수 심볼 형식 | FMP 심볼 체계 live 검증 |
| P2 | EPS 룰 indicator_type 드리프트 | `market_data`→`fundamental` 정정 |
| P3 | 동명 `AddIndicatorSheet` 2개 | 네이밍 구분(혼동 방지) |
