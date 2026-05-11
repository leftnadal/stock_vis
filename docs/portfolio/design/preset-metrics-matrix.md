# Stock-Vis 프리셋 × 지표 × 계층 매트릭스

> 작성일: 2026-04-08
> 상태: 초안 (Metric Dictionary 연결 전)
> 관련 문서: stock-vis-preset-design-v3.1.md (설계서), stock-vis-preset-reference.md (이론 레퍼런스)
> ROIC 산식: EBIT × (1 - 0.21) / Invested Capital. MVP는 미국 법정세율 21% 고정.

---

## 프리셋 목록 (MVP 12개)

| # | 카테고리 | 프리셋 | 코칭 질문 |
|---|---|---|---|
| 1 | 가치 | Buffett Quality Value | 경쟁우위가 있는 훌륭한 기업을 합리적 가격에 보유하고 있는가? |
| 2 | 가치 | Piotroski F-Score | 이 기업의 재무 건전성이 개선되고 있는가, 악화되고 있는가? |
| 3 | 성장 | GARP | 이 기업의 성장이 지속 가능하고, 그 대가로 지불하는 가격이 적정한가? |
| 4 | 성장 | Quality Growth / Compounder | 이 기업이 10년간 복리로 성장할 수 있는 구조를 갖추고 있는가? |
| 5 | 배당 | Dividend Growth | 이 기업이 앞으로도 배당을 올릴 수 있는 체력이 있는가? |
| 6 | 배당 | Shareholder Yield | 배당, 자사주매입, 부채 상환을 통해 주주에게 얼마나 돌려주고 있는가? |
| 7 | 퀄리티 | Quality Factor | 시장이 흔들릴 때 이 포트폴리오가 버틸 수 있는 체력이 있는가? |
| 8 | 퀄리티 | Low Volatility | 이 포트폴리오가 시장 하락 시 얼마나 방어적인가? |
| 9 | 모멘텀 | Price Momentum | 시장의 상승 흐름에 올라타고 있는 종목이 얼마나 되는가? |
| 10 | 퀀트 | Multi-Factor | 어떤 수익 요인(팩터)에 노출되어 있고, 특정 팩터에 쏠려있지 않은가? |
| 11 | 역발상 | Contrarian | 시장이 과잉 반응한 곳에서 기회를 잡고 있는가, 함정에 빠져 있는가? |
| 12 | 테마/전략 | Concentrated Portfolio | 포트폴리오의 집중도가 의도적인 것인가, 구조적으로 안전한가? |

---

## 1. Buffett Quality Value

### 코칭 질문
"경쟁우위가 있는 훌륭한 기업을 합리적 가격에 보유하고 있는가?"

### 지표 매트릭스

| 계층 | 지표 | metric_id | 산식 | 방향 | FMP 소스 | 투자자에게 주는 의미 |
|---|---|---|---|---|---|---|
| **Core** | ROIC | `roic` | EBIT×(1-0.21) / (Total Assets - Current Liabilities) | higher_is_better | operatingIncome, totalAssets, totalCurrentLiabilities | 이 기업이 투입한 돈 대비 얼마나 효율적으로 벌고 있는가. 높을수록 사업 자체가 좋은 구조 |
| **Core** | ROIC 5년 지속성 | `roic_consistency_5y` | 최근 5년 중 ROIC 15%+ 달성 연수 (0~5) | higher_is_better | 5년치 연간 재무 | 올해만 좋은 건지, 계속 좋은 건지. 5년 중 4~5년이면 경쟁우위가 진짜 있다는 증거 |
| **Core** | ROE | `roe` | Net Income / Shareholders Equity | higher_is_better | netIncome, totalStockholdersEquity | 주주의 돈으로 얼마나 벌어주는가. Buffett이 가장 자주 보는 지표. 15%+ 지속이면 우량 |
| **Core** | 이익 일관성 | `earnings_consistency_5y` | 최근 5년 중 EPS YoY 양수인 연수 (0~5) | higher_is_better | 5년치 EPS | 매년 꾸준히 이익이 느는 기업인가. 들쭉날쭉하면 사업 예측이 어렵고 장기 보유가 불안 |
| **Supporting** | P/E | `pe_ratio` | Price / EPS (TTM) | lower_is_better | peRatioTTM | 이 기업의 1년 이익 대비 현재 주가가 얼마나 비싼가. 좋은 기업이라도 너무 비싸면 수익이 제한됨 |
| **Supporting** | 부채비율 (D/E) | `debt_to_equity` | Total Debt / Shareholders Equity | lower_is_better | totalDebt, totalStockholdersEquity | 빚이 얼마나 많은가. 부채가 적은 기업이 금리 인상이나 경기 침체를 더 잘 버팀 |
| **Supporting** | FCF 마진 | `fcf_margin` | Free Cash Flow / Revenue | higher_is_better | freeCashFlow, revenue | 매출에서 실제로 현금이 얼마나 남는가. 회계상 이익이 아닌 진짜 현금 창출 능력 |
| **Supporting** | 자사주매입 여부 | `buyback_yield` | (전년 발행주식수 - 금년) / 전년 발행주식수 | higher_is_better | weightedAverageShsOut (2년치) | 회사가 자기 주식을 사서 소각하고 있는가. 경영진이 자기 회사를 저평가라고 판단하는 신호이자 주주환원 |
| **Context** | P/B | `pb_ratio` | Price / Book Value per Share | lower_is_better | pbRatio | 순자산 대비 주가가 얼마인가. 1 이하면 자산가치보다 싸게 거래되는 것 |
| **Context** | 배당수익률 | `dividend_yield` | Annual Dividend / Price | higher_is_better | dividendYield | 현재 주가 대비 매년 받는 배당 비율. 추가 현금흐름 |
| **Context** | 시가총액 | `market_cap` | | 정보 제공 | marketCap | 기업의 전체 크기. 대형주일수록 안정적이지만 성장 여지는 제한적 |
| **Context** | Beta | `beta` | | 정보 제공 | beta | 시장이 10% 움직일 때 이 종목은 몇 % 움직이는가. 1 이상이면 시장보다 더 크게 흔들림 |


### 보조 속성

| metric_id | metric_group | eligible_strength | eligible_weakness | eligible_card | hard_gate | display_condition | llm_comment_style |
|---|---|---|---|---|---|---|---|
| `roic` | quality | Y | Y | Y | N | 금융업 별도 검토 | 철학 직접 연결 — moat의 간접 증거 |
| `roic_consistency_5y` | quality | Y | Y | Y | Y | 상장 5년 미만 시 제한적 데이터 태그 | 철학 직접 연결 — 지속성이 핵심 |
| `roe` | quality | Y | Y | Y | N | 자본 음수 시 N/A | 철학 직접 연결 — Buffett 대표 지표 |
| `earnings_consistency_5y` | quality | Y | Y | Y | N | 상장 5년 미만 시 제한적 데이터 태그 | 예측 가능성 설명 |
| `pe_ratio` | valuation | Y | Y | 조건부Y | N | 적자 시 N/A | "합리적이면 OK" 톤 — 과도한 강조 금지 |
| `debt_to_equity` | quality | Y | Y | 조건부Y | N | 금융업 별도 해석 | 위기 버틸 수 있는가 관점 |
| `fcf_margin` | quality | Y | Y | 조건부Y | N | FCF 음수 시 경고 표시 | 진짜 현금 창출 강조 |
| `buyback_yield` | income | Y | Y | 조건부Y | N | 항상 표시 (0%도 의미 있음) | 경영진 판단 신호로 설명 |
| `pb_ratio` | valuation | N | N | N | N | 항상 표시 가능 | 수치만 노출 |
| `dividend_yield` | income | N | N | N | N | 무배당 시 0% 표시 | 수치만 노출 |
| `market_cap` | info | N | N | N | N | 항상 표시 | 별도 해설 최소 |
| `beta` | risk | N | N | N | N | 가격 데이터 필요 | 별도 해설 최소 |

### 해설

Buffett의 투자 철학은 Graham의 "싼 주식 사기"에서 Munger의 영향으로 "합리적 가격에 훌륭한 기업 사기"로 진화했다. 이 프리셋의 핵심은 "훌륭한"을 정량화하는 것이다.

ROIC와 ROIC 지속성이 가장 중요한 이유는, 일시적으로 높은 수익을 내는 기업은 많지만 5년 이상 유지하는 기업은 구조적 경쟁우위(moat)가 있다는 간접 증거이기 때문이다. ROE를 별도로 보는 이유는 Buffett이 실제로 가장 자주 언급하는 지표이기 때문이며, ROIC와 달리 부채를 통한 레버리지 효과를 포함한다.

P/E를 Core가 아닌 Supporting으로 놓은 이유: Buffett은 "좋은 기업이 적당히 비싼 것은 OK, 나쁜 기업이 싼 것은 안 OK"라고 말했다. 가격은 중요하지만 기업 품질보다는 후순위다.

### 특이사항

- ROIC 산식에서 Invested Capital = Total Assets - Current Liabilities로 정의. 이 정의가 학계에서 가장 널리 쓰이지만, 다른 정의(Equity + Long-term Debt - Cash 등)도 존재. MVP에서는 이 정의로 고정
- 5년치 데이터가 필요한 지표가 2개(ROIC 지속성, 이익 일관성). 상장 5년 미만 기업은 가용 기간으로 계산 + "제한적 데이터" 태그
- "경쟁우위(moat)"는 정량화할 수 없는 요소. ROIC 지속성은 moat의 결과이지 원인이 아님. Phase 2에서 Chain Sight의 관계 그래프가 moat의 원인(공급망 독점, 네트워크 효과 등)을 시각화할 수 있음
- Buffett은 "이해 가능한 비즈니스"를 강조하는데, 이건 데이터로 판단할 수 없음. Thesis Control에서 사용자가 직접 평가하도록 유도

### 진단 카드 예시

**카드 1: ROIC 지속성 부족**
> NVDA와 TSLA의 ROIC가 최근 5년 중 각각 3년, 2년만 15%를 넘었습니다. 반도체/전기차 업종 내에서 하위 40%에 해당합니다.
>
> Buffett은 경쟁우위가 10년 이상 지속되는 기업을 선호합니다. ROIC가 일시적으로 높았다가 떨어지는 패턴은 경쟁 심화나 사이클 의존성을 시사할 수 있습니다.
>
> 다만 NVDA의 경우 AI 인프라 수요 급증이 최근 3년의 ROIC를 끌어올린 것이므로, 이 성장이 구조적인지 일시적인지는 thesis에서 별도로 검증해볼 필요가 있습니다.

**카드 2: 부채 수준 주의**
> META의 부채비율(D/E 1.4)이 소프트웨어/인터넷 업종 내 하위 25%에 위치합니다.
>
> Buffett은 위기 시에도 생존할 수 있는 낮은 부채를 선호합니다. 높은 부채는 금리 인상기에 이자 부담을 증가시키고, 경기 침체 시 유동성 위기를 초래할 수 있습니다.
>
> 다만 META의 부채 증가가 자사주매입 자금 조달 목적이라면, 주주환원과 재무건전성 사이의 트레이드오프로 볼 수 있습니다. 이자보상배율을 함께 확인해보세요.

**카드 3: 이익 일관성 양호하나 주의 종목 존재**
> 5개 종목 중 MSFT, LLY, KO는 5년 연속 EPS 성장을 기록했으나, INTC는 최근 2년간 EPS가 감소했습니다.
>
> Buffett은 예측 가능한 이익 흐름을 가진 기업을 선호합니다. 이익이 들쭉날쭉한 기업은 내재가치 추정이 어렵고, 장기 보유 시 심리적 부담이 큽니다.
>
> INTC의 이익 감소가 일시적 사이클인지 구조적 경쟁력 약화인지에 따라 보유 근거가 달라집니다.

### 다른 프리셋과의 차별화

| 비교 대상 | 핵심 차이 |
|---|---|
| vs GARP | Buffett은 기업의 질(ROIC, moat)이 최우선. GARP은 가격 대비 성장(PEG)이 최우선 |
| vs Quality Growth | Buffett은 이미 좋은 기업의 현재 상태를 봄. Compounder는 앞으로 10년 복리 가능성을 봄 |
| vs Quality Factor | Buffett은 질적 판단(moat, 경영진)을 포함. Quality Factor는 순수 정량 팩터 |

---

## 2. Piotroski F-Score

### 코칭 질문
"이 기업의 재무 건전성이 개선되고 있는가, 악화되고 있는가?"

### 지표 매트릭스

