# Stock-Vis Metric Dictionary v1.0

**문서 버전**: v1.2 (2026-04-18 업데이트)
**대상 프리셋**: MVP 12개
**총 지표 수**: 57개 (Type 1: 39 / Type 2: 13 / Type 3: 5)
**연관 문서**: `stock-vis-preset-design-v3.md` (v3.1), `stock-vis-preset-reference.md`, `stock-vis-preset-metrics-matrix.md`

---

## 1. 개요

본 Dictionary는 Stock-Vis의 Portfolio Coach가 사용하는 모든 지표의 **산식, 데이터 소스, 방향성, 결측 정책, 프리셋별 계층 배정**을 `metric_id` 단위로 정의한다. 개별 프리셋이 참조하는 진리의 원천(single source of truth)이며, Saved Analysis의 불변성 보장을 위해 `metric_definition_version`으로 버전 관리된다.

### 범위와 경계

- **포함**: 57개 지표의 정의·산식·소스·결측 정책·프리셋 매핑
- **제외**: 프리셋별 철학·진단 카드 디자인·UI 렌더링 (별도 문서)
- **참조**: 설계서 v3.1의 §9 (결측치 정책, 버전 관리, 도메인 엔티티)

### 주의 사항

- 57개 지표 전체가 상세 정의 완료. 지표 1~10(수익성·성장·밸류에이션)은 이전 세션 원본 기반으로 검증 완료.
- FMP API 필드명은 버전마다 변경 가능. 구현 전 실제 API 응답과 교차 검증 권장.

---

## 2. 공통 스키마

### 2-1. 공통 코어 필드 (모든 Type 공통)

| 필드 | 값/형식 | 설명 |
|---|---|---|
| `metric_id` | string (snake_case) | 고유 식별자 |
| `display_name` | string | UI 표시명 |
| `description` | string (1~2문장) | 지표 설명 |
| `metric_type` | `stock_level` / `portfolio_level` / `composite` | Type 분류 |
| `direction` | `higher_is_better` / `lower_is_better` / `정보 제공` | 기본 방향성 |
| `applicable_presets` | list of (preset_id, tier) | 사용 프리셋과 계층 |
| `refresh_frequency` | string | 갱신 주기 |
| `comparison_group` | string | Type별 해석 상이 (§2-4) |
| `missing_policy` | table | 결측 처리 규칙 |
| `fallback_rule` | string | 비교군 표본 부족 시 대체 |

### 2-2. Type 1 확장 필드 (`stock_level`)

| 필드 | 설명 |
|---|---|
| `formula` | 산출 공식 (수식 표현) |
| `formula_detail` | 공식의 구현 세부 사항, 상수, TTM 방식 |
| `source_type` | `fmp_native` / `calculated` |
| `fmp_endpoint` | FMP API 엔드포인트 |
| `fmp_fields` | FMP 응답 필드명 목록 |
| `aggregation_type` | `count_based` / `numeric_aggregation` (멀티이어 지표 한정) |
| `min_years` | 계산 가능한 최소 연수 |
| `window_trading_days` | 가격 시계열 창 (거래일) |
| `price_source` | `adjusted` / `raw` |
| `excluded_sectors` | 해당 지표가 부적합한 업종 목록 |
| `ttm_method` | TTM 구성 방식 (예: netIncome → `sum`, equity → `latest`) |
| `display_condition` | 표시 가능 조건 |

### 2-3. Type 2 확장 필드 (`portfolio_level`)

| 필드 | 설명 |
|---|---|
| `input_schema` | 입력 포트폴리오 구조 (예: `[{ticker, weight}]`) |
| `calculation_logic` | 포트폴리오 단위 계산 알고리즘 |
| `dependencies` | 종목 단위로 필요한 Type 1 metric 목록 |
| `benchmark` | 비교 대상 포트폴리오 |
| `lookback_window_days` | 과거 기간 (거래일) |
| `min_holdings` | 계산 가능한 최소 종목 수 |
| `price_source` | `adjusted` / `raw` |

### 2-4. Type 3 확장 필드 (`composite`)

| 필드 | 설명 |
|---|---|
| `composition_metrics` | 구성 metric과 가중치 목록 |
| `normalization_method` | `z_score` / `rank_percentile` / `winsorized_z` |
| `aggregation_method` | `weighted_mean` / `median_of_z` / `rank_sum` / 커스텀 |
| `input_direction_handling` | 구성 metric 방향성 일치화 (부호 flip 여부) |
| `version_pinning` | 구성 metric 버전 고정 여부 (Saved Analysis 불변 보장) |

### 2-5. `comparison_group`의 Type별 해석

| metric_type | 의미 | 예시 값 |
|---|---|---|
| `stock_level` | 업종 peers 분포 | `industry → sector → universe` |
| `portfolio_level` | 벤치마크 포트폴리오 | `sp500_benchmark`, `balanced_60_40`, `none` |
| `composite` | 전체 universe 분포 (이미 정규화됨) | `universe` |

---

## 3. 공통 결정 사항 요약

본 Dictionary 작성 과정에서 확정된 cross-cutting 결정:

| # | 결정 | 선택지 | 적용 대상 |
|---|---|---|---|
| 1 | ROIC 세율 | 미국 법정세율 21% 고정 | `roic` 및 파생 지표 |
| 2 | 멀티이어 집계 정책 | Type별 차등 (`count_based` 관대 / `numeric_aggregation` Strict) | 지속성·멀티이어 7개 |
| 3 | 시간 단위 기준 | 거래일 기준 계산, 캘린더 표현 UI (A-3 하이브리드) | 가격·시장 13개 |
| 4 | 가격 소스 | 지표 유형별 차등 (수익률·변동성은 `adjusted`, 레벨형은 `raw`) | 가격·시장 13개 |
| 5 | 스키마 구조 | 공통 코어 + Type별 확장 섹션 | 전체 |
| 6 | 정규화 방법 | Winsorized z-score (2.5% 양측 클리핑) | Multi-Factor 합성 5개 |
| 7 | FMP 소스 전략 | 원칙 기반 혼합 (재무제표 항목 → 직접 계산, 시장 가격/통계 → FMP 값) | 전체 |
| 8 | 금융 기업 처리 | 포함 + 부적합 지표만 Not Applicable (Option B) | 전체 |

---

## 4. 지표 전체 목록

### Type 1 (stock_level) — 39개

| # | metric_id | 카테고리 | 주요 프리셋 |
|---|---|---|---|
| 1 | `roic` | 수익성 | Buffett, Quality Growth, Quality Factor |
| 2 | `roe` | 수익성 | Buffett, Quality Factor |
| 3 | `gross_margin` | 수익성 | Quality Growth, Quality Factor |
| 4 | `fcf_margin` | 수익성 | Buffett, Quality Growth |
| 5 | `eps_growth_yoy` | 성장 | GARP, Quality Growth |
| 6 | `revenue_growth_yoy` | 성장 | GARP, Quality Growth |
| 7 | `pe_ratio` | 밸류에이션 | Buffett, GARP, Contrarian |
| 8 | `pb_ratio` | 밸류에이션 | Buffett, Contrarian |
| 9 | `peg_ratio` | 밸류에이션 | GARP |
| 10 | `ev_to_ebitda` | 밸류에이션 | Buffett, Contrarian |
| 11 | `debt_to_equity` | 재무 건전성 | Buffett, Quality Factor, Low Volatility |
| 12 | `payout_ratio` | 재무 건전성 | Dividend Growth, Shareholder Yield |
| 13 | `dividend_yield` | 배당·주주환원 | Dividend Growth |
| 14 | `shareholder_yield` | 배당·주주환원 | Shareholder Yield |
| 15 | `net_buyback_yield` | 배당·주주환원 | Shareholder Yield |
| 16 | `net_debt_reduction_rate` | 배당·주주환원 | Shareholder Yield |
| 17 | `roic_consistency_5y` | 지속성 | Buffett, Quality Growth |
| 18 | `earnings_consistency_5y` | 지속성 | Buffett |
| 19 | `revenue_growth_consistency_3y` | 지속성 | GARP, Quality Growth |
| 20 | `roe_stability_5y` | 지속성 | Quality Factor, Multi-Factor |
| 21 | `earnings_volatility_5y` | 지속성 | Low Volatility, Quality Factor |
| 22 | `dividend_growth_consistency_5y` | 지속성 | Dividend Growth |
| 23 | `dividend_growth_rate_5y` | 지속성 | Dividend Growth |
| 24 | `beta` | 가격·시장 | Low Volatility, Buffett |
| 25 | `market_cap` | 가격·시장 | Multi-Factor, Concentrated |
| 26 | `return_12m` | 가격·시장 | Price Momentum, Contrarian |
| 27 | `return_6m` | 가격·시장 | Price Momentum, Contrarian |
| 28 | `return_3m` | 가격·시장 | Price Momentum, Contrarian |
| 29 | `relative_strength` | 가격·시장 | Price Momentum, Multi-Factor |
| 30 | `pct_from_52w_high` | 가격·시장 | Price Momentum, Contrarian |
| 31 | `pct_from_52w_low` | 가격·시장 | Contrarian |
| 32 | `volatility_1y` | 가격·시장 | Low Volatility, Multi-Factor |
| 33 | `downside_deviation` | 가격·시장 | Low Volatility, Concentrated |
| 34 | `max_drawdown_1y` | 가격·시장 | Low Volatility, Concentrated |
| 35 | `volume_change_ratio` | 가격·시장 | Contrarian |
| 36 | `buyback_yield` | 가격·시장 | Buffett |
| 37 | `f_score_total` | 체크리스트 스코어 | Piotroski, Contrarian |
| 38 | `ulcer_index` | 가격·시장 | Low Volatility |
| 39 | `up_capture_ratio` | 가격·시장 | Price Momentum |

