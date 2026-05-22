═══════════════════════════════════════════════════════════════
[슬라이스 14 / closing] 종결 보고서
짧은 슬라이스 — #63 cost ledger + 게이트 가치 probe(보류)
═══════════════════════════════════════════════════════════════

## (1) 슬라이스 정체성

Slice 14는 출발 시점 = 게이트 calibration 슬라이스(#61 본격 진행)였으나, Step 0.5
게이트 가치 probe 결과 사전등록 결정 규칙(≥75% → 보류)에 따라 calibration을 **보류**
하기로 확정. 따라서 짧은 슬라이스로 종결한다.

최종 정체성 = **두 가지 산출물**:
- **#63 cost ledger** (production 코드) — LLM 호출별 비용 영속화 인프라
- **게이트 가치 의사결정 probe** (데이터로 남긴 사전등록 의사결정 기록) — 휴면 게이트
  코드를 "calibrate 안 한다"는 결정을 데이터로 정당화한 산출

두 산출물 모두 그 자체로 가치 있으므로 보존하고 깔끔히 닫는다.

---

## (2) Step 0 요약 (#63 cost ledger 신설)

**커밋**: `a85a0c3` (사전 사실 확인) + `63fedaf` (#63 신설).

**산출**:
- `portfolio/llm/cost_ledger.py` 신설 — `append_call` / `read_records` / `sum_cost_usd`.
  경로 `docs/portfolio/coach/cost_ledger.jsonl` (REPO_ROOT 기준, `COST_LEDGER_PATH`
  override 지원). 9 컬럼: `timestamp / slice / entry_point / provider / model /
  input_tokens / output_tokens / cost_usd / fallback_from`.
- `portfolio/llm/client.py` `LLMClient.complete()` 내 `guard.record_response(...)` 직후
  `append_call(...)` 호출 1줄 추가. **이중 방어 try/except** (보조 장치 보호 최우선).
- `docs/portfolio/coach/COST_POLICY.md` §6 추가 — ledger 정책 명문화 (append-only,
  차단 동작 없음, 차단은 #64 별도 슬라이스).
- `portfolio/tests/test_cost_ledger.py` 신설 — 10 테스트.

**회귀·KPI**:
- 회귀 730 → **740 (+10)** — 지시서 +6~12 정확.
- IDENTICAL 31/31 PASS — service/LLM 호출 경로 무수정 보증.
- CostGuard 기존 회귀 **34/34 PASS** (`test_cost_guard*`, `test_cost_guard_cap` —
  차단 로직 무변경 보증).

**사전 사실 확인 (step0_facts.md)**:
- **FMP 시장 분포 capability 존재** — `validation/services/benchmark_calculator.py`의
  p25/p50/p75 + percentile_rank + size_bucket peer 선정. Part 1(가정) 신규 구축 불필요.
- **12 preset `gate_tiers` 전부 None** — Slice 13 Step 0a가 구조만 ADDITIVE로 붙였고
  preset 인스턴스에는 정의 없음. 따라서 Part 2(가정)는 *교체*가 아닌 *신규 정의*였을 것.
- **`_evaluate_gate_tier` 점수 경로 완전 분리** — prompt context 전용. 경계값 교체가
  IDENTICAL 무손상임을 보증하는 구조 확인.
- **ledger 유사 파일 부재** — #63 정당.

---

## (3) Step 0.5 요약 (게이트 가치 probe)

**커밋**: `b7f861b` (케이스 동결, 사전 등록) + `a353162` (24 생성 + 평가).

**설계**:
- production 코드 변경 0. LLM 호출만.
- 8 케이스 × haiku 3회 = 24 생성. gate_tiers=None 그대로(현 E3 지표 코멘트
  production 동작). 케이스 사전 동결 → 결론을 케이스에 맞추는 역방향 편향 차단.
- 5 카테고리 5/5 커버 (value 2 · growth 2 · income 2 · factor 1 · special 1).
  8 케이스 전부 합성 — 위험 지표 1개만 `level_tag="critical"` + 극단값, 나머지 Core
  지표는 `level_tag="moderate"` + 정상값으로 격리.

**케이스**:
| # | preset_id | category | 위험 지표 | 극단값 |
|---|-----------|----------|----------|--------|
| 1 | buffett_quality_value | value | roic | -0.08 |
| 2 | piotroski_f_score | value | f_score_total | 1 |
| 3 | garp | growth | eps_growth_yoy | -0.35 |
| 4 | quality_growth | growth | roic_consistency_5y | 0.10 |
| 5 | dividend_growth | income | dividend_yield | 0.001 |
| 6 | shareholder_yield | income | shareholder_yield | -0.05 |
| 7 | low_volatility | factor | beta | 1.8 |
| 8 | contrarian | special | pct_from_52w_high | 0.0 |

**집계**:
- **키워드 보수 판정**: 20/24 = **83.3%** (사전 등록 키워드 부분집합 매칭).
- **의미 판정 (인스펙션)**: ~**100%** (미포착 4건 중 1건은 LLM schema 위반 error,
  3건은 "약한"/"부정적"/"배치되는" 등 경고 framing은 명확하지만 사전 키워드 미매칭).
- 케이스별 분포: 3/3 **5건**, 2/3 **2건**, 1/3 **1건**, 0/3 **0건**.
- 비결정성 케이스(1/3·2/3) = **3건**.

---

## (4) 평가 방법 기록

지시서 사전등록 루브릭은 **의미 판정**(위험을 우려/약점/리스크로 명시 + 경고
framing)이었으나, 자동화를 위해 **사전 등록 키워드 매칭**으로 대리(scripts/slice14/
evaluate_gate_probe.py `WARNING_KEYWORDS` 상수). 키워드는 의미 판정의 보수적 하한이
며, 사전 등록(생성 후 변경 금지)로 인해 적합도 부족이 결론을 흔들 수 없게 설계됨.

**평가 방법 흔들림 견고성**:
- 키워드 판정 = **83.3%** → 사전 규칙 ≥75% 임계 충족 → 보류.
- 의미 판정 = **~100%** → 사전 규칙 ≥75% 임계 명백히 충족 → 보류.
- 두 방법 모두 동일한 결론(보류). 평가 방법론 차이로 결론이 뒤집히지 않음 — 견고함
  확인.

---

## (5) 결론

**게이트 calibration 보류**.

**사유**: LLM이 명백한 위험을 스스로·일관되게 자가 포착함이 24 호출 데이터로 확인됨
(키워드 83.3% / 의미 ~100%). 게이트의 가치 명제 "도메인 절대 기준의 위험을 LLM이
놓치는 부분까지 결정론적으로 잡아준다"는 본 probe에서 검증 실패 — LLM이 그 영역을
이미 커버한다.

**휴면 코드 처리 — "의도된 대기 폴백" 보존**:
- `gate_tiers` (12 preset 모두 None) 필드 정의 — **제거 안 함**.
- `ScoringEngineBase._evaluate_gate_tier()` — **제거 안 함**.
- `format_gate_tier_for_prompt()` — **제거 안 함**.
- e1~e6 service 내 게이트 호출 분기 — **제거 안 함**.

근거: production에서 LLM이 경계선 위험을 놓치는 정황이 나오면 12 preset에
`gate_tiers={metric, fail_below, warn_below, _op}`만 채워서 즉시 재가동 가능한
폴백을 유지하는 것이 안전. 제거하면 재진입 비용이 발생.

로드맵 "preset threshold 본격 설계" 항목 → **"LLM 커버로 의식적 종결"**로 기록.
부채로도 등록하지 않음 (사전등록 결정 규칙 그대로).

---

## (6) 비용

- **Slice 14 누적 = $0.1273** (#63 ledger 첫 실측값).
- 내역:
  - Step 0: $0 (LLM 호출 0).
  - Step 0.5: $0.1273 (24 호출).
- ledger 24행 합 = $0.1273 = closing 작업 2 검증 일치.
- script `run_gate_probe.py` 보고 = $0.1212. 차이 $0.0061 원인: case 6 rep 1 schema
  위반 응답이 LLM 호출은 완료(토큰 비용 발생, ledger 기록)되었으나 script는 metadata
  없는 error 레코드라 합산 제외. **ledger 값($0.1273)이 호출 단위 실측 진실**.
- 임계 $4.00 마진: $4.00 − $0.1273 = $3.8727 (3.2% 사용).
- slice cap $1.00 마진: $1.00 − $0.1273 = $0.8727 (12.7% 사용).
- pre-Slice-14 누적은 #63 ledger 부재로 추정값 — **본 슬라이스부터 ledger 영속화**.

---

## (7) 외부 커밋 처리

slice14 브랜치에 본 작업과 무관한 외부 커밋 2건이 자동 누적됨 (야간 자동화로 추정):

| 커밋 | 일시 | 내용 | 변경 파일 | 본 작업과의 관계 |
|------|------|------|----------|----------------|
| `ef46637` | 2026-05-22 21:58 | metrics: Phase 1 도메인별 4통 분리 일일 보고서 | `metrics/services/agent_reports.py` (336L 신규), `metrics/tasks.py` (+74L), `metrics/templates/email/agent_report.html` (118L 신규), `metrics/management/commands/register_agent_report_tasks.py` (81L 신규) | 무관 (`metrics/` 앱 — scoring/portfolio/coach 무관) |
| `a90d423` | 2026-05-22 23:53 | docs: 코드베이스 감사 보고서 12개 생성 | docs/codebase_audit/22일/*.md (12개, 3170 insertions) | 무관 (docs only — 코드 0 변경) |

**처리 방침**: 브랜치에 그대로 수용, history 미변경 (rebase/amend/cherry-pick 없음).
회귀 740 / IDENTICAL 31/31 PASS는 두 외부 커밋 전후 모두 유지됨을 closing 작업 0에서
재확인.

---

## (8) 회귀·IDENTICAL

- 회귀: **740 passed + 1 skipped** (포함 +10 #63 신설분).
- IDENTICAL: **31/31 PASS**.
- 측정 위치: slice14 브랜치 HEAD (closing 커밋 직전 확인).

---

## (9) 부채 변동

- **close**: `#61` (게이트 calibration) — Slice 14 Step 0.5 게이트 가치 probe로 보류
  결정. calibration 수행하지 않고 종결 — LLM이 명백한 위험을 자가 포착함이 확인됨
  (키워드 83.3% / 의미 ~100%). gate_tiers 휴면 코드는 폴백으로 보존.
- **신규**:
  - `#68` cost ledger entry_point null — caller(e1~e6)가 `record_response` 호출 시
    entry_point를 전달하지 않아 ledger 컬럼이 null로 기록됨. caller 6곳에 인자 1줄
    씩 추가하면 해소. **PS 1.0, 비위험**. (당초 Slice 14 결정 B-2였으나 Part 1
    미진입으로 부채로 재귀속.)
  - `#69` E3 LLM schema 위반 처리 확인 — probe 24건 중 1건이 `extra="forbid"` 위반
    응답(LLM이 정의 외 `metric_display_name` 필드 추가). production `run_e3`가 이런
    응답에 재시도/폴백을 갖는지 미확인. 조사 후 필요 시 조치. **PS 1.0, 조사성**.

---

## (10) Slice 14 보존 산출물

| 산출물 | 위치 | 성격 |
|--------|------|------|
| #63 cost ledger 모듈 | `portfolio/llm/cost_ledger.py` | **production 코드** |
| ledger client 통합 | `portfolio/llm/client.py:170` 직후 | **production 코드** |
| ledger 영속화 파일 | `docs/portfolio/coach/cost_ledger.jsonl` | **운영 데이터** (24행 초기 적재) |
| COST_POLICY §6 | `docs/portfolio/coach/COST_POLICY.md` | 정책 문서 |
| #63 테스트 | `portfolio/tests/test_cost_ledger.py` | 회귀 테스트 (10건) |
| 게이트 probe 케이스 | `docs/portfolio/coach/slice14/gate_probe_cases.md` | 사전 등록 의사결정 기록 |
| 게이트 probe 출력 | `docs/portfolio/coach/slice14/gate_probe_outputs.json` | 24 LLM 응답 원문 |
| 게이트 probe 평가 | `docs/portfolio/coach/slice14/gate_probe_eval.md` | 케이스별 판정 + 잠정 결론 |
| probe scripts | `scripts/slice14/run_gate_probe.py` + `evaluate_gate_probe.py` | 재실행/재평가 도구 |
| 휴면 게이트 코드 | `portfolio/services/scoring/preset_spec.py:44` (gate_tiers 필드), `portfolio/services/scoring/base.py::_evaluate_gate_tier`, `portfolio/services/scoring/__init__.py::format_gate_tier_for_prompt`, e1~e6 service 호출분기 | **의도된 대기 폴백** |
| step0 사실 확인 | `docs/portfolio/coach/slice14/step0_facts.md` | 1차 사실 기록 |
| 작업 지시서들 | `slice14/step_0.md`, `step_0.5.md` | 종결 시점 보존 (지시서 원본은 본 closing 커밋 직전 commit `a85a0c3` + `b7f861b`에 git history로 남음) |

---

## (11) 다음

**Slice 15 진입점 결정 사이클**.

- 부채 큐 우선순위 재평가 (PS 2.0+ 부채부터): #66 (E3 preset_id/metrics 미노출 — 분석엔진 #12 의존), #67 (Slice 13 #65 closing 등록분), 기타.
- Step 0 진입점 후보 검토 → 슬라이스 정체성 1줄 명문화.
- 본 Slice 14의 "짧은 슬라이스" 패턴은 Step 0.5 probe로 핵심 가설 검증 후 즉시 종결한
  사례로 기록 — Slice 10 mini-slice 패턴(MINI_SLICE_PATTERN.md)의 변형.
