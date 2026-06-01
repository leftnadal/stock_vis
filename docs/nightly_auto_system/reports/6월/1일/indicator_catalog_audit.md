# 지표 카탈로그 동기화 감사 보고서

- **감사일**: 2026-06-01
- **모드**: 읽기 전용 (코드 수정 없음)
- **감사 대상**:
  - BE 정의: `thesis/services/prompt_builder.py` (`INDICATOR_CATALOG`, 64개)
  - BE 후처리: `thesis/services/llm_postprocess.py`
  - BE 매칭: `thesis/services/indicator_matcher.py` (`KEYWORD_RULES`, 11규칙)
  - FE 표시: `frontend/components/thesis/AddIndicatorSheet.tsx` (`INDICATOR_CATALOG` 미러 64개 + `KEYWORD_INDICATOR_MAP` 30규칙)
  - 데이터 정의: `packages/shared/metrics/management/commands/seed_metric_definitions.py` (`metric_code` 34종)

---

## 요약 (동기화 상태)

| 검사 항목 | 상태 | 비고 |
|----------|------|------|
| BE ↔ FE 지표 **id/name** 동기화 | ✅ **완전 일치** | 64개 전건 id·name 동일, 누락 0 |
| BE ↔ FE **frequency** 동기화 | ✅ 일치 | `INDICATOR_FREQUENCY` ↔ FE `freq` 64건 일치 |
| BE ↔ FE **category 라벨** | ⚠️ 구조적 분기 | BE 5개 코드값 ↔ FE 17개 표시 라벨 (단일 소스 없음) |
| FE의 **description 보유** | ⚠️ 부재 | FE 카탈로그에 `description` 필드 자체가 없음 |
| BE description 품질 (빈값/<10자) | ✅ 양호 | 64개 전부 채워짐, 빈값·과소(<10자) 0건 |
| `KEYWORD_RULES` 고아 규칙 | ✅ 없음 | 참조 name 11종 전부 카탈로그 존재 |
| BE ↔ FE **키워드 룰** 동기화 | ⚠️ 별개 시스템 | BE 11규칙(name 기반) ↔ FE 30규칙(id 기반), 미러 아님 |
| `data_source='metrics'` metric_code | ✅ 일치 | 14개 전부 `seed_metric_definitions`에 존재 |
| `data_source='fmp'` 수급 지표 형식 | 🔴 의심 | `foreign_net_buy`·`institutional_net_buy` FMP 비표준 |
| 기술적 지표 `data_params` | ⚠️ 불완전 | `symbol` 부재 — fetch 시 target 주입 의존 |

**종합 판정**: 핵심 동기화축(id/name/freq)은 **건강**. 단 FE가 BE와 별개로 (1) category 세분류, (2) description 부재, (3) 키워드 룰 30종을 독자 유지 → **3중 미러 드리프트 리스크**. data_params 측면에서는 FMP 수급 지표 2건이 잠재적 데이터 공급자 불일치.

---

## BE ↔ FE 불일치 목록

### 1. 지표 id/name — 불일치 **없음** ✅

BE(`prompt_builder.py:14-310`)와 FE(`AddIndicatorSheet.tsx:15-91`) 모두 동일한 64개 id를 보유하며 id별 name이 전건 일치.

```
공통 id (64): 1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,20,21,22,23,24,25,26,
              30,31,32,33,34,35,36,37,38,39,40,41,42,43,44,45,46,47,
              50,51,52,53,54,55,56,57,58,60,61,62,63,64,65,66,67,68,69,70,71,72,73
BE에만 있는 것: 없음
FE에만 있는 것: 없음
```

### 2. category 라벨 — 구조적 분기 ⚠️

| 위치 | category 값 | 개수 |
|------|------------|------|
| BE (`category` 필드) | `market_data`, `macro`, `technical`, `fundamental`, `sentiment` | 5 (대분류 코드) |
| FE (`category` 필드) | `수급`, `주요 지수`, `원자재`, `암호화폐`, `금리`, `환율/변동성`, `고용/성장`, `물가/주택`, `기술적`, `펀더멘털`, `재무 체질`, `밸류에이션`, `성장`, `운영 효율`, `이익 품질`, `주주환원`, `심리` | 17 (표시 라벨) |

- FE 표시용 세분류가 BE에 존재하지 않음 → FE가 17개 라벨을 **하드코딩으로 독자 유지**.
- 예: BE에서 id 60~73은 모두 `fundamental` 한 묶음이나, FE는 `재무 체질`/`밸류에이션`/`성장`/`운영 효율`/`이익 품질`/`주주환원` 6개로 쪼갬.
- **리스크**: 신규 지표 추가 시 BE 대분류만 정하면 FE 세분류 매핑은 수동 결정 필요. 단일 소스가 없어 누락 시 FE에서 미분류로 빠질 수 있음(`categoryOrder` 배열에 없는 category면 렌더 누락).

