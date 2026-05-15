# 지표 카탈로그 동기화 감사 보고서

- 감사일: 2026-05-13
- 감사 범위: `INDICATOR_CATALOG` (BE), `KEYWORD_RULES` (BE), `INDICATOR_CATALOG`/`KEYWORD_INDICATOR_MAP` (FE), `INDICATOR_FREQUENCY`
- 감사 대상 파일
  - `thesis/services/prompt_builder.py` (BE 카탈로그 정의)
  - `thesis/services/llm_postprocess.py` (BE 후처리/`get_indicator_by_id` 검증)
  - `thesis/services/indicator_matcher.py` (BE 키워드 룰 + Gemini fallback)
  - `frontend/components/thesis/AddIndicatorSheet.tsx` (FE 미러 + UI 키워드 룰)

---

## 요약 (동기화 상태)

| 항목 | 상태 | 비고 |
|------|------|------|
| BE ↔ FE 카탈로그 ID 집합 | ✅ 완전 일치 | 양쪽 64개 ID (1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,20-26,30-47,50-58,60-73) |
| BE ↔ FE 지표 이름 | ✅ 완전 일치 | 64개 항목 모두 동일 문자열 |
| BE `INDICATOR_FREQUENCY` ↔ FE `freq` | ✅ 완전 일치 | 일간/주간/월간/분기 매핑 동일 |
| 카테고리 라벨 체계 | ⚠️ 의도된 차이 | BE 5개 대분류, FE 17개 세부 분류 (UI 그룹핑용) |
| BE `KEYWORD_RULES` ↔ BE 카탈로그 | ⚠️ 1건 카테고리 불일치 | "EPS 추이"의 `indicator_type` |
| BE `KEYWORD_RULES` 커버리지 | 🟥 심각하게 부족 | 11개 지표 룰 (FE는 26개 룰로 60+ ID 커버) |
| FE `KEYWORD_INDICATOR_MAP` 고아 ID | ✅ 없음 | 참조 ID 전부 카탈로그에 존재 |
| description 필드 채움 | ✅ 100% (64/64) | 빈/미달 항목 없음 |
| `data_params` 형식 (FMP 변환) | ✅ 명시됨 | PER/ROE/ROA/매출성장률은 `inverse`/`scale_multiplier`/`endpoint` + `audit_note` 표시 |

**총평**: 항목 집합·이름·주기는 BE/FE가 완전히 동기화되어 있음. 그러나 **BE 키워드 매칭(`KEYWORD_RULES`)이 카탈로그 64개 중 11개만 커버**하므로, 사용자가 "유가/금/배당/CPI/GDP/PER" 같은 단어를 써도 BE는 키워드 매칭에 실패하여 LLM fallback에 의존하게 된다. FE는 같은 컨텍스트에서 더 많은 ID를 추천한다.

---

## BE ↔ FE 불일치 목록

### 1. ID/이름/주기 불일치
**없음.** BE `INDICATOR_CATALOG` (총 64개)와 FE `INDICATOR_CATALOG` (총 64개)는 ID 집합·표시 이름·업데이트 주기까지 완전 일치.

검증한 ID 집합:
```
공통 64개: 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16,
           20, 21, 22, 23, 24, 25, 26,
           30, 31, 32, 33, 34, 35, 36, 37, 38, 39,
           40, 41, 42, 43, 44, 45, 46, 47,
           50, 51, 52, 53, 54, 55, 56, 57, 58,
           60, 61, 62, 63, 64, 65, 66, 67, 68, 69, 70, 71, 72, 73
```

> 결번: 17,18,19,27,28,29,48,49,59 — 향후 추가 슬롯 또는 폐기된 ID로 추정 (현재 어느 쪽에도 없으므로 동기화 영향 없음).

### 2. 카테고리 라벨 체계 차이 (의도된 분리)
| 측면 | BE (`category`) | FE (`category`) |
|------|----------------|-----------------|
| 분류 수 | 5개 | 17개 |
| 값 | `market_data` / `macro` / `technical` / `fundamental` / `sentiment` | `수급` / `주요 지수` / `원자재` / `암호화폐` / `금리` / `환율/변동성` / `고용/성장` / `물가/주택` / `기술적` / `펀더멘털` / `재무 체질` / `밸류에이션` / `성장` / `운영 효율` / `이익 품질` / `주주환원` / `심리` |
| 용도 | LLM 프롬프트 카테고리 그룹핑 (`build_indicator_block`) | 모바일 시트 UI 그룹핑 (사용자 탐색용) |

