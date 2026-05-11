# 지표 카탈로그 동기화 감사 보고서

- **감사일**: 2026-05-10 (5월 10일자 야간 감사)
- **모드**: 읽기 전용 (코드 수정 없음)
- **검사 대상**
  - BE 정의: `thesis/services/prompt_builder.py` (`INDICATOR_CATALOG`, `INDICATOR_FREQUENCY`, `_INDICATOR_BY_ID`, `_INDICATOR_NAME_TO_DESC`)
  - BE 후처리: `thesis/services/llm_postprocess.py` (`indicator_db_id` 카탈로그 검증, `target_symbol` 정규화)
  - BE 매칭: `thesis/services/indicator_matcher.py` (`KEYWORD_RULES`, `match_by_keywords`, `match_indicators_for_llm`, `_find_in_catalog`, `match_by_gemini`)
  - FE 표시: `frontend/components/thesis/AddIndicatorSheet.tsx` (`INDICATOR_CATALOG`, `KEYWORD_INDICATOR_MAP`, `findRelatedIndicators`)
- **카탈로그 규모**: BE 64개 / FE 64개 (id 1~73, 결번 17·18·19·27·28·29·48·49·59 정상)
- **이전 감사(5월 9일) 대비 코드 변경 여부**:
  - `prompt_builder.py` 최종 커밋 `3a0b76f` (2026-04-29) — 변경 없음
  - `indicator_matcher.py` 최종 커밋 `19d23ec` (2026-03-30) — 변경 없음
  - `AddIndicatorSheet.tsx` 최종 커밋 `b3b9bdf` (2026-04-27) — 변경 없음
  - `llm_postprocess.py` 최종 커밋 `9d8aacc` (2026-03-31) — 변경 없음
  → 4개 핵심 파일 모두 **5월 9일 감사 이후 무변경**. 5월 8일 감사에서 식별된 P1/P2 후속 큐(DXY 심볼, name→PK 결합화, KEYWORD_RULES 보강, gemini fallback 정책 통일) 그대로 잔존.

---

## 요약 (동기화 상태)

| 항목 | 상태 | 비고 |
|---|---|---|
| BE↔FE id 일치 | OK | 64/64 완전 일치 (BE-only/FE-only 0건) |
| BE↔FE name 일치 | OK | 64개 id 모두 표시 이름 동일 |
| BE↔FE 업데이트 주기 일치 | OK | `INDICATOR_FREQUENCY`(BE) ↔ `freq`(FE) 64/64 일치 |
| description 결손/단문 | OK | 빈 description 0개, 10자 미만 0개 (최단 14자: id 14 "한국 중소형 성장주 시장 지수.") |
| `_INDICATOR_NAME_TO_DESC` 파생 무결성 | OK | 64개 카탈로그 → 64개 키, 빈값 0건 |
| `INDICATOR_FREQUENCY` 키 누락 | OK | 카탈로그 64개 모두 매핑 (`build_indicator_block` 무태그 출력 위험 0) |
| KEYWORD_RULES 고아 | OK | 11개 룰의 indicator name 모두 카탈로그에 존재 |
| KEYWORD_INDICATOR_MAP(FE) 고아 | OK | 28개 룰의 indicatorIds 모두 카탈로그에 존재 |
| KEYWORD_RULES 커버리지 | **WARN** | BE 룰 11개 = 카탈로그 64개 중 17% 커버. FE 룰 28개 = 53/64(83%) 커버 → fallback 품질 BE/FE 비대칭 (5월 8일 P2 미반영) |
| name 기반 결합 | **WARN** | BE `KEYWORD_RULES`/`_find_in_catalog`가 PK 대신 name 문자열로 카탈로그 조회. 이름 변경 시 silent break (P2 미반영) |
| data_params 형식 일관성 | **WARN** | FMP 비표준 metric 2건(`foreign_net_buy`, `institutional_net_buy`) + DXY 심볼 우려 1건(`DX-Y.NYB`) + 별도 endpoint 1건(`growthRevenue`). P1 미반영 |
| `match_by_gemini` 정책 | OK (LLM 경로) / WARN (비-LLM 경로) | `match_indicators_for_llm`은 PK→키워드만 사용. `match_indicators_for_premise`는 여전히 gemini fallback 호출 가능 (P1 미반영) |

