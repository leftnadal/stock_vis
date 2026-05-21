# 지표 카탈로그 동기화 감사 보고서

- **생성일**: 2026-05-21
- **감사 범위**: `INDICATOR_CATALOG` BE/FE 미러 + `KEYWORD_RULES`(BE) ↔ `KEYWORD_INDICATOR_MAP`(FE)
- **모드**: 읽기 전용. 코드 수정 없음.

## 검사 대상 파일

| 역할 | 경로 | 정의/사용 |
|---|---|---|
| BE 정의 (1차 소스) | `thesis/services/prompt_builder.py:14` | `INDICATOR_CATALOG` 리스트 64개 |
| BE 후처리 | `thesis/services/llm_postprocess.py:33` | `indicator_db_id` ∉ CATALOG → None 교정 |
| BE 키워드 매칭 | `thesis/services/indicator_matcher.py:12` | `KEYWORD_RULES` 11 룰 |
| FE 미러 | `frontend/components/thesis/AddIndicatorSheet.tsx:15` | `INDICATOR_CATALOG` 리스트 64개 |
| FE 키워드 매칭 | `frontend/components/thesis/AddIndicatorSheet.tsx:109` | `KEYWORD_INDICATOR_MAP` 28 룰 |

---

## 요약 (동기화 상태)

| 항목 | 상태 | 비고 |
|---|---|---|
| ID 집합 (BE ↔ FE) | ✅ 일치 | 양쪽 64개 ID 동일 |
| 이름 (BE ↔ FE) | ✅ 일치 | 64/64 정확 일치 |
| 업데이트 주기 (BE `INDICATOR_FREQUENCY` ↔ FE `freq`) | ✅ 일치 | 샘플 검증 모두 일치 |
| BE description 품질 | ✅ 양호 | 64개 모두 비어있지 않고 ≥ 16자 |
| BE `KEYWORD_RULES` 고아 | ✅ 없음 | 모든 룰의 지표명 카탈로그 존재 |
| BE `KEYWORD_RULES` 커버리지 | ⚠️ **낮음** | 11/64 (17.2%)만 키워드 룰 보유 |
| FE `KEYWORD_INDICATOR_MAP` 고아 ID | ✅ 없음 | 모든 indicatorIds 카탈로그 존재 |
| FE vs BE 키워드 룰 비대칭 | ⚠️ **위험** | FE 28 룰, BE 11 룰. 동일 입력에 다른 추천 결과 |
| `data_params` 형식 일관성 | ⚠️ **부분 불일치** | id 1/2/5/58 등 fetcher 미보장 |

