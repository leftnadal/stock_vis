# 지표 카탈로그 동기화 감사 보고서

- 감사일: 2026-05-17
- 감사자: nightly_auto_system / claude
- 모드: 읽기 전용 (코드 수정 없음)
- 대상 파일:
  - BE 정의: `thesis/services/prompt_builder.py:14-310`
  - BE 후처리: `thesis/services/llm_postprocess.py:33-95`
  - BE 매칭/키워드 룰: `thesis/services/indicator_matcher.py:12-154`
  - BE metrics seed: `metrics/management/commands/seed_metric_definitions.py`
  - FE 표시: `frontend/components/thesis/AddIndicatorSheet.tsx:15-139`
  - 테스트 가드: `tests/unit/thesis/test_llm_builder.py:144-149`

---

## 요약 (동기화 상태)

| 검사 영역 | 상태 | 비고 |
|----------|------|------|
| 카탈로그 ID 집합 (BE↔FE) | ✅ 일치 | BE 64개 / FE 64개, ID 완전 일치 |
| 카탈로그 이름 (BE↔FE) | ✅ 일치 | 64개 모두 정확히 동일 문자열 |
| 카탈로그 빈도 (INDICATOR_FREQUENCY ↔ freq) | ✅ 일치 | 64개 모두 동일 분류 (일/주/월/분기) |
| 카탈로그 카테고리 분류 체계 | ⚠️ 불일치 | BE는 5개 대분류 / FE는 17개 서브분류 — 별개 체계 |
| `description` 필드 | ⚠️ FE 결손 | BE 64/64 보유 (모두 ≥25자) / FE는 필드 자체 부재 |
| `description` 품질 | ✅ 양호 | 빈/짧은(<10자) description 0건 |
| `metric_code` 참조 (`data_source='metrics'`) | ✅ 모두 시드 존재 | id 60~73 → seed_metric_definitions.py 모두 정의됨 |
| `keyword_rules` 고아 (룰 → 카탈로그) | ✅ 없음 | indicator_matcher.py 모든 name이 카탈로그에 존재 |
| `keyword_rules` 커버리지 균형 (BE↔FE) | ⚠️ 큰 불균형 | BE 11룰 / FE 28룰 — BE에 17개 룰 누락 |
| 동일 키워드 매핑 ID 일치 (BE↔FE) | ⚠️ 불일치 | 금리/환율 등 동일 키워드도 매핑 ID 다름 |
| `data_params` 함정 명시 (`audit_note`) | ✅ 명시됨 | #14 회귀 방지 노트 4건 모두 주석 보존 |
| FMP `key-metrics-ttm` 필드명 정합성 | ✅ 정합 | `peRatioTTM` 직접 사용 없음, `earningsYieldTTM` + inverse |
| `match_by_gemini` 환각 위험 | ⚠️ 잔존 경로 | LLM 빌더에서는 차단됐으나 `match_indicators_for_premise()` 경로 #L266 여전히 호출 |

종합: **핵심 동기화(ID/이름/빈도/metric_code)는 정상**이나 FE description 부재, 카테고리 분류 체계 분기, BE/FE 키워드 룰 큰 격차가 미해결 부채로 남아 있다.

---

## BE ↔ FE 불일치 목록

### 1. ID/이름/빈도 동기화

BE `INDICATOR_CATALOG` 항목 64개, FE `INDICATOR_CATALOG` 항목 64개로 **ID 집합 ≡ 완전 일치**.

BE ID 집합:
```
{1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16,
 20, 21, 22, 23, 24, 25, 26, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39,
 40, 41, 42, 43, 44, 45, 46, 47,
 50, 51, 52, 53, 54, 55, 56, 57, 58,
 60, 61, 62, 63, 64, 65, 66, 67, 68, 69, 70, 71, 72, 73}
```

FE ID 집합도 동일. BE에만 있거나 FE에만 있는 항목 **0건**.

각 ID의 `name` 문자열도 1:1 동일 (예: id:50 `'PER (주가수익비율)'`, id:67 `'EV/EBITDA'` 등).

