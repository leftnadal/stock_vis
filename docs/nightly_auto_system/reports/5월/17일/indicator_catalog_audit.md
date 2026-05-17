# 지표 카탈로그 동기화 감사 보고서

- 감사 일시: 2026-05-17
- 감사 범위: 읽기 전용 (코드 수정 없음)
- 감사 대상 파일
  - BE 정의: `thesis/services/prompt_builder.py` (INDICATOR_CATALOG)
  - BE 후처리: `thesis/services/llm_postprocess.py`
  - BE 매칭/keyword rule: `thesis/services/indicator_matcher.py` (KEYWORD_RULES)
  - FE 표시: `frontend/components/thesis/AddIndicatorSheet.tsx` (INDICATOR_CATALOG + KEYWORD_INDICATOR_MAP)
- 비교 절차: 각 파일에서 `id`, `name`, `category`, `description`, `data_source`, `data_params`, `support_direction` 필드를 수집하여 차집합·교집합·라벨 매핑 검사.

---

## 요약 (동기화 상태)

| 항목 | 결과 | 비고 |
|---|---|---|
| 항목 개수 (id 기준) | **BE 64개 / FE 64개** | id 집합 완전 일치 (차집합 0) |
| 지표 이름 (한국어) | **64/64 일치** | 모든 id에서 `name` 문자열 동일 |
| 카테고리 라벨 | **불일치** | BE 5개 대분류 (`market_data` / `macro` / `technical` / `fundamental` / `sentiment`) vs FE 17개 세분류 (`수급`, `주요 지수`, ... `주주환원`) |
| `description` 필드 | **편향** | BE 64/64 보유, FE 0/64 (필드 자체 부재) |
| BE `KEYWORD_RULES` 커버리지 | **11/64 (17.2%)** | id 1·2·3·4·5·6·7·8·9·10·11 한정. 카탈로그의 50개+ 지표는 BE 키워드 매칭 불가 |
| FE `KEYWORD_INDICATOR_MAP` 커버리지 | **52/64 (81.3%)** | id 13, 14, 15, 22, 38, 41, 42, 43, 44, 45, 46, 47만 keyword 비매핑 |
| `indicator_type` ↔ `category` 정합 | **1건 불일치** | EPS(id 5): KEYWORD_RULES `market_data` ↔ CATALOG `fundamental` |
| `data_params.endpoint` 노출 | **1건 별도 분기** | id 58 (매출성장률): `endpoint: financial-growth` — FMP `/stable/*` 정책 검증 필요 |
| FMP `audit_note` 분기 항목 | **4건** | id 50 / 52 / 53 / 58 (`inverse` / `scale_multiplier` 변환 필수) |
| `data_source='metrics'` 분기 | **14건** | id 60~73 (validation/metrics 시스템 의존, `metric_code` 형식) |

**핵심 위험 (P1 이상)**

1. BE `KEYWORD_RULES`의 53개 카탈로그 지표 누락 → LLM이 `indicator_db_id`를 빠뜨린 prem ise 텍스트에 대해 추천 0개로 추락 (`indicator_matcher.py:307` 주석에 의해 `match_by_gemini` fallback이 의도적으로 제거된 상태).
2. EPS(id 5)의 `indicator_type='market_data'`가 카탈로그 `category='fundamental'`과 불일치 → 후처리/필터 로직에서 카테고리 기반 분기 시 누락 가능.
3. FE 카탈로그에 `description` 필드 자체 부재 → FE에서 지표 설명/툴팁/관제실 description을 보여줘야 할 때 BE 라운드트립 강제.
4. id 58 (매출성장률)의 `endpoint: 'financial-growth'`가 FMP `/stable/*` 경로 정책과 합치하는지 코드 레벨 점검 미진 (`audit_note`만 남고 fetcher 분기 PR 보류 상태).

---

## BE ↔ FE 불일치 목록

### 1. 항목 차집합 (id 기준)
- BE − FE: **없음**
- FE − BE: **없음**
- 결론: 64개 id 모두 양쪽에 존재.

### 2. 카테고리 라벨 매핑 (BE category → FE category)