### Type 2 (portfolio_level) — 13개

| # | metric_id | 주요 프리셋 |
|---|---|---|
| 40 | `portfolio_volatility` | Low Volatility, Concentrated |
| 41 | `portfolio_beta` | Low Volatility, Concentrated |
| 42 | `sharpe_ratio` | Low Volatility, Concentrated |
| 43 | `sortino_ratio` | Low Volatility, Concentrated |
| 44 | `avg_correlation` | Low Volatility, Multi-Factor |
| 45 | `max_risk_contribution` | Low Volatility, Concentrated |
| 46 | `hhi_concentration` | Low Volatility, Concentrated, Multi-Factor |
| 47 | `top3_weight` | Low Volatility, Concentrated |
| 48 | `holding_count` | Concentrated (전 프리셋 Context) |
| 49 | `max_position_weight` | Low Volatility, Concentrated |
| 50 | `sector_hhi` | Low Volatility, Concentrated |
| 51 | `avg_market_cap` | Multi-Factor, Low Volatility |
| 52 | `dividend_yield_portfolio` | Concentrated, Dividend Growth |

### Type 3 (composite) — 5개

| # | metric_id | 구성 |
|---|---|---|
| 53 | `composite_value` | pe_ratio + pb_ratio + ev_to_ebitda |
| 54 | `composite_quality` | roic + gross_margin + debt_to_equity + roe_stability_5y |
| 55 | `composite_momentum` | return_12m + relative_strength + return_6m |
| 56 | `composite_growth` | eps_growth_yoy + revenue_growth_yoy + revenue_growth_consistency_3y |
| 57 | `composite_low_vol` | volatility_1y + downside_deviation + max_drawdown_1y (flip) |

---

## 5. Type 1 (stock_level) 지표 상세

### 5-1. 수익성 카테고리

#### 1. `roic` — Return on Invested Capital

| 필드 | 정의 |
|---|---|
| `display_name` | ROIC |
| `description` | 이 기업이 투입한 돈 대비 얼마나 효율적으로 벌고 있는가. 높을수록 사업 자체가 좋은 구조 |
| `formula` | `operatingIncome × (1 - 0.21) / (totalAssets - totalCurrentLiabilities)` |
| `formula_detail` | 미국 법정세율 21% 고정(MVP). Invested Capital = 총자산 − 유동부채. Phase 2에서 국가별 법정세율 테이블 |
| `source_type` | `calculated` |
| `fmp_endpoint` | `/income-statement?period=annual` + `/balance-sheet-statement?period=annual` |
| `fmp_fields` | `operatingIncome`, `totalAssets`, `totalCurrentLiabilities` |
| `direction` | `higher_is_better` |
| `comparison_group` | industry → sector → universe |
| `refresh_frequency` | 연간 |
| `ttm_method` | operatingIncome: `sum`, totalAssets: `latest`, totalCurrentLiabilities: `latest` |
| `excluded_sectors` | `Financial Services`, `Real Estate` (ROIC 의미 변형) |
| `applicable_presets` | Buffett(Core), Quality Growth(Core), Quality Factor(Core), Multi-Factor(Quality 구성) |

**결측 처리:**

| 상황 | 상태 | 처리 |
|---|---|---|
| operatingIncome 또는 totalAssets 없음 | Missing | null 반환 |
| Invested Capital ≤ 0 (유동부채 > 총자산) | Missing | null 반환 + "자본잠식" 태그 |
| operatingIncome < 0 (영업적자) | 정상 계산 | 음수 ROIC 그대로 저장. 퍼센타일에 포함 |

**엣지 케이스 메모:**
- 금융 기업(은행, 보험)은 totalCurrentLiabilities가 매우 커서 Invested Capital이 음수가 되기 쉬움. 비교군이 같은 industry라 금융끼리 비교하면 문제 없지만, universe fallback 시 왜곡 가능 → `excluded_sectors`로 처리
- Greenblatt의 Magic Formula도 동일한 한계세율 방식 사용

---

#### 2. `roe` — Return on Equity

| 필드 | 정의 |
|---|---|
| `display_name` | 자기자본이익률 (ROE) |
| `description` | 주주가 투자한 자기자본 대비 얼마나 이익을 냈는지. 주주 관점의 수익성. Buffett이 가장 자주 보는 지표, 15%+ 지속이면 우량 |
| `formula` | `netIncome / totalStockholdersEquity` |
| `source_type` | `calculated` |
| `fmp_endpoint` | `/income-statement?period=annual` + `/balance-sheet-statement?period=annual` |
| `fmp_fields` | `netIncome`, `totalStockholdersEquity` |
| `direction` | `higher_is_better` |
| `comparison_group` | industry → sector → universe |
| `refresh_frequency` | 연간 |
| `ttm_method` | netIncome: `sum`, equity: `latest` |
| `excluded_sectors` | 없음 (금융 기업의 ROE는 핵심 지표로 적용 가능) |
| `applicable_presets` | Buffett(Core), Dividend Growth(Supporting), Quality Factor(Supporting), Low Volatility(Context), Contrarian(Context) |

**결측 처리:**

| 상황 | 상태 | 처리 |
|---|---|---|
| netIncome 없음 | Missing | null 반환 |
| totalStockholdersEquity 없음 | Missing | null 반환 |
| equity = 0 | Temporarily Unstable | null 반환 + "자본 제로" 태그 |
| equity < 0 (자본잠식) | Temporarily Unstable | null 반환 + "자본잠식" 태그. 음수 equity로 계산하면 부호가 뒤집혀 왜곡됨 |
| netIncome < 0 + equity > 0 (단순 적자) | 정상 계산 | 음수 ROE 그대로 저장. 퍼센타일에 포함 |

**엣지 케이스 메모:**
- equity가 음수인 기업 예시: 스타벅스(SBUX)는 자사주매입 누적으로 equity가 음수. 사업은 건전하지만 회계상 자본잠식. 이런 기업에서 ROE를 null로 처리하면 Buffett 프리셋에서 중요한 Core 지표가 빠지는 문제가 있으나, 음수 equity 계산은 더 큰 왜곡을 초래. null + 태그가 가장 안전

---

#### 3. `gross_margin` — 매출총이익률

| 필드 | 정의 |
|---|---|
| `display_name` | 매출총이익률 |
| `description` | 매출에서 원가를 빼고 남는 비율. 기업의 가격결정력과 원가 경쟁력을 보여줌 |
| `formula` | `grossProfit / revenue` |
| `source_type` | `calculated` |
| `fmp_endpoint` | `/income-statement?period=annual` |
| `fmp_fields` | `grossProfit`, `revenue` |
| `direction` | `higher_is_better` |
| `comparison_group` | industry → sector (업종별 편차 매우 큼) |
| `refresh_frequency` | 연간 |
| `ttm_method` | grossProfit: `sum`, revenue: `sum` |
| `excluded_sectors` | `Financial Services` (COGS 개념 없음. grossProfit 미보고) |
| `applicable_presets` | Quality Factor(Core), GARP(Supporting), Quality Growth(Supporting), Multi-Factor(Quality 구성) |

**결측 처리:**

| 상황 | 상태 | 처리 |
|---|---|---|
| grossProfit 없음 | Not Applicable 또는 Missing | 금융 기업 → Not Applicable, 일반 기업 → Missing |
| revenue 없음 | Missing | null 반환 |
| revenue = 0 | Temporarily Unstable | null 반환 |
| grossProfit < 0 | 정상 계산 | 음수 마진 저장. 원가가 매출을 초과하는 사업 (극히 드묾) |

**엣지 케이스 메모:**
- 금융 기업(은행, 보험, 증권)은 매출원가(COGS) 개념이 없어서 FMP에서 grossProfit을 보고하지 않거나, revenue 자체를 이자수익으로 보고함 → `excluded_sectors`로 처리

---

#### 4. `fcf_margin` — 잉여현금흐름 마진

| 필드 | 정의 |
|---|---|
| `display_name` | 잉여현금흐름 마진 (FCF Margin) |
| `description` | 매출 중 실제로 자유롭게 쓸 수 있는 현금이 얼마나 남는지. 이익의 질을 보여주는 현금 기반 수익성 |
| `formula` | `freeCashFlow / revenue` |
| `formula_detail` | freeCashFlow = operatingCashFlow - capitalExpenditure. FMP의 cash-flow-statement에서 freeCashFlow 직접 제공되나, "직접 계산" 원칙에 따라 operatingCashFlow - capitalExpenditure로 직접 계산이 일관적 |
| `source_type` | `calculated` |
| `fmp_endpoint` | `/cash-flow-statement?period=annual` + `/income-statement?period=annual` |
| `fmp_fields` | `freeCashFlow` (또는 `operatingCashFlow`, `capitalExpenditure`), `revenue` |
| `direction` | `higher_is_better` |
| `comparison_group` | industry → sector → universe |
| `refresh_frequency` | 연간 |
| `ttm_method` | freeCashFlow: `sum`, revenue: `sum` |
| `excluded_sectors` | `Financial Services` (FCF 개념 부적합 — 설비 투자 기반 사업이 아님) |
| `applicable_presets` | Buffett(Supporting), Shareholder Yield(Supporting), Quality Factor(Supporting) |

**결측 처리:**

| 상황 | 상태 | 처리 |
|---|---|---|
| freeCashFlow 없음 | Missing | null 반환 |
| revenue 없음 | Missing | null 반환 |
| freeCashFlow < 0 (음수 FCF) | 정상 계산 | 음수 마진 저장 + 퍼센타일 포함. 성장기 기업(CAPEX 과다)에서 흔함 |
| revenue = 0 | Temporarily Unstable | null 반환 |

**엣지 케이스 메모:**
- FCF가 음수인 기업이 많음(특히 성장주). 이건 "나쁘다"가 아니라 "투자 중"일 수 있어서, 음수를 정상 포함하되 진단 카드에서 "이익은 나지만 현금은 설비 투자에 쓰이고 있다"로 맥락 제공