| 계층 | 지표 | metric_id | 산식 | 방향 | FMP 소스 | 투자자에게 주는 의미 |
|---|---|---|---|---|---|---|
| **Core** | F-Score 합산 | `f_score_total` | 아래 9개 항목의 0/1 합산 (0~9) | higher_is_better | 아래 항목들로 계산 | 9개 재무 체크리스트 중 몇 개를 통과했는가. 8~9점이면 재무 상태가 전반적으로 개선 중 |
| **Core** | ROA 양수 | `f_roa_positive` | Net Income / Total Assets > 0 → 1점 | pass/fail | netIncome, totalAssets | 기본적으로 돈을 벌고 있는가. 이게 0이면 적자 기업 |
| **Core** | 영업CFO 양수 | `f_cfo_positive` | Operating Cash Flow > 0 → 1점 | pass/fail | operatingCashFlow | 실제 영업에서 현금이 들어오고 있는가. 회계상 이익은 있는데 현금이 안 들어오면 위험 신호 |
| **Core** | ROA 개선 | `f_roa_change` | 올해 ROA > 전년 ROA → 1점 | pass/fail | 2년치 | 수익성이 좋아지고 있는가. 작년보다 올해가 더 나은 방향인지 확인 |
| **Core** | 발생주의 품질 | `f_accrual_quality` | CFO > Net Income → 1점 | pass/fail | operatingCashFlow, netIncome | 이익이 진짜 현금으로 뒷받침되는가. 현금흐름이 순이익보다 적으면 이익의 질이 낮다는 경고 |
| **Supporting** | 부채비율 감소 | `f_leverage_change` | 올해 장기부채/자산 < 전년 → 1점 | pass/fail | longTermDebt, totalAssets (2년치) | 빚을 줄이고 있는가. 부채 감소는 재무 체질 개선의 신호 |
| **Supporting** | 유동비율 개선 | `f_liquidity_change` | 올해 유동비율 > 전년 → 1점 | pass/fail | currentRatio (2년치) | 단기 빚을 갚을 능력이 좋아지고 있는가. 유동비율이 개선되면 단기 부도 위험 감소 |
| **Supporting** | 신주 미발행 | `f_no_dilution` | 올해 발행주식수 ≤ 전년 → 1점 | pass/fail | weightedAverageShsOut (2년치) | 주식을 새로 찍어서 내 지분을 희석시키지 않았는가. 신주 발행은 기존 주주의 가치를 깎는 행위 |
| **Supporting** | 매출총이익률 개선 | `f_gross_margin_change` | 올해 > 전년 → 1점 | pass/fail | grossProfitRatio (2년치) | 원가 대비 마진이 좋아지고 있는가. 개선되면 가격결정력이 강해지거나 비용 효율이 높아진 것 |
| **Supporting** | 자산회전율 개선 | `f_asset_turnover_change` | 올해 매출/자산 > 전년 → 1점 | pass/fail | revenue, totalAssets (2년치) | 보유 자산을 더 효율적으로 활용하고 있는가. 같은 자산으로 더 많은 매출을 올리면 효율 개선 |
| **Context** | P/B | `pb_ratio` | | lower_is_better | pbRatio | 순자산 대비 주가. 저PBR + 고F-Score 조합이 Piotroski 전략의 핵심 |
| **Context** | P/E | `pe_ratio` | | lower_is_better | peRatioTTM | 이익 대비 주가. 재무가 개선되는 저평가 기업이 가장 매력적 |
| **Context** | 시가총액 | `market_cap` | | 정보 제공 | marketCap | 기업 크기. 소형주에서 F-Score 효과가 더 강하다는 연구 결과 있음 |


### 보조 속성

| metric_id | metric_group | eligible_strength | eligible_weakness | eligible_card | hard_gate | display_condition | llm_comment_style |
|---|---|---|---|---|---|---|---|
| `f_score_total` | quality | Y | Y | Y | N | 항상 표시 | 철학 직접 연결 — 종합 체크리스트 |
| `f_roa_positive` | quality | Y | Y | Y | Y | 항상 표시 | 적자 여부 직접 진단 |
| `f_cfo_positive` | quality | Y | Y | Y | Y | 항상 표시 | 현금흐름 건전성 설명 |
| `f_roa_change` | quality | Y | Y | Y | N | 2년치 데이터 필요. 결측 시 판정 불가 | 개선 방향 설명 — 시간축 강조 |
| `f_accrual_quality` | quality | Y | Y | Y | N | 항상 표시 | 이익의 질 경고형 |
| `f_leverage_change` | quality | Y | Y | 조건부Y | N | 2년치 데이터 필요 | 재무 체질 개선 설명 |
| `f_liquidity_change` | quality | Y | Y | 조건부Y | N | 2년치 데이터 필요 | 단기 안전성 설명 |
| `f_no_dilution` | quality | Y | Y | 조건부Y | N | 2년치 데이터 필요 | 지분 희석 경고 |
| `f_gross_margin_change` | quality | Y | Y | 조건부Y | N | 2년치 데이터 필요 | 가격결정력 설명 |
| `f_asset_turnover_change` | quality | Y | Y | 조건부Y | N | 2년치 데이터 필요 | 효율성 설명 |
| `pb_ratio` | valuation | N | N | N | N | 항상 표시 | 저PBR+고F-Score 조합 맥락 |
| `pe_ratio` | valuation | N | N | N | N | 적자 시 N/A | 수치만 노출 |
| `market_cap` | info | N | N | N | N | 항상 표시 | 소형주 효과 맥락 |

### 해설

Piotroski의 핵심 통찰은 "저PBR 주식이 전부 좋은 게 아니다"는 것이다. 저PBR 주식 중에는 싸니까 좋은 것(진짜 가치)도 있고, 싸는 이유가 있는 것(가치 함정)도 있다. 9개 재무 체크리스트로 "재무가 개선되고 있는 기업"을 골라내면 가치 함정을 피할 수 있다.

이 프리셋의 독특한 점은 **"지금 좋은가"가 아니라 "좋아지고 있는가"를 본다**는 것이다. 다른 프리셋은 현재 상태(ROE가 15%인가)를 보지만, Piotroski는 변화 방향(ROA가 전년보다 올랐는가)을 본다. 이 시간축이 있는 진단이 다른 프리셋에는 없는 가치다.

9개 항목을 3개 영역으로 나누면 교차 진단이 가능하다. "수익성은 개선 중(3/4)이지만 부채가 늘고 있다(건전성 1/3)" 같은 다차원적 판단이 진단 카드에 자연스럽게 녹아든다.

### 특이사항

- **퍼센타일보다 체크리스트가 자연스러운 프리셋.** 9개 항목은 업종 대비 백분위가 아니라 해당 기업의 전년 대비 개선 여부를 봄. UI는 ✅/❌ 체크리스트 형태가 적합
- **레벨 태그와 정렬은 F-Score 합산의 업종 내 퍼센타일로 처리.** 예: 업종 내 F-Score 7점이 상위 몇 %인지로 레벨 태그 부여
- **2년치 재무 데이터 필수.** 9개 항목 중 8개가 "올해 vs 전년" 비교. 결측 시 해당 항목은 "판정 불가" 처리하고 합산에서 제외하되, 가능한 항목만으로 비율 점수 산출 (예: 7개 판정 가능 중 5개 통과 = 5/7)
- **실적 발표 시점에 따른 갱신 타이밍 이슈.** 기업마다 실적 발표 시기가 다르므로, "올해"의 정의를 최근 연간 재무제표(TTM 또는 최근 연도)로 통일해야 함
- **금융/유틸리티 기업에서 일부 지표가 부적합.** 금융사의 유동비율이나 자산회전율은 일반 기업과 해석이 다름. MVP에서는 일괄 적용하되, Phase 2에서 섹터별 예외 처리 검토

### 진단 카드 예시

**카드 1: 수익성 영역 부분 개선**
> 수익성 4개 항목 중 3개가 통과했으나 ROA가 전년 대비 하락했습니다(12.3% → 11.1%). 반도체 업종 87개사 중 F-Score 7점은 상위 35%에 해당합니다.
>
> Piotroski 관점에서 ROA 하락은 자본 효율성이 떨어지고 있다는 신호입니다. 매출이 늘었더라도 자산 증가 속도가 더 빠르면 ROA는 하락할 수 있습니다.
>
> 다만 NVDA의 경우 대규모 설비 투자(데이터센터용 GPU 생산 확대)가 단기적으로 자산을 크게 늘렸을 수 있습니다. 이 투자가 향후 매출로 전환되면 ROA가 회복될 가능성이 있습니다.

**카드 2: 신주 발행으로 지분 희석**
> INTC가 전년 대비 발행주식수가 2.3% 증가했습니다. 이 항목이 0점으로 신주 미발행 조건을 충족하지 못했습니다.
>
> 신주 발행은 기존 주주의 지분을 희석시킵니다. Piotroski는 외부 자금 조달 없이 내부 현금으로 운영하는 기업을 선호합니다.
>
> 다만 신주 발행이 전략적 인수합병이나 핵심 인력 보상(스톡옵션) 목적이라면, 장기적으로 기업 가치를 높일 수 있는 투자일 수 있습니다. 발행 목적을 확인해보세요.

**카드 3: 발생주의 품질 경고**
> AMZN의 순이익(38.5B)이 영업현금흐름(28.2B)보다 큽니다. 발생주의 품질 항목이 0점입니다.
>
> 이익이 현금으로 뒷받침되지 않으면 회계적 조정(감가상각 변경, 수익 인식 시점 등)으로 이익이 부풀려졌을 가능성이 있습니다. Piotroski는 이를 이익의 질이 낮다는 경고로 봅니다.
>
> 다만 대규모 선제 투자(물류 인프라, 클라우드 설비 등)가 있는 기업은 CAPEX가 커서 FCF가 일시적으로 낮을 수 있습니다. Operating CF vs Net Income의 괴리가 일시적인지 구조적인지 구분이 필요합니다.

### 다른 프리셋과의 차별화

| 비교 대상 | 핵심 차이 |
|---|---|
| vs Buffett | Buffett은 "이미 좋은 기업"의 현재 상태. Piotroski는 "좋아지고 있는 기업"의 변화 방향 |
| vs Quality Factor | Quality Factor는 수익성/안정성의 절대 수준. Piotroski는 개선 여부(전년 대비 변화) |
| vs Contrarian | Contrarian은 가격 기반 역발상. Piotroski는 재무제표 기반 필터링. 둘을 조합하면 "싸면서 재무가 개선 중인" 종목을 찾을 수 있음 |

---

## 3. GARP (Growth at a Reasonable Price)

### 코칭 질문
"이 기업의 성장이 지속 가능하고, 그 대가로 지불하는 가격이 적정한가?"

### 지표 매트릭스

| 계층 | 지표 | metric_id | 산식 | 방향 | FMP 소스 | 투자자에게 주는 의미 |
|---|---|---|---|---|---|---|
| **Core** | PEG | `peg_ratio` | P/E / EPS 성장률(연간) | lower_is_better | peRatioTTM, epsgrowth | 성장 속도 대비 주가가 적정한가. 1 이하면 성장에 비해 싸고, 2 이상이면 성장을 이미 반영한 가격 |
| **Core** | EPS 성장률 (YoY) | `eps_growth_yoy` | (올해 EPS - 전년 EPS) / 전년 EPS | higher_is_better | epsgrowth | 주당 이익이 얼마나 빠르게 늘고 있는가. GARP은 20~50% 성장을 적정 범위로 봄 |
| **Core** | P/E | `pe_ratio` | Price / EPS (TTM) | lower_is_better | peRatioTTM | 현재 이익 대비 가격. GARP은 성장주를 사되 P/E가 업종 평균을 크게 넘지 않길 원함 |
| **Core** | 매출 성장률 (YoY) | `revenue_growth_yoy` | (올해 매출 - 전년 매출) / 전년 매출 | higher_is_better | revenueGrowth | EPS 성장이 매출 성장에 기반하는가. 매출 없이 이익만 느는 건 비용 절감이라 지속 불가능 |
| **Supporting** | ROIC | `roic` | EBIT×(1-0.21) / Invested Capital | higher_is_better | 위와 동일 | 사업이 효율적인가. 성장이 빠르더라도 돈을 잘 못 버는 구조면 주주에게 돌아올 것이 없음 |
| **Supporting** | 부채비율 (D/E) | `debt_to_equity` | Total Debt / Shareholders Equity | lower_is_better | totalDebt, totalStockholdersEquity | 성장을 위해 빚을 과도하게 지지 않았는가. 부채로 성장하면 금리 리스크에 취약 |
| **Supporting** | 매출 성장 지속성 | `revenue_growth_consistency_3y` | 최근 3년 중 매출 YoY 양수인 연수 (0~3) | higher_is_better | 3년치 revenue | 성장이 일시적인가 지속적인가. 3년 연속 성장이면 일시적 반등이 아닌 구조적 성장 |
| **Supporting** | 매출총이익률 | `gross_margin` | Gross Profit / Revenue | higher_is_better | grossProfitRatio | 매출에서 원가를 빼고 얼마나 남는가. 마진이 높아야 성장이 이익으로 전환됨 |
| **Context** | FCF Yield | `fcf_yield` | Free Cash Flow / Market Cap | higher_is_better | freeCashFlow, marketCap | 시가총액 대비 실제 현금 창출. 성장주는 낮을 수 있지만 음수면 현금을 태우고 있는 것 |
| **Context** | Beta | `beta` | | 정보 제공 | beta | 시장 대비 변동성. 성장주는 보통 Beta가 높지만 너무 높으면 하락 시 타격 큼 |
| **Context** | 시가총액 | `market_cap` | | 정보 제공 | marketCap | 기업 크기. Lynch는 모든 규모의 기업에서 기회를 찾았음 |


### 보조 속성

| metric_id | metric_group | eligible_strength | eligible_weakness | eligible_card | hard_gate | display_condition | llm_comment_style |
|---|---|---|---|---|---|---|---|
| `peg_ratio` | valuation | Y | Y | Y | Y | EPS 성장률 양수인 종목만. 음수/0 시 "PEG 산출 불가" | 철학 직접 연결 — 성장 대비 가격 핵심 |
| `eps_growth_yoy` | growth | Y | Y | Y | Y | 실적 데이터 존재 시 | 성장 존재 자체 확인 |
| `pe_ratio` | valuation | Y | Y | Y | N | 적자 시 N/A | PEG 보조로 해석. PEG와 중복 해석 주의 |
| `revenue_growth_yoy` | growth | Y | Y | Y | N | 항상 표시 | 매출 없는 이익 성장 경고 |
| `roic` | quality | Y | Y | 조건부Y | N | 금융업 별도 검토 | 성장의 자본 효율성 설명 |
| `debt_to_equity` | quality | Y | Y | 조건부Y | N | 금융업 별도 해석 | 성장 지속성의 재무 부담 관점 |
| `revenue_growth_consistency_3y` | growth | Y | Y | 조건부Y | N | 3년 데이터 필요. 부족 시 제한적 데이터 태그 | 성장 일관성 설명 |
| `gross_margin` | quality | Y | Y | 조건부Y | N | 항상 표시 | 마진 확대/축소 설명 |
| `fcf_yield` | valuation | N | N | N | N | FCF 음수 시 경고 표시 | 현금 소진 여부 맥락 |
| `beta` | risk | N | N | N | N | 가격 데이터 필요 | 별도 해설 최소 |
| `market_cap` | info | N | N | N | N | 항상 표시 | 별도 해설 최소 |