| id 범위 | BE `category` | FE `category` | 비고 |
|---|---|---|---|
| 1, 2 | `market_data` | `수급` | FE만 세분류 |
| 3, 4, 12, 13, 14, 15, 16 | `market_data` | `주요 지수` | FE만 세분류 |
| 20~24 | `market_data` | `원자재` | FE만 세분류 |
| 25, 26 | `market_data` | `암호화폐` | FE만 세분류 |
| 6, 7, 30, 37 | `macro` | `금리` | FE만 세분류 |
| 8, 9, 38, 39 | `macro` | `환율/변동성` | FE만 세분류 |
| 31, 32, 34, 35 | `macro` | `고용/성장` | FE만 세분류 |
| 33, 36 | `macro` | `물가/주택` | FE만 세분류 |
| 10, 40~47 | `technical` | `기술적` | 라벨 자체는 호환 |
| 5, 50~58 | `fundamental` | `펀더멘털` | 라벨 호환 |
| 60~66 | `fundamental` | `재무 체질` | FE 세분류 |
| 67, 68 | `fundamental` | `밸류에이션` | FE 세분류 |
| 69 | `fundamental` | `성장` | FE 세분류 |
| 70, 71 | `fundamental` | `운영 효율` | FE 세분류 |
| 72 | `fundamental` | `이익 품질` | FE 세분류 |
| 73 | `fundamental` | `주주환원` | FE 세분류 |
| 11 | `sentiment` | `심리` | 라벨 호환 |

- **영향**: BE에서 `category`로 그룹핑하는 코드 (예: `prompt_builder.build_indicator_block()`의 `CATEGORY_LABELS`) 와 FE의 17 세분류 사이에 자동 변환 매핑이 없음. BE↔FE 통신 시 항상 id 기반으로만 동기 가능하며, 라벨 문자열 직접 비교는 금지.
- **권장**: BE `INDICATOR_CATALOG`에 `subcategory` 필드를 신설하거나, `contracts/`에 카테고리 매핑 테이블을 단일 소스로 두는 방향 검토.

### 3. 항목별 필드 차이 (BE에만 존재 / FE에만 존재)

| 필드 | BE | FE | 결론 |
|---|---|---|---|
| `id` | ✓ | ✓ | 일치 |
| `name` | ✓ | ✓ | 일치 |
| `category` | ✓ (5종) | ✓ (17종) | 다른 라벨 체계 |
| `description` | ✓ (모든 항목) | ✗ | FE 누락 |
| `data_source` | ✓ | ✗ | FE 누락 |
| `data_params` | ✓ | ✗ | FE 누락 |
| `support_direction` | ✓ | ✗ | FE 누락 |
| `freq` (업데이트 주기) | `INDICATOR_FREQUENCY` 별도 dict | `freq` 필드 인라인 | 양쪽 데이터 자체는 일치 |

- `freq` 값 표본 비교 (전수 64개 점검 결과 모두 일치)
  - id 1 → BE `'일간'` / FE `'일간'` ✓
  - id 6 → BE `'주간'` / FE `'주간'` ✓
  - id 31 → BE `'월간'` / FE `'월간'` ✓
  - id 50 → BE `'분기'` / FE `'분기'` ✓

### 4. 후처리·매칭 코드와의 정합

- `llm_postprocess.py:33` 주석: "indicator_db_id: INDICATOR_CATALOG에 없으면 None으로 교정" — id 집합 일치로 인해 현시점 정상.
- `indicator_matcher.py:284` `get_indicator_by_id`로 PK 조회 (1순위). FE 역시 `INDICATOR_BY_ID` Map 조회. 1순위 경로는 양쪽 일치.
- `indicator_matcher.py:308~327` 2순위 키워드 매칭: BE는 `match_by_keywords`만 사용 (gemini fallback 제거). 그러나 BE의 `KEYWORD_RULES` 커버리지가 17%에 불과 → 동일 텍스트를 FE/BE가 받았을 때 추천 결과가 크게 갈릴 가능성 있음. (예: 전제 텍스트에 "원자재" 키워드만 있을 때 — BE 0건, FE 1건(구리/원유 등)으로 갈림.)

---

## description 품질

### BE description 분포 (모든 64개 항목)
- 평균 길이: 약 38자
- 최소 길이: 18자 (`'한국 중소형 성장주 시장 지수.'` — id 14, `'한국 유가증권시장 전체 종목 시가총액 가중 지수.'` — id 4 등)
- 빈 description: **0건**
- 10자 미만: **0건**
- 30자 미만: 약 6건 (한국 지수 계열) — 정보량 부족이라기보다 단순 시장 정의이므로 품질 위험 없음.

**판정**: BE 단독으로는 description 품질 양호.