→ 이 차이는 의도된 것으로 보임. 다만 BE → FE 매핑 룰이 코드에 명시되어 있지 않아, 새 지표 추가 시 FE 카테고리를 수동으로 정해야 함. **위험도: 낮음**.

### 3. BE `KEYWORD_RULES` 내부 카테고리 vs 카탈로그 불일치
- `indicator_matcher.py:90-99` "EPS 추이" rule
  - `indicator_type`: `'market_data'`
  - `prompt_builder.py:190-193` 카탈로그: `category: 'fundamental'`
  - **불일치 1건**

→ `match_indicators_for_premise()` 결과가 직접 저장될 경우(LLM PK 매칭 실패 path), Premise/Indicator 모델의 `indicator_type`이 카탈로그와 다른 값으로 기록될 위험이 있음. 단, `match_indicators_for_llm()`은 최종적으로 `_find_in_catalog(name)`을 거치므로 실제 저장은 카탈로그 값으로 덮어쓰임 (`indicator_matcher.py:332`). **위험도: 낮음(자체 복구됨)**, 다만 코드 일관성 관점에서 정리 필요.

---

## description 품질

- 카탈로그 항목 수: **64개**
- description 누락(빈 문자열 또는 미정의): **0개**
- description 길이 < 10자: **0개**
- 최단 description: id=14 "코스닥 지수" — `"한국 중소형 성장주 시장 지수."` (16자)
- 평균 description 길이: 약 35~40자 (감각치). 모든 항목이 "지표 정의 + 시장적 의미"의 두 문장 패턴을 따름.

> 비고: `get_indicator_description()` (`prompt_builder.py:351`)는 정확 매칭 후 접두사 매칭 (`"EPS 추이 (META)"` 같은 LLM 출력 포맷) 폴백을 가지고 있어 description 조회 안정성이 확보됨.

품질 이슈 없음. ✅

---

## keyword_rules 고아 (BE)

### A. BE `KEYWORD_RULES` (`indicator_matcher.py:12-154`) → 카탈로그 참조 매핑
| 룰 키워드 그룹 | 참조 지표명 | 카탈로그 매칭 |
|---------------|------------|--------------|
| 외국인/외인/순매수/순매도/foreign | `외국인 순매수 추이` | ✅ id=1 |
| 금리/연준/FOMC/fed/기준금리 | `미국 기준금리 (Fed Funds Rate)`, `미국 10년 국채 금리` | ✅ id=6, id=7 |
| VIX/공포/변동성 | `VIX (공포지수)` | ✅ id=8 |
| 환율/달러/원달러/USD/KRW | `원/달러 환율` | ✅ id=9 |
| RSI/MACD/기술적/과매수 | `RSI (14일)` | ✅ id=10 |
| 센티먼트/여론/뉴스/심리 | `뉴스 센티먼트` | ✅ id=11 |
| 실적/EPS/매출/영업이익/PER | `EPS 추이` | ✅ id=5 (단, `indicator_type` 불일치 — 위 §3) |
| 기관/연기금/보험/자산운용 | `기관 순매수 추이` | ✅ id=2 |
| S&P/S&P500/나스닥/NASDAQ/다우 | `S&P 500` | ✅ id=3 |
| 코스피/KOSPI | `KOSPI 지수` | ✅ id=4 |
| 선거/정치/정책 | `VIX (공포지수)`, `KOSPI 지수` | ✅ id=8, id=4 |

**고아 룰(카탈로그에 없는 지표를 참조하는 룰): 0건** ✅

### B. 카탈로그 ↔ BE 룰 커버리지 갭 (역방향)
BE `KEYWORD_RULES`가 참조하는 카탈로그 항목은 **11개** (id 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11). 나머지 **53개 카탈로그 항목은 BE 키워드 룰에 노출되지 않음.**