빈도 분류(`INDICATOR_FREQUENCY` vs `freq`)도 항목별로 완전 일치. 예시 검증:
- id:6 Fed Funds Rate → BE `주간` / FE `주간` ✓
- id:7 10년 국채 → BE `일간` / FE `일간` ✓
- id:34 GDP → BE `분기` / FE `분기` ✓
- id:35 산업생산지수 → BE `월간` / FE `월간` ✓

### 2. 카테고리 분류 체계 분기 (⚠️ 구조적 불일치)

BE `category` 필드는 5개 대분류만 사용:
```
market_data, macro, technical, fundamental, sentiment
```

FE `category` 필드는 17개 서브분류 사용:
```
수급, 주요 지수, 원자재, 암호화폐,
금리, 환율/변동성, 고용/성장, 물가/주택,
기술적, 펀더멘털, 재무 체질, 밸류에이션, 성장,
운영 효율, 이익 품질, 주주환원, 심리
```

→ BE의 한 `market_data`가 FE에서 {수급, 주요 지수, 원자재, 암호화폐} 4개로 쪼개짐. **두 분류 체계가 서로 독립적으로 작성**되어 있어, 새 지표 추가 시 양쪽에서 다른 결정을 내릴 위험. 양쪽 카테고리 매핑이 명시된 테이블(예: `BE_CATEGORY → FE_SUBCATEGORY`)은 어디에도 없음.

### 3. 메타데이터 풍부도 차이

| 필드 | BE | FE |
|------|----|----|
| `id` | ✅ | ✅ |
| `name` | ✅ | ✅ |
| `category` | ✅ (대분류) | ✅ (서브분류, 다른 체계) |
| `freq` / 빈도 | ✅ (별도 dict) | ✅ (인라인) |
| `data_source` | ✅ | ❌ |
| `data_params` | ✅ | ❌ |
| `support_direction` | ✅ | ❌ |
| `description` | ✅ (64/64) | ❌ (필드 없음) |

→ FE는 단순 선택 UI용 미러라 OK일 수도 있으나, **`description`이 빠진 것은 UX 결함**. 사용자가 지표를 고를 때 의미를 알 수 없음. 향후 백엔드 API(`/api/v1/thesis/indicator_catalog/`)로 통일하면 자연스럽게 해결되는 부채.

---

## description 품질

대상: BE `INDICATOR_CATALOG` 64개 (`prompt_builder.py:16-309`).

### 빈/짧은 description

| 검사 | 결과 |
|------|------|
| `description` 키 자체 누락 | 0건 |
| 빈 문자열 description | 0건 |
| 10자 미만 description | 0건 |
| 평균 길이 | 약 30~45자 |
| 최단 길이 | id:14 `'한국 중소형 성장주 시장 지수.'` (16자) |
| 최장 길이 | id:51 `'주가를 주당순자산으로 나눈 값. 자산 대비 주가 할인/할증 수준.'` (37자) |

**모든 64개 항목의 description이 품질 기준(≥10자, 의미 있는 문장)을 통과**.

### 일관성 (스타일)

- 대부분 "지표 정의 + 해석" 두 문장 구성으로 일관성 양호
- `negative` support_direction 지표는 "급등 시 부정적" 류 해석 명시 (id:33 CPI, id:54 부채비율 등) ✓
- 단, FE에 표시 안 됨 → 사용자가 카탈로그 시트(`AddIndicatorSheet.tsx`)에서 description 못 봄. 이는 품질이 아닌 **노출 누락** 이슈.

### `_INDICATOR_NAME_TO_DESC` 접두사 매칭 로직

`prompt_builder.py:351-361 get_indicator_description()`는 `'EPS 추이 (META)'`처럼 LLM이 심볼을 덧붙이는 케이스를 접두사 매칭으로 처리. ✓ 양호.

---

## keyword_rules 고아 (indicator_matcher.py vs INDICATOR_CATALOG)

### 1. 룰 → 카탈로그 매핑 검증 (고아 검사)