### FE description 누락
- FE `INDICATOR_CATALOG`에는 `description` 필드가 정의되지 않음 (`CatalogIndicator` interface 자체에 없음 — `AddIndicatorSheet.tsx:8~13`).
- 그 결과 BottomSheet/툴팁 등 FE 단독 렌더링 환경에서는 지표 의미를 보여줄 방법이 없음. 관제실 description은 별도 API (`recommendation_reason`) 통해 가져오는 구조여서 분리되어 있음.

**판정**: FE는 description **전면 미러 누락**. 카탈로그 동기화 항목 중 가장 큰 격차.

### description 신뢰성 점검 (스팟 체크 5개)
| id | BE description 발췌 | 정확성 |
|---|---|---|
| 50 (PER) | "주가를 EPS로 나눈 값. 수익 대비 주가 수준(밸류에이션) 측정." | ✓ |
| 52 (ROE) | "자기자본 대비 순이익 비율. 주주 자본의 수익 창출 효율성." | ✓ |
| 65 (순부채/EBITDA) | "순부채를 EBITDA로 나눈 값. 부채 상환에 필요한 영업이익 년수." | ✓ (정확) |
| 72 (Accruals) | "순이익 대비 발생액 비율. 높을수록 이익의 현금 품질이 낮음." | ✓ |
| 39 (DXY) | "주요 6개 통화 대비 달러 강도 지수. 달러 강세는 위험자산에 부정적." | ✓ |

---

## keyword_rules 고아

### 1. BE `KEYWORD_RULES` (`indicator_matcher.py:12~154`) 분석

BE의 KEYWORD_RULES는 다음 11개 카탈로그 지표만 다룬다.

| 키워드 그룹 | 매핑된 지표 (이름) | 카탈로그 id |
|---|---|---|
| 외국인 / 외인 / 순매수 / 순매도 / foreign | 외국인 순매수 추이 | 1 |
| 기관 / 기관투자자 / 연기금 / 보험 / 자산운용 | 기관 순매수 추이 | 2 |
| 금리 / 연준 / FOMC / fed / 기준금리 / 금리인하 / 금리인상 | 미국 기준금리 (Fed Funds Rate), 미국 10년 국채 금리 | 6, 7 |
| VIX / 공포 / 변동성 / 변동성지수 / volatility | VIX (공포지수) | 8 |
| 환율 / 달러 / 원달러 / USD / KRW / 원화 | 원/달러 환율 | 9 |
| RSI / MACD / 기술적 / 과매수 / 과매도 / 이동평균 / MA | RSI (14일) | 10 |
| 센티먼트 / 여론 / 뉴스 / 심리 / 감성 | 뉴스 센티먼트 | 11 |
| 실적 / EPS / 매출 / 영업이익 / 순이익 / PER / earnings | EPS 추이 | 5 |
| S&P / S&P500 / 나스닥 / NASDAQ / 미국시장 / 다우 / DOW | S&P 500 | 3 |
| 코스피 / KOSPI / 종합주가지수 | KOSPI 지수 | 4 |
| 선거 / 정치 / 정책 / 대통령 / 국회 | VIX, KOSPI | 8, 4 |

- **고아 규칙**: 모든 규칙이 INDICATOR_CATALOG 항목에 매핑됨. **고아 0건**.
- **고아 지표 (역방향, 카탈로그 → keyword)**: id 12, 13, 14, 15, 16, 20, 21, 22, 23, 24, 25, 26, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 46, 47, 51, 52, 53, 54, 55, 56, 57, 58, 60~73. **53개 (전체의 82.8%)가 BE 키워드 매칭 사각지대**.

### 2. KEYWORD_RULES 정의 자체의 결함

- **`id` 필드 부재**: KEYWORD_RULES의 `indicators` 객체는 `{name, data_source, data_params, indicator_type, support_direction, reason}` 만 보유하고 카탈로그 `id`가 빠져 있음. `match_by_keywords` 반환값으로는 PK 매칭이 불가능하고, `match_indicators_for_llm` 라인 308~315에서 `_find_in_catalog(ind['name'])`로 이름 역매칭하는 우회 경로가 필요한 상태.
- **카테고리 라벨 불일치**: 라인 95 EPS 항목의 `'indicator_type': 'market_data'`는 카탈로그의 `category='fundamental'`(`prompt_builder.py:190`)과 불일치. `_find_in_catalog`로 보강할 때 카탈로그 메타가 덮어쓰지만, 카탈로그 외 경로(예: legacy `match_indicators_for_premise` 호출자)에서는 EPS가 잘못된 카테고리로 흘러갈 수 있음.

