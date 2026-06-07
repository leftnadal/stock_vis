# 지표 카탈로그 동기화 감사 보고서

> 생성일: 2026-06-07 | 모드: 읽기 전용 (코드 미수정) | 대상: Thesis Control 지표 카탈로그

## 검사 대상 파일

| 역할 | 파일 | 핵심 구조 |
|------|------|----------|
| BE 정의 (1차 소스) | `thesis/services/prompt_builder.py` | `INDICATOR_CATALOG` (64개) + `INDICATOR_FREQUENCY` + `CATEGORY_LABELS` |
| BE 후처리 | `thesis/services/llm_postprocess.py` | `get_indicator_by_id` 검증으로 환각 id → None 교정 |
| BE 매칭 | `thesis/services/indicator_matcher.py` | `KEYWORD_RULES` (11룰, name 기반) |
| FE 미러 (빌더) | `frontend/components/thesis/AddIndicatorSheet.tsx` | `INDICATOR_CATALOG` (64개) + `KEYWORD_INDICATOR_MAP` (26룰) → **`/thesis/new`** |
| FE props (지표 페이지) | `frontend/components/thesis/indicators/AddIndicatorSheet.tsx` | 카탈로그 없음, 서버 추천 props만 → **`/thesis/[id]/indicators`** |

---

## 요약 (동기화 상태)

| 검사 항목 | 상태 | 비고 |
|-----------|------|------|
| 1. BE ↔ FE 지표 항목 (id/name/freq) | 🟢 **완전 동기화** | 64개 id 집합 일치, name·freq 전수 일치 |
| 2. description 품질 (BE 카탈로그) | 🟢 양호 | 빈 항목 0건, <10자 0건 |
| 3. keyword_rules 고아 | 🟢 고아 없음 | KEYWORD_RULES의 11개 name 전부 카탈로그 존재 |
| 3-b. BE/FE 키워드 룰 커버리지 | 🟡 **격차** | BE 11룰 vs FE 26룰 — 같은 전제에 추천 결과 상이 가능 |
| 3-c. KEYWORD_RULES 메타 불일치 | 🟡 **1건** | `EPS 추이` indicator_type=`market_data` vs 카탈로그 category=`fundamental` |
| 4. data_params 형식 | 🟢 일관 / 🟡 중복 | FMP 함정 4건은 audit_note로 박제 완료. 단 4중 미러로 DRY 위반 |

**총평**: 지표 카탈로그 본체(id/name/freq/description)의 BE↔FE 동기화는 **매우 깨끗**하다. 위험은 카탈로그 본체가 아니라 **주변 미러(keyword 룰)의 분기**와 **단일 소스 부재(4중 정의)**에 집중되어 있다. 즉시 깨지는 버그는 없으나 향후 drift 시 silent 실패 가능성이 있는 구조적 부채다.

---

## 1. BE ↔ FE 불일치 목록

### 1-1. 지표 항목 (id/name) — 불일치 없음 🟢

양쪽 `INDICATOR_CATALOG`의 id 집합이 정확히 일치한다 (각 64개).

```
공통 id (64): 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16 20 21 22 23 24 25 26
              30 31 32 33 34 35 36 37 38 39 40 41 42 43 44 45 46 47
              50 51 52 53 54 55 56 57 58 60 61 62 63 64 65 66 67 68 69 70 71 72 73
BE에만 있음: (없음)
FE에만 있음: (없음)
```

- 모든 id의 `name` 문자열이 BE/FE 동일 (예: id 1 `외국인 순매수 추이`, id 73 `순주주수익률`).
- 업데이트 주기도 일치: BE `INDICATOR_FREQUENCY` ↔ FE `freq` 필드 전수 대조 결과 불일치 0건 (id 34 `분기`, id 6/37 `주간` 포함 모두 일치).

### 1-2. category 분류 체계 차이 — 표시용, 기능 영향 없음 🟢(주의)

| | category 개수 | 값 |
|--|--|--|
| BE (`category` 필드) | 5개 대분류 | `market_data` / `macro` / `technical` / `fundamental` / `sentiment` |
| FE (`category` 필드) | 17개 소분류 | `수급` `주요 지수` `원자재` `암호화폐` `금리` `환율/변동성` `고용/성장` `물가/주택` `기술적` `펀더멘털` `재무 체질` `밸류에이션` `성장` `운영 효율` `이익 품질` `주주환원` `심리` |

