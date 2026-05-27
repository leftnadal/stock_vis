# 지표 카탈로그 동기화 감사 보고서

- 일시: 2026-05-27
- 범위: BE `thesis/services/prompt_builder.py` ↔ FE `frontend/components/thesis/AddIndicatorSheet.tsx` ↔ 매칭 `thesis/services/indicator_matcher.py`
- 모드: 읽기 전용 (코드 수정 없음)

---

## 요약 (동기화 상태)

| 항목 | 결과 | 상세 |
|------|------|------|
| BE 카탈로그 항목 수 | **64** | `prompt_builder.py:14-310` |
| FE 카탈로그 항목 수 | **64** | `AddIndicatorSheet.tsx:15-91` |
| BE↔FE ID 일치 | ✅ **64/64** | 누락/추가 없음 |
| BE↔FE 이름 일치 | ✅ **64/64** | 모든 `name` 동일 |
| BE↔FE 업데이트 주기 | ✅ **일치** | BE `INDICATOR_FREQUENCY` ↔ FE `freq` 전수 비교 |
| FE description 필드 | ❌ **없음** | FE는 `description`을 미러하지 않음 (단일 갭) |
| 카테고리 분류 | ⚠️ **의도된 차이** | BE 5개 대분류 ↔ FE 17개 세분류 |
| BE keyword_rules 키 정합성 | ✅ **11/11 유효** | 모두 카탈로그 이름과 일치 |
| BE keyword_rules 필드 형식 | ❌ **불일치** | `indicator_type` vs `category`, `reason` vs `description`, `id` 누락 |
| BE↔FE keyword 룰 풍부도 | ⚠️ **대칭 깨짐** | BE 11 룰 vs FE 28 룰 |
| FMP `data_params` 매핑 주석 | ✅ **3건 명시** | id:50/52/53 — `audit_note` 주석 보존 |
| FMP `data_params` 매핑 누락 | ⚠️ **다수** | id:1, 2, 5, 51, 54~57 — endpoint/스케일 명세 없음 |

**결론**: ID/이름/주기는 정합. 단, ① FE는 description을 미러하지 않고, ② BE keyword_rules가 INDICATOR_CATALOG와 별도 스키마이며, ③ FE 키워드 매칭이 BE 대비 2.5배 풍부해 같은 전제 텍스트에서 BE/FE 추천 결과가 달라질 수 있음.

---

## BE ↔ FE 불일치 목록

### ID 단위 불일치
**없음.** BE 64개, FE 64개, ID 셋 완전 일치.

```
BE IDs = {1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,20,21,22,23,24,25,26,
          30,31,32,33,34,35,36,37,38,39,40,41,42,43,44,45,46,47,
          50,51,52,53,54,55,56,57,58,60,61,62,63,64,65,66,67,68,69,70,71,72,73}
FE IDs = (동일)
```

### 이름 단위 불일치
**없음.** 64개 모두 동일 문자열.

### 업데이트 주기(freq) 단위 불일치
**없음.** BE `INDICATOR_FREQUENCY`(prompt_builder.py:321-342) ↔ FE 인라인 `freq` 전수 일치.

| 분류 | BE 주기 | FE 주기 | 결과 |
|------|---------|---------|------|
| id:6 (Fed Funds) | 주간 | 주간 | ✅ |
| id:7, 30 (UST 10Y/2Y) | 일간 | 일간 | ✅ |
| id:37 (모기지 30Y) | 주간 | 주간 | ✅ |
| id:31~36 (고용/물가/주택) | 월간/분기 | 월간/분기 | ✅ |
| id:34 (실질 GDP) | 분기 | 분기 | ✅ |
| id:5, 50~58, 60~73 (펀더멘털) | 분기 | 분기 | ✅ |

### 카테고리 분류 차이 (의도된 차이)
BE 5개 대분류로 운영:
```
market_data, macro, technical, fundamental, sentiment
```
FE 17개 세분류로 사용자 표시:
```
수급, 주요 지수, 원자재, 암호화폐, 금리, 환율/변동성,
고용/성장, 물가/주택, 기술적, 펀더멘털, 재무 체질,
밸류에이션, 성장, 운영 효율, 이익 품질, 주주환원, 심리
```

대응 예시:
- BE `fundamental` 24개 → FE 7개 카테고리(펀더멘털/재무 체질/밸류에이션/성장/운영 효율/이익 품질/주주환원)로 분산
- BE `market_data` 16개 → FE 4개 카테고리(수급/주요 지수/원자재/암호화폐)로 분산
- BE `macro` 14개 → FE 4개 카테고리(금리/환율/변동성/고용/성장/물가/주택)로 분산

