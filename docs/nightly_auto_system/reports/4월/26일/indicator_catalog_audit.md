# 지표 카탈로그 동기화 감사 보고서

- 감사일: 2026-04-26
- 모드: 읽기 전용 (코드 수정 없음)
- 대상 파일
  - BE 정의: `thesis/services/prompt_builder.py` (`INDICATOR_CATALOG`, `INDICATOR_FREQUENCY`, `CATEGORY_LABELS`)
  - BE 후처리: `thesis/services/llm_postprocess.py` (`get_indicator_by_id` 사용)
  - BE 매칭: `thesis/services/indicator_matcher.py` (`KEYWORD_RULES`, `_find_in_catalog`)
  - FE 표시: `frontend/components/thesis/AddIndicatorSheet.tsx` (`INDICATOR_CATALOG`, `KEYWORD_INDICATOR_MAP`)

## 요약 (동기화 상태)

| 항목 | 상태 | 비고 |
|------|------|------|
| BE/FE 지표 ID 집합 | ✅ 동기화 | 양쪽 모두 64개 ID, 누락/추가 없음 |
| BE/FE 지표 표시 이름 | ⚠️ 4건 불일치 (회귀) | id 6, 7, 30, 54 — 25일 보고서와 동일, 미해결 |
| BE/FE 카테고리 라벨 | ⚠️ 정책 차이 | BE 5개 대분류 vs FE 17개 세분류 — 매핑 표 부재 |
| description 필드 | ✅ 양호 | 64개 모두 채움. 최단 14자 (id 14), 빈 값/10자 미만 없음 |
| FE description 보유 | ❌ 미보유 | FE `CatalogIndicator`에 description 필드 자체가 없음 |
| `KEYWORD_RULES` (BE) ↔ CATALOG | ✅ 고아 없음 | 11개 룰 모두 CATALOG의 지표 이름과 정확 매칭 |
| `KEYWORD_INDICATOR_MAP` (FE) ↔ CATALOG | ✅ 고아 없음 | 28개 룰이 참조하는 모든 ID가 FE CATALOG에 존재 |
| BE/FE 키워드 룰 커버리지 | ❌ 큰 비대칭 (회귀) | BE 11개 룰 / FE 28개 룰 — `match_by_gemini` 제거 이후 BE 키워드 추천 풀이 11개 ID로 협소 |
| `data_params` ↔ FMP API 필드명 | ❌ 일부 불일치 (회귀) | id 50, 52, 53, 58 등 common-bugs #14 패턴 미반영 |
| 커스텀 metric 키 (`foreign_net_buy` 등) | ⚠️ 핸들러 검증 필요 | FMP 표준 필드 아님, endpoint 라우팅 메타데이터 부재 |

총평: **ID 수준의 동기화는 안정적**(64↔64)이지만, ① 표시 이름 4건 불일치, ② BE 키워드 룰 커버리지가 FE의 약 39% 수준에 머무름, ③ `data_params`가 FMP 실응답 필드와 어긋난 항목이 다수 존재해 common-bugs #14 회귀 위험이 누적되고 있다. 25일 보고서 대비 **카탈로그·룰·data_params 모두 변동 없음** — 즉 기존 권고 P0 항목들이 미해결 상태로 유지된다.

---

## BE ↔ FE 불일치 목록

### A. 지표 ID — 누락/추가
없음. BE 64개와 FE 64개의 ID 집합이 정확히 일치한다.

```
BE only: (없음)
FE only: (없음)
공통:    1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16,
         20, 21, 22, 23, 24, 25, 26,
         30, 31, 32, 33, 34, 35, 36, 37, 38, 39,
         40, 41, 42, 43, 44, 45, 46, 47,
         50, 51, 52, 53, 54, 55, 56, 57, 58,
         60, 61, 62, 63, 64, 65, 66, 67, 68, 69, 70, 71, 72, 73
```

### B. 지표 표시 이름 — 4건 불일치 (25일 보고서와 동일, 미해결)

