# 지표 카탈로그 동기화 감사 보고서

- **감사일**: 2026-04-24
- **범위**: INDICATOR_CATALOG (BE/FE) · KEYWORD_RULES · data_params 포맷
- **대상 파일**
  - BE 정의: `thesis/services/prompt_builder.py`
  - BE 후처리: `thesis/services/llm_postprocess.py`
  - BE 매칭: `thesis/services/indicator_matcher.py`
  - BE 페처: `thesis/tasks/eod_pipeline.py`
  - FE 표시: `frontend/components/thesis/AddIndicatorSheet.tsx`
- **유형**: 읽기 전용 감사 — 코드 변경 없음

---

## 요약 (동기화 상태)

| 항목 | 결과 |
|------|------|
| BE 카탈로그 항목 수 | **64개** (`prompt_builder.py:14-294`) |
| FE 카탈로그 항목 수 | **64개** (`AddIndicatorSheet.tsx:15-91`) |
| ID 기준 교집합 | **64개** (누락/추가 없음) |
| 이름 불일치 | **4건** (id 6, 7, 30, 54) |
| BE description 빈 값 | **0건** (전 항목 20자 이상, 10자 미만 없음) |
| FE description 필드 | **부재** (`CatalogIndicator` 인터페이스에 `description` 없음) |
| BE `KEYWORD_RULES` ↔ BE 카탈로그 | 모든 이름 매칭, **고아 0건** (11개 룰/11개 지표) |
| FE `KEYWORD_INDICATOR_MAP` ↔ FE 카탈로그 | 모든 `indicatorIds` 매칭, **고아 0건** (29개 룰) |
| BE vs FE 키워드 룰 커버리지 | **심한 비대칭** — BE 11개 / FE 50개 |
| FMP `data_params` vs 실제 fetcher(`_fetch_fmp_value`) | **21건 포맷 불일치** |

결론: ID 셋은 동기화되었으나 이름·키워드 룰 커버리지·FMP 필드 포맷에 체계적 불일치가 남아있음. 특히 `data_params.metric`가 FMP `/quote` 응답 필드와 어긋나 펀더멘털 TTM 지표 9건, 기술적 지표 9건이 실시간 값 수집에서 조용히 `None`을 반환할 가능성이 있다.

---

## BE ↔ FE 불일치 목록

### 1) 이름 불일치 (4건, 동일 ID)

| id | BE name (`prompt_builder.py`) | FE name (`AddIndicatorSheet.tsx`) | 영향 |
|----|-------------------------------|-----------------------------------|------|
| 6  | `미국 기준금리 (Fed Funds Rate)` | `미국 기준금리` | `get_indicator_description(name)`의 접두사 매칭(`prompt_builder.py:335-345`)으로 흡수 — 현재는 문제 없음 |
| 7  | `미국 10년 국채 금리` | `미국 10년 국채` | 접두사 흡수 가능. 단, FE 라벨 그대로 역조회 시 실패 |
| 30 | `미국 2년 국채 금리` | `미국 2년 국채` | 동일 |
| 54 | `부채비율 (Debt/Equity)` | `부채비율 (D/E)` | 괄호 안 표기 차이 — 접두사 `부채비율 `만 일치, 정확 매칭 실패 |

**권고**: id 54는 BE/FE 한쪽을 고정해 표기 통일 필요. id 6, 7, 30은 현재 접두사 매칭으로 덮이지만 "FE 라벨 → BE 조회" 경로가 생기면 즉시 깨짐.

### 2) ID 셋

- BE IDs (64): `{1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,20,21,22,23,24,25,26,30,31,32,33,34,35,36,37,38,39,40,41,42,43,44,45,46,47,50,51,52,53,54,55,56,57,58,60,61,62,63,64,65,66,67,68,69,70,71,72,73}`
- FE IDs (64): **BE와 완전 동일**
- 결번 구간 `17,18,19,27,28,29,48,49,59`는 양쪽 모두 의도적 예약(동기 일치).

