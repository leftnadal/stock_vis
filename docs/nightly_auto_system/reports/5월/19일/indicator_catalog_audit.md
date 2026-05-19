# 지표 카탈로그 동기화 감사 보고서

- 감사 일자: 2026-05-20 (보고 디렉토리 5월 19일자에 적재)
- 모드: 읽기 전용 (코드 수정 없음)
- 대상 파일
  - BE 정의: `thesis/services/prompt_builder.py` (`INDICATOR_CATALOG`, `INDICATOR_FREQUENCY`, `CATEGORY_LABELS`)
  - BE 후처리: `thesis/services/llm_postprocess.py` (`INDICATOR_CATALOG`에 없는 id → None 교정)
  - BE 매칭: `thesis/services/indicator_matcher.py` (`KEYWORD_RULES`, `match_by_keywords`, `match_indicators_for_llm`, `_find_in_catalog`)
  - FE 표시: `frontend/components/thesis/AddIndicatorSheet.tsx` (`INDICATOR_CATALOG`, `KEYWORD_INDICATOR_MAP`, `findRelatedIndicators`)
- 테스트 커버: `tests/unit/thesis/test_llm_builder.py::test_indicator_catalog_has_all_fields` — BE 카탈로그 필드 존재 검증 (FE/BE 동기화는 자동 검증 없음)

---

## 요약 (동기화 상태)

| 검사 항목 | 결과 | 비고 |
|---|---|---|
| BE/FE 지표 id 집합 일치 | ✅ 양쪽 모두 64개, id 차이 0 | 그러나 자동 검증 없음 |
| BE/FE 지표 name 표기 일치 | ✅ 64건 전부 동일 | 수동 비교 결과 |
| 카테고리 체계 일치 | ⚠️ BE 5개 vs FE 17개 (서브카테고리) | 드리프트 위험 — 매핑 규칙 미문서화 |
| description 누락/빈 항목 | ✅ 64건 전부 description 존재 | 모두 10자 이상 |
| description 너무 짧음 (<10자) | ✅ 0건 | 최소 16자 (id 14 코스닥) |
| `KEYWORD_RULES`의 지표 모두 카탈로그에 존재 | ✅ 11개 indicator name 전부 매칭 | 고아 규칙 0건 |
| `KEYWORD_INDICATOR_MAP`(FE)의 id 모두 카탈로그 id로 존재 | ✅ 참조 id 53개 전부 BE 카탈로그에 존재 | 고아 0건 |
| BE/FE 키워드 매칭 룰 동기화 | ❌ BE 11개 vs FE 29개 (룰 수/키워드/타겟 id 모두 비대칭) | 동일 기능 이중 구현 |
| data_params 후처리 플래그(BE 카탈로그) | ⚠️ id 50/52/53/58에 `inverse`/`scale_multiplier`/`endpoint`/`audit_note` 존재 | FE는 data_params 미사용이라 충돌은 없음 — 단, 후처리 일관성 책임이 BE 단일 |
| `match_by_gemini` fallback 실제 사용 여부 | ⚠️ `match_indicators_for_llm`에서는 의도적으로 제외(주석 명시) | `match_indicators_for_premise`에서는 여전히 호출 — 카탈로그 외 환각 위험 잔존 |

**결론**: id/name 수준의 동기화는 현재 정확히 일치하나, **(1)** 카테고리 체계 비대칭, **(2)** BE/FE 키워드 룰 이중 구현, **(3)** Gemini fallback 잔존이 향후 드리프트와 환각의 주된 위험 지점.

---

## BE ↔ FE 불일치 목록

### 1) 지표 id/name 자체
- 불일치 없음 (64건 전부 일치).
- BE/FE 양쪽 id 집합 (정렬):
  ```
  1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16,
  20, 21, 22, 23, 24, 25, 26,
  30, 31, 32, 33, 34, 35, 36, 37, 38, 39,
  40, 41, 42, 43, 44, 45, 46, 47,
  50, 51, 52, 53, 54, 55, 56, 57, 58,
  60, 61, 62, 63, 64, 65, 66, 67, 68, 69, 70, 71, 72, 73
  ```
  (id 17~19, 27~29, 48, 49, 59 는 사전 예약/결번)