### 해설

Peter Lynch의 GARP은 "성장 투자자와 가치 투자자의 중간 지점"이다. 성장주를 사되 무한정 비싼 가격을 지불하지 않겠다는 원칙. 핵심 도구는 PEG 비율이다.

PEG = P/E ÷ EPS 성장률. 이 비율이 1이면 "성장률만큼의 프리미엄을 내고 있다"는 뜻이고, 1 이하면 "성장에 비해 싸다", 2 이상이면 "성장을 이미 주가가 반영했다"는 의미다.

GARP이 4개 Core 지표를 가진 이유는 PEG만으로는 부족하기 때문이다. PEG가 낮아도 EPS 성장이 일시적이거나, 매출 성장 없이 비용 절감으로만 EPS가 늘었으면 지속 불가능하다. 그래서 EPS 성장률, 매출 성장률, P/E를 각각 보면서 "진짜로 성장하면서 적정 가격인" 종목을 걸러낸다.

### 특이사항

- **PEG 계산에서 EPS 성장률이 음수이면 PEG가 의미 없음.** 역성장 기업은 PEG 계산 자체가 불가능. 이 경우 "PEG 산출 불가 — EPS 역성장 중" 표시. Phase 2에서 Definitional Core로 처리
- **EPS 성장률이 극단적으로 높으면(예: 500%) PEG가 0에 가까워지는 왜곡 발생.** 저이익 기저효과(전년 EPS $0.01 → 올해 $0.05 = 400% 성장)일 수 있음. EPS 성장률에 상한 캡(예: 100%)을 적용하는 것을 검토
- **Lynch는 PEG 외에도 재고 수준, 부채, 현금흐름을 중시.** 재고 급증은 매출 부진의 선행 지표. 다만 재고 데이터는 분기 재무제표에서 가져와야 하므로 MVP에서는 Supporting으로 넣지 않고, Phase 2에서 검토

### 진단 카드 예시

**카드 1: 성장 대비 가격 초과**
> 포트폴리오 내 NVDA(PEG 2.9)와 TSLA(PEG 4.8)의 PEG가 GARP 적정 범위(0.5~1.5)를 크게 초과합니다. 각각 반도체, 자동차 업종 내 하위 30%, 25%에 해당합니다.
>
> GARP의 핵심은 성장에 대해 합리적인 가격만 지불하는 것입니다. PEG가 높다는 것은 현재 주가가 향후 성장을 이미 상당 부분 반영했을 가능성을 의미합니다. 성장이 예상보다 둔화되면 주가 조정 폭이 클 수 있습니다.
>
> 다만 NVDA의 AI 인프라 독점적 위치, TSLA의 에너지 사업 확장 등 PEG에 반영되지 않는 미래 성장 옵션이 있을 수 있습니다. 이런 관점은 thesis에서 검증해보시기 바랍니다.

**카드 2: 매출 없는 이익 성장 주의**
> META의 EPS 성장률(35%)이 매출 성장률(8%)을 크게 상회합니다.
>
> GARP 관점에서 매출 성장 없는 EPS 성장은 비용 절감에 의존한 것이며, 지속 가능성이 낮습니다. 비용 절감은 한계가 있고, 결국 매출 성장이 이익 성장을 뒷받침해야 합니다.
>
> 다만 META의 경우 2022~2023년의 "효율화의 해" 이후 수익성이 구조적으로 개선되었을 수 있으며, 이 경우 비용 절감이 일회성이 아닌 영구적 효과일 수 있습니다.

### 다른 프리셋과의 차별화

| 비교 대상 | 핵심 차이 |
|---|---|
| vs Buffett | Buffett은 기업 품질(ROIC, moat)이 최우선이고 가격은 "합리적이면 OK". GARP은 가격 대비 성장(PEG)이 최우선 |
| vs Quality Growth | GARP은 "지금 성장 대비 가격이 적정한가"(현재 시점). Compounder는 "이 성장이 10년 지속되는가"(장기 시계) |
| vs Price Momentum | GARP은 펀더멘털(이익 성장) 기반. Momentum은 가격 추세 기반. GARP 종목이 모멘텀도 강하면 가장 이상적 |

---

## 4. Quality Growth / Compounder

### 코칭 질문
"이 기업이 10년간 복리로 성장할 수 있는 구조를 갖추고 있는가?"

### 지표 매트릭스

| 계층 | 지표 | metric_id | 산식 | 방향 | FMP 소스 | 투자자에게 주는 의미 |
|---|---|---|---|---|---|---|
| **Core** | ROIC | `roic` | EBIT×(1-0.21) / Invested Capital | higher_is_better | 위와 동일 | 투입 자본 대비 수익. 높으면 재투자할 때마다 높은 수익이 복리로 쌓임 — 복리 기계의 핵심 |
| **Core** | ROIC 5년 지속성 | `roic_consistency_5y` | 최근 5년 중 ROIC 15%+ 달성 연수 (0~5) | higher_is_better | 5년치 | 높은 수익률이 지속되는가. 1~2년만 좋으면 경쟁자가 따라잡을 수 있다는 뜻 |
| **Core** | FCF Yield | `fcf_yield` | Free Cash Flow / Market Cap | higher_is_better | freeCashFlow, marketCap | 실제 현금 창출 대비 현재 가격. 복리 성장의 원천은 결국 현금 |
| **Core** | FCF 재투자율 | `fcf_reinvestment_rate` | (CAPEX + R&D) / FCF | higher_is_better (적정 범위) | capitalExpenditure, researchAndDevelopmentExpenses, freeCashFlow | 번 돈을 얼마나 미래에 다시 투자하는가. 너무 낮으면 성장 의지 부족, 너무 높으면 현금 소진 |
| **Supporting** | 매출 성장 지속성 | `revenue_growth_consistency_5y` | 최근 5년 중 매출 YoY 양수인 연수 (0~5) | higher_is_better | 5년치 revenue | 매출이 꾸준히 느는가. 복리 기계는 멈추지 않고 계속 커야 함 |
| **Supporting** | 영업레버리지 | `operating_leverage` | 영업이익 성장률 / 매출 성장률 | higher_is_better | operatingIncomeGrowth, revenueGrowth | 매출이 10% 늘 때 이익이 몇 % 느는가. 1보다 크면 규모의 경제가 작동하는 증거 |
| **Supporting** | 매출총이익률 | `gross_margin` | Gross Profit / Revenue | higher_is_better | grossProfitRatio | 원가 대비 마진. 높은 마진은 가격결정력이나 차별화된 제품의 증거 |
| **Supporting** | 부채비율 (D/E) | `debt_to_equity` | Total Debt / Shareholders Equity | lower_is_better | totalDebt, totalStockholdersEquity | 빚에 의존하지 않고 자체 현금으로 성장하는가. 복리 기계는 외부 자금 없이도 성장 가능해야 |
| **Context** | P/E | `pe_ratio` | | lower_is_better | peRatioTTM | 좋은 기업은 비싸기 마련이지만, 너무 비싸면 복리 효과가 주가에 이미 반영된 것 |
| **Context** | EPS 성장률 (YoY) | `eps_growth_yoy` | | higher_is_better | epsgrowth | 올해 이익 성장. Compounder 관점에서는 올해보다 5년 추세가 더 중요 |
| **Context** | Beta | `beta` | | 정보 제공 | beta | 시장 대비 변동성. 진짜 Compounder는 시장이 흔들려도 이익이 꾸준 |


### 보조 속성

| metric_id | metric_group | eligible_strength | eligible_weakness | eligible_card | hard_gate | display_condition | llm_comment_style |
|---|---|---|---|---|---|---|---|
| `roic` | quality | Y | Y | Y | Y | 금융업 별도 검토 | 복리 기계의 핵심 — 재투자 수익률 강조 |
| `roic_consistency_5y` | quality | Y | Y | Y | Y | 상장 5년 미만 시 제한적 데이터 태그 | 지속성이 핵심 — 1~2년만 좋으면 경쟁자 추격 |
| `fcf_yield` | valuation | Y | Y | Y | N | FCF 음수 시 "현금 소진 중" 태그 | 복리 원천은 현금 |
| `fcf_reinvestment_rate` | growth | Y | Y | Y | N | FCF 음수 시 산출 불가 | 적정 범위(50~120%) 설명. 과소/과다 모두 설명 |
| `revenue_growth_consistency_5y` | growth | Y | Y | 조건부Y | N | 5년 데이터 필요 | 복리 기계 멈춤 여부 |
| `operating_leverage` | growth | Y | Y | 조건부Y | N | 매출 성장률 0/음수 시 산출 불가 | 규모의 경제 설명 |
| `gross_margin` | quality | Y | Y | 조건부Y | N | 항상 표시 | 가격결정력/차별화 설명 |
| `debt_to_equity` | quality | Y | Y | 조건부Y | N | 금융업 별도 해석 | 자체 현금 성장 강조 |
| `pe_ratio` | valuation | N | N | N | N | 적자 시 N/A | "비싸기 마련" 톤 — 과도한 경고 금지 |
| `eps_growth_yoy` | growth | N | N | N | N | 실적 데이터 필요 | 5년 추세가 더 중요하다는 맥락 |
| `beta` | risk | N | N | N | N | 가격 데이터 필요 | 별도 해설 최소 |

### 해설

Compounder 철학의 핵심은 "복리"다. ROIC가 20%인 기업이 이익의 절반을 재투자하면, 그 재투자 역시 20% 수익을 낸다. 이게 10년, 20년 반복되면 기하급수적 성장이 된다. Terry Smith의 유명한 3원칙: "좋은 기업을 사서, 과대평가하지 말고, 아무것도 하지 마라."

GARP과의 핵심 차이는 시간 시계다. GARP은 "올해 PEG가 1 이하인가?"를 묻지만, Compounder는 "이 기업이 ROIC 20%를 10년간 유지할 수 있는 구조인가?"를 묻는다. 그래서 Core 지표에 ROIC 5년 지속성, FCF 재투자율이 들어간다.

FCF 재투자율은 양날의 검이다. 너무 낮으면(30% 미만) "성장 의지가 없다. 배당이나 자사주매입으로 돌려줄 뿐, 새로운 성장 동력을 만들지 않는다"는 의미. 너무 높으면(150%+) "벌어들이는 것보다 더 많이 투자한다. 현금을 태우고 있다"는 의미. 적정 범위(50~120%)가 복리 기계의 스윗 스팟이다.

### 특이사항

- **FCF 재투자율 계산에서 FCF가 음수이면 비율이 의미 없음.** FCF 음수 기업은 "현금 소진 중" 태그 표시
- **영업레버리지 계산에서 매출 성장률이 0이거나 음수면 나눗셈 오류.** 이 경우 "산출 불가" 처리
- **CAPEX와 R&D를 합산하는 이유:** 소프트웨어 기업은 공장(CAPEX)보다 개발인력(R&D)에 투자하므로, CAPEX만 보면 투자 강도를 과소평가. 업종에 따라 R&D 비중이 매우 다름
- **5년치 데이터 필요.** ROIC 지속성, 매출 성장 지속성 모두 5년 롤링. 상장 5년 미만 기업은 가용 기간 사용 + "제한적 데이터" 태그

### 진단 카드 예시

**카드 1: 복리 구조 양호**
> MSFT의 ROIC가 5년 연속 25% 이상을 유지하고 있으며, FCF 재투자율이 65%로 적정 범위(50~120%)에 있습니다. 소프트웨어 업종 상위 15%에 해당합니다.
>
> Compounder 관점에서 높은 ROIC + 적극적 재투자 = 복리 기계가 잘 돌아가고 있다는 의미입니다. 이런 구조가 유지되면 10년간 이익이 복리로 성장할 수 있습니다.
>
> 다만 현재 P/E가 업종 상위 70%로 비싼 편이므로, 이 복리 효과의 상당 부분이 이미 주가에 반영되었을 수 있습니다.

**카드 2: 재투자율 과도**
> AMZN의 FCF 재투자율이 185%로 적정 범위(50~120%)를 크게 초과합니다. 벌어들이는 현금보다 더 많이 투자하고 있습니다.
>
> Compounder는 자체 현금으로 성장할 수 있어야 합니다. 재투자율이 100%를 넘으면 외부 자금(부채 또는 증자)에 의존하는 것이며, 이는 복리 구조의 지속 가능성에 의문을 제기합니다.
>
> 다만 AMZN의 경우 AWS 인프라 등 대규모 선제 투자가 장기적으로 높은 ROIC를 만들어낼 수 있으며, 이 투자 사이클이 끝나면 FCF가 크게 개선될 수 있습니다.

### 다른 프리셋과의 차별화

| 비교 대상 | 핵심 차이 |
|---|---|
| vs Buffett | Buffett은 현재 상태(moat 있는가, 이익 일관적인가). Compounder는 미래 구조(복리로 10년 갈 수 있는가) |
| vs GARP | GARP은 현재 시점의 가격 적정성(PEG). Compounder는 장기 지속 가능성(ROIC 지속성, 재투자율) |
| vs Quality Factor | Quality Factor는 방어적 관점(위기 때 버티는가). Compounder는 공격적 관점(복리로 성장하는가) |

---

## 5. Dividend Growth

### 코칭 질문
"이 기업이 앞으로도 배당을 올릴 수 있는 체력이 있는가?"

### 지표 매트릭스

