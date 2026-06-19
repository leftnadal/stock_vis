# 지표 카탈로그 동기화 감사 보고서

- **생성일**: 2026-06-19
- **모드**: 읽기 전용 (코드 수정 없음)
- **감사 범위**: `thesis` 앱의 INDICATOR_CATALOG 정의/사용처 4개 파일
- **검사 대상 파일**:
  - BE 정의: `thesis/services/prompt_builder.py` (`INDICATOR_CATALOG`)
  - BE 후처리: `thesis/services/llm_postprocess.py`
  - BE 매칭: `thesis/services/indicator_matcher.py` (`KEYWORD_RULES`)
  - FE 표시: `frontend/components/thesis/AddIndicatorSheet.tsx` (`INDICATOR_CATALOG` 미러 + `KEYWORD_INDICATOR_MAP`)

---

## 요약 (동기화 상태)

| 항목 | 상태 | 비고 |
|------|------|------|
| BE↔FE 카탈로그 ID 집합 | ✅ **완전 일치** | 양쪽 64개, ID·이름·업데이트주기(freq) 100% 일치 |
| description 품질 | ✅ **양호** | 64/64 존재, 빈 값 0, 10자 미만 0 (최단 17자) |
| BE keyword_rules 고아 | ✅ **없음** | 11개 룰 참조 이름 전부 카탈로그 존재 |
| FE keyword_map 고아 | ✅ **없음** | 29개 룰 참조 ID 전부 카탈로그 존재 |
| BE↔FE 카테고리 체계 | ⚠️ **분기** | BE 5개 기능 카테고리 vs FE 17개 표시 카테고리 (드리프트 위험) |
| BE↔FE keyword 엔진 | ⚠️ **심각한 분기** | BE 11룰 vs FE 29룰 — 동일 전제에 서로 다른 추천 결과 |
| keyword_rules 필드 중복 | ⚠️ **드리프트 위험** | BE 룰이 data_source/params/type을 카탈로그 참조 없이 인라인 복제 |
| EPS 룰 indicator_type | ⚠️ **불일치 1건** | 룰=`market_data`, 카탈로그=`fundamental` |
| data_params provider 정합 | ⚠️ **부분 미검증** | #14 4건은 audit_note로 방어됨, 미주석 6건 잔존 |

**총평**: BE↔FE **카탈로그 본체(ID/이름/주기)는 완벽하게 동기화**되어 있고 description 품질도 양호하다. 위험은 카탈로그 본체가 아니라 **(1) 두 개의 독립된 keyword 추천 엔진(BE 11 vs FE 29)** 과 **(2) keyword_rules가 카탈로그를 참조하지 않고 필드를 복제**하는 구조에 집중되어 있다. 모두 정합성 드리프트의 잠재 소스다.

---

## BE ↔ FE 불일치 목록

### 1. 카탈로그 본체 — 불일치 **없음** ✅

- BE(`prompt_builder.py`) ID: `1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,20,21,22,23,24,25,26,30,31,32,33,34,35,36,37,38,39,40,41,42,43,44,45,46,47,50~58,60~73` → **64개**
- FE(`AddIndicatorSheet.tsx`) ID: **동일 64개**
- 이름 대조: 64건 전부 일치 (mismatch 0)
- 업데이트 주기(freq) 대조: BE `INDICATOR_FREQUENCY` ↔ FE `freq` 필드 — 표본 대조 전건 일치 (예: id6 주간, id7 일간, id34 분기, id37 주간)

> BE에만 있거나 FE에만 있는 지표: **없음.**

### 2. 카테고리 체계 분기 ⚠️ (구조적 드리프트 위험)

FE 주석(line 6)은 `INDICATOR_CATALOG 미러 (prompt_builder.py와 동기화)`라고 명시하나, **category 필드는 의도적으로 다른 체계**를 쓴다.

| | BE (`category`) | FE (`category`) |
|--|------|------|
| 체계 | 5개 **기능** 카테고리 | 17개 **표시** 카테고리 |
| 값 | `market_data`, `macro`, `technical`, `fundamental`, `sentiment` | `수급`, `주요 지수`, `원자재`, `암호화폐`, `금리`, `환율/변동성`, `고용/성장`, `물가/주택`, `기술적`, `펀더멘털`, `재무 체질`, `밸류에이션`, `성장`, `운영 효율`, `이익 품질`, `주주환원`, `심리` |

