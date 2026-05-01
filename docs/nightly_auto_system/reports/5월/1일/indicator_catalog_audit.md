# 지표 카탈로그 동기화 감사 보고서

- **감사 일자**: 2026-05-01
- **감사 범위**: BE 카탈로그 ↔ FE 미러 ↔ keyword_rules ↔ 실제 데이터 fetcher 정합성
- **모드**: 읽기 전용 (코드 수정 없음)
- **대상 파일**:
  - BE 정의: `thesis/services/prompt_builder.py` (`INDICATOR_CATALOG`)
  - BE 후처리: `thesis/services/llm_postprocess.py` (`normalize_llm_output`)
  - BE 매칭: `thesis/services/indicator_matcher.py` (`KEYWORD_RULES`)
  - BE fetch: `thesis/tasks/eod_pipeline.py` (`_fetch_fmp_value`, `_fetch_fred_value`, `_fetch_metrics_value`, `_fetch_news_sentiment_value`)
  - FE 표시: `frontend/components/thesis/AddIndicatorSheet.tsx` (`INDICATOR_CATALOG`, `KEYWORD_INDICATOR_MAP`)

---

## 요약 (동기화 상태)

| 영역 | 상태 | 핵심 결과 |
|------|------|---------|
| BE ↔ FE id/name 매핑 | ✅ **OK** | 64개 항목 모두 id/name 일치 |
| FE 카테고리 라벨 | ⚠️ **부분 차이** | FE는 17개 세분 카테고리, BE는 5개 거친 카테고리. 데이터가 아닌 UI 그룹핑 |
| description 품질 | ✅ **OK** | 64개 모두 작성됨, 빈 값/10자 미만 없음 |
| BE keyword_rules 커버리지 | 🔴 **심각** | 11개 카탈로그 항목만 커버 (전체 64개 중 17%). FE는 약 50개 커버 |
| BE/FE keyword 매핑 결과 일관성 | 🔴 **불일치** | 동일 키워드 입력 시 BE는 1개 추천, FE는 7개 추천 등 결과 자체가 다름 |
| FMP fetcher ↔ data_params | 🔴 **심각** | FMP fundamental(id 50–58, 9개)·기술적 지표(id 10, 40–47, 9개)는 fetcher가 metric/indicator 키를 인식하지 못해 항상 null 또는 잘못된 값 반환 |
| FMP foreign/institutional net_buy | 🔴 **심각** | id 1, 2는 symbol 부재 + value_map 미존재 → 영구 null reading |
| FRED 매크로 fetcher | ✅ **OK** | id 6, 7, 30, 37, 38, 31–36 정상 동작 가능 |
| metrics(분기 재무체질) fetcher | ✅ **OK** | id 60–73 metric_code 모두 fetcher와 매핑 일치 |
| news_sentiment fetcher | ⚠️ **잠재 결함** | data_params={}로 정의되어 있으나 fetcher는 `symbol` 필수 — target_symbol 미주입 시 null |

**총평**: id/name/description 같은 *정의 레벨*은 깔끔하지만, *런타임 fetch 레벨*에서 카탈로그의 약 30%가 잘못된 값 또는 null만 생산한다. UX 측면에서는 BE keyword 룰이 FE 대비 17%만 커버해 LLM 추천 실패 시 fallback 품질이 빈약하다.

---

## BE ↔ FE 불일치 목록

### id / name 불일치
없음. 64개 항목 모두 id, name이 정확히 일치한다.

