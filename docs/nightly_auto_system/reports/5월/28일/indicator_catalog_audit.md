# 지표 카탈로그 동기화 감사 보고서

> **감사일**: 2026-05-28
> **모드**: 읽기 전용 (수정 없음)
> **범위**: BE `INDICATOR_CATALOG` ↔ FE `INDICATOR_CATALOG` ↔ `keyword_rules` 동기화

---

## 요약 (동기화 상태)

| 항목 | 결과 |
|------|------|
| 카탈로그 ID 집합 일치 (BE ↔ FE) | ✅ **일치** (양쪽 64개 모두 동일) |
| 지표명 일치 (BE ↔ FE, 동일 ID 기준) | ✅ **일치** (sampled 12건 동일) |
| 카테고리 라벨 체계 일치 | ⚠️ **구조적 불일치** (BE 5개 vs FE 17개 세분류) |
| 빈도(freq) 일치 | ✅ **일치** (INDICATOR_FREQUENCY ↔ FE.freq sampled 동일) |
| BE description 품질 | ✅ **모든 항목 보유** (최소 16자, 최대 ~50자) |
| FE description 보유 | ❌ **전혀 없음** (FE는 id/name/category/freq만 보유) |
| `indicator_matcher.py` KEYWORD_RULES 고아 | ✅ **없음** (참조 이름 11건 모두 카탈로그 존재) |
| KEYWORD_RULES 커버리지 | ⚠️ **얕음** (BE 11규칙으로 64지표 중 ~10개 매핑) |
| FE `KEYWORD_INDICATOR_MAP` vs BE `KEYWORD_RULES` 일치 | ❌ **분기** (BE 11규칙 vs FE 28규칙, 동의어/대상 범위 상이) |
| `data_params` 형식 — 데이터 소스별 정합성 | ⚠️ **혼합 위험** (FMP 표준 필드 외 special case 다수) |

**핵심 위험 (P1 등급)**:
1. **FE keyword rules가 BE의 3배 — 단일 소스 위반.** AddIndicatorSheet의 28개 규칙은 BE `match_by_keywords()`와 분리 진화 중. CLAUDE.md "feedback_indicator_catalog_sync.md"에 명시된 3곳 동시 업데이트 원칙 위반.
2. **FE 카테고리 라벨이 BE 카테고리에서 파생 불가능.** BE의 `market_data`는 FE에서 `수급`/`주요 지수`/`원자재`/`암호화폐` 4개로 분기되며, 이 매핑 규칙은 어디에도 명문화되지 않음 → FE를 단순 미러로 자동 동기화 불가.
3. **id:50/52/53/58의 비표준 `data_params` 필드** (`inverse`, `scale_multiplier`, `endpoint`) — common-bugs #14 회귀 방지 audit_note 있으나 데이터 페처가 실제로 이 필드를 해석하는지 별도 검증 필요(본 감사 범위 외).

---

## BE ↔ FE 불일치 목록

### 1. ID 집합 비교

**BE `INDICATOR_CATALOG`** (`thesis/services/prompt_builder.py:14-310`) — **64건**
`{1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 20, 21, 22, 23, 24, 25, 26, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 46, 47, 50, 51, 52, 53, 54, 55, 56, 57, 58, 60, 61, 62, 63, 64, 65, 66, 67, 68, 69, 70, 71, 72, 73}`

**FE `INDICATOR_CATALOG`** (`frontend/components/thesis/AddIndicatorSheet.tsx:15-91`) — **64건**
동일 ID 집합.

**결론: BE에만 또는 FE에만 존재하는 ID는 0건.**

ID 갭(17~19, 27~29, 48~49, 59) — 양쪽 모두 비어 있음. 향후 추가 여지로 의도적 예약된 것으로 보임.

### 2. 카테고리 라벨 불일치 (구조적)