- 예: BE에서 id 60~73은 전부 `fundamental` 단일 카테고리지만, FE는 `재무 체질/밸류에이션/성장/운영 효율/이익 품질/주주환원`으로 6분할.
- **영향**: 기능적 깨짐은 아님(매칭 계약은 id+name). 다만 한쪽에서 카테고리 추가/이동 시 다른 쪽이 자동 추적 불가 → 수동 동기화 부채.

### 3. FE 미러의 필드 축소 ⚠️ (정보성)

FE 미러는 `id / name / category / freq` 4개 필드만 보유한다. BE 카탈로그의 다음 필드는 **FE에 부재**:

- `data_source`, `data_params`, `support_direction`, `description`

→ FE는 화면 표시 전용 축소 미러이므로 정상 설계지만, **description이 FE에 노출되지 않음**(지표 선택 시 사용자에게 설명 없음). `get_indicator_description()`은 BE 프롬프트/why 생성에만 쓰임.

---

## description 품질

| 검사 | 결과 |
|------|------|
| 총 description 수 | 64 / 64 (전건 보유) |
| 빈 description | **0건** |
| 10자 미만 description | **0건** |
| 최단 description | `한국 중소형 성장주 시장 지수.` (id 14, 17자) |

→ **이슈 없음.** 모든 항목이 충분한 설명을 가지며, 평균적으로 30~50자 수준의 구체적 설명(측정 대상 + 투자적 함의)을 포함.

---

## keyword_rules 고아

### 고아 규칙 — **없음** ✅

- **BE** `indicator_matcher.KEYWORD_RULES` (11개 룰, **이름 기반** 참조): 참조 이름 11종(`EPS 추이`, `KOSPI 지수`, `RSI (14일)`, `S&P 500`, `VIX (공포지수)`, `기관 순매수 추이`, `뉴스 센티먼트`, `미국 10년 국채 금리`, `미국 기준금리`, `외국인 순매수 추이`, `원/달러 환율`) → **전부 카탈로그 존재**. 고아 0.
- **FE** `KEYWORD_INDICATOR_MAP` (29개 룰, **ID 기반** 참조): 참조 ID 53종 → **전부 카탈로그 존재**. 고아 0.

### ⚠️ 발견 1 — BE/FE keyword 엔진의 심각한 분기 (핵심 리스크)

두 개의 **독립적인** keyword 추천 엔진이 존재하며 커버리지 격차가 크다.

| | BE `KEYWORD_RULES` | FE `KEYWORD_INDICATOR_MAP` |
|--|------|------|
| 룰 그룹 수 | **11** | **29** |
| 참조 방식 | 지표 **이름** | 지표 **ID** |
| 커버 주제 | 수급/금리/VIX/환율/기술적/센티먼트/실적/기관/S&P/코스피/정치 | 좌측 + 유가·금·구리·천연가스·암호화폐·PER/PBR·ROE/ROA·부채·배당·회전율·이익품질·인플레·고용·GDP·주택·반도체·중국·일본·광고 등 |

- **결과**: 동일 전제 텍스트에 대해 BE `match_by_keywords()`와 FE `findRelatedIndicators()`가 **서로 다른 추천 집합**을 반환한다. BE는 FE의 부분집합.
- FE keyword map이 **한 번도 추천하지 않는 카탈로그 ID 11개**: `13(다우존스), 14(코스닥), 22(은), 38(달러/유로), 41(스토캐스틱), 42(볼린저), 43(ATR), 44(OBV), 45(SMA50), 46(SMA200), 47(EMA12)` → 이들은 전체 카탈로그 브라우즈로만 도달 가능(키워드 추천 경로 없음).

### ⚠️ 발견 2 — keyword_rules 필드 인라인 복제 (드리프트 위험)

BE `KEYWORD_RULES`의 각 지표는 `data_source / data_params / support_direction`을 **카탈로그에서 조회하지 않고 인라인으로 복제**한다. 카탈로그 변경 시 룰이 자동 추종하지 못함.

- 단, `match_indicators_for_llm()`의 2순위 경로는 `_find_in_catalog(name)`으로 카탈로그 항목을 재조회하여 덮어쓰므로 이 경로에서는 드리프트가 완화됨.
- 그러나 `match_indicators_for_premise()`(직접 API 경로)는 룰 dict를 그대로 반환 → 복제된 값이 그대로 노출됨.

### ⚠️ 발견 3 — EPS 룰 indicator_type 불일치

| 지표 | KEYWORD_RULES `indicator_type` | 카탈로그 `category` | 판정 |
|------|------|------|------|
| EPS 추이 (id 5) | `market_data` | `fundamental` | ❌ **불일치** |
| (그 외 10건) | — | — | ✅ 일치 |