- BE는 LLM 프롬프트 그룹화용(`CATEGORY_LABELS`), FE는 UI 섹션 표시용으로 의도적으로 세분화 — **기능적 불일치 아님**.
- 다만 BE category 필드는 단일 소스가 아니며 FE가 자체 분류를 들고 있어, 신규 지표 추가 시 양쪽 분류를 별도 관리해야 한다.

### 1-3. description 미러 부재 — 의도적 🟢

- BE 카탈로그는 64개 전부 `description` 보유.
- FE 미러본(`components/thesis/AddIndicatorSheet.tsx`)은 `id/name/category/freq`만 보유, **description 필드 없음**.
- FE는 description 대신 keyword 룰의 `reason`(전제 관련 추천 사유)을 표시 → 의도된 설계로 판단. 단 지표 설명 툴팁이 필요해지면 별도 fetch 필요.

---

## 2. description 품질

대상: BE `INDICATOR_CATALOG` 64개 (FE는 description 미보유).

| 검사 | 결과 |
|------|------|
| 빈 description (`''` 또는 키 누락) | **0건** 🟢 |
| 너무 짧은 description (<10자) | **0건** 🟢 |

- 전 항목이 1~2문장의 충실한 설명을 보유. 최단 사례도 충분: id 14 `한국 중소형 성장주 시장 지수.` (16자), id 4 `한국 유가증권시장 전체 종목 시가총액 가중 지수.`
- `get_indicator_description()`은 접두사 매칭(`"EPS 추이 (META)"` → `"EPS 추이"`)을 지원하므로 LLM 모드의 심볼 접미사도 안전하게 description을 회수한다.

**조치 불필요.**

---

## 3. keyword_rules 고아

### 3-1. KEYWORD_RULES name → 카탈로그 매핑 — 고아 없음 🟢

`indicator_matcher.py`의 `KEYWORD_RULES`는 **id가 아닌 `name` 문자열로** 카탈로그를 참조한다 (`_find_in_catalog(name)`). 11개 룰이 참조하는 모든 name이 카탈로그에 존재:

| KEYWORD_RULES name | 카탈로그 id | data_params 일치 |
|--------------------|------------|------------------|
| 외국인 순매수 추이 | 1 | ✅ `{metric: foreign_net_buy}` |
| 기관 순매수 추이 | 2 | ✅ `{metric: institutional_net_buy}` |
| S&P 500 | 3 | ✅ `{symbol: ^GSPC}` |
| KOSPI 지수 | 4 | ✅ `{symbol: ^KS11}` |
| EPS 추이 | 5 | ✅ `{metric: eps}` |
| 미국 기준금리 (Fed Funds Rate) | 6 | ✅ `{series_id: FEDFUNDS}` |
| 미국 10년 국채 금리 | 7 | ✅ `{series_id: DGS10}` |
| VIX (공포지수) | 8 | ✅ `{symbol: ^VIX}` |
| 원/달러 환율 | 9 | ✅ `{symbol: USDKRW}` |
| RSI (14일) | 10 | ✅ `{indicator: RSI, period: 14}` |
| 뉴스 센티먼트 | 11 | ✅ `{}` |

**고아 규칙 0건.** 단 아래 구조적 위험 존재.

### 3-2. ⚠️ P1 — name 문자열 결합의 silent 실패 위험

- `KEYWORD_RULES`는 `indicator_db_id`를 갖지 않고 name 문자열로만 카탈로그와 연결된다.
- `match_indicators_for_llm()`의 2순위 fallback에서 `_find_in_catalog(ind['name'])`가 `None`을 반환하면 **카탈로그가 아닌 룰 자체 dict(`catalog_entry or ind`)를 사용** → 카탈로그 id/description 없이 진행된다.
- 현재는 name이 전부 일치하므로 무해하나, 카탈로그 name을 한 글자라도 수정하면(예: `RSI (14일)` → `RSI (14)`) 예외 없이 조용히 룰 dict로 폴백된다. **방어 로그 없음.**

### 3-3. 🟡 P1 — KEYWORD_RULES ↔ 카탈로그 메타 필드 불일치