총평: **id/name/주기 카탈로그 자체는 BE/FE 완전 동기화 상태**. 4월 29일 이후 5/10 현재까지 코드 변경이 없어 5월 8~9일 감사에서 도출된 4건의 P1/P2 권장 사항이 11일째 잔존.

---

## BE ↔ FE 불일치 목록

### 1. id 차집합

- **BE-only id**: 없음
- **FE-only id**: 없음
- **양쪽 결번 id (사용 안 함, 정상)**: 17, 18, 19, 27, 28, 29, 48, 49, 59

> 결번 사유: 과거 카탈로그 정리/병합 흔적. `get_indicator_by_id(17)` 등은 `None` 반환, `llm_postprocess.normalize_llm_output`에서 자동 nullify. 사용자/LLM 경로 모두 안전.

### 2. name 차이 (id별)

64개 id 전체에서 BE name과 FE name이 문자 단위로 일치. 차이 없음.

| 검증 키 | BE 출처 | FE 출처 | 결과 |
|---|---|---|---|
| 1 외국인 순매수 추이 | prompt_builder.py:16 | AddIndicatorSheet.tsx:17 | 동일 |
| 5 EPS 추이 | prompt_builder.py:190 | AddIndicatorSheet.tsx:64 | 동일 |
| 8 VIX (공포지수) | prompt_builder.py:106 | AddIndicatorSheet.tsx:42 | 동일 |
| 11 뉴스 센티먼트 | prompt_builder.py:306 | AddIndicatorSheet.tsx:90 | 동일 |
| 39 달러 인덱스 (DXY) | prompt_builder.py:118 | AddIndicatorSheet.tsx:45 | 동일 |
| 50 PER (주가수익비율) | prompt_builder.py:196 | AddIndicatorSheet.tsx:65 | 동일 |
| 73 순주주수익률 | prompt_builder.py:300 | AddIndicatorSheet.tsx:88 | 동일 |
| (이하 57개 id 생략) | — | — | 전수 동일 |

### 3. 업데이트 주기 차이 (id별)

`INDICATOR_FREQUENCY`(BE 정수 키) ↔ `freq`(FE 객체 필드) 비교 결과 64/64 일치.

대표 검증 케이스:
- 6 미국 기준금리 → BE `'주간'` / FE `'주간'` ✓
- 7 미국 10년 국채 금리 → BE `'일간'` / FE `'일간'` ✓
- 34 실질 GDP → BE `'분기'` / FE `'분기'` ✓
- 37 30년 모기지 금리 → BE `'주간'` / FE `'주간'` ✓
- 5/50/51/52/53/54/55/56/57/58 펀더멘털 10종 → BE/FE 모두 `'분기'` ✓
- 60~73 재무 체질 14종 → BE/FE 모두 `'분기'` ✓

### 4. 카테고리 라벨 분류 차이 (참고)

BE 카테고리(`category`)는 `prompt_builder.py:14`의 5종 분류 키(`market_data`/`macro`/`technical`/`fundamental`/`sentiment`)이며, FE는 17종 한국어 표시 라벨(예: `'수급'`, `'주요 지수'`, `'원자재'`, `'밸류에이션'`, `'재무 체질'`)을 사용. 화면 그루핑 단위만 더 세분화한 것이라 **불일치 아님**(역할 분리 의도). 단, 신규 지표 추가 시 두 분류를 모두 맞춰야 한다는 절차적 부담은 잔존.

---

## description 품질

