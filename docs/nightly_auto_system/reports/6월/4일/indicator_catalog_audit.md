# 지표 카탈로그 동기화 감사 보고서

- **작성일**: 2026-06-04
- **모드**: 읽기 전용 (코드 수정 없음)
- **감사 대상**:
  - BE 정의: `thesis/services/prompt_builder.py` (`INDICATOR_CATALOG`)
  - BE 후처리: `thesis/services/llm_postprocess.py`
  - BE 매칭: `thesis/services/indicator_matcher.py` (`KEYWORD_RULES`)
  - BE fetch: `thesis/tasks/eod_pipeline.py` (data_params 실제 소비처)
  - FE 표시: `frontend/components/thesis/AddIndicatorSheet.tsx` (`INDICATOR_CATALOG` 미러 + `KEYWORD_INDICATOR_MAP`)

---

## 요약 (동기화 상태)

| 검사 항목 | 결과 | 심각도 |
|-----------|------|--------|
| BE↔FE 카탈로그 **ID/이름** 동기화 | ✅ 64개 전건 일치 | — |
| BE↔FE **category 필드** 의미 차이 | ⚠️ 의도적 분리 (BE 5종 ↔ FE 17종 표시용) | INFO |
| description 빈 값 / 10자 미만 | ✅ 없음 (64/64 적정) | — |
| **2개 키워드 시스템 분기** (BE `KEYWORD_RULES` ↔ FE `KEYWORD_INDICATOR_MAP`) | ⚠️ 완전 별개, 미동기화 | P2 |
| BE `KEYWORD_RULES` `indicator_type` ↔ 카탈로그 `category` 불일치 | ⚠️ EPS 1건 | P2 |
| FE 키워드맵 고아 ID | ✅ 없음 (참조 ID 전부 카탈로그 존재) | — |
| 키워드로 **추천 불가능한** 카탈로그 항목 | ⚠️ 11개 (수동 선택만 가능) | INFO |
| **data_params ↔ 실제 제공자 형식 불일치** | 🔴 `foreign_net_buy`/`institutional_net_buy` 상시 None | **P1** |
| 한국 지수(`^KS11`/`^KQ11`) FMP 커버리지 | ⚠️ 검증 필요 | P2 |
| `.` 포함 심볼(`DX-Y.NYB`) FMP 402 위험 | ⚠️ 검증 필요 (common-bugs #23) | P2 |

**종합**: 카탈로그 본체(ID/이름/description)의 BE↔FE 정합성은 **양호**. 핵심 위험은 (1) 수급 지표 2종이 FMP에서 데이터를 받지 못하는 **데이터 형식 불일치(P1)**, (2) BE/FE 키워드 추천 룰이 **이중 정의**되어 표류 위험이 있는 구조 문제(P2)에 집중됨.

---

## BE ↔ FE 불일치 목록

### 1. 카탈로그 항목 (ID / 이름) — ✅ 완전 일치

- BE `INDICATOR_CATALOG`: **64개** (`prompt_builder.py:14-310`)
- FE `INDICATOR_CATALOG`: **64개** (`AddIndicatorSheet.tsx:15-91`)
- ID 집합 동일, 각 ID의 `name` 문자열 **전건 동일**.
- BE에만 있고 FE에 없는 항목: **없음**
- FE에만 있고 BE에 없는 항목: **없음**

> ID는 연속이 아님(1~73 중 17·18·19·27~29·48·49·59 등 결번). 양쪽 동일하게 결번 처리되어 정합.

### 2. `category` 필드 — ⚠️ 의도적 의미 분리 (INFO)

| 측 | category 종류 | 목적 |
|----|--------------|------|
| BE | `market_data` / `macro` / `technical` / `fundamental` / `sentiment` (5종) | LLM 프롬프트 그룹핑 + `indicator_type` 매핑 |
| FE | `수급` / `주요 지수` / `원자재` / `암호화폐` / `금리` / `환율/변동성` / `고용/성장` / `물가/주택` / `기술적` / `펀더멘털` / `재무 체질` / `밸류에이션` / `성장` / `운영 효율` / `이익 품질` / `주주환원` / `심리` (17종) | 바텀시트 표시용 세분류 |

- FE는 BE 5종을 화면 표시용 17종으로 **세분화**한 별도 체계. 1:1 매핑이 아니므로 "불일치"가 아닌 **표현 계층 분리**로 판단.
- **위험**: 신규 지표 추가 시 BE category(필수, fetch 분기 영향)와 FE category(표시 그룹) 양쪽을 각각 수동 관리해야 함. FE `categoryOrder` 배열(`AddIndicatorSheet.tsx:211-216`)에 누락 시 해당 그룹이 화면에서 통째로 사라짐(렌더 가드 `if (!indicators) return null`).

### 3. FE 미러의 누락 필드 — INFO

- FE `CatalogIndicator`는 `{id, name, category, freq}`만 보유.
- BE만 보유: `data_source`, `data_params`, `support_direction`, `description`.
- FE는 표시 전용(추가 버튼 + 빈도 배지)이므로 누락은 설계 의도. 단, **FE `freq` ↔ BE `INDICATOR_FREQUENCY`(`prompt_builder.py:321-342`)** 도 별도 미러이므로 동기화 대상임 — 본 감사에서 64건 빈도 값 스팟 체크 결과 일치(예: id6 주간, id37 주간, id34 분기).

---

## description 품질

- **검사 범위**: BE `INDICATOR_CATALOG` 64개 전건 (`description` 키).
- **빈 description**: **0건** (모든 항목이 비어있지 않음).
- **10자 미만**: **0건**. 최단 항목도 13자 이상이며 완결된 문장 형태.
  - 최단 예시: id14 `한국 중소형 성장주 시장 지수.` / id4 `한국 유가증권시장 전체 종목 시가총액 가중 지수.`
- **품질 평가**: 전 항목이 "정의 + 시장 의미"의 2문장 구조를 일관 유지(예: id23 구리 — *"구리 선물 가격. 경기 선행지표로 'Dr. Copper'라 불림."*). 양호.
- **참고**: FE 미러에는 description이 없어 `get_indicator_description()`(`prompt_builder.py:351`)는 BE 단일 소스. FE 화면에 설명 노출이 필요해지면 추가 미러가 발생할 수 있음.

---

## keyword_rules 고아

> ⚠️ **구조 핵심 발견**: 키워드 추천 룰이 **2곳에 완전히 별개로 정의**되어 있음.

### A. BE `KEYWORD_RULES` (`indicator_matcher.py:12-154`)

- **11개 룰**, 지표를 **이름(name) + data_source/data_params 인라인 복제**로 정의 (카탈로그 ID 참조가 아님).
- 사용된 이름 11종 모두 카탈로그에 **존재** → **고아 룰 없음**.
- 단, **두 가지 표류 위험**:
  1. **`indicator_type` 불일치 1건**: `'EPS 추이'` 룰의 `indicator_type='market_data'`(`indicator_matcher.py:95`) 인데 카탈로그 id5는 `category='fundamental'`. fetch에는 영향 없으나 의미 불일치.
  2. **data_params 이중 정의**: 같은 지표의 `data_source`/`data_params`를 카탈로그와 `KEYWORD_RULES`가 각각 보유. 카탈로그만 수정하면 `match_by_keywords()` 경로(`match_indicators_for_premise`)는 옛 값을 계속 사용 → **표류 위험**.
- **방어 장치 존재**: LLM 빌더 경로 `match_indicators_for_llm()`(`indicator_matcher.py:271-329`)는 PK(카탈로그 id) 1순위, 키워드 매칭 시 `_find_in_catalog(name)`로 **카탈로그 최종 검증**(`:316-317`) → 환각/표류 일부 차단. 단 이름이 정확히 일치해야 하므로 카탈로그 이름 변경 시 `KEYWORD_RULES`의 이름도 동시 수정 필수.
- `match_by_gemini()`(`indicator_matcher.py:186`)는 카탈로그 외 지표를 생성할 수 있어 LLM 빌더 경로에서 **의도적으로 제외**됨(`:306-307` 주석). 단 `match_indicators_for_premise()` 비-LLM 경로에서는 여전히 fallback으로 호출됨 → 환각 지표 유입 잔존 경로.

### B. FE `KEYWORD_INDICATOR_MAP` (`AddIndicatorSheet.tsx:109-139`)

- **27개 룰**, 지표를 **ID 배열(`indicatorIds`)**로 참조.
- 참조된 모든 ID가 카탈로그에 **존재** → **고아 ID 없음**.
- BE `KEYWORD_RULES`(11룰, 이름 기반)와 **완전히 다른 별개 시스템** — 룰 개수·키워드·대상 지표가 모두 상이. 동일 입력에 대해 BE와 FE가 **서로 다른 지표를 추천**할 수 있음.

### C. 키워드로 추천 불가능한 카탈로그 항목 (INFO)

FE `KEYWORD_INDICATOR_MAP` 어느 룰에도 등장하지 않는 카탈로그 ID **11개** (수동 선택만 가능, 전제 기반 자동 추천 대상 아님):

| ID | 지표 |
|----|------|
| 13 | 다우존스 |
| 14 | 코스닥 지수 |
| 22 | 은 (Silver) |
| 38 | 달러/유로 환율 |
| 41 | 스토캐스틱 %K |
| 42 | 볼린저 밴드 %B |
| 43 | ATR (평균진폭) |
| 44 | OBV (거래량 누적) |
| 45 | SMA 50일 |
| 46 | SMA 200일 |
| 47 | EMA 12일 |

> 고아 "룰"은 아니며(룰→없는 지표 참조는 0건), 반대로 **룰의 사각지대에 있는 지표**. 기술적 지표(41~47)가 다수 — RSI/MACD(id 10,40)만 키워드 추천되고 나머지 기술 지표는 수동 추가만 가능.

---

## data_params 형식

### 🔴 P1 — `foreign_net_buy` / `institutional_net_buy` 상시 None

- **대상**: id1 외국인 순매수 추이 `{'metric': 'foreign_net_buy'}`, id2 기관 순매수 추이 `{'metric': 'institutional_net_buy'}` (`prompt_builder.py:17,21`)
- **fetch 경로**: `_fetch_fmp_value()`(`eod_pipeline.py:81-154`)
  - `symbol` 없음 → thesis.target(주식 티커)으로 fallback
  - metric이 `TTM`도 아니고 `endpoint`도 없음 → **분기 2 `/stable/quote`** 진입
  - `value_map`(`eod_pipeline.py:128-138`)에 `foreign_net_buy`/`institutional_net_buy` **키 없음** → `field = metric` 그대로 → `quote.get('foreign_net_buy')` = **None**
- **근본 원인**: FMP `/stable/quote` 응답에 외국인/기관 순매수 필드가 존재하지 않음(한국 거래소 수급 데이터로, FMP 미제공). 데이터 소스 가정과 실제 제공자 스키마 불일치.
- **영향**: 두 지표를 선택해도 IndicatorReading이 영구히 적재되지 않음(`validation_status='null_value'`). 점수 기여 0. 카탈로그·키워드 룰·프롬프트에는 정상 노출되므로 **사용자에게는 "추적 중"으로 보이나 실제로는 dead**.
- **권고(보고용)**: 별도 데이터 소스 필요(KRX/대체 제공자) 또는 카탈로그에서 제외. 코드 수정은 본 감사 범위 외.

### ⚠️ P2 — 한국 지수 `^KS11` / `^KQ11` FMP 커버리지

- 대상: id4 KOSPI `{'symbol':'^KS11'}`, id14 코스닥 `{'symbol':'^KQ11'}` (`prompt_builder.py:31,43`)
- `/stable/quote`로 조회되나, FMP의 한국 지수 커버리지가 불확실. 미지원 시 `quote={}` → None.
- **검증 필요**: 운영 FMP 키로 `/stable/quote?symbol=^KS11` 실응답 확인 권장(본 감사 정적 분석으로는 단정 불가).

### ⚠️ P2 — `.` 포함 심볼 FMP 402 위험 (common-bugs #23 연계)

- 대상: id39 달러 인덱스 `{'symbol':'DX-Y.NYB'}` (`prompt_builder.py:119`)
- common-bugs #23: FMP 프리미엄/특수 심볼 중 `.` 포함 심볼이 402(`FMPPremiumError`)를 유발해 배치에서 제외되는 패턴 존재.
- `_fetch_fmp_value`는 `FMPPremiumError`를 잡아 None 반환(`eod_pipeline.py:146-148`)하므로 크래시는 없으나, 값이 안 들어올 수 있음. **검증 필요**.

### ✅ 정상 — TTM/financial-growth 메타 처리 (#14 회귀 방지 적용됨)

- id50 PER `{'metric':'earningsYieldTTM','inverse':True}` → `_apply_value_postprocess` 역수 처리(`eod_pipeline.py:36-39`)
- id52 ROE / id53 ROA `{'scale_multiplier':100}` → ×100 % 변환(`eod_pipeline.py:40-42`)
- id58 매출성장률 `{'endpoint':'financial-growth','metric':'growthRevenue','scale_multiplier':100}` → `/stable/financial-growth` 분기(`eod_pipeline.py:57-62`)
- 카탈로그에 `audit_note`로 #14 근거 명시. data_params ↔ fetcher 분기 정합 확인.

### ✅ 정상 — data_source별 파라미터 키 일관성

| data_source | 기대 키 | fetcher 참조 | 카탈로그 항목 | 정합 |
|-------------|---------|--------------|--------------|------|
| `fred` | `series_id` | `_fetch_fred_value:162` | id6,7,30,31~38 등 | ✅ 전건 `series_id` 보유 |
| `metrics` | `metric_code` | `_fetch_metrics_value:235` | id60~73 | ✅ 전건 `metric_code` 보유 |
| `news_sentiment` | (symbol/없음) | `_fetch_news_sentiment_value:204` | id11 `{}` | ⚠️ id11 data_params 빈 dict → symbol 없으면 None. thesis.target fallback 없음(fred/metrics와 달리 symbol fallback 미구현) → **종목 미지정 시 항상 None** |
| `fmp` (TTM) | `metric(...TTM)` + meta | `_fetch_fmp_ttm_or_growth:68` | id50,52,53 | ✅ |

> **추가 발견(P2)**: id11 뉴스 센티먼트는 `data_params={}`이고 `_fetch_news_sentiment_value`는 `params.get('symbol')`만 보고 fallback이 없어, target_symbol 미지정 시 상시 None. (fmp/metrics fetcher는 thesis.target fallback 있음.)

---

## 부록 — 점검 방법 및 한계

- **정적 분석 기준**: 4개 BE 파일 + 1개 FE 파일을 직접 대조. 외부 API 실호출은 수행하지 않음(읽기 전용).
- **테스트 커버리지**: `tests/unit/thesis/test_llm_builder.py:157` `test_indicator_catalog_has_all_fields`가 `id/name/category/data_source` 존재만 검증. **description 비어있음·BE↔FE 동기화·keyword_rules 정합은 테스트 없음** → 회귀 방지 사각지대.
- **단정 불가 항목**: FMP의 한국 지수/forex/commodity/crypto 심볼 실제 커버리지(P2 2건)는 운영 키 실호출 검증 필요.
- **본 보고서는 수정 제안만 포함하며 코드 변경을 수행하지 않음.**
