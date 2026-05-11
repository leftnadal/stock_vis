# 지표 카탈로그 동기화 감사 보고서

> 감사일: 2026-04-14  
> 감사 대상 파일:
> - BE 정의: `thesis/services/prompt_builder.py` — `INDICATOR_CATALOG`
> - BE 후처리: `thesis/services/llm_postprocess.py` — normalize/validate
> - BE 매칭: `thesis/services/indicator_matcher.py` — `KEYWORD_RULES`
> - FE 표시: `frontend/components/thesis/AddIndicatorSheet.tsx` — `INDICATOR_CATALOG`

---

## 1. 요약 (동기화 상태)

| 항목 | 상태 | 비고 |
|------|------|------|
| ID 동기화 | ✅ 완전 일치 | BE 64개 = FE 64개, 동일 ID 세트 |
| Name 동기화 | ⚠️ **4건 불일치** | 금리 3건 + 부채비율 1건 |
| Category 체계 | ℹ️ 의도적 차이 | BE 5개(영문) vs FE 17개(한글, UI용 세분화) |
| Description 품질 | ✅ 양호 | 64개 전부 비어있지 않음, 최소 15자 이상 |
| BE keyword_rules 커버리지 | ⚠️ **17% (11/64)** | FE는 83% (53/64) — 심각한 격차 |
| data_params 형식 | ⚠️ **2건 의심** | `foreign_net_buy`, `institutional_net_buy` — FMP에 미존재 |

**종합 판정: ⚠️ 경미한 불일치 4건 + 구조적 격차 1건**

---

## 2. BE ↔ FE 불일치 목록

### 2.1 Name 불일치 (4건)

| ID | BE (`prompt_builder.py`) | FE (`AddIndicatorSheet.tsx`) | 위험도 |
|----|--------------------------|------------------------------|--------|
| 6 | `미국 기준금리 (Fed Funds Rate)` | `미국 기준금리` | 중 |
| 7 | `미국 10년 국채 금리` | `미국 10년 국채` | 중 |
| 30 | `미국 2년 국채 금리` | `미국 2년 국채` | 중 |
| 54 | `부채비율 (Debt/Equity)` | `부채비율 (D/E)` | 낮음 |

**영향 분석:**
- **ID 기반 매칭 경로** (`get_indicator_by_id`): 영향 없음 — ID로 조회하므로 이름 무관
- **이름 기반 매칭 경로** (`_find_in_catalog(name)`): FE에서 FE 이름으로 저장 후 BE에서 이름 검색 시 불일치 가능
- **사용자 표시**: FE에서 선택한 지표 이름과 BE에서 반환하는 이름이 다르게 표시될 수 있음

### 2.2 ID 불일치

없음. BE와 FE 모두 동일한 64개 ID 세트를 사용.

```
공통 ID: 1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,
         20,21,22,23,24,25,26,
         30,31,32,33,34,35,36,37,38,39,
         40,41,42,43,44,45,46,47,
         50,51,52,53,54,55,56,57,58,
         60,61,62,63,64,65,66,67,68,69,70,71,72,73
```

### 2.3 Category 체계 차이 (의도적)

| BE category (영문, 5개) | FE category (한글, 17개) |
|-------------------------|--------------------------|
| `market_data` | 수급, 주요 지수, 원자재, 암호화폐 |
| `macro` | 금리, 환율/변동성, 고용/성장, 물가/주택 |
| `technical` | 기술적 |
| `fundamental` | 펀더멘털, 재무 체질, 밸류에이션, 성장, 운영 효율, 이익 품질, 주주환원 |
| `sentiment` | 심리 |

FE가 UI 표시용으로 세분화한 것으로 판단됨. BE `CATEGORY_LABELS` 매핑과 일치하며 기능적 문제 없음.

---

## 3. Description 품질

### 3.1 빈 description

없음. 64개 전부 description 필드가 존재하며 비어있지 않음.

### 3.2 짧은 description (< 20자)

없음. 가장 짧은 description:

| ID | Name | Description | 길이 |
|----|------|-------------|------|
| 14 | 코스닥 지수 | 한국 중소형 성장주 시장 지수. | 15자 |
| 4 | KOSPI 지수 | 한국 유가증권시장 전체 종목 시가총액 가중 지수. | 22자 |

이 수준은 허용 범위 내이나, id 14의 description은 다른 지표 대비 상대적으로 빈약함.

### 3.3 FE description 부재

FE `AddIndicatorSheet.tsx`의 `CatalogIndicator` 타입에는 `description` 필드가 없음.
현재 FE에서 description을 표시하지 않으므로 기능적 문제는 없으나, 향후 툴팁/상세 설명 표시 시 BE에서 가져오거나 FE 카탈로그에 추가 필요.