### 3) 카테고리 라벨링 구조 차이 (정보성)

- BE `category` (5개 시스템 키): `market_data`, `macro`, `technical`, `fundamental`, `sentiment`
- FE `category` (17개 한글 소분류): `수급`, `주요 지수`, `원자재`, `암호화폐`, `금리`, `환율/변동성`, `고용/성장`, `물가/주택`, `기술적`, `펀더멘털`, `재무 체질`, `밸류에이션`, `성장`, `운영 효율`, `이익 품질`, `주주환원`, `심리`
- 두 구조를 잇는 단일 소스가 없음 → 신규 지표를 추가할 때 양쪽 분류를 수동으로 맞춰야 한다.

### 4) frequency(주기)

- BE: `INDICATOR_FREQUENCY` dict(`prompt_builder.py:305-326`), ID→주기 매핑
- FE: 항목 객체의 `freq` 필드로 인라인
- 모든 ID에서 값 일치(일간/주간/월간/분기). **이상 없음**.

---

## description 품질

- BE `description`: **64/64 전 항목 비어 있지 않음**, 모두 20자 이상. `< 10자` 항목 **0건**.
- 정규식 `description.*''`는 `_INDICATOR_NAME_TO_DESC` 빌더(`prompt_builder.py:332`)와 validator 스키마 정의에서만 검출됨 — **실제 데이터에 빈 값 없음**.
- FE `CatalogIndicator` 타입(`AddIndicatorSheet.tsx:8-13`)에는 `description` 필드 자체가 없음. FE에서 지표 설명을 보여주려면 BE API 응답을 경유해야 하는 구조.

**결론**: BE description 품질에는 문제 없음. FE 미러에 description이 빠져있다는 구조적 공백만 존재.

---

## keyword_rules 고아

### BE `KEYWORD_RULES` (`indicator_matcher.py:12-154`) — 11개 룰

| 키워드 그룹 | 추천 지표 이름 (BE) | 카탈로그 매칭 | 비고 |
|-------------|-----------------------|------------------|------|
| 외국인/외인/순매수/foreign | 외국인 순매수 추이 (id 1) | ✓ |  |
| 금리/연준/FOMC/… | 미국 기준금리 (Fed Funds Rate)(6), 미국 10년 국채 금리(7) | ✓ | id 30(2년 국채) 미포함 |
| VIX/공포/변동성 | VIX (공포지수)(8) | ✓ |  |
| 환율/달러/원달러 | 원/달러 환율(9) | ✓ | DXY(39) 미포함 |
| RSI/MACD/기술적 | RSI (14일)(10) | ✓ | MACD(40) 키워드만 있고 추천 누락 |
| 센티먼트/여론/뉴스 | 뉴스 센티먼트(11) | ✓ |  |
| 실적/EPS/매출/PER | EPS 추이(5) | ✓ | PER(50) 키워드만 있고 추천 누락 |
| 기관/연기금 | 기관 순매수 추이(2) | ✓ |  |
| S&P/나스닥 | S&P 500(3) | ✓ | NASDAQ(12) 미포함 |
| 코스피 | KOSPI 지수(4) | ✓ |  |
| 선거/정치/정책 | VIX(8), KOSPI(4) | ✓ |  |

- **BE 카탈로그에 없는 이름을 추천하는 고아 룰: 0건.** 모든 `KEYWORD_RULES[*].indicators[*].name`이 카탈로그 이름과 정확 일치.
- **카탈로그엔 있으나 BE 키워드 룰이 안 건드리는 지표(커버리지 공백)**: 53개. 예: NASDAQ(12), MACD(40), DXY(39), 원자재(20·21·23·24), 암호화폐(25·26), 재무 체질(60-73), 거시 고용/성장/물가(31-36, 38) 등.

### FE `KEYWORD_INDICATOR_MAP` (`AddIndicatorSheet.tsx:109-139`) — 29개 룰