---

### 5-2. 성장 카테고리

#### 5. `eps_growth_yoy` — EPS 성장률(전년 대비)

| 필드 | 정의 |
|---|---|
| `display_name` | EPS 성장률 (YoY) |
| `description` | 주당 이익이 얼마나 빠르게 늘고 있는가. GARP은 20~50% 성장을 적정 범위로 봄 |
| `formula` | `(EPS_current - EPS_prev) / abs(EPS_prev)` |
| `formula_detail` | abs() 사용하여 음수→양수 전환(흑자전환)도 양의 성장률로 표시. `epsdiluted` 사용(희석 주식 반영) |
| `source_type` | `calculated` |
| `fmp_endpoint` | `/income-statement?period=annual` (2년치) |
| `fmp_fields` | `epsdiluted` (또는 `eps`, fallback) |
| `direction` | `higher_is_better` |
| `comparison_group` | industry → sector → universe |
| `refresh_frequency` | 연간 |
| `ttm_method` | EPS: 연간 확정값 2시점 비교 |
| `applicable_presets` | GARP(Core), Quality Growth(Supporting) |

**결측 처리:**

| 상황 | 상태 | 처리 |
|---|---|---|
| EPS_prev = 0 | Missing | null 반환. 분모 0으로 성장률 정의 불가 |
| EPS_prev, EPS_current 중 없음 | Missing | null 반환 |
| EPS_prev < 0 → EPS_current > 0 (흑자전환) | 정상 계산 | abs() 사용으로 양의 성장률 반환 |
| EPS_prev > 0 → EPS_current < 0 (적자전환) | 정상 계산 | 큰 음수 성장률 반환 |

---

#### 6. `revenue_growth_yoy` — 매출 성장률(전년 대비)

| 필드 | 정의 |
|---|---|
| `display_name` | 매출 성장률 (YoY) |
| `description` | EPS 성장이 매출 성장에 기반하는가. 매출 없이 이익만 느는 건 비용 절감이라 지속 불가능 |
| `formula` | `(revenue_current - revenue_prev) / revenue_prev` |
| `source_type` | `calculated` |
| `fmp_endpoint` | `/income-statement?period=annual` (2년치) |
| `fmp_fields` | `revenue` |
| `direction` | `higher_is_better` |
| `comparison_group` | industry → sector → universe |
| `refresh_frequency` | 연간 |
| `ttm_method` | revenue: 연간 확정값 2시점 비교 |
| `applicable_presets` | GARP(Core), Quality Growth(Core) |

**결측 처리:**

| 상황 | 상태 | 처리 |
|---|---|---|
| revenue_prev = 0 | Missing | null 반환 |
| revenue 중 없음 | Missing | null 반환 |
| revenue_prev < 0 (음수 매출, 극히 드묾) | Temporarily Unstable | null 반환 |

---

### 5-3. 밸류에이션 카테고리

#### 7. `pe_ratio` — P/E Ratio

| 필드 | 정의 |
|---|---|
| `display_name` | P/E |
| `description` | 이 기업의 1년 이익 대비 현재 주가가 얼마나 비싼가. 좋은 기업이라도 너무 비싸면 수익이 제한됨 |
| `formula` | `price / (netIncome / weightedAverageShsOut)` |
| `formula_detail` | 분모(EPS)를 직접 계산. "직접 계산" 원칙에 따라 Price는 FMP 시세, EPS는 재무제표에서 직접 |
| `source_type` | `calculated` |
| `fmp_endpoint` | `/quote` + `/income-statement?period=annual` |
| `fmp_fields` | `price`, `netIncome`, `weightedAverageShsOut` |
| `direction` | `lower_is_better` |
| `comparison_group` | industry → sector → universe |
| `refresh_frequency` | 가격 EOD, EPS 연간 |
| `ttm_method` | price: 실시간, netIncome: `sum`, shares: `latest` |
| `display_condition` | 흑자 기업만 (EPS ≤ 0 시 N/A) |
| `applicable_presets` | Buffett(Supporting), GARP(Core), Piotroski(Context), Contrarian(Supporting), Multi-Factor(Value 구성) |

**결측 처리:**

| 상황 | 상태 | 처리 |
|---|---|---|
| price, netIncome, shares 중 없음 | Missing | null 반환 |
| EPS ≤ 0 (적자 기업) | Not Applicable | null 반환 + "적자 기업 P/E 산출 불가" 태그 |
| EPS가 0에 극도로 가까움 (0 < EPS < 0.01) | Temporarily Unstable | null 반환 + "EPS 극소" 태그. P/E가 수천~수만이 나와서 퍼센타일 왜곡 |

**엣지 케이스 메모:**
- 적자 기업의 밸류에이션은 P/E 대신 P/S(매출 대비)나 EV/Revenue로 봐야 하지만, MVP에서는 N/A + 태그 처리. Phase 2에서 대체 지표 검토
- 시장에서 가장 많이 쓰는 지표라 사용자 기대치가 높음. "P/E가 왜 없나요?"에 대한 명확한 답변 필요

---

#### 8. `pb_ratio` — P/B Ratio

| 필드 | 정의 |
|---|---|
| `display_name` | 주가순자산비율 (P/B) |
| `description` | 순자산 대비 주가가 얼마인가. 1 이하면 자산가치보다 싸게 거래되는 것 |
| `formula` | `price / (totalStockholdersEquity / weightedAverageShsOut)` |
| `source_type` | `calculated` |
| `fmp_endpoint` | `/quote` + `/balance-sheet-statement?period=annual` + `/income-statement?period=annual` |
| `fmp_fields` | `price`, `totalStockholdersEquity`, `weightedAverageShsOut` |
| `direction` | `lower_is_better` |
| `comparison_group` | industry → sector → universe |
| `refresh_frequency` | 가격 EOD, equity 연간 |
| `ttm_method` | price: 실시간, equity: `latest`, shares: `latest` |
| `excluded_sectors` | 없음 |
| `applicable_presets` | Piotroski(Context), Contrarian(Supporting), Buffett(Context), Multi-Factor(Value 구성) |

**결측 처리:**

| 상황 | 상태 | 처리 |
|---|---|---|
| price, equity, shares 중 없음 | Missing | null 반환 |
| equity ≤ 0 (자본잠식) | Not Applicable | null 반환 + "자본잠식 P/B 산출 불가" 태그. ROE와 동일한 이유 |
| Book Value per Share가 극소 | Temporarily Unstable | P/B가 수백~수천이 나옴. null 반환 |

---

#### 9. `peg_ratio` — PEG Ratio

| 필드 | 정의 |
|---|---|
| `display_name` | PEG 비율 |
| `description` | 성장 속도 대비 주가가 적정한가. 1 이하면 성장에 비해 싸고, 2 이상이면 성장을 이미 반영한 가격 |
| `formula` | `pe_ratio / (eps_growth_yoy × 100)` |
| `formula_detail` | eps_growth_yoy를 백분율로 변환 후 사용. 성장률 25%면 PEG = P/E ÷ 25. Peter Lynch의 원래 정의는 "향후 3~5년 예상 성장률"이지만, MVP는 과거 1년 실현 성장률 사용 |
| `source_type` | `calculated` (pe_ratio와 eps_growth_yoy의 조합) |
| `fmp_endpoint` | pe_ratio + eps_growth_yoy와 동일 |
| `fmp_fields` | `price`, `netIncome`, `weightedAverageShsOut` (2년치) |
| `direction` | `lower_is_better` |
| `comparison_group` | industry → sector → universe |
| `refresh_frequency` | 가격 EOD + EPS 연간 |
| `ttm_method` | pe_ratio, eps_growth_yoy 각각의 ttm_method 따름 |
| `excluded_sectors` | 없음 |
| `display_condition` | 성장률 양수 + PE 양수만 |
| `applicable_presets` | GARP(Core) |

**결측 처리:**

| 상황 | 상태 | 처리 |
|---|---|---|
| pe_ratio가 null | — | null 반환 (pe_ratio의 결측 사유 상속) |
| eps_growth_yoy가 null | — | null 반환 |
| eps_growth_yoy ≤ 0 (역성장 또는 적자) | Not Applicable | null 반환 + "역성장 기업 PEG 산출 불가" 태그 |
| eps_growth_yoy가 극소 (0~2%) | Temporarily Unstable | PEG가 수십~수백이 되어 의미 없음. null 반환 + 태그 |

**엣지 케이스 메모:**
- PEG는 의존 지표가 2개(pe_ratio, eps_growth_yoy)라서 양쪽 모두 유효해야 계산 가능. 적자 기업이나 역성장 기업은 자동으로 null
- Phase 2 검토: 분모를 과거 1년 대신 과거 5년 CAGR로 대체하는 옵션

---

#### 10. `ev_to_ebitda` — EV/EBITDA

| 필드 | 정의 |
|---|---|
| `display_name` | EV/EBITDA |
| `description` | 기업가치(부채 포함) 대비 영업이익+감가상각. 자본구조에 중립적인 밸류에이션 척도 |
| `formula` | `enterpriseValue / ebitda` |
| `formula_detail` | enterpriseValue = marketCap + totalDebt - cashAndCashEquivalents. ebitda = operatingIncome + depreciationAndAmortization |
| `source_type` | `calculated` |
| `fmp_endpoint` | `/quote` + `/balance-sheet-statement?period=annual` + `/income-statement?period=annual` + `/cash-flow-statement?period=annual` |
| `fmp_fields` | `marketCap`, `totalDebt`, `cashAndCashEquivalents`, `operatingIncome`, `depreciationAndAmortization` |
| `direction` | `lower_is_better` |
| `comparison_group` | industry → sector → universe |
| `refresh_frequency` | marketCap은 EOD, 나머지 연간 |
| `ttm_method` | EV 구성요소: `latest`, EBITDA 구성요소: operatingIncome `sum`, D&A `sum` |
| `excluded_sectors` | `Financial Services` (EV 개념이 금융 기업에 부적합 — 부채가 사업 원재료) |
| `applicable_presets` | Buffett(Supporting), Contrarian(Supporting), Multi-Factor(Value 구성) |