---

## 4. keyword_rules 분석

### 4.1 BE KEYWORD_RULES 커버리지 (indicator_matcher.py)

**11개 규칙 그룹, 11개 고유 지표 커버 (17%)**

| 규칙 키워드 그룹 | 매칭 지표 (name) | ID |
|------------------|------------------|----|
| 외국인, 외인, 순매수... | 외국인 순매수 추이 | 1 |
| 금리, 연준, FOMC... | 미국 기준금리, 미국 10년 국채 | 6, 7 |
| VIX, 공포, 변동성... | VIX (공포지수) | 8 |
| 환율, 달러, 원달러... | 원/달러 환율 | 9 |
| RSI, MACD, 기술적... | RSI (14일) | 10 |
| 센티먼트, 여론, 뉴스... | 뉴스 센티먼트 | 11 |
| 실적, EPS, 매출... | EPS 추이 | 5 |
| 기관, 기관투자자... | 기관 순매수 추이 | 2 |
| S&P, 나스닥... | S&P 500 | 3 |
| 코스피, KOSPI... | KOSPI 지수 | 4 |
| 선거, 정치, 정책... | VIX + KOSPI | 8, 4 |

### 4.2 FE KEYWORD_INDICATOR_MAP 커버리지 (AddIndicatorSheet.tsx)

**28개 규칙 그룹, 53개 고유 지표 커버 (83%)**

### 4.3 BE keyword_rules에 없는 지표 (53개 — 고아 지표)

BE KEYWORD_RULES로 텍스트 매칭되지 않는 지표:

| 카테고리 | 미커버 지표 (ID) |
|---------|-----------------|
| 주요 지수 | NASDAQ(12), 다우존스(13), 코스닥(14), 니케이(15), 항셍(16) |
| 원자재 | 금(20), 원유(21), 은(22), 구리(23), 천연가스(24) |
| 암호화폐 | 비트코인(25), 이더리움(26) |
| 금리 | 2년 국채(30), 30년 모기지(37) |
| 환율 | 달러/유로(38), DXY(39) |
| 고용/성장 | 실업률(31), NFP(32), GDP(34), 산업생산(35) |
| 물가/주택 | CPI(33), 주택착공(36) |
| 기술적 | MACD(40), 스토캐스틱(41), 볼린저(42), ATR(43), OBV(44), SMA 50(45), SMA 200(46), EMA 12(47) |
| 펀더멘털 | PER(50), PBR(51), ROE(52), ROA(53), 부채비율(54), FCF(55), 배당(56), 영업이익률(57), 매출성장률(58) |
| 재무 체질 | 60~73 전부 (14개) |

**영향:** LLM이 `indicator_db_id`를 제공하지 않고 키워드 매칭 fallback에 의존하는 경우, 위 53개 지표는 BE에서 매칭 불가. 단, `match_indicators_for_llm`은 PK 매칭 실패 시에만 keyword fallback을 사용하고, LLM 빌더에서는 주로 PK 경로를 사용하므로 실질적 영향은 제한적.

### 4.4 FE KEYWORD_INDICATOR_MAP에 없는 지표 (11개)

FE 키워드 규칙에서 참조되지 않는 지표:

| ID | Name | 비고 |
|----|------|------|
| 13 | 다우존스 | S&P/NASDAQ 규칙에 포함 안 됨 |
| 14 | 코스닥 지수 | KOSPI 규칙에 포함 안 됨 |
| 22 | 은 (Silver) | 금/구리는 있으나 은은 빠짐 |
| 38 | 달러/유로 환율 | 환율 규칙에 DXY(39)만 포함 |
| 41 | 스토캐스틱 %K | RSI/MACD 규칙에 포함 안 됨 |
| 42 | 볼린저 밴드 %B | 동일 |
| 43 | ATR (평균진폭) | 동일 |
| 44 | OBV (거래량 누적) | 동일 |
| 45 | SMA 50일 | 이동평균 키워드 있으나 참조 ID에 미포함 |
| 46 | SMA 200일 | 동일 |
| 47 | EMA 12일 | 동일 |

이 지표들은 전제 기반 추천("Sparkles 전제 관련 추천")에 등장하지 않으며, 전체 카탈로그 목록에서 수동 선택만 가능.

---

## 5. data_params 형식 분석

### 5.1 data_source별 분포

