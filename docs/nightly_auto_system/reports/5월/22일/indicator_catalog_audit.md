# 지표 카탈로그 동기화 감사 보고서

- 일시: 2026-05-22 (slice14 브랜치)
- 검사 대상:
  - BE 정의: `thesis/services/prompt_builder.py` (`INDICATOR_CATALOG`)
  - BE 후처리: `thesis/services/llm_postprocess.py`
  - BE 매칭: `thesis/services/indicator_matcher.py` (`KEYWORD_RULES`)
  - FE 표시: `frontend/components/thesis/AddIndicatorSheet.tsx` (`INDICATOR_CATALOG` + `KEYWORD_INDICATOR_MAP`)
- 작성: 읽기 전용 감사 (코드 수정 없음)

---

## 요약 (동기화 상태)

| 항목 | 상태 | 비고 |
|------|------|------|
| 지표 ID 동기화 (BE ↔ FE) | ✅ 일치 (64/64) | 양쪽 모두 동일한 ID 집합 보유 |
| 지표 이름 동기화 | ✅ 일치 | 64개 모두 동일한 한글명 |
| 빈도 (freq) 동기화 | ✅ 일치 | BE `INDICATOR_FREQUENCY` ↔ FE `freq` 64/64 일치 |
| description 누락 | ✅ 없음 | 64개 모두 보유, 최소 길이 17자 (id 14) |
| description < 10자 | ✅ 없음 | 모두 ≥ 10자 |
| BE↔FE category 구조 | ⚠ 의도적 차이 | BE 5개 대분류, FE 17개 세부분류 (UX 그루핑) |
| FE에만 있는 항목 | ✅ 없음 | |
| BE에만 있는 항목 | ✅ 없음 | |
| `KEYWORD_RULES` 고아 (BE) | ✅ 없음 | 11개 이름 모두 카탈로그에 존재 |
| `KEYWORD_INDICATOR_MAP` 고아 (FE) | ✅ 없음 | 28개 규칙의 모든 ID가 카탈로그에 존재 |
| **`KEYWORD_RULES` 커버리지 (BE)** | 🔴 **심각** | **64개 중 11개(17%)만 매칭 가능. 53개 인디케이터 unreachable** |
| **BE ↔ FE 키워드 매칭 룰 비대칭** | 🔴 **심각** | **BE 11 룰 vs FE 28 룰. 검색·자동매칭 결과가 채널마다 다를 수 있음** |
| FMP data_params 형식 위험 (#14 회귀) | ⚠ 일부 audit_note로 방어 중 | id 50/52/53/58. id 58은 `/financial-growth` endpoint 분기 권장 (실 구현 확인 필요) |

판정: **카탈로그 자체 동기화는 견고. 다만 BE 키워드 매칭 룰 커버리지 + BE/FE 룰 비대칭이 가장 큰 부채.**

---

## BE ↔ FE 불일치 목록

### 1. ID/이름/빈도 일치 (64건)

| Category(BE) | Category(FE) | id | name | freq |
|---|---|---|---|---|
| market_data | 수급 | 1 | 외국인 순매수 추이 | 일간 |
| market_data | 수급 | 2 | 기관 순매수 추이 | 일간 |
| market_data | 주요 지수 | 3 | S&P 500 | 일간 |
| market_data | 주요 지수 | 4 | KOSPI 지수 | 일간 |
| market_data | 주요 지수 | 12 | NASDAQ | 일간 |
| market_data | 주요 지수 | 13 | 다우존스 | 일간 |
| market_data | 주요 지수 | 14 | 코스닥 지수 | 일간 |
| market_data | 주요 지수 | 15 | 니케이 225 | 일간 |
| market_data | 주요 지수 | 16 | 항셍 지수 | 일간 |
| market_data | 원자재 | 20 | 금 (Gold) | 일간 |
| market_data | 원자재 | 21 | 원유 (WTI) | 일간 |
| market_data | 원자재 | 22 | 은 (Silver) | 일간 |
| market_data | 원자재 | 23 | 구리 (Copper) | 일간 |
| market_data | 원자재 | 24 | 천연가스 | 일간 |
| market_data | 암호화폐 | 25 | 비트코인 (BTC) | 일간 |
| market_data | 암호화폐 | 26 | 이더리움 (ETH) | 일간 |
| macro | 금리 | 6 | 미국 기준금리 (Fed Funds Rate) | 주간 |
| macro | 금리 | 7 | 미국 10년 국채 금리 | 일간 |
| macro | 금리 | 30 | 미국 2년 국채 금리 | 일간 |
| macro | 금리 | 37 | 30년 모기지 금리 | 주간 |
| macro | 환율/변동성 | 8 | VIX (공포지수) | 일간 |
| macro | 환율/변동성 | 9 | 원/달러 환율 | 일간 |
| macro | 환율/변동성 | 38 | 달러/유로 환율 | 일간 |
| macro | 환율/변동성 | 39 | 달러 인덱스 (DXY) | 일간 |
| macro | 고용/성장 | 31 | 실업률 | 월간 |
| macro | 고용/성장 | 32 | 비농업 고용 (NFP) | 월간 |
| macro | 고용/성장 | 34 | 실질 GDP | 분기 |
| macro | 고용/성장 | 35 | 산업생산지수 | 월간 |
| macro | 물가/주택 | 33 | 소비자물가지수 (CPI) | 월간 |
| macro | 물가/주택 | 36 | 주택착공건수 | 월간 |
| technical | 기술적 | 10 | RSI (14일) | 일간 |
| technical | 기술적 | 40 | MACD | 일간 |
| technical | 기술적 | 41 | 스토캐스틱 %K | 일간 |
| technical | 기술적 | 42 | 볼린저 밴드 %B | 일간 |
| technical | 기술적 | 43 | ATR (평균진폭) | 일간 |
| technical | 기술적 | 44 | OBV (거래량 누적) | 일간 |
| technical | 기술적 | 45 | SMA 50일 | 일간 |
| technical | 기술적 | 46 | SMA 200일 | 일간 |
| technical | 기술적 | 47 | EMA 12일 | 일간 |
| fundamental | 펀더멘털 | 5 | EPS 추이 | 분기 |
| fundamental | 펀더멘털 | 50 | PER (주가수익비율) | 분기 |
| fundamental | 펀더멘털 | 51 | PBR (주가순자산비율) | 분기 |
| fundamental | 펀더멘털 | 52 | ROE (자기자본이익률) | 분기 |
| fundamental | 펀더멘털 | 53 | ROA (총자산이익률) | 분기 |
| fundamental | 펀더멘털 | 54 | 부채비율 (Debt/Equity) | 분기 |
| fundamental | 펀더멘털 | 55 | 잉여현금흐름 (FCF) | 분기 |
| fundamental | 펀더멘털 | 56 | 배당수익률 | 분기 |
| fundamental | 펀더멘털 | 57 | 영업이익률 | 분기 |
| fundamental | 펀더멘털 | 58 | 매출성장률 (YoY) | 분기 |
| fundamental | 재무 체질 | 60 | 매출총이익률 (Gross Margin) | 분기 |
| fundamental | 재무 체질 | 61 | 순이익률 (Net Margin) | 분기 |
| fundamental | 재무 체질 | 62 | ROIC (투하자본이익률) | 분기 |
| fundamental | 재무 체질 | 63 | 유동비율 (Current Ratio) | 분기 |
| fundamental | 재무 체질 | 64 | 이자보상배율 | 분기 |
| fundamental | 재무 체질 | 65 | 순부채/EBITDA | 분기 |
| fundamental | 재무 체질 | 66 | FCF 마진 | 분기 |
| fundamental | 밸류에이션 | 67 | EV/EBITDA | 분기 |
| fundamental | 밸류에이션 | 68 | FCF 수익률 | 분기 |
| fundamental | 성장 | 69 | 영업이익 성장률 | 분기 |
| fundamental | 운영 효율 | 70 | 매출채권 회전일수 (DSO) | 분기 |
| fundamental | 운영 효율 | 71 | 총자산회전율 | 분기 |
| fundamental | 이익 품질 | 72 | 발생액 비율 (Accruals) | 분기 |
| fundamental | 주주환원 | 73 | 순주주수익률 | 분기 |
| sentiment | 심리 | 11 | 뉴스 센티먼트 | 일간 |

**id 누락 또는 불일치: 없음.**

### 2. Category 구조 차이 (의도적, but 모니터링 필요)

- BE는 `CATEGORY_LABELS` 5분류 (market_data, macro, technical, fundamental, sentiment).
- FE는 UX 그루핑 17분류 (수급/주요 지수/원자재/암호화폐/금리/환율·변동성/고용·성장/물가·주택/기술적/펀더멘털/재무 체질/밸류에이션/성장/운영 효율/이익 품질/주주환원/심리).
- 불일치는 아니지만 **신규 지표 추가 시 BE 5분류 + FE 17분류 중 어디에 들어갈지 결정 규칙이 코드 어디에도 명시되지 않음.** 운영 시 분류 누락 위험.

### 3. description은 FE 미러에 없음

- BE에는 description 64개 모두 보유.
- FE `CatalogIndicator` 인터페이스에는 `description` 필드 자체가 없음 → FE BottomSheet는 지표 이름·빈도·카테고리만 노출.
- 영향: 사용자가 FE에서 지표 의미를 알 수 없음. 관제실/추천 패널 등 다른 곳에서는 BE에서 description을 가져와야 한다.

---

## description 품질

- 64개 모두 보유.
- 최소 길이: id 14 (코스닥 지수) "한국 중소형 성장주 시장 지수." (17자).
- 모두 마침표 종결, 한 줄.
- **빈 description: 0건. < 10자: 0건. < 20자: 1건 (id 14).**

판정: 양호. id 14만 약간 짧지만 의미 전달은 충분.

---

## keyword_rules 고아

### BE `thesis/services/indicator_matcher.py::KEYWORD_RULES`

- 룰 수: **11개**
- 룰이 가리키는 카탈로그 이름 (모두 카탈로그에 존재함):
  1. 외국인 순매수 추이 (id 1) ✓
  2. 미국 기준금리 (Fed Funds Rate) (id 6) ✓
  3. 미국 10년 국채 금리 (id 7) ✓
  4. VIX (공포지수) (id 8) ✓
  5. 원/달러 환율 (id 9) ✓
  6. RSI (14일) (id 10) ✓
  7. 뉴스 센티먼트 (id 11) ✓
  8. EPS 추이 (id 5) ✓
  9. 기관 순매수 추이 (id 2) ✓
  10. S&P 500 (id 3) ✓
  11. KOSPI 지수 (id 4) ✓

**고아 규칙: 없음.**

### BE 커버리지 (심각)

- 카탈로그 64개 중 룰이 가리키는 ID 집합: **{1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11} = 11개 (17.2%)**
- **매칭 불가능 (unreachable) 53개**:
  - 시장 데이터/원자재 미커버: 12, 13, 14, 15, 16, 20, 21, 22, 23, 24
  - 암호화폐 미커버: 25, 26
  - 거시 미커버: 30, 31, 32, 33, 34, 35, 36, 37, 38, 39
  - 기술적 미커버 (RSI 외): 40, 41, 42, 43, 44, 45, 46, 47
  - 펀더멘털 미커버 (EPS 외): 50, 51, 52, 53, 54, 55, 56, 57, 58, 60–73
- 결과: `match_indicators_for_premise()`는 사실상 11개 옛 지표만 자동 매칭. 나머지는 LLM이 `indicator_db_id`를 명시한 경로(`match_indicators_for_llm`의 1순위 PK 매칭)에서만 살아남는다.
- `match_by_gemini` fallback은 환각 위험으로 `match_indicators_for_llm()`에서 의도적으로 비활성화 (코드 주석 명시).

### FE `frontend/components/thesis/AddIndicatorSheet.tsx::KEYWORD_INDICATOR_MAP`

- 룰 수: **28개**
- 모든 `indicatorIds`가 FE 카탈로그(=BE와 동일)에 존재함 ✓
- 커버하는 ID 집합:
  `{1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 15, 16, 20, 21, 23, 24, 25, 26, 30, 31, 32, 33, 34, 35, 36, 37, 39, 40, 50, 51, 52, 53, 54, 55, 56, 57, 58, 60, 61, 62, 63, 64, 65, 66, 67, 68, 69, 70, 71, 72, 73}` = **53개 (82.8%)**
- 미커버 (FE): 13, 14, 22, 38, 41, 42, 43, 44, 45, 46, 47 (대부분 기술적 + 일부 지수/원자재/환율). 그러나 FE는 키워드 매칭이 없어도 카탈로그 전체를 UI에서 보여주므로 unreachable이 아님.

### BE ↔ FE 룰 비대칭 (가장 큰 부채)

| 채널 | 룰 수 | 커버 지표 | 미커버 지표 |
|------|-------|----------|------------|
| BE `KEYWORD_RULES` | 11 | 11/64 (17%) | 53개 |
| FE `KEYWORD_INDICATOR_MAP` | 28 | 53/64 (83%) | 11개 (UI 카탈로그에서 표시) |

- **결과**: 동일 전제 텍스트라도 FE에선 적절한 지표가 "전제 관련 추천" 영역에 뜨고, BE 자동 매칭(`match_by_keywords`)은 11개 옛 지표만 반환. 가설 빌더 자동 추천 흐름의 일관성에 균열.
- 권장: BE `KEYWORD_RULES`를 FE `KEYWORD_INDICATOR_MAP`과 동일한 28개 룰로 확장하거나, **단일 소스(JSON/YAML 카탈로그 + 룰)에서 BE/FE를 모두 생성**하는 빌드 패턴 도입 검토 (CLAUDE.md 버그 #15: 캐시 키 불일치와 동일 패턴 — 단일 소스 원칙).

---

## data_params 형식

### BE `INDICATOR_CATALOG` data_source/data_params 분포

| data_source | 개수 | 비고 |
|-------------|------|------|
| fmp | 36 | 시장 데이터(수급/지수/원자재/암호화폐), VIX/환율, 기술적, 일부 펀더멘털(5, 50–58) |
| fred | 12 | 금리(6, 7, 30, 37), 환율 일부(38), 거시(31, 32, 34, 35, 33, 36) |
| metrics | 14 | id 60–73 — `quarterly_metric_fetcher`/validation/metrics 경로 |
| news_sentiment | 1 | id 11 |
| (data_source 없음) | 1 | id 39 (`DX-Y.NYB`)는 fmp로 분류되지만 실제 FMP에서 이 심볼 fetch 가능 여부 별도 확인 필요 |

### 알려진 #14 회귀 패턴 (audit_note로 방어 중)

| id | 지표 | data_params | 주의 |
|----|------|-------------|------|
| 50 | PER | `metric=earningsYieldTTM, inverse=True` | ✅ audit_note 명시 (PER = 1/earningsYieldTTM) |
| 52 | ROE | `metric=returnOnEquityTTM, scale_multiplier=100` | ✅ audit_note 명시 (0~1 → %) |
| 53 | ROA | `metric=returnOnAssetsTTM, scale_multiplier=100` | ✅ audit_note 명시 |
| 58 | 매출성장률 YoY | `metric=growthRevenue, endpoint='financial-growth', scale_multiplier=100` | ⚠ 표준 key-metrics-ttm 아님. **실 FMP fetcher가 endpoint 분기를 처리하는지 별도 확인 권장**. 권장 대안: `data_source='metrics'`로 이전 (`revenue_growth_yoy` RATIO_METRICS 사용) — 코드 주석에도 표기됨 |

### 추가 위험 포인트

1. **id 39 (DXY) 심볼**: `DX-Y.NYB`는 FMP 표준 quotes 응답에서 안 받아질 수 있음. 다른 DXY 심볼(`^DXY`, `DXY`)도 함께 시도해보는 fallback 권장. (보고서만, 코드 미수정.)
2. **id 9 (USDKRW), id 38 (DEXUSEU)**: 9는 fmp, 38은 fred. 두 환율의 source가 다른 점이 의도된 것인지 운영 확인 권장.
3. **`metrics` 경로 (60–73)**: `data_params={'metric_code': '...'}`. `metric_code`가 `metrics` 앱(`validation/metrics`)의 메타데이터 키와 1:1 일치해야 한다. 본 보고서는 read-only이므로 실제 metric_code 존재 여부는 미검증 — 별도 감사 필요.
4. **`fmp` 펀더멘털 (5, 51, 54, 55, 56, 57)**: data_params에 audit_note가 없지만 FMP key-metrics-ttm 필드명(`pbRatioTTM`, `debtToEquityTTM`, `freeCashFlowTTM`, `dividendYieldTTM`, `operatingProfitMarginTTM`)이 실제 응답 키와 일치하는지 정기 회귀 점검 권장.
5. **FE에는 data_params가 없음**: FE 미러는 id/name/category/freq만 가짐 → 형식 불일치 자체가 발생하지 않음. 모든 데이터 fetch는 BE에서 수행.

### 권장 후속

| 우선순위 | 항목 | 작업 |
|---------|------|------|
| P0 | id 58 endpoint 분기 검증 | `quarterly_metric_fetcher`/FMP service에서 `endpoint='financial-growth'`를 실제로 수용하는지 확인. 미수용 시 호출 시점에 무음 실패 |
| P1 | BE `KEYWORD_RULES` 확장 | FE 28룰 수준으로 확장 또는 단일 소스 생성 패턴 도입 |
| P1 | id 39 DXY 심볼 회귀 점검 | FMP에서 `DX-Y.NYB` 실제 응답 확인 |
| P2 | FE 카탈로그에 description 노출 | 사용자 이해도 향상 (현재 이름만 보임) |
| P2 | 카테고리 매핑 단일 소스화 | BE 5분류 ↔ FE 17분류 매핑을 코드 외부로 분리 |
| P3 | metrics(60–73) `metric_code` 존재 검증 | validation/metrics 메타데이터와 cross-check |

---

## 결론

- **양적 동기화는 완벽**: ID/이름/빈도 64개 모두 일치, description 누락 없음, 양쪽 모두 카탈로그 외부를 가리키는 고아 룰 없음.
- **질적 일관성은 부분 부채**:
  1. BE 키워드 매칭 룰이 11개에 머물러 카탈로그의 83%가 자동 매칭 불가능.
  2. FE 키워드 룰은 28개로 BE보다 풍부 → 동일 전제에 대해 채널별 추천 결과가 달라질 수 있음.
  3. `metrics`(60–73) 경로의 `metric_code`와 fmp 펀더멘털(58 등)의 endpoint 분기는 실제 fetcher 동작 검증이 필요한 잠재 회귀 지점.
- **단기 권장**: id 58 endpoint 분기 검증(P0), BE `KEYWORD_RULES` 확장 또는 단일 소스화(P1).