| id | BE 이름 (`prompt_builder.py`) | FE 이름 (`AddIndicatorSheet.tsx`) | 영향 |
|----|------|------|------|
| 6 | `미국 기준금리 (Fed Funds Rate)` | `미국 기준금리` | LLM 프롬프트/저장값과 FE 카드 라벨이 다름. `_find_in_catalog(name)` 정확 매칭 시 우회될 가능성 |
| 7 | `미국 10년 국채 금리` | `미국 10년 국채` | 동상. `get_indicator_description()`의 접두사 매칭은 BE→이름 변형 단방향만 안전, FE 표시명 → BE 탐색은 깨짐 |
| 30 | `미국 2년 국채 금리` | `미국 2년 국채` | 동상 |
| 54 | `부채비율 (Debt/Equity)` | `부채비율 (D/E)` | 동상. 사용자가 "Debt/Equity"로 검색 시 두 표시 사이에 단절 |

영향 범위:
- `prompt_builder.py:335-345` `get_indicator_description()`은 `for name, d in _INDICATOR_NAME_TO_DESC.items(): if indicator_name.startswith(name)` 식의 접두사 매칭이라 BE→FE 단방향만 안전하다. FE에서 사용자가 입력한 이름을 그대로 BE에 보내는 경로가 있다면 깨진다.
- `indicator_matcher.py:332-338` `_find_in_catalog()`는 정확 매칭(`if ind['name'] == name`)이므로 FE 표시명 그대로 들어오면 None을 반환한다. 현재 호출 경로(`match_indicators_for_llm`)는 BE 자체 keyword 결과를 받기 때문에 운영상 안전하나, 프론트에서 raw name을 보내는 신규 API가 추가되면 잠재 버그.

### C. 카테고리 — 매핑 표 부재 (정책 차이)

| 측면 | BE | FE |
|------|----|----|
| 대분류 키 | `market_data`, `macro`, `technical`, `fundamental`, `sentiment` | `수급`, `주요 지수`, `원자재`, `암호화폐`, `금리`, `환율/변동성`, `고용/성장`, `물가/주택`, `기술적`, `펀더멘털`, `재무 체질`, `밸류에이션`, `성장`, `운영 효율`, `이익 품질`, `주주환원`, `심리` |
| 개수 | 5 | 17 |
| 매핑 정의 | `CATEGORY_LABELS`(prompt_builder.py:296-302)에 한글 라벨 5종만 존재 | `categoryOrder` 배열(AddIndicatorSheet.tsx:211-216)에 정렬용 순서만 존재 |

상세 매핑 분석:
- BE `market_data` (15개) → FE `수급/주요 지수/원자재/암호화폐` (15개) ✓ 1:N 분리
- BE `macro` (12개) → FE `금리/환율/변동성/고용·성장/물가·주택` (12개) ✓ 1:N 분리
- BE `technical` (9개) → FE `기술적` (9개) ✓ 1:1
- BE `fundamental` (24개) → FE `펀더멘털/재무 체질/밸류에이션/성장/운영 효율/이익 품질/주주환원` (24개) ✓ 1:N
- BE `sentiment` (1개) → FE `심리` (1개) ✓ 1:1

→ **개수는 일치**하지만 양쪽 어디에도 매핑 표가 없어, 추후 카테고리 변경 시 한쪽이 반영되지 않을 위험이 있다. `contracts/` 또는 공유 타입으로 매핑 표 단일화 필요.

---

## description 품질

### 1. 빈 description
없음. 64개 지표 모두 description 필드를 보유하며 0자가 아니다.

### 2. 짧은 description (< 10자)
없음. 가장 짧은 항목은 다음과 같다.

| id | 이름 | description | 길이 |
|----|------|-------------|------|
| 14 | 코스닥 지수 | `한국 중소형 성장주 시장 지수.` | 14자 |
| 4 | KOSPI 지수 | `한국 유가증권시장 전체 종목 시가총액 가중 지수.` | 22자 |
| 23 | 구리 (Copper) | `구리 선물 가격. 경기 선행지표로 "Dr. Copper"라 불림.` | 25자 |

