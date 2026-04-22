# 지표 카탈로그 동기화 감사 보고서

- 감사 일자: 2026-04-21
- 감사 범위: BE(`thesis/services/prompt_builder.py`, `llm_postprocess.py`, `indicator_matcher.py`) ↔ FE(`frontend/components/thesis/AddIndicatorSheet.tsx`)
- 감사자 결론: **카탈로그 ID 집합은 BE/FE 간 100% 일치**하나, **4개 항목의 표기명 차이**와 **keyword_rules 범위 불균형(BE 11 rule · FE 28 rule)**, **indicator_matcher 내 `indicator_type` vs catalog `category` 필드 혼용** 등 하위 문제가 존재한다.

---

## 요약 (동기화 상태)

| 항목 | BE | FE | 상태 |
|------|----|----|------|
| 카탈로그 항목 수 | 64 | 64 | ✅ 일치 |
| ID 집합 | {1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,20,21,22,23,24,25,26,30,31,32,33,34,35,36,37,38,39,40~47,50~58,60~73} | 동일 | ✅ 완전 일치 |
| 표기명(name) 동일 | — | — | ⚠️ 4건 불일치 (id 6, 7, 30, 54) |
| description 누락/빈 값 | 0 | N/A (FE에는 description 없음) | ⚠️ FE 카탈로그에 description 필드 자체가 없음 |
| description 짧음(< 10자) | 0 | — | ✅ 없음 |
| keyword_rules ↔ catalog 고아 규칙 | 0 | 0 | ✅ 모두 카탈로그 존재 ID/이름만 참조 |
| keyword_rules `indicator_type` ↔ catalog `category` 값 일치 | — | — | ⚠️ 1건 불일치 (EPS: market_data vs fundamental) |
| keyword_rules 범위 | 11개 규칙 (이름 기반) | 28개 규칙 (ID 기반) | ⚠️ 심각한 비대칭 — 같은 키워드도 다른 추천 결과 |
| data_params 형식 BE ↔ FE | 내부에서만 사용 | FE는 data_params 미사용 | — |
| data_params 형식 catalog ↔ keyword_rules | 10개 항목 비교 | — | ✅ 모두 일치 |
| FMP 필드명 실제 응답 매핑 | 일부 항목 가공 필요 | — | ⚠️ PER/ROE 등 common-bugs #14 관련 항목 7개, 별도 fetcher 변환 전제 |

결론 한 줄: **ID 계층은 깨끗하지만 "표기명"과 "키워드 규칙 커버리지"가 동기화되지 않았다.** LLM 응답 파이프라인(PK 기반)은 안전하나, 텍스트 기반 추천(keyword_rules) 경로는 BE/FE가 전혀 다른 추천을 내놓는다.

---

## 1. BE ↔ FE 불일치 목록

### 1-1. 카탈로그 ID 불일치
**없음.** BE 64개, FE 64개, 모두 동일한 ID 집합.

### 1-2. 표기명(name) 차이 — 4건

| id | BE name (prompt_builder.py) | FE name (AddIndicatorSheet.tsx) | 영향 |
|----|-----------------------------|----------------------------------|------|
| 6  | `미국 기준금리 (Fed Funds Rate)` | `미국 기준금리` | 기관명이 BE에만 표기. FE 목록 ↔ BE 프롬프트 노출 명칭 상이 → 사용자 눈에 동일 지표가 다른 이름으로 보일 가능성 |
| 7  | `미국 10년 국채 금리` | `미국 10년 국채` | "금리" 접미사 FE에서 누락 |
| 30 | `미국 2년 국채 금리` | `미국 2년 국채` | 동일 패턴 |
| 54 | `부채비율 (Debt/Equity)` | `부채비율 (D/E)` | 축약 표기 불일치 |

**왜 중요한가**: `prompt_builder.get_indicator_description(indicator_name)`은 접두사 매칭까지만 지원한다(l.336). `"미국 기준금리"`(FE) → `"미국 기준금리 (Fed Funds Rate)"`(BE catalog) 접두사 매칭은 성공하지만, 역방향 조회나 이름 기반 로그/알림은 BE 기준 풀 네임으로 기록되어 FE 표기와 어긋난다. 또한 LLM이 프롬프트에서 본 BE 이름을 그대로 `indicator_name`으로 회신할 경우 FE 화면에 "모르는 지표"로 보일 수 있다(현재 UI는 id 기반 매핑이라 큰 문제는 아님, 다만 메시지 영역에서 표기가 섞임).