두 가지 키/값 불일치:

1. **키 이름 불일치**: KEYWORD_RULES는 `indicator_type` 키, 카탈로그는 `category` 키 (같은 의미, 다른 이름).
2. **값 불일치 (실질 1건)**:

   | name | KEYWORD_RULES `indicator_type` | 카탈로그 `category` | 판정 |
   |------|-------------------------------|---------------------|------|
   | EPS 추이 | `market_data` | `fundamental` | ❌ **불일치** |
   | 기관 순매수 추이 | `market_data` | `market_data` | ✅ |
   | S&P 500 / KOSPI | `market_data` | `market_data` | ✅ |
   | VIX / 금리 / 환율 | `macro` | `macro` | ✅ |
   | RSI | `technical` | `technical` | ✅ |
   | 뉴스 센티먼트 | `sentiment` | `sentiment` | ✅ |

   → `EPS 추이`는 펀더멘털 지표인데 KEYWORD_RULES에서 `market_data`로 분류. 카탈로그 폴백이 일어나면 분류가 뒤집힌다.

### 3-4. 🟡 P1 — BE/FE 키워드 룰 시스템 이중화 (커버리지 격차)

두 키워드 매핑이 **완전히 독립된 별도 시스템**으로 존재한다:

| | 파일 | 룰 수 | 참조 방식 | 누락 영역 |
|--|------|------|----------|----------|
| BE | `indicator_matcher.py` `KEYWORD_RULES` | **11** | name 문자열 | 금/구리/천연가스/암호화폐/주택/고용/GDP/반도체/중국/일본/광고/물가 등 미커버 |
| FE | `AddIndicatorSheet.tsx` `KEYWORD_INDICATOR_MAP` | **26** | id 배열 | (FE가 더 풍부) |

- FE 룰이 BE의 약 2.4배. 같은 전제 텍스트라도 **BE 자동 매칭(서버 추천)과 FE 클라이언트 추천이 서로 다른 지표를 제시**할 수 있다.
- 예: 전제에 `"유가"`/`"구리"`/`"비트코인"`/`"반도체"`가 있으면 FE는 전용 지표를 추천하지만 BE `KEYWORD_RULES`에는 해당 룰이 없어 빈 결과 → Gemini fallback(`match_by_gemini`)으로 빠진다.
- FE `KEYWORD_INDICATOR_MAP`이 참조하는 모든 `indicatorIds`는 카탈로그에 존재함을 확인 (FE 룰 고아 0건).

> 참고: `match_indicators_for_llm()`은 카탈로그 환각을 막기 위해 `match_by_gemini` fallback을 **의도적으로 제외**하고 키워드 룰만 사용한다(주석 명시). 따라서 LLM 빌더 경로에서는 BE 룰 커버리지 부족이 곧 "추천 누락"으로 직결된다.

---

## 4. data_params 형식

### 4-1. FMP 알려진 함정 — 박제 완료 🟢

common-bugs #14 회귀 방지용 `audit_note`가 카탈로그에 명시되어 있어 현재 대응 상태:

| id | name | data_params 처리 | 근거 |
|----|------|-----------------|------|
| 50 | PER | `{metric: earningsYieldTTM, inverse: True}` | FMP에 `peRatioTTM` 미존재 → 역수 |
| 52 | ROE | `{metric: returnOnEquityTTM, scale_multiplier: 100}` | 0~1 스케일 → % 변환 |
| 53 | ROA | `{metric: returnOnAssetsTTM, scale_multiplier: 100}` | 동일 패턴 |
| 58 | 매출성장률 | `{metric: growthRevenue, endpoint: financial-growth, scale_multiplier: 100}` | key-metrics-ttm 표준 필드 아님 |

→ 형식 변환 메타(`inverse`, `scale_multiplier`, `endpoint`)가 data_params에 인라인으로 박혀 있어 데이터 제공자 형식 차이를 흡수한다. **양호.**

### 4-2. data_source × data_params 형식 매트릭스 — 일관 🟢

