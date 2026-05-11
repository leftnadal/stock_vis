# 지표 카탈로그 동기화 감사 보고서

- 일자: 2026-05-04
- 범위: BE `thesis/services/prompt_builder.py` ↔ FE `frontend/components/thesis/AddIndicatorSheet.tsx` ↔ `thesis/services/indicator_matcher.py` ↔ `thesis/services/llm_postprocess.py`
- 모드: 읽기 전용 감사 (코드 수정 없음)

## 요약 (동기화 상태)

| 항목 | 상태 | 비고 |
|------|------|------|
| 카탈로그 항목 ID 동기화 | ✅ 일치 | BE 64개 / FE 64개, ID/이름/주기 100% 동일 |
| description 필드 품질 | ✅ 양호 | 64/64 항목 모두 존재, 모두 10자 이상 (최소 15자, 최대 ~70자) |
| keyword_rules 고아 규칙 | ✅ 없음 | KEYWORD_RULES 11개 그룹 모두 INDICATOR_CATALOG에 매칭됨 |
| keyword_rules 커버리지 | ⚠️ 매우 낮음 | 64개 카탈로그 중 11개만 BE 키워드 룰로 추천 가능 (53개는 사각지대) |
| BE/FE 키워드 룰 일치 | ⚠️ 큰 격차 | BE 11그룹 vs FE 30그룹 (FE가 거의 3배 풍부) |
| data_params 형식 | ⚠️ 일부 문제 | FMP 펀더멘털 metric 명 9개가 실제 FMP 응답 필드와 불일치 가능 (peRatioTTM 등) |
| INDICATOR_FREQUENCY 동기화 | ✅ 일치 | 64개 모두 BE 주기 = FE freq |

**판정**: 카탈로그 자체(ID/이름/주기) 동기화는 완벽. 문제는 (a) BE 키워드 매칭 룰의 좁은 커버리지, (b) FMP 펀더멘털 9개 metric 명이 카탈로그 정의와 실제 FMP 응답 키 사이에 다리(어댑터)가 필요하다는 점.

---

## BE ↔ FE 불일치 목록

### 카탈로그 항목 (id, name, freq) 비교

BE(`thesis/services/prompt_builder.py:14-294`)의 INDICATOR_CATALOG와 FE(`frontend/components/thesis/AddIndicatorSheet.tsx:15-91`)의 INDICATOR_CATALOG를 ID 단위로 비교.

| 검사 | 결과 |
|------|------|
| BE에만 있는 ID | (없음) |
| FE에만 있는 ID | (없음) |
| 이름 차이 | (없음) — 64개 ID 모두 한 글자도 다르지 않음 |
| 주기(freq) 차이 | (없음) — BE `INDICATOR_FREQUENCY` dict와 FE `freq` 필드 100% 일치 |

존재하는 ID(공통):
```
1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16,
20, 21, 22, 23, 24, 25, 26,
30, 31, 32, 33, 34, 35, 36, 37, 38, 39,
40, 41, 42, 43, 44, 45, 46, 47,
50, 51, 52, 53, 54, 55, 56, 57, 58,
60, 61, 62, 63, 64, 65, 66, 67, 68, 69, 70, 71, 72, 73
```

빈 ID 갭(향후 확장 예약 추정): 17–19, 27–29, 48–49, 59. 양쪽 동일.

### 카테고리 분류 차이 (의도적, 위험 없음)

BE는 5개 광역 카테고리(`market_data` / `macro` / `technical` / `fundamental` / `sentiment`)로 분류, FE는 17개 세분 UX 카테고리(`수급` / `주요 지수` / `원자재` / `암호화폐` / `금리` / `환율/변동성` / …)로 분류. **카테고리 명칭은 다르지만 동일 ID에서 의미적으로 같은 자리에 매핑**되며, 이는 화면 표시 목적의 의도된 분리이므로 동기화 결함은 아니다.

다만 FE는 `categoryOrder` 배열(`AddIndicatorSheet.tsx:211-216`)에 17개 카테고리를 명시 — FE 카탈로그에 새 카테고리 문자열을 추가할 때 `categoryOrder`에 등록하지 않으면 화면에 표시되지 않는 잠재적 함정. 현재는 모든 카테고리가 등록되어 있어 문제 없음.

### 데이터 소스/파라미터 (BE 단독)

FE는 `data_source` / `data_params`를 갖지 않고 BE에서만 정의. FE는 ID로만 BE와 통신하므로 형식 불일치는 BE 내부 문제.