| 카테고리(BE) | id 범위 | 항목 수 | BE/FE 일치 |
|------------|--------|--------|----------|
| market_data 수급 | 1, 2 | 2 | ✅ |
| market_data 주요 지수 | 3, 4, 12–16 | 7 | ✅ |
| market_data 원자재 | 20–24 | 5 | ✅ |
| market_data 암호화폐 | 25, 26 | 2 | ✅ |
| macro 금리 | 6, 7, 30, 37 | 4 | ✅ |
| macro 환율/변동성 | 8, 9, 38, 39 | 4 | ✅ |
| macro 고용/성장 | 31, 32, 34, 35 | 4 | ✅ |
| macro 물가/주택 | 33, 36 | 2 | ✅ |
| technical | 10, 40–47 | 9 | ✅ |
| fundamental(quote/TTM) | 5, 50–58 | 10 | ✅ |
| fundamental(metrics) | 60–73 | 14 | ✅ |
| sentiment | 11 | 1 | ✅ |
| **합계** | — | **64** | — |

### 카테고리 라벨 차이 (정보성)

BE `category` 필드(저장 단위)는 5개 거친 분류:
- `market_data`, `macro`, `technical`, `fundamental`, `sentiment`

FE `category`(UI 표시 단위)는 17개 세분:
- `수급`, `주요 지수`, `원자재`, `암호화폐`, `금리`, `환율/변동성`, `고용/성장`, `물가/주택`, `기술적`, `펀더멘털`, `재무 체질`, `밸류에이션`, `성장`, `운영 효율`, `이익 품질`, `주주환원`, `심리`

특히 BE에서는 모두 `fundamental`인 id 60~73이 FE에서는 `재무 체질/밸류에이션/성장/운영 효율/이익 품질/주주환원` 6개 카테고리로 분산된다. 데이터 무결성 이슈는 아니지만, 향후 BE에 sub_category가 추가되거나 카탈로그 갱신 자동화를 시도할 때 FE 분류 기준을 별도 매핑 테이블로 옮겨두지 않으면 지속적인 손작업 동기화가 필요하다.

### support_direction 누락
FE `CatalogIndicator`는 `id, name, category, freq` 4개만 들고 있어 `support_direction`(BE 필드)을 가지지 않는다. 현재 FE는 표시·선택 용도로만 사용되므로 기능적 결함은 아니지만, 추후 FE에서 "이 지표가 가설을 지지/반박" 시각화를 하려면 누락 필드다.

### INDICATOR_FREQUENCY (BE) ↔ freq (FE) 일치 검증

BE `INDICATOR_FREQUENCY` (prompt_builder.py:305–326) vs FE `freq` 필드 검증 결과 64개 모두 라벨 일치 (`일간`/`주간`/`월간`/`분기`).

---

## description 품질

`prompt_builder.INDICATOR_CATALOG`의 `description` 필드 64개 모두 작성됨.

| 항목 | 값 |
|------|-----|
| 빈 description | 0개 |
| 10자 미만 description | 0개 |
| 최단 description (글자수, 의미) | id 14 코스닥 지수 — `'한국 중소형 성장주 시장 지수.'` (14자, 명료함) |
| 최장 description | id 14 NASDAQ 등 다수 — 30자 내외 |

**FE 미러에는 description이 없음**. BE만 가짐. AddIndicatorSheet.tsx는 description을 사용하지 않으며, 사용자가 카드 호버/선택 시 추가 설명을 보지 못한다. 사용처는 `prompt_builder.get_indicator_description()` (관제실 카드 description 표시용 monitoring_views.py:172).

**잠재 이슈**: description 동기화 정책 부재. BE 단일 소스이므로 FE 카드에 "이 지표가 무엇을 측정하는지" 안내가 없다. UX 관점에서 추후 보완 후보.

---

## keyword_rules 고아

### keyword_rules → INDICATOR_CATALOG 매핑 검증

`indicator_matcher.KEYWORD_RULES`의 11개 룰이 가리키는 지표 이름 모두 `INDICATOR_CATALOG`에 존재.

