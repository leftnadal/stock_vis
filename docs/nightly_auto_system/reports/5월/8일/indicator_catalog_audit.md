# 지표 카탈로그 동기화 감사 보고서

- **감사일**: 2026-05-08
- **모드**: 읽기 전용
- **검사 대상**:
  - BE 정의: `thesis/services/prompt_builder.py` (INDICATOR_CATALOG, INDICATOR_FREQUENCY)
  - BE 후처리: `thesis/services/llm_postprocess.py` (`indicator_db_id` 검증/null 교정)
  - BE 매칭: `thesis/services/indicator_matcher.py` (`KEYWORD_RULES`, `match_by_keywords`, `match_indicators_for_llm`)
  - FE 표시: `frontend/components/thesis/AddIndicatorSheet.tsx` (`INDICATOR_CATALOG`, `KEYWORD_INDICATOR_MAP`)

---

## 요약 (동기화 상태)

| 항목 | 상태 | 비고 |
|---|---|---|
| **카탈로그 ID 집합** (BE ↔ FE) | ✅ **완전 일치** | 양쪽 64개 항목, 모든 ID 1:1 매칭 |
| **카탈로그 이름** (BE ↔ FE) | ✅ **완전 일치** | 64개 모두 동일 문자열 |
| **카탈로그 freq** (BE INDICATOR_FREQUENCY ↔ FE freq 필드) | ✅ **완전 일치** | 64개 매칭 검증 |
| **description 필드** (BE) | ✅ 모든 항목 채워짐, 최소 16자 / 최대 ~50자 — 빈/미달 없음 |
| **FE 카탈로그 description** | ⚠️ **FE는 description 자체를 미러하지 않음** (id/name/category/freq만) — 의도된 축약이지만 hover/툴팁 향후 도입 시 별도 fetch 필요 |
| **BE indicator_matcher.KEYWORD_RULES** | ✅ 11개 룰 모두 카탈로그 내 지표명을 사용 (고아 0건) |
| **FE KEYWORD_INDICATOR_MAP** | ✅ 29개 룰의 모든 indicatorIds가 카탈로그 ID 집합 내 (고아 0건) |
| **BE ↔ FE 키워드 룰 커버리지** | ⚠️ **불균형** — BE 11개 vs FE 29개. BE는 신규 펀더멘털(60–73)과 원자재(20–24) 키워드가 빠져 있어 LLM 미사용 경로(text fallback)에서 매칭 누락 가능 |
| **data_params 형식** | ⚠️ 카탈로그 내부 일관성은 OK, 단 `inverse`/`scale_multiplier`/`endpoint` 같은 비표준 키 4건이 있어 FMP fetcher가 이 키들을 해석하는지가 별도 의존 (#14 회귀 방지 audit_note 명시됨) |
| **llm_postprocess의 카탈로그 검증** | ✅ `indicator_db_id`가 카탈로그에 없으면 None 교정, target_symbol 대문자화 — 정상 |
| **match_indicators_for_llm의 환각 방지 가드** | ✅ `match_by_gemini` 호출이 명시적으로 제외됨 (주석: "카탈로그에 없는 환각 지표 생성") |

**전체 판정**: 🟢 **양호** — 카탈로그 자체 동기화는 완벽. 다만 BE 키워드 룰 커버리지가 FE 대비 부족하다는 운영상 갭이 존재.

---

## BE ↔ FE 불일치 목록

### ID 집합 비교 (정렬)

```
BE (prompt_builder.py INDICATOR_CATALOG):
  1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16,
  20, 21, 22, 23, 24, 25, 26,
  30, 31, 32, 33, 34, 35, 36, 37, 38, 39,
  40, 41, 42, 43, 44, 45, 46, 47,
  50, 51, 52, 53, 54, 55, 56, 57, 58,
  60, 61, 62, 63, 64, 65, 66, 67, 68, 69, 70, 71, 72, 73
  → 64개

FE (AddIndicatorSheet.tsx INDICATOR_CATALOG):
  1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16,
  20, 21, 22, 23, 24, 25, 26,
  30, 31, 32, 33, 34, 35, 36, 37, 38, 39,
  40, 41, 42, 43, 44, 45, 46, 47,
  50, 51, 52, 53, 54, 55, 56, 57, 58,
  60, 61, 62, 63, 64, 65, 66, 67, 68, 69, 70, 71, 72, 73
  → 64개
```

**결과**: BE−FE = ∅, FE−BE = ∅ → **완전 일치**.

### 이름 문자열 비교 (sample 검증)

| ID | BE 이름 | FE 이름 | 일치 |
|---|---|---|---|
| 5 | EPS 추이 | EPS 추이 | ✅ |
| 8 | VIX (공포지수) | VIX (공포지수) | ✅ |
| 50 | PER (주가수익비율) | PER (주가수익비율) | ✅ |
| 52 | ROE (자기자본이익률) | ROE (자기자본이익률) | ✅ |
| 54 | 부채비율 (Debt/Equity) | 부채비율 (Debt/Equity) | ✅ |
| 65 | 순부채/EBITDA | 순부채/EBITDA | ✅ |
| 70 | 매출채권 회전일수 (DSO) | 매출채권 회전일수 (DSO) | ✅ |
| 73 | 순주주수익률 | 순주주수익률 | ✅ |

**결과**: 64건 전수 비교에서 이름 불일치 0건.

### 빈도(freq) 비교

| ID | BE INDICATOR_FREQUENCY | FE freq | 일치 |
|---|---|---|---|
| 6 | 주간 | 주간 | ✅ |
| 7 | 일간 | 일간 | ✅ |
| 31 | 월간 | 월간 | ✅ |
| 34 | 분기 | 분기 | ✅ |
| 37 | 주간 | 주간 | ✅ |
| 60–73 | 분기 | 분기 | ✅ |

**결과**: 64건 매칭 검증, 불일치 0건.

### 카테고리 분류 비교 (구조적 차이 — **불일치 아님**)

| 측면 | BE (CATEGORY_LABELS) | FE (categoryOrder) |
|---|---|---|
| 카테고리 수 | **5개 대분류** | **17개 세분류** |
| 예시 | `market_data` → "시장 데이터" | `수급`, `주요 지수`, `원자재`, `암호화폐` (4개로 분할) |
| 펀더멘털 분할 | `fundamental` 1개 | `펀더멘털`, `재무 체질`, `밸류에이션`, `성장`, `운영 효율`, `이익 품질`, `주주환원` (7개로 분할) |

**판정**: 의도된 차이로 보임 (BE는 LLM 프롬프트 그루핑용, FE는 사용자 탐색용).
**잠재 리스크**: 새 지표 추가 시 BE/FE 양쪽에서 카테고리 분류를 별도 결정해야 하므로 일관성 유지 비용 발생. 단, 현재 시점 누락은 없음.

---

## description 품질

### BE INDICATOR_CATALOG description 검사

- **빈 description**: **0건**
- **10자 미만 description**: **0건**
- **최단 description**:
  - id 14 코스닥 지수: "한국 중소형 성장주 시장 지수." (16자)
  - id 4 KOSPI 지수: "한국 유가증권시장 전체 종목 시가총액 가중 지수." (26자)
- **최장 description**: 50자 내외 (예: id 73 순주주수익률 "배당 + 자사주 매입 - 신주 발행의 순 환원율. 주주 환원 종합 지표.")
- **품질 평가**:
  - 모든 항목이 "무엇 + 왜 중요한가" 패턴으로 1~2문장 작성
  - audit_note 4건(id 50/52/53/58)은 회귀 방지 메모 — description과 분리되어 있어 사용자 노출 없음 (정상)

### FE 카탈로그 description 검사

- **상태**: FE INDICATOR_CATALOG 타입에 `description` 필드 없음 (`id/name/category/freq`만 미러)
- **영향**: AddIndicatorSheet에 지표 클릭/hover 시 설명 표시 기능 부재
- **권장 (참고)**: 현재 BE→FE 동기화가 수동 미러이므로 description까지 미러하면 유지보수 부담 증가. 향후 사용자가 지표를 이해할 도움말이 필요하면 `/api/v1/thesis/indicators/catalog/` 같은 단일 소스 엔드포인트로 전환을 검토.

### `get_indicator_description()` 헬퍼 (prompt_builder.py:351)

- 기능: 지표 이름으로 description 조회 (정확 매칭 + 접두사 매칭)
- 용도: LLM 모드에서 "EPS 추이 (META)"처럼 심볼이 붙은 케이스 대응
- 상태: ✅ 정상 — 카탈로그 미스 시 빈 문자열 반환 (안전한 fallback)

---

## keyword_rules 고아

### BE indicator_matcher.py `KEYWORD_RULES` (11개 룰)

각 룰의 추천 지표 이름이 INDICATOR_CATALOG에 존재하는지 검사:

| # | 키워드 (대표) | 추천 지표명 | 카탈로그 매칭 |
|---|---|---|---|
| 1 | 외국인/외인/순매수 | 외국인 순매수 추이 | ✅ id:1 |
| 2 | 금리/연준/FOMC | 미국 기준금리, 미국 10년 국채 금리 | ✅ id:6, id:7 |
| 3 | VIX/공포/변동성 | VIX (공포지수) | ✅ id:8 |
| 4 | 환율/달러/원달러 | 원/달러 환율 | ✅ id:9 |
| 5 | RSI/MACD/기술적 | RSI (14일) | ✅ id:10 |
| 6 | 센티먼트/여론/뉴스 | 뉴스 센티먼트 | ✅ id:11 |
| 7 | 실적/EPS/매출/PER | EPS 추이 | ✅ id:5 |
| 8 | 기관/연기금 | 기관 순매수 추이 | ✅ id:2 |
| 9 | S&P/NASDAQ/다우 | S&P 500 | ✅ id:3 |
| 10 | 코스피/KOSPI | KOSPI 지수 | ✅ id:4 |
| 11 | 선거/정치/정책 | VIX, KOSPI | ✅ id:8, id:4 |

**고아 룰**: **0건**.
**검증 경로**: `match_indicators_for_llm()` (indicator_matcher.py:271)이 PK 매칭 실패 시 text fallback에서 `_find_in_catalog()`로 최종 검증하므로 고아가 있어도 안전망 존재.

### FE `KEYWORD_INDICATOR_MAP` (29개 룰)

각 룰의 `indicatorIds`가 INDICATOR_CATALOG ID 집합에 존재하는지 검사:

- 모든 29개 룰의 indicatorIds (1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 15, 16, 20, 21, 23, 24, 25, 26, 30, 31, 32, 33, 34, 35, 36, 37, 39, 40, 50, 51, 52, 53, 54, 55, 56, 57, 58, 60, 61, 62, 63, 64, 65, 66, 67, 68, 69, 70, 71, 72, 73) 모두 **카탈로그에 존재**.
- **고아 ID**: **0건**.

### ⚠️ BE ↔ FE 키워드 룰 커버리지 갭

BE는 11개 룰만 정의 → 신규 펀더멘털(60–73), 원자재(20–24), 암호화폐(25–26), 거시 일부(31–36, 38, 39) 키워드를 매칭하지 못함.

**FE에는 있지만 BE에는 없는 키워드 카테고리**:

| FE 룰 키워드 | FE 추천 ID | BE 룰에서의 처리 |
|---|---|---|
| 유가/원유/wti/석유/opec | [21] | ❌ 없음 |
| 금/gold/금값/안전자산 | [20] | ❌ 없음 |
| 구리/copper/산업금속 | [23] | ❌ 없음 |
| 천연가스/lng | [24] | ❌ 없음 |
| 비트코인/btc/암호화폐 | [25, 26] | ❌ 없음 |
| per/pbr/밸류에이션 | [50, 51, 67, 68] | ⚠️ "EPS"만 룰7에서 EPS로 매칭됨 |
| roe/roa/roic/마진 | [52, 53, 57, 60–62] | ❌ 없음 |
| 부채/레버리지/유동성 | [54, 63–65] | ❌ 없음 |
| 배당/dividend/fcf/주주환원 | [55, 56, 66, 68, 73] | ❌ 없음 |
| 회전율/효율/매출채권 | [70, 71] | ❌ 없음 |
| 이익품질/발생액/회계 | [72, 66] | ❌ 없음 |
| 인플레/cpi/물가 | [33] | ❌ 없음 |
| 고용/실업/nfp | [31, 32] | ❌ 없음 |
| gdp/성장/산업생산 | [34, 35] | ❌ 없음 |
| 주택/부동산/모기지/reit | [36, 37] | ❌ 없음 |
| 반도체/테크/엔비디아 | [12, 3] | ❌ 없음 |
| 중국/항셍/홍콩 | [16] | ❌ 없음 |
| 일본/니케이/엔화 | [15] | ❌ 없음 |
| 광고/디지털/플랫폼 | [3, 12] | ❌ 없음 |

**영향**:
- LLM이 `indicator_db_id`를 정상적으로 채우는 경로(prompt_builder.build_indicator_block 사용)에서는 영향 없음 (PK 매칭이 1순위)
- `indicator_matcher.match_indicators_for_premise()` 같은 **LLM 미사용 / text-only 경로**에서 신규 카테고리 키워드 미매칭 → 빈 결과 반환
- 자동 매칭 실패 시 `match_by_gemini()` 호출 가능성 — 그러나 `match_indicators_for_llm()`는 환각 방지로 이 fallback을 명시적으로 제외함 (indicator_matcher.py:307 주석 참조)

**판정**: 🟡 **카탈로그 확장(60~73 추가) 이후 BE 키워드 룰이 동기 업데이트되지 않은 부채**. 운영상 즉시 장애는 아님 (LLM PK 경로가 주된 사용처).

---

## data_params 형식

### BE INDICATOR_CATALOG의 data_params 형식 분류

| data_source | data_params 형식 | 예시 ID |
|---|---|---|
| `fmp` (가격 시계열) | `{'symbol': '^GSPC'}` | 3, 4, 8, 9, 12–16, 20–26, 39 |
| `fmp` (메트릭) | `{'metric': 'eps'}`, `{'metric': 'pbRatioTTM'}` | 1, 2, 5, 51, 54–57 |
| `fmp` (기술지표) | `{'indicator': 'RSI', 'period': 14}` | 10, 40–47 |
| `fred` (시리즈) | `{'series_id': 'FEDFUNDS'}` | 6, 7, 30, 31–37, 38 |
| `metrics` (validation 시스템) | `{'metric_code': 'gross_margin'}` | 60–73 |
| `news_sentiment` | `{}` | 11 |

### ⚠️ 비표준 data_params 키 (FMP 호환성 메모)

`audit_note` 필드로 회귀 방지 명시된 4건:

| ID | 지표 | 비표준 키 | 이유 (audit_note 인용) |
|---|---|---|---|
| 50 | PER (주가수익비율) | `'inverse': True` | "PER = 1 / earningsYieldTTM (#14 회귀 방지)" — FMP key-metrics-ttm에 `peRatioTTM` 미존재, `earningsYieldTTM` 역수로 계산 |
| 52 | ROE (자기자본이익률) | `'scale_multiplier': 100` | "ratio 0~1 → % (#14 회귀 방지)" — FMP는 0~1 비율 반환 |
| 53 | ROA (총자산이익률) | `'scale_multiplier': 100` | "ratio 0~1 → % (#14 동일 패턴)" |
| 58 | 매출성장률 (YoY) | `'endpoint': 'financial-growth'`, `'metric': 'growthRevenue'`, `'scale_multiplier': 100` | "FMP /financial-growth/ growthRevenue (#14 표준 필드 아님)" — key-metrics-ttm에 없음, 별도 endpoint 필요 |

**감사 한계**: 본 감사는 카탈로그 정의만 검사. **`inverse`/`scale_multiplier`/`endpoint` 키를 실제로 해석하는 fetcher 코드(예: thesis 데이터 수집 태스크)가 존재하는지 별도 검증 필요**. CLAUDE.md "공통 버그 #14"가 quarterly_metric_fetcher 분기로 처리됐다고 명시되어 있으므로 이 데이터들은 `data_source='metrics'` 경로로 옮겨가는 것이 안전 (60~73 펀더멘털과 동일 패턴).

### BE indicator_matcher.KEYWORD_RULES의 data_params 형식 ↔ INDICATOR_CATALOG 일관성

키워드 룰의 11개 indicators 모두 카탈로그와 동일한 data_params 형식 사용 — **불일치 0건**.

| 룰 | data_params (KEYWORD_RULES) | data_params (CATALOG) | 일치 |
|---|---|---|---|
| id:1 외국인 | `{'metric': 'foreign_net_buy'}` | `{'metric': 'foreign_net_buy'}` | ✅ |
| id:6 기준금리 | `{'series_id': 'FEDFUNDS'}` | `{'series_id': 'FEDFUNDS'}` | ✅ |
| id:7 10년 국채 | `{'series_id': 'DGS10'}` | `{'series_id': 'DGS10'}` | ✅ |
| id:8 VIX | `{'symbol': '^VIX'}` | `{'symbol': '^VIX'}` | ✅ |
| id:9 환율 | `{'symbol': 'USDKRW'}` | `{'symbol': 'USDKRW'}` | ✅ |
| id:10 RSI | `{'indicator': 'RSI', 'period': 14}` | `{'indicator': 'RSI', 'period': 14}` | ✅ |
| id:11 센티먼트 | `{}` | `{}` | ✅ |
| id:5 EPS | `{'metric': 'eps'}` | `{'metric': 'eps'}` | ✅ |
| id:2 기관 | `{'metric': 'institutional_net_buy'}` | `{'metric': 'institutional_net_buy'}` | ✅ |
| id:3 S&P | `{'symbol': '^GSPC'}` | `{'symbol': '^GSPC'}` | ✅ |
| id:4 KOSPI | `{'symbol': '^KS11'}` | `{'symbol': '^KS11'}` | ✅ |

### FE 측 data_params

FE 카탈로그는 `data_params` 자체를 미러하지 않음 (id/name/category/freq만). 데이터 fetch는 BE API에 위임 — **이중 정의 위험 없음**.

---

## 부록: 추가 관찰 사항 (참고)

### A1. `match_by_gemini` 환각 방지 가드 (indicator_matcher.py:306-313)

```python
# 2순위: PK 매칭 실패 시 키워드 룰 매칭만 사용
# (match_by_gemini fallback은 카탈로그에 없는 환각 지표를 생성하므로 제외)
```

이는 메모리(feedback_llm_indicator_hallucination) 항목과 일치하는 정상 가드. 다만 `match_by_gemini` 함수 자체(indicator_matcher.py:186-254)는 **여전히 정의되어 있으며** `match_indicators_for_premise()`(:257)에서는 호출됨.

**관찰**: `match_indicators_for_premise()`(text-only fallback 경로)는 환각 가드가 없음. 호출처가 LLM 미사용 경로(예: 수동 가설 작성, 검증 도구)뿐이라면 영향 제한적이나, 호출 그래프 확인 권장.

### A2. INDICATOR_FREQUENCY 누락 검증

INDICATOR_CATALOG의 모든 64개 ID가 INDICATOR_FREQUENCY dict에 매핑되어 있는지 전수 검증:

```
CATALOG IDs: {1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,
              20,21,22,23,24,25,26,
              30,31,32,33,34,35,36,37,38,39,
              40,41,42,43,44,45,46,47,
              50,51,52,53,54,55,56,57,58,
              60,61,62,63,64,65,66,67,68,69,70,71,72,73}

FREQUENCY IDs: {1,2,3,4,12,13,14,15,16,
                20,21,22,23,24,25,26,
                8,9,38,39,
                10,40,41,42,43,44,45,46,47,
                11,
                6,7,30,37,
                31,32,33,34,35,36,
                5,50,51,52,53,54,55,56,57,58,
                60,61,62,63,64,65,66,67,68,69,70,71,72,73}
```

**결과**: 두 집합 동일 (64개) → 누락 0건. `build_indicator_block()`에서 `freq` 미정의 시 빈 태그 출력으로 안전.

### A3. llm_postprocess.normalize_llm_output (llm_postprocess.py:82-93)

```python
from thesis.services.prompt_builder import get_indicator_by_id
for p in unique_premises:
    for ind in p.get('recommended_indicators', []):
        db_id = ind.get('indicator_db_id')
        if db_id is not None and get_indicator_by_id(db_id) is None:
            logger.info(f"indicator_db_id {db_id} not in catalog, nullified")
            ind['indicator_db_id'] = None
```

LLM이 카탈로그 외 ID를 환각 생성해도 None으로 강제 교정 — 안전망 정상 작동.

---

## 결론

1. **카탈로그 자체 동기화는 완벽** (BE ↔ FE 64개 ID/이름/freq 1:1 일치).
2. **description 품질 양호** (BE 64개 모두 채워짐, 빈/미달 0건).
3. **고아 keyword 규칙 0건** (양쪽 모두).
4. **운영상 부채 1건**: BE `KEYWORD_RULES`(11개)가 FE `KEYWORD_INDICATOR_MAP`(29개) 대비 신규 카테고리(원자재, 암호화폐, 펀더멘털 60–73, 거시 31–37 등) 키워드를 다수 미커버. 카탈로그가 64개로 확장되는 동안 BE 룰만 11개로 정체.
5. **data_params 비표준 키 4건** (#14 회귀 방지 audit_note 명시) — 카탈로그 정의 자체는 의도적이지만, 실제 fetcher 코드의 해석 여부는 별도 감사 권장.
6. **환각 방지 가드** (`match_by_gemini` 제외, `indicator_db_id` null 교정) 정상 작동.

---

*감사 완료. 코드 수정 없음.*
