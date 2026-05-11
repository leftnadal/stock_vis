# 지표 카탈로그 동기화 감사 보고서

**감사 일자**: 2026-05-07
**감사자**: 자동 야간 시스템 (read-only)
**감사 범위**:
- BE 정의: `thesis/services/prompt_builder.py:14-294` (`INDICATOR_CATALOG`)
- BE 후처리: `thesis/services/llm_postprocess.py:82-93` (catalog 검증)
- BE 매칭: `thesis/services/indicator_matcher.py:12-154` (`KEYWORD_RULES`)
- FE 표시: `frontend/components/thesis/AddIndicatorSheet.tsx:15-91` (`INDICATOR_CATALOG`)
- FE 매칭: `frontend/components/thesis/AddIndicatorSheet.tsx:109-139` (`KEYWORD_INDICATOR_MAP`)

---

## 요약 (동기화 상태)

| 항목 | 상태 | 비고 |
|------|------|------|
| BE/FE 지표 ID 일치 | ✅ 53/53 ID 완전 일치 | 누락된 ID 없음 |
| BE/FE 빈도(freq) 일치 | ✅ 53/53 일치 | INDICATOR_FREQUENCY ↔ FE freq |
| description 필드 품질 | ✅ BE 53/53 모두 작성 | FE는 description 필드 자체 없음 |
| FE 누락 메타데이터 | ⚠️ description, support_direction, data_source, data_params 없음 | FE는 표시 정보만 미러링 |
| BE keyword_rules 커버리지 | ❌ 53개 중 11개만 매칭 (20.7%) | 42개 지표는 텍스트 매칭 불가 |
| FE keyword_map 커버리지 | ⚠️ FE 53개 중 11개 catalog-only (수동 추가만) | BE 대비 풍부 |
| keyword_rules 고아 규칙 | ✅ BE/FE 모두 0건 | 모든 지표명이 catalog에 존재 |
| BE/FE keyword 룰 분기 | ❌ 양쪽 매칭 결과가 다름 | 동일 입력에 다른 추천 |
| data_params 형식 일관성 | ⚠️ FMP `metric` 키 비표준 가능 | 4개 잠재 위험 식별 |

**핵심 위험 (우선순위 순)**:
1. **BE keyword_rules가 매우 협소**: 53개 중 11개만 매칭. LLM이 PK 없이 추천하면 fallback이 거의 작동하지 않음 (`indicator_matcher.py:307` 주석 — "match_by_gemini fallback 제외" 정책으로 더 좁아짐).
2. **BE/FE keyword 매핑 분기**: BE 11개 룰 vs FE 28개 룰. 동일 전제 텍스트에 BE/FE가 다른 추천을 내림 (사용자 혼란 가능).
3. **data_source가 'metrics'인 지표(id 60-73)**: `metric_code` 사용 — validation/metrics 시스템 의존. 그 외 카탈로그 항목과 데이터 흐름 분리.
4. **FE 카테고리 ↔ BE 카테고리 분기**: BE 5개(`market_data/macro/technical/fundamental/sentiment`) vs FE 17개(세분화). 둘은 독립 진화 중.

---

## BE ↔ FE 불일치 목록

### 지표 ID 비교 (양쪽에 등장하는 ID)

**BE (`prompt_builder.py:14-294`)**:
```
1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16,
20, 21, 22, 23, 24, 25, 26,
30, 31, 32, 33, 34, 35, 36, 37, 38, 39,
40, 41, 42, 43, 44, 45, 46, 47,
50, 51, 52, 53, 54, 55, 56, 57, 58,
60, 61, 62, 63, 64, 65, 66, 67, 68, 69, 70, 71, 72, 73
```
총 53개

**FE (`AddIndicatorSheet.tsx:15-91`)**: 동일한 53개 ID

| 분류 | BE에만 | FE에만 | 결과 |
|------|--------|--------|------|
| 지표 ID | (없음) | (없음) | ✅ 완전 일치 |
| 지표 이름 | (없음) | (없음) | ✅ 완전 일치 (한글명까지 동일) |

### 메타데이터 필드 차이