| 계층 | 지표 | metric_id | 산식 | 방향 | FMP 소스 | 투자자에게 주는 의미 |
|---|---|---|---|---|---|---|
| **Core** | 배당성장률 (5년 CAGR) | `dividend_growth_5y` | 5년간 배당금 연평균 성장률 | higher_is_better | dividendHistory (5년치) | 배당이 매년 얼마나 빠르게 늘고 있는가. 5~15%면 양호. 장기 보유 시 원금 대비 수익률이 복리로 증가 |
| **Core** | 배당성향 | `payout_ratio` | Dividend per Share / EPS | lower_is_better (적정 범위) | payoutRatio | 이익의 몇 %를 배당으로 주는가. 60% 이하가 건강. 80%+면 이익 감소 시 배당 삭감 위험 |
| **Core** | 배당 연속 인상 연수 | `dividend_streak_years` | 연속으로 배당을 올린 연수 | higher_is_better | dividendHistory | 몇 년 연속 배당을 올렸는가. 10년+이면 경영진의 배당 의지가 강한 증거. 25년+이면 Aristocrat |
| **Core** | FCF 대비 배당 커버리지 | `fcf_dividend_coverage` | FCF / Total Dividends Paid | higher_is_better | freeCashFlow, dividendsPaid | 실제 현금흐름으로 배당을 충분히 감당할 수 있는가. 1.5배 이상이 안전. 1배 미만이면 빚으로 배당하는 것 |
| **Supporting** | 배당수익률 | `dividend_yield` | Annual Dividend / Price | higher_is_better | dividendYield | 현재 주가 대비 연간 배당. 현재 받는 현금 수익률. 2~4%가 배당 성장주의 전형적 범위 |
| **Supporting** | EPS 성장률 (YoY) | `eps_growth_yoy` | | higher_is_better | epsgrowth | 이익이 느는가. 배당은 결국 이익에서 나오므로 이익 성장 없는 배당 성장은 지속 불가 |
| **Supporting** | 부채비율 (D/E) | `debt_to_equity` | | lower_is_better | totalDebt, totalStockholdersEquity | 부채가 낮아야 이자 부담이 적고 배당 지속 여력이 높음 |
| **Supporting** | ROE | `roe` | | higher_is_better | netIncome, totalStockholdersEquity | 수익성이 높아야 배당 성장을 뒷받침할 이익 기반이 있음 |
| **Context** | P/E | `pe_ratio` | | lower_is_better | peRatioTTM | 배당주가 너무 비싸면 배당수익률이 낮아지고 시세차익도 제한적 |
| **Context** | Beta | `beta` | | 정보 제공 | beta | 배당주는 보통 Beta가 낮아 하락장에서 방어력이 있음. Beta가 높으면 배당주답지 않은 변동성 |
| **Context** | 시가총액 | `market_cap` | | 정보 제공 | marketCap | 대형주일수록 배당 안정성이 높은 경향 |


### 보조 속성

| metric_id | metric_group | eligible_strength | eligible_weakness | eligible_card | hard_gate | display_condition | llm_comment_style |
|---|---|---|---|---|---|---|---|
| `dividend_growth_5y` | income | Y | Y | Y | Y | 배당 지급 기업만. 5년 이력 필요 | 철학 직접 연결 — 배당 성장이 핵심 |
| `payout_ratio` | income | Y | Y | Y | N | 적자 시 해석 불가. 배당 지급 기업만 | 지속 가능성 관점. 업종별 적정 범위 다름 주의 |
| `dividend_streak_years` | income | Y | Y | Y | Y | 배당 지급 기업만 | 경영진 의지 + 사업 안정성 증거 |
| `fcf_dividend_coverage` | income | Y | Y | Y | Y | FCF/배당 데이터 필요. 무배당 시 N/A | 현금 기반 지속 가능성 — 1배 미만 경고 |
| `dividend_yield` | income | Y | Y | 조건부Y | N | 무배당 시 0% 표시 | 현재 인컴 수준. 과도한 강조 금지 — 이 프리셋 핵심은 "성장" |
| `eps_growth_yoy` | growth | Y | Y | 조건부Y | N | 실적 데이터 필요 | 배당 원천인 이익 성장 설명 |
| `debt_to_equity` | quality | Y | Y | 조건부Y | N | 금융업 별도 해석 | 배당 여력 관점 |
| `roe` | quality | Y | Y | 조건부Y | N | 자본 음수 시 N/A | 배당 뒷받침 수익성 설명 |
| `pe_ratio` | valuation | N | N | N | N | 적자 시 N/A | 배당주 밸류에이션 맥락 |
| `beta` | risk | N | N | N | N | 가격 데이터 필요 | 배당주의 방어력 맥락 |
| `market_cap` | info | N | N | N | N | 항상 표시 | 별도 해설 최소 |

### 해설

Dividend Growth의 핵심은 "배당수익률"이 아니라 "배당성장률"이다. 현재 배당수익률이 2%여도 매년 10%씩 배당을 올리면, 10년 후에는 원금 대비 5.2%의 배당을 받게 된다(Yield on Cost). 이것이 배당 성장 투자의 복리 효과다.

배당성향(Payout Ratio)이 Core인 이유는 배당 지속 가능성의 핵심 지표이기 때문이다. 이익의 80%를 배당으로 주면 이익이 조금만 줄어도 배당을 삭감해야 한다. 반면 40%만 주면 이익이 반토막 나도 배당은 유지할 수 있다.

FCF 대비 배당 커버리지는 배당성향과 다른 관점을 제공한다. 배당성향은 회계상 이익 기준이지만, FCF 커버리지는 실제 현금 기준이다. 회계 이익은 있는데 현금이 안 들어오는 기업은 배당성향이 낮아도 배당을 유지하기 어렵다.

### 특이사항

- **무배당 기업이 이 프리셋에 포함되면 Core 지표 전부가 0 또는 산출 불가.** MVP에서는 극저점 + "이 프리셋과의 적합성이 낮습니다" UI 표시. Phase 2에서 Definitional Core 처리
- **배당 연속 인상 연수 데이터는 FMP의 dividend history에서 계산해야 함.** 배당 삭감 후 재개한 경우 연속 인상이 끊김. 이력 데이터의 정확성에 의존
- **배당성향이 음수(적자 기업)이면 해석 불가.** "적자 중에도 배당을 유지"하는 기업은 배당성향이 의미 없으므로 FCF 커버리지로 대체 판단
- **REIT, MLP 등은 배당성향이 구조적으로 90%+.** 업종 특성상 높은 배당성향이 정상인 경우가 있음. 산업 대비 퍼센타일을 쓰므로 업종 내에서는 공정하게 비교됨

### 진단 카드 예시

**카드 1: 배당 성장 여력 양호**
> KO의 배당 연속 인상 62년, 배당성장률(5년 CAGR) 3.5%, 배당성향 72%. 필수소비재 업종 내 배당 연속 인상 연수 상위 5%입니다.
>
> Dividend Growth 관점에서 62년 연속 인상은 경영진의 배당 의지와 사업 안정성을 극도로 강하게 보여줍니다.
>
> 다만 배당성장률 3.5%는 업종 평균(6%) 대비 낮은 편이며, 배당성향 72%로 추가 인상 여력이 제한적입니다. 이익 성장 없이 배당성장률을 높이기 어려운 구조입니다.

**카드 2: FCF 커버리지 부족 경고**
> INTC의 FCF 대비 배당 커버리지가 0.6배로, 벌어들이는 현금보다 배당으로 나가는 돈이 더 많습니다. 반도체 업종 내 하위 10%입니다.
>
> Dividend Growth에서 FCF 커버리지 1배 미만은 빚을 내서 배당하는 것과 같습니다. 이 상태가 지속되면 배당 삭감이 불가피합니다.
>
> 다만 INTC가 현재 대규모 설비 투자(파운드리 사업 진출) 중이라 CAPEX가 일시적으로 높을 수 있습니다. 투자 사이클이 끝나면 FCF가 회복될 가능성이 있으나, 그 전까지 배당 지속성은 불확실합니다.

### 다른 프리셋과의 차별화

| 비교 대상 | 핵심 차이 |
|---|---|
| vs Shareholder Yield | Dividend Growth는 배당 인상 이력과 지속 가능성 중심. Shareholder Yield는 배당+자사주+부채상환의 총합 |
| vs Buffett | Buffett은 배당보다 재투자를 선호("배당은 경영진이 돈 쓸 곳을 못 찾았다는 뜻"). Dividend Growth는 배당 자체가 목적 |
| vs Quality Factor | Quality Factor는 재무 건전성 중심. Dividend Growth는 배당 체력 중심. 겹치는 부분(부채, ROE)이 있지만 핵심 질문이 다름 |

---

## 6. Shareholder Yield

### 코칭 질문
"이 기업이 배당, 자사주매입, 부채 상환을 통해 주주에게 얼마나 돌려주고 있는가?"

### 지표 매트릭스

| 계층 | 지표 | metric_id | 산식 | 방향 | FMP 소스 | 투자자에게 주는 의미 |
|---|---|---|---|---|---|---|
| **Core** | 총주주환원율 | `shareholder_yield` | 배당수익률 + 순자사주매입률 + 순부채감소율 | higher_is_better | 아래 세 항목 합산 | 배당+자사주매입+부채상환을 합친 전체 주주환원. 배당만 보면 놓치는 Apple, Alphabet 같은 기업도 포착 |
| **Core** | 배당수익률 | `dividend_yield` | Annual Dividend / Price | higher_is_better | dividendYield | 직접적인 현금 배당. 총주주환원의 첫 번째 축 |
| **Core** | 순자사주매입률 | `net_buyback_yield` | (전년 발행주식수 - 금년) / 전년 발행주식수 | higher_is_better | weightedAverageShsOut (2년치) | 자기 주식을 사서 소각하는 비율. 스톡옵션으로 희석한 걸 제외한 "순" 매입이 중요 |
| **Core** | 순부채감소율 | `net_debt_reduction_rate` | (전년 순부채 - 금년 순부채) / 전년 시가총액 | higher_is_better | totalDebt, cashAndCashEquivalents, marketCap (2년치) | 빚을 갚아서 기업 가치를 높이는 행위. 부채 감소는 간접적으로 주주 가치를 올림 |
| **Supporting** | FCF 마진 | `fcf_margin` | Free Cash Flow / Revenue | higher_is_better | freeCashFlow, revenue | 주주환원의 원천. FCF가 풍부해야 배당+매입+부채상환을 동시에 할 여력이 있음 |
| **Supporting** | 배당성향 | `payout_ratio` | Dividend / EPS | lower_is_better (적정 범위) | payoutRatio | 이익 대비 배당 비중. 너무 높으면 자사주매입이나 재투자 여력이 부족 |
| **Supporting** | EPS 성장률 (YoY) | `eps_growth_yoy` | | higher_is_better | epsgrowth | 이익이 느는가. 이익 성장 없이 주주환원만 높으면 결국 지속 불가 |
| **Supporting** | ROIC | `roic` | | higher_is_better | 위와 동일 | 사업 효율성. 주주환원보다 사업 재투자가 더 나은 수익을 낼 수 있다면 환원보다 재투자가 맞음 |
| **Context** | P/E | `pe_ratio` | | lower_is_better | peRatioTTM | 밸류에이션. 주주환원이 높아도 너무 비싸면 투자 매력 감소 |
| **Context** | 부채비율 (D/E) | `debt_to_equity` | | lower_is_better | totalDebt, totalStockholdersEquity | 전체 부채 수준. 부채감소율이 높아도 절대 수준이 과도하면 아직 갈 길이 먼 것 |
| **Context** | 시가총액 | `market_cap` | | 정보 제공 | marketCap | 대형 성숙 기업일수록 주주환원 성향이 강한 경향 |


### 보조 속성

| metric_id | metric_group | eligible_strength | eligible_weakness | eligible_card | hard_gate | display_condition | llm_comment_style |
|---|---|---|---|---|---|---|---|
| `shareholder_yield` | income | Y | Y | Y | N | 항상 표시 (0%도 의미 있음) | 철학 직접 연결 — 총환원 관점 |
| `dividend_yield` | income | Y | Y | Y | N | 무배당 시 0% 표시 | 총환원의 첫 번째 축 |
| `net_buyback_yield` | income | Y | Y | Y | N | 항상 표시. 음수면 순희석 | "순" 매입 강조. 스톡옵션 희석 설명 필요 |
| `net_debt_reduction_rate` | income | Y | Y | Y | N | 2년치 데이터 필요 | 간접 환원 설명. 음수(부채 증가) 해석도 필요 |
| `fcf_margin` | quality | Y | Y | 조건부Y | N | FCF 음수 시 경고 | 환원 원천 설명 |
| `payout_ratio` | income | Y | Y | 조건부Y | N | 적자/무배당 시 N/A | 환원 여력 관점 |
| `eps_growth_yoy` | growth | Y | Y | 조건부Y | N | 실적 데이터 필요 | 환원 지속 가능성 설명 |
| `roic` | quality | Y | Y | 조건부Y | N | 금융업 별도 검토 | 재투자 vs 환원 트레이드오프 설명 |
| `pe_ratio` | valuation | N | N | N | N | 적자 시 N/A | 수치만 노출 |
| `debt_to_equity` | quality | N | N | N | N | 금융업 별도 해석 | 부채감소율과 절대 수준 맥락 |
| `market_cap` | info | N | N | N | N | 항상 표시 | 별도 해설 최소 |

### 해설

Meb Faber의 연구에 따르면 총주주환원율(Shareholder Yield)이 단순 배당수익률보다 미래 수익률 예측력이 높다. 이유는 명확하다 — 배당만 보면 Apple 같은 기업을 놓친다. Apple은 배당수익률이 0.5%에 불과하지만, 연간 수백억 달러의 자사주를 매입한다. 이건 EPS를 높이고 주당 가치를 올리는 강력한 주주환원이다.

"순" 자사주매입이 중요한 이유: 많은 기업이 자사주를 매입하면서 동시에 경영진/직원에게 스톡옵션을 부여한다. 총매입 100억 달러인데 스톡옵션으로 80억 달러어치 신주가 발행되면 순매입은 20억에 불과하다. 순자사주매입률은 이 희석을 반영한 실질적 환원을 보여준다.

순부채감소율은 가장 간접적인 주주환원이지만 실제로는 강력하다. 부채를 갚으면 이자 비용이 줄고, 기업의 위험이 감소하고, 자기자본의 가치가 올라간다.

### 특이사항