| KEYWORD_RULES 지표명 | 카탈로그 id | 존재 여부 |
|---------------------|----------|---------|
| 외국인 순매수 추이 | 1 | ✅ |
| 미국 기준금리 (Fed Funds Rate) | 6 | ✅ |
| 미국 10년 국채 금리 | 7 | ✅ |
| VIX (공포지수) | 8 (룰 2개 항목 모두) | ✅ |
| 원/달러 환율 | 9 | ✅ |
| RSI (14일) | 10 | ✅ |
| 뉴스 센티먼트 | 11 | ✅ |
| EPS 추이 | 5 | ✅ |
| 기관 순매수 추이 | 2 | ✅ |
| S&P 500 | 3 | ✅ |
| KOSPI 지수 | 4 (룰 2개 항목 모두) | ✅ |

**고아 규칙(KEYWORD_RULES → 카탈로그 미존재)**: 0개. ✅

### 카탈로그 → keyword_rules 역방향 커버리지 (심각)

전체 64개 카탈로그 항목 중 `KEYWORD_RULES`에 매핑된 것은 11개뿐. **53개(83%)가 키워드 매칭 미커버**.

미커버 핵심 항목:

| 영역 | 미커버 id |
|------|---------|
| 주요 지수 | 12 NASDAQ, 13 다우존스, 14 코스닥, 15 니케이, 16 항셍 |
| 원자재 | 20 금, 21 원유 WTI, 22 은, 23 구리, 24 천연가스 |
| 암호화폐 | 25 BTC, 26 ETH |
| 금리 | 30 미국 2Y, 37 모기지 30Y |
| 환율/변동성 | 38 EUR, 39 DXY |
| 고용/성장 | 31 실업률, 32 NFP, 34 GDP, 35 산업생산 |
| 물가/주택 | 33 CPI, 36 주택착공 |
| 기술적(RSI 외 전부) | 40–47 (MACD, 스토캐스틱, 볼린저, ATR, OBV, SMA50/200, EMA12) |
| 펀더멘털(EPS 외 전부) | 50–58 (PER, PBR, ROE, ROA, 부채, FCF, 배당, 영업마진, 매출성장) |
| 재무 체질 metrics | 60–73 (전부) |

**FE 대비 격차**: FE의 `KEYWORD_INDICATOR_MAP`은 약 28개 룰로 50개 가까운 카탈로그 항목을 커버한다. 즉 같은 입력에 대해 BE와 FE의 키워드 추천 결과가 **대규모 불일치**.

### BE/FE 동일 키워드 결과 비교 샘플

| 키워드 | BE 추천 (KEYWORD_RULES) | FE 추천 (KEYWORD_INDICATOR_MAP) |
|------|------------------------|-------------------------------|
| `유가`, `WTI`, `원유` | (없음, fallback Gemini 호출) | id 21 |
| `RSI` | id 10만 | id 10, 40 |
| `실적`, `EPS` | id 5만 | id 5, 50, 57, 58, 60, 61, 69 |
| `로ROE`, `이익률` | (없음) | id 52, 53, 57, 62, 60, 61 |
| `부채`, `레버리지` | (없음) | id 54, 63, 64, 65 |
| `배당`, `FCF` | (없음) | id 55, 56, 66, 68, 73 |
| `CPI`, `물가` | (없음) | id 33 |
| `고용`, `실업` | (없음) | id 31, 32 |
| `비트코인` | (없음) | id 25, 26 |
| `구리`, `Dr. Copper` | (없음) | id 23 |
| `다우`, `나스닥` | id 3만 (룰 키워드에 NASDAQ 포함됨) | id 3, 12 |
| `중국`, `항셍` | (없음) | id 16 |

### 영향

- **LLM 빌더에서 `indicator_db_id`를 정확히 반환하지 못해 fallback이 트리거되면**, `match_indicators_for_llm`은 `match_by_keywords`(BE 룰)만 사용한다(`indicator_matcher.py:312–326`). 카탈로그 64개 중 11개만 매칭 가능하므로, 거시·펀더멘털·암호·기술적 영역에 대한 가설은 추천 누락이 자주 발생한다.
- 같은 가설을 작성하는 사용자가 LLM 모드(BE) vs 수동 추가 모드(FE의 추천 패널) 사이에서 **다른 추천을 받게 됨** → 일관성 결손.