- 모든 `indicatorIds`가 FE 카탈로그에 존재 → **고아 ID 0건**.
- 커버 ID(중복 제외): `{1, 2, 3, 6, 7, 8, 9, 10, 11, 12, 16, 20, 21, 23, 24, 25, 26, 30, 31, 32, 33, 34, 35, 36, 37, 39, 40, 50, 51, 52, 53, 54, 55, 56, 57, 58, 60, 61, 62, 63, 64, 65, 66, 67, 68, 69, 70, 71, 72, 73}` → **50개**.
- 미커버: `{4, 5, 13, 14, 15, 22, 38, 41, 42, 43, 44, 45, 46, 47}` (KOSPI, EPS 추이, 다우, 코스닥, 니케이, 은, EUR/USD, 스토캐스틱, 볼린저밴드, ATR, OBV, SMA50/200, EMA12).

### BE ↔ FE 룰 커버리지 비대칭

| | BE (`match_by_keywords`) | FE (`findRelatedIndicators`) |
|---|---|---|
| 룰 수 | 11 | 29 |
| 지표 커버리지 | 11/64 (17%) | 50/64 (78%) |

`indicator_matcher.match_indicators_for_llm()`(`indicator_matcher.py:271-329`)은 LLM이 `indicator_db_id`를 찾지 못한 전제에 대해 2순위로 `match_by_keywords`만 사용한다(주석: *Gemini fallback은 카탈로그에 없는 환각 지표를 생성하므로 제외*). 따라서 BE 경로는 11개 지표 범위 안에서만 추천이 이뤄지고, 나머지 53개 지표는 LLM이 `indicator_db_id`를 정확히 짚어주지 않으면 선택될 수 없다. FE는 별도 키워드 맵으로 UI에서는 훨씬 폭넓게 추천되는 반면, BE는 좁은 병목이 된다.

**시사점**: 같은 "전제 → 지표 추천" 로직이 양쪽에 이중 구현되어 있고 커버리지/추천 이유 텍스트가 서로 다른 상태로 드리프트 중. 단일 소스(예: BE `KEYWORD_RULES`를 FE가 API로 가져오기) 또는 FE 커버리지 수준까지 BE를 확장하는 정리가 필요하다.

---

## data_params 형식

### 1) FMP (`data_source='fmp'`) — 시장지수/원자재/크립토 (16건)

현재 포맷: `{'symbol': '^GSPC'}` 등. 실제 수집 경로 `eod_pipeline._fetch_fmp_value()`는 `FMPClient.get_quote(symbol)`을 호출하고 metric으로 dict 매핑 수행(`eod_pipeline.py:52-65`).

| 카탈로그 심볼 예시 | FMP `/quote` 호환성 | 메모 |
|--------------------|----------------------|------|
| `^GSPC`, `^IXIC`, `^DJI`, `^VIX` | ✓ 표준 FMP 규약 일치 | |
| `^KS11`, `^KQ11` | ⚠ FMP의 한국 지수 Quote 커버리지 제한적 — 운영 확인 필요 | |
| `^N225`, `^HSI` | ⚠ 프리미엄/지역 제한 가능성 — 실측 필요 | |
| `GCUSD`, `CLUSD`, `SIUSD`, `HGUSD`, `NGUSD` | ⚠ FMP 원자재 티커 관례상 대부분 지원되나 일부 응답 필드 누락 보고 사례 존재 | |
| `BTCUSD`, `ETHUSD` | ✓ | |
| `USDKRW` (id 9) | ⚠ FMP FX 표기는 종종 `KRW=X` 또는 `USD/KRW` 계열 — 실측 필요 | |
| `DX-Y.NYB` (id 39, DXY) | ⚠ 드문 표기, FMP에서는 `^DXY`/`DXY`가 일반적 — `FMPPremiumError` 또는 `None` 가능 | |

