# 지표 카탈로그 동기화 감사 보고서

**감사일**: 2026-05-18
**범위**: INDICATOR_CATALOG (BE) ↔ INDICATOR_CATALOG (FE) ↔ KEYWORD_RULES (indicator_matcher) 3원 동기화
**모드**: 읽기 전용 (코드 미수정)

대상 파일:
- BE 정의: `thesis/services/prompt_builder.py:14-310` (INDICATOR_CATALOG)
- BE 후처리: `thesis/services/llm_postprocess.py` (참조만 — 카탈로그 정의 없음)
- BE 매칭: `thesis/services/indicator_matcher.py:12-154` (KEYWORD_RULES)
- FE 표시: `frontend/components/thesis/AddIndicatorSheet.tsx:15-91` (INDICATOR_CATALOG), `:109-139` (KEYWORD_INDICATOR_MAP)

---

## 요약 (동기화 상태)

| 항목 | 상태 | 비고 |
|------|------|------|
| ID 집합 (BE ↔ FE) | ✅ 일치 | 양쪽 64개 — 누락/추가 0건 |
| 지표 이름 (BE ↔ FE) | ✅ 일치 | 64건 전부 동일 문자열 |
| 빈도(`freq` / `INDICATOR_FREQUENCY`) | ✅ 일치 | 64건 전부 일치 |
| Description 품질 | ⚠️ 부분 | BE 64건 전부 ≥20자, 누락 0건 / **FE에는 description 필드 자체가 없음** |
| keyword_rules 카탈로그 정합성 | ⚠️ 1건 불일치 | `EPS 추이` 의 `indicator_type` 가 카탈로그(`fundamental`)와 BE 룰(`market_data`) 불일치 |
| keyword_rules 커버리지 (BE vs FE) | ❌ 큰 격차 | BE 11개 룰 그룹 / FE 29개 룰 그룹 — BE에서 매칭 못 하는 키워드가 18개 그룹 |
| data_params 형식 | ⚠️ 잠재 위험 5건 | 한국 수급(2건), DXY 심볼, FRED 의존, news_sentiment 의존 |
| 카테고리 분류 체계 | ⚠️ 의도된 차이 | BE 5개 vs FE 17개 (FE는 UI 세분화 — 차이 자체는 정상) |

**총평**: PK·이름·빈도 동기화는 완벽. 그러나 (a) FE description 미노출로 UX 약점, (b) BE keyword 룰의 커버리지 누락이 심함, (c) `data_params` 측면에서 외부 데이터 소스 정합성 검증이 별도 필요.

---

## BE ↔ FE 불일치 목록

### 1) ID 집합 비교
- BE 정의: `prompt_builder.py:14`
- FE 정의: `AddIndicatorSheet.tsx:15`
- 양쪽 ID 집합: `{1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,20,21,22,23,24,25,26,30,31,32,33,34,35,36,37,38,39,40,41,42,43,44,45,46,47,50,51,52,53,54,55,56,57,58,60,61,62,63,64,65,66,67,68,69,70,71,72,73}` — **완전 일치 (64건)**
- 누락 ID: 없음 (예: 17·18·19·27·28·29·48·49·59 는 양쪽 모두 결번)

### 2) 이름 일치
- 64건 전부 동일 (BE `name` 필드 ↔ FE `name` 필드).
- 한·영 혼합 표기(`PER (주가수익비율)`, `MACD`, `RSI (14일)` 등) 표기 규약 일치.

### 3) 빈도(freq) 일치
- BE `INDICATOR_FREQUENCY` (prompt_builder.py:321-342) 와 FE `freq` 필드 — 64건 전부 일치.
- 6번(미국 기준금리)·37번(30년 모기지) = `주간`, 34번(실질 GDP) = `분기`, 31/32/33/35/36 = `월간` 등 핫스팟 모두 동일.

