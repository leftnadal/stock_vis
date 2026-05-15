# 지표 카탈로그 동기화 감사 보고서

- 감사일: 2026-05-14
- 감사 범위: `thesis/services/prompt_builder.py`, `thesis/services/llm_postprocess.py`, `thesis/services/indicator_matcher.py`, `frontend/components/thesis/AddIndicatorSheet.tsx`
- 정책 근거: CLAUDE.md "지표 카탈로그 BE/FE 동기화" (3곳 분산 미러, 동시 업데이트 필수)
- 모드: 읽기 전용. 코드 수정 없음.

---

## 요약 (동기화 상태)

| 영역 | 결과 |
|---|---|
| BE ↔ FE id/name 동기화 | ✅ 일치 (양쪽 64개, id 1·2·3·4·5·6·7·8·9·10·11·12·13·14·15·16·20·21·22·23·24·25·26·30·31·32·33·34·35·36·37·38·39·40·41·42·43·44·45·46·47·50·51·52·53·54·55·56·57·58·60·61·62·63·64·65·66·67·68·69·70·71·72·73 모두 양쪽에 존재, 이름 문자열 완전 일치) |
| BE ↔ FE 업데이트 주기(freq) | ✅ 64개 모두 일치 (BE `INDICATOR_FREQUENCY` 표 vs FE 인라인 `freq`) |
| BE ↔ FE 카테고리 라벨 | ⚠️ 의도된 분기 (BE 5단계 대분류, FE 17단계 세분류). 깨짐 아님 |
| description 품질 (BE) | ✅ 64개 전부 25~45자, 빈 값/단문(<10자) 없음 |
| `KEYWORD_RULES` (BE) ↔ 카탈로그 | ✅ 참조 이름 11개 모두 카탈로그에 존재 (고아 0). 단 **커버리지 17%** — 53개 지표는 텍스트 fallback 도달 불가 |
| BE `KEYWORD_RULES` ↔ FE `KEYWORD_INDICATOR_MAP` | ⚠️ 두 곳에 독립된 키워드 사전이 공존. 규칙 수 BE 11 < FE 28, 추천 지표 폭이 다름 — **동기화 정책 사각지대** |
| `data_params` 형식 | ⚠️ 4종 특수 필드(`inverse`, `scale_multiplier`, `endpoint`, `audit_note`) 사용 — 실제 fetcher가 이 키들을 해석하는지 본 감사 범위에서는 미확인 (별도 검증 필요) |
| 전체 판정 | 🟡 **부분 일치** — BE/FE 카탈로그 자체는 정합. 그러나 키워드 매핑 이중 소스와 `data_params` 특수 필드 해석 책임이 사각지대로 남음 |

---

## BE ↔ FE 불일치 목록

### id/name 불일치
없음. 모든 64개 항목이 양쪽에 존재하며 `name` 문자열도 글자 단위로 일치.

### freq(업데이트 주기) 불일치
없음. BE `INDICATOR_FREQUENCY` 64개 ↔ FE 인라인 `freq` 64개 모두 일치 확인:
- 일간: 1·2·3·4·12·13·14·15·16·20·21·22·23·24·25·26·8·9·38·39·10·40·41·42·43·44·45·46·47·11·7·30
- 주간: 6·37
- 월간: 31·32·33·35·36
- 분기: 34·5·50·51·52·53·54·55·56·57·58·60·61·62·63·64·65·66·67·68·69·70·71·72·73

### category 라벨 차이 (의도된 분기 — 깨짐 아님)
BE는 `prompt_builder.py:312-318`의 `CATEGORY_LABELS`로 5개 대분류(market_data / macro / technical / fundamental / sentiment)를 사용. FE는 `AddIndicatorSheet.tsx:211-216`의 `categoryOrder`로 17개 세분류(수급 / 주요 지수 / 원자재 / 암호화폐 / 금리 / 환율·변동성 / 고용·성장 / 물가·주택 / 기술적 / 펀더멘털 / 재무 체질 / 밸류에이션 / 성장 / 운영 효율 / 이익 품질 / 주주환원 / 심리)를 사용. BE는 LLM 프롬프트용 그루핑, FE는 UI 표시용 그루핑으로 역할이 다름.