→ 임계값(10자) 위반 없음.

### 3. 품질 메모 (선택사항)
- 대부분의 description이 "정의 + 활용/해석" 2단 구조로 균질하다 (예: id 6 "연준 기준금리. 유동성과 할인율에 직접 영향. 금리 인상은 주식에 부정적.").
- 일부 펀더멘털 지표(id 60~73)는 정의 위주이며 "지지/반박 시그널 해석"이 빠져 있어, 가설 빌더 UX에서 사용자가 `support_direction`을 직관적으로 이해하기 어려울 수 있다 (즉시 수정 대상 아님).

### 4. FE에는 description 미보유
FE `CatalogIndicator` 인터페이스 정의(`AddIndicatorSheet.tsx:8-13`)에 `description` 필드가 없다. 카드는 이름·주기 뱃지만 표시한다.

```ts
interface CatalogIndicator {
  id: number
  name: string
  category: string
  freq: Frequency
}
```

→ BE는 64개 지표 description을 갖췄지만 FE에서 활용되지 못함. UX 개선 여지: FE 카드 hover/expand 시 BE description 노출 (P2).

---

## keyword_rules 고아

### A. BE `KEYWORD_RULES` (`indicator_matcher.py:12-154`) — 11개 룰

| # | 키워드 그룹 | 가리키는 지표 이름 (id) | CATALOG 매칭 | 상태 |
|---|------|------|------|------|
| 1 | 외국인 / 외인 / 순매수 / foreign | `외국인 순매수 추이` (1) | ✓ | OK |
| 2 | 금리 / 연준 / FOMC / fed | `미국 기준금리 (Fed Funds Rate)` (6), `미국 10년 국채 금리` (7) | ✓ ✓ | OK |
| 3 | VIX / 공포 / 변동성 | `VIX (공포지수)` (8) | ✓ | OK |
| 4 | 환율 / 달러 / 원달러 | `원/달러 환율` (9) | ✓ | OK |
| 5 | RSI / MACD / 기술적 | `RSI (14일)` (10) | ✓ | OK |
| 6 | 센티먼트 / 여론 / 뉴스 | `뉴스 센티먼트` (11) | ✓ | OK |
| 7 | 실적 / EPS / 매출 / earnings | `EPS 추이` (5) | ✓ | OK |
| 8 | 기관 / 연기금 / 자산운용 | `기관 순매수 추이` (2) | ✓ | OK |
| 9 | S&P / 나스닥 / NASDAQ / 다우 | `S&P 500` (3) | ✓ | OK |
| 10 | 코스피 / KOSPI | `KOSPI 지수` (4) | ✓ | OK |
| 11 | 선거 / 정치 / 정책 | `VIX (공포지수)` (8), `KOSPI 지수` (4) | ✓ ✓ | OK |

→ **고아 룰 없음.** 11개 모든 룰이 가리키는 지표 이름이 BE CATALOG에 정확히 존재한다.

추가 메모: 룰 9는 키워드에 `다우`/`DOW`까지 포함하면서 결과 지표는 S&P 500 (id 3) 하나만 매핑한다. id 13 (다우존스) 카탈로그 항목이 있음에도 룰에서 참조되지 않는 비대칭이 있다 (룰 정확성 문제는 아니나 의도성 검증 필요).

### B. 룰 커버리지 — BE가 FE 대비 협소 (회귀 위험)

`KEYWORD_RULES`(BE)와 `KEYWORD_INDICATOR_MAP`(FE) 모두 동일 목적(전제 텍스트 → 추천 지표)이지만 커버리지가 크게 다르다.

| 측면 | BE | FE |
|------|----|----|
| 룰 수 | 11 | 28 |
| 가리키는 고유 지표 ID 수 | 11 (1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11) | 50개 이상 (1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 15, 16, 20, 21, 23, 24, 25, 26, 30, 31, 32, 33, 34, 35, 36, 37, 39, 40, 50, 51, 52, 53, 54, 55, 56, 57, 58, 60, 61, 62, 63, 64, 65, 66, 67, 68, 69, 70, 71, 72, 73) |