`indicator_matcher.py:12-154 KEYWORD_RULES`의 모든 `indicators[].name`이 카탈로그에 존재하는지:

| 룰 키워드 | indicators name | 카탈로그 매칭 | 결과 |
|----------|------------------|-------------|------|
| 외국인/외인 | `'외국인 순매수 추이'` | id:1 | ✅ |
| 금리/연준/FOMC | `'미국 기준금리 (Fed Funds Rate)'` | id:6 | ✅ |
| 금리/연준/FOMC | `'미국 10년 국채 금리'` | id:7 | ✅ |
| VIX/공포 | `'VIX (공포지수)'` | id:8 | ✅ |
| 환율/달러 | `'원/달러 환율'` | id:9 | ✅ |
| RSI/MACD/기술적 | `'RSI (14일)'` | id:10 | ✅ |
| 센티먼트/뉴스 | `'뉴스 센티먼트'` | id:11 | ✅ |
| 실적/EPS | `'EPS 추이'` | id:5 | ✅ |
| 기관/연기금 | `'기관 순매수 추이'` | id:2 | ✅ |
| S&P/나스닥/다우 | `'S&P 500'` | id:3 | ✅ |
| 코스피 | `'KOSPI 지수'` | id:4 | ✅ |
| 선거/정치/정책 | `'VIX (공포지수)'`, `'KOSPI 지수'` | id:8, id:4 | ✅ |

**고아 0건.** 모든 룰의 name이 카탈로그에 존재.

### 2. 동기화 위험 — 이름 기반 참조 (⚠️ 구조적 부채)

`indicator_matcher.KEYWORD_RULES`는 카탈로그 `id`를 참조하지 않고 **이름 문자열 + 자체 data_source/data_params/support_direction 메타데이터**를 다시 적어 둠 (예: id:1의 `'fmp'/'foreign_net_buy'/'positive'`가 두 파일에 중복 정의).

```
prompt_builder.py:16-19  → {'id': 1, 'name': '외국인 순매수 추이', 'data_source':'fmp', 'data_params':{'metric':'foreign_net_buy'}, 'support_direction':'positive'}
indicator_matcher.py:15-21 → {'name':'외국인 순매수 추이', 'data_source':'fmp', 'data_params':{'metric':'foreign_net_buy'}, 'support_direction':'positive'}
```

→ 카탈로그에서 `'외국인 순매수 추이'` 이름을 바꾸면 `indicator_matcher.py`는 침묵 깨짐. 같은 메타가 두 곳에 적힌 것도 표류(drift) 가능성. 개선 방향: `KEYWORD_RULES`를 `{keywords, indicator_ids}` 형태로 정규화하고 카탈로그를 단일 진실 소스로 사용.

### 3. 카탈로그 커버리지 (룰이 다루지 못하는 지표)

BE `KEYWORD_RULES`가 매핑하는 카탈로그 ID = `{1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11}` → 11개.

