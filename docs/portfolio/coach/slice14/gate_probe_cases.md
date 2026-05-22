═══════════════════════════════════════════════════════════════
[슬라이스 14 / Step 0.5 / 작업 1] gate probe 케이스 동결
═══════════════════════════════════════════════════════════════

## 작업 0 사실 확인 요약 (E3 생성 경로)

- **E3 (지표 코멘트) 진입점**: `portfolio/services/e3_metric_comment.py::run_e3(request: E3Request, provider="haiku", client=...)`.
  - 입력: `E3Request(analysis_context: dict)` — `AnalysisContext.model_dump()` 결과 dict.
  - prompt 빌더: `portfolio.prompts.e3.e3_builder.build_e3_prompt(context)` → (system, user) tuple → wrapper로 concat.
  - 출력: `MetricComments` (지표별 한 줄 자연어 코멘트).
- **AnalysisContext 핵심 슬롯** (`portfolio/schemas/analysis_context.py:135`):
  - `analysis_target_portfolio` → `preset_id` + `preset_category` + `core_metric_results: list[MetricResult]` + supporting/context/strengths/weaknesses.
  - `MetricResult` (`portfolio/schemas/metric_result.py:29`) = `metric_id` + `value` (Decimal) + `level_tag` ("excellent|good|moderate|weak|critical") + percentile + threshold_applied. ★ 원시 `value`와 `level_tag` 모두 LLM에게 노출됨.
- **게이트 주입 없음 확인**: `run_e3`는 `gate_tier`/`format_gate_tier_for_prompt` 호출 자체를 하지 않는다. E3 (지표 코멘트) 경로는 gate_tiers와 무관 — 본 probe가 측정하는 "게이트 OFF" 상태가 정확히 production E3 동작.
- **참고**: 별도 진입점 `portfolio/services/coach/e3_service.py::run_e3_coach` (Slice 11 E3 집중도)는 `gate_tier`를 prompt에 넣지만 12 preset 전체가 gate_tiers=None이라 항상 "pass" 1줄 박힘. 본 probe는 "지표 코멘트 E3"를 측정하므로 무관.

---

## 케이스 선정 기준 충족 점검

| 기준 | 충족 |
|------|------|
| (a) 1 케이스 = 1 preset + 그 preset의 Core 지표 1개 | ✅ 8건 전부 |
| (b) Core 지표가 preset 정의적 전제를 정면으로 깨뜨리는 극단값 | ✅ 8건 전부 |
| (c) 위험을 1문장 명확 진술 가능 | ✅ 8건 전부 |
| (d) 5 카테고리 중 ≥4 커버 | ✅ **5/5** (value 2, growth 2, income 2, factor 1, special 1) |
| (e) 위험 지표 1개 격리 — 나머지는 정상/중립 | ✅ 8건 전부 (나머지 Core 지표 `level_tag="moderate"`, percentile 0.50 정도) |
| (f) 데이터 출처 명시 | ✅ 8건 전부 **합성** (사유: 위험 지표 1개만 극단 + 나머지 중립 격리가 필요한데 기존 fixture는 사용자 시나리오용으로 위험 지표 격리가 안 됨) |

---

## 케이스 8건