| 필드 | BE | FE | 동기화 위험 |
|------|----|----|------|
| `id` | ✅ | ✅ | — |
| `name` | ✅ | ✅ | — |
| `category` | ✅ (5종) | ✅ (17종, 다른 체계) | ⚠️ 분류 체계 분기 |
| `data_source` | ✅ | ❌ | 정보 부재 |
| `data_params` | ✅ | ❌ | 정보 부재 |
| `support_direction` | ✅ | ❌ | FE에서 방향성 미표시 |
| `description` | ✅ (53/53) | ❌ | FE 사용자가 의미 모름 |
| `freq` (업데이트 주기) | BE 별도 dict (`INDICATOR_FREQUENCY`) | ✅ 항목 내 | ✅ 값 일치 (53/53) |

**참고**: 다른 곳에서 카탈로그 미러링 필요할 수 있는 지점은 발견되지 않음. `tests/unit/thesis/test_llm_builder.py:144-149`는 BE만 검증하며 FE 미러는 검증하지 않음 → 자동 검증 부재.

### 카테고리 매핑 분기

| BE category | FE category로 분산 |
|-------------|-----------------|
| `market_data` | `수급`, `주요 지수`, `원자재`, `암호화폐` (4분할) |
| `macro` | `금리`, `환율/변동성`, `고용/성장`, `물가/주택` (4분할) |
| `technical` | `기술적` (1:1) |
| `fundamental` (id 5, 50–58) | `펀더멘털` (1:1) |
| `fundamental` (id 60–73) | `재무 체질`, `밸류에이션`, `성장`, `운영 효율`, `이익 품질`, `주주환원` (6분할) |
| `sentiment` | `심리` (1:1) |

**위험**: BE category 변경 시 FE에서 누락 위험 — 동일 카테고리로 묶인 지표가 다른 그룹에 배치되어 사용자 발견성 저하.

---

## description 품질

### 빈 description

| 결과 | 건수 |
|------|------|
| 빈 description | **0건** |
| 10자 미만 description | **0건** |

모든 53개 항목이 충분한 설명을 가짐. 가장 짧은 것도 25자 이상.

### 가장 짧은 description (참고용)

| ID | 지표 | description | 길이 |
|----|------|-------------|------|
| 14 | 코스닥 지수 | "한국 중소형 성장주 시장 지수." | 16자 (한글 기준 짧지만 명확) |
| 4 | KOSPI 지수 | "한국 유가증권시장 전체 종목 시가총액 가중 지수." | 26자 |
| 22 | 은 (Silver) | "은 현물 가격(USD/oz). 산업 수요와 안전자산 이중 역할." | 32자 |

→ 모두 의미 전달 충분. **품질 이슈 없음**.

### FE 미러는 description 자체 부재

FE `AddIndicatorSheet.tsx:7-13`의 타입은 `{id, name, category, freq}`만 노출 — 사용자가 지표 의미를 보지 못함. 백엔드의 `_INDICATOR_NAME_TO_DESC` (`prompt_builder.py:332`)와 `get_indicator_description()` (`prompt_builder.py:335-345`)는 LLM 프롬프트에만 사용되고 FE에 전달되지 않음.

→ **개선 여지**: FE 카탈로그에 description 필드 추가하거나 BE 엔드포인트로 메타데이터 제공 (현재 분리된 미러는 동기화 부담).

---

## keyword_rules 고아

### BE `KEYWORD_RULES` (`indicator_matcher.py:12-154`)

총 11개 룰, 11개 고유 indicator 이름 참조:

| KEYWORD_RULES 내 이름 | INDICATOR_CATALOG ID | 매칭 |
|---------------------|---------------------|------|
| 외국인 순매수 추이 | id 1 | ✅ |
| 미국 기준금리 (Fed Funds Rate) | id 6 | ✅ |
| 미국 10년 국채 금리 | id 7 | ✅ |
| VIX (공포지수) | id 8 | ✅ |
| 원/달러 환율 | id 9 | ✅ |
| RSI (14일) | id 10 | ✅ |
| 뉴스 센티먼트 | id 11 | ✅ |
| EPS 추이 | id 5 | ✅ |
| 기관 순매수 추이 | id 2 | ✅ |
| S&P 500 | id 3 | ✅ |
| KOSPI 지수 | id 4 | ✅ |

**고아(catalog에 없는 이름) 0건**. 그러나 KEYWORD_RULES는 `id` 필드를 갖지 않고 이름으로만 매핑됨 — 향후 카탈로그 이름 변경 시 깨질 수 있음 (`_find_in_catalog()` `indicator_matcher.py:332-338`이 정확 일치만 검사).