### 2) 카테고리 체계
- BE `CATEGORY_LABELS`는 5개 그룹: `market_data / macro / technical / fundamental / sentiment`.
- FE `categoryOrder`는 17개 서브카테고리:
  `수급 / 주요 지수 / 원자재 / 암호화폐 / 금리 / 환율/변동성 / 고용/성장 / 물가/주택 / 기술적 / 펀더멘털 / 재무 체질 / 밸류에이션 / 성장 / 운영 효율 / 이익 품질 / 주주환원 / 심리`.
- **위험**: 새 지표 추가 시 FE 서브카테고리 분류가 BE에는 없으므로 누락/오분류 가능. 매핑 규칙이 코드/문서 어디에도 없음.
- **권고(보고용)**: BE 카탈로그 엔트리에 `subcategory` 필드를 추가하거나, FE 매핑 표를 BE 측 단일 소스에 기록해 동기화 자동 검증을 가능하게 할 것.

### 3) `INDICATOR_FREQUENCY`(BE) ↔ FE `freq` 필드
- BE는 id→주기 매핑 dict (`prompt_builder.py:321`).
- FE는 각 엔트리에 `freq: '일간'|'주간'|'월간'|'분기'` 인라인.
- 64건 모두 값 일치 (수기 대조). 단, 자동 검증 없음 → 향후 드리프트 위험 동일.

### 4) data_params 필드
- FE `CatalogIndicator` 인터페이스에는 `data_params` 필드 자체가 없음 (id/name/category/freq만).
- 따라서 "FE/BE 형식 불일치"라기보다 **FE는 표시 전용, 데이터 호출은 100% BE 책임** 구조 → 직접 충돌 없음.

---

## description 품질

- BE 카탈로그 64건 전수 검사. 빈 description 0건, <10자 0건.
- 가장 짧은 description:
  - id 14 코스닥 지수: `'한국 중소형 성장주 시장 지수.'` (16자)
  - id 4 KOSPI 지수: `'한국 유가증권시장 전체 종목 시가총액 가중 지수.'` (26자)
- 가장 긴 description은 id 50(PER), id 36(주택착공) 등 50~60자 범위.
- `get_indicator_description()`는 접두사 매칭 폴백을 가지므로 LLM이 `"EPS 추이 (META)"` 같은 변형을 내도 description 유실 없음. ✅
- **권고**: 현재 품질은 양호. 단, "support_direction"이 `'positive'`/`'negative'`로만 표기되어 사용자 노출 시 의미 해석이 어려움 — 보고용 관찰 사항.

---

## keyword_rules 고아 (`indicator_matcher.py`)

### 4-1) BE `KEYWORD_RULES` (총 11개 룰)
- 룰이 가리키는 indicator name → 카탈로그 매칭 결과:

| 룰 키워드(대표) | 대상 name | 카탈로그 id | 결과 |
|---|---|---|---|
| 외국인/외인 | 외국인 순매수 추이 | 1 | ✅ |
| 금리/FOMC | 미국 기준금리 (Fed Funds Rate) | 6 | ✅ |
| 금리/FOMC | 미국 10년 국채 금리 | 7 | ✅ |
| VIX/공포 | VIX (공포지수) | 8 | ✅ |
| 환율/달러 | 원/달러 환율 | 9 | ✅ |
| RSI/MACD | RSI (14일) | 10 | ✅ |
| 센티먼트/여론 | 뉴스 센티먼트 | 11 | ✅ |
| 실적/EPS | EPS 추이 | 5 | ✅ |
| 기관/연기금 | 기관 순매수 추이 | 2 | ✅ |
| S&P/나스닥 | S&P 500 | 3 | ✅ |
| 코스피 | KOSPI 지수 | 4 | ✅ |
| 선거/정치 | VIX (공포지수), KOSPI 지수 | 8, 4 | ✅ |

