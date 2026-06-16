# 지표 카탈로그 동기화 감사 보고서

> 작성일: 2026-06-16 · 읽기 전용 감사 (코드 수정 없음)
> 대상 파일:
> - BE 정의/프롬프트: `thesis/services/prompt_builder.py`
> - BE 후처리: `thesis/services/llm_postprocess.py`
> - BE 키워드 매칭: `thesis/services/indicator_matcher.py`
> - FE 표시: `frontend/components/thesis/AddIndicatorSheet.tsx`

---

## 요약 (동기화 상태)

| 검사 항목 | 결과 | 심각도 |
|----------|------|--------|
| **지표 항목 (id/name/freq)** | ✅ BE 64개 ↔ FE 64개 **완전 일치** | — |
| **카테고리 체계** | ⚠️ BE 5분류 vs FE 17분류 (단일 소스 아님, 표시용) | P2 |
| **description 품질** | ✅ BE 64개 전부 양호 (빈/10자 미만 없음) | — |
| **FE description 미러** | ⚠️ FE에 description 필드 자체 없음 (BE 전용) | P3 |
| **keyword_rules (BE↔FE)** | 🔴 BE 11규칙 vs FE 28규칙 **대규모 불일치** | P1 |
| **keyword_rules 고아** | ✅ BE/FE 모두 카탈로그에 존재하는 지표만 참조 | — |
| **keyword_rules indicator_type 메타** | ⚠️ BE id 5 'EPS 추이' = `market_data`인데 카탈로그 = `fundamental` | P2 |
| **match_by_gemini 환각 경로** | ⚠️ `match_indicators_for_premise`에 잔존 (LLM 경로는 차단됨) | P2 |
| **data_params 형식** | ⚠️ 한국 데이터(KOSPI/코스닥/USDKRW/외국인·기관 순매수) FMP 가용성 의문 | P1 |

**총평**: 핵심 자산인 **지표 카탈로그(id·name·freq)는 BE↔FE 64개가 완전히 동기화**되어 있어 건전하다. 가장 큰 리스크는 (1) **keyword_rules의 BE/FE 이중 진화**(BE 11개 / FE 28개)와 (2) **일부 지표의 data_params가 실제 데이터 제공자(FMP)와 정합하지 않을 가능성**이다.

---

## BE ↔ FE 불일치 목록

### 1. 지표 항목 자체 — 불일치 **없음** ✅

BE `INDICATOR_CATALOG`(prompt_builder.py:14-310)와 FE `INDICATOR_CATALOG`(AddIndicatorSheet.tsx:15-91) 모두 **동일한 64개 id**를 보유. 누락/추가 항목 없음.

확인한 id 집합 (양쪽 동일, 64개):
```
1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,
20,21,22,23,24,25,26,30,31,32,33,34,35,36,37,38,39,40,
41,42,43,44,45,46,47,50,51,52,53,54,55,56,57,58,
60,61,62,63,64,65,66,67,68,69,70,71,72,73
```
- `name` 필드: 64개 모두 문자열 일치 (예: id 50 = 'PER (주가수익비율)' 양쪽 동일)
- `freq` 필드: BE `INDICATOR_FREQUENCY`(prompt_builder.py:321-342)와 FE `freq` 속성이 64개 모두 일치
  - 교차검증한 경계 케이스: id 6 주간 / id 7 일간 / id 37 주간 / id 34 분기 / id 33 월간 → 전부 일치

### 2. 카테고리 체계 불일치 ⚠️ (P2)

| | 분류 수 | 값 |
|--|--------|----|
| BE (`CATEGORY_LABELS`, prompt_builder.py:312-318) | **5개** | market_data, macro, technical, fundamental, sentiment |
| FE (`category` 인라인, AddIndicatorSheet.tsx) | **17개** | 수급, 주요 지수, 원자재, 암호화폐, 금리, 환율/변동성, 고용/성장, 물가/주택, 기술적, 펀더멘털, 재무 체질, 밸류에이션, 성장, 운영 효율, 이익 품질, 주주환원, 심리 |

- BE는 거친 5분류(LLM 프롬프트 그룹핑용), FE는 17개 세분 분류(UI 그룹핑용).
- **기능 영향 없음** — 매칭 키는 `id`이지 category가 아니므로 동작에는 무해.
- 다만 "단일 소스(single source of truth)"가 아니어서, 향후 지표 추가 시 양쪽 category를 따로 관리해야 하는 유지보수 부담 존재.

### 3. FE에 description 미러 부재 ⚠️ (P3)

- BE 항목은 `description` 필드 보유(64개 전부). `get_indicator_description()`(prompt_builder.py:351)으로 조회.
- FE `CatalogIndicator` 인터페이스(AddIndicatorSheet.tsx:8-13)는 `{ id, name, category, freq }`만 — **description 없음**.
- 사용자 메모리의 "지표 카탈로그 3곳 분산 미러, 동시 업데이트 필수" 원칙과 연결: FE는 description을 표시하지 않으므로 현재는 의도된 설계로 보이나, FE에서 지표 툴팁/설명을 추가하려면 별도 동기화 필요.

---

## description 품질