### 2) FMP — 수급 가짜 metric (2건, 구조적 수집 불가)

| id | 카탈로그 `data_params` | 문제 |
|----|------------------------|------|
| 1 | `{'metric': 'foreign_net_buy'}` | `symbol` 키 없음 → `_fetch_fmp_value`가 즉시 `None` 반환(`eod_pipeline.py:35-37`). FMP `/quote` 응답에 해당 필드 자체 없음 |
| 2 | `{'metric': 'institutional_net_buy'}` | 동일 — 수집 경로 부재 |

→ 구조적으로 데이터 수집 불가. 다른 소스(예: KRX, 국내 증권사 API)로 `data_source` 분기 신설이 필요하거나, 해당 지표를 수집 대상에서 제외해야 함.

### 3) FMP — 펀더멘털 TTM (9건, 필드명 불일치)

`_fetch_fmp_value`의 `value_map`(`eod_pipeline.py:53-63`)에 정의된 허용 metric:
```
price, change_percent, volume, pe, eps, market_cap, previous_close, day_high, day_low
```
`value_map.get(metric, metric)` 패턴이므로 매핑에 없으면 metric을 그대로 `quote.get(metric)`에 시도한다. 그러나 FMP `/quote` 응답에는 TTM 필드가 없음 (`/key-metrics-ttm`, `/ratios-ttm`, `/financial-growth` 등 별도 엔드포인트 필요).

| id | 카탈로그 `metric` | 기대 엔드포인트 | `_fetch_fmp_value` 결과 |
|----|-------------------|-----------------|-------------------------|
| 50 | `peRatioTTM` | `/key-metrics-ttm` | `quote['peRatioTTM']` 없음 → `None` |
| 51 | `pbRatioTTM` | `/key-metrics-ttm` 또는 `/ratios-ttm` | `None` |
| 52 | `returnOnEquityTTM` | `/ratios-ttm` | `None` |
| 53 | `returnOnAssetsTTM` | `/ratios-ttm` | `None` |
| 54 | `debtToEquityTTM` | `/ratios-ttm` | `None` |
| 55 | `freeCashFlowTTM` | `/key-metrics-ttm` | `None` |
| 56 | `dividendYieldTTM` | `/ratios-ttm` | `None` |
| 57 | `operatingProfitMarginTTM` | `/ratios-ttm` | `None` |
| 58 | `revenueGrowthYoY` | `/financial-growth` (실제 필드명 `revenueGrowth`) | `None`, 필드명 자체도 틀림 |

**참고**: `common-bugs.md` #14에서 이미 같은 증상이 기록됨 — *"FMP Key Metrics 필드명 불일치: `earningsYieldTTM` 역수 = PE, `returnOnEquityTTM` × 100 = ROE"*. 즉 `/key-metrics-ttm` 응답에는 `peRatioTTM` 대신 `earningsYieldTTM`이 있을 수 있고 ROE 등은 소수→퍼센트 변환이 필요하다. 현재 `_fetch_fmp_value`는 이 경로를 구현하지 않는다.

→ 펀더멘털 TTM 지표는 `data_source='fmp'`로 선언되었지만 실제 fetcher는 Quote 기반이라 **값 수집 불가**. 동등한 데이터는 `data_source='metrics'`(id 60-73, `metric_code` 기반)에서 `fetch_quarterly_metric`으로 이미 커버되므로 id 50-58과 **중복/경쟁 관계**이기도 하다.

### 4) FMP — 기술적 지표 (9건, 엔드포인트 불일치)

| id | `data_params` | 실제 `_fetch_fmp_value` 동작 |
|----|----------------|------------------------------|
| 10 | `{'indicator': 'RSI', 'period': 14}` | `symbol` 키 없음 → 즉시 `None` |
| 40-47 | 동일 패턴 | 동일 — `symbol` 없어 조기 종료 |