**핵심 위험 2건**:
1. **BE↔FE 키워드 매칭 비대칭**: 같은 전제 텍스트에 대해 BE(서버 fallback) vs FE(추천 sheet)가 서로 다른 지표를 제안 — UX/일관성 위험.
2. **데이터 fetcher와 `data_params` 형식 정합성 미보장**: PER/ROE/ROA/매출성장률 등 4건은 `audit_note`로 처리법을 명시하지만 (감사 #14 회귀 방지), `foreign_net_buy`/`institutional_net_buy`/`eps` (id 1/2/5) 등은 표준 FMP key-metrics 필드 아님 → 별도 fetcher 분기 필요.

---

## BE ↔ FE 불일치 목록

### 1. ID/이름 불일치

**없음.**

전체 64개 ID(`1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,20,21,22,23,24,25,26,30,31,32,33,34,35,36,37,38,39,40,41,42,43,44,45,46,47,50,51,52,53,54,55,56,57,58,60,61,62,63,64,65,66,67,68,69,70,71,72,73`)가 BE/FE에 동일하게 정의됨. 이름 문자열도 1:1 매치 (예: `'외국인 순매수 추이'`, `'EV/EBITDA'`, `'스토캐스틱 %K'` 등).

### 2. 카테고리 표기 불일치 (의미상 동일, 문자열 차이)

BE는 `category`가 5개 매크로 카테고리(`market_data` / `macro` / `technical` / `fundamental` / `sentiment`), FE는 16개 세부 카테고리(`수급` / `주요 지수` / `원자재` / `암호화폐` / `금리` / `환율/변동성` / `고용/성장` / `물가/주택` / `기술적` / `펀더멘털` / `재무 체질` / `밸류에이션` / `성장` / `운영 효율` / `이익 품질` / `주주환원` / `심리`).

| 영향 | 평가 |
|---|---|
| API 동작 | 영향 없음 (BE는 매크로 카테고리, FE는 표시 전용 그루핑) |
| 동기화 의무 | 약함 — FE 그루핑 변경 시 BE는 영향 없음 |
| 권장 | BE에 보조 필드(`display_category`)를 두거나 FE 그루핑은 별도 매핑 테이블로 추출 |

### 3. 메타데이터 풍부도 차이

| 필드 | BE | FE |
|---|---|---|
| `description` | ✅ 보유 (64건) | ❌ 없음 |
| `data_source` | ✅ 보유 | ❌ 없음 |
| `data_params` | ✅ 보유 | ❌ 없음 |
| `support_direction` | ✅ 보유 | ❌ 없음 |
| `freq` / `INDICATOR_FREQUENCY` | ✅ 별도 dict | ✅ 인라인 필드 |

FE는 표시·선택용 최소 데이터만 보유. 정상 설계지만 **API로 가져오는 카탈로그 엔드포인트가 없다면** FE description 미러링이 어려움 (FE에서 지표 설명 노출 불가).

---

## description 품질

### 빈 description

**없음.** 64건 모두 비어있지 않음.

### 짧은 description (< 10자)

**없음.** 가장 짧은 항목:

| id | name | description | 길이(한글 기준) |
|---|---|---|---|
| 14 | 코스닥 지수 | 한국 중소형 성장주 시장 지수. | 16자 |
| 4 | KOSPI 지수 | 한국 유가증권시장 전체 종목 시가총액 가중 지수. | 25자 |
| 22 | 은 (Silver) | 은 현물 가격(USD/oz). 산업 수요와 안전자산 이중 역할. | 32자 |

평균 description 길이 ≈ 40~50자. 풍부도 양호.

### 잠재 개선 (정보 부족)

| id | name | 메모 |
|---|---|---|
| 14 | 코스닥 지수 | 시가총액 가중인지, 가격 가중인지 누락 (다른 지수는 명시) |
| 4 | KOSPI 지수 | 단순 정의 외 활용 맥락 없음 (다른 지수는 "벤치마크", "선행지표" 등 언급) |

> 강한 결함 아님 — 참고용 기록.

---

## keyword_rules 고아

### BE `KEYWORD_RULES` 정의 11건 vs 카탈로그 존재 여부

`indicator_matcher.py:12`의 `KEYWORD_RULES`는 지표를 **이름 문자열**로 참조. 모든 참조 이름이 `INDICATOR_CATALOG`에 존재:

| 룰 # | 키워드 그룹 | 참조 지표 이름 | 카탈로그 id | 존재 |
|---|---|---|---|---|
| 1 | 외국인/외인/순매수/순매도/foreign | 외국인 순매수 추이 | 1 | ✅ |
| 2 | 금리/연준/FOMC/fed/기준금리/금리인하/금리인상 | 미국 기준금리 (Fed Funds Rate) | 6 | ✅ |
| 2 | 〃 | 미국 10년 국채 금리 | 7 | ✅ |
| 3 | VIX/공포/변동성/변동성지수/volatility | VIX (공포지수) | 8 | ✅ |
| 4 | 환율/달러/원달러/USD/KRW/원화 | 원/달러 환율 | 9 | ✅ |
| 5 | RSI/MACD/기술적/과매수/과매도/이동평균/MA | RSI (14일) | 10 | ✅ |
| 6 | 센티먼트/여론/뉴스/심리/감성 | 뉴스 센티먼트 | 11 | ✅ |
| 7 | 실적/EPS/매출/영업이익/순이익/PER/earnings | EPS 추이 | 5 | ✅ |
| 8 | 기관/기관투자자/연기금/보험/자산운용 | 기관 순매수 추이 | 2 | ✅ |
| 9 | S&P/S&P500/나스닥/NASDAQ/미국시장/다우/DOW | S&P 500 | 3 | ✅ |
| 10 | 코스피/KOSPI/종합주가지수 | KOSPI 지수 | 4 | ✅ |
| 11 | 선거/정치/정책/대통령/국회 | VIX (공포지수), KOSPI 지수 | 8, 4 | ✅ |

**고아 룰 없음.** 매칭 키 일치도 100%.

### ⚠️ 커버리지 결함 (낮은 매칭 가능성)

BE `KEYWORD_RULES`가 직접 추천 가능한 지표는 11개 (id `1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11`). 나머지 53개 지표(`12~16, 20~26, 30~58, 60~73`)는 키워드 매칭만으로는 **절대 추천되지 않음**. 결과적으로:

- LLM이 `indicator_db_id`를 정확히 추천하지 못한 전제 → 키워드 fallback도 53개 지표는 못 잡음 → **결국 텍스트 fallback이 빈 추천 반환**.
- 사용자가 키워드를 입력한다면 FE는 28개 룰(53개 지표 대부분 커버)로 즉시 추천 표시, BE는 동일 키워드에 빈 결과 — **클라이언트/서버 추천 결과 불일치**.

### FE `KEYWORD_INDICATOR_MAP` 28건 vs 카탈로그 존재 여부

`AddIndicatorSheet.tsx:109` 모든 `indicatorIds`가 카탈로그에 존재:

전체 참조 ID 집합 (중복 제거):
`1, 2, 3, 6, 7, 8, 9, 10, 11, 12, 16, 15, 20, 21, 23, 24, 25, 26, 30, 31, 32, 33, 34, 35, 36, 37, 39, 40, 50, 51, 52, 53, 54, 55, 56, 57, 58, 60, 61, 62, 63, 64, 65, 66, 67, 68, 69, 70, 71, 72, 73`

**고아 ID 없음.** 모두 카탈로그 보유.

### FE에는 있지만 BE에 없는 키워드 매핑 (비대칭)

| FE 키워드 | FE 추천 id | BE 매칭 |
|---|---|---|
| s&p, nasdaq, 미국시장 | 3, 12 | ✅ (룰 9, NASDAQ 추가 없음) |
| 유가/wti/석유/에너지/opec/오일 | 21 | ❌ 없음 |
| 금/gold/금값/안전자산 | 20 | ❌ 없음 |
| 구리/copper/산업금속/경기선행 | 23 | ❌ 없음 |
| 천연가스/lng/가스 | 24 | ❌ 없음 |
| 비트코인/btc/암호화폐/크립토/코인 | 25, 26 | ❌ 없음 |
| per/pbr/밸류에이션 등 | 50, 51, 67, 68 | ❌ 없음 (룰 7은 EPS만) |
| roe/roa/수익성/마진 등 | 52, 53, 57, 62, 60, 61 | ❌ 없음 |
| 부채/레버리지/debt 등 | 54, 63, 64, 65 | ❌ 없음 |
| 배당/dividend/현금흐름/fcf 등 | 55, 56, 66, 68, 73 | ❌ 없음 |
| 회전율/효율/재고/매출채권 | 70, 71 | ❌ 없음 |
| 이익 품질/발생액/accrual | 72, 66 | ❌ 없음 |
| 인플레/cpi/물가 | 33 | ❌ 없음 |
| 고용/실업/nfp/비농업 | 31, 32 | ❌ 없음 |
| gdp/성장/경기/산업생산 | 34, 35 | ❌ 없음 |
| 주택/부동산/모기지 | 36, 37 | ❌ 없음 |
| 반도체/테크/ai/엔비디아/nvidia/칩 | 12, 3 | ❌ 없음 |
| 중국/항셍/홍콩 | 16 | ❌ 없음 |
| 일본/니케이/엔화 | 15 | ❌ 없음 |
| 광고/디지털/플랫폼/meta/구글 | 3, 12 | ❌ 없음 |

⇒ **17건 비대칭**. BE-only fallback 경로가 FE보다 현저히 빈약함.

---

## data_params 형식

### 데이터 소스별 분포 (BE)

| `data_source` | 개수 | 형식 키 |
|---|---|---|
| `fmp` | 36 | `symbol`, `metric`, `indicator+period`, 기타 fetcher별 키 |
| `fred` | 12 | `series_id` |
| `metrics` | 14 | `metric_code` (validation/metrics 시스템) |
| `news_sentiment` | 1 | (빈 dict) |
| **합계** | 63 (id 1, 2는 metric이지만 fetcher 미보장 — 후술) | |

### fmp `data_params` 패턴 그룹

| 패턴 | 예시 | 가정된 fetcher |
|---|---|---|
| `{'symbol': '...'}` | id 3 `^GSPC`, id 8 `^VIX`, id 9 `USDKRW` | FMP `/quote/{symbol}` 또는 `/historical-price-eod` |
| `{'indicator': '...', 'period': N}` | id 10 RSI 14, id 45 SMA 50 | FMP `/technical-indicator/{type}` |
| `{'metric': 'XxxTTM'}` | id 51 `pbRatioTTM`, id 54 `debtToEquityTTM` | FMP key-metrics-ttm endpoint |
| `{'metric': 'foreign_net_buy'}` | id 1, 2 | **FMP key-metrics-ttm 표준 필드 아님** ⚠️ |
| `{'metric': 'eps'}` | id 5 | FMP key-metrics에 직접 없음. `epsTTM` 또는 income-statement 분기 ⚠️ |
| 특수: `inverse=True` | id 50 PER = 1 / `earningsYieldTTM` | `audit_note` 명시 (common-bugs #14 회귀 방지) |
| 특수: `scale_multiplier=100` | id 52 ROE, id 53 ROA, id 58 매출성장률 | `audit_note` 명시 |
| 특수: `endpoint='financial-growth'` | id 58 매출성장률 | key-metrics-ttm 외 별도 endpoint ⚠️ |

### ⚠️ fetcher 실재 정합성 위험 (실측 미확인, 정적 분석만)

| id | name | `data_params` | 위험 |
|---|---|---|---|
| 1 | 외국인 순매수 추이 | `{'metric': 'foreign_net_buy'}` | FMP 미국 데이터에 해당 필드 없음. 한국 시장은 KRX 또는 별도 API 필요 — 현재 fetcher 어디서 처리하는지 불명. |
| 2 | 기관 순매수 추이 | `{'metric': 'institutional_net_buy'}` | id 1과 동일 위험. FMP `/institutional-ownership` 등 별도 endpoint 가능. |
| 5 | EPS 추이 | `{'metric': 'eps'}` | FMP key-metrics-ttm에는 `earningsYieldTTM`만 존재. `epsTTM`은 income-statement-ttm endpoint. 분기 별도. |
| 58 | 매출성장률 (YoY) | `{'metric': 'growthRevenue', 'endpoint': 'financial-growth', 'scale_multiplier': 100}` | `audit_note` 명시 — fetcher가 이 `endpoint` 키를 인식하지 못하면 무시될 수 있음. |
| 9 | 원/달러 환율 | `{'symbol': 'USDKRW'}` | FMP forex 형식은 `USDKRW` 또는 `KRW=X`. 확정 필요. |
| 39 | 달러 인덱스 (DXY) | `{'symbol': 'DX-Y.NYB'}` | Yahoo 형식. FMP는 `DXY.FOREX` 또는 별칭 사용. 형식 충돌 가능. |
| 21 | 원유 (WTI) | `{'symbol': 'CLUSD'}` | FMP commodities는 `CLUSD` 사용 OK, 그러나 `^WTIC`(Stooq) 형식과 혼동 주의. |

> 권장: fetcher 측 코드와의 통합 테스트 1회 — 현재 보고서는 정적 분석만 수행. 실제 API 호출 결과는 별도 PR에서 검증해야 위험 해소.

### `audit_note` 처리 정책

`prompt_builder.py`에 4건 `audit_note`가 주석 형태로 존재 — fetcher가 이 키를 무시하는지/처리하는지 정의 없음. 안전한 디자인은 fetcher가 `audit_note` 키를 **자동으로 제거**한 뒤 fetch 호출하는 것이지만, 현재 코드에서는 확인 불가.

| 대상 id | `audit_note` 내용 |
|---|---|
| 50 (PER) | "PER = 1 / earningsYieldTTM (#14 회귀 방지)" |
| 52 (ROE) | "ratio 0~1 → % (#14 회귀 방지)" |
| 53 (ROA) | "ratio 0~1 → % (#14 동일 패턴)" |
| 58 (매출성장률) | "FMP /financial-growth/ growthRevenue (#14 표준 필드 아님)" |

### FE는 `data_params`를 갖지 않음 → 위험 없음

FE는 `data_params`를 표시·매핑하지 않으므로 형식 불일치 위험은 BE 단일 책임.

---

## 후속 권장 (참고용)

> 이 보고서는 읽기 전용. 아래는 향후 작업 후보일 뿐 본 PR/세션의 행동 항목 아님.

1. **BE `KEYWORD_RULES` 확장 → FE `KEYWORD_INDICATOR_MAP`와 동등 커버리지**: BE 11 룰 → 28 룰 수준으로. (LLM이 ID를 못 찍을 때 fallback 품질 균일화)
2. **카탈로그 API 엔드포인트**: BE가 카탈로그를 1차 소스로 노출하고 FE가 빌드 타임에 미러링 — 미러 드리프트 영구 차단. (현재는 사람이 수동으로 양쪽 일치 유지)
3. **`audit_note` 처리 규약 명문화**: fetcher 단에서 strip 하는지 단위 테스트 1건 추가.
4. **id 1, 2 (외국인/기관 순매수) fetcher 위치 확인 또는 catalog `data_source` 정정**: 현 `data_source='fmp'`는 표준 fetcher가 해당 metric 키를 모를 가능성 큼.
5. **id 58 매출성장률**: `data_source='metrics'`로 전환 (`revenue_growth_yoy` metric_code 존재 시) — `audit_note` 의존 제거.