---

## description 품질

### 존재 여부

BE INDICATOR_CATALOG 64개 항목 **모두** `description` 필드 보유. 빈 description: **0개**.

### 길이 통계 (한글 문자수 기준 추정)

| 구간 | 항목 수 | 예시 |
|------|--------|------|
| 10자 미만 | **0개** | (없음) |
| 10–20자 | 4개 | id 14 `'한국 중소형 성장주 시장 지수.'` (15자) |
| 20–40자 | 28개 | id 4 `'한국 유가증권시장 전체 종목 시가총액 가중 지수.'` (24자) |
| 40–70자 | 32개 | id 21, 23 등 (Dr. Copper 등 부연 설명) |
| 70자 초과 | 0개 | — |

### 주의가 필요한 항목 (짧지는 않으나 부정확/오해 소지)

| ID | 이름 | description | 의견 |
|----|------|-------------|------|
| 14 | 코스닥 지수 | "한국 중소형 성장주 시장 지수." | 정확하나 다른 항목들에 비해 정보 밀도 낮음. 'IT/바이오 비중 높음' 같은 식별 단서가 있으면 사용자 학습 가치 더 큼 |
| 24 | 천연가스 | "천연가스 선물 가격. 에너지 비용과 계절적 수요 반영." | OK |
| 50 | PER (주가수익비율) | "주가를 EPS로 나눈 값. 수익 대비 주가 수준(밸류에이션) 측정." | description은 맞지만 `data_params={'metric':'peRatioTTM'}`이 실제 FMP에서 수집되는지가 별개 이슈 (data_params 섹션 참고) |
| 58 | 매출성장률 (YoY) | "전년 동기 대비 매출 증가율. 사업 성장 속도의 기본 지표." | description은 OK이나 `metric:'revenueGrowthYoY'`는 FMP `/stable/key-metrics-ttm`/`ratios-ttm` 표준 응답 키가 아님 |

전반적으로 **description 품질은 양호**. 순수 description 길이/존재 측면의 결함은 없음.

---

## keyword_rules 고아

### KEYWORD_RULES 정의 위치

`thesis/services/indicator_matcher.py:12-154`. 11개 키워드 그룹.

### 카탈로그 매핑 검증 (이름 기반)

| 그룹 | 추천 지표 이름 | 카탈로그 ID | 매핑 상태 |
|------|---------------|-------------|----------|
| 외국인 | 외국인 순매수 추이 | 1 | ✅ |
| 금리 | 미국 기준금리 (Fed Funds Rate), 미국 10년 국채 금리 | 6, 7 | ✅ |
| VIX | VIX (공포지수) | 8 | ✅ |
| 환율 | 원/달러 환율 | 9 | ✅ |
| RSI | RSI (14일) | 10 | ✅ |
| 센티먼트 | 뉴스 센티먼트 | 11 | ✅ |
| 실적 | EPS 추이 | 5 | ✅ |
| 기관 | 기관 순매수 추이 | 2 | ✅ |
| S&P | S&P 500 | 3 | ✅ |
| 코스피 | KOSPI 지수 | 4 | ✅ |
| 선거 | VIX (공포지수), KOSPI 지수 | 8, 4 | ✅ |

**고아 규칙: 0개**. 11개 그룹의 모든 추천 이름이 INDICATOR_CATALOG에 존재.

### 그러나 — 커버리지 사각지대 (역방향)

KEYWORD_RULES가 카탈로그 64개 중 **11개만 매칭**. 키워드 룰로는 추천 불가능한 53개 지표:

- **주요 지수 5개**: 12 NASDAQ, 13 다우존스, 14 코스닥, 15 니케이 225, 16 항셍 지수
- **원자재/암호화폐 7개**: 20 금, 21 원유(WTI), 22 은, 23 구리, 24 천연가스, 25 BTC, 26 ETH
- **거시 8개**: 30 미국 2년, 31 실업률, 32 NFP, 33 CPI, 34 GDP, 35 산업생산, 36 주택착공, 37 모기지
- **환율/변동성 2개**: 38 달러/유로, 39 DXY
- **기술 8개**: 40 MACD, 41 스토캐스틱, 42 볼린저, 43 ATR, 44 OBV, 45 SMA50, 46 SMA200, 47 EMA12
- **펀더멘털 8개**: 50 PER, 51 PBR, 52 ROE, 53 ROA, 54 부채비율, 55 FCF, 56 배당수익률, 57 영업이익률, 58 매출성장률
- **재무 체질 14개**: 60–73 전부