| 검사 | 결과 |
|------|------|
| 빈 description | **0건** |
| 10자 미만 description | **0건** |
| 전체 항목 수 | 64개 |

- BE 64개 항목 모두 한 문장(약 25~45자) 수준의 설명을 보유. 가장 짧은 것도 'KOSPI 지수'(id 4) = "한국 유가증권시장 전체 종목 시가총액 가중 지수." (24자)로 기준 충족.
- 품질 양호. 추가 조치 불필요.
- (참고) FE에는 description 필드가 없어 품질 검사 대상에서 제외.

---

## keyword_rules 고아

### 1. BE ↔ FE keyword 규칙 대규모 불일치 🔴 (P1)

| | 위치 | 규칙 수 | 매칭 방식 |
|--|------|--------|----------|
| BE | `KEYWORD_RULES` (indicator_matcher.py:12-154) | **11개** | **name 문자열** 매칭 (취약) |
| FE | `KEYWORD_INDICATOR_MAP` (AddIndicatorSheet.tsx:109-139) | **28개** | **indicator id** 매칭 (견고) |

- 두 테이블이 **독립적으로 진화**했다. FE가 훨씬 풍부(유가/금/구리/암호화폐/밸류에이션/재무건전성/배당/회전율/이익품질/물가/고용/GDP/주택/반도체/중국/일본/광고 등 커버), BE는 초기 11개 규칙에 머물러 있음.
- 결과: 동일한 전제 텍스트라도 **BE 자동 매칭(`match_by_keywords`)과 FE 추천 결과가 크게 달라짐**.
  - 예: "유가 상승" 전제 → FE는 id 21(WTI) 추천하지만, BE `KEYWORD_RULES`에는 유가 규칙 자체가 없음.
  - 예: "배당/FCF" → FE는 id 55/56/66/68/73 추천, BE는 해당 규칙 없음.
- **권장**: keyword 규칙을 단일 소스(BE 또는 공유 contract)로 통합하고, BE 매칭을 name 문자열 → id 기반으로 전환.

### 2. 고아 규칙 — **없음** ✅

- **BE `KEYWORD_RULES`**: 참조하는 지표 이름 11종(외국인 순매수 추이, 미국 기준금리, 미국 10년 국채 금리, VIX, 원/달러 환율, RSI(14일), 뉴스 센티먼트, EPS 추이, 기관 순매수 추이, S&P 500, KOSPI 지수) → **전부 카탈로그에 존재** (`_find_in_catalog`로 검증되는 경로).
- **FE `KEYWORD_INDICATOR_MAP`**: `indicatorIds`로 참조하는 모든 id가 카탈로그 64개 집합 안에 존재 → 고아 id 없음.

### 3. BE name 문자열 매칭의 구조적 취약성 ⚠️ (P2)

- BE `KEYWORD_RULES`는 `indicator_db_id`가 아닌 **`name` 문자열**로 카탈로그를 참조(indicator_matcher.py:332-338 `_find_in_catalog`).
- 카탈로그에서 지표 이름이 한 글자라도 바뀌면(예: 'RSI (14일)' → 'RSI(14일)') 매칭이 조용히 실패하여 `catalog_entry`가 `None`이 되고, 카탈로그 메타데이터(audit_note 등)가 유실된 raw dict가 사용됨. 현재는 일치하나 회귀 취약점.

### 4. indicator_type 메타데이터 불일치 ⚠️ (P2)

- BE `KEYWORD_RULES`의 'EPS 추이'(indicator_matcher.py:90-99)는 `'indicator_type': 'market_data'`로 지정.
- 그러나 카탈로그(prompt_builder.py:190-193)에서 EPS(id 5)의 `category`는 **`fundamental`**.
- 키워드 룰에서 직접 생성하는 dict의 `indicator_type`이 카탈로그 `category`와 어긋난다. 저장/표시 시 카테고리가 다르게 찍힐 수 있음.

### 5. match_by_gemini 환각 경로 잔존 ⚠️ (P2)

- `match_indicators_for_llm`(indicator_matcher.py:271-329)은 의도적으로 `match_by_gemini` fallback을 **제외**(307줄 주석: "카탈로그에 없는 환각 지표 생성하므로 제외") — 사용자 메모리 `feedback_llm_indicator_hallucination`과 정합.
- 그러나 `match_indicators_for_premise`(indicator_matcher.py:257-268)는 키워드 매칭 실패 시 **여전히 `match_by_gemini`를 호출**한다.
  - 이 경로로 들어오면 카탈로그에 없는 임의 지표(name/data_source/data_params 자유 생성)가 반환될 수 있어, "카탈로그 외 지표 생성 금지" 정책의 사각지대.
  - 현재 어느 호출자가 `match_indicators_for_premise`를 사용하는지 추가 확인 권장(LLM 빌더는 `_for_llm` 경로 사용).

---

## data_params 형식

### 1. data_source별 키 스키마 (BE 카탈로그)