| data_source | data_params 키 | 사용 지표 |
|-------------|---------------|----------|
| `fmp` (지수/원자재/암호화폐/환율) | `{symbol}` | 3,4,8,9,12~16,20~26,39 |
| `fmp` (수급) | `{metric}` | 1,2 |
| `fmp` (기술적) | `{indicator, period, ...}` | 10,40~47 |
| `fmp` (펀더멘털 TTM) | `{metric, inverse?, scale_multiplier?, endpoint?}` | 5,50~58 |
| `fred` (거시) | `{series_id}` | 6,7,30,31~38 |
| `metrics` (재무 체질) | `{metric_code}` | 60~73 |
| `news_sentiment` | `{}` | 11 |

- 카탈로그 내 형식 규칙이 data_source별로 일관되게 적용됨.

### 4-3. 🟡 P2 — data_params 4중 정의 (DRY 위반)

동일한 지표 메타가 **네 곳에 중복 정의**되어 있다:

1. `prompt_builder.py` `INDICATOR_CATALOG` (1차 소스, data_params 완전판)
2. `indicator_matcher.py` `KEYWORD_RULES` (name + data_source + data_params **재정의**)
3. `frontend/components/thesis/AddIndicatorSheet.tsx` `INDICATOR_CATALOG` (id/name/category/freq)
4. `frontend/components/thesis/AddIndicatorSheet.tsx` `KEYWORD_INDICATOR_MAP` (keyword → id)

- 현재 #2의 data_params는 #1과 값이 동일(3-1 표 참조)하지만, 별도 정의이므로 한쪽만 수정하면 drift가 발생한다.
- 특히 #2(KEYWORD_RULES)는 FMP 함정 대응(`inverse`/`scale_multiplier`)을 **전혀 반영하지 않은 단순 data_params**를 들고 있다. EPS 외 펀더멘털 지표가 KEYWORD_RULES에 추가될 경우 #1의 변환 메타가 누락된 채 사용될 위험.
- CLAUDE.md 메모리에도 기록된 기존 인지 사항(`feedback_indicator_catalog_sync` — "3곳 분산 미러, 동시 업데이트 필수")과 일치하며, 실제로는 **4곳**으로 확인됨.

### 4-4. 🟢 검증 권고 — KEYWORD_RULES `EPS 추이` data_params

- `{metric: eps}` (data_source=`fmp`)는 카탈로그 id 5와 동일하나, FMP `key-metrics-ttm`의 표준 필드 여부는 본 감사 범위(정적 분석)에서 확정 불가. PER/ROE와 동일한 #14 계열 함정일 가능성 있어 실제 API 응답 대조 권고(별도 작업).

---

## 권고 우선순위 (참고 — 본 보고서는 코드 미수정)

| 우선순위 | 항목 | 위치 |
|---------|------|------|
| P1 | `EPS 추이` indicator_type `market_data` → `fundamental` 교정 | `indicator_matcher.py` §3-3 |
| P1 | BE `KEYWORD_RULES`를 name 문자열 → `indicator_db_id` 참조로 전환 (silent 폴백 제거) | `indicator_matcher.py` §3-2 |
| P1 | BE 키워드 룰(11) ↔ FE 룰(26) 커버리지 정렬 또는 단일 소스화 | §3-4 |
| P2 | data_params 4중 정의 → contracts 단일 소스 + codegen 검토 | §4-3 |
| P3 | `EPS 추이` FMP 필드 실측 대조 | §4-4 |

---

## 결론

카탈로그 **본체(64개 지표의 id/name/freq/description)의 BE↔FE 동기화는 결함 없음**. 빈/짧은 description, 고아 keyword 규칙, 누락 지표 모두 0건이다.

실질 리스크는 **카탈로그를 둘러싼 미러 레이어**에 있다:
1. BE/FE가 키워드 룰을 이중으로 들고 있어 추천 결과가 갈릴 수 있음 (§3-4)
2. KEYWORD_RULES가 name 문자열로 느슨하게 연결돼 drift 시 조용히 실패 (§3-2)
3. `EPS 추이`의 분류 메타 1건 불일치 (§3-3)
4. 동일 메타가 4곳 중복 (§4-3)

모두 **즉시 장애를 일으키는 버그는 아니나**, 지표를 추가/수정할 때 4곳을 동시에 손대야 하는 구조적 부채이며, 단일 소스화(contracts 기반 codegen) 시 근본 해소 가능하다.