이는 BE의 `match_indicators_for_premise()`가 **PK 직접 지정 → 키워드 룰 → (Gemini fallback 비활성)** 순서로 동작(`indicator_matcher.py:257-268`, `271-329`)하므로, LLM이 `indicator_db_id`를 명시하지 않고 키워드 룰 매칭에 떨어지는 53개 지표는 **자동 추천 누락**.

피드백 메모리(`feedback_llm_indicator_hallucination.md`) 정책상 `match_by_gemini` fallback은 의도적으로 비활성(`indicator_matcher.py:306-312` 주석 참고). 따라서 이 사각지대는 **의도된 안전장치의 부수효과**이지만, "키워드 룰 강화" 또는 "LLM이 indicator_db_id를 더 적극 채택하도록 프롬프트 보강"을 통해 보완 여지 있음.

### BE vs FE 키워드 룰 격차

`AddIndicatorSheet.tsx:109-139`의 `KEYWORD_INDICATOR_MAP`은 30개 그룹으로 BE의 11개를 상회. FE에만 있는 키워드 그룹(BE 키워드 룰 누락분):

| FE 그룹 | indicatorIds | BE에 동등 룰 존재? |
|---------|-------------|------------------|
| 유가/원유/wti/석유/에너지/opec | 21 | ❌ |
| 금/gold/금값/안전자산 | 20 | ❌ |
| 구리/copper/산업금속/경기선행 | 23 | ❌ |
| 천연가스/lng/가스 | 24 | ❌ |
| 비트코인/btc/암호화폐/크립토/코인 | 25, 26 | ❌ |
| per/pbr/밸류에이션/저평가/고평가/가치 | 50, 51, 67, 68 | ❌ |
| roe/roa/수익성/이익률/roic/마진 | 52, 53, 57, 62, 60, 61 | ❌ |
| 부채/레버리지/debt/재무건전/유동성/현금 | 54, 63, 64, 65 | ❌ |
| 배당/dividend/현금흐름/fcf/자사주/주주환원 | 55, 56, 66, 68, 73 | ❌ |
| 회전율/효율/재고/매출채권/운영 | 70, 71 | ❌ |
| 이익 품질/발생액/accrual/분식/회계 | 72, 66 | ❌ |
| 인플레/cpi/물가/소비자물가 | 33 | ❌ |
| 고용/실업/nfp/비농업/일자리 | 31, 32 | ❌ |
| gdp/성장/경기/산업생산 | 34, 35 | ❌ |
| 주택/부동산/모기지/reit | 36, 37 | ❌ |
| 반도체/테크/ai/엔비디아/nvidia/칩 | 12, 3 | ❌ |
| 중국/항셍/홍콩 | 16 | ❌ |
| 일본/니케이/엔화 | 15 | ❌ |
| 광고/디지털/플랫폼/meta/구글/google | 3, 12 | ❌ |

→ **FE 사용자는 카탈로그 거의 전부에 대해 키워드 추천을 받지만, BE LLM 빌더 경로는 11개 영역만 자동 매칭**됨. 두 경로의 추천 풍부도가 사용자 경험상 비대칭.

---

## data_params 형식

### 형식 분류 (BE INDICATOR_CATALOG)

| 형식 | 개수 | 예시 |
|------|-----|------|
| `fmp` + `symbol` | 18 | `{'symbol': '^GSPC'}` (지수/원자재/암호화폐/환율/VIX) |
| `fmp` + `indicator` | 9 | `{'indicator': 'RSI', 'period': 14}` (기술적) |
| `fmp` + `metric` | 12 | `{'metric': 'peRatioTTM'}`, `{'metric': 'foreign_net_buy'}` |
| `fred` + `series_id` | 11 | `{'series_id': 'FEDFUNDS'}` |
| `metrics` + `metric_code` | 14 | `{'metric_code': 'gross_margin'}` |
| `news_sentiment` + `{}` | 1 | id 11 |

### 1. `fmp` + `metric` 패턴 — 펀더멘털 9개 (id 50–58) 위험

CLAUDE.md `자주 발생하는 버그 #14`, `sub_claude_md/common-bugs.md:99-118`, `serverless/services/enhanced_screener_service.py:75-77`, `scripts/add_kb_lessons_screener.py:26-49`에서 명시된 사항:

> **FMP `/stable/key-metrics-ttm` / `/stable/ratios-ttm` 응답에는 `peRatioTTM` 필드가 존재하지 않음.** PE는 `earningsYieldTTM`의 역수로 계산해야 함. `returnOnEquityTTM`은 decimal(1.5 = 150%)로 반환.

INDICATOR_CATALOG의 펀더멘털 정의(`prompt_builder.py:194-229`):

| ID | name | data_params['metric'] | FMP 표준 응답 키와 일치? | 비고 |
|----|------|----------------------|------------------------|------|
| 50 | PER (주가수익비율) | `peRatioTTM` | ❌ | `earningsYieldTTM` 역수 계산 필요 |
| 51 | PBR (주가순자산비율) | `pbRatioTTM` | ⚠️ | FMP 응답에 `pbRatioTTM` 또는 `priceToBookRatioTTM` 형태로 존재 — 정확 확인 필요 |
| 52 | ROE (자기자본이익률) | `returnOnEquityTTM` | ⚠️ | 키 일치, 단 *100 변환 필요 (decimal → %) |
| 53 | ROA (총자산이익률) | `returnOnAssetsTTM` | ⚠️ | 키 일치 추정, 단위 검증 필요 |
| 54 | 부채비율 (Debt/Equity) | `debtToEquityTTM` | ⚠️ | 키 일치 추정 |
| 55 | 잉여현금흐름 (FCF) | `freeCashFlowTTM` | ⚠️ | 키 일치 추정 (단위 USD 절대값) |
| 56 | 배당수익률 | `dividendYieldTTM` | ⚠️ | decimal/percent 단위 검증 필요 |
| 57 | 영업이익률 | `operatingProfitMarginTTM` | ⚠️ | 키 일치 추정, decimal |
| 58 | 매출성장률 (YoY) | `revenueGrowthYoY` | ❌ | FMP `key-metrics-ttm` / `ratios-ttm`에 표준 키로 존재하지 않음. `/stable/income-statement-growth` 별도 endpoint 필요 |

**결론**: data_params는 "추상 metric 라벨"이며, 실제로 FMP 응답에 그대로 키로 매핑하면 id 50, 58에서 즉시 None을 받게 됨. **BE 카탈로그 정의 ↔ 실제 FMP 응답 사이를 잇는 어댑터(예: `enhanced_screener_service.py`의 `'pe_ratio': 'earningsYieldTTM'` 매핑 + 역수 변환)가 별도로 필요**한데, 카탈로그에는 그 변환 의무가 명시되지 않음.

이미 KB 레슨/CLAUDE.md/common-bugs로 동일 함정이 반복 기록되어 있으므로, 카탈로그를 사용하는 신규 코드가 같은 트랩에 빠질 가능성이 큼.

### 2. `fmp` + `metric` 패턴 — 수급 3개 (id 1, 2, 5)

| ID | metric | 비고 |
|----|--------|------|
| 1 | `foreign_net_buy` | FMP 표준 endpoint 아님. 한국 시장 외국인 수급은 FnGuide/KRX 등 별도 출처 필요. abstract label로 추정 |
| 2 | `institutional_net_buy` | 동일 |
| 5 | `eps` | FMP `quote`/`income-statement`에서 `eps`/`epsTTM` 등으로 제공되나 어느 endpoint를 가리키는지 카탈로그만으로는 불명 |

이 3개도 어댑터(또는 task 내부의 명시 매핑)가 없으면 작동하지 않음.

### 3. `metrics` + `metric_code` 패턴 — id 60–73 (14개)

이 14개는 외부 FMP가 아닌 **내부 metrics 앱**의 사전 등록된 코드를 가리킴. CLAUDE.md 앱 표에 명시된 `metrics` 앱(공유 지표 메타데이터 + 배치 실행 이력)과 매핑 추정. metric_code 목록:

```
gross_margin, net_margin, roic, current_ratio, interest_coverage,
net_debt_to_ebitda, fcf_margin, ev_to_ebitda, fcf_yield,
operating_income_growth, dso, asset_turnover, accruals_ratio,
net_shareholder_yield
```

이 14개 코드가 metrics/portfolio metrics 앱에 실제로 등록되어 있는지(예: portfolio/metrics/definitions/metrics.py — 검색에서 일부 발견됨)는 본 감사 범위 밖이지만, **카탈로그 단독으로는 검증 불가**한 외부 의존이라는 점은 유의.

### 4. `fred` + `series_id` 패턴 — 11개