→ BE는 11개 ID만 키워드 매칭 대상으로 처리하므로, common-bugs(LLM 지표 환각 방지 — `match_by_gemini` 제거, `indicator_matcher.py:306-307` 주석 참조) 이후 PK 매칭이 실패한 전제는 11개 풀에서만 추천된다. 펀더멘털·원자재·암호화폐 전제는 사실상 추천이 비어버린다.

→ **고아는 없으나 커버리지 비대칭이 심각하다.** 동기화 권고: BE `KEYWORD_RULES`를 FE의 28개 룰 수준으로 확장하거나, 양쪽을 단일 contracts 파일로 추출.

### C. FE `KEYWORD_INDICATOR_MAP` (`AddIndicatorSheet.tsx:109-139`) — 28개 룰 고아 검사

FE 룰이 참조하는 모든 indicatorIds (1~16, 20~26, 30~37, 39, 40, 50~58, 60~73)가 FE `INDICATOR_CATALOG`에 존재한다.
→ **FE 측 고아 없음.**

추가 메모 — FE 카탈로그에 있으나 어떤 룰에서도 참조되지 않는 ID:
- id 13 (다우존스), id 14 (코스닥), id 22 (은), id 38 (달러/유로), id 41~47 (스토캐스틱~EMA), id 56 (배당수익률 — 룰 18에 한 번 등장하므로 참조됨)
- 정확히 룰에서 미참조: 13, 14, 22, 38, 41, 42, 43, 44, 45, 46, 47

→ 이는 고아가 아니다(카탈로그 항목이 룰에 매핑되지 않는 것은 정상). 단, 사용자가 "다우/은/스토캐스틱"으로 전제를 작성하면 추천이 0건이 되므로 룰 추가 여지 있음 (P2).

---

## data_params 형식

### A. 데이터 소스별 분류

| data_source | 항목 수 | data_params 패턴 | 비고 |
|-------------|---------|------------------|------|
| `fmp` (지수/원자재/암호화폐) | 16 | `{symbol: '^XXX' \| 'YYYUSD'}` | FMP `/quote/`, `/historical-price-eod/` 계열 |
| `fmp` (기술적 지표) | 9 | `{indicator: 'RSI', period: 14}` | FMP `/technical-indicators/` |
| `fmp` (펀더멘털 TTM) | 9 | `{metric: 'peRatioTTM' 등}` | FMP `/key-metrics-ttm/` 또는 `/ratios-ttm/` |
| `fmp` (커스텀 metric) | 4 | `{metric: 'foreign_net_buy' 등}` | FMP 표준 아님 — 자체 fetcher 필요 |
| `fred` | 9 | `{series_id: 'FEDFUNDS' 등}` | FRED 표준 시리즈 ID |
| `metrics` | 14 | `{metric_code: 'gross_margin' 등}` | 자체 metrics 앱 코드 |
| `news_sentiment` | 1 | `{}` | 자체 처리 |

### B. FMP 펀더멘털 — `key-metrics-ttm` 실제 필드명과 비교 (common-bugs #14)

`common-bugs.md` 버그 #14: "FMP Key Metrics 필드명 불일치 — `earningsYieldTTM` 역수 = PE, `returnOnEquityTTM` * 100 = ROE"