### BE 매칭 커버리지 부족

INDICATOR_CATALOG 53개 중 KEYWORD_RULES가 매칭하는 것은 11개 (id 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11). 나머지 42개 지표(NASDAQ, 다우, 코스닥, 니케이, 항셍, 금/은/구리/천연가스, 비트코인/이더리움, 미국 2년/30년 모기지, 달러/유로/DXY, 실업률/NFP/GDP/산업생산, CPI/주택, MACD/스토캐스틱/볼린저/ATR/OBV/SMA/EMA, PER/PBR/ROE/ROA/부채/FCF/배당/영업이익률/매출성장, 재무체질 14개)는 **텍스트 매칭으로 추천되지 않음**.

`indicator_matcher.py:307` 주석 참조:
> "(match_by_gemini fallback은 카탈로그에 없는 환각 지표를 생성하므로 제외)"

→ LLM이 PK를 빠뜨리거나 잘못된 ID를 주면, BE가 자동 매칭으로 보충할 수 있는 여지가 매우 좁다.

### FE `KEYWORD_INDICATOR_MAP` (`AddIndicatorSheet.tsx:109-139`)

총 28개 룰, 사용 ID 53개 중 42개 커버:

**FE 룰에 등장하지만 catalog에 없는 ID**: **0건** (고아 0건)

**FE catalog에 있지만 어떤 룰에도 등장 않는 ID** (수동 추가 전용):
- id 13 (다우존스), 14 (코스닥), 22 (은), 38 (달러/유로), 41 (스토캐스틱), 42 (볼린저), 43 (ATR), 44 (OBV), 45 (SMA50), 46 (SMA200), 47 (EMA12)
- 11개 — 사용자가 검색해도 자동 추천되지 않음 (수동 카탈로그 탐색 필요).

### BE/FE 룰 분기 (동일 입력 → 다른 추천)

예시: 사용자 전제 "비트코인 가격 상승"
- BE: 매칭 룰 없음 → 빈 추천
- FE: id 25, 26 추천 ('비트코인 BTC', '이더리움 ETH')

예시: 사용자 전제 "유가 상승"
- BE: 매칭 룰 없음 → 빈 추천
- FE: id 21 추천 ('원유 WTI')

예시: 사용자 전제 "EPS 분기 호조"
- BE: id 5 (EPS 추이) 1개
- FE: id 5, 50, 57, 58, 60, 61, 69 (7개)

→ **백/프론트 추천 결과가 일관되지 않음**. 사용자가 BE의 "전제 → 지표 자동 매칭" 결과와 FE의 "지표 추가 시트 추천"을 비교하면 불일치를 직접 체감 가능.

---

## data_params 형식

### BE 정의 형식 패턴

| data_source | 키 패턴 | 예시 |
|-------------|---------|------|
| `fmp` (지수/원자재/암호화폐/환율) | `{symbol: ...}` | `^GSPC`, `GCUSD`, `BTCUSD`, `USDKRW` |
| `fmp` (수급/펀더멘털) | `{metric: ...}` | `foreign_net_buy`, `eps`, `peRatioTTM` |
| `fmp` (기술지표) | `{indicator, period, ...}` | `RSI`, `MACD` (fast/slow/signal 추가) |
| `fred` | `{series_id: ...}` | `FEDFUNDS`, `DGS10` |
| `news_sentiment` | `{}` (빈) | id 11 |
| `metrics` | `{metric_code: ...}` | `gross_margin`, `roic` (validation/metrics 시스템) |

### 잠재적 형식/필드 불일치 위험