- **순부채감소율이 음수(부채 증가)인 경우가 많음.** 많은 기업이 저금리 시대에 부채를 늘려 자사주매입에 사용했음. 이 경우 순부채감소율은 음수이지만 자사주매입률이 그것을 상쇄할 수 있음. 총주주환원율의 합산을 보는 것이 중요
- **스톡옵션 희석이 큰 기술 기업에서 순자사주매입률이 낮거나 음수일 수 있음.** 매입은 많이 하는데 발행도 많으면 순매입이 적음. 이건 주주환원의 효율성 문제
- **2년치 데이터 필요.** 발행주식수 변화, 순부채 변화 모두 전년 대비. 결측 시 해당 항목 "산출 불가"
- **ROIC를 Supporting에 넣은 이유:** 주주환원보다 사업 재투자가 더 높은 수익을 낼 수 있다면, 환원을 줄이고 재투자하는 것이 주주에게 더 유리. 이 트레이드오프를 코칭해야 함

### 진단 카드 예시

**카드 1: 총주주환원 우수**
> AAPL의 총주주환원율이 7.2%(배당 0.5% + 순자사주매입 5.8% + 순부채감소 0.9%)로 기술 업종 상위 8%입니다.
>
> Shareholder Yield 관점에서 배당수익률만 보면 0.5%로 매력 없어 보이지만, 실제로는 연간 수백억 달러를 주주에게 환원하고 있습니다. 자사주매입은 EPS를 높이고 주당 가치를 올리는 강력한 환원 방식입니다.
>
> 다만 AAPL의 자사주매입 자금 일부가 부채 조달인 점은 참고해야 합니다. 금리 상승 시 이 전략의 효율성이 떨어질 수 있습니다.

**카드 2: 스톡옵션 희석 주의**
> META의 총자사주매입은 연간 $40B이지만, 스톡옵션으로 인한 신주 발행이 $12B 수준이어서 순자사주매입률은 4.1%입니다.
>
> Shareholder Yield는 "순" 매입을 봅니다. 한 손으로 주고 다른 손으로 빼가는 구조는 실질적 주주환원이 줄어듭니다.
>
> 다만 스톡옵션은 핵심 인력 유지를 위한 비용으로 볼 수도 있으며, 이 인력이 만들어내는 가치가 희석 비용을 상쇄한다면 합리적 트레이드오프일 수 있습니다.

### 다른 프리셋과의 차별화

| 비교 대상 | 핵심 차이 |
|---|---|
| vs Dividend Growth | Dividend Growth는 배당 인상 이력과 지속 가능성. Shareholder Yield는 배당+자사주+부채의 총합. 무배당 기업도 평가 가능 |
| vs Buffett | Buffett도 자사주매입을 중시하지만 Core가 아닌 Supporting. Shareholder Yield는 환원 자체가 Core |

---

## 7. Quality Factor

### 코칭 질문
"시장이 흔들릴 때 이 포트폴리오가 버틸 수 있는 체력이 있는가?"

### 지표 매트릭스

| 계층 | 지표 | metric_id | 산식 | 방향 | FMP 소스 | 투자자에게 주는 의미 |
|---|---|---|---|---|---|---|
| **Core** | ROE 안정성 | `roe_stability_5y` | 5년간 ROE의 표준편차 (낮을수록 안정) | lower_is_better | 5년치 netIncome, equity | 수익성이 얼마나 일정한가. 변동이 크면 사업이 경기에 취약하다는 신호 |
| **Core** | 매출총이익률 | `gross_margin` | Gross Profit / Revenue | higher_is_better | grossProfitRatio | 원가 대비 마진. 마진이 높으면 가격을 올릴 수 있는 힘(pricing power)이 있다는 증거 |
| **Core** | 이익 변동성 | `earnings_volatility_5y` | 5년간 EPS의 변동계수 (표준편차/평균) | lower_is_better | 5년치 EPS | 이익이 얼마나 들쭉날쭉한가. 변동성이 낮으면 예측 가능하고 방어적 |
| **Core** | 부채비율 (D/E) | `debt_to_equity` | Total Debt / Shareholders Equity | lower_is_better | totalDebt, totalStockholdersEquity | 부채가 적을수록 금리 인상이나 경기 침체에 강함. Quality의 핵심 조건 |
| **Supporting** | ROE | `roe` | Net Income / Equity | higher_is_better | netIncome, totalStockholdersEquity | 수익성의 절대 수준. 안정적이면서 높아야 진짜 Quality |
| **Supporting** | 발생주의 비율 | `accrual_ratio` | (Net Income - Operating CF) / Total Assets | lower_is_better | netIncome, operatingCashFlow, totalAssets | 이익이 현금으로 뒷받침되는가. 높으면 이익의 질이 낮다는 경고(분식 위험) |
| **Supporting** | 이자보상배율 | `interest_coverage` | EBIT / Interest Expense | higher_is_better | operatingIncome, interestExpense | 이자 비용을 이익으로 몇 배나 커버하는가. 3배 이상이면 안전. 1배 미만이면 이자도 못 내는 상태 |
| **Supporting** | FCF 마진 | `fcf_margin` | FCF / Revenue | higher_is_better | freeCashFlow, revenue | 매출에서 진짜 현금이 얼마나 남는가. Quality 기업은 FCF 마진이 높고 안정적 |
| **Context** | P/E | `pe_ratio` | | lower_is_better | peRatioTTM | Quality 프리미엄이 주가에 얼마나 반영됐는가 |
| **Context** | Beta | `beta` | | lower_is_better | beta | Quality 기업은 보통 Beta가 낮음. 높으면 "질 좋은데 변동 큰" 특이 케이스 |
| **Context** | 배당수익률 | `dividend_yield` | | higher_is_better | dividendYield | Quality 기업은 종종 안정적 배당도 제공 |


### 보조 속성

| metric_id | metric_group | eligible_strength | eligible_weakness | eligible_card | hard_gate | display_condition | llm_comment_style |
|---|---|---|---|---|---|---|---|
| `roe_stability_5y` | quality | Y | Y | Y | N | 5년 데이터 필요 | 안정성이 핵심 — 수준보다 변동 강조 |
| `gross_margin` | quality | Y | Y | Y | N | 항상 표시 | 가격결정력(pricing power) 관점 |
| `earnings_volatility_5y` | quality | Y | Y | Y | N | 5년 데이터 필요 | 예측 가능성 + 방어력 설명 |
| `debt_to_equity` | quality | Y | Y | Y | N | 금융업 별도 해석 | 위기 버틸 체력 |
| `roe` | quality | Y | Y | 조건부Y | N | 자본 음수 시 N/A | 안정적이면서 높아야 진짜 Quality |
| `accrual_ratio` | quality | Y | Y | 조건부Y | N | CF/NI 데이터 필요 | 이익의 질 경고. 분식 위험 맥락 |
| `interest_coverage` | quality | Y | Y | 조건부Y | N | 이자비용 0 시 "무차입" 표시 (최고 레벨) | 이자 감당 능력 설명 |
| `fcf_margin` | quality | Y | Y | 조건부Y | N | FCF 음수 시 경고 | 진짜 현금 창출 강조 |
| `pe_ratio` | valuation | N | N | N | N | 적자 시 N/A | Quality 프리미엄 맥락 |
| `beta` | risk | N | N | N | N | 가격 데이터 필요 | Quality 기업은 보통 Beta 낮음 맥락 |
| `dividend_yield` | income | N | N | N | N | 무배당 시 0% | 안정적 배당 맥락 |

### 해설

Quality Factor는 학술 연구(AQR, MSCI)에서 나온 팩터다. 핵심 발견은 "수익성이 높고 안정적이며 재무가 건전한 기업이 장기적으로, 특히 시장 하락기에 아웃퍼폼한다"는 것이다.

이 프리셋이 Buffett과 다른 점은 순수 정량적이라는 것이다. Buffett은 moat, 경영진, 비즈니스 모델의 이해 가능성 같은 질적 판단을 포함하지만, Quality Factor는 ROE 안정성, 이익 변동성, 부채비율 같은 숫자만 본다. "이 기업이 왜 좋은지"는 묻지 않고 "숫자상으로 좋은가"만 판단한다.

ROE의 절대 수준(높은가)보다 안정성(일정한가)을 Core로 놓은 이유: Quality의 핵심 가치는 방어력이다. ROE가 30%였다가 5%로 떨어지는 기업보다, 15%를 꾸준히 유지하는 기업이 Quality 관점에서 더 높은 평가를 받는다.

### 특이사항

- **5년치 데이터 필요.** ROE 안정성, 이익 변동성 모두 5년 표준편차. 변동계수(CV = 표준편차/평균)를 쓰는 이유: 평균 이익이 큰 기업과 작은 기업의 변동성을 공정하게 비교하기 위함
- **이자보상배율에서 Interest Expense가 0인 기업(무차입).** 이 경우 이자보상배율은 무한대. "해당 없음 — 무차입" 표시. 무차입 자체가 Quality의 강점이므로 최고 레벨로 처리
- **발생주의 비율(Accrual Ratio)은 이익 조작 감지 지표.** 이익과 현금흐름의 괴리가 크면 경영진이 회계적 수법으로 이익을 부풀렸을 가능성. 다만 성장 기업은 매출 증가로 운전자본이 늘어나 일시적으로 발생주의 비율이 높을 수 있음

### 진단 카드 예시

**카드 1: 이익 안정성 우수**
> 포트폴리오 5개 종목 중 4개가 이익 변동성(CV) 업종 상위 30% 이내입니다. 전반적으로 예측 가능한 이익 흐름을 가진 종목으로 구성되어 있습니다.
>
> Quality 관점에서 이익이 안정적인 포트폴리오는 시장 하락기에 방어력이 우수합니다. 이익 예측이 가능하면 내재가치 추정도 안정적이어서, 급격한 밸류에이션 조정을 받을 확률이 낮습니다.

**카드 2: 발생주의 비율 주의**
> TSLA의 발생주의 비율이 업종 내 하위 20%에 해당합니다. 순이익 대비 영업현금흐름이 낮아 이익의 질에 대한 점검이 필요합니다.
>
> Quality Factor에서 발생주의 비율이 높으면 이익이 현금으로 충분히 뒷받침되지 않는다는 의미입니다. 이는 공격적 수익 인식, 운전자본 증가, 또는 비현금성 항목의 영향일 수 있습니다.
>
> 다만 TSLA의 경우 급격한 매출 성장에 따른 운전자본(재고, 매출채권) 증가가 원인일 수 있으며, 성장이 안정화되면 현금흐름이 개선될 수 있습니다.

### 다른 프리셋과의 차별화

| 비교 대상 | 핵심 차이 |
|---|---|
| vs Buffett | Buffett은 질적 판단(moat, 경영진) 포함. Quality Factor는 순수 정량. Buffett은 공격적(좋은 기업을 사자), Quality Factor는 방어적(위기에 버티자) |
| vs Low Volatility | Quality Factor는 펀더멘털 기반(재무 건전성). Low Volatility는 가격 기반(변동성, Beta). 둘 다 방어적이지만 보는 데이터가 다름 |
| vs Piotroski | Piotroski는 "개선 방향". Quality Factor는 "현재 수준". Piotroski는 가치주 필터, Quality Factor는 방어적 포트폴리오 구축 |

---

## 8. Low Volatility

### 코칭 질문
"이 포트폴리오가 시장 하락 시 얼마나 방어적인가, 어떤 종목이 위험을 끌어올리는가?"

### 지표 매트릭스

| 계층 | 지표 | metric_id | 산식 | 방향 | FMP 소스 | 투자자에게 주는 의미 |
|---|---|---|---|---|---|---|
| **Core** | Beta | `beta` | 시장 대비 민감도 (1년) | lower_is_better | beta | 시장이 10% 빠질 때 이 종목은 몇 % 빠지는가. 0.7이면 7%만 빠짐. 1.3이면 13% 빠짐 |
| **Core** | 변동성 (연환산) | `volatility_1y` | 일간 수익률의 연환산 표준편차 | lower_is_better | 1년 일간 가격 데이터 계산 | 주가가 얼마나 크게 흔들리는가. 낮을수록 안정적. 밤에 잠 못 자게 만드는 수준인가를 나타냄 |
| **Core** | 하방편차 (Downside Deviation) | `downside_deviation` | 음수 수익률만의 표준편차 | lower_is_better | 1년 일간 가격 데이터 계산 | 하락할 때만 따로 본 변동성. 상승 변동은 좋은 거니까 빼고, 순수하게 "얼마나 아프게 빠지는가" |
| **Core** | MDD (최대낙폭) | `max_drawdown_1y` | 최근 1년 최고점 대비 최대 하락폭 | lower_is_better | 1년 일간 가격 데이터 계산 | 최악의 순간에 얼마나 빠졌는가. -20%면 고점에서 1/5이 날아간 것. 심리적 한계를 테스트하는 지표 |
| **Supporting** | Sortino Ratio | `sortino_ratio` | (수익률 - 무위험) / 하방편차 | higher_is_better | 계산 | 하락 위험 대비 수익. Sharpe보다 정확. "좋은 변동(상승)은 벌 안 주고 나쁜 변동(하락)만 벌 주는" 지표 |
| **Supporting** | Sharpe Ratio | `sharpe_ratio` | (수익률 - 무위험) / 표준편차 | higher_is_better | 계산 | 총 위험 대비 수익. 1 이상이면 위험을 감수할 만한 보상이 있다는 의미 |
| **Supporting** | 종목 간 상관관계 평균 | `avg_correlation` | 포트폴리오 내 종목 쌍의 가격 상관관계 평균 | lower_is_better | 가격 데이터 매트릭스 계산 | 종목들이 같이 움직이는가 따로 움직이는가. 높으면 분산 효과 없이 동반 하락 위험 |
| **Supporting** | 리스크 기여도 최대값 | `max_risk_contribution` | 가장 큰 리스크 기여 종목의 기여 비율 | lower_is_better | 비중 + 공분산 매트릭스 계산 | 한 종목이 포트폴리오 전체 위험의 몇 %를 차지하는가. 비중 15%인데 리스크 기여 40%면 구조적 문제 |
| **Context** | 배당수익률 | `dividend_yield` | | higher_is_better | dividendYield | 저변동성 종목은 종종 안정적 배당 제공. 하락장에서 배당이 쿠션 역할 |
| **Context** | ROE | `roe` | | higher_is_better | netIncome, equity | 낮은 변동성이 낮은 수익을 의미하는 건 아닌지 확인. 수익성도 괜찮아야 진짜 좋은 저변동성 |
| **Context** | P/E | `pe_ratio` | | lower_is_better | peRatioTTM | 안정적인 종목이 너무 비싸지 않은지 확인 |