**나머지 53개 지표(id:12~16, 20~26, 30~73)는 BE 키워드 룰로 매칭 불가**. 사용자가 "비트코인" 입력해도 `match_by_keywords()`는 빈 결과 반환 → `match_by_gemini` fallback 경로로 폴백 (#L266) → **카탈로그에 없는 환각 지표 생성 위험**.

참고: `match_indicators_for_llm()` (#L271)은 명시적으로 gemini fallback을 제외(#L307 코멘트)했으나, **`match_indicators_for_premise()`(#L257)는 여전히 fallback 호출**. View/Service에서 어느 함수가 쓰이는지 확인 필요 (이번 감사 범위 밖).

### 4. BE ↔ FE 룰 셋 비교

| 차원 | BE `KEYWORD_RULES` | FE `KEYWORD_INDICATOR_MAP` |
|------|---------------------|------------------------------|
| 룰 개수 | 11 | 28 |
| 커버 카탈로그 ID 수 | 11개 | 50+ 개 |
| 펀더멘털 (PER/PBR/ROE/ROA/배당/FCF) | ❌ 없음 | ✅ 5개 룰 |
| 원자재 (유가/금/구리/가스) | ❌ 없음 | ✅ 4개 룰 |
| 암호화폐 | ❌ 없음 | ✅ 1개 룰 |
| 거시(CPI/고용/GDP/주택) | ❌ 없음 | ✅ 4개 룰 |
| 섹터(반도체/중국/일본/광고) | ❌ 없음 | ✅ 4개 룰 |
| 동일 키워드 매핑 ID 일치 | — | — |

동일 키워드에 매핑 ID 차이:

| 키워드 | BE | FE | 차이 |
|--------|------|------|------|
| 금리 | [6, 7] | [6, 7, 30] | FE는 2년 국채(id:30) 추가 |
| 환율 | [9] | [9, 39] | FE는 DXY(id:39) 추가 |
| RSI/MACD | [10] | [10, 40] | FE는 MACD(id:40) 추가 |
| S&P | [3] | [3, 12] | FE는 NASDAQ(id:12) 추가 |

→ FE 룰이 일관되게 더 풍부. **BE 매칭 결과와 FE 추천 결과가 동일 키워드에 대해 다른 지표 목록을 보여줌**.

### 5. `reason` 텍스트 불일치

동일 룰의 `reason`/`reason` 필드도 BE와 FE에서 별개로 작성됨. 예시:

| 키워드 | BE reason | FE reason |
|--------|-----------|-----------|
| 외국인 | "외국인 투자자의 매매 동향은 시장 방향을 선행하는 핵심 지표입니다." | "외국인 수급 변화 직접 추적" |
| VIX | "VIX는 시장의 공포와 불확실성을 나타내는 대표적 지표입니다." | "시장 불확실성/공포 수준 측정" |
| 금리 | "기준금리 변동은 유동성과 할인율에 영향을 미칩니다." | "금리 변동이 유동성과 할인율에 영향" |

→ 본질은 동일하지만 표현이 다름. 향후 통일 시 둘 중 하나를 진실 소스로 정해야 함.

---

## data_params 형식

### 1. data_source별 분포

| `data_source` | 항목 수 | data_params 형식 |
|---------------|--------|------------------|
| `fmp` (가격/지수/원자재/암호화폐) | 25 | `{'symbol': '^GSPC'}` 등 |
| `fmp` (수급/펀더멘털 메트릭) | 11 | `{'metric': 'foreign_net_buy'}` / `{'metric': 'pbRatioTTM'}` 등 |
| `fmp` (기술적 지표) | 9 | `{'indicator': 'RSI', 'period': 14}` 등 |
| `fred` | 11 | `{'series_id': 'FEDFUNDS'}` 등 |
| `metrics` (재무 체질) | 14 | `{'metric_code': 'gross_margin'}` 등 |
| `news_sentiment` | 1 | `{}` |
| **합계** | **64** | — |

### 2. FMP `key-metrics-ttm` 함정 처리 (✅ 양호)

**audit_note로 명시된 함정 처리 4건** (`prompt_builder.py`):

| id | name | data_params | 함정 |
|----|------|-------------|------|
| 50 | PER | `{'metric': 'earningsYieldTTM', 'inverse': True, 'audit_note': 'PER = 1 / earningsYieldTTM (#14 회귀 방지)'}` | FMP에 `peRatioTTM` 필드 없음 → 역수로 계산 |
| 52 | ROE | `{'metric': 'returnOnEquityTTM', 'scale_multiplier': 100, 'audit_note': 'ratio 0~1 → % (#14 회귀 방지)'}` | 0~1 스케일 → ×100 |
| 53 | ROA | `{'metric': 'returnOnAssetsTTM', 'scale_multiplier': 100, 'audit_note': 'ratio 0~1 → % (#14 동일 패턴)'}` | 0~1 스케일 → ×100 |
| 58 | 매출성장률 (YoY) | `{'metric': 'growthRevenue', 'endpoint': 'financial-growth', 'scale_multiplier': 100, 'audit_note': 'FMP /financial-growth/ growthRevenue (#14 표준 필드 아님)'}` | `key-metrics-ttm`이 아닌 별도 endpoint |

→ `common-bugs.md #14` 회귀 방지가 카탈로그 메타에 잘 박혀 있음. **포맷 표준 준수.**

cross-check: `serverless/services/enhanced_screener_service.py:75,295,313`에서도 동일하게 `earningsYieldTTM` 역수로 PER 계산 — 정합.

### 3. data_source='metrics' metric_code 참조 정합성

`prompt_builder.py`의 id 60~73이 사용하는 `metric_code` 14개가 `seed_metric_definitions.py`에 존재하는지:

| id | metric_code | seed 존재 | line |
|----|-------------|----------|------|
| 60 | gross_margin | ✅ | 8 |
| 61 | net_margin | ✅ | 36 |
| 62 | roic | ✅ | 64 |
| 63 | current_ratio | ✅ | 157 |
| 64 | interest_coverage | ✅ | 171 |
| 65 | net_debt_to_ebitda | ✅ | 185 |
| 66 | fcf_margin | ✅ | 229 |
| 67 | ev_to_ebitda | ✅ | 479 |
| 68 | fcf_yield | ✅ | 493 |
| 69 | operating_income_growth | ✅ | 95 |
| 70 | dso | ✅ | 316 |
| 71 | asset_turnover | ✅ | 387 |
| 72 | accruals_ratio | ✅ | 271 |
| 73 | net_shareholder_yield | ✅ | 448 |

**모두 정합. 미정의 metric_code 0건.**

### 4. `endpoint` 키 사용 일관성

`endpoint` 키는 id:58 (`growthRevenue`)에서 처음 등장. `fmp` data_source에서 endpoint를 명시한 항목은 이 1건뿐. 다른 fmp 펀더멘털 항목들(id:50~57)은 endpoint를 생략(=암묵적으로 `key-metrics-ttm`).

→ 데이터 fetcher가 `endpoint` 키 부재 시 어떤 default를 쓰는지는 이 감사 파일 범위 밖. 만약 default가 `key-metrics-ttm`이라면, **`peRatioTTM`도 없는데 `pbRatioTTM`(id:51)·`debtToEquityTTM`(id:54)·`freeCashFlowTTM`(id:55) 등은 같은 엔드포인트에서 옴**을 fetcher가 보장해야 한다.

검증 권고: `portfolio/metrics/definitions/metrics.py`의 `fmp_endpoint` 패턴과 thesis 쪽이 별도 path를 갖는지 cross-check 필요.

### 5. `inverse` / `scale_multiplier` 처리 책임

`prompt_builder.py`는 메타로만 표시. 실제 변환은 데이터 fetcher 책임. fetcher가 이 키들을 인식하지 못하면 **PER이 0.03 같은 값으로 저장될 위험** (#14 재발). 이번 감사 범위 밖이지만 cross-check가 필요한 회귀 포인트.

---

## 부록 — 권장 조치 (우선순위)

1. **(중) BE keyword_rules 확장** — FE의 28개 룰과 동등하게 17개 룰 추가, 동일 키워드 매핑 ID 통일. 단일 진실 소스(JSON 파일 또는 DB) 분리 권장.
2. **(중) FE에 description 노출** — BE에서 카탈로그 API를 만들고 FE는 fetch. 64개 description이 사용자에게 보이지 않는 UX 결함 해소.
3. **(중) `match_indicators_for_premise()`의 gemini fallback 검토** — LLM 빌더 경로에서는 막혔지만 다른 경로에서 환각 가능성 잔존 (`indicator_matcher.py:266`).
4. **(저) 카테고리 분류 체계 통일** — BE 5분류와 FE 17분류 사이의 매핑 테이블을 명시하거나 한쪽으로 통합.
5. **(저) keyword_rules의 id 참조화** — name 문자열 대신 `id: 1` 참조로 바꿔 카탈로그를 단일 진실 소스로.
6. **(정보) fetcher 측 cross-check 별도 감사 필요** — `inverse`/`scale_multiplier`/`endpoint` 키를 실제로 처리하는지, default endpoint가 무엇인지 확인.