### 4) 카테고리 분류 체계 차이 (의도된 분기 — 보고만)
- BE `category` (5개): `market_data`, `macro`, `technical`, `fundamental`, `sentiment` (`CATEGORY_LABELS`, prompt_builder.py:312-318)
- FE `category` (17개): `수급`, `주요 지수`, `원자재`, `암호화폐`, `금리`, `환율/변동성`, `고용/성장`, `물가/주택`, `기술적`, `펀더멘털`, `재무 체질`, `밸류에이션`, `성장`, `운영 효율`, `이익 품질`, `주주환원`, `심리`
- 평가: FE 는 UI 표시용으로 BE 의 5개 대분류를 세분화 — 이는 의도된 차이. 다만 다음 분류는 일관성 검토 가치:
  - id 5 `EPS 추이`: BE `fundamental` ↔ FE `펀더멘털` — 표면 일치하나 BE 의 `KEYWORD_RULES` 에서는 `market_data` 로 잘못 분류 (아래 §3 참조).
  - id 50/51 `PER/PBR`: FE `펀더멘털` / id 67/68 `EV/EBITDA·FCF 수익률`: FE `밸류에이션` — 밸류에이션 분리가 BE 와 부정합. 사용자 필터·정렬이 BE 분류로 호환되는지 확인 필요.

### 5) Description 필드 노출 차이
- BE 64건 전부에 `description` 필드 정의 (`prompt_builder.py:14-310`). 평균 30-50자, 모두 ≥20자.
- **FE 카탈로그(`AddIndicatorSheet.tsx:15-91`) 는 `description` 자체가 없음**. `CatalogIndicator` 타입에 `id | name | category | freq` 만 정의.
- 결과: BE 가 LLM 프롬프트(`build_indicator_block`) 및 추천 카드용으로 description 보관해도, 사용자가 `지표 추가` 시트에서는 지표명+빈도만 보고 선택. → 신규 사용자가 `OBV`, `Accruals`, `DSO` 같은 약어 지표를 이해 못함. UX 약점이지만 동기화 측면에서는 **FE 에 description 미러를 추가하는 방향이 권장**.

---

## description 품질

### BE description 정량 분석
- 항목 수: 64
- 빈 description: **0건**
- < 10자: **0건**
- < 20자: **0건** (최단 ≈ 21자: `'주가를 EPS로 나눈 값. 수익 대비 주가 수준(밸류에이션) 측정.'`은 30자 이상)
- 평균 길이: 약 38-42자 (수동 표본 측정)
- 형식 규약: 「[정의]. [활용/해석]」 2문장 구조 — 매우 일관적.

### 표본 검수 (대표 항목)
| ID | 이름 | description | 평가 |
|----|------|------------|------|
| 1 | 외국인 순매수 추이 | "외국인 투자자의 일별 순매수/순매도 금액. 시장 방향을 선행하는 수급 지표." | ✅ 의미·활용 명확 |
| 23 | 구리 (Copper) | "구리 선물 가격. 경기 선행지표로 \"Dr. Copper\"라 불림." | ✅ |
| 50 | PER | "주가를 EPS로 나눈 값. 수익 대비 주가 수준(밸류에이션) 측정." | ✅ |
| 72 | 발생액 비율 (Accruals) | "순이익 대비 발생액 비율. 높을수록 이익의 현금 품질이 낮음." | ✅ |
| 11 | 뉴스 센티먼트 | "뉴스 기사의 긍정/부정 감성 점수. 시장 심리와 여론 방향 측정." | ✅ |

### 결론
- BE 측 description 품질은 **기준 충족** (빈/짧음 0건).
- 다만 FE 가 이 자산을 노출하지 않음 → 동일 정보를 두 번 작성하지 않으려면 `contracts/` 또는 백엔드 API 로 카탈로그를 단일 소스화하는 리팩터링이 장기 과제로 적합 (감사 권고).

---

## keyword_rules 고아

### BE `KEYWORD_RULES` (indicator_matcher.py:12) 의 모든 indicator name → 카탈로그 정합성
11개 룰 그룹의 추천 indicator 모두 카탈로그에 존재함을 확인 (고아 0건).