### 보조 속성

| metric_id | metric_group | eligible_strength | eligible_weakness | eligible_card | hard_gate | display_condition | llm_comment_style |
|---|---|---|---|---|---|---|---|
| `beta` | risk | Y | Y | Y | N | 가격 데이터 필요 | 시장 민감도 직접 설명 |
| `volatility_1y` | risk | Y | Y | Y | N | 1년 일간 가격 데이터 필요 | 흔들림 정도 직관적 설명 |
| `downside_deviation` | risk | Y | Y | Y | N | 1년 일간 가격 데이터 필요 | PMPT 개념 — 하락만 따로 본 위험 |
| `max_drawdown_1y` | risk | Y | Y | Y | N | 1년 가격 데이터 필요 | 최악 시나리오 — 심리적 한계 테스트 |
| `sortino_ratio` | risk | Y | Y | 조건부Y | N | 무위험수익률 + 가격 데이터 필요 | Sharpe보다 정확한 위험 조정 수익 |
| `sharpe_ratio` | risk | Y | Y | 조건부Y | N | 무위험수익률 + 가격 데이터 필요 | 총 위험 대비 보상 |
| `avg_correlation` | risk | Y | Y | 조건부Y | N | 종목 2개 이상 필요 | 분산 효과 유무 — 동반 하락 위험 |
| `max_risk_contribution` | risk | Y | Y | 조건부Y | N | 종목 2개 이상 + 공분산 계산 필요 | 리스크 집중도 — Risk Parity 관점 |
| `dividend_yield` | income | N | N | N | N | 무배당 시 0% | 하락장 쿠션 맥락 |
| `roe` | quality | N | N | N | N | 자본 음수 시 N/A | 저변동성 ≠ 저수익 확인 |
| `pe_ratio` | valuation | N | N | N | N | 적자 시 N/A | 안정적 종목의 밸류에이션 맥락 |

### 해설

Low Volatility는 12개 프리셋 중 **유일하게 가격 데이터 중심**인 프리셋이다. 나머지 프리셋이 "이 기업이 좋은가?"(펀더멘털)를 묻는다면, Low Volatility는 "이 종목 조합이 안정적인가?"(가격 행동)를 묻는다.

이 프리셋이 MVP에서 반드시 필요한 이유는, 설계서에서 1순위로 반영하기로 한 포트폴리오 이론 3개(MPT, PMPT, Risk Parity)가 실제로 작동하는 곳이 바로 여기이기 때문이다:
- MPT → 종목 간 상관관계
- PMPT → 하방편차, Sortino Ratio
- Risk Parity → 리스크 기여도

리스크 기여도의 실용적 가치: "NVDA가 비중 20%인데 리스크 기여도가 45%"라면, 이 포트폴리오의 위험은 사실상 NVDA 하나에 의존하는 것이다. 비중만 보면 분산되어 보이지만 위험은 집중되어 있다. 이 인사이트는 다른 프리셋에서는 나올 수 없다.

### 특이사항

- **상관관계 매트릭스 계산은 종목 수의 제곱에 비례.** 종목 50개면 1,225개 쌍. 일간 배치로 처리하되, 캐시 TTL 24시간
- **리스크 기여도 계산은 공분산 매트릭스가 필요.** 구현 난이도가 다른 프리셋보다 높음. 다만 한번 구현하면 Concentrated Portfolio 등 다른 프리셋에서도 재사용 가능
- **1년치 일간 가격 데이터 필요.** 재무제표 의존이 없어 실적 발표 지연에 영향 안 받음
- **변동성은 시장 상황에 따라 크게 변동.** 저변동성 시기(VIX 12)에는 모든 종목이 다 좋게 나오고, 고변동성 시기(VIX 35)에는 다 나쁘게 나옴. 산업 대비 퍼센타일을 쓰므로 어느 정도 보정되지만, 시장 전체 변동성 수준도 Context로 표시하면 좋음 (Phase 2)
- **Sortino Ratio, Sharpe Ratio 계산에 무위험수익률 필요.** 미국 10년 국채 수익률 또는 3개월 T-Bill 사용. FMP에서 조회 가능하거나 고정값 사용

### 진단 카드 예시

**카드 1: 리스크 기여도 불균형**
> NVDA가 포트폴리오 비중 25%이지만 리스크 기여도는 48%입니다. 반도체 업종의 높은 변동성(연환산 42%)이 원인입니다.
>
> Low Volatility 관점에서 한 종목이 포트폴리오 전체 위험의 절반 가까이를 차지하면, 비중은 분산되어 보여도 실질적으로는 그 종목에 의존하는 구조입니다. NVDA가 20% 하락하면 포트폴리오 전체에 약 10%의 타격이 예상됩니다.
>
> 다만 NVDA의 높은 변동성이 대부분 상승 방향이었다면(하방편차는 상대적으로 낮다면), 실제 하방 위험은 총 변동성이 시사하는 것보다 작을 수 있습니다. Sortino Ratio를 함께 확인해보세요.

**카드 2: 종목 간 상관관계 과다**
> 포트폴리오 내 종목 간 평균 상관관계가 0.72로, 기술 업종 평균(0.55) 대비 높은 편입니다.
>
> 상관관계가 높으면 시장 하락 시 종목들이 동반 하락할 가능성이 큽니다. 7개 종목을 들고 있지만 실질적인 분산 효과가 제한적입니다.
>
> 이는 포트폴리오가 AI 인프라 테마에 집중되어 있기 때문일 수 있습니다. 다른 테마나 섹터의 종목을 추가하면 상관관계가 낮아지고 분산 효과가 개선될 수 있습니다.

### 다른 프리셋과의 차별화

| 비교 대상 | 핵심 차이 |
|---|---|
| vs Quality Factor | Quality Factor는 펀더멘털 건전성(재무제표). Low Volatility는 가격 행동(변동성, 상관관계). 둘 다 방어적이지만 보는 데이터가 완전히 다름 |
| vs Concentrated Portfolio | Concentrated Portfolio는 "얼마나 집중했나"(비중 구조). Low Volatility는 "그 집중이 얼마나 위험한가"(리스크 구조). 보완적 관계 |
| vs 나머지 모든 프리셋 | 유일하게 재무제표를 Core로 사용하지 않는 프리셋. 순수 가격/포트폴리오 구조 관점 |

---

## 9. Price Momentum

### 코칭 질문
"시장의 상승 흐름에 올라타고 있는 종목이 얼마나 되는가?"

### 지표 매트릭스

| 계층 | 지표 | metric_id | 산식 | 방향 | FMP 소스 | 투자자에게 주는 의미 |
|---|---|---|---|---|---|---|
| **Core** | 12개월 수익률 | `return_12m` | (현재가 - 12개월 전 가격) / 12개월 전 가격 | higher_is_better | 가격 데이터 계산 | 최근 1년간 얼마나 올랐는가. 모멘텀의 핵심. 상위 20%면 시장에서 가장 강한 흐름에 있는 것 |
| **Core** | 6개월 수익률 | `return_6m` | 위와 동일 (6개월) | higher_is_better | 가격 데이터 계산 | 중기 추세. 12개월은 강한데 6개월이 약하면 추세가 꺾이고 있을 수 있다는 경고 |
| **Core** | 3개월 수익률 | `return_3m` | 위와 동일 (3개월) | higher_is_better | 가격 데이터 계산 | 단기 추세. 최근 3개월이 가속 중인지 감속 중인지. 12m > 6m > 3m이면 감속 신호 |
| **Core** | 상대강도 (RS) | `relative_strength` | 12개월 수익률의 시장 내 백분위 (0~100) | higher_is_better | 계산 | 시장 전체 종목 대비 가격 흐름이 얼마나 강한가. 80 이상이면 상위 20% 리더 |
| **Supporting** | 52주 고가 대비 | `pct_from_52w_high` | (현재가 - 52주 고가) / 52주 고가 | higher_is_better | 가격 데이터 계산 | 최고점에서 얼마나 떨어져 있는가. 고가 근처면 강한 추세. 20%+ 떨어졌으면 추세 약화 |
| **Supporting** | 거래량 변화 | `volume_change_ratio` | 최근 20일 평균 거래량 / 50일 평균 거래량 | higher_is_better | volume 데이터 계산 | 최근 거래가 활발해지고 있는가. 가격 상승 + 거래량 증가면 추세 강도 뒷받침 |
| **Supporting** | EPS 성장률 (YoY) | `eps_growth_yoy` | | higher_is_better | epsgrowth | 가격 모멘텀이 이익 성장에 기반하는가. 이익 없이 가격만 오르면 투기적 모멘텀 |
| **Context** | P/E | `pe_ratio` | | 정보 제공 | peRatioTTM | 모멘텀 강한 종목이 얼마나 비싸졌는가. 극단적 고평가면 추세 반전 시 하방 리스크 큼 |
| **Context** | Beta | `beta` | | 정보 제공 | beta | 모멘텀 종목의 시장 민감도. Beta 높으면 시장 반전 시 더 크게 빠짐 |
| **Context** | 시가총액 | `market_cap` | | 정보 제공 | marketCap | 소형주 모멘텀이 대형주보다 강한 경향이 있으나 변동성도 높음 |


### 보조 속성

| metric_id | metric_group | eligible_strength | eligible_weakness | eligible_card | hard_gate | display_condition | llm_comment_style |
|---|---|---|---|---|---|---|---|
| `return_12m` | momentum | Y | Y | Y | N | 12개월 가격 데이터 필요 | 모멘텀 핵심 — 추세 강도 |
| `return_6m` | momentum | Y | Y | Y | N | 6개월 가격 데이터 필요 | 가속/감속 판단 — 12m과 비교 |
| `return_3m` | momentum | Y | Y | Y | N | 3개월 가격 데이터 필요 | 최근 추세 — 감속 시 경고 |
| `relative_strength` | momentum | Y | Y | Y | N | 시장 전체 수익률 분포 필요 | 시장 내 위치 — 리더 vs 래거드 |
| `pct_from_52w_high` | momentum | Y | Y | 조건부Y | N | 52주 가격 데이터 필요 | 추세 강도 보조 확인 |
| `volume_change_ratio` | momentum | Y | Y | 조건부Y | N | 거래량 데이터 필요 | 추세 강도 뒷받침 — 거래량 동반 여부 |
| `eps_growth_yoy` | growth | Y | Y | 조건부Y | N | 실적 데이터 필요 | 펀더멘털 뒷받침 여부 — 투기적 모멘텀 구분 |
| `pe_ratio` | valuation | N | N | N | N | 적자 시 N/A | 모멘텀 종목 밸류에이션 맥락 |
| `beta` | risk | N | N | N | N | 가격 데이터 필요 | 추세 반전 시 하방 리스크 맥락 |
| `market_cap` | info | N | N | N | N | 항상 표시 | 소형주 모멘텀 맥락 |

### 해설

Price Momentum은 학술적으로 가장 강력하고 지속적으로 검증된 팩터 중 하나다(Jegadeesh & Titman, 1993). "최근에 올라간 종목이 앞으로도 오르는 경향"이 전세계 시장에서, 수십 년간 관찰되었다.

행동경제학적 설명: 투자자들이 좋은 뉴스에 느리게 반응하기 때문(under-reaction). 실적이 좋게 나와도 주가가 한번에 반영되지 않고 점진적으로 올라간다. 이 점진적 상승이 모멘텀이다.

3개월, 6개월, 12개월 수익률을 모두 Core로 넣은 이유는 **모멘텀의 가속/감속을 감지**하기 위해서다. 12m +50%, 6m +30%, 3m +5%면 "모멘텀이 꺾이고 있다"는 신호. 12m +20%, 6m +15%, 3m +12%면 "모멘텀이 가속 중"이라는 신호.

### 특이사항

- **Contrarian과 12개월 수익률의 방향이 정반대.** Momentum에서는 높을수록 좋고, Contrarian에서는 낮을수록(많이 빠질수록) 좋음. 같은 지표가 프리셋에 따라 정반대로 해석됨. 이게 "같은 데이터, 다른 렌즈"의 대표적 예시
- **모멘텀 크래시 리스크.** 추세가 갑자기 반전되면 모멘텀 종목이 가장 크게 빠짐. 이 리스크를 코칭에서 반드시 언급해야 함
- **EPS 성장률을 Supporting에 넣은 이유:** "이익으로 뒷받침되는 모멘텀"과 "투기적 모멘텀"을 구분하기 위함. 이익 없이 가격만 오르면 거품 위험

### 진단 카드 예시

**카드 1: 모멘텀 감속 신호**
> NVDA의 12개월 수익률 +85%이지만, 6개월 +25%, 3개월 +3%로 뚜렷한 감속세입니다.
>
> Momentum 관점에서 가속→감속 전환은 추세 약화의 초기 신호일 수 있습니다. 아직 12개월 기준으로는 강하지만, 단기 추세가 약해지면 중기 추세도 약해질 수 있습니다.
>
> 다만 이익 실적이 여전히 강하다면(EPS 성장 양호), 이 감속이 일시적 조정일 수 있으며 추세가 재가속될 가능성도 있습니다.