**잠재 리스크**: 새 지표 추가 시 BE 5개 분류 중 하나를 고른 후 FE 17개 분류 중 어디에 넣을지 별도 판단 필요. 매핑 규칙이 코드/문서로 명시돼 있지 않아 휴리스틱에 의존.

### BE에만 있는 메타데이터
다음 필드는 BE 카탈로그에만 있고 FE에는 없음. FE는 UI 표시 목적이라 의도된 부재.
- `data_source` (fmp / fred / metrics / news_sentiment)
- `data_params` (각 지표별 fetch 파라미터)
- `support_direction` (positive / negative)
- `description` (LLM 프롬프트 + 관제실 표시)

---

## description 품질 (BE `INDICATOR_CATALOG`)

### 빈 description
없음.

### 단문(< 10자) description
없음. 모든 64개가 25~45자 범위.

### 표본 검증 (랜덤)
| id | name | description 길이 | 평가 |
|---|---|---|---|
| 1 | 외국인 순매수 추이 | 38자 | ✅ 정보·뉘앙스 충분 |
| 8 | VIX (공포지수) | 27자 | ✅ |
| 23 | 구리 (Copper) | 28자 | ✅ "Dr. Copper" 별칭 포함 |
| 50 | PER | 28자 | ✅ "수익 대비 주가 수준" 명확 |
| 67 | EV/EBITDA | 31자 | ✅ "자본구조 중립적" 차별점 명시 |
| 73 | 순주주수익률 | 33자 | ✅ "배당+자사주-신주" 공식 포함 |

품질 양호. 추가 보완 권고 없음.

### 참고: 활용처
- `prompt_builder.py:347-361` `get_indicator_description()` — 이름 prefix 매칭(예: "EPS 추이 (META)"도 매칭)으로 LLM/관제실에 description 노출
- common-bugs.md #11과 연동된 `audit_note` 필드도 description과 별개로 PER/ROE/ROA/매출성장률 4건에 동봉 (회귀 방지 메모)

---

## keyword_rules 고아 / 동기화 사각지대

### `KEYWORD_RULES` (BE) — 참조 지표 ↔ 카탈로그 매칭
파일: `thesis/services/indicator_matcher.py:12-154`. 11개 규칙에서 참조하는 이름과 카탈로그 id 매핑:

| KEYWORD_RULES 참조명 | 카탈로그 id | 매칭 |
|---|---|---|
| 외국인 순매수 추이 | 1 | ✅ |
| 기관 순매수 추이 | 2 | ✅ |
| 미국 기준금리 (Fed Funds Rate) | 6 | ✅ |
| 미국 10년 국채 금리 | 7 | ✅ |
| VIX (공포지수) | 8 (2회 등장) | ✅ |
| 원/달러 환율 | 9 | ✅ |
| RSI (14일) | 10 | ✅ |
| 뉴스 센티먼트 | 11 | ✅ |
| EPS 추이 | 5 | ✅ |
| S&P 500 | 3 | ✅ |
| KOSPI 지수 | 4 (2회 등장) | ✅ |

→ **고아 규칙 없음**. 모든 참조 이름이 카탈로그에 존재.

### 커버리지 갭 (BE 측)
`KEYWORD_RULES`가 추천 가능한 카탈로그 id는 {1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11}로 **11개 / 64개 = 17%**. 나머지 53개(12·13·14·15·16·20·21·22·23·24·25·26·30·31·32·33·34·35·36·37·38·39·40·41·42·43·44·45·46·47·50·51·52·53·54·55·56·57·58·60~73)는 텍스트 매칭으로 도달 불가.