| data_source | 지표 수 | params 형식 |
|-------------|---------|-------------|
| `fmp` (symbol) | 17 | `{'symbol': '...' }` |
| `fmp` (metric) | 13 | `{'metric': '...' }` |
| `fmp` (indicator) | 9 | `{'indicator': '...', 'period': N}` |
| `fred` | 10 | `{'series_id': '...' }` |
| `metrics` | 14 | `{'metric_code': '...' }` |
| `news_sentiment` | 1 | `{}` |
| **합계** | **64** | |

### 5.2 의심 항목

#### (a) FMP에 존재하지 않는 metric (위험: 높음)

| ID | Name | data_params | 문제 |
|----|------|-------------|------|
| 1 | 외국인 순매수 추이 | `{'metric': 'foreign_net_buy'}` | FMP에 해당 metric 없음. 한국 시장 전용 데이터로 별도 수집원 필요 |
| 2 | 기관 순매수 추이 | `{'metric': 'institutional_net_buy'}` | 동일. FMP는 기관 보유 비중만 제공 (13F), 일별 순매수 미제공 |

이 두 지표는 `data_source: 'fmp'`로 설정되어 있지만 FMP API에서 직접 제공하지 않는 데이터. 실제 데이터 페칭 시 실패할 가능성 높음.

#### (b) FMP 심볼 형식 확인 필요 (위험: 낮음)

| ID | Symbol | 비고 |
|----|--------|------|
| 20 | `GCUSD` | FMP 금 선물 — 일부 환경에서 `XAUUSD` 사용 |
| 21 | `CLUSD` | FMP 원유 선물 — 일부 환경에서 `WTICOUSD` 사용 |
| 22 | `SIUSD` | FMP 은 선물 |
| 23 | `HGUSD` | FMP 구리 선물 |
| 24 | `NGUSD` | FMP 천연가스 선물 |
| 39 | `DX-Y.NYB` | 달러 인덱스 — FMP에서 지원 여부 확인 필요 |

이 심볼들은 FMP의 commodity 엔드포인트에서 사용하는 형식과 일치하는지 실제 API 호출로 검증 필요.

#### (c) metrics data_source 연동 (위험: 미확인)

ID 60~73 (14개)은 `data_source: 'metrics'`를 사용하며 `metric_code`로 내부 metrics 시스템 참조. 실제 `metrics` 앱의 `MetricDefinition` 모델에 해당 코드가 등록되어 있는지 별도 검증 필요.

#### (d) FMP 펀더멘털 metric명 (위험: 낮음)

FMP Key Metrics TTM 엔드포인트 필드명과의 일치를 가정. 참고: CLAUDE.md 버그 #14에서 FMP 필드명 불일치 이력 있음.