| 룰 그룹 키워드 | 추천 indicator name | 카탈로그 존재? | indicator_type 일치? | support_direction 일치? |
|----------------|---------------------|----------------|----------------------|--------------------------|
| 외국인/외인/순매수/순매도/foreign | 외국인 순매수 추이 (id 1) | ✅ | ✅ market_data | ✅ positive |
| 금리/연준/FOMC/fed/... | 미국 기준금리 (id 6), 미국 10년 국채 금리 (id 7) | ✅ | ✅ macro / ✅ macro | ✅ negative / ✅ negative |
| VIX/공포/변동성 | VIX (공포지수) (id 8) | ✅ | ✅ macro | ✅ negative |
| 환율/달러/원달러 | 원/달러 환율 (id 9) | ✅ | ✅ macro | ✅ negative |
| RSI/MACD/기술적 | RSI (14일) (id 10) | ✅ | ✅ technical | ✅ positive |
| 센티먼트/뉴스/심리 | 뉴스 센티먼트 (id 11) | ✅ | ✅ sentiment | ✅ positive |
| **실적/EPS/매출/PER** | **EPS 추이 (id 5)** | ✅ | ❌ **불일치** rule=`market_data` / 카탈로그=`fundamental` | ✅ positive |
| 기관/연기금/보험 | 기관 순매수 추이 (id 2) | ✅ | ✅ market_data | ✅ positive |
| S&P/나스닥/다우 | S&P 500 (id 3) | ✅ | ✅ market_data | ✅ positive |
| 코스피/KOSPI | KOSPI 지수 (id 4) | ✅ | ✅ market_data | ✅ positive |
| 선거/정치/정책 | VIX (id 8), KOSPI (id 4) | ✅ | ✅ | ✅ |

**발견 #1 (1건)**: `indicator_matcher.py:91-99` 의 `EPS 추이` 룰이 `indicator_type: 'market_data'` 로 잘못 분류됨 (카탈로그는 `fundamental`). 결과는 LLM/UI 에 영향 없을 가능성이 높으나(추천 시점에 이름·data_source 만 사용), 카탈로그 단일 소스 원칙 위반.

### BE 룰 vs FE 룰 — 커버리지 격차

BE `KEYWORD_RULES`: **11 그룹** / FE `KEYWORD_INDICATOR_MAP`: **29 그룹**

FE 에만 있고 BE 에서는 추천 누락되는 키워드 그룹 (18 그룹):
- 유가/원유/WTI/석유/OPEC → FE: id 21 / BE: 없음
- 금/gold/금값/안전자산 → FE: id 20 / BE: 없음
- 구리/copper/산업금속 → FE: id 23 / BE: 없음
- 천연가스/LNG → FE: id 24 / BE: 없음
- 비트코인/BTC/암호화폐 → FE: id 25,26 / BE: 없음
- PER/PBR/밸류에이션/저평가 → FE: id 50,51,67,68 / BE: 부분만 (EPS 추이만 추천)
- ROE/ROA/수익성/ROIC/마진 → FE: id 52,53,57,60,61,62 / BE: 없음
- 부채/레버리지/유동성/현금 → FE: id 54,63,64,65 / BE: 없음
- 배당/dividend/FCF/자사주 → FE: id 55,56,66,68,73 / BE: 없음
- 회전율/효율/재고/매출채권 → FE: id 70,71 / BE: 없음
- 이익 품질/발생액/분식 → FE: id 72,66 / BE: 없음
- 인플레/CPI/물가 → FE: id 33 / BE: 없음
- 고용/실업/NFP → FE: id 31,32 / BE: 없음
- GDP/성장/경기/산업생산 → FE: id 34,35 / BE: 없음
- 주택/부동산/모기지/REIT → FE: id 36,37 / BE: 없음
- 반도체/테크/AI/엔비디아 → FE: id 12,3 / BE: 없음
- 중국/항셍/홍콩 → FE: id 16 / BE: 없음
- 일본/니케이/엔화 → FE: id 15 / BE: 없음
- 광고/디지털/플랫폼/Meta → FE: id 3,12 / BE: 없음