FRED 표준 series_id 사용:
```
FEDFUNDS, DGS10, DGS2, MORTGAGE30US, DEXUSEU, UNRATE, PAYEMS,
CPIAUCSL, GDPC1, INDPRO, HOUST
```
모두 FRED 공식 ID 형식과 일치. 형식적 위험 없음.

### 5. `fmp` + `symbol` 패턴 — 18개 (지수/상품/암호/환율)

FMP 심볼 표기:
- 지수: `^GSPC`, `^KS11`, `^IXIC`, `^DJI`, `^KQ11`, `^N225`, `^HSI`, `^VIX`
- 상품: `GCUSD`, `CLUSD`, `SIUSD`, `HGUSD`, `NGUSD`
- 암호: `BTCUSD`, `ETHUSD`
- 환율: `USDKRW`, `DX-Y.NYB`

`DX-Y.NYB`(id 39 달러 인덱스)는 FMP 자체보다 Yahoo Finance 기호 형태에 가까움 — FMP에서 별도 매핑이 필요할 수 있음. 나머지는 FMP `/stable/historical-price` 등에서 사용 가능한 표준 형식.

### 6. `fmp` + `indicator` 패턴 — 9개 (기술적)

`{'indicator': 'RSI', 'period': 14}` 형식. FMP 기술적 지표 endpoint(`/stable/technical-indicator`)는 path 인자에 indicator 명을 받는 구조이므로 형식적으로 호환 가능. 단:
- id 41 `'indicator': 'stochastic'`: FMP는 보통 `stoch` 또는 `stochastic`을 사용 — 정확 키 확인 필요.
- id 42 `'indicator': 'bollinger'`: FMP는 `bbands`/`bollingerbands` 등 별칭 가능 — 사용 시점에 매핑 필요.

### 형식 일관성 점검

`'fmp'`라는 동일 data_source 안에 4가지 서로 다른 키 스키마(`symbol` vs `indicator+period` vs `metric`)가 혼재. 이 자체가 잘못은 아니나, **소비자(데이터 페처)는 data_source 외에 data_params 키를 봐야 분기**할 수 있어 디스패치 로직이 의도치 않게 복잡해질 가능성. 향후 `provider_method` 같은 명시 필드를 두는 편이 안전.

---

## 종합 권고 (참고용, 코드 수정 없음)

1. **카탈로그 본체(id/이름/주기/description) 동기화는 우수** — 현 상태 유지.
2. **BE keyword_rules 보강 필요** — FE의 `KEYWORD_INDICATOR_MAP` 30 그룹을 BE에 미러링하면 LLM PK 매칭 실패 시에도 53개 지표가 자동 추천 가능.
3. **펀더멘털 data_params 어댑터 명시** — id 50, 58은 현 정의로는 FMP에서 직접 fetch 불가. 카탈로그 외부의 매핑 테이블(예: `screener.md`/`common-bugs.md` #14에서 검증된 `pe_ratio: earningsYieldTTM (역수)` 패턴)을 참조한다는 사실이 카탈로그 description 또는 별도 문서에 표기되어야 신규 개발자가 같은 함정에 빠지지 않음.
4. **`metrics` 14개 코드의 등록 여부 별도 검증** — portfolio/metrics/definitions/metrics.py와 metric_code 목록을 1:1 대조하는 후속 감사 권장.
5. **`stochastic`/`bollinger` 등 FMP 기술 지표 별칭 매핑 확인** — 사용 시점 어댑터에서 보정되는지 검증 필요.

---

## 참고 파일

- `thesis/services/prompt_builder.py:14-294` — INDICATOR_CATALOG (BE)
- `thesis/services/prompt_builder.py:305-326` — INDICATOR_FREQUENCY (BE)
- `thesis/services/indicator_matcher.py:12-154` — KEYWORD_RULES (BE)
- `thesis/services/llm_postprocess.py:82-89` — indicator_db_id catalog 검증
- `frontend/components/thesis/AddIndicatorSheet.tsx:15-91` — INDICATOR_CATALOG (FE)
- `frontend/components/thesis/AddIndicatorSheet.tsx:109-139` — KEYWORD_INDICATOR_MAP (FE)
- `CLAUDE.md` 자주 발생하는 버그 #14 — FMP Key Metrics 필드 트랩
- `sub_claude_md/common-bugs.md:99-118` — peRatioTTM 트랩 상세
- `serverless/services/enhanced_screener_service.py:75-77, 296-298` — 검증된 FMP 매핑 사례