### 3. FE `KEYWORD_INDICATOR_MAP` (`AddIndicatorSheet.tsx:109~139`) 분석

- 29개 규칙, **52/64 (81.3%)** 카탈로그 지표를 인덱스로 매핑.
- 비매핑 id: 13, 14, 15, 22, 38, 41, 42, 43, 44, 45, 46, 47
  - 13/14/15: 다우존스/코스닥/니케이 — `미국시장`, `한국시장`, `일본` 키워드가 가까운 id로만 매핑되어 있음.
  - 22: 은 — `금`/`구리` 규칙은 있으나 은 단독 키워드 부재.
  - 38: 달러/유로 환율 — `달러` 키워드는 9·39로 매핑.
  - 41~47: 기술적 지표 (스토캐스틱, 볼린저, ATR, OBV, SMA50, SMA200, EMA12) — 통합 키워드 `rsi, macd, 기술적, 과매수, 과매도, 이동평균`이 10·40만 매핑.
- **고아 규칙 (FE → 카탈로그)**: 모든 indicatorIds가 카탈로그에 존재 (id 1~73 범위 내). **고아 0건**.

### 4. BE ↔ FE keyword 매핑 격차 사례

| 전제 텍스트 예시 | BE 추천 (KEYWORD_RULES) | FE 추천 (KEYWORD_INDICATOR_MAP) |
|---|---|---|
| "유가 상승이 인플레 자극" | 매칭 0건 → 추천 없음 | id 21 (원유 WTI), id 33 (CPI) |
| "ROE 개선" | 매칭 0건 | id 52, 53, 57, 62, 60, 61 |
| "비트코인 강세" | 매칭 0건 | id 25, 26 |
| "고용 호조" | 매칭 0건 | id 31, 32 |
| "외국인 순매수 전환" | id 1 ✓ | id 1 ✓ |

- 같은 사용자 입력에 대해 FE는 인사이트를 제공하지만 BE는 침묵하는 케이스가 다수 발생.

---

## data_params 형식

### 1. data_source별 표준 형식

| `data_source` | 표준 키 | 예시 항목 |
|---|---|---|
| `fmp` (시장가/지수/원자재) | `symbol` | id 3 (`'^GSPC'`), id 8 (`'^VIX'`), id 21 (`'CLUSD'`), id 39 (`'DX-Y.NYB'`) |
| `fmp` (수급 메트릭) | `metric` | id 1 (`'foreign_net_buy'`), id 2 (`'institutional_net_buy'`), id 5 (`'eps'`) |
| `fmp` (key-metrics-ttm 류) | `metric` + 선택적 `inverse` / `scale_multiplier` / `audit_note` | id 50, 52, 53 |
| `fmp` (financial-growth) | `metric` + `endpoint='financial-growth'` + `scale_multiplier=100` | id 58 (`'growthRevenue'`) |
| `fmp` (기술적 지표) | `indicator`, `period`, (옵션 `fast/slow/signal`) | id 10, 40, 41, 42, 43, 44, 45, 46, 47 |
| `fred` | `series_id` | id 6 (`FEDFUNDS`), id 7 (`DGS10`), id 31 (`UNRATE`) |
| `news_sentiment` | `{}` | id 11 |
| `metrics` (validation/metrics) | `metric_code` | id 60~73 (`gross_margin`, `roic`, `dso` 등) |

### 2. 외부 데이터 제공자 형식과의 정합

#### 2-1. FMP key-metrics-ttm 분기 (audit_note 보유 4건, common-bugs #14 회귀 방지)

| id | data_params | 비고 |
|---|---|---|
| 50 | `{'metric': 'earningsYieldTTM', 'inverse': True}` | PER = 1 / earningsYieldTTM. fetcher가 `inverse` 플래그를 인지해야 함. |
| 52 | `{'metric': 'returnOnEquityTTM', 'scale_multiplier': 100}` | FMP 응답 0~1 → ×100 % 변환. |
| 53 | `{'metric': 'returnOnAssetsTTM', 'scale_multiplier': 100}` | 동일 패턴. |
| 58 | `{'metric': 'growthRevenue', 'endpoint': 'financial-growth', 'scale_multiplier': 100}` | key-metrics-ttm이 아닌 별도 endpoint. |