FMP 기술적 지표는 `/technical-indicator/{interval}/{symbol}?type=...&period=...` 경로가 별도. 현재 fetcher(`get_quote` 기반)는 이 호출을 **전혀 처리하지 않음**. 카탈로그와 수집기 사이 포맷 약속이 어긋나 있다.

### 5) FMP — EPS (id 5)

`{'metric': 'eps'}`. `value_map`에 `eps`가 있지만 `symbol`이 없음 → 조기 종료. 실제 수집에는 가설의 `target` 심볼 주입이 필요한데, FMP 경로는 `thesis.target` fallback 로직을 갖고 있지 않다(`_fetch_metrics_value`만 해당 fallback 구현, `eod_pipeline.py:164`).

### 6) FRED (`data_source='fred'`) — 6건

`{'series_id': 'FEDFUNDS'}` 등. `_fetch_fred_value`(`eod_pipeline.py:84-124`)가 `series_id` 키만 기대 → **포맷 정합. 이상 없음**.

### 7) metrics (`data_source='metrics'`) — 14건 (id 60-73)

`{'metric_code': 'gross_margin', ...}`. `_fetch_metrics_value`가 `metric_code` + `symbol`(`thesis.target` fallback)을 사용 → **포맷 정합. 이상 없음**.

### 8) news_sentiment (`data_source='news_sentiment'`) — 1건

카탈로그: `{'data_params': {}}` (id 11). `_fetch_news_sentiment_value`는 `params.get('symbol')`을 요구하며 없으면 조기 반환. 카탈로그 빈 dict → **항상 `None`**. `thesis.target` fallback 로직이 없어 실질 수집 불가.

### 9) FMP 소스 요약

| 구분 | 카탈로그 건수 | fetcher 정합 | 예상 결과 |
|------|---------------|--------------|-----------|
| 시장지수/원자재/크립토(`symbol` 기반) | 16 | ✓ (심볼 유효성은 운영 확인 필요) | 수집 가능 |
| 수급 가짜 metric(id 1, 2) | 2 | ✗ | 항상 `None` |
| EPS 추이(id 5) | 1 | ✗ (`symbol` 주입 경로 없음) | 항상 `None` |
| 펀더멘털 TTM(id 50-58) | 9 | ✗ (엔드포인트/필드 불일치) | 항상 `None` |
| 기술적 지표(id 10, 40-47) | 9 | ✗ (기술적 엔드포인트 미구현) | 항상 `None` |

→ FMP 선언 지표 37건 중 **약 21건이 구조적으로 값 수집 불가 상태**.

---

## 종합 결론

1. **ID 셋은 동기화** (BE = FE = 64개).
2. **이름 4건 불일치** — id 6/7/30은 접두사 매칭으로 흡수되나 id 54는 정확 매칭 실패.
3. **description**은 BE에서 품질 문제 없음. FE 미러 타입에 `description` 필드가 없는 구조적 공백.
4. **keyword_rules 고아는 없으나** BE/FE 커버리지 비대칭이 심하고(BE 11 vs FE 50) 같은 추천 로직을 이중 구현해 드리프트 위험.
5. **data_params**는 FMP 쪽에서 체계적 결함:
   - 펀더멘털 TTM 9건, 기술적 지표 9건, 수급 2건, EPS 1건 — 총 **21건이 fetcher와 포맷 호환 불가**.
   - 카탈로그는 FMP TTM 엔드포인트를 전제하고 선언되어 있으나 fetcher는 Quote 엔드포인트만 처리.
   - id 11 뉴스 센티먼트도 `symbol` 주입 경로가 없어 실질 수집 불가.
6. 단일 소스 관리 부재 — BE 카탈로그, FE 미러, BE 키워드 룰, FE 키워드 맵 네 곳이 각각 수동 동기화되고 있으며 카테고리 라벨링 기준도 상이.

감사는 읽기 전용으로 종료하며, 수정은 별도 PR/티켓으로 다루는 것을 권고한다.