**리스크**: BE 측 분기 로직(`data_source`별 분기, 프롬프트 그룹핑)은 5분류 기준이고, FE 측은 17분류 — 분류 추가 시 단방향만 갱신될 위험. 단일 카테고리 메타데이터 소스 부재.

### 누락된 미러: description 필드
- BE는 64개 모두 `description` 필드를 보유 (사용자 노출용 한 줄 설명)
- FE `CatalogIndicator` 타입(`AddIndicatorSheet.tsx:8-13`)에 `description` 필드 자체가 없음
- FE는 이름/주기/카테고리만 표시 → BE description은 UI에 노출되지 않음

→ 백엔드에서 description 채워도 사용자 경험에 반영되지 않는 단방향 갭.

---

## description 품질

### 빈 description
**없음.** 64개 모두 채워져 있음.

### 너무 짧은 description (<10자)
**없음.** 최단 description은 24자 ('한국 유가증권시장 전체 종목 시가총액 가중 지수.', id:4).

### 평균 길이/품질 샘플
- id:8 VIX: "S&P 500 옵션 내재변동성. 시장 공포와 불확실성 수준 측정." (35자)
- id:50 PER: "주가를 EPS로 나눈 값. 수익 대비 주가 수준(밸류에이션) 측정." (38자)
- id:62 ROIC: "투하자본 대비 영업이익. 사업에 투입된 자본의 진정한 수익률." (33자)

품질 자체는 양호. 단 위 "FE 누락" 갭으로 인해 사용자에게 노출되는 채널은 LLM 프롬프트와 관제실 설명용으로 한정.

---

## keyword_rules 고아

### KEYWORD_RULES (`indicator_matcher.py:12-154`, 11개 룰)
지표명 → 카탈로그 존재 여부:

| 룰 # | 키워드 그룹 (요약) | indicator name | 카탈로그 매칭 | 결과 |
|------|-----------------|----------------|--------------|------|
| 1 | 외국인 | 외국인 순매수 추이 | id:1 | ✅ |
| 2 | 금리/연준 | 미국 기준금리 (Fed Funds Rate), 미국 10년 국채 금리 | id:6, 7 | ✅ |
| 3 | VIX/변동성 | VIX (공포지수) | id:8 | ✅ |
| 4 | 환율/달러 | 원/달러 환율 | id:9 | ✅ |
| 5 | RSI/MACD/기술적 | RSI (14일) | id:10 | ✅ |
| 6 | 센티먼트/뉴스 | 뉴스 센티먼트 | id:11 | ✅ |
| 7 | 실적/EPS | EPS 추이 | id:5 | ✅ |
| 8 | 기관 | 기관 순매수 추이 | id:2 | ✅ |
| 9 | S&P/나스닥/다우 | S&P 500 | id:3 | ✅ |
| 10 | 코스피 | KOSPI 지수 | id:4 | ✅ |
| 11 | 선거/정치 | VIX (공포지수), KOSPI 지수 | id:8, 4 | ✅ |

**고아 규칙: 없음.** 모든 indicator name이 INDICATOR_CATALOG에 존재.

### 잠재 리스크 — name 기반 매칭
- KEYWORD_RULES는 `name` 문자열로 카탈로그를 참조 (id 미참조)
- `_find_in_catalog(name)`(`indicator_matcher.py:332-338`)에서 정확 문자열 매칭
- 카탈로그의 `name` 변경 시 KEYWORD_RULES 모두 무성 실패

권장: KEYWORD_RULES 항목에 `id: <int>`를 보존하여 id 기준 매칭으로 전환.

### 필드 스키마 불일치 (스타일 부채)
KEYWORD_RULES indicator dict의 키 이름이 INDICATOR_CATALOG와 다름:

| KEYWORD_RULES 키 | INDICATOR_CATALOG 키 | 동등성 |
|-----------------|--------------------|-------|
| `name` | `name` | ✅ |
| `data_source` | `data_source` | ✅ |
| `data_params` | `data_params` | ✅ |
| `indicator_type` | `category` | ❌ 키 이름 다름 |
| `support_direction` | `support_direction` | ✅ |
| `reason` | `description` | ❌ 키 이름·의미 다름 |
| (없음) | `id` | ❌ id 누락 |