### 1-3. category(BE) ↔ category(FE) 차이

FE는 UI 분류 목적상 BE의 5개 `category`(`market_data` / `macro` / `technical` / `fundamental` / `sentiment`)를 **17개 세부 카테고리**(`수급`, `주요 지수`, `원자재`, `암호화폐`, `금리`, `환율/변동성`, `고용/성장`, `물가/주택`, `기술적`, `펀더멘털`, `재무 체질`, `밸류에이션`, `성장`, `운영 효율`, `이익 품질`, `주주환원`, `심리`)로 재분류해 사용한다.

- BE 카테고리 → FE 카테고리 매핑 테이블/계산식이 **문서화되어 있지 않다.**
- `category` 라벨이 BE에서 한국어로 바뀔 때(예: `CATEGORY_LABELS['market_data'] = '시장 데이터'`) FE의 17개 세부 분류와 대응되지 않는다.
- 새로운 지표가 추가되면 FE의 `categoryOrder`(l.211~216)에 수동으로 올바른 카테고리 문자열을 지정해야 하며, 누락 시 "전체 카탈로그" 섹션에서 해당 카테고리만 누락돼 표시되지 않는 위험이 있다.

**분류 불일치 예시**:
- BE: `{id: 67, category: 'fundamental'}` / FE: `{id: 67, category: '밸류에이션'}`
- BE: `{id: 69, category: 'fundamental'}` / FE: `{id: 69, category: '성장'}`
- BE: `{id: 73, category: 'fundamental'}` / FE: `{id: 73, category: '주주환원'}`

→ UI 의도라면 정상이나, "단일 소스" 원칙이라면 BE 카탈로그에 `fe_category` 필드를 추가하거나 FE가 BE에서 내려받는 구조로 바꿔야 한다.

### 1-4. FE만 존재하는 필드
- FE는 `freq: '일간' | '주간' | '월간' | '분기'`를 각 항목에 인라인으로 가지고 있으나, BE는 별도 사전 `INDICATOR_FREQUENCY`(prompt_builder.py l.305-326)에 id→주기 매핑으로 분리.
- BE에는 `description`, `data_source`, `data_params`, `support_direction`이 있으나 FE에는 없음. FE는 순수 UI 표시용 메타데이터만 들고 있어 **동일 id에 대해 두 소스가 서로 다른 필드 집합을 유지**한다.

---

## 2. description 필드 품질

### 2-1. 빈 description
**없음.** BE catalog 64개 항목 전부 `description` 필드가 비어 있지 않다.

### 2-2. 너무 짧은 description (< 10 한글/영문자)
**없음.** 가장 짧은 항목도 10자 이상:

| id | name | description | 길이(대략) |
|----|------|-------------|------------|
| 14 | 코스닥 지수 | `한국 중소형 성장주 시장 지수.` | 15자 |
| 4  | KOSPI 지수 | `한국 유가증권시장 전체 종목 시가총액 가중 지수.` | 24자 |
| 22 | 은 (Silver) | `은 현물 가격(USD/oz). 산업 수요와 안전자산 이중 역할.` | 27자 |

### 2-3. description 일관성 관찰
- 대부분 `{정의/산출방식}. {투자 맥락 해설}.` 2문장 패턴을 지킨다.
- 몇 개 지표는 1문장만 제공(id 4, 14, 22 등)으로 상대적으로 정보량이 적다. 품질 기준 미달은 아니지만 UI의 **관제실 지표 설명**(CLAUDE.md 구현 상태 기재) 품질과 균일성을 높이려면 2문장 통일이 바람직하다.

### 2-4. FE 측 description 노출 여부
- `AddIndicatorSheet.tsx`는 `description`을 **전혀 렌더링하지 않는다.** 카드 표면에는 `name + freq + reason(전제 기반 추천일 때만)`만 노출.
- BE가 정성껏 작성한 description이 유저에게 닿는 경로는 "관제실 지표 설명" / "관제실 대시보드 지표 카드"뿐이라 추정되며, Add 화면의 정보 밀도는 낮다.
- FE가 BE의 description을 별도 API(`/api/v1/thesis/indicators/` 등)로 받아와 표시할 여지가 있다면 싱크 로직이 추가로 필요하다(현재 AddIndicatorSheet는 하드코딩 미러 의존).