- **고아 0건**.
- 단, BE 룰은 11개로 64개 카탈로그의 ~17%만 커버. `match_by_keywords()`가 다양한 펀더멘털/재무 체질 지표를 매칭하지 못함 → `match_indicators_for_premise` 경로에서 Gemini fallback이 자주 동작할 수밖에 없는 구조.

### 4-2) FE `KEYWORD_INDICATOR_MAP` (총 29개 룰)
- 룰이 가리키는 indicator id 모두 BE 카탈로그에 존재. **고아 0건**.
- FE 룰 ID 집합: `{1,2,3,4,5,6,7,8,9,10,11,12,15,16,20,21,23,24,25,26,30,31,32,33,34,35,36,37,39,40,50,51,52,53,54,55,56,57,58,60,61,62,63,64,65,66,67,68,69,70,71,72,73}` — 모두 카탈로그 유효.
- **위험 — BE/FE 룰 이중 구현**:
  - 동일 기능을 BE(`match_by_keywords`)와 FE(`findRelatedIndicators`)에서 각각 작성. 키워드, 타겟 id, 추천 이유가 비대칭.
  - 예: "유가/원유" → BE에는 매칭 룰 없음, FE는 id 21 추천.
  - 예: "rsi/macd" → BE는 id 10만 추천, FE는 id 10, 40 동시 추천.
  - 예: "기관" → BE/FE 둘 다 id 2 추천. 일관됨.
- **권고(보고용)**: 룰을 BE 단일 소스로 통합하거나 contracts 측에 JSON으로 추출하고 양쪽이 참조하도록 해야 드리프트가 멈춤.

### 4-3) Gemini fallback (`match_by_gemini`)
- `match_indicators_for_llm`은 의도적으로 제외(주석: "카탈로그에 없는 환각 지표를 생성하므로 제외"). ✅
- 그러나 `match_indicators_for_premise()`는 `if not matched: matched = match_by_gemini(...)` 경로로 여전히 호출됨 (`indicator_matcher.py:265-266`).
- `match_by_gemini` 응답은 `data_source/indicator_type/support_direction`만 검증할 뿐 카탈로그에 실존하는지 확인하지 않음. **카탈로그 외 환각 잔존 위험**.
- 메모리 노트(`feedback_llm_indicator_hallucination.md`)에 "match_by_gemini 제거, 카탈로그 외 지표 생성 금지"가 있으나 `match_indicators_for_premise` 경로는 아직 정리되지 않음 → **회귀 위험 항목으로 표시**.

---

## data_params 형식