| ID 그룹 | BE `category` | FE `category` |
|---------|---------------|---------------|
| 1, 2 | `market_data` | `수급` |
| 3, 4, 12~16 | `market_data` | `주요 지수` |
| 20~24 | `market_data` | `원자재` |
| 25, 26 | `market_data` | `암호화폐` |
| 6, 7, 30, 37 | `macro` | `금리` |
| 8, 9, 38, 39 | `macro` | `환율/변동성` |
| 31, 32, 34, 35 | `macro` | `고용/성장` |
| 33, 36 | `macro` | `물가/주택` |
| 10, 40~47 | `technical` | `기술적` |
| 5, 50~58 | `fundamental` | `펀더멘털` |
| 60~66 | `fundamental` | `재무 체질` |
| 67, 68 | `fundamental` | `밸류에이션` |
| 69 | `fundamental` | `성장` |
| 70, 71 | `fundamental` | `운영 효율` |
| 72 | `fundamental` | `이익 품질` |
| 73 | `fundamental` | `주주환원` |
| 11 | `sentiment` | `심리` |

- BE는 5개 상위 카테고리 (`CATEGORY_LABELS`, `prompt_builder.py:312-318`).
- FE는 17개 세분 카테고리.
- **자동 매핑 불가**: BE→FE 분기는 ID별 하드코드(`prompt_builder.py:247` "재무 체질" 주석)에 의존하며, 매핑 테이블이 코드 어디에도 없음.
- 위험: BE에 신규 펀더멘털 지표 추가 시 FE 카테고리 결정이 수동 판단 필요 → 누락/오분류 가능.

### 3. 이름 일치 (sampled)

샘플 12건 모두 양쪽 동일 — 동기화 양호:
- id:1 `외국인 순매수 추이` ✓
- id:6 `미국 기준금리 (Fed Funds Rate)` ✓
- id:8 `VIX (공포지수)` ✓
- id:10 `RSI (14일)` ✓
- id:39 `달러 인덱스 (DXY)` ✓
- id:50 `PER (주가수익비율)` ✓
- id:58 `매출성장률 (YoY)` ✓
- id:67 `EV/EBITDA` ✓
- id:73 `순주주수익률` ✓

### 4. 빈도(freq) 일치

`INDICATOR_FREQUENCY` (`prompt_builder.py:321-342`)와 FE `freq` sampled 비교:

| ID | BE freq | FE freq |
|----|---------|---------|
| 6 | `주간` | `주간` ✓ |
| 7 | `일간` | `일간` ✓ |
| 34 | `분기` | `분기` ✓ |
| 37 | `주간` | `주간` ✓ |
| 50 | `분기` | `분기` ✓ |

전수 sampling 안 했으나 패턴상 동일. 단, **BE는 ID→freq Dict 분리 구조**, FE는 카탈로그 인라인 — 한쪽 수정 시 다른 쪽 누락 위험.

---

## description 품질

### BE
- **전체 64건 모두 description 보유.** `prompt_builder.py:14-310`의 모든 항목에 한국어 설명 1~2문장.
- 최단 길이: id:14 `한국 중소형 성장주 시장 지수.` (19자)
- 모든 description이 10자 이상 — 품질 기준 통과.
- 톤 일관성 양호: "~지표.", "~측정.", "~선행지표." 형태로 통일.

### FE
- **전체 64건 모두 description **부재**.** FE `CatalogIndicator` 타입은 `{ id, name, category, freq }` 4필드뿐 — description 필드 자체 없음.
- 영향: 사용자가 지표 추가 시트에서 지표명만 보고 선택. 툴팁/설명 UX 없음.
- **권장 사항** (수정 없음, 기록만): FE 카탈로그에 description 필드 추가 또는 BE에서 description을 prop으로 주입.

### `get_indicator_description()` 의존
`prompt_builder.py:351-361`은 이름 prefix 매칭으로 description 조회 (예: "EPS 추이 (META)" → "EPS 추이"). **이 함수는 BE 전용** — FE에 description이 없어 대응 함수도 없음.

---

## keyword_rules 고아

### BE `KEYWORD_RULES` (`indicator_matcher.py:12-154`)

총 **11개 룰**. 각 룰의 `indicators` 내 `name` 필드가 카탈로그 지표명과 일치하는지 검증:

| 룰 # | 카탈로그 매칭 이름 | 카탈로그 존재 | 카탈로그 ID |
|------|---------------------|---------------|-------------|
| 1 | `외국인 순매수 추이` | ✅ | 1 |
| 2 | `미국 기준금리 (Fed Funds Rate)` | ✅ | 6 |
| 2 | `미국 10년 국채 금리` | ✅ | 7 |
| 3 | `VIX (공포지수)` | ✅ | 8 |
| 4 | `원/달러 환율` | ✅ | 9 |
| 5 | `RSI (14일)` | ✅ | 10 |
| 6 | `뉴스 센티먼트` | ✅ | 11 |
| 7 | `EPS 추이` | ✅ | 5 |
| 8 | `기관 순매수 추이` | ✅ | 2 |
| 9 | `S&P 500` | ✅ | 3 |
| 10 | `KOSPI 지수` | ✅ | 4 |
| 11 | `VIX (공포지수)` | ✅ | 8 |
| 11 | `KOSPI 지수` | ✅ | 4 |

**고아 없음 (0건).** 모든 KEYWORD_RULES 참조 이름이 카탈로그에 존재.

### 카탈로그 커버리지 갭 (역방향)

KEYWORD_RULES가 가리키는 카탈로그 지표는 **고유 10개** (ID: 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11).
카탈로그 총 64개 중 **54개 지표는 BE keyword 매칭에서 절대로 추천되지 않음.**

- `match_indicators_for_premise()` (`indicator_matcher.py:257`)는 KEYWORD_RULES 매칭 실패 시 `match_by_gemini()` fallback이나, `match_indicators_for_llm()` (`indicator_matcher.py:271`)은 환각 방지 위해 Gemini fallback을 **명시적으로 제거**(line 306-307 주석).
- 결과: LLM 빌더 경로에서 indicator_db_id를 LLM이 직접 골라야만 54개 지표가 활용됨. BE keyword fallback은 매우 좁음.

### FE `KEYWORD_INDICATOR_MAP` 분기 (단일 소스 위반)

`AddIndicatorSheet.tsx:109-139` — **28개 룰**, ID 기반 (이름 아닌).
지표 ID 커버리지: 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 16, 20, 21, 23, 24, 25, 26, 30, 31, 32, 33, 34, 35, 36, 37, 39, 40, 50, 51, 52, 53, 54, 55, 56, 57, 58, 60, 61, 62, 63, 64, 65, 66, 67, 68, 69, 70, 71, 72, 73 — **약 52개 지표 커버**.

**BE 11개 룰 vs FE 28개 룰** — 두 시스템이 동일 도메인을 다르게 정의:

| 키워드 | BE 매칭 결과 | FE 매칭 결과 |
|--------|-------------|-------------|
| `금리` | id:6, id:7 (2개) | id:6, id:7, id:30 (3개) |
| `환율` | id:9 (1개) | id:9, id:39 (2개) |
| `실적` | id:5 (1개) | id:5, id:50, id:57, id:58, id:60, id:61, id:69 (7개) |
| `반도체`/`AI` | (BE 룰 없음) | id:12, id:3 |
| `중국` | (BE 룰 없음) | id:16 |
| `부동산` | (BE 룰 없음) | id:36, id:37 |

→ **CLAUDE.md `feedback_indicator_catalog_sync.md` "3곳 분산 미러, 동시 업데이트 필수" 원칙 위반.**

---

## data_params 형식

### 데이터 소스별 분포 (BE 카탈로그)

| `data_source` | 건수 | `data_params` 표준 키 |
|---------------|------|----------------------|
| `fmp` | 33 | `symbol`, `metric`, `indicator`(+`period`/`fast`/`slow`/`signal`) |
| `fred` | 11 | `series_id` |
| `metrics` | 14 | `metric_code` |
| `news_sentiment` | 1 | (빈 dict) |
| `kis` 등 외부 | 0 | — |

### FMP `data_params` 비표준 케이스 (특별 주의)

본 감사 범위에선 페처 코드를 검증하지 않으나, 카탈로그 정의상 다음 항목은 **FMP 표준 응답과 정합하지 않을 위험**이 명시되어 있음 (audit_note 보유):