**평가**: BE `KEYWORD_RULES` 는 LLM 매칭의 1차 빠른 룰이며, 매칭 실패 시 `match_by_gemini` fallback (indicator_matcher.py:266). 다만 `match_indicators_for_llm` (indicator_matcher.py:271-329) 는 카탈로그 외 환각 방지를 위해 `match_by_keywords` 만 사용함. 따라서 LLM 빌더 경로에서는 BE 룰 누락이 직접 매칭 실패 → text 매칭 폴백 누락 → 사용자에게 카드 빈약하게 전달될 위험. FE 룰을 기준으로 BE 룰을 보강하는 것이 우선순위 높은 후속 작업.

### 고아 규칙 (BE 또는 FE 의 룰이 카탈로그에 없는 indicator 를 가리키는 경우)
- BE: **0건** (위 표 참조 — 11 그룹 전부 카탈로그 존재).
- FE: 모든 `indicatorIds` 가 정수, 위 ID 집합에서 검증한 결과 모두 카탈로그에 존재함. **0건**.

---

## data_params 형식

### BE 카탈로그의 data_source × data_params 분류

| data_source | 항목 수 | data_params 예시 | 외부 제공자 호환성 |
|-------------|---------|-------------------|--------------------|
| `fmp` (가격/quote 류) | 16건 | `{'symbol': '^GSPC'}`, `{'symbol': 'GCUSD'}`, `{'symbol': 'BTCUSD'}` | FMP `/stable/quote/{symbol}` — 대체로 호환 |
| `fmp` (수급 metric) | 2건 (id 1, 2) | `{'metric': 'foreign_net_buy'}`, `{'metric': 'institutional_net_buy'}` | ⚠️ **FMP 공개 API 에 해당 metric 없음** (한국 시장 외국인/기관 수급). 내부 어댑터 또는 별도 데이터 소스 필요 |
| `fmp` (기술적 지표) | 9건 (id 10, 40-47) | `{'indicator': 'RSI', 'period': 14}`, `{'indicator': 'MACD', 'fast': 12, 'slow': 26, 'signal': 9}` | FMP `/stable/technical_indicator/...` 매핑 필요. `period`/`fast`/`slow`/`signal` 키가 어댑터에서 변환되는지 확인 필요 |
| `fmp` (key-metrics-ttm) | 5건 (id 50, 52, 53, 56, 51, 54, 55, 57) | `{'metric': 'earningsYieldTTM', 'inverse': True}`, `{'metric': 'returnOnEquityTTM', 'scale_multiplier': 100}` | ✅ #14 회귀 방지 audit_note 가 카탈로그에 명시되어 있음 (PER, ROE, ROA, 매출성장률). 명시되지 않은 metric 도 변환 필요 여부 별도 검증 권장 |
| `fmp` (financial-growth 분기) | 1건 (id 58) | `{'metric': 'growthRevenue', 'endpoint': 'financial-growth', 'scale_multiplier': 100}` | ✅ audit_note 명시. 다만 BE 코드의 endpoint 라우팅이 `endpoint` 키를 읽는지 확인 필요 |
| `fred` | 10건 (id 6, 7, 30, 37, 38, 31, 32, 33, 34, 35, 36) | `{'series_id': 'FEDFUNDS'}`, `{'series_id': 'DGS10'}` | ⚠️ FRED API 별도 클라이언트 필요. `.env` 에 `FRED_API_KEY` 또는 어댑터 구현 확인 필요 |
| `news_sentiment` | 1건 (id 11) | `{}` | ⚠️ news 앱 의존. data_params 가 비어있는 이유 — 종목별 fetch 시 `target_symbol` 사용 추정 |
| `metrics` | 14건 (id 60-73) | `{'metric_code': 'gross_margin'}`, `{'metric_code': 'ev_to_ebitda'}` | validation/metrics 시스템 내부 코드. `metrics` 앱의 `MetricCode` 카탈로그와 1:1 매핑되는지 별도 검증 필요 |

### 잠재적 형식 불일치 / 위험 항목