| ID | metric | FMP 예상 필드 | 일치 여부 |
|----|--------|--------------|----------|
| 50 | `peRatioTTM` | `peRatioTTM` | ✅ |
| 51 | `pbRatioTTM` | `pbRatioTTM` | ✅ |
| 52 | `returnOnEquityTTM` | `returnOnEquityTTM` | ✅ (×100 변환 필요 — 버그 #14) |
| 53 | `returnOnAssetsTTM` | `returnOnAssetsTTM` | ✅ |
| 54 | `debtToEquityTTM` | `debtToEquityTTM` | ✅ |
| 55 | `freeCashFlowTTM` | ⚠️ TTM 엔드포인트에 없을 수 있음 | 확인 필요 |
| 56 | `dividendYieldTTM` | `dividendYieldTTM` | ✅ |
| 57 | `operatingProfitMarginTTM` | ⚠️ `operatingProfitMargin` vs TTM 접미사 | 확인 필요 |
| 58 | `revenueGrowthYoY` | ⚠️ FMP Key Metrics에 미포함 — 별도 계산 필요 | 확인 필요 |

---

## 6. 기타 발견 사항

### 6.1 BE `match_by_gemini` 환각 방지 장치

`indicator_matcher.py:match_indicators_for_llm` (line 307)에서 Gemini fallback을 의도적으로 제외함:
```python
# (match_by_gemini fallback은 카탈로그에 없는 환각 지표를 생성하므로 제외)
```
이는 CLAUDE.md 피드백 "LLM 지표 환각 방지"와 일치. 그러나 `match_indicators_for_premise` (line 257~268)은 여전히 Gemini fallback을 사용 — 이 경로는 사용자 직접 호출 시에만 실행되므로 허용 범위.

### 6.2 `llm_postprocess.py`의 indicator_db_id 검증

line 83~89에서 `get_indicator_by_id(db_id)`로 카탈로그에 없는 ID를 None으로 교정. 이 방어 로직은 정상 동작.

### 6.3 INDICATOR_FREQUENCY (prompt_builder.py) vs FE freq

BE `INDICATOR_FREQUENCY` dict와 FE `CatalogIndicator.freq` 필드가 동일한 값을 사용하는지 확인:

| ID | BE freq | FE freq | 일치 |
|----|---------|---------|------|
| 1 | 일간 | 일간 | ✅ |
| 6 | 주간 | 주간 | ✅ |
| 5 | 분기 | 분기 | ✅ |
| 31 | 월간 | 월간 | ✅ |

전수 검사: **64개 전부 일치**

---

## 7. 권고 사항 (우선순위순)

### P0 — 즉시 수정

1. **Name 불일치 4건 통일** — BE 또는 FE 한쪽으로 통일
   - 권장: FE를 BE에 맞춤 (BE가 data_source/data_params와 함께 정의의 원천이므로)
   - 대상: id 6, 7, 30, 54

### P1 — 단기 개선

2. **BE KEYWORD_RULES 확장** — FE 수준(28개 규칙)으로 확대하거나, PK 매칭 경로를 더 강화
   - 현재 BE 11개 규칙 vs FE 28개 규칙의 격차가 큼
   - BE keyword fallback이 필요한 시나리오에서 사용자 경험 저하

3. **data_params 검증** — id 1, 2의 `foreign_net_buy`, `institutional_net_buy` metric이 실제 페칭 가능한지 확인
   - 불가능하면 `data_source`를 `manual`로 변경하거나 대체 데이터 소스 연결

### P2 — 중기 개선

4. **FE KEYWORD_INDICATOR_MAP 빈틈** — 은(22), 스토캐스틱(41), 볼린저(42), ATR(43), OBV(44), SMA(45,46), EMA(47) 등 11개 지표를 키워드 규칙에 추가

5. **FMP 심볼 검증** — 원자재 심볼(GCUSD, CLUSD 등)과 DX-Y.NYB의 실제 API 응답 확인

6. **metrics 연동 검증** — id 60~73의 `metric_code`가 metrics 앱 `MetricDefinition`에 등록되어 있는지 확인

---

## 부록: 전체 카탈로그 비교표

| ID | BE Name | FE Name | Name 일치 | BE KEYWORD | FE KEYWORD |
|----|---------|---------|-----------|------------|------------|
| 1 | 외국인 순매수 추이 | 외국인 순매수 추이 | ✅ | ✅ | ✅ |
| 2 | 기관 순매수 추이 | 기관 순매수 추이 | ✅ | ✅ | ✅ |
| 3 | S&P 500 | S&P 500 | ✅ | ✅ | ✅ |
| 4 | KOSPI 지수 | KOSPI 지수 | ✅ | ✅ | ✅ |
| 5 | EPS 추이 | EPS 추이 | ✅ | ✅ | ✅ |
| 6 | 미국 기준금리 (Fed Funds Rate) | 미국 기준금리 | ❌ | ✅ | ✅ |
| 7 | 미국 10년 국채 금리 | 미국 10년 국채 | ❌ | ✅ | ✅ |
| 8 | VIX (공포지수) | VIX (공포지수) | ✅ | ✅ | ✅ |
| 9 | 원/달러 환율 | 원/달러 환율 | ✅ | ✅ | ✅ |
| 10 | RSI (14일) | RSI (14일) | ✅ | ✅ | ✅ |
| 11 | 뉴스 센티먼트 | 뉴스 센티먼트 | ✅ | ✅ | ✅ |
| 12 | NASDAQ | NASDAQ | ✅ | ❌ | ✅ |
| 13 | 다우존스 | 다우존스 | ✅ | ❌ | ❌ |
| 14 | 코스닥 지수 | 코스닥 지수 | ✅ | ❌ | ❌ |
| 15 | 니케이 225 | 니케이 225 | ✅ | ❌ | ✅ |
| 16 | 항셍 지수 | 항셍 지수 | ✅ | ❌ | ✅ |
| 20 | 금 (Gold) | 금 (Gold) | ✅ | ❌ | ✅ |
| 21 | 원유 (WTI) | 원유 (WTI) | ✅ | ❌ | ✅ |
| 22 | 은 (Silver) | 은 (Silver) | ✅ | ❌ | ❌ |
| 23 | 구리 (Copper) | 구리 (Copper) | ✅ | ❌ | ✅ |
| 24 | 천연가스 | 천연가스 | ✅ | ❌ | ✅ |
| 25 | 비트코인 (BTC) | 비트코인 (BTC) | ✅ | ❌ | ✅ |
| 26 | 이더리움 (ETH) | 이더리움 (ETH) | ✅ | ❌ | ✅ |
| 30 | 미국 2년 국채 금리 | 미국 2년 국채 | ❌ | ❌ | ✅ |
| 31 | 실업률 | 실업률 | ✅ | ❌ | ✅ |
| 32 | 비농업 고용 (NFP) | 비농업 고용 (NFP) | ✅ | ❌ | ✅ |
| 33 | 소비자물가지수 (CPI) | 소비자물가지수 (CPI) | ✅ | ❌ | ✅ |
| 34 | 실질 GDP | 실질 GDP | ✅ | ❌ | ✅ |
| 35 | 산업생산지수 | 산업생산지수 | ✅ | ❌ | ✅ |
| 36 | 주택착공건수 | 주택착공건수 | ✅ | ❌ | ✅ |
| 37 | 30년 모기지 금리 | 30년 모기지 금리 | ✅ | ❌ | ✅ |
| 38 | 달러/유로 환율 | 달러/유로 환율 | ✅ | ❌ | ❌ |
| 39 | 달러 인덱스 (DXY) | 달러 인덱스 (DXY) | ✅ | ❌ | ✅ |
| 40 | MACD | MACD | ✅ | ❌ | ✅ |
| 41 | 스토캐스틱 %K | 스토캐스틱 %K | ✅ | ❌ | ❌ |
| 42 | 볼린저 밴드 %B | 볼린저 밴드 %B | ✅ | ❌ | ❌ |
| 43 | ATR (평균진폭) | ATR (평균진폭) | ✅ | ❌ | ❌ |
| 44 | OBV (거래량 누적) | OBV (거래량 누적) | ✅ | ❌ | ❌ |
| 45 | SMA 50일 | SMA 50일 | ✅ | ❌ | ❌ |
| 46 | SMA 200일 | SMA 200일 | ✅ | ❌ | ❌ |
| 47 | EMA 12일 | EMA 12일 | ✅ | ❌ | ❌ |
| 50 | PER (주가수익비율) | PER (주가수익비율) | ✅ | ❌ | ✅ |
| 51 | PBR (주가순자산비율) | PBR (주가순자산비율) | ✅ | ❌ | ✅ |
| 52 | ROE (자기자본이익률) | ROE (자기자본이익률) | ✅ | ❌ | ✅ |
| 53 | ROA (총자산이익률) | ROA (총자산이익률) | ✅ | ❌ | ✅ |
| 54 | 부채비율 (Debt/Equity) | 부채비율 (D/E) | ❌ | ❌ | ✅ |
| 55 | 잉여현금흐름 (FCF) | 잉여현금흐름 (FCF) | ✅ | ❌ | ✅ |
| 56 | 배당수익률 | 배당수익률 | ✅ | ❌ | ✅ |
| 57 | 영업이익률 | 영업이익률 | ✅ | ❌ | ✅ |
| 58 | 매출성장률 (YoY) | 매출성장률 (YoY) | ✅ | ❌ | ✅ |
| 60 | 매출총이익률 (Gross Margin) | 매출총이익률 (Gross Margin) | ✅ | ❌ | ✅ |
| 61 | 순이익률 (Net Margin) | 순이익률 (Net Margin) | ✅ | ❌ | ✅ |
| 62 | ROIC (투하자본이익률) | ROIC (투하자본이익률) | ✅ | ❌ | ✅ |
| 63 | 유동비율 (Current Ratio) | 유동비율 (Current Ratio) | ✅ | ❌ | ✅ |
| 64 | 이자보상배율 | 이자보상배율 | ✅ | ❌ | ✅ |
| 65 | 순부채/EBITDA | 순부채/EBITDA | ✅ | ❌ | ✅ |
| 66 | FCF 마진 | FCF 마진 | ✅ | ❌ | ✅ |
| 67 | EV/EBITDA | EV/EBITDA | ✅ | ❌ | ✅ |
| 68 | FCF 수익률 | FCF 수익률 | ✅ | ❌ | ✅ |
| 69 | 영업이익 성장률 | 영업이익 성장률 | ✅ | ❌ | ✅ |
| 70 | 매출채권 회전일수 (DSO) | 매출채권 회전일수 (DSO) | ✅ | ❌ | ✅ |
| 71 | 총자산회전율 | 총자산회전율 | ✅ | ❌ | ✅ |
| 72 | 발생액 비율 (Accruals) | 발생액 비율 (Accruals) | ✅ | ❌ | ✅ |
| 73 | 순주주수익률 | 순주주수익률 | ✅ | ❌ | ✅ |

**통계:**
- Name 일치: 60/64 (93.8%)
- BE KEYWORD 커버: 11/64 (17.2%)
- FE KEYWORD 커버: 53/64 (82.8%)