---

## data_params 형식

### 카탈로그 정의 vs fetcher 처리 매트릭스

| data_source | 카탈로그 키 (정의) | fetcher가 읽는 키 | 처리 위치 | 정합성 |
|-----------|-----------------|----------------|---------|------|
| `fmp` (지수/원자재/암호/VIX/환율) | `symbol` | `params.get('symbol')` + metric 디폴트 `price` | eod_pipeline.py:31–34 | ✅ 일치 — quote.price 반환 |
| `fmp` (id 1, 2 수급) | `metric: foreign_net_buy / institutional_net_buy` (symbol 없음) | symbol 필수, value_map에 미존재 | eod_pipeline.py:35–37 | 🔴 **항상 null** — symbol 없으니 즉시 None,None 반환 |
| `fmp` (id 5 EPS) | `metric: eps` | value_map['eps']='eps' → quote.eps | eod_pipeline.py:53–63 | ⚠️ 동작은 하지만 quote.eps는 TTM 단일값. 분기 비교는 metrics 시스템과 분리됨 |
| `fmp` (id 50–58 fundamental TTM) | `metric: peRatioTTM, pbRatioTTM, returnOnEquityTTM, returnOnAssetsTTM, debtToEquityTTM, freeCashFlowTTM, dividendYieldTTM, operatingProfitMarginTTM, revenueGrowthYoY` | value_map에 키 없음 → fallback로 동일 문자열을 quote 필드명으로 사용 | eod_pipeline.py:64 | 🔴 **항상 null** — quote endpoint는 `peRatioTTM` 같은 키 미반환 (TTM 데이터는 별도 `key-metrics-ttm` endpoint 필요) |
| `fmp` (id 10, 40–47 기술적) | `indicator: 'RSI'/'MACD'/'stochastic'/...`, `period`, `fast`/`slow`/`signal` | `indicator` 키 미인식, metric 디폴트 `price` → quote.price | eod_pipeline.py:33, 53–64 | 🔴 **잘못된 값** — 사용자는 RSI 값을 기대하지만 종가가 저장됨. value_map 매핑 누락 + 별도 technical-indicator 엔드포인트 호출 미구현 |
| `fred` (id 6, 7, 30, 33–37, 38) | `series_id` | `params.get('series_id')` | eod_pipeline.py:88 | ✅ 일치 |
| `metrics` (id 60–73) | `metric_code` (gross_margin, net_margin, roic, current_ratio, interest_coverage, net_debt_to_ebitda, fcf_margin, ev_to_ebitda, fcf_yield, operating_income_growth, dso, asset_turnover, accruals_ratio, net_shareholder_yield) | `params.get('metric_code')` + `params.get('symbol') or thesis.target` | eod_pipeline.py:161–174 | ✅ 일치 — symbol은 가설 target에서 자동 보충, metric_code는 quarterly_metric_fetcher의 RATIO_METRICS/COMPARISON_TYPE_MAP과 매칭 |
| `news_sentiment` (id 11) | `data_params: {}` (빈 dict) | `params.get('symbol')` 필수, 없으면 즉시 null | eod_pipeline.py:130–135 | ⚠️ **target_symbol 주입 의존** — `thesis_builder.py:1156–1157`에서 `data_params['symbol'] = target_sym`로 주입되지만 LLM이 target_symbol을 누락하면 영구 null |

### 핵심 결함 상세

**(1) FMP TTM 펀더멘털 9개 (id 50–58) — 데이터 영구 null**