| id | 이름 | data_params.metric | FMP `/key-metrics-ttm/` 실제 동작 | 상태 |
|----|------|------|------|------|
| 50 | PER | `peRatioTTM` | `peRatioTTM` 미존재 → `earningsYieldTTM`의 역수로 산출 필요 | ❌ #14 미반영 |
| 51 | PBR | `pbRatioTTM` | `priceToBookRatioTTM` 또는 `pbRatioTTM` — 실응답 검증 필요 | ⚠️ 검증 필요 |
| 52 | ROE | `returnOnEquityTTM` | `returnOnEquityTTM` 존재하나 0.0~1.0 스케일 → ×100 필요 | ❌ #14 미반영 (스케일 메타 없음) |
| 53 | ROA | `returnOnAssetsTTM` | 동상 (스케일 변환 필요 가능) | ⚠️ #14 동일 패턴 위험 |
| 54 | 부채비율 | `debtToEquityTTM` | `debtToEquityTTM` 존재 가능, 응답 키 검증 필요 | ⚠️ 검증 필요 |
| 55 | FCF | `freeCashFlowTTM` | `freeCashFlowPerShareTTM` 또는 별도 endpoint(`/cash-flow-statement-ttm`) 필요 | ⚠️ 검증 필요 |
| 56 | 배당수익률 | `dividendYieldTTM` | `dividendYieldTTM` 존재 가능 (스케일 0~1 vs %) | ⚠️ 검증 필요 |
| 57 | 영업이익률 | `operatingProfitMarginTTM` | `key-metrics-ttm`에 없을 수 있음 — `/ratios-ttm/` 분기 필요 | ⚠️ 검증 필요 |
| 58 | 매출성장률 YoY | `revenueGrowthYoY` | FMP `key-metrics-ttm`에 없음 — `/financial-growth/` 별도 호출 (`growthRevenue`) | ❌ 표준 필드 아님 |

→ **펀더멘털 9개 항목 중 최소 3건(id 50, 52, 58)이 common-bugs #14에서 경고된 패턴과 일치**. 실제 호출 시 KeyError 또는 잘못된 스케일(0.15 vs 15%) 위험. metric별 후처리 함수 또는 endpoint 라우팅이 필요한데 현재 `data_params`만으로는 표현 불가.

### C. 커스텀 metric — 별도 핸들러 의존

| id | 이름 | data_params | FMP 표준 여부 | 비고 |
|----|------|-------------|------|------|
| 1 | 외국인 순매수 | `{metric: 'foreign_net_buy'}` | ❌ | KRX 데이터 또는 자체 수집 필요 |
| 2 | 기관 순매수 | `{metric: 'institutional_net_buy'}` | ❌ | 동상 |
| 5 | EPS 추이 | `{metric: 'eps'}` | ⚠️ | FMP `epsTTM`/`/historical-earning-calendar/` 등 endpoint 명시 필요 |
| 58 | 매출성장률 | `{metric: 'revenueGrowthYoY'}` | ❌ | `/financial-growth/` endpoint, 필드명 `growthRevenue` |

→ `metric` 키만으로는 호출 endpoint를 결정할 수 없다. 호출 단계의 별도 fetcher가 분기하는 구조로 추정되나, **데이터 계약 차원에서 `endpoint`/`field`/`scale` 등을 명시하는 구조가 권장**된다.

### D. FRED — 안전

9개 FRED 항목(`FEDFUNDS`, `DGS10`, `DGS2`, `MORTGAGE30US`, `UNRATE`, `PAYEMS`, `GDPC1`, `INDPRO`, `CPIAUCSL`, `HOUST`, `DEXUSEU`)은 모두 FRED 표준 시리즈 ID로 검증 가능. 형식 안정.

### E. 비표준 심볼

| id | data_params | 메모 |
|----|------|------|
| 39 | `{symbol: 'DX-Y.NYB'}` | Yahoo 형식. FMP는 `DXY`/`USDX` 등 다른 표기 사용 — 검증 필요 |
| 21 | `{symbol: 'CLUSD'}` | FMP commodity 표기. 일반 FMP는 `CLUSD` 또는 `CL=F` — 응답 키 검증 필요 |
| 14 | `{symbol: '^KQ11'}` | 코스닥. FMP 지원 여부 확인 필요 |
| 15 | `{symbol: '^N225'}` | 니케이. FMP `^N225` 지원 가능 |
| 16 | `{symbol: '^HSI'}` | 항셍. FMP `^HSI` 지원 가능 |

---