**카드 2: 거래량 없는 상승 주의**
> LLY의 3개월 수익률 +18%이지만 거래량은 50일 평균 대비 0.7배로 오히려 줄었습니다.
>
> 가격 상승에 거래량이 동반하지 않으면 추세의 강도가 약합니다. 소수 참여자에 의한 상승은 매물이 나오면 쉽게 되돌려질 수 있습니다.
>
> 다만 헬스케어 업종은 기관 중심 거래가 많아 거래량 변화가 덜 극적일 수 있으며, 이 업종에서는 거래량보다 기관 보유 비율 변화가 더 유의미할 수 있습니다.

### 다른 프리셋과의 차별화

| 비교 대상 | 핵심 차이 |
|---|---|
| vs Contrarian | 정반대 철학. Momentum은 "오르는 데 올라타라". Contrarian은 "빠진 데서 기회를 잡아라" |
| vs GARP | GARP은 펀더멘털(이익 성장 대비 가격). Momentum은 가격 추세 자체 |
| vs Low Volatility | Low Volatility는 "안정적인가". Momentum은 "강한가". 둘 다 가격 기반이지만 질문이 다름 |

---

## 10. Multi-Factor

### 코칭 질문
"어떤 수익 요인(팩터)에 노출되어 있고, 특정 팩터에 과도하게 쏠려있지 않은가?"

### 지표 매트릭스

| 계층 | 지표 | metric_id | 산식 | 방향 | FMP 소스 | 투자자에게 주는 의미 |
|---|---|---|---|---|---|---|
| **Core** | Value 점수 | `factor_value` | P/E + P/B + EV/EBITDA의 역수 합산 퍼센타일 | higher_is_better | peRatio, pbRatio, evToEbitda | 이 포트폴리오가 가치 팩터에 얼마나 노출되어 있는가. 높으면 싼 기업 중심 |
| **Core** | Quality 점수 | `factor_quality` | ROE 안정성 + 부채비율 역수 + 이익 변동성 역수의 퍼센타일 | higher_is_better | 위 지표들 재활용 | 퀄리티 팩터 노출. 높으면 재무 건전한 기업 중심 |
| **Core** | Momentum 점수 | `factor_momentum` | 12개월 수익률 퍼센타일 | higher_is_better | 가격 데이터 | 모멘텀 팩터 노출. 높으면 상승 추세 종목 중심 |
| **Core** | 팩터 균형도 | `factor_balance` | Value/Quality/Momentum 점수의 표준편차 (낮을수록 균형) | lower_is_better | 위 3개 합산 계산 | 특정 팩터에 쏠려있지 않은가. 균형잡힌 멀티팩터가 단일 팩터보다 안정적 |
| **Supporting** | Size 점수 | `factor_size` | 시가총액 역수 퍼센타일 (작을수록 소형주 노출) | 정보 제공 | marketCap | 소형주/대형주 편향. 소형주 프리미엄이 있지만 리스크도 높음 |
| **Supporting** | Low Vol 점수 | `factor_low_vol` | Beta 역수 퍼센타일 | higher_is_better | beta | 저변동성 팩터 노출. 높으면 방어적 구성 |
| **Supporting** | Yield 점수 | `factor_yield` | 배당수익률 + 자사주매입률 퍼센타일 | higher_is_better | dividendYield, buyback 계산 | 주주환원 팩터 노출 |
| **Context** | 포트폴리오 Beta | `portfolio_beta` | 비중 가중 평균 Beta | 정보 제공 | beta, 비중 | 포트폴리오 전체의 시장 민감도 |
| **Context** | 종목 수 | `stock_count` | | 정보 제공 | 직접 계산 | 종목이 너무 적으면 팩터 노출이 특정 기업에 좌우됨 |


### 보조 속성

| metric_id | metric_group | eligible_strength | eligible_weakness | eligible_card | hard_gate | display_condition | llm_comment_style |
|---|---|---|---|---|---|---|---|
| `factor_value` | valuation | Y | Y | Y | N | P/E, P/B, EV/EBITDA 데이터 필요 | 가치 팩터 노출도 설명 |
| `factor_quality` | quality | Y | Y | Y | N | ROE, 부채비율 등 데이터 필요 | 퀄리티 팩터 노출도 설명 |
| `factor_momentum` | momentum | Y | Y | Y | N | 12개월 수익률 데이터 필요 | 모멘텀 팩터 노출도 설명 |
| `factor_balance` | risk | Y | Y | Y | N | 위 3개 팩터 산출 필요 | 팩터 편향 경고/균형 칭찬 |
| `factor_size` | info | Y | Y | 조건부Y | N | 시가총액 데이터 필요 | 소형주/대형주 편향 설명 |
| `factor_low_vol` | risk | Y | Y | 조건부Y | N | Beta 데이터 필요 | 방어적 구성 여부 설명 |
| `factor_yield` | income | Y | Y | 조건부Y | N | 배당/매입 데이터 필요 | 주주환원 팩터 설명 |
| `portfolio_beta` | risk | N | N | N | N | Beta + 비중 데이터 필요 | 시장 민감도 맥락 |
| `stock_count` | info | N | N | N | N | 항상 표시 | 팩터 노출 신뢰도 맥락 |

### 해설

Multi-Factor는 "메타 프리셋"이다. 다른 프리셋이 각각 하나의 관점을 제공한다면, Multi-Factor는 여러 관점을 종합적으로 조망한다. "내 포트폴리오가 어떤 팩터에 기울어져 있는지"를 보여주는 X-ray 같은 역할이다.

팩터 균형도가 Core인 이유: 연구에 따르면 단일 팩터(예: Value만)는 수년간 부진할 수 있지만, 여러 팩터를 균형 있게 가져가면 부진 기간이 짧아진다. "모든 계절에 대비하는" 접근이다.

### 특이사항

- **다른 프리셋의 지표를 재활용하는 구조.** Value 점수는 Contrarian/Buffett의 P/E, P/B를 재활용. Quality 점수는 Quality Factor의 ROE 안정성, 부채비율을 재활용. Momentum 점수는 Price Momentum의 12개월 수익률을 재활용. 구현 시 이미 계산된 값을 가져오면 됨
- **팩터 점수는 포트폴리오 비중 가중 평균으로 산출.** 각 종목의 해당 지표 퍼센타일을 비중으로 가중 평균하여 포트폴리오 수준의 팩터 노출도를 산출
- **팩터 균형도 해석:** 표준편차가 낮으면 균형, 높으면 특정 팩터 편향. 예: Value 80, Quality 75, Momentum 30이면 "모멘텀 팩터 노출이 약합니다. 하락세 종목이 포함되어 있을 수 있습니다"
- **이 프리셋은 초보자보다 중급 이상 사용자에게 유용.** "팩터"라는 개념 자체가 낯설 수 있으므로, 온보딩에서는 후순위로 노출

### 진단 카드 예시

**카드 1: 모멘텀 팩터 부족**
> 포트폴리오의 Momentum 점수가 32로 Value(78), Quality(71) 대비 현저히 낮습니다. 팩터 균형도(표준편차) 25.3으로 편향이 감지됩니다.
>
> Multi-Factor 관점에서 특정 팩터에 과도하게 기울어진 포트폴리오는 해당 팩터가 부진한 시기에 크게 흔들릴 수 있습니다. 현재 구성은 Value/Quality에 강하지만 가격 추세가 약한 종목이 다수 포함되어 있습니다.
>
> 다만 이것이 반드시 나쁜 것은 아닙니다. 의도적으로 역발상(Contrarian) 관점에서 저모멘텀 종목을 보유하고 있다면, 이 팩터 불균형은 전략적 선택일 수 있습니다.

**카드 2: Value 팩터 과다 노출**
> 포트폴리오의 Value 점수가 85로 매우 높습니다. 저평가 종목 중심 구성입니다.
>
> 가치 팩터는 장기적으로 유효하지만, 성장주 강세장(2020~2021 같은)에서는 수년간 부진할 수 있습니다. Quality나 Momentum을 보완하면 단일 팩터 의존도를 줄일 수 있습니다.

### 다른 프리셋과의 차별화

| 비교 대상 | 핵심 차이 |
|---|---|
| vs 다른 모든 프리셋 | 다른 프리셋은 하나의 관점을 깊이 봄. Multi-Factor는 여러 관점의 노출도를 종합적으로 조망 |
| vs Concentrated Portfolio | Concentrated는 비중 구조. Multi-Factor는 팩터 구조. 다른 축의 분석 |

---

## 11. Contrarian

### 코칭 질문
"시장이 과잉 반응한 곳에서 기회를 잡고 있는가, 아니면 함정에 빠져 있는가?"

### 지표 매트릭스

| 계층 | 지표 | metric_id | 산식 | 방향 | FMP 소스 | 투자자에게 주는 의미 |
|---|---|---|---|---|---|---|
| **Core** | P/E (저평가 확인) | `pe_ratio` | Price / EPS | lower_is_better | peRatioTTM | 시장이 이 기업을 외면하고 있는가. 업종 하위 20% P/E면 역발상 기회일 수 있음 |
| **Core** | P/B (자산 대비 할인) | `pb_ratio` | Price / Book Value | lower_is_better | pbRatio | 자산가치보다 싸게 거래되는가. 1 이하면 시장이 이 기업을 청산가치 이하로 평가하는 것 |
| **Core** | 12개월 수익률 | `return_12m` | | lower_is_better (역발상!) | 가격 데이터 | 최근 1년 얼마나 빠졌는가. 역발상 관점에서는 많이 빠진 종목이 기회. 모멘텀과 정반대 |
| **Core** | 52주 저가 대비 | `pct_from_52w_low` | (현재가 - 52주 저가) / 52주 저가 | lower_is_better | 가격 데이터 | 바닥에서 얼마나 올라왔는가. 아직 바닥 근처면 회복 초기. 많이 올라왔으면 이미 기회 지남 |
| **Supporting** | Piotroski F-Score | `f_score_total` | 9개 항목 합산 | higher_is_better | 위와 동일 | 싸게 빠진 종목이 진짜 가치인지 함정인지 구분. F-Score 높으면 재무가 개선 중이라 회복 가능성 높음 |
| **Supporting** | FCF Yield | `fcf_yield` | FCF / Market Cap | higher_is_better | freeCashFlow, marketCap | 현금 창출 대비 얼마나 싼가. 주가는 빠졌지만 현금은 잘 벌고 있으면 과잉 반응의 증거 |
| **Supporting** | 부채비율 (D/E) | `debt_to_equity` | | lower_is_better | totalDebt, equity | 싸게 빠진 이유가 부채 때문이면 진짜 위험. 부채 낮은데 빠졌으면 과잉 반응일 가능성 높음 |
| **Supporting** | 배당수익률 | `dividend_yield` | | higher_is_better | dividendYield | 주가 하락으로 배당수익률이 비정상적으로 높아졌는가. 배당 유지 가능하면 하방 지지 역할 |
| **Context** | EPS 성장률 (YoY) | `eps_growth_yoy` | | higher_is_better | epsgrowth | 이익이 실제로 줄고 있는가. 이익 멀쩡한데 주가만 빠졌으면 역발상 기회. 이익도 빠지면 함정 위험 |
| **Context** | ROE | `roe` | | higher_is_better | netIncome, equity | 사업 자체의 수익성은 괜찮은가. 주가만 빠진 건지 사업 자체가 망가진 건지 구분 |
| **Context** | 시가총액 | `market_cap` | | 정보 제공 | marketCap | 대형주가 크게 빠지면 기관의 과잉 매도일 가능성. 소형주가 빠지면 유동성 부족일 수 있음 |


### 보조 속성

| metric_id | metric_group | eligible_strength | eligible_weakness | eligible_card | hard_gate | display_condition | llm_comment_style |
|---|---|---|---|---|---|---|---|
| `pe_ratio` | valuation | Y | Y | Y | N | 적자 시 N/A | 역발상 관점 — 낮을수록 기회 |
| `pb_ratio` | valuation | Y | Y | Y | N | 항상 표시 | 자산 대비 할인 설명 |
| `return_12m` | momentum | Y | Y | Y | N | 12개월 가격 데이터 필요 | **방향 역전!** 낮을수록 기회. 모멘텀과 정반대 |
| `pct_from_52w_low` | momentum | Y | Y | Y | N | 52주 가격 데이터 필요 | 바닥 근처 여부 — 회복 초기 포착 |
| `f_score_total` | quality | Y | Y | 조건부Y | N | 2년치 재무 데이터 필요 | 가치 함정 필터 — 재무 개선 중인지 확인 |
| `fcf_yield` | valuation | Y | Y | 조건부Y | N | FCF 데이터 필요 | 현금 창출 vs 가격 — 과잉 반응 증거 |
| `debt_to_equity` | quality | Y | Y | 조건부Y | N | 금융업 별도 해석 | 싸게 빠진 이유가 부채인지 구분 |
| `dividend_yield` | income | Y | Y | 조건부Y | N | 무배당 시 0% | 주가 하락으로 비정상 고배당인지 확인 |
| `eps_growth_yoy` | growth | N | N | N | N | 실적 데이터 필요 | 이익 감소 여부 — 함정 vs 과잉 반응 구분 |
| `roe` | quality | N | N | N | N | 자본 음수 시 N/A | 사업 자체 건전성 맥락 |
| `market_cap` | info | N | N | N | N | 항상 표시 | 대형주/소형주 과잉 매도 맥락 |

### 해설

Contrarian의 핵심은 "시장은 과잉 반응한다"는 믿음이다. 좋은 뉴스에 과도하게 올리고, 나쁜 뉴스에 과도하게 떨어뜨린다. 과도하게 떨어진 곳에서 매수하면 "정상화"만으로도 수익이 발생한다.

**Momentum과 정반대 방향이라는 점이 가장 중요한 특이사항이다.** 같은 12개월 수익률 지표가 Momentum에서는 higher_is_better이고 Contrarian에서는 lower_is_better다. "올라간 주식을 사라" vs "떨어진 주식을 사라". 사용자가 두 프리셋을 바꿔가며 같은 포트폴리오를 보면 정반대 진단이 나온다. 이것이 "같은 데이터, 다른 렌즈, 다른 코칭"의 가장 극적인 사례다.