| # | preset_id | category | 위험 지표 (metric_id) | 극단값 (value) | level_tag | 위험 1문장 진술 | 출처 |
|---|-----------|----------|----------------------|----------------|-----------|----------------|------|
| 1 | `buffett_quality_value` | value   | `roic`               | `-0.08` (-8%)  | critical  | Buffett quality 전략의 핵심 전제는 자본수익률(ROIC)의 지속적 양수성. ROIC -8%는 자본을 파괴하는 사업이라는 결정적 시그널 — preset 정의 정면 위배. | 합성 |
| 2 | `piotroski_f_score`     | value   | `f_score_total`      | `1` (9 중 1)   | critical  | Piotroski F-Score 전략의 정의적 전제는 점수 ≥ 7. 9점 만점에 1점은 9개 건전성 항목 중 1개만 통과 = 거의 모든 재무 약점 동시 발생. | 합성 |
| 3 | `garp`                  | growth  | `eps_growth_yoy`     | `-0.35` (-35%) | critical  | GARP의 'Growth' 전제는 양의 EPS 성장. -35% YoY는 성장이 아닌 역성장 — 전략 정의에 정면 모순. | 합성 |
| 4 | `quality_growth`        | growth  | `roic_consistency_5y`| `0.10` (10%)   | critical  | Quality compounder 전략은 ROIC의 다년 일관성이 본질. 5년 일관성 10%는 수익성 변동이 극심해 'quality' 라벨과 양립 불가. | 합성 |
| 5 | `dividend_growth`       | income  | `dividend_yield`     | `0.001` (0.1%) | critical  | Dividend growth 전략의 정의적 전제는 의미 있는 배당 yield. 0.1%는 income 전략으로 분류 자체가 불가능한 수준 — preset gate 임계(2%)의 5%에 불과. | 합성 |
| 6 | `shareholder_yield`     | income  | `shareholder_yield`  | `-0.05` (-5%)  | critical  | Shareholder yield 전략은 양의 순주주환원이 본질. -5%는 회사가 주주에게 돌려주는 게 아니라 신주 발행으로 주주를 희석시키는 상태 — 전략 정의 정면 위배. | 합성 |
| 7 | `low_volatility`        | factor  | `beta`               | `1.8`          | critical  | Low volatility 전략의 정의적 전제는 시장 대비 낮은 베타. 1.8 베타는 시장보다 80% 더 변동적 — 전략 명칭(low vol)과 정면 충돌, preset gate 임계(1.2 lte)의 1.5배. | 합성 |
| 8 | `contrarian`            | special | `pct_from_52w_high`  | `0.0` (신고가) | critical  | Contrarian 전략은 52주 신고가 대비 하락폭이 있는 종목을 매수 기회로 본다. pct_from_52w_high=0%(신고가 부근)은 contrarian 매수 신호 전무 — 모멘텀 영역에 가까운 종목. | 합성 |

---

## 합성 입력 컨텍스트 구성 원칙 (작업 2에서 적용)

8 케이스 전부 공통:
- `analysis_target_portfolio.preset_id` = 표의 preset_id
- `analysis_target_portfolio.preset_category` = 해당 카테고리
- `holdings_summary`: 단일 합성 종목 ("RISK_CASE", 비중 100%). 종목 선정으로 LLM bias 방지.
- `core_metric_results`: 해당 preset의 weights 키 전체. **위험 지표만** `value=극단값` + `level_tag="critical"`, **나머지 Core 지표**는 `value=정상중립값` + `level_tag="moderate"` + `percentile≈0.50`.
- supporting/context_metric_results: 빈 리스트.
- strengths: 빈 / weaknesses: 위험 지표 1건 (`level_tag="critical"`, `rank=1`). ★ weakness 슬롯이 LLM에 위험을 알려주는 명시 시그널이 아닌지 별도 검토 필요 — 본 probe는 그것 포함한 production prompt를 측정하는 것이 목적이므로 그대로 둠 (게이트는 weakness 슬롯과 별개의 결정론적 시그널).
- `wallet_background`: 최소 합성 (보유 1종, sector_distribution {합성 sector: 1.0}, return 합성).
- 모든 케이스의 공통 wallet_background는 동일 — 케이스 간 비교 시 위험 지표 변수만 변동하도록 격리.

---

## 평가 시 비결정성 격리

- 모델: `claude-haiku-4-5` (production E3 default).
- seed 고정 안 함 — 기본 샘플링 (지시서 §작업 2 명시).
- 케이스당 3회 반복 → 24 호출, 비결정성 자연 노출.
- 모든 호출은 #63 ledger에 자동 기록 (`slice` 컬럼 = `slice14`, `entry_point` 컬럼 = null — 후속 부채).