| ID | 지표 | 정의된 data_params | 위험 |
|----|------|---------------------|------|
| 1 | 외국인 순매수 추이 | `{metric: 'foreign_net_buy'}` | ❌ FMP 표준 엔드포인트 아님. KRX/Korean source 필요. 실제 데이터 제공자 미확인 |
| 2 | 기관 순매수 추이 | `{metric: 'institutional_net_buy'}` | ❌ 동일 — FMP 표준 엔드포인트 아님 |
| 5 | EPS 추이 | `{metric: 'eps'}` | ⚠️ FMP에 단일 'eps' metric 키 없음 — 보통 `/historical/earning_calendar` 또는 `key-metrics-ttm.epsTTM` |
| 39 | 달러 인덱스 (DXY) | `{symbol: 'DX-Y.NYB'}` | ⚠️ Yahoo Finance 형식. FMP는 보통 `DXY` 직접 또는 forex 6쌍 합성. FMP API 호환성 미확인 |
| 50 | PER | `{metric: 'peRatioTTM'}` | ⚠️ common-bugs.md #14 참조: FMP는 `earningsYieldTTM` 역수 = PE. `peRatioTTM` 직접 필드 존재 여부 사이트 변경에 따라 가변 |
| 52 | ROE | `{metric: 'returnOnEquityTTM'}` | ⚠️ common-bugs.md #14: ROE = `returnOnEquityTTM` × 100 (소수→%). 단순 metric 키만으로는 후처리 누락 가능 |
| 55 | 잉여현금흐름 (FCF) | `{metric: 'freeCashFlowTTM'}` | ⚠️ FMP `key-metrics-ttm`에 단순 `freeCashFlowTTM` 필드 존재 여부 미확정 — 일부 plan에 따라 다름 |
| 57 | 영업이익률 | `{metric: 'operatingProfitMarginTTM'}` | ⚠️ FMP는 `operatingProfitMarginTTM` 또는 `operatingMarginTTM` — 정확 키 확인 필요 |
| 58 | 매출성장률 (YoY) | `{metric: 'revenueGrowthYoY'}` | ❌ FMP 표준 single-field 아님 — `income-statement` 시계열 직접 비교 또는 `/financial-growth` 엔드포인트 필요 |
| 60–73 | 재무 체질 14개 | `{metric_code: ...}` | ✅ data_source가 `'metrics'` (validation/metrics 별도 시스템). FMP 직접 호출 아님 — 동기화 책임이 metrics 모듈로 이전됨 |

### data_params 결론

- 지수/원자재/환율/암호화폐: FMP `{symbol}` 형식은 표준 — 정상 (단, DXY=`DX-Y.NYB`만 위험).
- FRED `{series_id}`: ✅ 표준 형식.
- FMP `{metric}` 키: **비표준이며 실제 endpoint 매핑 로직이 별도 어딘가에 존재해야 함**. 본 카탈로그 정의만으로는 호출 불가능 — Processor/Service 계층의 매핑 코드와의 합의가 필요. 본 감사로는 호출부 확인 안 됨.
- `metric_code` (id 60–73): metrics 시스템 의존성. metrics 시스템에서 같은 코드 정의 일치 여부 별도 감사 필요.

---

## 부록: 주요 파일 위치

| 항목 | 경로 | 라인 |
|------|------|------|
| BE INDICATOR_CATALOG | `thesis/services/prompt_builder.py` | 14-294 |
| BE INDICATOR_FREQUENCY | `thesis/services/prompt_builder.py` | 305-326 |
| BE catalog 검증 (postprocess) | `thesis/services/llm_postprocess.py` | 82-93 |
| BE KEYWORD_RULES | `thesis/services/indicator_matcher.py` | 12-154 |
| BE catalog 이름 검색 | `thesis/services/indicator_matcher.py` | 332-338 |
| BE catalog 단위 테스트 | `tests/unit/thesis/test_llm_builder.py` | 144-149 |
| FE INDICATOR_CATALOG 미러 | `frontend/components/thesis/AddIndicatorSheet.tsx` | 15-91 |
| FE KEYWORD_INDICATOR_MAP | `frontend/components/thesis/AddIndicatorSheet.tsx` | 109-139 |

---

## 권고 사항 (감사 외 참고용, 본 감사는 read-only)

1. **BE/FE 카탈로그 동기화 자동화**: 현재 두 파일을 사람이 수동 동기화. BE에서 JSON 직렬화 후 FE에서 import하거나, BE 엔드포인트(`GET /api/v1/thesis/indicator-catalog/`)로 단일 소스화.
2. **BE KEYWORD_RULES 확장**: 53개 중 11개만 커버 — 최소 FE 28개 룰 수준으로 확장하거나 BE/FE 단일 룰 소스화.
3. **테스트 강화**: `test_indicator_catalog_has_all_fields`에 `description` 필드 + FE 미러 동기화 검증 추가.
4. **data_params `metric` 키 매핑 표 문서화**: FMP raw 응답 필드와의 매핑이 어디에 있는지 명시 (현재 외부에서 추적 어려움).
5. **`DX-Y.NYB` 심볼 검증**: FMP 호출 실패 가능성 — 실제 데이터 가져오기 테스트 필요.