- 카탈로그가 `metric: 'peRatioTTM'` 등 FMP `key-metrics-ttm` 엔드포인트의 필드명을 그대로 사용한다.
- 그러나 `_fetch_fmp_value`는 오로지 `client.get_quote(symbol)`만 호출한다.
- value_map (eod_pipeline.py:53)에는 `pe`, `eps`만 등록되어 있고 `peRatioTTM` 등은 없다 → `field = value_map.get(metric, metric)` 폴백으로 `peRatioTTM` 그대로 사용 → `quote.get('peRatioTTM')` → None.
- 결과: 사용자가 LLM 빌더 또는 FE에서 PER/PBR/ROE/ROA/부채/FCF/배당/영업마진/매출성장률을 선택해도 매일 null reading이 누적됨.
- **권장**: 동일 의미의 metric_code(`pe_ratio`, `roe` 등)로 `data_source='metrics'` 사용으로 통합 OR `_fetch_fmp_value`에 key-metrics-ttm 분기 추가.

**(2) FMP 기술적 9개 (id 10, 40–47) — 잘못된 값 저장**

- 카탈로그가 `indicator: 'RSI'/'MACD'/...` 키와 `period`/`fast`/`slow`/`signal` 파라미터를 사용한다.
- 그러나 `_fetch_fmp_value`는 `metric` 키만 읽고, `indicator` 키는 무시한다.
- `metric` 부재 → 디폴트 `'price'` → `quote.get('price')` 반환.
- 결과: `RSI (14일)` 지표에 매일 *현재 종가*가 저장됨.
- **권장**: `_fetch_fmp_value`에 `indicator` 키 분기 추가 후 별도 `client.get_technical_indicators(...)` 경로 사용. (`api_request/providers/base.py:455`에 `get_technical_indicators` 시그니처 존재 확인됨)

**(3) FMP 수급 2개 (id 1, 2) — 영구 null**

- 카탈로그가 `metric: 'foreign_net_buy' / 'institutional_net_buy'`만 정의하고 `symbol` 미정의.
- `_fetch_fmp_value` 첫 단계에서 `if not symbol: return None, None` (eod_pipeline.py:35–37).
- target_symbol을 LLM이 명시해도 그 키워드는 FMP 표준 quote에는 없는 metric이므로 null로 끝남.
- **권장**: 데이터 출처 명확화 필요. 한국 외국인/기관 수급은 FMP가 아닌 KIS/KRX API 영역. 카탈로그에서 `data_source: 'manual'` 또는 별도 'krx_supply' 도입 검토.

**(4) news_sentiment (id 11) — target_symbol 의존성**

- `data_params: {}`로 정의됨 → 자체로는 작동 불가.
- `thesis_builder.py:1156`이 `target_symbol`을 자동 주입하는 경로가 있어 LLM 모드 + target_symbol이 잘 들어오면 동작.
- 그러나 FE에서 수동 추가하는 경로는 target_symbol 주입을 보장하지 않으면 null.
- **권장**: 카탈로그 정의에 "target_symbol 필수" 메타 플래그를 두거나, FE 수동 선택 시 symbol prompt를 강제.

### 정상 동작 항목 (참고)

| 영역 | 항목 수 | 비고 |
|------|------|------|
| FMP 지수 | 7 | id 3, 4, 12–16 — quote.price 반환으로 정상 |
| FMP 원자재 | 5 | id 20–24 |
| FMP 암호화폐 | 2 | id 25, 26 |
| FMP 변동성/환율 | 2 | id 8 VIX, 9 USDKRW (id 39 DXY는 `DX-Y.NYB` symbol을 FMP quote가 처리하는지 별도 검증 필요) |
| FRED 매크로 | 11 | id 6, 7, 30, 31–37, 38 |
| metrics 분기 재무 | 14 | id 60–73 |
| FMP EPS | 1 | id 5 (TTM 한정 동작) |

**합계**: 64개 중 약 42개 정상, 20개 데이터 결함, 1개 부분 동작, 1개 의존성 결함.

---

## 권장 후속 조치 (우선순위)