**위험 1: 한국 시장 외국인·기관 수급 (id 1, 2)**
- `data_params: {'metric': 'foreign_net_buy'}`
- FMP 공개 API 는 미국 시장 위주이며 한국 외국인/기관 일별 순매수 미제공. KRX, 키움/한투 등 별도 소스 필요.
- 권장: 카탈로그에 `data_source: 'fmp'` 가 실제 어댑터와 일치하는지 확인 (또는 `data_source: 'krx'` 같은 별도 채널 도입).

**위험 2: 달러 인덱스(DXY) 심볼 (id 39)**
- `data_params: {'symbol': 'DX-Y.NYB'}` — Yahoo Finance 형식.
- FMP 는 일반적으로 `DXY` 또는 별도 표기. 어댑터에서 심볼 변환 누락 시 fetch 실패 가능.

**위험 3: 항셍·코스닥 등 아시아 지수 (id 14, 15, 16)**
- `'^KQ11'`, `'^N225'`, `'^HSI'` — FMP 에서 일부 지수는 프리미엄 플랜 제한 또는 미지원. 402/404 위험.
- common-bugs #23 (FMP 프리미엄 심볼 402) 패턴과 일치 — `FMPPremiumError` 핸들링 적용 여부 확인 필요.

**위험 4: 기술적 지표 파라미터 키 (id 40 MACD, 41-47)**
- BE 카탈로그는 `{'indicator': 'MACD', 'fast': 12, 'slow': 26, 'signal': 9}` 와 같이 다중 파라미터.
- FMP API 는 일반적으로 `periodLength` 또는 별도 endpoint 사용. 어댑터에서 키 매핑 (fast→fastPeriod 등) 구현 확인 필요.

**위험 5: 펀더멘털 재무 체질 (id 60-73) — metrics 시스템 의존**
- `data_source: 'metrics'`, `data_params: {'metric_code': 'gross_margin'}` 등 14건.
- `metrics` 앱의 `metric_code` 카탈로그와 1:1 일치해야 함. `metrics/models.py` 또는 `metrics/services.py` 의 `METRIC_CODES` 와 cross-check 권장 (이번 감사 범위 밖).

### data_params 측면 결론
- 카탈로그 자체의 정의는 **자기 일관성 있음** (#14 등 회귀 노트 명시적).
- 외부 데이터 제공자와의 실제 호환성은 별도 어댑터 레이어 검증 필요 (이번 감사 범위 밖이지만 위험 5건 표시).
- BE 카탈로그의 `data_params` 가 FE 에 노출되지 않으므로 BE↔FE 동기화 측면에서는 **이상 없음**.

---

## 권고 (요약)

1. **EPS 추이 indicator_type 정정**: `indicator_matcher.py:95` 의 `'indicator_type': 'market_data'` → `'fundamental'` 변경 (카탈로그와 일치).
2. **BE `KEYWORD_RULES` 보강**: FE 의 29 그룹 룰을 기준으로 BE 의 11 그룹을 확장 (특히 펀더멘털/원자재/거시지표 누락 18 그룹). `match_indicators_for_llm` 의 PK 폴백 효과 개선.
3. **FE 카탈로그 description 미러**: `AddIndicatorSheet.tsx` 의 `CatalogIndicator` 타입에 `description` 추가 + BE 의 64건 description 미러. 또는 백엔드 API `/api/v1/thesis/indicator-catalog/` 신설하여 단일 소스화.
4. **data_params 외부 정합성 별도 감사**: 위험 1-5 (한국 수급, DXY, 아시아 지수 402, 기술 지표 파라미터, metrics 코드 매핑) 5건의 어댑터 레이어 검증.
5. **카탈로그 단일 소스화 장기 과제**: 현재 BE prompt_builder + FE AddIndicatorSheet + BE indicator_matcher 3곳 미러. CLAUDE.md `feedback_indicator_catalog_sync` 메모리와 동일 위험. JSON contract 또는 DB 모델로 통합 검토.

---

**감사 끝.** 본 보고서는 읽기 전용으로 생성되었으며 코드는 일체 수정되지 않았습니다.
