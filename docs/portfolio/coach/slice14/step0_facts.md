═══════════════════════════════════════════════════════════════
[슬라이스 14 / Step 0 / 작업 1] 사전 사실 확인 결과
═══════════════════════════════════════════════════════════════

## 베이스라인 (S0-1)

- 브랜치: `slice14` (분기 HEAD `e337200` — #65 closing)
- 회귀: `730 passed, 1 skipped` (`portfolio/tests tests/coach tests/scoring`)
- IDENTICAL 31/31 PASS — 4 파일:
  - `portfolio/tests/test_e4_conversation_schema.py` (20)
  - `portfolio/tests/test_llm_client_system_arg.py` (4)
  - `portfolio/tests/slice8/test_input_v2_smoke.py` (5)
  - `tests/scoring/test_e3_scoring_integration.py` (2)

---

## 1-1. gate_tiers 현 구조

### 필드 정의 (`portfolio/services/scoring/preset_spec.py:38~44`)

```python
gate: Optional[dict[str, float | str]] = None
# Slice 13 Step 0a #60: 3단 게이트 (ADDITIVE). 점수 경로 무손상 — pass/warn/fail
# 결과는 commentary prompt context로만 흐른다. 기존 gate / _apply_gate / score=0
# 로직과 완전 분리. None이면 평가 결과 항상 "pass".
# 구조: {"metric": <name>, "fail_below": <float>, "warn_below": <float>, "_op": "gte"}
# PLACEHOLDER: 경계값은 Slice 14 #61 calibration 대상.
gate_tiers: Optional[dict[str, float | str]] = None
```

- 타입: `Optional[dict[str, float | str]]`
- 기본값: `None`
- 검증: `_validate_gate_tiers` (preset_spec.py:80~124) — None이면 skip.
  - metric: 비어있지 않은 str 필수
  - fail_below, warn_below: 모두 numeric 필수
  - _op: 옵션 `("gte","lte","gt","lt")`, default `"gte"`
  - 단조성: gte/gt → `fail_below < warn_below`, lte/lt → `fail_below > warn_below`

### 추정 ↔ 코드 일치

- 메모리/지시서 추정: `metric / fail_below / warn_below` 키 구조.
- 실제 코드: **추정과 일치**. 추가로 `_op` 옵션 키 존재 (default `"gte"`).
- ⚠ 중단 트리거(§중단 §3) 해당 없음 — 구조 동일.

### 12 preset gate_tiers 정의 현황

`portfolio/services/scoring/presets/*.py` 전수 점검 (5 파일 × 12 preset):

| preset_id                | category | gate                                  | gate_tiers |
|--------------------------|----------|---------------------------------------|------------|
| buffett_quality_value    | value    | None                                  | (미정의)   |
| piotroski_f_score        | value    | None                                  | (미정의)   |
| garp                     | growth   | None                                  | (미정의)   |
| quality_growth           | growth   | None                                  | (미정의)   |
| dividend_growth          | income   | `{"dividend_yield": 0.02, "_op": "gte"}` | (미정의)   |
| shareholder_yield        | income   | `{"shareholder_yield": 0.02, "_op": "gte"}` | (미정의) |
| quality_factor           | factor   | None                                  | (미정의)   |
| low_volatility           | factor   | `{"beta": 1.2, "_op": "lte"}`         | (미정의)   |
| price_momentum           | factor   | None                                  | (미정의)   |
| multi_factor             | factor   | None                                  | (미정의)   |
| contrarian               | special  | None                                  | (미정의)   |
| concentrated_portfolio   | special  | None                                  | (미정의)   |

**중요 발견**:
- **12 preset 모두 `gate_tiers`가 인스턴스에 명시되어 있지 않다** → 전부 default `None`.
- "PLACEHOLDER" 주석은 `preset_spec.py:43` 필드 정의에만 존재. preset 인스턴스에는 placeholder 경계값 자체가 없음.
- 지시서 추정("warn_below = fail_below × 1.5 류 임시 공식")은 **현재 코드에 부재**. Slice 13 Step 0a는 구조만 ADDITIVE로 추가했고, 12 preset 신규 정의 자체가 비어 있는 상태.
- 그 결과 `_evaluate_gate_tier(metrics, None)` 경로로 모든 preset이 항상 `"pass"` 반환 (점수·prompt 동작 변경 없음).

**Part 1~3 영향**:
- Part 2(경계값 교체)는 사실상 "신규 12 preset에 gate_tiers 정의" 작업이 된다.
  *교체*가 아니라 *신규 추가*. 따라서 _기존 경계값 → 실측 경계값 비교 검증_은 불가.
- 정의 누락 preset에 대해 "신규 정의가 IDENTICAL을 깨지 않는다"는 보호는 그대로 유효
  (gate_tiers는 prompt context로만 흐르므로 점수 hash 무손상).
- Part 1 분포 산출은 12 preset 전부의 metric에 대해 진행.

---

## 1-2. 게이트 평가 함수

### 시그니처 (`portfolio/services/scoring/base.py:102~156`)

```python
@staticmethod
def _evaluate_gate_tier(
    metrics: dict[str, float],
    gate_tiers: Optional[dict[str, float | str]],
) -> str:
    """Returns "pass" | "warn" | "fail" — 점수에 영향 없음, prompt context 전용."""
```

### 반환 계약

- `gate_tiers is None` → `"pass"` (12 preset 현 상태에서 항상 이 분기).
- `metric_name` 부재 또는 type 불일치 → `"fail"`.
- `value = metrics.get(metric_name)`이 None → `"fail"` (보수적).
- fail_below/warn_below numeric 검증 실패 → `"fail"`.
- `_op="gte"|"gt"`: `value < fail_below` → fail, `value < warn_below` → warn, 그 외 pass.
- `_op="lte"|"lt"`: `value > fail_below` → fail, `value > warn_below` → warn, 그 외 pass.

### 점수 경로 분리 (★ Part 2 IDENTICAL 보장의 근거)

- `_evaluate_gate_tier`는 `base.py`의 `_weighted_sum`/`_normalize_to_0_100`/`_apply_gate`(기존)와 **완전 별개 정적 메서드**.
- 점수 계산(`_weighted_sum` line 158~) 및 기존 gate 차단(`_apply_gate`)은 `_evaluate_gate_tier` 호출과 무관.
- 경계값(fail_below/warn_below)만 바꿔도 점수 hash는 변동하지 않음 — IDENTICAL 31/31 보장.

### Prompt context 주입 경로 (1줄)

- e1~e6 service (`portfolio/services/coach/e{1,2,3,5,6}_service.py:52|73|74` 등) → `gate_tier = ScoringEngineBase._evaluate_gate_tier(metrics, spec.gate_tiers)` → `format_gate_tier_for_prompt(preset_id, gate_tier)`를 `user_prompt`에 append.

---

## 1-3. FMP 시장 분포 capability (Part 1 핵심 선행 조사)

### 결론: **존재** — 신규 작성 불필요. 기존 인프라 활용.

### 주요 모듈

| 파일                                                  | 역할                                                                   |
|-------------------------------------------------------|------------------------------------------------------------------------|
| `validation/services/benchmark_calculator.py`         | p25/p50/p75, percentile_rank, size_bucket peer 선정                    |
| `validation/services/preset_generator.py`             | preset 생성 (percentile 활용)                                          |
| `validation/models/benchmark_delta.py`                | percentile_rank 저장 모델                                              |
| `validation/services/peer_selector.py`                | peer 그룹 멤버 선정                                                    |
| `stocks/services/fmp_screener.py`                     | FMP 스크리너 (market_cap 등으로 종목 필터)                             |
| `API_request/providers/fmp/processor.py`              | FMP 원본 데이터 fetch                                                  |

### `BenchmarkCalculator` 핵심 시그니처

```python
class BenchmarkCalculator:
    def calculate_for_symbol(self, symbol: str) -> dict
    def calculate_for_symbols(self, symbols: list[str] = None) -> dict
    def _select_peers(self, stock: Stock) -> tuple
    def _filter_by_size(self, qs, adjacent_buckets: list[str])
    def _calculate_benchmarks_for_year(...)  # p25/median/p75 산출 + percentile_rank
    def _calculate_industry_benchmarks(self, industry: str, fiscal_years: list[int]) -> int
```

- 산출 데이터 형태: per-(symbol, year, metric) `{p25_value, median_value, p75_value, percentile_rank, peer_count, confidence}`
- size_bucket 정책: `assign_size_bucket(market_cap)`, `get_adjacent_buckets(bucket)` (validation/services/benchmark_calculator.py:29, 41)
- 시장 전체 분포 산출: `_calculate_industry_benchmarks(industry, fiscal_years)` — 산업 단위 합산.

### Part 1 분량 영향

- **활용 — 신규 구축 X**. Part 1은 `BenchmarkCalculator`를 호출해 12 preset의 metric별 시장 분포(p25/median/p75)를 추출하고, gate_tiers fail_below/warn_below 경계값으로 매핑하는 작업이 핵심.
- FMP API 신규 엔드포인트 호출 불필요 — DB 내 캐시된 재무 데이터 위에서 percentile 계산 (validation app 의존).

---

## 1-4. 비용 인프라 현황 (#63 작업의 선행 조사)

### cost_guard.py 요약 (`portfolio/llm/cost_guard.py`)

- `CostGuard`: 싱글톤. `slice_id`, `call_count`, `instance_call_count`, `total_cost_usd`, `records: list[CallRecord]`, `cumulative_usd`, `slice_usd`.
- 두 계열의 비용 집계 메서드 존재:
  - `record_call(cost_usd, model)` / `record_response(cost_usd, model)` → `_record_response_internal` 호출 → `total_cost_usd += cost_usd` + `records.append(CallRecord(...))`
  - `record_cost(cost_usd)` (Slice 9 #43) → `cumulative_usd += cost_usd`, `slice_usd += cost_usd` + cap/threshold 차단 예외.
- `reset_slice(slice_id, max_calls)`: `slice_id`, `call_count`, `instance_call_count`, `total_cost_usd`, `records=[]`, `slice_usd=0` 리셋. `cumulative_usd`는 **보존**.

### LLM 호출 1건당 비용 산출 경로

- LLM 호출 단위 = `portfolio/llm/client.py:170` `guard.record_response(cost_usd=response.cost_usd, model=response.model)` 1지점.
- `LLMResponse.cost_usd` 산출 = `client.py` 내 `_ANTHROPIC_PRICING` × input/output 토큰 매핑 (provider별).
- entry_point는 `client.py` 단계에서는 보지 못함 (caller인 e1~e6 service에서만 명시).

### 누적 비용을 파일에 기록하는 인프라

- **부재** — 인메모리 list (`CostGuard.records`)만 존재. 파일 영속화 0건.
- `reset_slice` 호출 시 `records=[]`로 휘발. 즉 슬라이스 종료 후 호출별 비용 원본은 사라짐.
- closing 보고서의 누적 비용은 보고서 기재값(상기 휘발성 list로부터 수집 후 매뉴얼 기록)으로 미검증.
- **#63 ledger 신설은 정당** — 유사 파일 부재 확인.

### CostGuard reset 동작 정리

- `reset_slice` / `reset_for_slice`(alias)는 슬라이스 진입 시 호출. records 휘발.
- ledger는 이 reset과 **무관해야** 함 (append-only 외부 파일).

### entry_point 캡처 가능 여부

- `client.complete()` 시그니처(client.py 인근)에 entry_point 인자 없음.
- caller(e1~e6 service)만 entry_point를 알고 있음.
- 작업 2의 선택지:
  - (A) ledger append를 `client.py:170` 인근에 끼우되 entry_point는 `"unknown"`으로 채움.
  - (B) ledger append를 caller 측(e1~e6)에서 호출 후 명시적 entry_point 전달.
- (A) → 단일 지점 / entry_point 손실. (B) → 6지점 + 시그니처 확장 → IDENTICAL 위험 회피 위해 시그니처 변경 없이 `LLMResponse.metadata_dict()` 보강 또는 별도 helper로 처리.
- 작업 2는 IDENTICAL/append-only/기록 전용 원칙 충족하는 최소 변경을 선택. 후보 (A) 기반 — entry_point=null/unknown 허용, 후속 부채로 분리(필요 시 #67 또는 신규 부채).

### COST_POLICY.md 현재 내용 요약

- §1 임계값: 누적 임계 $4.00, 80% 경고 $3.20, slice cap $1.00, mini cap $0.50.
- §1.2 slice cap, §1.3 per-call 임계 (haiku $0.03 / sonnet $0.10).
- ledger 관련 섹션 부재 — 작업 2-4에서 추가 신설 필요.

---

## 중단 트리거 점검

- IDENTICAL 31/31 FAIL: 없음 (PASS).
- ledger 유사 파일 존재: 부재 (확인 완료).
- gate_tiers 구조 추정 ↔ 코드 불일치: 일치. (다만 12 preset 정의 자체가 비어 있음 — 신규 정의로 진행).
- 회귀 증분: 작업 1은 코드 변경 0이므로 N/A.
- ledger 기록을 위한 CostGuard 차단 로직 수정 필요성: 없음. `client.py:170` 또는 `_record_response_internal` 자리에서 보조 append 가능.

→ 작업 1 완료. 작업 2(#63 ledger) 진행 가능.