### 검사 결과
- **항목 수**: 64
- **빈 description**: 0건
- **10자 미만**: 0건
- **최단 길이**: 14자 — id 14 코스닥 지수 `"한국 중소형 성장주 시장 지수."`
- **다음 단문 후보**:
  - id 4 KOSPI 지수 — `"한국 유가증권시장 전체 종목 시가총액 가중 지수."` (24자)
  - id 11 뉴스 센티먼트 — `"뉴스 기사의 긍정/부정 감성 점수. 시장 심리와 여론 방향 측정."` (33자)
  - id 56 배당수익률 — `"주당 배당금을 주가로 나눈 비율. 현금 환원 수준 측정."` (28자)
- **평균 길이(추정)**: 35~45자대 (한국어 1바이트당 1자 가정)

### 최종 평가
- **임계값(10자) 초과 0건** → 단문 결손 측면에서 통과.
- **품질 메모**: id 14 description 14자는 통과선이지만, 다른 지수 항목(예: id 3 S&P 500: `"미국 대형주 500개 종목 시가총액 가중 지수. 글로벌 주식시장 벤치마크."` 38자)에 비해 정보 밀도가 낮음. 권장 임계값을 30자로 올릴 경우 id 14 1건이 보강 후보로 들어옴(P3, blocker 아님).
- **`get_indicator_description` 접두사 매칭** (`prompt_builder.py:351-361`): "EPS 추이 (META)" 등 LLM target_symbol 접미사가 붙은 케이스도 정확하게 description 회복. 단, 카탈로그에 없는 이름은 빈 문자열 반환 → 호출자가 빈 값을 허용하는지 확인 필요.

---

## keyword_rules 고아

### BE: `indicator_matcher.KEYWORD_RULES` (11개 룰, 11개 unique 지표)

| # | keywords (대표) | indicator name | 카탈로그 매칭 |
|---|---|---|---|
| 1 | 외국인, 외인, 순매수 | 외국인 순매수 추이 (id 1) | OK |
| 2 | 금리, 연준, FOMC | 미국 기준금리(id 6), 미국 10년 국채 금리(id 7) | OK |
| 3 | VIX, 공포, 변동성 | VIX (공포지수) (id 8) | OK |
| 4 | 환율, 달러, USD | 원/달러 환율 (id 9) | OK |
| 5 | RSI, MACD, 기술적 | RSI (14일) (id 10) | OK |
| 6 | 센티먼트, 뉴스, 심리 | 뉴스 센티먼트 (id 11) | OK |
| 7 | 실적, EPS, 매출 | EPS 추이 (id 5) | OK |
| 8 | 기관, 연기금 | 기관 순매수 추이 (id 2) | OK |
| 9 | S&P, 나스닥, 미국시장 | S&P 500 (id 3) | OK |
| 10 | 코스피, KOSPI | KOSPI 지수 (id 4) | OK |
| 11 | 선거, 정치, 정책 | VIX(id 8) + KOSPI(id 4) | OK |

- **고아 (카탈로그 미존재) 0건**.
- **결합 방식**: `_find_in_catalog`(`indicator_matcher.py:332`)가 **name 문자열 완전 일치**로 카탈로그를 조회 → BE name 변경 시 sliently break. 데이터-params는 KEYWORD_RULES 자체에 박혀 있어 카탈로그 ↔ KEYWORD_RULES 간 `data_params` 일관성도 수동 동기화 의존.
- **커버리지**: 카탈로그 64개 중 11개(약 17%) — `match_by_keywords`는 사실상 거시·지수·수급·EPS·RSI 위주 안전망.

### FE: `KEYWORD_INDICATOR_MAP` (`AddIndicatorSheet.tsx:109-139`, 28개 룰)

- 사용된 indicatorIds: 53개 unique (1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 15, 16, 20, 21, 23, 24, 25, 26, 30, 31, 32, 33, 34, 35, 36, 37, 39, 40, 50, 51, 52, 53, 54, 55, 56, 57, 58, 60, 61, 62, 63, 64, 65, 66, 67, 68, 69, 70, 71, 72, 73)
- **고아 0건** — 모두 BE 카탈로그에 존재.
- **카탈로그 64개 중 미커버 11개**: 13(다우존스), 14(코스닥), 22(은), 38(달러/유로 환율), 41(스토캐스틱), 42(볼린저 %B), 43(ATR), 44(OBV), 45(SMA50), 46(SMA200), 47(EMA12). 즉 추천 리스트에는 노출되지만 추천 fallback에서는 자동 제안되지 않음 (카탈로그 전체 표시는 별도 경로이므로 문제 아님).