→ EPS는 카탈로그상 `fundamental`인데 keyword 룰에서는 `market_data`로 분류. 단일 건이지만 발견 2(복제 구조)가 드리프트를 허용한 실제 증거.

---

## data_params 형식

### 데이터 소스별 분포 (64개)

| data_source | 개수 | data_params 형식 |
|------|------|------|
| `fmp` | 34 | `{'symbol': '^GSPC'}` 또는 `{'metric': '...'}` 또는 `{'indicator': 'RSI', 'period': 14}` |
| `fred` | 11 | `{'series_id': 'FEDFUNDS'}` |
| `metrics` | 14 | `{'metric_code': 'gross_margin'}` (validation/metrics 시스템) |
| `news_sentiment` | 1 | `{}` (빈 dict) |

> **BE↔FE data_params 불일치는 구조적으로 발생 불가** — FE 미러는 data_params를 보유하지 않음. data_params는 전적으로 BE 관심사.

### ⚠️ provider(FMP 등) 정합 점검 대상

**이미 코드에서 방어됨 (#14 / common-bugs):** `audit_note`로 명시된 4건
- id 50 PER: `earningsYieldTTM` + `inverse=True` (PER = 1/earningsYield)
- id 52 ROE: `returnOnEquityTTM` + `scale_multiplier=100` (0~1 → %)
- id 53 ROA: `returnOnAssetsTTM` + `scale_multiplier=100`
- id 58 매출성장률: `growthRevenue` + `endpoint='financial-growth'` + `scale_multiplier=100`

**미주석 — provider 형식 검증 필요 (6건):**

| id | 지표 | data_params | 우려 |
|----|------|------|------|
| 1 | 외국인 순매수 추이 | `{'metric': 'foreign_net_buy'}` | FMP에 한국 외국인 순매수 표준 엔드포인트 부재 가능 — **데이터 미제공 의심** |
| 2 | 기관 순매수 추이 | `{'metric': 'institutional_net_buy'}` | 동일 — 한국 기관 순매수 데이터 FMP 미지원 의심 |
| 5 | EPS 추이 | `{'metric': 'eps'}` | `eps`는 key-metrics-ttm 표준 필드 아님 — income-statement/ratios 경유 필요 가능 |
| 51 | PBR | `{'metric': 'pbRatioTTM'}` | `/stable/ratios-ttm` vs `key-metrics-ttm` 필드명 검증 필요 |
| 54 | 부채비율 | `{'metric': 'debtToEquityTTM'}` | 동일 — TTM 필드명/엔드포인트 정합 미검증 |
| 55 | 잉여현금흐름 | `{'metric': 'freeCashFlowTTM'}` | 동일 |
| 56 | 배당수익률 | `{'metric': 'dividendYieldTTM'}` | 동일 |
| 57 | 영업이익률 | `{'metric': 'operatingProfitMarginTTM'}` | 동일 |

> ※ 본 감사는 읽기 전용이며 FMP API 실호출 검증은 수행하지 않음. 위 6건은 #14 패턴(필드명/스케일 불일치)의 미주석 후보로, 실제 fetch 시 누락/형식 오류 가능성을 표시한 것임. id 1·2(한국 수급)는 우선순위 높은 검증 대상.

---

## 권장 후속 조치 (참고 — 본 보고서는 수정 미수행)

1. **(우선) keyword 엔진 단일화**: BE 11룰을 FE 29룰 수준으로 보강하거나, 한쪽을 단일 출처로 삼아 codegen. 현재 동일 전제에 다른 추천이 나가는 사용자 경험 불일치.
2. **keyword_rules의 카탈로그 참조화**: BE `KEYWORD_RULES`가 `data_source/params/type`을 복제하지 말고 이름→카탈로그 조회로 전환 (EPS indicator_type 불일치 근본 해소).
3. **data_params provider 검증**: 미주석 6건(특히 id 1·2 한국 수급) FMP 실호출 정합 확인 후 `audit_note` 보강.
4. **카테고리 체계**: BE 5분류 ↔ FE 17분류 매핑 테이블을 contracts에 1곳 명문화하여 드리프트 차단.

> 관련 메모리: `feedback_indicator_catalog_sync` (3곳 분산 미러, 동시 업데이트 필수), `feedback_llm_indicator_hallucination` (카탈로그 외 지표 생성 금지 — `match_by_gemini`는 `match_indicators_for_llm` 2순위에서 이미 제외됨).