→ `match_indicators_for_premise()` 반환값이 `match_indicators_for_llm()` 반환값과 다른 스키마를 가짐. 사용처에서 `indicator_type`/`category` 모두 처리 필요 — 호출자 부담.

### BE↔FE 키워드 룰 대칭성
- BE `KEYWORD_RULES`: **11개 룰** (카탈로그 64개 중 11 지표만 1차 매칭)
- FE `KEYWORD_INDICATOR_MAP`: **28개 룰** (`AddIndicatorSheet.tsx:109-139`)
- FE에만 있는 매칭 도메인 (BE 미커버):
  - 원자재: 유가/금/구리/천연가스 → id:21, 20, 23, 24
  - 암호화폐: 비트코인 → id:25, 26
  - 밸류에이션: PER/PBR → id:50, 51, 67, 68
  - 수익성: ROE/ROA/ROIC → id:52, 53, 57, 62, 60, 61
  - 재무건전성: 부채/레버리지 → id:54, 63, 64, 65
  - 주주환원: 배당/FCF/자사주 → id:55, 56, 66, 68, 73
  - 운영 효율: 회전율/재고 → id:70, 71
  - 이익 품질: 발생액 → id:72, 66
  - 인플레/CPI → id:33
  - 고용/실업/NFP → id:31, 32
  - GDP/성장/산업생산 → id:34, 35
  - 주택/모기지 → id:36, 37
  - 지역: 중국/일본/한국 → id:16, 15, 4
  - 섹터: 반도체·테크/광고·디지털 → id:12, 3

**결과**: 동일 전제 텍스트를 BE 보조 매칭에 넣으면 추천이 비고, FE 빌더에 넣으면 풍부하게 매칭. 같은 사용자가 BE LLM 미사용 경로(키워드 fallback)와 FE 'AddIndicatorSheet' 추천 경로에서 다른 추천을 받음 — 추천 일관성 측면의 부채.

---

## data_params 형식

### BE 카탈로그가 기대하는 data_params 패턴

| data_source | 키 형식 | 예시 ID |
|------------|--------|--------|
| `fmp` (시장 가격/지수) | `{'symbol': '<티커>'}` | 3 (^GSPC), 8 (^VIX), 21 (CLUSD) |
| `fmp` (기술적) | `{'indicator': '<NAME>', 'period': <int>}` | 10, 40, 45, 46, 47 |
| `fmp` (수급) | `{'metric': '<key>'}` | 1 (foreign_net_buy), 2 (institutional_net_buy) |
| `fmp` (펀더멘털 단순) | `{'metric': '<TTM 필드>'}` | 5, 51, 54, 55, 56, 57 |
| `fmp` (펀더멘털 보정) | `{'metric': ..., 'inverse': True}` 또는 `scale_multiplier` | 50, 52, 53 |
| `fmp` (financial-growth) | `{'metric': ..., 'endpoint': 'financial-growth', 'scale_multiplier': 100}` | 58 |
| `fred` | `{'series_id': '<FRED ID>'}` | 6, 7, 30~38 |
| `metrics` (사내 metric_code) | `{'metric_code': '<code>'}` | 60~73 |
| `news_sentiment` | `{}` (빈) | 11 |

### 실제 FMP 응답과의 정합성

#### 명시적으로 보정 주석을 남긴 항목 (common-bugs #14)
- **id:50 PER** — FMP `key-metrics-ttm`에 `peRatioTTM` 미존재 → `earningsYieldTTM` + `inverse: True` 사용 (PER = 1 / earningsYieldTTM). 주석에 회귀 방지 명시.
- **id:52 ROE** — FMP `returnOnEquityTTM` 스케일 0~1 → `scale_multiplier: 100` 적용 (% 변환).
- **id:53 ROA** — `returnOnAssetsTTM` 동일 패턴, scale 보정.
- **id:58 매출성장률** — `key-metrics-ttm`에 미존재. `/financial-growth/` 엔드포인트 + `growthRevenue` 필드, scale 0~1. `endpoint`/`scale_multiplier` 명시. 다만 주석에서 "권장: data_source='metrics' (quarterly_metric_fetcher 분기)"로 마이그레이션 후보로 표기.