### BE↔FE keyword 룰 격차

- BE(11) vs FE(28): 동일 의미 그룹을 BE가 단일 룰로 묶고, FE가 더 세분화한 결과. 예: FE는 `['per','pbr','밸류에이션']`(밸류에이션 50/51/67/68), `['배당','dividend','자사주']`(주주환원 55/56/66/68/73), `['고용','실업','nfp']`(31/32) 등 12개 펀더멘털·거시 도메인을 추가로 다룸.
- 동일 입력 텍스트("배당 늘어나는 기업")에 대해 BE는 0건 추천 → gemini fallback 진입, FE는 `[55,56,66,68,73]` 즉시 표시. **사용자 경로별 추천 결과 비대칭** 확정. 5월 8일 감사 P2와 동일.

---

## data_params 형식

### 1. data_source 분포 (BE)

| data_source | 항목 수 | 대표 |
|---|---|---|
| `fmp` (symbol/metric/indicator) | 32 | 1, 2, 3, 4, 8, 9, 10, 20~26, 39~47, 50~58 |
| `fred` (series_id) | 11 | 6, 7, 30, 31~38 |
| `metrics` (metric_code) | 14 | 60~73 |
| `news_sentiment` | 1 | 11 |

### 2. 형식 분류 및 검증

| 형식 | 예시 키 | 항목 | FMP 매핑 적정성 |
|---|---|---|---|
| symbol(시세) | `{'symbol': '^GSPC'}` | 3,4,8,9,12,13,14,15,16,20~26,38,39 | 대부분 표준. **id 39 `DX-Y.NYB` 우려** — Yahoo 표기, FMP 표준은 `DXY`가 흔함 (5/8 감사 P1) |
| metric(KeyMetricsTTM 필드) | `{'metric': 'pbRatioTTM'}` | 5, 50, 51, 52, 53, 54, 55, 56, 57 | 대체로 정상. **id 50/52/53은 audit_note로 변환 규칙 명시** (#14 회귀 방지). **id 1/2 `foreign_net_buy`/`institutional_net_buy`는 FMP 비표준** — 별도 어댑터 필요 (잠재적 silent fail) |
| metric+endpoint+scale | `{'metric': 'growthRevenue', 'endpoint': 'financial-growth', 'scale_multiplier': 100}` | 58 | OK — 비표준 endpoint 명시. 호출자가 endpoint 분기 처리 필요 |
| indicator+period | `{'indicator': 'RSI', 'period': 14}` | 10, 40~47 | OK — FMP technical indicator 엔드포인트 표준 |
| series_id | `{'series_id': 'FEDFUNDS'}` | 6, 7, 30~38 | OK — FRED 표준 |
| metric_code | `{'metric_code': 'gross_margin'}` | 60~73 | metrics 시스템 내부 키. 카탈로그 ↔ `metrics.MetricRegistry` 간 키 정합성은 본 감사 범위 외(별도 검증 필요) |
| empty | `{}` | 11 (news_sentiment) | OK — symbol 가변 |

### 3. 알려진 위험/주의 항목 (재기록)

| id | 키 | 위험 | 완화책 |
|---|---|---|---|
| 1 | `metric: foreign_net_buy` | FMP key-metrics-ttm 표준 필드 아님. 별도 호출 어댑터 필요 | KEYWORD_RULES와 카탈로그 양쪽에 동일 키 존재 — 어댑터 미존재 시 동일 silent fail |
| 2 | `metric: institutional_net_buy` | 동상 | 동상 |
| 39 | `symbol: DX-Y.NYB` | FMP에서 Yahoo 형식 미지원 가능성 | `DXY` 또는 ICE 코드(`DXC`) 검증 필요 (P1) |
| 50 | `metric: earningsYieldTTM, inverse: True` | FMP에 `peRatioTTM` 부재 (#14) | audit_note로 명시 + 호출자 측 inverse 변환 필수 |
| 52 | `metric: returnOnEquityTTM, scale_multiplier: 100` | 0~1 ratio (#14) | audit_note로 명시 + ×100 변환 |
| 53 | `metric: returnOnAssetsTTM, scale_multiplier: 100` | 동상 | 동상 |
| 58 | `metric: growthRevenue, endpoint: financial-growth` | key-metrics-ttm 표준 필드 아님 (#14) | endpoint+scale_multiplier로 명시 |

> 이 7건 모두 5월 8일 감사 시점부터 동일하게 잔존. 본 감사일 기준 **신규 위험 0건, 해소 0건**.

### 4. `data_params` BE-only / FE-only 비교

FE `INDICATOR_CATALOG`은 `id/name/category/freq` 4필드만 보유 — **`data_params`는 FE에 미보관**. 호출 책임이 FE에 없으므로 형식 차이 자체는 발생하지 않음. 단, FE `KEYWORD_INDICATOR_MAP`이 indicatorIds로만 결합하기 때문에 BE 측 `data_params`가 잘못되어도 FE에서는 식별 불가 → **FE는 BE 호출 결과를 신뢰만 할 뿐 자체 검증 수단 없음** (구조적 한계, action 불요).

---

## 후속 권장 (P0~P3, 5월 8일 감사와 동일·11일째 잔존)

| 우선순위 | 항목 | 위치 | 비고 |
|---|---|---|---|
| P0 | (없음) | — | 카탈로그 자체 무결성은 OK |
| P1 | `id 39` symbol을 `^DXY` 또는 `DXY`로 교체 후 FMP 응답 회귀 테스트 | `prompt_builder.py:118-121` | 선행 5/8 P1 잔존 |
| P1 | `match_by_gemini` 호출 경로 통일 — `match_indicators_for_premise`도 PK→키워드만 사용 (gemini fallback 제거 또는 카탈로그 강제 매핑) | `indicator_matcher.py:263-266` | common-bugs.md #11 일반화 (5/8 P1 잔존) |
| P2 | KEYWORD_RULES 보강 — FE 28개 도메인에 맞춰 BE 룰을 28개 이상으로 확장 (밸류에이션·재무체질·고용·물가) | `indicator_matcher.py:12-154` | BE/FE 추천 결과 비대칭 해소 |
| P2 | `_find_in_catalog`/KEYWORD_RULES → name 대신 id 결합으로 리팩토링 | `indicator_matcher.py:14-154, 332-338` | 이름 표기 변경 시 silent break 방지 |
| P3 | id 14 코스닥 지수 description을 30자 이상으로 보강 | `prompt_builder.py:42-44` | 임계값 상향 시 cleanup |
| P3 | 카탈로그를 `dataclasses` 또는 Pydantic 스키마로 캡슐화하여 `data_params` shape 강제 | `prompt_builder.py:14-310` | `audit_note` 필수성 표현 가능 |

---

## 결론

- **카탈로그 동기화 자체는 OK** — id/name/freq 64건 전수 일치, description 결손 없음, KEYWORD_RULES/MAP 고아 없음, FE indicatorIds 고아 없음.
- **잠재 위험 4건 잔존** (모두 5월 8일 감사부터 11일째 동결): BE 룰 커버리지(17% vs FE 83%), name 기반 카탈로그 결합, `DX-Y.NYB` 심볼, 비-LLM 경로의 gemini fallback 정책.
- **본 감사일 신규 발견 사항 없음** — 4개 핵심 파일 모두 4월 29일 이후 무변경. 다음 야간 감사에서도 코드가 그대로면 P1 2건은 별도 PR로 처리 권장.