### 3. description — FE 부재 ⚠️

- BE `INDICATOR_CATALOG` 각 항목은 `description` 보유 (관제실 지표 설명·`_INDICATOR_NAME_TO_DESC`에 사용).
- FE `CatalogIndicator` 인터페이스(`AddIndicatorSheet.tsx:8-13`)는 `{ id, name, category, freq }`만 — **description 필드 없음**.
- 결과: 지표 추가 시트(`AddIndicatorSheet`)에서 사용자에게 지표 설명을 보여줄 수 없음. 메모리 기록상 "관제실 지표 설명(description 73개)"은 BE/관제실 경로에서만 노출되고 추가 시트에는 미반영.

---

## description 품질

BE `INDICATOR_CATALOG` 64개 전수 점검:

| 점검 | 결과 |
|------|------|
| 빈 description (`''` 또는 키 부재) | **0건** |
| 과소 description (< 10자) | **0건** |
| 최단 description | `한국 중소형 성장주 시장 지수.` (id 14, 16자) 등 — 전부 10자 이상 |

- 품질 양호. 모든 항목이 "정의 + 투자적 의미" 2요소를 갖춘 1~2문장 구조.
- 참고: `get_indicator_description()`(`prompt_builder.py:351`)는 접두사 매칭을 지원 → LLM 모드의 `"EPS 추이 (META)"` 형태도 description 회수 가능.

---

## keyword_rules 고아

### BE `KEYWORD_RULES` (`indicator_matcher.py:12-154`) — 고아 **없음** ✅

11개 규칙이 참조하는 지표 name 11종 전부 `INDICATOR_CATALOG`에 존재:

```
외국인 순매수 추이, 미국 기준금리 (Fed Funds Rate), 미국 10년 국채 금리,
VIX (공포지수), 원/달러 환율, RSI (14일), 뉴스 센티먼트, EPS 추이,
기관 순매수 추이, S&P 500, KOSPI 지수  → 11/11 카탈로그 매칭
```

`match_indicators_for_llm()`(`indicator_matcher.py:271-329`)는 PK 우선 → 키워드 fallback 시 `_find_in_catalog(name)`으로 최종 검증하므로 환각 지표 차단됨.

### 구조적 취약점 ⚠️

1. **name 기반 연결 (id 아님)**: `KEYWORD_RULES`의 indicator는 `indicator_db_id`가 없고 `name` 문자열로만 카탈로그와 연결. 카탈로그에서 지표 이름을 바꾸면 `_find_in_catalog` 매칭이 조용히 깨져 `catalog_entry=None`으로 떨어짐(고아화). 현재는 일치하지만 리네임 회귀에 무방비.

2. **`indicator_type` vs `category` 필드명 불일치**: `KEYWORD_RULES`의 dict는 `indicator_type`을 쓰고 카탈로그는 `category`를 씀. 같은 의미인데 키 이름이 달라 후처리에서 혼선 가능.

3. **BE 11규칙 ↔ FE 30규칙 비미러**: FE `KEYWORD_INDICATOR_MAP`(`AddIndicatorSheet.tsx:109-139`)은 30개 규칙·id 기반으로 BE보다 훨씬 풍부(원자재·암호화폐·밸류에이션·운영효율 등 커버). BE는 11규칙·name 기반. **두 키워드 추천 엔진이 독립적으로 진화 중** → 같은 전제에 대해 BE/FE 추천 결과가 달라질 수 있음. 메모리 `feedback_llm_indicator_hallucination` 원칙(카탈로그 외 생성 금지)은 지켜지나, 추천 커버리지 자체가 불일치.

---

## data_params 형식

### 1. `data_source='metrics'` (id 60~73, 14개) — ✅ 정합

`metric_code`가 `seed_metric_definitions.py`의 34종 정의와 전건 일치:

```
gross_margin, net_margin, roic, current_ratio, interest_coverage,
net_debt_to_ebitda, fcf_margin, ev_to_ebitda, fcf_yield,
operating_income_growth, dso, asset_turnover, accruals_ratio,
net_shareholder_yield  → 14/14 seed 존재
```

### 2. `data_source='fmp'` + `metric` (펀더멘털) — ⚠️ #14 방어됨, 일부 비표준

| id | metric | 처리 | 판정 |
|----|--------|------|------|
| 50 PER | `earningsYieldTTM` + `inverse:True` | `audit_note`로 `PER=1/earningsYield` 명시 | ✅ #14 회귀 방지 |
| 52 ROE | `returnOnEquityTTM` + `scale_multiplier:100` | 0~1 → % 변환 명시 | ✅ |
| 53 ROA | `returnOnAssetsTTM` + `scale_multiplier:100` | 동일 패턴 | ✅ |
| 58 매출성장률 | `growthRevenue` + `endpoint:financial-growth` + `scale_multiplier:100` | FMP 표준 필드 아님 명시 | ✅ note 있음 (단 별도 fetch 분기 필요) |