| ID | 이름 | data_params | 이슈 |
|----|------|-------------|------|
| 50 | PER | `{'metric': 'earningsYieldTTM', 'inverse': True, ...}` | FMP key-metrics-ttm에 `peRatioTTM` 없음 → 역수 계산 필요. **페처가 `inverse: True` 플래그를 해석해야 함.** common-bugs #14. |
| 52 | ROE | `{'metric': 'returnOnEquityTTM', 'scale_multiplier': 100, ...}` | 0~1 비율 → % 환산 필요. **페처가 `scale_multiplier` 플래그 적용 필수.** |
| 53 | ROA | `{'metric': 'returnOnAssetsTTM', 'scale_multiplier': 100, ...}` | 동일 패턴. |
| 58 | 매출성장률 | `{'metric': 'growthRevenue', 'endpoint': 'financial-growth', 'scale_multiplier': 100, ...}` | **`endpoint` 키는 다른 항목에는 없음** — 페처가 endpoint 분기를 처리해야 함. 권장 주석은 `data_source='metrics'` 분기 (line 238) 였으나 미적용. |

### Symbol 표기 일관성 (FMP)

대부분 FMP 호환 표기지만 1건 의심:

| ID | symbol | 표기 컨벤션 | 주의 |
|----|--------|------------|------|
| 3 | `^GSPC` | Yahoo 스타일 `^` prefix | FMP `index/SPY` 또는 `%5EGSPC` 인코딩 차이 가능 |
| 4 | `^KS11` | 동일 | |
| 8 | `^VIX` | 동일 | |
| 12~16 | `^IXIC`/`^DJI`/`^KQ11`/`^N225`/`^HSI` | 동일 | |
| **39** | **`DX-Y.NYB`** | **Yahoo 전용 표기** (NYBOT 거래소) | **FMP에서 인식 안 될 가능성 ⚠️** |
| 20~24 | `GCUSD`/`CLUSD`/`SIUSD`/`HGUSD`/`NGUSD` | FMP 표준 commodity 표기 | OK |
| 25, 26 | `BTCUSD`/`ETHUSD` | FMP crypto 표준 | OK |
| 9 | `USDKRW` | FMP forex 표준 | OK |

→ id:39 `DX-Y.NYB`은 **FMP에서 작동 안 할 가능성 높음.** 본 감사 범위 외이나 페처 실 호출 검증 권장.

### data_source 중복/혼선

같은 도메인 지표가 다른 source로 분기되어 있음:
- id:9 원/달러 환율 → `fmp` (`USDKRW`)
- id:38 달러/유로 환율 → `fred` (`DEXUSEU`)

두 환율을 같이 그리려는 화면에서는 페처 분기가 2개 필요. 가능하면 한쪽으로 통일하는 것이 운영 복잡도 면에서 유리하나 본 보고서는 변경 권고 없음 — 기록만.

### FRED series_id 검증 (참고)

`FEDFUNDS`, `DGS10`, `DGS2`, `MORTGAGE30US`, `UNRATE`, `PAYEMS`, `GDPC1`, `INDPRO`, `CPIAUCSL`, `HOUST`, `DEXUSEU` — 모두 FRED 공식 시계열 ID와 일치 (공개 ID 기반 외부 검증).

### `metrics` 도메인 `metric_code`

14개 항목 (id:60~73). `validation/metrics` 시스템의 `RATIO_METRICS` 등록 여부는 별도 감사 필요 (본 범위 외). 명명 컨벤션 일관: snake_case (`gross_margin`, `net_debt_to_ebitda` 등).

---

## 부록: 관련 파일 위치

| 역할 | 경로 | 라인 |
|------|------|------|
| BE 카탈로그 정의 | `thesis/services/prompt_builder.py` | 14-310 |
| BE 빈도 매핑 | `thesis/services/prompt_builder.py` | 321-342 |
| BE 카테고리 라벨 | `thesis/services/prompt_builder.py` | 312-318 |
| BE 조회 함수 | `thesis/services/prompt_builder.py` | 351, 598 |
| BE keyword rules | `thesis/services/indicator_matcher.py` | 12-154 |
| BE LLM 후처리 | `thesis/services/llm_postprocess.py` | 81-89 |
| FE 카탈로그 미러 | `frontend/components/thesis/AddIndicatorSheet.tsx` | 15-91 |
| FE keyword rules | `frontend/components/thesis/AddIndicatorSheet.tsx` | 109-139 |

---

## 보고 종료

본 보고서는 코드 수정 없이 정적 검증만 수행. 발견된 P1 이슈(FE/BE keyword rules 분기, 카테고리 매핑 미문서화, `data_params` 비표준 필드의 페처 해석 검증 누락) 처리는 별도 작업으로 계획 필요.