**결측 처리:**

| 상황 | 상태 | 처리 |
|---|---|---|
| EV 구성요소 중 없음 | Missing | null 반환 |
| EBITDA 구성요소 없음 | Missing | null 반환 |
| EBITDA ≤ 0 (영업적자 + 감가상각으로도 양수 안 됨) | Not Applicable | null 반환 + "EBITDA 음수" 태그 |
| cashAndCashEquivalents 없음 | Missing | totalDebt만으로 EV 근사 가능하나, 정확도 저하. null 반환이 안전 |

---

### 5-4. 재무 건전성 카테고리

#### 11. `debt_to_equity`

| 필드 | 정의 |
|---|---|
| `display_name` | 부채비율 (D/E) |
| `description` | 자기자본 대비 총부채 |
| `formula` | `Total Debt / Total Stockholders Equity` |
| `source_type` | `calculated` |
| `fmp_endpoint` | `/balance-sheet-statement` (최신) |
| `fmp_fields` | `totalDebt`, `totalStockholdersEquity` |
| `direction` | `lower_is_better` |
| `comparison_group` | industry → sector |
| `refresh_frequency` | 분기 |
| `excluded_sectors` | `Financial Services` (부채가 원재료) |
| `applicable_presets` | Buffett(Supporting), Quality Factor(Supporting), Low Volatility(Supporting), Multi-Factor(Quality 구성, 부호 flip) |

**결측 처리**: Equity ≤ 0 → Missing (자본잠식).

---

#### 12. `payout_ratio` — 배당성향

| 필드 | 정의 |
|---|---|
| `display_name` | 배당성향 |
| `description` | 순이익 중 배당으로 지급된 비율 |
| `formula` | `Dividends Paid / Net Income` (TTM, 절댓값) |
| `source_type` | `calculated` |
| `fmp_endpoint` | `/cash-flow-statement-ttm`, `/income-statement-ttm` |
| `fmp_fields` | `dividendsPaid` (abs), `netIncome` |
| `direction` | `정보 제공` (프리셋별 해석) |
| `comparison_group` | industry → sector |
| `refresh_frequency` | 분기 |
| `display_condition` | 배당 지급 기업만 |
| `applicable_presets` | Dividend Growth(Supporting), Shareholder Yield(Context) |

**결측 처리**: 무배당 → Not Applicable. 순이익 ≤ 0 → Temporarily Unstable (비율 발산 가능).

**엣지 케이스**: 80% 초과 시 "배당 지속 가능성 경계", 100% 초과 시 "이익 대비 과도한 배당"으로 진단 카드 트리거 후보.

---

### 5-5. 배당·주주환원 카테고리

#### 13. `dividend_yield` — 배당수익률

| 필드 | 정의 |
|---|---|
| `display_name` | 배당수익률 |
| `description` | 현재 주가 대비 연간 배당 |
| `formula` | `Annual Dividend / Current Price` |
| `source_type` | `fmp_native` |
| `fmp_endpoint` | `/quote` 또는 `/ratios-ttm` |
| `fmp_fields` | `dividendYieldTTM` |
| `direction` | `higher_is_better` |
| `comparison_group` | industry → sector → universe |
| `refresh_frequency` | EOD |
| `display_condition` | 배당 지급 기업만 |
| `applicable_presets` | Dividend Growth(Supporting), Buffett(Context) |

---

#### 14. `shareholder_yield` — 주주수익률

| 필드 | 정의 |
|---|---|
| `display_name` | 주주수익률 |
| `description` | 배당 + 자사주매입 + 순부채감소를 시가총액으로 정규화한 총 주주환원율 |
| `formula` | `dividend_yield + net_buyback_yield + net_debt_reduction_rate` |
| `formula_detail` | 3개 구성요소 모두 시가총액 대비 비율로 정규화되어 있어 단순 합산 가능 |
| `source_type` | `calculated` (합성) |
| `direction` | `higher_is_better` |
| `comparison_group` | industry → sector → universe |
| `refresh_frequency` | 분기 (구성 요소 중 가장 긴 주기) |
| `excluded_sectors` | `Financial Services` (순부채 개념 반대) |
| `applicable_presets` | Shareholder Yield(Core) |

**결측 처리**: 3개 구성요소 중 1개 Missing → 남은 것만 합산 + 플래그. 2개 이상 Missing → Missing.

---

#### 15. `net_buyback_yield`

| 필드 | 정의 |
|---|---|
| `display_name` | 순자사주매입률 |
| `description` | 자사주매입액에서 신주발행액을 차감한 순액을 시가총액으로 정규화 |
| `formula` | `(commonStockRepurchased - commonStockIssued) / marketCap` |
| `formula_detail` | CFS에서 두 항목의 차이. 시가총액은 연말 기준 |
| `source_type` | `calculated` |
| `fmp_endpoint` | `/cash-flow-statement?period=annual` + `/historical-market-capitalization` |
| `fmp_fields` | `commonStockRepurchased`, `commonStockIssued`, `marketCap` |
| `direction` | `higher_is_better` |
| `comparison_group` | industry → sector → universe |
| `refresh_frequency` | 연간 |
| `applicable_presets` | Shareholder Yield(Core) |

**엣지 케이스**: 스톡옵션 희석 반영. 분할 조정 값 사용.

---

#### 16. `net_debt_reduction_rate`

| 필드 | 정의 |
|---|---|
| `display_name` | 순부채감소율 |
| `description` | 전년 대비 순부채 감소분을 시가총액으로 정규화. 간접적 주주환원 |
| `formula` | `(netDebt_prev - netDebt_curr) / marketCap_prev` |
| `formula_detail` | netDebt = totalDebt − cashAndCashEquivalents |
| `source_type` | `calculated` |
| `fmp_endpoint` | `/balance-sheet-statement?period=annual` (2년치) + `/historical-market-capitalization` |
| `fmp_fields` | `totalDebt`, `cashAndCashEquivalents`, `marketCap` |
| `direction` | `higher_is_better` |
| `comparison_group` | industry → sector → universe |
| `refresh_frequency` | 연간 |
| `excluded_sectors` | `Financial Services` |
| `applicable_presets` | Shareholder Yield(Core) |

**엣지 케이스**: netDebt 양↔음 전환은 정상 계산. 상장 1년 미만은 Insufficient History.

---

### 5-6. 지속성·멀티이어 카테고리

