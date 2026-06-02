# 지표 카탈로그 동기화 감사 보고서

> **감사일**: 2026-06-02
> **범위**: INDICATOR_CATALOG (BE ↔ FE), KEYWORD_RULES, data_params 형식
> **유형**: 읽기 전용 감사 (코드 수정 없음)
> **대상 파일**:
> - BE 정의: `thesis/services/prompt_builder.py`
> - BE 후처리: `thesis/services/llm_postprocess.py`
> - BE 매칭: `thesis/services/indicator_matcher.py`
> - FE 표시: `frontend/components/thesis/AddIndicatorSheet.tsx`

---

## 요약 (동기화 상태)

| 검사 항목 | 상태 | 비고 |
|----------|------|------|
| 1. BE ↔ FE 항목 동기화 | ✅ **완전 일치** | id 64개 / name 64개 전부 일치, 불일치 0건 |
| 2. description 품질 | ✅ **양호** | 빈 항목 0, 10자 미만 0 (최단 17자) |
| 3. KEYWORD_RULES 고아 | ⚠️ **경미** | FE 고아 규칙 0건, 단 BE `indicator_type` 1건 불일치 |
| 4. data_params 형식 | ⚠️ **주의** | FMP 표준 필드 아님 4건(audit_note로 방어됨) + 한국 수급/지수 제공 의문 |

**종합 판정**: 🟢 동기화 자체는 건전. BE/FE 카탈로그가 ID·이름 기준 100% 정합하며 #14 회귀 방지 주석이 충실히 박혀 있음. 다만 (a) KEYWORD_RULES의 메타데이터 1건 불일치, (b) FMP 비표준 필드 의존성, (c) 한국 시장 데이터 제공 가능성은 운영 모니터링 필요.

---

## BE ↔ FE 불일치 목록

### 결과: 불일치 0건 ✅

- **BE 카탈로그** (`prompt_builder.py:14-310`): 64개 항목
- **FE 카탈로그** (`AddIndicatorSheet.tsx:15-91`): 64개 항목
- **BE에만 존재**: 없음
- **FE에만 존재**: 없음
- **id ↔ name 매핑**: 64개 전부 동일 (이름 표기까지 글자 단위 일치)

ID 집합 (정렬): `1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,20,21,22,23,24,25,26,30,31,32,33,34,35,36,37,38,39,40,41,42,43,44,45,46,47,50,51,52,53,54,55,56,57,58,60,61,62,63,64,65,66,67,68,69,70,71,72,73`

### 구조적 차이 (불일치 아님, 설계상 의도)

| 구분 | BE | FE |
|------|-----|-----|
| 카테고리 체계 | 5개 대분류 (`market_data`/`macro`/`technical`/`fundamental`/`sentiment`) | 17개 세분류 (`수급`/`주요 지수`/`원자재`/`암호화폐`/`금리`/`환율/변동성`/`고용/성장`/`물가/주택`/`기술적`/`펀더멘털`/`재무 체질`/`밸류에이션`/`성장`/`운영 효율`/`이익 품질`/`주주환원`/`심리`) |
| 보유 필드 | `data_source`, `data_params`, `support_direction`, `description` | `freq`(업데이트 주기), `category` |

- FE는 **표시 전용**이라 `data_params`/`data_source`/`support_direction`을 갖지 않음 → 의도된 설계.
- 단, **2곳에 카탈로그가 하드코딩 미러링**되어 있어 향후 항목 추가 시 양쪽을 동시에 수정해야 함 (메모리 `feedback_indicator_catalog_sync` 정책과 일치). 현재는 정합하나 구조적 drift 위험은 상존.

> 🔎 **drift 위험 지점**: FE 주석 `// INDICATOR_CATALOG 미러 (prompt_builder.py와 동기화)` (`AddIndicatorSheet.tsx:6`)가 단일 진실 소스 부재를 명시. 신규 지표 추가 PR에서 한쪽만 수정될 경우 침묵 누락 발생 가능.

---

## description 품질

### 결과: 전 항목 양호 ✅

- 총 description 수: **64개**
- 빈 description: **0건**
- 10자 미만: **0건**
- 최단 description: `한국 중소형 성장주 시장 지수.` (id 14, 17자)

모든 지표가 "지표 의미 + 투자 맥락" 2요소를 갖춘 충실한 설명을 보유. 예) id 23 구리 — *"구리 선물 가격. 경기 선행지표로 'Dr. Copper'라 불림."*

> 참고: FE 카탈로그(`AddIndicatorSheet.tsx`)에는 description 필드가 존재하지 않음. 사용자 노출 설명은 BE 프롬프트(`build_indicator_block`)와 LLM `why` 필드로 전달되는 구조이므로, FE description 부재는 품질 결함이 아님.

---

## keyword_rules 고아

### 1) FE `KEYWORD_INDICATOR_MAP` (`AddIndicatorSheet.tsx:109-139`) — 고아 0건 ✅