특히 영향 큰 미커버 영역:
- **원자재 전부 (id 20~24)**: "유가", "금", "구리", "천연가스" 같은 흔한 키워드에 무대응
- **암호화폐 (id 25, 26)**: "비트코인", "이더리움", "코인" 무대응
- **거시 고용/물가/성장 (id 31~36)**: "CPI", "인플레", "실업률", "GDP", "주택" 무대응
- **밸류에이션·재무체질 전부 (id 50~73, 단 5/57 제외)**: "PBR", "ROE", "ROA", "부채비율", "FCF", "배당", "ROIC", "EV/EBITDA" 등 모두 무대응
- **기술 보조지표 (id 40~47)**: "스토캐스틱", "볼린저", "ATR", "OBV", "SMA", "EMA" 무대응
- **지수 일부 (id 12~16, 30, 37~39)**: "NASDAQ", "다우", "코스닥", "니케이", "항셍", "2년 국채", "DXY" 등 무대응

→ 결과: BE의 `match_indicators_for_premise()` 1단계(키워드)에서 90% 이상의 케이스가 누락되어, 2단계 `match_by_gemini()`로 폴백되거나 빈 배열을 반환함.

또한 **`match_indicators_for_llm()` (`indicator_matcher.py:271-329`)는 `match_by_gemini` fallback을 의도적으로 제거**하고 키워드 룰만 사용함. 이는 LLM 환각 방지 목적(메모리 `feedback_llm_indicator_hallucination.md` 참조). 그러나 그 결과, LLM이 `indicator_db_id`를 누락한 케이스에서 BE 텍스트 매칭이 11개 지표만 커버하는 한계가 직접 노출된다.

### C. FE `KEYWORD_INDICATOR_MAP` (`AddIndicatorSheet.tsx:109-139`)
- 룰 수: **26개**
- 참조 ID 총 합집합: 60+ (사실상 카탈로그 대부분 커버)
- **고아 ID (카탈로그에 없는 ID 참조): 0건** ✅ — 모든 ID가 BE 카탈로그에 존재

> FE가 BE 키워드 매칭보다 5배 이상 풍부함. 사용자 입장에서는 같은 전제 텍스트로 FE에서는 풍부한 추천이 보이지만, BE LLM 단계의 자동 매칭은 빈약함. 이 격차가 사용자 혼란의 원인이 될 수 있음.

### D. 권장 정리
1. BE `KEYWORD_RULES`를 FE `KEYWORD_INDICATOR_MAP`과 1:1로 동기화 — FE는 ID 기반, BE는 name 기반이라는 비대칭부터 해소 (BE도 ID 기반으로 통일 권장).
2. `indicator_matcher.py:96` "EPS 추이" rule의 `indicator_type`을 `'fundamental'`로 정정.
3. 단일 소스화: 키워드 룰을 한 곳(예: `prompt_builder.py` 카탈로그 항목의 `keywords` 필드)에 두고 BE/FE가 동일 JSON을 fetch하는 것이 이상적. 현재는 "지표 카탈로그 BE/FE 동기화" 메모리(`feedback_indicator_catalog_sync.md`)가 명시하듯 3곳 분산 미러 상태.

---

## data_params 형식

### A. 카탈로그 내 `data_params` 패턴 분류 (BE)
| 패턴 | 예시 ID | 형식 |
|------|---------|------|
| FMP 시계열 (지수/원자재/암호화폐/환율) | 3, 8, 9, 20, 25, 39 등 | `{'symbol': '<ticker>'}` |
| FMP 수급/실적 메트릭 | 1, 2, 5 | `{'metric': '<key>'}` |
| FRED 시리즈 | 6, 7, 30, 31, 32, 33, 34, 35, 36, 37, 38 | `{'series_id': '<FRED ID>'}` |
| FMP 기술적 지표 | 10, 40~47 | `{'indicator': '<NAME>', 'period': N, ...}` |
| FMP key-metrics-ttm (단순) | 51, 54, 55, 56, 57 | `{'metric': '<fieldTTM>'}` |
| FMP key-metrics-ttm (변환 필요) | 50, 52, 53 | `{'metric': '<fieldTTM>', 'inverse'\|'scale_multiplier': ..., 'audit_note': '...'}` |
| FMP /financial-growth (변환) | 58 | `{'metric': 'growthRevenue', 'endpoint': 'financial-growth', 'scale_multiplier': 100, 'audit_note': '...'}` |
| metrics 시스템 (quarterly_metric_fetcher) | 60~73 | `{'metric_code': '<snake_case>'}` (data_source='metrics') |
| 뉴스 센티먼트 | 11 | `{}` (data_source='news_sentiment') |