| data_source | 필수 키 | 예시 | 비고 |
|-------------|---------|------|------|
| `fmp` (지수/원자재/암호) | `symbol` | `{'symbol': '^GSPC'}` | 티커 직접 |
| `fmp` (수급) | `metric` | `{'metric': 'foreign_net_buy'}` | 커스텀 메트릭 |
| `fmp` (기술적) | `indicator`, `period`(+옵션) | `{'indicator': 'RSI', 'period': 14}` | TA 엔드포인트 |
| `fmp` (펀더멘털 TTM) | `metric`(+변환 플래그) | `{'metric': 'earningsYieldTTM', 'inverse': True}` | #14 변환 동반 |
| `fred` | `series_id` | `{'series_id': 'FEDFUNDS'}` | FRED 시리즈 |
| `metrics` | `metric_code` | `{'metric_code': 'gross_margin'}` | 내부 metrics 시스템 |
| `news_sentiment` | (없음) | `{}` | 파라미터 불요 |

### 2. #14 회귀 방지 변환 플래그 — 양호 ✅

FMP Key Metrics 필드명 함정(common-bugs #14)에 대한 방어가 카탈로그에 명시적으로 박혀 있음:

| id | 지표 | data_params | 방어 |
|----|------|-------------|------|
| 50 | PER | `{'metric': 'earningsYieldTTM', 'inverse': True}` | PER = 1 / earningsYield |
| 52 | ROE | `{'metric': 'returnOnEquityTTM', 'scale_multiplier': 100}` | 0~1 → % |
| 53 | ROA | `{'metric': 'returnOnAssetsTTM', 'scale_multiplier': 100}` | 0~1 → % |
| 58 | 매출성장률 | `{'metric': 'growthRevenue', 'endpoint': 'financial-growth', 'scale_multiplier': 100}` | 표준 필드 아님 + % 변환 |

→ `inverse`/`scale_multiplier`/`endpoint`/`audit_note` 플래그가 카탈로그 정의에 함께 들어 있어, 소비자(데이터 fetcher)가 이를 해석한다는 전제. **fetcher 측에서 이 플래그를 실제로 읽는지** 별도 확인 권장(이번 감사 범위 밖).

### 3. 실제 제공자 가용성 의문 ⚠️ (P1)

형식은 일관되나, **FMP가 해당 데이터를 실제로 제공하는지** 의심되는 항목:

| id | 지표 | data_params | 우려 |
|----|------|-------------|------|
| 1 | 외국인 순매수 추이 | `{'metric': 'foreign_net_buy'}` | FMP는 미국 중심 — 한국식 외국인 순매수 데이터 비표준 메트릭 |
| 2 | 기관 순매수 추이 | `{'metric': 'institutional_net_buy'}` | 동일 우려 |
| 4 | KOSPI 지수 | `{'symbol': '^KS11'}` | FMP 한국 지수 커버리지 확인 필요 |
| 14 | 코스닥 지수 | `{'symbol': '^KQ11'}` | 동일 |
| 9 | 원/달러 환율 | `{'symbol': 'USDKRW'}` | FMP forex 심볼 표기(`USDKRW` vs `USD/KRW`) 확인 필요 |

- `foreign_net_buy`/`institutional_net_buy`는 표준 FMP 엔드포인트 메트릭이 아닌 **커스텀 키**로 보임 — 실제 fetch 로직에서 별도 매핑/소스가 없으면 데이터 공백 발생.
- 사용자 메모리(common-bugs #23): `.` 포함 심볼은 FMP 프리미엄 402 위험 → id 39 `DX-Y.NYB`는 `.` 포함 심볼이라 **402/제외 대상**일 수 있음.

### 4. KEYWORD_RULES ↔ 카탈로그 data_params 정합 — 일치 ✅

BE `KEYWORD_RULES`가 들고 있는 `data_params`(예: '외국인 순매수 추이' = `{'metric': 'foreign_net_buy'}`)는 카탈로그 동일 지표의 data_params와 일치. 중복 정의이지만 값은 어긋나지 않음. (단, 중복 정의 자체가 향후 drift 소스이므로 단일 소스화 권장.)

---

## 권장 조치 (우선순위)

| 우선 | 항목 | 조치 |
|------|------|------|
| **P1** | keyword_rules BE/FE 이중 진화 | 단일 소스(contract/공유 테이블)로 통합, BE 매칭을 id 기반으로 전환 |
| **P1** | 한국/커스텀 메트릭 data_params 가용성 | id 1/2/4/14/9/39 실제 fetcher 동작 검증 (별도 데이터 소스 매핑 여부) |
| **P2** | match_by_gemini 환각 경로 | `match_indicators_for_premise`의 gemini fallback 호출자 점검 |
| **P2** | BE name 문자열 매칭 취약성 | `KEYWORD_RULES`를 indicator_db_id 참조로 전환 |
| **P2** | EPS indicator_type 메타 불일치 | `market_data` → `fundamental` 정정 |
| **P2** | #14 변환 플래그 소비 검증 | fetcher가 inverse/scale_multiplier/endpoint를 읽는지 확인 |
| **P3** | 카테고리/description 단일 소스화 | BE category(5) ↔ FE category(17) 매핑 문서화 |

---

*본 보고서는 읽기 전용 감사로, 코드 변경을 수행하지 않았습니다.*