### 5-1) data_source별 BE 카탈로그 형식
| data_source | data_params 형식 | 비고 |
|---|---|---|
| `fmp` (지수/원자재/암호화폐/환율) | `{'symbol': '^GSPC' \| 'GCUSD' \| 'BTCUSD' \| 'USDKRW' ...}` | FMP `/stable/quote` 호출 키 |
| `fmp` (수급/EPS 등) | `{'metric': 'foreign_net_buy' \| 'institutional_net_buy' \| 'eps'}` | 내부 prefetch/processor 측 키 |
| `fmp` (key-metrics-ttm) | `{'metric': 'pbRatioTTM'}` 등 | id 51, 54~57 |
| `fmp` (보정 필요 — #14 회귀) | `{'metric': 'earningsYieldTTM', 'inverse': True, 'audit_note': ...}` (id 50 PER) | `1 / earningsYieldTTM` |
| | `{'metric': 'returnOnEquityTTM', 'scale_multiplier': 100, 'audit_note': ...}` (id 52 ROE) | 0~1 → % 변환 |
| | `{'metric': 'returnOnAssetsTTM', 'scale_multiplier': 100, 'audit_note': ...}` (id 53 ROA) | 동일 패턴 |
| | `{'metric': 'growthRevenue', 'endpoint': 'financial-growth', 'scale_multiplier': 100, 'audit_note': ...}` (id 58) | FMP `/stable/financial-growth/` |
| `fmp` (기술적) | `{'indicator': 'RSI', 'period': 14}`, `{'indicator': 'MACD', 'fast': 12, 'slow': 26, 'signal': 9}` 등 | FMP technical indicator API 키 |
| `fred` | `{'series_id': 'FEDFUNDS' \| 'DGS10' \| 'CPIAUCSL' ...}` | FRED series id |
| `metrics` | `{'metric_code': 'gross_margin' \| 'roic' ...}` (id 60~73) | 내부 `metrics` 앱의 `MetricCode` enum 키 |
| `news_sentiment` | `{}` (파라미터 없음, target_symbol로 식별) | id 11 |

### 5-2) 실제 데이터 제공자 정합성 (감사 시점 관찰)
- ✅ `audit_note` 4건은 모두 `common-bugs.md` #14 회귀 방지 마커. 후처리 책임이 어떤 모듈에 있는지(예: `quarterly_metric_fetcher.RATIO_METRICS`)는 카탈로그 메타데이터에 명시되어 있지 않고 주석으로만 존재 → **메타데이터화 권고(보고용)**.
- ⚠️ id 50 PER `data_source='fmp'` + 주석에는 "정확 fetch는 `quarterly_metric_fetcher` 분기 (별도 PR)" 라고 명시되어 있어 **현재 카탈로그의 data_source가 실제 fetch 경로와 일치하지 않을 수 있음**. 분기 PR 진행 상태를 별도 확인 권장.
- ⚠️ id 58 매출성장률 `endpoint: 'financial-growth'`도 BE 측에서 default `/stable/quote` 가 아닌 `/stable/financial-growth/` 호출 분기 처리가 필요. 호출자 코드(별도 모듈, 본 감사 범위 외)에서 `endpoint` 키를 인식하지 못하면 잘못된 API로 빠질 위험. 감사 범위에서는 호출자 검증 미수행.
- ⚠️ `indicator_matcher.KEYWORD_RULES`에 적힌 `data_params`(예: VIX → `{'symbol': '^VIX'}`)는 카탈로그와 형식 동일하나 **`indicator_db_id` 키가 빠져 있음**. `match_indicators_for_llm`은 `_find_in_catalog(name)` 폴백으로 보완하므로 현재는 안전. 그러나 카탈로그의 name이 바뀌면 룰의 name과 어긋나 폴백 실패 → 드리프트 위험.

### 5-3) FE측
- FE는 데이터 호출을 하지 않고, BE의 `/api/v1/thesis/*` 응답을 그대로 렌더링. 따라서 `data_params` 형식 불일치 영향 없음.

---

## 부록 — 보고용 권고 사항 (참고)

1. **단일 소스 통합**: `KEYWORD_RULES`(BE) 과 `KEYWORD_INDICATOR_MAP`(FE) 을 `contracts/` 혹은 BE 노출 엔드포인트로 통합. 이중 작성 종식.
2. **`match_by_gemini` 사용처 정리**: `match_indicators_for_premise` 경로의 Gemini fallback도 카탈로그 외 지표를 생성하므로 `match_indicators_for_llm`과 동일 정책 적용 검토. 메모리 노트 `feedback_llm_indicator_hallucination.md` 정책 일관 적용.
3. **카테고리 매핑 명시**: BE 카탈로그 항목에 `subcategory` 필드 추가 또는 FE 서브카테고리 매핑을 BE에 기록. 자동 동기화 검증 테스트 추가.
4. **`audit_note`/`inverse`/`scale_multiplier`/`endpoint` 메타 사용처 명문화**: 어느 fetcher가 어느 키를 인식해야 하는지 contracts 또는 docs/에 기록. 호출자가 키를 무시해도 침묵 실패하지 않도록 방어 코드.
5. **자동 동기화 테스트**: `tests/unit/thesis/test_llm_builder.py`에 "FE catalog mirror" 비교 테스트(예: ts 파일을 정규식 파싱하여 id/name 집합 비교) 추가 검토.

---

## 감사 종료 메모
- 코드 수정 0건. 본 보고서는 읽기 전용 산출물.
- 다음 감사 권장 주기: 2주 또는 신규 지표 추가 PR 시점.