---

## 3. keyword_rules 고아 / 커버리지

### 3-1. 고아(카탈로그에 없는 지표 참조) 규칙
**없음.** `indicator_matcher.py`의 `KEYWORD_RULES` 11개 규칙이 참조하는 모든 지표 이름은 catalog에 존재한다:

| 참조 이름 | 매칭되는 catalog id | 상태 |
|-----------|---------------------|------|
| 외국인 순매수 추이 | 1 | ✅ |
| 기관 순매수 추이 | 2 | ✅ |
| S&P 500 | 3 | ✅ |
| KOSPI 지수 | 4 | ✅ |
| EPS 추이 | 5 | ✅ |
| 미국 기준금리 (Fed Funds Rate) | 6 | ✅ |
| 미국 10년 국채 금리 | 7 | ✅ |
| VIX (공포지수) | 8 | ✅ |
| 원/달러 환율 | 9 | ✅ |
| RSI (14일) | 10 | ✅ |
| 뉴스 센티먼트 | 11 | ✅ |

### 3-2. 커버리지 불균형 — 심각
- BE keyword_rules: **11개 규칙 / 11개 고유 지표** (catalog 64개 중 17%만 텍스트 매칭 가능).
- FE KEYWORD_INDICATOR_MAP: **28개 규칙 / 30개+ 고유 지표** (catalog 64개 중 ~47%).
- **같은 전제 텍스트가 BE에서는 추천되지 않고 FE에서만 추천되는 경우가 다수 발생.**

구체적 예시 — BE에는 없고 FE에만 있는 키워드 규칙:
- `['유가', '원유', 'wti', '석유', '에너지', 'opec', '오일']` → 원유 id 21
- `['금', 'gold', '금값', '안전자산']` → 금 id 20
- `['구리', 'copper', '산업금속', '경기선행']` → 구리 id 23
- `['비트코인', 'btc', '암호화폐']` → id 25, 26
- `['per', 'pbr', '밸류에이션', '저평가', '고평가']` → id 50, 51, 67, 68
- `['roe', 'roa', '수익성', '이익률', 'roic', '마진']` → id 52, 53, 57, 62, 60, 61
- `['부채', '레버리지', 'debt']` → id 54, 63, 64, 65
- `['배당', 'dividend', '현금흐름', 'fcf']` → id 55, 56, 66, 68, 73
- `['회전율', '효율', '재고', '매출채권']` → id 70, 71
- `['cpi', '물가', '소비자물가', '인플레']` → id 33
- `['고용', '실업', 'nfp', '비농업']` → id 31, 32
- `['gdp', '성장', '경기', '산업생산']` → id 34, 35
- `['주택', '부동산', '모기지', 'reit']` → id 36, 37
- `['반도체', '테크', 'ai', '엔비디아']` → id 12, 3
- `['중국', '항셍', '홍콩']` → id 16
- `['일본', '니케이', '엔화']` → id 15

→ **결과**: 사용자가 "유가 상승 시 정유주 수혜" 같은 전제를 입력하면 FE 추천은 원유(id 21)를 띄우지만, LLM의 PK 매칭이 실패해 BE fallback인 `match_by_keywords`로 떨어지면 **추천 결과가 빈 목록**이 된다. 동일 전제에 대해 "FE는 3개 추천, BE는 0개" 상황이 발생한다.

**공식적인 1차 소스**가 어느 쪽인지 설계 문서에 명시되지 않았다(`docs/thesis_control/indicator_catalog_audit.md` 이전 리포트 확인 권장).

### 3-3. `indicator_type` vs `category` 필드 명칭 혼용
`indicator_matcher.py`의 `KEYWORD_RULES` 각 항목은 `indicator_type` 키를 사용하나, `prompt_builder.INDICATOR_CATALOG`는 동일 개념을 `category`로 표기한다. 값 자체는 대부분 일치(`market_data`, `macro`, `technical`, `sentiment`)하지만 필드명이 다르다. **consumer 측(예: `match_by_keywords` 반환을 쓰는 호출부)**이 `category` 키를 기대하면 누락 속성으로 깨질 가능성이 있다.

또한 값 불일치 1건:

| 지표 | indicator_matcher `indicator_type` | catalog `category` | 실제 맞는 쪽 |
|------|-------------------------------------|---------------------|---------------|
| EPS 추이 (id 5) | `market_data` | `fundamental` | `fundamental` (실적은 펀더멘털) |