영향:
- `match_indicators_for_premise()` 1순위가 빈 결과면 2순위 `match_by_gemini()` fallback이 호출되지만, `match_indicators_for_llm()` (LLM 빌더 경로)에서는 환각 방지 목적으로 `match_by_gemini` fallback이 **명시적으로 차단** (`indicator_matcher.py:306-307` 주석 — "match_by_gemini fallback은 카탈로그에 없는 환각 지표를 생성하므로 제외").
- 따라서 LLM이 `indicator_db_id`를 잘못 주거나 누락한 premise는 본 키워드 룰의 11개 안에서만 텍스트 fallback이 동작. 53개 지표는 LLM이 정확히 PK를 넣어야만 추천됨.

### `KEYWORD_RULES` (BE) ↔ `KEYWORD_INDICATOR_MAP` (FE) 이중 소스
파일: FE `AddIndicatorSheet.tsx:109-139` — BE와 **별개의** 키워드 사전 28규칙.

| 항목 | BE `KEYWORD_RULES` | FE `KEYWORD_INDICATOR_MAP` |
|---|---|---|
| 규칙 수 | 11 | 28 |
| 추천 가능 id 수 | 11 (1·2·3·4·5·6·7·8·9·10·11) | ~50개 (예: 1·2·3·4·5·6·7·8·9·10·11·12·15·16·20·21·23·24·25·26·30·31·32·33·34·35·36·37·39·50·51·52·53·54·55·56·57·58·60·61·62·63·64·65·66·67·68·69·70·71·72·73) |
| 키워드 어휘 일관성 | 한국어/영문 혼용 (대문자 보존) | 한국어/영문 모두 소문자 정규화 후 `includes` |
| 매칭 방식 | `text_lower / 원문` 둘 다 검사 (`indicator_matcher.py:165`) | `textLower.includes(keyword.toLowerCase())` 단일 |
| 결과 형식 | indicator 객체(name/data_source/data_params/...) 반환 | id + reason + score만 반환 |

**리스크**:
1. **단일 진실 소스(Single Source of Truth) 부재** — 같은 사용자 입력이라도 BE 빌더(LLM 보강용)와 FE "전제 관련 추천" 칩 영역에서 서로 다른 지표 후보가 표시될 수 있음.
2. **유지보수 비대칭** — FE에 새 키워드 추가해도 BE 텍스트 fallback은 갱신되지 않음. 그 반대도 동일.
3. **언어 정규화 차이** — BE는 "FOMC"가 원문에 있으면 그대로 매칭하지만, FE는 toLowerCase 후 `fomc`로 변환해 비교. 동일 케이스라 결과는 같으나, 향후 keyword 추가 시 혼동 여지.

권고(보고서 차원): KEYWORD 규칙을 contracts/ 또는 공유 JSON으로 옮기고 BE/FE 양쪽에서 빌드 타임에 import 하는 단일 소스 구조 검토.

---

## data_params 형식

### BE 카탈로그에서 사용되는 형식 (data_source별)

| data_source | 표준 키 | 사용 지표 (id) |
|---|---|---|
| `fmp` (메트릭) | `{'metric': '<fmp field>'}` | 1·2·5·50·51·52·53·54·55·56·57·58 |
| `fmp` (심볼) | `{'symbol': '<티커>'}` | 3·4·8·9·12·13·14·15·16·20·21·22·23·24·25·26·39 |
| `fmp` (테크니컬) | `{'indicator': '<TA name>', 'period': N}` 또는 추가 `fast/slow/signal` | 10·40·41·42·43·44·45·46·47 |
| `fred` | `{'series_id': '<FRED 시리즈>'}` | 6·7·30·31·32·33·34·35·36·37·38 |
| `metrics` (자체 시스템) | `{'metric_code': '<snake_case>'}` | 60·61·62·63·64·65·66·67·68·69·70·71·72·73 |
| `news_sentiment` | `{}` | 11 |