→ 과거 common-bugs #14(FMP key-metrics 필드명 불일치) 경험이 `audit_note`로 잘 박제되어 회귀 방지됨.

### 3. `data_source='fmp'` + `metric` (수급) — 🔴 데이터 공급자 불일치 의심

| id | metric | 우려 |
|----|--------|------|
| 1 외국인 순매수 추이 | `foreign_net_buy` | FMP(미국 시장 중심, `/stable/*`)는 **한국 외국인 수급 데이터를 제공하지 않음**. FMP 표준 엔드포인트에 대응 필드 없음 |
| 2 기관 순매수 추이 | `institutional_net_buy` | 동일. FMP의 institutional ownership(`/institutional-ownership/`)은 보유 잔량이지 일별 순매수 흐름이 아님 |

→ 두 지표는 `data_source='fmp'`로 선언됐으나 FMP가 실제 일별 순매수 시계열을 주는지 **검증 필요**(P0 후보). 한국 수급은 통상 KRX/타 공급자 영역. fetch 단계에서 빈 데이터로 조용히 실패할 가능성.

### 4. `data_source='fmp'` + `symbol` (지수/원자재/환율) — ⚠️ 심볼 표기 검증 필요

| 구분 | 예시 symbol | 비고 |
|------|------------|------|
| 미국 지수 | `^GSPC`, `^IXIC`, `^DJI`, `^VIX` | 캐럿(`^`) 표기 — FMP `/stable` index 심볼 형식 확인 필요 |
| 해외 지수 | `^KS11`(KOSPI), `^KQ11`(코스닥), `^N225`, `^HSI` | FMP Starter Plan에서 비미국 지수 커버리지 제한 가능 |
| 환율 | `USDKRW`(id 9) | FMP forex 심볼 표기(`USDKRW` vs `KRW=X`) 확인 필요 |
| 달러 인덱스 | `DX-Y.NYB`(id 39) | Yahoo 표기 형식 — FMP 형식과 상이할 가능성 |
| 원자재 | `GCUSD`, `CLUSD`, `BTCUSD` 등 | FMP commodity/crypto 표기와 정합 추정(추가 확인 권장) |

→ 본 감사는 **정적 코드 대조**만 수행. 위 심볼들이 FMP `/stable` 응답에서 실제 데이터를 반환하는지는 런타임 검증 영역(코드 수정 금지 범위 밖).

### 5. `data_source='fmp'` + `indicator` (기술적, id 10·40~47) — ⚠️ 형식 불완전

```python
{'indicator': 'RSI', 'period': 14}          # id 10
{'indicator': 'MACD', 'fast':12,'slow':26,'signal':9}  # id 40
{'indicator': 'SMA', 'period': 50}          # id 45
```

- **`symbol` 키가 없음**: 어떤 종목/지수에 대한 RSI인지 `data_params`만으로 결정 불가. fetch 시점에 가설의 target symbol을 외부에서 주입하는 설계로 보임 → params 단독으로는 self-contained 하지 않음. 다른 지표(지수·펀더멘털)는 params에 대상이 박혀 있어 형식이 비대칭.

### 6. `data_source='fred'` + `series_id` (거시) — ✅ 표준

`FEDFUNDS`, `DGS10`, `DGS2`, `MORTGAGE30US`, `UNRATE`, `PAYEMS`, `GDPC1`, `INDPRO`, `CPIAUCSL`, `HOUST`, `DEXUSEU` — 전부 FRED 표준 시리즈 ID 표기. 정합.

---

## 권고 (우선순위순, 모두 후속 작업 제안 — 본 보고서는 미수정)

| 우선 | 항목 | 제안 |
|------|------|------|
| 🔴 P0 | id 1·2 FMP 수급 지표 | `foreign_net_buy`/`institutional_net_buy`의 FMP 실데이터 반환 여부 런타임 검증. 미지원 시 data_source 교체 또는 지표 비활성화 |
| 🟡 P1 | 기술적 지표 `symbol` 부재 | fetch 주입 경로가 견고한지 확인, 또는 params 스키마에 target 슬롯 명시 |
| 🟡 P1 | FE description 부재 | BE description을 FE로 전달(API 노출 or codegen)하여 추가 시트에서 설명 표시 |
| 🟢 P2 | category/키워드 룰 단일 소스화 | BE 카탈로그에 FE 세분류 라벨 + 키워드 메타 추가 → FE는 미러 대신 소비. 3중 드리프트 제거 |
| 🟢 P2 | `KEYWORD_RULES` name→id 전환 | name 문자열 연결을 `indicator_db_id`로 교체해 리네임 회귀 방지. `indicator_type`→`category` 키명 통일 |

---

*본 감사는 정적 코드 대조 기반이며 코드를 수정하지 않았습니다. FMP 심볼 유효성·수급 데이터 반환 여부 등 런타임 검증 항목은 별도 작업이 필요합니다.*