- 28개 규칙이 참조하는 모든 `indicatorIds`가 카탈로그에 존재 (고아 규칙 0건).
- **추천에서 한 번도 매칭되지 않는 카탈로그 항목 11개** (역(逆)고아 — 카탈로그에는 있으나 키워드 규칙이 닿지 못함):

  | id | 지표 | 비고 |
  |----|------|------|
  | 13 | 다우존스 | 키워드 규칙 미커버 (s&p/나스닥만 존재) |
  | 14 | 코스닥 지수 | 키워드 규칙 미커버 (kospi만 존재) |
  | 22 | 은 (Silver) | 키워드 규칙 미커버 (금/구리만 존재) |
  | 38 | 달러/유로 환율 | 키워드 규칙 미커버 (원달러/dxy만 존재) |
  | 41 | 스토캐스틱 %K | rsi/macd 규칙에만 묶임 (id 10,40) |
  | 42 | 볼린저 밴드 %B | 〃 |
  | 43 | ATR (평균진폭) | 〃 |
  | 44 | OBV (거래량 누적) | 〃 |
  | 45 | SMA 50일 | 〃 |
  | 46 | SMA 200일 | 〃 |
  | 47 | EMA 12일 | 〃 |

  → 이 11개는 "전제 관련 추천" 섹션에 자동 노출되지 않지만, **전체 카탈로그 목록에서는 수동 선택 가능**하므로 기능 결함은 아님. 추천 품질 개선 여지(특히 13/14/22/38은 1줄 규칙 추가로 커버 가능).

### 2) BE `KEYWORD_RULES` (`indicator_matcher.py:12-154`) — 고아 0건, 메타데이터 1건 불일치 ⚠️

- 11개 규칙이 참조하는 모든 `name`이 카탈로그에 존재 (이름 기반 매칭, `_find_in_catalog`로 최종 검증).
- **⚠️ `indicator_type` 불일치 1건**:

  | 항목 | KEYWORD_RULES (`indicator_matcher.py:95`) | INDICATOR_CATALOG (`prompt_builder.py:190`) |
  |------|------|------|
  | EPS 추이 (id 5) | `indicator_type: 'market_data'` | `category: 'fundamental'` |

  → 실적/EPS 키워드 룰(`indicator_matcher.py:90-99`)에서 EPS를 `market_data`로 분류. 카탈로그상 `fundamental`과 불일치.
  → 영향도: `match_indicators_for_llm`은 PK 우선 매칭 후 `_find_in_catalog`로 카탈로그 항목을 재조회하므로(`indicator_matcher.py:316`) **최종 저장 데이터는 카탈로그 값으로 덮어써져 실질 영향 낮음**. 단 `match_by_keywords` 직접 호출 경로(`match_indicators_for_premise`)에서는 룰의 `market_data`가 그대로 노출될 수 있음.

### 3) BE ↔ FE 키워드 규칙 커버리지 격차 (참고)

- BE `KEYWORD_RULES`: 11개 규칙 (이름 기반)
- FE `KEYWORD_INDICATOR_MAP`: 28개 규칙 (id 기반)
- FE가 BE보다 훨씬 풍부한 키워드 커버리지를 가짐 (재무 체질·밸류에이션·섹터 키워드 등). 두 매칭 엔진이 **독립적으로 운영**되며 규칙 동기화 의무는 없으나, 동일 전제 텍스트에 대해 BE/FE 추천 결과가 달라질 수 있음을 인지 필요.

---

## data_params 형식

### 1) FMP 표준 필드 아님 — audit_note로 방어됨 ⚠️ (4건)

`prompt_builder.py`에 #14 회귀 방지 주석과 변환 파라미터가 명시되어 있음. **이미 인지·방어된 항목**:

| id | 지표 | data_params | 형식 이슈 | 방어 |
|----|------|-------------|-----------|------|
| 50 | PER | `metric: earningsYieldTTM, inverse: True` | FMP key-metrics-ttm에 `peRatioTTM` 미존재 → PER = 1/earningsYield | `inverse` 플래그 + audit_note (`:196-201`) |
| 52 | ROE | `metric: returnOnEquityTTM, scale_multiplier: 100` | FMP가 0~1 비율로 반환 → ×100 필요 | `scale_multiplier` + audit_note (`:207-212`) |
| 53 | ROA | `metric: returnOnAssetsTTM, scale_multiplier: 100` | 동일 0~1 스케일 | `scale_multiplier` + audit_note (`:214-219`) |
| 58 | 매출성장률(YoY) | `metric: growthRevenue, endpoint: financial-growth, scale_multiplier: 100` | key-metrics-ttm에 없음, `/financial-growth/` 별도 엔드포인트 + 0~1 스케일 | `endpoint`+`scale_multiplier`+audit_note (`:239-245`) |

> 권장(주석에 기재됨): id 58은 `data_source='metrics'`(quarterly_metric_fetcher의 `revenue_growth_yoy` RATIO_METRICS)로 분기하는 것이 표준. 현재는 FMP 직접 호출 + 변환으로 운영.