> 본 보고서는 읽기 전용 감사이며 코드 수정은 수행하지 않음. 아래는 향후 PR 후보.

1. **🔴 [긴급] FMP fundamental TTM 지표(id 50–58) 데이터 출처 변경**
   - 동일 의미의 `metric_code`(pe_ratio, pbr, roe, roa, debt_to_equity, fcf, dividend_yield, operating_margin, revenue_growth_yoy)가 metrics 시스템에 이미 존재하는지 확인 후 `data_source='metrics'`로 일원화 검토.
   - 또는 `_fetch_fmp_value`를 `key-metrics-ttm` 엔드포인트 분기로 확장.

2. **🔴 [긴급] FMP 기술적 지표(id 10, 40–47) fetcher 분기 추가**
   - `_fetch_fmp_value`에 `indicator` 키 검출 로직 추가, `client.get_technical_indicators(...)` 호출 경로 신설.
   - 그 전까지는 카탈로그에서 일시적으로 `data_source='manual'`로 표시해 잘못된 종가 저장 방지.

3. **🔴 [긴급] id 1, 2 수급 지표 데이터 출처 재정의**
   - FMP 적격성 결정 + symbol 부재 문제 해결.

4. **🟠 [중요] BE keyword_rules 커버리지 확대**
   - FE `KEYWORD_INDICATOR_MAP`을 BE로 1:1 미러링하거나, 양쪽이 공통 JSON 룰셋을 참조하도록 단일 소스화.
   - 현재 LLM fallback 매칭이 17%만 작동.

5. **🟠 [중요] news_sentiment(id 11) target_symbol 강제**
   - 카탈로그에 `requires_target_symbol: True` 메타 추가 + `llm_postprocess.normalize_llm_output`에서 target_symbol 누락 시 경고 또는 reject.

6. **🟡 [개선] FE 카탈로그에 description / support_direction 동기화**
   - AddIndicatorSheet의 hover/expand UI에 description 표시.
   - 단일 소스(BE)에서 build-time generate 또는 contracts/shared-types 활용.

7. **🟡 [개선] 카탈로그 단일 소스화**
   - `prompt_builder.INDICATOR_CATALOG`을 JSON으로 분리 후 BE/FE 빌드 타임에 import 또는 contracts/ 자산화 검토.
   - 64개 항목을 두 곳에서 손으로 동기화하는 현재 구조는 향후 확장 시 누락 위험.

---

## 참고: 검증한 파일/라인

- `thesis/services/prompt_builder.py:14–294` (INDICATOR_CATALOG 정의)
- `thesis/services/prompt_builder.py:305–326` (INDICATOR_FREQUENCY)
- `thesis/services/prompt_builder.py:335–345` (get_indicator_description)
- `thesis/services/llm_postprocess.py:82–95` (indicator_db_id 카탈로그 검증)
- `thesis/services/indicator_matcher.py:12–154` (KEYWORD_RULES)
- `thesis/services/indicator_matcher.py:271–329` (match_indicators_for_llm + PK 검증)
- `thesis/services/thesis_builder.py:1148–1173` (data_params에 target_symbol 주입)
- `thesis/tasks/eod_pipeline.py:25–194` (4종 fetcher + DATA_SOURCE_FETCHERS)
- `thesis/views/monitoring_views.py:120–174` (분기 metrics 처리)
- `thesis/views/monitoring_views.py:280–344` (FMP 히스토리 fallback)
- `thesis/services/quarterly_metric_fetcher.py:30–65` (RATIO_METRICS, COMPARISON_TYPE_MAP)
- `thesis/models/indicator.py:35–46` (data_source choices, data_params JSONField)
- `frontend/components/thesis/AddIndicatorSheet.tsx:15–91` (FE INDICATOR_CATALOG)
- `frontend/components/thesis/AddIndicatorSheet.tsx:109–139` (FE KEYWORD_INDICATOR_MAP)