- **위험**: `audit_note`는 자유 문자열로만 남아 있고, 실제 fetcher가 `inverse`/`scale_multiplier`/`endpoint` 키를 일관되게 해석하는지에 대한 단일 기준 코드를 카탈로그가 강제하지 않음. 분기 PR(별도)이 진행되기 전까지는 호출자별 변환 누락 가능성이 잠재.
- **FMP /stable/* 정책 정합 검토 포인트**: id 58의 `endpoint='financial-growth'`가 CLAUDE.md의 "FMP Starter Plan `/stable/*` 경로만 사용" 규칙과 호환되는지 확인 필요. `prompt_builder.py` 자체에는 경로 prefix가 없고 fetcher에 위임 — fetcher 측에서 `/stable/financial-growth/*` 형태로 호출되는지 별도 감사 필요. (본 감사 범위 밖)

#### 2-2. FMP 기술적 지표

- BE 형식: `{'indicator': 'RSI', 'period': 14}`, `{'indicator': 'MACD', 'fast': 12, 'slow': 26, 'signal': 9}` 등.
- FMP `/stable/technical-indicators/{indicator}?periodLength=...&type=...` 가 표준. `indicator` 키는 enum, `period`는 `periodLength`로 변환 필요. MACD의 `fast/slow/signal`은 FMP 응답에 모두 포함되지만 요청 파라미터로는 비표준.
- **점검 포인트**: fetcher가 `period` → `periodLength`로 매핑하는 어댑터가 있는지 미확인. 카탈로그 단계에서 키 명명이 FMP API와 일대일이 아니므로 변환 레이어 검증 필요.

#### 2-3. FRED

- BE 형식: `{'series_id': 'FEDFUNDS'}` 등 표준적. FRED `/fred/series/observations` 호출에 그대로 사용 가능.

#### 2-4. metrics (validation/metrics 시스템)

- 14개 항목 (id 60~73)이 `data_source='metrics'`, `data_params={'metric_code': '...'}` 패턴.
- `metric_code` 값 (e.g. `gross_margin`, `roic`, `dso`, `accruals_ratio`)이 `metrics` 앱의 `MetricDefinition.code` 또는 `quarterly_metric_fetcher` 등록 키와 일치해야 함. 본 감사 범위에서는 매핑 테이블 단일 진실 소스를 확인하지 못함 — 별도 정합 점검 필요.

### 3. data_params 부재·결손 점검

- BE 64개 모두 `data_params` 키 자체는 보유.
- 빈 dict (`{}`): id 11 (뉴스 센티먼트) — `data_source='news_sentiment'` 자체가 파라미터 비요구. **정상**.
- `inverse`/`scale_multiplier`/`audit_note`/`endpoint` 등 비표준 키는 4개 항목에만 등장 (50, 52, 53, 58). fetcher 측이 키를 무시할 수 있으므로 호출 직전에 변환 헬퍼가 필요한지 코드 레벨 확인 권고.

---

## 부록 A. 검사 대상 ID 64개 명세

```
1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16,
20, 21, 22, 23, 24, 25, 26,
30, 31, 32, 33, 34, 35, 36, 37, 38, 39,
40, 41, 42, 43, 44, 45, 46, 47,
50, 51, 52, 53, 54, 55, 56, 57, 58,
60, 61, 62, 63, 64, 65, 66, 67, 68, 69, 70, 71, 72, 73
```

- 결번: 17, 18, 19, 27, 28, 29, 48, 49, 59 (의도된 결번으로 추정. 추후 신규 지표 슬롯).

## 부록 B. 권장 후속 액션 (수정 미실행)

1. BE `KEYWORD_RULES`에 카탈로그 50+개 지표 매핑 보강 (또는 FE `KEYWORD_INDICATOR_MAP`을 BE로 포팅) — id 기반 단일 소스화.
2. FE `INDICATOR_CATALOG`에 `description`/`data_source`/`support_direction` 필드 추가 (또는 BE → FE 단일 빌드 산출물로 변환).
3. id 5(EPS) `indicator_type` `market_data` → `fundamental`로 정정.
4. id 58 `endpoint='financial-growth'`가 `/stable/financial-growth/*`로 호출되는지 fetcher 어댑터 감사 (CLAUDE.md `/stable/*` 정책).
5. `inverse`/`scale_multiplier` 비표준 키를 단일 fetcher 변환 헬퍼로 통합 (common-bugs #14 회귀 방지).
6. `contracts/` 디렉토리에 카탈로그 JSON 단일 소스를 두고 BE/FE가 빌드 타임 임포트하는 구조 검토 — 카테고리 라벨 매핑 17↔5 격차 해소.

---

(보고서 끝)