## 추가 발견 (참고)

1. **`_find_in_catalog(name)` vs `get_indicator_by_id(id)` 이중 경로**
   - `prompt_builder.get_indicator_by_id` (id 매칭): 안전
   - `indicator_matcher._find_in_catalog` (정확 이름 매칭): 표시 이름 4건 불일치(B 섹션)에 취약
   - 이름 매칭이 끝까지 필요한지 재검토 권장. id 기반 단일 경로로 정리 가능.

2. **`get_indicator_description` 접두사 매칭 (`prompt_builder.py:341-344`)**
   - LLM이 `EPS 추이 (META)`처럼 종목명을 붙여 반환할 때 폴백 매칭. 합리적이나 BE 이름이 `미국 10년 국채 금리`이고 LLM이 `미국 10년 국채`만 반환할 경우 접두사 매칭 실패.
   - FE 표시 이름과 BE 이름의 접두/접미 관계가 일관되지 않은 점이 잠재 위험.

3. **`indicator_matcher.match_by_gemini` 데드코드 가능성**
   - `match_by_gemini` 함수는 `match_indicators_for_premise`에서만 호출되며, `match_indicators_for_llm`(현재 LLM 빌더 주 경로)는 카탈로그 환각 방지를 위해 의도적으로 호출하지 않는다 (`indicator_matcher.py:306-307` 주석). 
   - `match_indicators_for_premise`의 호출처 추적 필요 — 미사용이면 제거 후보 (LLM 환각 방지 정책 일원화).

4. **테스트 커버리지**
   - `tests/unit/thesis/test_llm_builder.py`가 `INDICATOR_CATALOG` 사용 — id↔이름 정합성 단위 테스트 추가 권장.
   - FE/BE 카탈로그 동기화를 검증하는 통합 테스트는 부재.

---

## 권고 (요약)

| 우선순위 | 항목 | 근거 |
|----------|------|------|
| P0 | id 50, 52, 53, 58의 `data_params`/스케일 정의 점검 | common-bugs #14 회귀 위험 (3일 연속 회귀 보고) |
| P0 | 표시 이름 4건(id 6, 7, 30, 54) BE/FE 통일 | `_find_in_catalog` 정확 매칭 안정화 (3일 연속 미해결) |
| P1 | BE `KEYWORD_RULES` 확장 또는 BE/FE 단일 소스화 | `match_by_gemini` 미사용 후 BE 추천 풀이 11개 ID로 축소 |
| P1 | `data_params`에 `endpoint`/`field`/`scale` 메타데이터 추가 검토 | 커스텀 metric 4건의 호출 분기 표현 부족 |
| P2 | FE 카드에 BE description 노출 | 학습 곡선 단축, 64개 description 활용 |
| P2 | BE/FE 카테고리 매핑 표를 contracts/에 1차 소스화 | 카테고리 추가 시 누락 방지 |
| P2 | id↔이름 정합성 + BE/FE 카탈로그 동기화 테스트 | 회귀 방지 자동화 |
| P3 | `match_by_gemini` 데드코드 여부 확인 후 제거 검토 | LLM 환각 방지 정책 일원화 |

---

## 변동 요약 (vs 25일 보고서)

| 항목 | 25일 | 26일 | 변동 |
|------|------|------|------|
| BE/FE ID 집합 | 64↔64 일치 | 64↔64 일치 | 동일 |
| 이름 불일치 4건 | id 6/7/30/54 | id 6/7/30/54 | **미해결** |
| description < 10자 | 0건 | 0건 | 동일 |
| BE KEYWORD_RULES 수 | 11 | 11 | 동일 |
| FE KEYWORD_INDICATOR_MAP 수 | 28 | 28 | 동일 |
| common-bugs #14 패턴 위반 | id 50, 52, 58 | id 50, 52, 58 | **미해결** |

→ 카탈로그 영역의 코드 변경이 24시간 내에 발생하지 않았음을 의미한다. P0 권고가 누적되고 있으므로 우선 처리 필요.