### 특수 필드 (회귀 방지 메모와 함께 동봉)

| id | 지표 | 특수 필드 | 의미 / 출처 |
|---|---|---|---|
| 50 | PER | `inverse: True`, `audit_note: 'PER = 1 / earningsYieldTTM (#14 회귀 방지)'` | FMP `key-metrics-ttm`에 `peRatioTTM` 없음 → `earningsYieldTTM`의 역수. common-bugs #14 / audit P0 #11 연동 |
| 52 | ROE | `scale_multiplier: 100`, `audit_note: 'ratio 0~1 → % (#14 회귀 방지)'` | FMP `returnOnEquityTTM`이 0~1 스케일 → ×100 |
| 53 | ROA | `scale_multiplier: 100`, `audit_note: 'ratio 0~1 → % (#14 동일 패턴)'` | 동일 |
| 58 | 매출성장률(YoY) | `endpoint: 'financial-growth'`, `scale_multiplier: 100`, `audit_note: 'FMP /financial-growth/ growthRevenue (#14 표준 필드 아님)'` | `key-metrics-ttm` 아닌 `/financial-growth/` 호출 분기 필요. 권장 마이그레이션은 `data_source='metrics'` (`quarterly_metric_fetcher`의 `revenue_growth_yoy`) |

### FMP 실제 응답과의 정합 메모
- 카탈로그 주석(`prompt_builder.py:194-245`)이 명시한 대로 FMP key-metrics-ttm 표준 필드 이름은 위 4건에서 모두 비표준. common-bugs #14 회귀 방지 차원에서 `audit_note`로 명문화돼 있음.
- 단, 본 감사 범위에서 확인하지 못한 부분:
  - 실제 fetcher 코드가 `inverse`, `scale_multiplier`, `endpoint` 키를 **읽고 처리**하는가?
  - `data_source='metrics'` 14종이 `quarterly_metric_fetcher`의 `metric_code`와 1:1 매칭되는가?
  - `data_source='fmp'` `metric` 모드와 `symbol`/`indicator` 모드를 각각 어느 fetcher가 처리하는가?
- 권고(보고서 차원): 별도 감사 라운드에서 fetcher 측 코드(`metrics/services/quarterly_metric_fetcher.py`, FMP client)와 카탈로그 `data_params` 사이의 **수신측 계약 검증**이 필요. 본 보고서는 카탈로그 송신측 정의만 확인.

### FE 측 data_params 부재
FE 미러는 id/name/category/freq만 보유 — 데이터 fetch는 BE 책임이므로 의도된 설계. 단, FE의 "전제 관련 추천"이 보여주는 지표를 사용자가 선택했을 때 BE가 그 id를 받아 `data_params`를 해석하는 구조라 BE 데이터가 진실의 소스. 이 비대칭은 정상.

---

## 종합 권고 (보고서 차원, 코드 수정 없음)

1. **KEYWORD 단일 소스화 검토** — BE `KEYWORD_RULES`(11규칙)와 FE `KEYWORD_INDICATOR_MAP`(28규칙)의 격차가 사용자 경험 비대칭으로 이어질 수 있음. 향후 PR에서 contracts/ 공유 JSON 또는 BE API로 통합 검토.
2. **카테고리 매핑 명시화** — BE 5분류 ↔ FE 17분류 사이의 매핑 규칙을 sub_claude_md 또는 코드 주석으로 명시하면 신규 지표 추가 시 혼동 감소.
3. **`data_params` 수신측 감사 별도 라운드** — 본 감사는 송신측만 확인. fetcher 측에서 `inverse`/`scale_multiplier`/`endpoint`/`metric_code`를 실제 해석하는지 별도 검증 필요.
4. **현재 동기화 정상** — id/name/freq/description 4축은 양호. 본 보고서 작성 시점 기준으로 BE/FE 카탈로그 본체는 즉시 조치 필요한 깨짐 없음.