→ `match_by_keywords`가 반환한 EPS 항목의 `indicator_type` 값이 downstream에서 사용된다면 분류 오인 발생.

### 3-4. `support_direction` 불일치 체크
catalog와 keyword_rules 11개 항목을 병렬 확인했을 때 `support_direction` 값은 모두 일치한다(외국인 순매수 positive, 금리 negative, VIX negative, 환율 negative, RSI positive, 뉴스 센티먼트 positive, EPS positive, 기관 순매수 positive, S&P positive, KOSPI positive).

### 3-5. 키워드 매칭 정책 자체의 이슈 (부수적)
- `indicator_matcher.match_by_keywords`는 **선언 순서대로 먼저 매칭되는 규칙**에 따라 지표를 골라, "금리" 키워드가 들어간 뉴스 기반 전제에서도 VIX보다 FEDFUNDS가 우선. 이 자체는 버그가 아니지만, FE의 `findRelatedIndicators`는 **모든 규칙을 돌며 score 누적**하는 구조여서 **동일 문장에 대해 BE는 2개, FE는 5개**가 나오는 상황이 생긴다.
- `match_by_gemini`는 `match_indicators_for_llm`에서 주석으로 **명시적 제외**(l.306-307, "카탈로그에 없는 환각 지표를 생성하므로 제외"). 다만 `match_indicators_for_premise`(l.263-268)는 여전히 gemini fallback을 호출하므로 **진입 경로에 따라 환각 재발 가능**(feedback memory `feedback_llm_indicator_hallucination.md` 참고 필요).

---

## 4. data_params 형식

### 4-1. 형식 체계 (BE catalog 관점)

| data_source | data_params 키 | 예시 | 소비자 |
|-------------|-----------------|------|--------|
| `fmp` (quote) | `symbol` | `^GSPC`, `USDKRW`, `GCUSD`, `^VIX` | FMP `/stable/quote/{symbol}` 계열 |
| `fmp` (technical) | `indicator`, `period` (± `fast`/`slow`/`signal`) | `{'indicator':'RSI','period':14}`, `{'indicator':'MACD','fast':12,...}` | FMP `/stable/technical-indicator/*` |
| `fmp` (TTM metric) | `metric` | `peRatioTTM`, `returnOnEquityTTM`, `freeCashFlowTTM`, `operatingProfitMarginTTM`, `revenueGrowthYoY` | FMP `/stable/key-metrics-ttm` 또는 내부 래퍼 |
| `fmp` (custom market metric) | `metric` | `foreign_net_buy`, `institutional_net_buy`, `eps` | 내부 aggregation/`quarterly_metric_fetcher.py` |
| `fred` | `series_id` | `FEDFUNDS`, `DGS10`, `DGS2`, `UNRATE`, `CPIAUCSL`, `HOUST`, `DEXUSEU`, `MORTGAGE30US`, `PAYEMS`, `GDPC1`, `INDPRO` | FRED API |
| `metrics` | `metric_code` | `gross_margin`, `net_margin`, `roic`, `current_ratio`, ... | `metrics/` 앱의 SharedMetric 코드 |
| `news_sentiment` | (없음, `{}`) | — | news 앱 집계 |

### 4-2. keyword_rules의 data_params ↔ catalog data_params
11개 중첩 항목 모두 **정확히 동일한 키·값**(`symbol`/`series_id`/`indicator+period`/`metric` 키 포함) — 위 3-1 표의 상태 열과 동일.

### 4-3. FMP 실제 필드 응답과의 잠재 불일치 — 검증 필요
CLAUDE.md의 `sub_claude_md/common-bugs.md` 버그 #14가 지목하는 FMP Key Metrics TTM 응답 vs 카탈로그 `metric` 값:

| catalog id | catalog `metric` 값 | FMP 응답 필드 | 가공 규칙 (common-bugs #14) |
|------------|---------------------|----------------|-------------------------------|
| 50 PER     | `peRatioTTM`        | `earningsYieldTTM` | **역수 = PER** (직접 키 없음) |
| 52 ROE     | `returnOnEquityTTM` | `returnOnEquityTTM` | **×100** (FMP 응답은 소수 형태) |
| 53 ROA     | `returnOnAssetsTTM` | `returnOnAssetsTTM` | ×100 필요 여부 검증 |
| 54 D/E     | `debtToEquityTTM`   | `debtToEquityTTM`   | 검증 필요 |
| 55 FCF     | `freeCashFlowTTM`   | `freeCashFlowTTM`   | 직접 |
| 56 Dividend Yield | `dividendYieldTTM` | `dividendYieldTTM` | ×100 여부 검증 |
| 57 영업이익률 | `operatingProfitMarginTTM` | 확인 필요 — FMP /stable/key-metrics-ttm에 표준 필드로 존재하지 않을 수 있음 |
| 58 매출성장률 | `revenueGrowthYoY`  | 확인 필요 — 표준 필드 아님 |
| 51 PBR     | `pbRatioTTM`        | `priceToBookRatioTTM` 또는 `pbRatioTTM` | 필드명 버전 편차 가능 |

**조치 제안**: 카탈로그에 적힌 `metric` 문자열이 "FMP API 필드 이름"인지 "내부 추상 지표 이름(후가공 규칙 적용 대상)"인지 혼재한다. fetcher 쪽 매핑 테이블(`thesis/services/quarterly_metric_fetcher.py`)과 교차 검증이 필요하며, 본 감사 범위 밖이다. **이 리포트는 "기재된 문자열" 수준의 관찰만 기록.**

### 4-4. 새 확장 소스(`metrics`) 매핑
id 60~73 (14개) 펀더멘털/재무 체질 지표는 `data_source: 'metrics'`로 내부 `metrics` 앱에 의존한다. `metric_code` 14종이 실제로 `metrics/` 앱에 존재하는지 본 감사 범위에서 미확인(READ ONLY). fetcher가 없는 경우 관제실 대시보드에서 "데이터 없음"이 표시될 위험 → 별도 확인 PR 권장.

---

## 부록 A. 전체 카탈로그 ID ↔ name 대조표 (BE vs FE)

| id | BE name | FE name | 동일 여부 |
|----|---------|---------|-----------|
| 1  | 외국인 순매수 추이 | 외국인 순매수 추이 | ✅ |
| 2  | 기관 순매수 추이 | 기관 순매수 추이 | ✅ |
| 3  | S&P 500 | S&P 500 | ✅ |
| 4  | KOSPI 지수 | KOSPI 지수 | ✅ |
| 5  | EPS 추이 | EPS 추이 | ✅ |
| 6  | 미국 기준금리 (Fed Funds Rate) | 미국 기준금리 | ❌ |
| 7  | 미국 10년 국채 금리 | 미국 10년 국채 | ❌ |
| 8  | VIX (공포지수) | VIX (공포지수) | ✅ |
| 9  | 원/달러 환율 | 원/달러 환율 | ✅ |
| 10 | RSI (14일) | RSI (14일) | ✅ |
| 11 | 뉴스 센티먼트 | 뉴스 센티먼트 | ✅ |
| 12 | NASDAQ | NASDAQ | ✅ |
| 13 | 다우존스 | 다우존스 | ✅ |
| 14 | 코스닥 지수 | 코스닥 지수 | ✅ |
| 15 | 니케이 225 | 니케이 225 | ✅ |
| 16 | 항셍 지수 | 항셍 지수 | ✅ |
| 20 | 금 (Gold) | 금 (Gold) | ✅ |
| 21 | 원유 (WTI) | 원유 (WTI) | ✅ |
| 22 | 은 (Silver) | 은 (Silver) | ✅ |
| 23 | 구리 (Copper) | 구리 (Copper) | ✅ |
| 24 | 천연가스 | 천연가스 | ✅ |
| 25 | 비트코인 (BTC) | 비트코인 (BTC) | ✅ |
| 26 | 이더리움 (ETH) | 이더리움 (ETH) | ✅ |
| 30 | 미국 2년 국채 금리 | 미국 2년 국채 | ❌ |
| 31 | 실업률 | 실업률 | ✅ |
| 32 | 비농업 고용 (NFP) | 비농업 고용 (NFP) | ✅ |
| 33 | 소비자물가지수 (CPI) | 소비자물가지수 (CPI) | ✅ |
| 34 | 실질 GDP | 실질 GDP | ✅ |
| 35 | 산업생산지수 | 산업생산지수 | ✅ |
| 36 | 주택착공건수 | 주택착공건수 | ✅ |
| 37 | 30년 모기지 금리 | 30년 모기지 금리 | ✅ |
| 38 | 달러/유로 환율 | 달러/유로 환율 | ✅ |
| 39 | 달러 인덱스 (DXY) | 달러 인덱스 (DXY) | ✅ |
| 40 | MACD | MACD | ✅ |
| 41 | 스토캐스틱 %K | 스토캐스틱 %K | ✅ |
| 42 | 볼린저 밴드 %B | 볼린저 밴드 %B | ✅ |
| 43 | ATR (평균진폭) | ATR (평균진폭) | ✅ |
| 44 | OBV (거래량 누적) | OBV (거래량 누적) | ✅ |
| 45 | SMA 50일 | SMA 50일 | ✅ |
| 46 | SMA 200일 | SMA 200일 | ✅ |
| 47 | EMA 12일 | EMA 12일 | ✅ |
| 50 | PER (주가수익비율) | PER (주가수익비율) | ✅ |
| 51 | PBR (주가순자산비율) | PBR (주가순자산비율) | ✅ |
| 52 | ROE (자기자본이익률) | ROE (자기자본이익률) | ✅ |
| 53 | ROA (총자산이익률) | ROA (총자산이익률) | ✅ |
| 54 | 부채비율 (Debt/Equity) | 부채비율 (D/E) | ❌ |
| 55 | 잉여현금흐름 (FCF) | 잉여현금흐름 (FCF) | ✅ |
| 56 | 배당수익률 | 배당수익률 | ✅ |
| 57 | 영업이익률 | 영업이익률 | ✅ |
| 58 | 매출성장률 (YoY) | 매출성장률 (YoY) | ✅ |
| 60 | 매출총이익률 (Gross Margin) | 매출총이익률 (Gross Margin) | ✅ |
| 61 | 순이익률 (Net Margin) | 순이익률 (Net Margin) | ✅ |
| 62 | ROIC (투하자본이익률) | ROIC (투하자본이익률) | ✅ |
| 63 | 유동비율 (Current Ratio) | 유동비율 (Current Ratio) | ✅ |
| 64 | 이자보상배율 | 이자보상배율 | ✅ |
| 65 | 순부채/EBITDA | 순부채/EBITDA | ✅ |
| 66 | FCF 마진 | FCF 마진 | ✅ |
| 67 | EV/EBITDA | EV/EBITDA | ✅ |
| 68 | FCF 수익률 | FCF 수익률 | ✅ |
| 69 | 영업이익 성장률 | 영업이익 성장률 | ✅ |
| 70 | 매출채권 회전일수 (DSO) | 매출채권 회전일수 (DSO) | ✅ |
| 71 | 총자산회전율 | 총자산회전율 | ✅ |
| 72 | 발생액 비율 (Accruals) | 발생액 비율 (Accruals) | ✅ |
| 73 | 순주주수익률 | 순주주수익률 | ✅ |

일치 60 / 불일치 4 / 총 64

---

## 부록 B. 권장 후속 조치 (코드 미수정, 제안만)

1. **표기명 통일 (id 6/7/30/54)**: FE를 BE 풀 네임으로 맞추거나, BE에 `short_name` 필드 추가 + FE가 그 필드를 사용.
2. **keyword_rules 동기화 전략 수립**: BE 11 rule vs FE 28 rule 비대칭을 해소. 단일 YAML/JSON으로 둘 다 공유하는 구조 검토.
3. **`indicator_type` → `category` 필드명 통일** (indicator_matcher 내부).
4. **EPS의 `indicator_type` 값 정정**: `market_data` → `fundamental` (catalog 기준).
5. **FE에 `description` 노출 경로 추가**: 별도 API에서 id→description 매핑을 내려받거나, AddIndicatorSheet 툴팁/상세 시트로 표시.
6. **FMP Key Metrics TTM fetcher와 catalog `metric` 문자열 매핑 감사**(별도 PR): common-bugs #14 관련 7개 항목.
7. **`metrics` 앱의 `metric_code` 14종 존재 여부 감사**(별도 PR).

---

## 부록 C. 감사 방법

- 파일 직접 읽기: `thesis/services/prompt_builder.py` (전체 976줄), `llm_postprocess.py` (전체 218줄), `indicator_matcher.py` (전체 339줄), `frontend/components/thesis/AddIndicatorSheet.tsx` (전체 308줄).
- 코드 실행 없음, 자동화 도구 없음, 수동 대조.
- 감사 범위: 정적 읽기 전용. 실행시 렌더링/프롬프트 결과는 미확인.