### B. 변환 메타 적용 현황 (common-bugs #14 회귀 방지)
- ✅ id=50 PER: `peRatioTTM` 미존재 → `earningsYieldTTM` + `inverse: True` + `audit_note`
- ✅ id=52 ROE: 0~1 스케일 → `scale_multiplier: 100` + `audit_note`
- ✅ id=53 ROA: 동일 패턴 적용 + `audit_note`
- ✅ id=58 매출성장률 YoY: `key-metrics-ttm`에 없음 → `/financial-growth/` endpoint 명시 + `growthRevenue` 필드 + `scale_multiplier: 100`
- 비고: id=58은 `endpoint` 키가 다른 항목에는 없는 고유 필드. fetcher 측에서 `endpoint` 키를 인식하는지 별도 검증 필요(이 감사 범위 밖).

### C. BE `KEYWORD_RULES` vs 카탈로그 — `data_params` 형식 비교
키워드 룰에 정의된 11개 항목의 `data_params`는 카탈로그와 모두 동일한 형식·값. ✅
- 단, 룰 측에는 `inverse`/`scale_multiplier`/`endpoint` 같은 변환 메타가 **없음** (룰은 11개 모두 변환 불필요 항목만 커버하므로 현재는 문제 없음).
- 향후 PER/ROE 같은 변환 필요 지표를 키워드 룰에 추가할 경우, 룰만 보고 fetch하면 변환 누락 가능. → 항상 `_find_in_catalog(name)`을 거쳐 카탈로그 메타를 덮어쓰는 현재 패턴을 유지해야 함 (`indicator_matcher.py:316-322` 이미 적용됨).

### D. FE 측 `data_params` 표현
FE는 `data_params`를 보유하지 않음 (UI 추천/표시만 담당). 실제 fetch는 BE가 카탈로그 메타로 수행하므로 형식 차이는 발생할 수 없음. ✅

### E. 카테고리별 형식 일관성 위험
- `data_source='fmp'` 안에 5가지 서로 다른 `data_params` 키 패턴(`symbol`, `metric`, `metric+inverse`, `metric+scale_multiplier`, `metric+endpoint`, `indicator+period`)이 공존. fetcher가 `data_source`만 보고 분기하면 실수 위험 큼.
- 권장: `data_source`를 `fmp_quote`, `fmp_key_metrics_ttm`, `fmp_growth`, `fmp_technical` 처럼 세분화하거나, `data_params`에 명시적 `fetch_kind` 키를 두는 방향 고려 (현재 `audit_note`로만 표시되어 휴먼 리뷰에 의존).

---

## 부록: 카탈로그 추가/삭제 시 체크리스트
새 지표 추가 시 동시 업데이트 필요 위치 (메모리 `feedback_indicator_catalog_sync.md`와 합치):
1. `thesis/services/prompt_builder.py` — `INDICATOR_CATALOG` 본문 + `INDICATOR_FREQUENCY` 매핑
2. `frontend/components/thesis/AddIndicatorSheet.tsx` — `INDICATOR_CATALOG` 미러 + (선택) `KEYWORD_INDICATOR_MAP` 룰 추가 + `categoryOrder` 확인
3. `thesis/services/indicator_matcher.py` — `KEYWORD_RULES` 신규 룰 (변환 필요 지표면 룰 데이터에 변환 메타 넣지 말고 이름 매칭 후 카탈로그 조회 유지)
4. (필요 시) `quarterly_metric_fetcher` 등 데이터 제공자 측 `metric_code` 또는 `endpoint` 처리 분기

---

## 우선순위별 액션 아이템
| 우선순위 | 항목 | 작업 |
|---------|------|------|
| P1 | BE 키워드 룰 커버리지 53개 갭 | FE `KEYWORD_INDICATOR_MAP` 26개 룰을 BE에도 포팅 (ID 기반) |
| P2 | "EPS 추이" `indicator_type` 불일치 | `indicator_matcher.py:96` `'market_data'` → `'fundamental'` |
| P3 | 키워드 룰 단일 소스화 | 카탈로그 항목에 `keywords: []` 필드를 두고 BE/FE가 같은 데이터 참조 |
| P4 | `data_source='fmp'` 다형성 정리 | `data_params`에 `fetch_kind` 키 도입 또는 `data_source` 세분화 |
| P4 | 결번 ID(17~19, 27~29, 48~49, 59) 정책 문서화 | 의도된 슬롯/폐기 여부 명시 |