역발상 투자의 가장 큰 위험은 **가치 함정(value trap)**이다. "싸니까 좋다"가 아니라 "싼 이유가 있다"인 경우. F-Score를 Supporting으로 넣은 이유가 이것이다. 주가가 빠졌는데 F-Score가 높으면(재무 개선 중) 과잉 반응일 가능성이 높고, F-Score도 낮으면(재무 악화 중) 정당한 하락이자 함정일 가능성이 높다.

### 특이사항

- **12개월 수익률과 52주 저가 대비의 방향이 다른 프리셋과 반대.** direction_override가 필요한 유일한 프리셋. Metric Dictionary에서 기본 방향은 higher_is_better이지만, Contrarian 프리셋에서는 역전
- **F-Score를 Supporting으로 재활용.** Piotroski 프리셋의 핵심 지표가 Contrarian에서는 보조 필터로 작동. "싸면서 개선 중인" 종목을 찾는 크로스오버 진단
- **코칭 톤이 특히 중요.** 역발상은 본질적으로 위험한 전략이므로, Coach가 "이 종목이 싸니까 좋다"가 아니라 "이 종목이 싼 이유가 과잉 반응인지 정당한 이유인지 구분해야 한다"는 톤을 유지해야 함

### 진단 카드 예시

**카드 1: 역발상 기회 가능성**
> INTC가 12개월 수익률 -35%로 반도체 업종 하위 15%이지만, F-Score 7점으로 재무 건전성은 업종 상위 30%입니다. P/B 1.2로 역사적 저점 수준입니다.
>
> Contrarian 관점에서 주가는 크게 빠졌지만 재무가 개선 중인 종목은 시장의 과잉 반응일 가능성이 있습니다. 특히 P/B가 역사적 저점이면 하방이 제한적일 수 있습니다.
>
> 다만 반도체 업계의 구조적 변화(파운드리 경쟁, AI 반도체 전환)가 INTC에 근본적 불리한 환경을 만들고 있을 수 있으며, 이 경우 저평가가 아니라 정당한 재평가일 수 있습니다. 경쟁 환경 변화에 대한 thesis를 세워보시기 바랍니다.

**카드 2: 가치 함정 경고**
> 종목X가 P/E 업종 하위 10%, 12개월 수익률 -50%이지만, F-Score 2점이며 부채비율이 업종 하위 5%입니다.
>
> Contrarian 관점에서 가격은 매우 매력적이지만, 재무 건전성이 심각하게 악화되고 있습니다. 이는 가치 함정(value trap)의 전형적 패턴입니다. 싼 데는 이유가 있을 수 있으며, 추가 하락 위험이 있습니다.
>
> 부채비율이 극도로 높고 F-Score가 낮은 종목은 회복보다 추가 악화 가능성이 더 높습니다. 명확한 회복 촉매(경영진 교체, 구조조정 계획 등)가 보이지 않으면 주의가 필요합니다.

### 다른 프리셋과의 차별화

| 비교 대상 | 핵심 차이 |
|---|---|
| vs Momentum | 정반대 철학. 같은 12개월 수익률을 반대 방향으로 해석 |
| vs Piotroski | Piotroski는 재무 개선 자체가 목적. Contrarian은 재무 개선을 가치 함정 필터로 사용 |
| vs Buffett | Buffett은 "좋은 기업을 합리적 가격에". Contrarian은 "빠진 기업에서 반등 기회를" |

---

## 12. Concentrated Portfolio

### 코칭 질문
"포트폴리오의 집중도가 의도적인 것인가, 그리고 그 집중이 구조적으로 안전한가?"

### 지표 매트릭스

| 계층 | 지표 | metric_id | 산식 | 방향 | FMP 소스 | 투자자에게 주는 의미 |
|---|---|---|---|---|---|---|
| **Core** | HHI 집중도 | `hhi_concentration` | Σ(종목 비중²) | 정보 제공 | 비중 데이터 계산 | 포트폴리오가 얼마나 집중되어 있는가. 0.1이면 분산, 0.3+이면 고도 집중 |
| **Core** | 상위 3종목 비중 합 | `top3_weight` | 비중 가장 큰 3개의 합 | 정보 제공 | 비중 데이터 | 포트폴리오의 운명이 3개 종목에 얼마나 좌우되는가. 60%+면 사실상 3종목 포트폴리오 |
| **Core** | 총 종목 수 | `stock_count` | | 정보 제공 | 직접 계산 | 몇 개 종목을 들고 있는가. 3개 이하 극단 집중, 30개+ 과도한 분산 |
| **Core** | 최대 단일 포지션 비중 | `max_position_weight` | 가장 큰 포지션의 비중 | 정보 제공 | 비중 데이터 | 한 종목에 얼마나 몰려있는가. 25%+면 그 종목이 틀리면 큰 타격 |
| **Supporting** | 섹터 집중도 | `sector_hhi` | 섹터별 비중의 HHI | 정보 제공 | FMP sector + 비중 | 종목은 달라도 같은 업종에 몰려있는가 |
| **Supporting** | 종목 간 상관관계 평균 | `avg_correlation` | 종목 쌍의 가격 상관관계 평균 | lower_is_better | 가격 데이터 매트릭스 | 종목들이 같이 움직이는가. 상관관계 높으면 분산 효과 없음 |
| **Supporting** | 포트폴리오 Beta | `portfolio_beta` | 비중 가중 평균 Beta | 정보 제공 | beta, 비중 | 집중 포트폴리오의 전체 시장 민감도 |
| **Supporting** | 리스크 기여도 최대값 | `max_risk_contribution` | 가장 큰 리스크 기여 종목의 기여 비율 | lower_is_better | 비중 + 공분산 매트릭스 | 비중 큰 종목이 리스크도 크게 차지하는가 |
| **Context** | 변동성 (포트폴리오) | `portfolio_volatility` | 포트폴리오 전체 변동성 | lower_is_better | 가격 + 비중 데이터 | 이 집중도가 실제로 만드는 변동성 |
| **Context** | 평균 시가총액 | `avg_market_cap` | 비중 가중 평균 시가총액 | 정보 제공 | marketCap | 대형주 집중인가 소형주 집중인가 |


### 보조 속성

| metric_id | metric_group | eligible_strength | eligible_weakness | eligible_card | hard_gate | display_condition | llm_comment_style |
|---|---|---|---|---|---|---|---|
| `hhi_concentration` | risk | Y | Y | Y | N | 종목 2개 이상 필요 | 집중도 정보 제공 — 경고 아닌 인식 톤 |
| `top3_weight` | risk | Y | Y | Y | N | 종목 3개 이상 필요. 3개 미만이면 100% 표시 | Munger 철학 존중 톤 |
| `stock_count` | info | Y | Y | Y | N | 항상 표시 | 집중/분산 정보 제공 — 판단은 사용자에게 |
| `max_position_weight` | risk | Y | Y | Y | N | 항상 표시 | 단일 종목 의존도 설명 — 확신 필요성 강조 |
| `sector_hhi` | risk | Y | Y | 조건부Y | N | 섹터 데이터 필요 | "같은 선반 위 바구니" 비유 |
| `avg_correlation` | risk | Y | Y | 조건부Y | N | 종목 2개 이상 + 가격 데이터 | 실질 분산 효과 설명 |
| `portfolio_beta` | risk | Y | Y | 조건부Y | N | Beta + 비중 데이터 필요 | 집중 포트폴리오의 시장 민감도 |
| `max_risk_contribution` | risk | Y | Y | 조건부Y | N | 종목 2개 이상 + 공분산 필요 | 비중 vs 실질 리스크 괴리 설명 |
| `portfolio_volatility` | risk | N | N | N | N | 가격 + 비중 데이터 필요 | 집중도가 만드는 변동성 맥락 |
| `avg_market_cap` | info | N | N | N | N | 시가총액 데이터 필요 | 대형주/소형주 집중 맥락 |

### 해설

Concentrated Portfolio는 12개 프리셋 중 **가장 독특한 관점**을 제공한다. 나머지 11개는 "어떤 종목이 좋은가" 또는 "종목의 속성이 어떤가"를 보지만, 이 프리셋만 유일하게 "몇 개에 얼마나 집중하고 있는가"를 본다.

Core 지표들의 방향이 "정보 제공"인 것에 주의해야 한다. 집중도가 높다고 나쁜 게 아니고, 낮다고 좋은 게 아니다. Charlie Munger는 "과도한 분산은 무지에 대한 보호장치"라고 말했다. 5개 종목에 집중하는 것은 전략적 선택이다. 다만 그 집중이 **의도적이고 각 포지션에 대한 확신이 뒷받침**되어야 한다.

이 프리셋의 진짜 가치는 **다른 프리셋과 교차 사용**할 때 나온다. Buffett으로 보면 "좋은 기업이다", Low Volatility로 보면 "변동성이 크다", Concentrated로 보면 "그 종목에 30%가 들어가 있다" — 이 세 관점을 합치면 "좋은 기업이지만 변동성이 크고 비중이 과도하다"는 입체적 진단이 된다.

### 특이사항

- **코칭 톤이 매우 중요.** "집중도가 높습니다"가 경고가 아니라 "이 집중이 의도적이라면 각 포지션에 대한 확신이 뒷받침되어야 합니다"로 표현. Munger 철학을 존중하는 톤
- **상관관계와 리스크 기여도는 Low Volatility 프리셋에서 이미 구현.** 재사용하면 됨
- **구현 난이도 가장 낮음.** Core 4개가 전부 산술 계산(비중의 제곱합, 상위 3개 합, 종목 수 세기, 최대값). 외부 데이터 의존 없음
- **Phase 2에서 Kelly Criterion + Thesis 확신도 연결:** "비중 25%인 NVDA에 대한 thesis 확신도가 60%입니다. Kelly 기준으로 이 확신도에 적정한 비중은 약 15%이므로, 현재 비중이 확신 대비 과도합니다"
- **"적정 집중도"의 기준이 투자자마다 다름.** MVP에서는 판단을 내리지 않고 현황만 보여줌. 사용자가 스스로 "이 정도 집중이 내 성향에 맞는가"를 판단하도록 유도

### 진단 카드 예시

**카드 1: 종목 분산 vs 섹터 집중**
> 7개 종목을 보유하고 있지만, 섹터 HHI가 0.42로 기술 섹터에 68%가 집중되어 있습니다. 종목 수는 분산되어 보이지만 섹터 관점에서는 고도로 집중된 포트폴리오입니다.
>
> Concentrated Portfolio 관점에서 "다른 바구니에 계란을 나눴지만 바구니가 전부 같은 선반 위"인 상태입니다. 기술 섹터 전체에 불리한 이벤트(금리 급등, 규제 강화 등)가 발생하면 7개 종목이 동시에 타격받을 수 있습니다.
>
> 다만 이것이 의도적인 기술 섹터 집중 전략이라면, 섹터 내에서 서로 다른 하위 산업(반도체, 소프트웨어, 클라우드 등)에 분산되어 있는지 확인해보세요.

**카드 2: 단일 포지션 과대**
> NVDA 비중 35%로 단일 포지션이 포트폴리오의 1/3 이상을 차지합니다.
>
> Munger의 집중 투자 철학에서도 단일 포지션 35%는 높은 편입니다. 이 수준의 집중은 해당 종목에 대한 매우 강한 확신을 요구합니다.
>
> 이 확신이 뒷받침된다면 전략적 선택이지만, NVDA에 부정적 이벤트 발생 시 포트폴리오 전체에 -10% 이상의 타격이 예상됩니다. thesis에서 이 확신의 근거를 검증해보시기 바랍니다.

### 다른 프리셋과의 차별화

| 비교 대상 | 핵심 차이 |
|---|---|
| vs Low Volatility | Low Volatility는 "리스크가 얼마나 큰가". Concentrated는 "왜 리스크가 큰가(집중 때문인가)". 원인과 결과의 관계 |
| vs Multi-Factor | Multi-Factor는 "팩터 구조". Concentrated는 "비중 구조". 다른 축의 분석 |
| vs 나머지 모든 프리셋 | 나머지는 "종목의 속성"을 봄. Concentrated만 "포트폴리오의 구조"를 봄 |

---

## 전체 지표 중복 현황

| metric_id | 사용 프리셋 수 | Core인 프리셋 | Supporting인 프리셋 | Context인 프리셋 |
|---|---|---|---|---|
| `roic` | 4 | Buffett, Quality Growth | GARP, Shareholder Yield | — |
| `pe_ratio` | 10 | GARP, Contrarian | Buffett, Piotroski(C), Dividend, Shareholder | Quality, Low Vol, Momentum, Multi(계산), Concentrated(없음) |
| `roe` | 5 | Buffett | Dividend, Quality Factor | Low Vol, Contrarian |
| `debt_to_equity` | 7 | Quality Factor | Buffett, GARP, Quality Growth, Dividend, Contrarian | Shareholder |
| `beta` | 8 | Low Volatility | — | Buffett, GARP, Quality Growth, Dividend, Quality Factor, Momentum, Concentrated |
| `eps_growth_yoy` | 6 | GARP | Dividend, Shareholder, Momentum | Quality Growth, Contrarian |
| `dividend_yield` | 6 | Shareholder Yield | Dividend | Buffett, Quality Factor, Low Vol, Contrarian |
| `fcf_margin` | 3 | — | Buffett, Shareholder, Quality Factor | — |
| `market_cap` | 9 | — | — | Buffett, Piotroski, GARP, Quality Growth, Dividend, Momentum, Contrarian, Multi, Concentrated |
| `f_score_total` | 2 | Piotroski | Contrarian | — |
| `return_12m` | 3 | Momentum(↑), Contrarian(↓) | — | — |
| `avg_correlation` | 2 | — | Low Vol, Concentrated | — |
| `max_risk_contribution` | 2 | — | Low Vol, Concentrated | — |

**같은 지표, 다른 계층, 다른 해석** — 이것이 프리셋 시스템의 본질이다.