> **공통 적용**: `aggregation_type` (count_based / numeric_aggregation), `min_years` 정책 적용 (§3, 결정 #2)

#### 17. `roic_consistency_5y`

| 필드 | 정의 |
|---|---|
| `display_name` | ROIC 5년 지속성 |
| `description` | 최근 5년 중 ROIC 15%+ 달성 연수의 비율 |
| `formula` | `count(annual_roic >= 0.15) / 가용_연수` |
| `aggregation_type` | `count_based` |
| `min_years` | 3 |
| `direction` | `higher_is_better` |
| `excluded_sectors` | `Financial Services`, `Real Estate` |
| `applicable_presets` | Buffett(Core), Quality Growth(Supporting) |

---

#### 18. `earnings_consistency_5y`

| 필드 | 정의 |
|---|---|
| `display_name` | 이익 일관성 (5년) |
| `formula` | `count(EPS_t > EPS_{t-1}) / 가용_비교쌍` |
| `aggregation_type` | `count_based` |
| `min_years` | 3 (= 비교쌍 2개) |
| `direction` | `higher_is_better` |
| `applicable_presets` | Buffett(Core) |

---

#### 19. `revenue_growth_consistency_3y`

| 필드 | 정의 |
|---|---|
| `display_name` | 매출 성장 일관성 (3년) |
| `formula` | `count(revenue_t > revenue_{t-1}) / 가용_비교쌍` |
| `aggregation_type` | `count_based` |
| `min_years` | 2 (예외 — 단일 비교쌍도 의미 있음) |
| `direction` | `higher_is_better` |
| `applicable_presets` | GARP(Supporting), Quality Growth(Core) |

---

#### 20. `roe_stability_5y`

| 필드 | 정의 |
|---|---|
| `display_name` | ROE 안정성 (5년) |
| `formula` | `std(ROE_Y1..Y5)` (표본 표준편차) |
| `aggregation_type` | `numeric_aggregation` |
| `min_years` | 5 (Strict) |
| `direction` | `lower_is_better` |
| `applicable_presets` | Quality Factor(Core), Multi-Factor(Quality 구성, 부호 flip) |

---

#### 21. `earnings_volatility_5y`

| 필드 | 정의 |
|---|---|
| `display_name` | 이익 변동성 (5년) |
| `formula` | `std(EPS_5y) / abs(mean(EPS_5y))` (변동계수 CV) |
| `aggregation_type` | `numeric_aggregation` |
| `min_years` | 5 (Strict) |
| `direction` | `lower_is_better` |
| `applicable_presets` | Low Volatility(Supporting), Quality Factor(Supporting) |

**엣지 케이스**: |mean(EPS)| < 0.01 → Temporarily Unstable (CV 발산).

---

#### 22. `dividend_growth_consistency_5y`

| 필드 | 정의 |
|---|---|
| `display_name` | 배당 성장 일관성 (5년) |
| `formula` | `count(dividend_t > dividend_{t-1}) / 가용_비교쌍` |
| `aggregation_type` | `count_based` |
| `min_years` | 3 |
| `direction` | `higher_is_better` |
| `display_condition` | 5년 풀 배당 지급 기업만 |
| `applicable_presets` | Dividend Growth(Core) |

---

#### 23. `dividend_growth_rate_5y`

| 필드 | 정의 |
|---|---|
| `display_name` | 배당 성장률 (5년 CAGR) |
| `formula` | `(dividend_Y5 / dividend_Y1)^(1/4) - 1` |
| `aggregation_type` | `numeric_aggregation` |
| `min_years` | 5 (Strict) |
| `direction` | `higher_is_better` |
| `display_condition` | 5년 풀 배당 지급 기업만 |
| `applicable_presets` | Dividend Growth(Core) |

**엣지 케이스**: 시작 연도 배당 = 0 → Not Applicable. CAGR > 100% → Temporarily Unstable.

---

### 5-7. 가격·시장 카테고리

> **공통 적용**: `window_trading_days` (거래일 기준, §3 결정 #3), `price_source` (§3 결정 #4)

#### 24. `beta`

| 필드 | 정의 |
|---|---|
| `display_name` | 베타 |
| `formula` | `Cov(R_stock, R_market) / Var(R_market)` (FMP 5년 월간) |
| `source_type` | `fmp_native` |
| `fmp_fields` | `beta` |
| `direction` | `정보 제공` |
| `refresh_frequency` | 월 1회 |
| `applicable_presets` | Low Volatility(Core), Buffett(Context), Quality Factor(Supporting) |

---

#### 25. `market_cap`

| 필드 | 정의 |
|---|---|
| `display_name` | 시가총액 |
| `source_type` | `fmp_native` |
| `fmp_fields` | `mktCap` |
| `direction` | `정보 제공` |
| `comparison_group` | universe |
| `refresh_frequency` | EOD |
| `price_source` | raw |
| `applicable_presets` | Multi-Factor(Size 입력), Concentrated(Context), Low Volatility(Context) |

---

#### 26. `return_12m`

| 필드 | 정의 |
|---|---|
| `display_name` | 12개월 수익률 |
| `formula` | `(adjClose_today / adjClose_t-252) - 1` |
| `window_trading_days` | 252 |
| `price_source` | adjusted |
| `direction` | `higher_is_better` (Momentum) / `lower_is_better` (Contrarian) |
| `refresh_frequency` | EOD |
| `applicable_presets` | Price Momentum(Core), Multi-Factor(Momentum 구성), Contrarian(Core, flip) |

---

#### 27. `return_6m`

| 필드 | 정의 |
|---|---|
| `display_name` | 6개월 수익률 |
| `formula` | `(adjClose_today / adjClose_t-126) - 1` |
| `window_trading_days` | 126 |
| `price_source` | adjusted |
| `direction` | `higher_is_better` / 프리셋별 |
| `applicable_presets` | Price Momentum(Supporting), Contrarian(Supporting), Multi-Factor(Momentum 구성) |

---

#### 28. `return_3m`

| 필드 | 정의 |
|---|---|
| `display_name` | 3개월 수익률 |
| `formula` | `(adjClose_today / adjClose_t-63) - 1` |
| `window_trading_days` | 63 |
| `price_source` | adjusted |
| `direction` | `higher_is_better` / 프리셋별 |
| `applicable_presets` | Price Momentum(Supporting), Contrarian(Core) |

---

#### 29. `relative_strength`

| 필드 | 정의 |
|---|---|
| `display_name` | 상대강도 |
| `formula` | `return_12m_stock - return_12m_sp500` |
| `window_trading_days` | 252 |
| `price_source` | adjusted |
| `direction` | `higher_is_better` / 프리셋별 |
| `comparison_group` | universe |
| `applicable_presets` | Price Momentum(Core), Multi-Factor(Momentum 구성) |

---

#### 30. `pct_from_52w_high`

| 필드 | 정의 |
|---|---|
| `display_name` | 52주 고가 대비 현재가 |
| `formula` | `(close_today - max(close_252d)) / max(close_252d)` |
| `window_trading_days` | 252 |
| `price_source` | raw |
| `direction` | `higher_is_better` (Momentum) / `lower_is_better` (Contrarian) |
| `applicable_presets` | Price Momentum(Supporting), Contrarian(Core) |

---

#### 31. `pct_from_52w_low`

| 필드 | 정의 |
|---|---|
| `display_name` | 52주 저가 대비 현재가 |
| `formula` | `(close_today - min(close_252d)) / min(close_252d)` |
| `window_trading_days` | 252 |
| `price_source` | raw |
| `direction` | `정보 제공` |
| `applicable_presets` | Contrarian(Supporting) |

---

#### 32. `volatility_1y`

| 필드 | 정의 |
|---|---|
| `display_name` | 연간 변동성 |
| `formula` | `std(daily_returns) × √252` |
| `window_trading_days` | 252 (+1일 수익률 계산용) |
| `price_source` | adjusted |
| `direction` | `lower_is_better` |
| `applicable_presets` | Low Volatility(Core), Multi-Factor(Quality 구성) |

---

#### 33. `downside_deviation`

| 필드 | 정의 |
|---|---|
| `display_name` | 하방 변동성 |
| `formula` | `√(mean(min(r_t, 0)²)) × √252` |
| `window_trading_days` | 252 |
| `price_source` | adjusted |
| `direction` | `lower_is_better` |
| `applicable_presets` | Low Volatility(Supporting), Concentrated(Supporting) |

---

#### 34. `max_drawdown_1y`

| 필드 | 정의 |
|---|---|
| `display_name` | 최대 낙폭 (1년) |
| `formula` | `min((adjClose_t / running_max(adjClose_t)) - 1)` for 252-day window |
| `window_trading_days` | 252 |
| `price_source` | adjusted |
| `direction` | `higher_is_better` (0에 가까울수록 좋음, 항상 ≤ 0) |
| `applicable_presets` | Low Volatility(Core), Concentrated(Context) |

---

#### 35. `volume_change_ratio`

| 필드 | 정의 |
|---|---|
| `display_name` | 거래량 변화 비율 |
| `formula` | `mean(volume_20d) / mean(volume_60d)` |
| `window_trading_days` | 60 + 20 |
| `price_source` | N/A (거래량) |
| `direction` | `정보 제공` |
| `applicable_presets` | Contrarian(Supporting) |

---

#### 36. `buyback_yield`

| 필드 | 정의 |
|---|---|
| `display_name` | 자사주매입 수익률 |
| `formula` | `(sharesOutstanding_prev - sharesOutstanding_curr) / sharesOutstanding_prev` |
| `formula_detail` | `weightedAverageShsOutDil` 사용 (diluted 기준) |
| `source_type` | `calculated` |
| `fmp_endpoint` | `/income-statement?period=annual` (2년치) |
| `direction` | `higher_is_better` |
| `refresh_frequency` | 연간 |
| `applicable_presets` | Buffett(Supporting) |

---

#### 37. `f_score_total` — Piotroski F-Score

| 필드 | 정의 |
|---|---|
| `display_name` | Piotroski F-Score |
| `description` | Joseph Piotroski가 제안한 9개 재무 건전성 체크리스트의 합산 점수(0~9). 수익성 4개 + 레버리지/유동성/자본조달 3개 + 운영 효율성 2개. |
| `formula` | `sum(9개 서브 bool 판정)` |
| `formula_detail` | 각 서브 항목이 통과(True)=1, 미달(False)=0. 9개 중 통과 항목 합산. 결측 서브는 0점 처리(보수적 해석). 서브 상세는 아래 표 참조. |
| `source_type` | `composite` |
| `fmp_endpoint` | `/income-statement?period=annual`, `/balance-sheet-statement?period=annual`, `/cash-flow-statement?period=annual` (2년치, Y-0과 Y-1 비교 필요) |
| `direction` | `higher_is_better` |
| `metric_type` | `stock_level` |
| `aggregation_type` | `composite_checklist` |
| `comparison_group` | `universe` (퍼센타일 산출 시 업종 무관) |
| `fallback_rule` | universe only (0~9 이산값은 업종별 분포 차이가 작음) |
| `refresh_frequency` | 연간 (연차 재무제표 확정 시점) |
| `ttm_method` | `latest_annual` (TTM 적용 불가 — 연차 재무제표 기반 체크리스트) |
| `excluded_sectors` | `Financial Services`, `Real Estate` (일부 서브 항목의 해석이 변형됨 — MVP에서는 F-Score 자체를 N/A 처리) |
| `applicable_presets` | Piotroski F-Score(Core), Contrarian(Core) |

**퍼센타일 주의**: 0~9의 이산값이라 전통적 winsorized z-score가 아닌 **직접 빈도 분포 매핑**을 사용. 업계 관행은 F ≥ 7 강세, F ≤ 3 약세, F = 8~9 최상위 약 15%.

**서브 9개 항목 내부 스펙**

각 서브는 독립 `metric_id`가 아닌 **내부 계산 세부** (04-18 결정 "f_score_total + details JSON"). `StockMetricValue.extra_data` JSON에 개별 결과 보존.

| # | sub_id | 카테고리 | 판정 조건 | FMP 필드 (원본) | 결측 처리 |
|---|---|---|---|---|---|
| 1 | `roa_positive` | 수익성 | `netIncome > 0` | `netIncome` | 필드 결측 시 0점 |
| 2 | `cfo_positive` | 수익성 | `operatingCashFlow > 0` | `operatingCashFlow` | 필드 결측 시 0점 |
| 3 | `roa_change_positive` | 수익성 | `ROA_t > ROA_{t-1}` where `ROA = netIncome / totalAssets (avg)` | `netIncome`, `totalAssets` (2년치) | 2년 데이터 부족 시 0점 |
| 4 | `accrual_quality` | 수익성 | `operatingCashFlow > netIncome` (당해 연도) | `operatingCashFlow`, `netIncome` | 필드 결측 시 0점 |
| 5 | `leverage_decrease` | 레버리지 | `(longTermDebt_t / totalAssets_t) < (longTermDebt_{t-1} / totalAssets_{t-1})` | `longTermDebt`, `totalAssets` (2년치) | 2년 데이터 부족 시 0점 |
| 6 | `liquidity_increase` | 유동성 | `currentRatio_t > currentRatio_{t-1}` where `currentRatio = totalCurrentAssets / totalCurrentLiabilities` | `totalCurrentAssets`, `totalCurrentLiabilities` (2년치) | 2년 데이터 부족 시 0점 |
| 7 | `no_share_issuance` | 자본조달 | `weightedAverageShsOutDil_t <= weightedAverageShsOutDil_{t-1}` (신주발행 없음) | `weightedAverageShsOutDil` (2년치) | 2년 데이터 부족 시 0점 |
| 8 | `margin_increase` | 운영 효율성 | `grossProfitMargin_t > grossProfitMargin_{t-1}` where `grossProfitMargin = grossProfit / revenue` | `grossProfit`, `revenue` (2년치) | 2년 데이터 부족 시 0점 |
| 9 | `asset_turnover_increase` | 운영 효율성 | `assetTurnover_t > assetTurnover_{t-1}` where `assetTurnover = revenue / totalAssets (avg)` | `revenue`, `totalAssets` (2년치) | 2년 데이터 부족 시 0점 |

**결측 처리 원칙**

| 상황 | 상태 | 처리 |
|---|---|---|
| 당해 연도 1년치만 존재 (IPO 직후 등) | `Insufficient History` | 서브 1·2·4만 판정 가능 → 최대 3점. 나머지 6개는 0점 처리. UI에 "제한적 데이터" 태그 |
| 2년치 완전 | 정상 | 9개 서브 전부 판정 가능 |
| 필수 필드 결측 (예: operatingCashFlow null) | 해당 서브만 0점 | 전체는 남은 서브로 계산. extra_data에 `missing_subs` 리스트 기록 |
| 금융/부동산 업종 | `Not Applicable` | F-Score 자체를 N/A. 관련 프리셋에서 제외 |

**엣지 케이스 메모**
- 당해 순이익이 음수여도 F-Score 계산 자체는 수행 (#1이 0점이 될 뿐). F-Score는 저평가·턴어라운드 진단용으로 설계된 지표라서 음수 이익 케이스도 의미가 있음.
- `weightedAverageShsOutDil` 대신 자사주 매입을 차감한 순 변화를 쓰지 않음 — Piotroski 원저에서 "신주 발행 여부"만 판정. 자사주 매입 효과는 별도 `net_buyback_yield`·`buyback_yield`에서 다룸.

---

#### 38. `ulcer_index`

| 필드 | 정의 |
|---|---|
| `display_name` | Ulcer Index |
| `description` | 가격 하락 기간의 "깊이"와 "지속 시간"을 통합한 하방 리스크 지표. Martin & McCann이 1987년 제안. 투자자가 느끼는 불편함(ulcer)을 정량화. |
| `formula` | `sqrt(mean(drawdown_i^2))` where `drawdown_i = (price_i - max_price_up_to_i) / max_price_up_to_i * 100` |
| `formula_detail` | 각 일자의 "그동안 최고가 대비 하락률(%)"을 계산하고, 이 값들의 제곱평균제곱근(RMS). 표준편차와 달리 **하방만** 반영하고, 변동성 크기뿐 아니라 **하락 지속 시간**도 벌칙화. 값이 클수록 고통스러운 하락. |
| `source_type` | `calculated` |
| `fmp_endpoint` | `/historical-price-full/{symbol}` (1년치, 252 거래일) |
| `fmp_fields` | `adjClose` (adjusted close 사용) |
| `direction` | `lower_is_better` |
| `metric_type` | `stock_level` |
| `window_trading_days` | 252 |
| `price_source` | adjusted |
| `comparison_group` | `industry` |
| `fallback_rule` | industry → sector → universe |
| `refresh_frequency` | EOD (일간) |
| `ttm_method` | N/A (rolling window 기반) |
| `excluded_sectors` | [] |
| `applicable_presets` | Low Volatility(Supporting) |

**결측 처리**

| 상황 | 상태 | 처리 |
|---|---|---|
| 상장 252일 미만 | `Insufficient History` | 가용 기간으로 계산 + "제한적 데이터" 태그. 최소 126거래일(6개월) 필요 |
| 상장 126일 미만 | `Missing` | null 반환 |
| 가격 데이터 공백 | 보간 후 계산 | FMP의 거래 중단 일자 제외 (주말·공휴일 자동 처리됨) |

---

#### 39. `up_capture_ratio`

| 필드 | 정의 |
|---|---|
| `display_name` | 상승 포착 비율 |
| `description` | 벤치마크가 상승한 기간 동안 종목이 얼마나 잘 따라가는지 측정. 100%는 정확히 동일, 120%는 벤치마크 대비 20% 초과 수익, 80%는 20% 미달. |
| `formula` | `(product(1 + r_stock_i for i in up_days) - 1) / (product(1 + r_bench_i for i in up_days) - 1) × 100` |
| `formula_detail` | 벤치마크 일간 수익률이 양수인 거래일만 필터링하여, 그 기간 동안의 종목 누적수익률 / 벤치마크 누적수익률. 252 거래일(1년) 기준. 벤치마크는 S&P 500 (`^GSPC`). |
| `source_type` | `calculated` |
| `fmp_endpoint` | `/historical-price-full/{symbol}`, `/historical-price-full/^GSPC` (각 1년치) |
| `fmp_fields` | `adjClose` (종목 + 벤치마크) |
| `direction` | `higher_is_better` |
| `metric_type` | `stock_level` |
| `window_trading_days` | 252 |
| `price_source` | adjusted |
| `benchmark` | S&P 500 (`^GSPC`) |
| `comparison_group` | `industry` |
| `fallback_rule` | industry → sector → universe |
| `refresh_frequency` | EOD |
| `ttm_method` | N/A (rolling window 기반) |
| `excluded_sectors` | [] |
| `applicable_presets` | Price Momentum(Supporting) |

**결측 처리**

| 상황 | 상태 | 처리 |
|---|---|---|
| 상장 252일 미만 | `Insufficient History` | 가용 기간으로 계산 + 태그. 최소 126거래일 필요 |
| 벤치마크 상승일 부족 (<30 거래일) | `Temporarily Unstable` | 계산 + "표본 부족" 태그. 극단적 약세장에서 발생 가능 |
| 벤치마크 상승일 0 | `Missing` | null (분모 0) |

**Phase 2 확장 예정**
- `down_capture_ratio` (하락 포착 비율) 짝 지표
- 다중 벤치마크 (`up_capture_ratio_vs_{benchmark}` 패턴)

---

## 6. Type 2 (portfolio_level) 지표 상세

### 40. `portfolio_volatility`

| 필드 | 정의 |
|---|---|
| `description` | 공분산을 반영한 포트폴리오 연간 변동성 |
| `calculation_logic` | `σ_p = √(w^T × Σ × w) × √252` |
| `dependencies` | 각 종목 252일 adjClose |
| `benchmark` | S&P 500의 동일 기간 변동성 |
| `lookback_window_days` | 252 |
| `min_holdings` | 2 |
| `price_source` | adjusted |
| `direction` | `lower_is_better` |
| `applicable_presets` | Low Volatility(Core), Concentrated(Context), Multi-Factor(Context) |

---

### 41. `portfolio_beta`

| 필드 | 정의 |
|---|---|
| `description` | 포트폴리오의 시장 민감도. 종목 beta의 비중 가중 평균 |
| `calculation_logic` | `β_p = Σ(w_i × β_i)` |
| `dependencies` | 각 종목 `beta` |
| `benchmark` | S&P 500 (beta=1 기준선) |
| `min_holdings` | 1 |
| `direction` | `정보 제공` |
| `applicable_presets` | Low Volatility(Core), Concentrated(Context) |

---

### 42. `sharpe_ratio`

| 필드 | 정의 |
|---|---|
| `description` | 초과 수익률 / 변동성. William Sharpe 고안 |
| `calculation_logic` | `(R_p - R_f) / σ_p`. R_f = 10Y Treasury yield |
| `dependencies` | `portfolio_volatility`, 10Y Treasury yield |
| `benchmark` | S&P 500 동일 기간 Sharpe |
| `lookback_window_days` | 252 |
| `min_holdings` | 2 |
| `price_source` | adjusted |
| `direction` | `higher_is_better` |
| `applicable_presets` | Low Volatility(Supporting), Concentrated(Supporting), Multi-Factor(Context) |

**R_f fallback 체인**: FMP Treasury → 최근 7일 평균 → 상수 4.0% + 로그 경고.

---

### 43. `sortino_ratio`

| 필드 | 정의 |
|---|---|
| `description` | Sharpe의 변형. 분모가 downside deviation |
| `calculation_logic` | `(R_p - R_f) / DD_p`. DD는 포트폴리오 일간 수익률 기반 재계산(종목 DD 가중평균 아님) |
| `dependencies` | 각 종목 historical_price, 10Y Treasury yield |
| `direction` | `higher_is_better` |
| `min_holdings` | 2 |
| `applicable_presets` | Low Volatility(Supporting), Concentrated(Core) |

---

### 44. `avg_correlation`

| 필드 | 정의 |
|---|---|
| `description` | 종목 쌍 상관계수의 단순 평균 |
| `calculation_logic` | N*(N-1)/2 쌍의 상관계수 단순 평균 |
| `comparison_group` | none (절대값 해석: 0.3 이하 양호, 0.6 이상 우려) |
| `min_holdings` | 2 |
| `direction` | `lower_is_better` |
| `applicable_presets` | Low Volatility(Supporting), Multi-Factor(Context) |

---

### 45. `max_risk_contribution`

| 필드 | 정의 |
|---|---|
| `description` | 개별 종목의 포트폴리오 변동성 기여 최댓값 |
| `calculation_logic` | `MRC_i = w_i × (Σw)_i / σ_p`. 최댓값 반환 |
| `dependencies` | 공분산 행렬, `portfolio_volatility` |
| `direction` | `lower_is_better` (프리셋별 flip 가능) |
| `comparison_group` | none (0.4 이상 집중 과다) |
| `applicable_presets` | Low Volatility(Core), Concentrated(Supporting) |

---

### 46. `hhi_concentration`

| 필드 | 정의 |
|---|---|
| `description` | 종목 비중의 제곱합. 반독점법 표준 집중도 |
| `calculation_logic` | `HHI = Σ(w_i²)` |
| `benchmark` | `1/N` (균등 분산 이론 최솟값) |
| `direction` | `lower_is_better` / `higher_is_better` (프리셋별) |
| `min_holdings` | 1 |
| `applicable_presets` | Low Volatility(Context), Concentrated(Core, flip), Multi-Factor(Context) |

**해석 기준**: <0.10 매우 분산, 0.10~0.18 적정, 0.18~0.25 집중, >0.25 고집중.

---

### 47. `top3_weight`

| 필드 | 정의 |
|---|---|
| `description` | 비중 상위 3종목 합 |
| `min_holdings` | 3 |
| `direction` | 프리셋별 |
| `applicable_presets` | Low Volatility(Context), Concentrated(Supporting) |

---

### 48. `holding_count`

| 필드 | 정의 |
|---|---|
| `display_name` | 보유 종목 수 |
| `description` | 포트폴리오에 포함된 고유 종목 수 (비중과 무관) |
| `formula` | `len(set(holdings))` |
| `direction` | `neutral` (정보 제공 목적) |
| `metric_type` | `portfolio_level` |
| `min_holdings` | 0 |
| `comparison_group` | N/A (포트폴리오 단일 값) |
| `refresh_frequency` | 포트폴리오 구성 변경 시 |
| `applicable_presets` | Concentrated(Core), 전 프리셋 Context |

**해석 가이드**: 단독으로는 좋고 나쁨이 없으나, 프리셋 철학에 따라 적정 범위가 다름. Concentrated Portfolio는 5~15개가 적정 범위로 통상 간주. Multi-Factor·Low Volatility는 30+ 선호.

---

### 49. `max_position_weight`

| 필드 | 정의 |
|---|---|
| `description` | 최대 단일 종목 비중 |
| `direction` | 프리셋별 |
| `min_holdings` | 1 |
| `applicable_presets` | Low Volatility(Supporting), Concentrated(Supporting) |

---

### 50. `sector_hhi`

| 필드 | 정의 |
|---|---|
| `description` | 섹터 비중의 제곱합 |
| `calculation_logic` | 종목 비중을 섹터별로 합산 후 제곱합 |
| `dependencies` | FMP `/profile`의 `sector` |
| `direction` | `lower_is_better` |
| `applicable_presets` | Low Volatility(Supporting), Concentrated(Context) |

---

### 51. `avg_market_cap`

| 필드 | 정의 |
|---|---|
| `description` | 비중 가중 평균 시가총액 |
| `calculation_logic` | `Σ(w_i × market_cap_i)` |
| `dependencies` | 각 종목 `market_cap` |
| `direction` | `정보 제공` |
| `applicable_presets` | Multi-Factor(Size 참고), Low Volatility(Context) |

---

### 52. `dividend_yield_portfolio`

| 필드 | 정의 |
|---|---|
| `display_name` | 포트폴리오 배당수익률 |
| `description` | 비중 가중 평균 배당수익률. 포트폴리오 전체가 연간 현재 주가 대비 얼마의 현금 배당을 기대할 수 있는지. |
| `formula` | `Σ(w_i × dividend_yield_i)` |
| `calculation_logic` | 무배당 종목은 dividend_yield = 0으로 취급 (N/A 아님 — 포트폴리오 산술에서는 0) |
| `dependencies` | 각 종목 `dividend_yield` |
| `direction` | `higher_is_better` (Dividend Growth 관점), `neutral` (일반 관점) |
| `metric_type` | `portfolio_level` |
| `comparison_group` | benchmark (S&P 500 배당수익률 vs 포트폴리오 배당수익률) |
| `benchmark` | S&P 500 배당수익률 (`^GSPC` dividend yield) |
| `refresh_frequency` | 일간 (가격 변동 반영) |
| `applicable_presets` | Dividend Growth(Supporting), Shareholder Yield(Supporting), Concentrated(Context) |

**해석 가이드**: 프리셋별로 의미가 다름. Dividend Growth에서는 핵심 확인 지표, Growth Compounder나 Price Momentum에서는 단순 정보. UI에서 프리셋 철학에 따라 tier 구분.

---

## 7. Type 3 (composite) 지표 상세

> **공통 적용**: Winsorized z-score (2.5% 양측 클리핑), §3 결정 #6

### 53. `composite_value`

| 필드 | 정의 |
|---|---|
| `composition_metrics` | `[(pe_ratio, 0.34), (pb_ratio, 0.33), (ev_to_ebitda, 0.33)]` |
| `normalization_method` | winsorized_z (2.5%, 업종 내) |
| `aggregation_method` | weighted_mean of z-scores |
| `input_direction_handling` | 3개 모두 lower_is_better → 부호 flip |
| `direction` | `higher_is_better` (저평가 → 양수) |
| `comparison_group` | universe |
| `version_pinning` | 분석 시점 고정 |
| `applicable_presets` | Multi-Factor(Core), Contrarian(Supporting) |

**결측 정책**: 1개 결측 시 2개로 가중 재분배, 2개 이상 결측 시 Missing.

---

### 54. `composite_quality`

| 필드 | 정의 |
|---|---|
| `composition_metrics` | `[(roic, 0.35), (gross_margin, 0.25), (debt_to_equity, 0.20), (roe_stability_5y, 0.20)]` |
| `normalization_method` | winsorized_z (2.5%, 업종 내) |
| `aggregation_method` | weighted_mean of z-scores |
| `input_direction_handling` | `debt_to_equity`, `roe_stability_5y` 부호 flip (둘 다 lower_is_better) |
| `direction` | `higher_is_better` |
| `comparison_group` | universe |
| `applicable_presets` | Multi-Factor(Core), Quality Factor(Context) |

**결측 정책**: `roe_stability_5y` 결측(상장 5년 미만) 시 3개로 폴백. 2개 이상 결측 시 Missing.

---

### 55. `composite_momentum`

| 필드 | 정의 |
|---|---|
| `composition_metrics` | `[(return_12m, 0.40), (relative_strength, 0.35), (return_6m, 0.25)]` |
| `normalization_method` | winsorized_z (2.5%, universe 전체) |
| `aggregation_method` | weighted_mean of z-scores |
| `input_direction_handling` | 모두 higher_is_better → 부호 그대로 |
| `direction` | `higher_is_better` |
| `comparison_group` | universe |
| `applicable_presets` | Multi-Factor(Core), Price Momentum(Context) |

**엣지 케이스**: MVP는 단순 12m. Phase 2에 "12-1 모멘텀" 교체 예정.

---

### 56. `composite_growth`

| 필드 | 정의 |
|---|---|
| `display_name` | 성장 합성 |
| `description` | EPS 성장률 + 매출 성장률 + 매출 성장 지속성의 정규화 합성. Multi-Factor 프리셋의 5개 Core 팩터 중 하나. |
| `composition_metrics` | `[(eps_growth_yoy, 0.40), (revenue_growth_yoy, 0.35), (revenue_growth_consistency_3y, 0.25)]` |
| `normalization_method` | winsorized_z (2.5%, 업종 내) |
| `aggregation_method` | weighted_mean of z-scores |
| `input_direction_handling` | 3개 모두 higher_is_better → 부호 그대로 |
| `direction` | `higher_is_better` |
| `metric_type` | `composite` |
| `comparison_group` | industry → sector → universe |
| `version_pinning` | 분석 시점 고정 |
| `dependencies` | `eps_growth_yoy`, `revenue_growth_yoy`, `revenue_growth_consistency_3y` |
| `applicable_presets` | Multi-Factor(Core), Quality Growth(Context) |

**결측 정책**: `revenue_growth_consistency_3y` 결측(상장 3년 미만) 시 앞 2개 가중 재분배(0.53/0.47). 2개 이상 결측 시 Missing.

**엣지 케이스**
- 턴어라운드 기업(순이익 음수 → 양수): EPS 성장률이 극단값(수백~수천%) → winsorized로 클리핑
- 적자 기업: EPS 성장률 계산 불가 → `Not Applicable` (분모 음수 또는 0)

**설계 근거**: 기존 `factor_size`(크기 팩터) 대체. 04-18 결정 "Multi-Factor 5개 Core 슬롯 = Value / Quality / Growth / Momentum / Low Vol"에 따라 Size 팩터는 Phase 2로 이연, Growth 팩터가 Core로 승격.

---

### 57. `composite_low_vol`

| 필드 | 정의 |
|---|---|
| `display_name` | 저변동성 합성 |
| `description` | 1년 변동성 + 하방 편차 + 최대 낙폭의 정규화 합성 (모두 flip). Multi-Factor 프리셋의 5개 Core 팩터 중 하나. |
| `composition_metrics` | `[(volatility_1y, 0.40), (downside_deviation, 0.35), (max_drawdown_1y, 0.25)]` |
| `normalization_method` | winsorized_z (2.5%, universe 전체 — 저변동성은 업종 무관 특성) |
| `aggregation_method` | weighted_mean of z-scores |
| `input_direction_handling` | 3개 모두 lower_is_better → 부호 flip |
| `direction` | `higher_is_better` (변동성 낮을수록 양수) |
| `metric_type` | `composite` |
| `comparison_group` | universe |
| `version_pinning` | 분석 시점 고정 |
| `dependencies` | `volatility_1y`, `downside_deviation`, `max_drawdown_1y` |
| `applicable_presets` | Multi-Factor(Core), Low Volatility(Supporting) |

**결측 정책**: 상장 252일 미만으로 3개 모두 계산 불가 시 Missing. 1개 결측(드물음) 시 2개로 가중 재분배.

**설계 근거**: 기존 `factor_balance_score`(4팩터 균형 메타 지표) 대체. 04-18 결정에 따라 5번째 Core 슬롯은 Low Vol 팩터로 확정. 균형 측정은 MVP 필수가 아니며 Phase 2로 이연.

---

## 8. 결측 상태 (Data Status) 정의

설계서 v3.1의 §9-3과 동일. 재확인용:

| 상태 | 의미 | UI 처리 |
|---|---|---|
| `Missing` | 데이터 소스에 값 없음 | "데이터 없음" |
| `Not Applicable` | 해당 종목에 지표 미적용 | "해당 없음" + 설명 |
| `Delayed` | 미갱신 (실적 발표 직후 등) | 이전 값 + "갱신 대기" |
| `Insufficient History` | 상장 기간·표본 부족 | 가용 기간 계산 + "제한적 데이터" |
| `Temporarily Unstable` | 일시적 이상치 (M&A, 대규모 상각) | 값 + "일시적 왜곡 가능" |

---

## 9. 버전 관리

### 9-1. `metric_definition_version`

| 변경 사유 | 예시 | 버전 증가 |
|---|---|---|
| 산식 변경 | ROIC 세율 21% → 국가별 테이블 | major |
| 구성 요소 추가·삭제 | composite_quality에 새 metric 추가 | major |
| 임계값·파라미터 변경 | winsorization 2.5% → 1.0% | minor |
| 결측 정책 조정 | min_years 변경 | minor |
| 문서 오타 수정 | | patch |

### 9-2. 호환성 규칙

- **Saved Analysis**: 분석 시점의 `metric_definition_version` 고정. 이후 버전 변경 무관하게 동일 결과 재현 가능
- **Temp Analysis**: 최신 버전 사용. 버전 변경 시 재계산
- **Percentile Cache**: 버전별 독립 캐시 키. 버전 변경 시 신규 캐시 생성, 구 캐시는 TTL 만료 대기

---

## 10. 구현 로드맵

### 10-1. MVP (현 단계)

| 우선순위 | 작업 | 예상 |
|---|---|---|
| P0 | Type 1 지표 36개 구현 (Django + Celery 배치) | 4~6주 |
| P0 | Metric Dictionary DB 모델링 (Django models) | 1주 |
| P0 | Percentile 배치 (S&P 500 + 사용자 보유 종목 industry peers) | 1~2주 |
| P1 | Type 2 지표 12개 구현 (포트폴리오 조회 시 on-demand) | 2~3주 |
| P1 | Type 3 합성 팩터 5개 구현 (Type 1 의존) | 1~2주 |
| P2 | 결측 플래그 UI 연동 (Insufficient History, Temporarily Unstable 등) | 1주 |

### 10-2. Phase 2 이후

- Core 계층의 Definitional vs. Evaluative 세분화 (Hard Gate 처리)
- `return_12_1m` 등 정교한 모멘텀 변형
- 국가별 법정세율 테이블 (ROIC 글로벌 확장)
- 기하평균 `avg_log_market_cap`
- 다중 벤치마크 (`relative_strength_vs_{benchmark}` 패턴)
- 업종별 팩터 합성 가중치 조정

---

## 11. 변경 이력

| 버전 | 날짜 | 변경 내용 |
|---|---|---|
| v1.0 | 2026-04-16 | 초안 — 53개 지표 전체 정의, 공통 스키마(Type별 확장) 확정 |
| v1.1 | 2026-04-17 | 지표 1~10 원본 상세 반영 (formula_detail, ttm_method, 결측 처리 테이블, 엣지 케이스 메모). 공통 결정 #7(FMP 소스 전략), #8(금융 기업 처리) 추가. Type 1 확장 필드에 ttm_method 추가 |
| v1.2 | 2026-04-18 | **동기화 배치 1/3 (Dictionary)**. ① rename 4건: `stock_count`→`holding_count`, `factor_value`→`composite_value`, `factor_quality`→`composite_quality`, `factor_momentum`→`composite_momentum`. ② 재구성 2건: `factor_size`→`composite_growth` (EPS/매출 성장 합성으로 교체), `factor_balance_score`→`composite_low_vol` (변동성 합성으로 교체). ③ 신규 추가 4건: `f_score_total`(Piotroski, 서브 9개 내부 표 포함), `ulcer_index`, `up_capture_ratio`, `dividend_yield_portfolio`. ④ 번호 재정렬: Type 1 36→39개, Type 2 12→13개, Type 3 5개 유지. 총 53→57개. ⑤ 섹션 #4(목록)·#9(예시)·#11(이력) 동기화 |

---

## 부록 A. 공통 결정 사항 상세

### A-1. ROIC 세율 21% 고정 (결정 #1)

- **배경**: 기업 간 비교의 공정성 vs 실제 세부담 반영의 트레이드오프
- **선택**: Greenblatt Magic Formula 방식의 한계세율 고정
- **이유**: 비교 공정성, 구현 단순성, 결측치 문제 제거
- **Phase 2**: 국가별 법정세율 테이블

### A-2. 멀티이어 집계 정책 (결정 #2)

- **Count형** (`count_based`): `min_years = max(3, ceil(N × 0.6))`. 가용 기간 대비 비율로 정규화
- **수치형** (`numeric_aggregation`): `min_years = N` (Strict). 기간 다른 값 혼재 방지
- **예외**: `revenue_growth_consistency_3y`는 N=3 지표 특성상 `min_years=2`

### A-3. 시간 단위 기준 (결정 #3)

- 내부 계산: 거래일 기준 (`window_trading_days`)
- UI 표시: 캘린더 표현 ("12개월 수익률")
- 툴팁 주석: "최근 252 거래일 기준 (약 12개월)"

### A-4. 가격 소스 (결정 #4)

- 수익률·변동성·리스크: `adjusted` (배당·분할 조정)
- 레벨형 (52w high/low): `raw` (사용자 체감 일치)
- `PriceFetcher` 인터페이스: `get_prices(ticker, window, source='adjusted'|'raw')`

### A-5. 스키마 구조 (결정 #5)

- 공통 코어 + Type별 확장 섹션
- 신규 Type 추가(자산유형 확장 등) 시 공통 코어 불변

### A-6. 정규화 방법 (결정 #6)

- Winsorized z-score, 2.5% 양측 클리핑
- 클리핑 임계값은 `scoring_version` 관리 대상
- 클리핑된 원시값은 `clipped_from` 필드에 별도 저장 (디버깅용)

### A-7. FMP 소스 전략 (결정 #7)

- **원칙**: "산식의 분자·분모를 우리가 통제할 수 있는가?"
- **재무제표 항목으로 계산 가능한 지표 → 직접 계산**: ROIC, ROE, gross_margin, fcf_margin, D/E, payout_ratio, EPS 성장률, P/E(분모 EPS 직접 계산), P/B(분모 BPS 직접 계산), EV/EBITDA 등
- **시장 가격·통계 지표 → FMP 값 사용**: beta, market_cap, 현재 주가, 52주 고가/저가, 거래량
- **밸류에이션 비율(P/E, P/B 등) → 혼합**: Price는 FMP 시세(quote), 분모(EPS, BPS)는 재무제표에서 직접 계산
- Dictionary의 `source_type` 필드로 명확 구분: `calculated` / `fmp_native`

### A-8. 금융 기업 처리 방침 (결정 #8)

- **방침**: 금융 기업도 포트폴리오에 포함. 부적합 지표만 `Not Applicable` 처리 (Option B)
- **부적합 지표**: `roic`(Invested Capital 부적합), `gross_margin`(COGS 없음), `fcf_margin`(FCF 부적합), `debt_to_equity`(부채=원재료), `ev_to_ebitda`(EV 개념 부적합)
- **적용 가능 지표**: `roe`(은행 핵심), `pe_ratio`, `pb_ratio`, `beta`, `market_cap`, 가격 기반 전체
- **coverage_ratio 표시**: 진단 결과에 "12개 지표 중 8개 적용 가능" 안내
- **Phase 2 확장**: 금융 전용 대체 지표(`net_interest_margin`, `tier1_capital_ratio` 등) 매핑 검토

---

## 부록 B. 프리셋-지표 매핑 요약표

각 프리셋이 참조하는 Core/Supporting/Context 지표 수:

| 프리셋 | Core | Supporting | Context | Total |
|---|---|---|---|---|
| Buffett Quality Value | 4 | 4 | 4 | 12 |
| Piotroski F-Score | 1 (f_score_total) | — | — | 1 (+ 9 서브) |
| GARP | 2 | 2 | 2 | 6 |
| Quality Growth | 3 | 3 | 2 | 8 |
| Dividend Growth | 3 | 1 | 1 | 5 |
| Shareholder Yield | 3 | — | 1 | 4 |
| Quality Factor | 3 | 3 | — | 6 |
| Low Volatility | 4 | 4 | 4 | 12 |
| Price Momentum | 2 | 3 | 1 | 6 |
| Multi-Factor | 5 (4 factor + 1 balance) | 1 | 2 | 8 |
| Contrarian | 3 | 3 | — | 6 |
| Concentrated Portfolio | 3 | 3 | 3 | 9 |

**상세 배정**은 `stock-vis-preset-metrics-matrix.md` 참조.

---

**문서 종료 — v1.2 (2026-04-18 업데이트)**