#### 정합성 의문/명세 부족 항목
- **id:1 foreign_net_buy / id:2 institutional_net_buy** — FMP 표준 엔드포인트에서 직접 노출되는 필드명이 아님. 한국 시장 수급 데이터일 가능성이 높음 → 어떤 어댑터/엔드포인트가 처리하는지 `data_params`에 미표기. 데이터 제공자가 모호.
- **id:5 EPS 추이 (`metric: 'eps'`)** — `key-metrics-ttm`에 'eps' 필드는 존재하지 않음 (FMP는 `epsTTM` 또는 income-statement). 정확한 필드 매핑은 어댑터 측에서 처리되어야 함. 카탈로그 단독으로 보면 모호.
- **id:51 PBR (`pbRatioTTM`)** — FMP 표준 필드. ✅
- **id:54 부채비율 (`debtToEquityTTM`)** — FMP 표준 필드. ✅
- **id:55 FCF (`freeCashFlowTTM`)** — FMP 표준 필드. ✅
- **id:56 배당수익률 (`dividendYieldTTM`)** — FMP 표준 필드 (단, 일부 플랜에서는 % 스케일이 다를 수 있음 — `scale_multiplier` 미명시).
- **id:57 영업이익률 (`operatingProfitMarginTTM`)** — FMP 표준 필드. 단, 0~1 vs % 스케일 명세 없음.
- **id:60~73 (metrics)** — `metric_code`로 사내 `metrics` 시스템에 위임. 카탈로그만으로는 실제 계산식/소스 확인 불가. 시스템 간 책임 분리는 깔끔하나, 카탈로그 단독 감사는 불가능.

#### 기술적 지표 (id:10, 40~47)
`{'indicator': 'RSI', 'period': 14}` 등 표준화된 형태. FMP `/stable/technical-indicators/<period>` 엔드포인트로 매핑 추정. data_params만으로 endpoint 식별 가능.

### 잠재 부채 정리
1. **endpoint 명세가 일부에만 있음** (id:58만 `endpoint` 키 보유). 다른 펀더멘털 지표가 어느 FMP 엔드포인트를 사용하는지 카탈로그에서 확인 불가 — 어댑터 측 매핑에 의존.
2. **scale_multiplier 정책 불일치** — id:52/53/58은 명시. id:56(`dividendYieldTTM`), id:57(`operatingProfitMarginTTM`)은 동일하게 0~1 스케일일 가능성이 있으나 명세 없음. % 표시 일관성 검증 필요.
3. **id:1, 2 (한국 시장 수급)** — 데이터 제공자가 사실상 FMP 표준 외 어댑터 — `data_source: 'fmp'`로 일괄 표기되어 있어 fetcher 라우팅 디버깅 시 혼동 가능. `data_source: 'fmp_kr'` 또는 별도 source 분리 후보.
4. **KEYWORD_RULES의 data_params 사본** — 11개 룰의 indicator dict가 카탈로그와 별도 `data_params`를 가지고 있어 카탈로그 변경 시 동기화 누락 위험. 룰은 `id`만 남기고 카탈로그를 1차 소스로 삼는 패턴이 권장됨.

---

## 부록: 권장 후속 작업 (코드 수정 없음, 참고용)

| 우선순위 | 항목 | 이유 |
|---------|------|------|
| P1 | KEYWORD_RULES → `id` 기반 매칭으로 전환 | name 문자열 변경 시 무성 실패 차단 |
| P1 | KEYWORD_RULES 인디케이터 사본 제거, 카탈로그 1차 소스화 | data_params/카테고리 이중 관리 부채 해소 |
| P2 | FE `CatalogIndicator`에 `description` 필드 추가, BE에서 API로 전달 | description이 사용자에게 노출되도록 갭 해소 |
| P2 | BE↔FE 카탈로그 단일 소스화 (예: spec JSON → 양쪽 생성) | 64개 항목 수동 미러 운영 부채 |
| P2 | id:1, 2 `data_source` 명세 정확화 (`fmp_kr` 또는 별도 어댑터 표기) | 라우팅 디버깅성 개선 |
| P3 | BE KEYWORD_RULES를 FE KEYWORD_INDICATOR_MAP과 동등 풍부도로 확대 | BE 키워드 fallback이 11/64 커버에 그침 |
| P3 | id:56/57 등 0~1 스케일 의심 항목의 `scale_multiplier` 정책 명시 | #14 회귀 방지 패턴 일관화 |
| P3 | id:58 `data_source='metrics'`로 마이그레이션 (카탈로그 주석 권장) | quarterly_metric_fetcher 단일 경로 통일 |

---

(끝 — 코드 변경 없음, 감사 결과만 기록)