### 2) data_source별 data_params 스키마 (정상 — 형식 일관성 확인)

| data_source | data_params 키 | 예시 | 항목 수 |
|-------------|---------------|------|---------|
| `fmp` (symbol) | `symbol` | `{'symbol': '^GSPC'}` | 지수/원자재/암호화폐/환율 다수 |
| `fmp` (metric) | `metric` (+`inverse`/`scale_multiplier`/`endpoint`/`audit_note`) | `{'metric': 'eps'}` | 펀더멘털 |
| `fmp` (indicator) | `indicator`, `period`(+`fast`/`slow`/`signal`) | `{'indicator': 'RSI', 'period': 14}` | 기술적 9건 |
| `fred` | `series_id` | `{'series_id': 'FEDFUNDS'}` | 거시 다수 |
| `metrics` | `metric_code` | `{'metric_code': 'roic'}` | 재무 체질 14건 |
| `news_sentiment` | (없음) | `{}` | id 11 |

→ data_source별 키 스키마가 일관됨. 형식 혼선 없음.

### 3) ⚠️ 데이터 제공 가능성 의문 (FMP 실제 응답 미검증 — 운영 모니터링 권장)

다음 항목은 코드상 `data_source='fmp'`이나 **FMP가 실제로 제공하는지 본 감사 범위(정적 분석)에서 확정 불가**. FMP는 미국 시장 중심이므로 잠재적 형식/제공 불일치 위험:

| id | 지표 | data_params | 의문점 |
|----|------|-------------|--------|
| 1 | 외국인 순매수 추이 | `{'metric': 'foreign_net_buy'}` | `foreign_net_buy`는 FMP 표준 메트릭 아님. 한국 외국인 수급 데이터를 FMP가 제공하는지 불명 |
| 2 | 기관 순매수 추이 | `{'metric': 'institutional_net_buy'}` | 동일 — `institutional_net_buy` FMP 표준 아님 |
| 4 | KOSPI 지수 | `{'symbol': '^KS11'}` | FMP 한국 지수 심볼 제공 여부 검증 필요 |
| 14 | 코스닥 지수 | `{'symbol': '^KQ11'}` | 동일 |
| 9 | 원/달러 환율 | `{'symbol': 'USDKRW'}` | FMP 환율 심볼 형식(`USDKRW` vs `USD/KRW`) 검증 필요 |
| 39 | 달러 인덱스 | `{'symbol': 'DX-Y.NYB'}` | 심볼 형식 FMP 호환성 검증 필요 |

→ 이들은 **실제 fetch 단계에서만 검증 가능**. id 1/2의 `foreign_net_buy`/`institutional_net_buy`는 KEYWORD_RULES(`indicator_matcher.py:18,104`)에도 동일하게 정의되어 있어, 만약 FMP 미제공이면 두 곳 모두 영향.

---

## 권장 후속 조치 (우선순위)

| 우선순위 | 항목 | 조치 | 근거 |
|---------|------|------|------|
| P1 | id 1/2 외국인·기관 순매수 FMP 제공 검증 | 실제 fetch 테스트로 데이터 수신 여부 확인 | 미제공 시 해당 지표 추적 전면 실패 |
| P2 | id 5 EPS `indicator_type` 불일치 | `indicator_matcher.py:95` `market_data`→`fundamental` 정정 검토 | 카탈로그 정합성 (영향도 낮으나 혼선 원인) |
| P3 | id 4/14/9/39 FMP 심볼 형식 검증 | 한국 지수·환율·DXY 심볼 fetch 확인 | 형식 불일치 시 조용히 빈 데이터 |
| P3 | FE 추천 미커버 11개 지표 | id 13/14/22/38에 키워드 규칙 1줄씩 추가 검토 | 추천 품질 향상 (기능 결함 아님) |
| P4 | 카탈로그 단일 소스화 | BE/FE 2곳 미러 → contracts/ 또는 codegen 검토 | drift 예방 (장기) |

---

## 부록: 검증 방법

- **항목 동기화**: 정규식으로 BE `prompt_builder.py` INDICATOR_CATALOG 블록과 FE `AddIndicatorSheet.tsx` 카탈로그 블록에서 `id`/`name` 추출 후 집합 비교 → 64=64, 차집합 0, 이름 불일치 0 확인.
- **description 품질**: BE 64개 description 길이 측정 → 빈 항목 0, 10자 미만 0.
- **keyword_rules**: FE 28개 규칙의 `indicatorIds` ⊆ 카탈로그 확인(고아 0), 역으로 미참조 카탈로그 11개 식별. BE 11개 규칙의 `name` ⊆ 카탈로그 확인, `indicator_type` 대조.
- **data_params**: data_source별 키 스키마 수동 분류 + audit_note 주석 추적.
- **한계**: 본 감사는 정적 분석. FMP/FRED 실제 API 응답은 검증하지 않음 (P1/P3 항목은 런타임 검증 필요).
