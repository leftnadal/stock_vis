═══════════════════════════════════════════════════════════════
[슬라이스 13 / Step 0a] 작업 지시서
3단 게이트(additive) + estimator multivariate fit + 베이스라인 정정
═══════════════════════════════════════════════════════════════

■ 사전 조건 (반드시 먼저 수행)
S0a-0. 브랜치 분기

- portfolio 브랜치는 slice7에서 멈춰 있음. slice12 헤드에서 분기할 것.
- `git checkout <slice12 종결 commit>` 후 `git checkout -b slice13`
- slice12 종결 commit 해시를 보고에 명기.

S0a-1. 베이스라인 사실 확정

- 회귀 전체 실행 → 현재 카운트 보고 (점검 시 669 확인됨, 재확인).
- slice12 종결 commit 이후 git log로 +1 테스트의 출처를 1줄로 확인해 보고.
- IDENTICAL 7/7 보호 테스트 전체 실행 → 현 상태 PASS 여부 확정.
- 이 시점의 회귀 카운트를 "Step 0a 베이스라인"으로 고정.

───────────────────────────────────────────────────────────────
■ 작업 1 — #60 3단 게이트 (ADDITIVE 방식, 점수 경로 무손상)
───────────────────────────────────────────────────────────────
[설계 원칙 — 위반 금지]

- 기존 `gate` 필드, `_apply_gate()`, `score=0.0` 로직은 한 줄도 수정 금지.
- 3단 분류는 기존 점수 계산과 완전히 분리된 ADDITIVE 레이어로만 구현.
- 3단 결과는 점수에 일절 관여하지 않고, commentary prompt context로만 흐른다.

1-1. preset_spec.py — 신규 Optional 필드 추가

- PresetSpec에 `gate_tiers: Optional[dict] = None` 추가.
- 구조 예시:
  gate_tiers = {
  "metric": "dividend_yield",
  "fail_below": <기존 단일 gate 임계값>,
  "warn_below": <fail_below × 1.5>, # placeholder
  }
- 미정의(None) 시 평가 결과는 항상 "pass" → 기존 12 preset 동작 불변.
- ⚠ 경계값(fail_below/warn_below)은 PLACEHOLDER다. 실제 calibration은
  Slice 14로 분리 등록(아래 작업 3 참조). 코드 주석에 "# PLACEHOLDER:
  Slice 14 calibration 대상" 명기.

1-2. scoring/base.py — 신규 평가 함수 추가 (기존 함수 수정 아님)

- `_evaluate_gate_tier(metrics, gate_tiers) -> str` 신규 @staticmethod 추가.
- 반환: "pass" | "warn" | "fail" (gate_tiers=None → "pass").
- 지표 부재 시 처리는 \_apply_gate와 동일 정책("fail" 또는 보수적 처리)으로
  통일하되, 점수에는 영향 없음을 코드/주석으로 명확히.

1-3. E1/E2/E3/E5/E6 service — gate-tier context 주입

- E3는 이미 preset_id+metrics kwarg 패턴 보유 → 3단 결과를 prompt에 추가.
- E1/E2/E5/E6 service에 E3와 동일하게 `*, preset_id: Optional[str] = None,
metrics: Optional[dict] = None` kwarg 추가.
- kwarg가 None이면 기존 동작 100% 동일(게이트 미주입) → 하위호환 보장.
- kwarg 제공 시 `_evaluate_gate_tier` 결과("pass/warn/fail")를 prompt
  context에 1줄 주입. prompt 주입 형식은 E3 기존 패턴 답습.

1-4. 테스트 (회귀 +예상 8~12)

- gate_tiers=None일 때 모든 경로 "pass" 확인 (기존 preset 불변 보증).
- gate_tiers 정의 시 pass/warn/fail 3분기 각각 검증.
- E1/E2/E5/E6 service: kwarg 미전달 시 출력이 기존과 동일함을 확인.
- ★ IDENTICAL 7/7 보호 테스트 재실행 → fixture가 gate_tiers 미정의이므로
  출력 해시 불변이어야 함. 깨지면 ADDITIVE 원칙 위반 → 즉시 보고하고 중단.

───────────────────────────────────────────────────────────────
■ 작업 2 — #51 estimator multivariate fit (순수 추정, 비위험)
───────────────────────────────────────────────────────────────
[범위 한정]

- 이 Step 0a에서는 추정 정확도 개선(fit)만 수행.
- CostGuard integration은 Step 0b에서 별도 격리 처리 → 여기서 손대지 말 것.

2-1. estimator_v3.py — output_tokens 추정 모델 다변량화

- 현재: output_tokens = expected_output_chars × ratio (단변량).
- 개선: all_llm_calls.jsonl(200 entries, 8 진입점) 기반으로
  (expected_output_chars, entry_point, model)을 설명변수로 한
  다변량 회귀/구간별 모델로 교체.
- 기존 estimate_output_tokens() 시그니처는 유지(하위호환). 내부 구현만 교체.
- ENTRY_POINT_OUTPUT_RATIOS / GLOBAL_OUTPUT_RATIO는 신모델로 대체하되,
  구모델 계수는 주석 또는 backtest baseline으로 보존.

2-2. 백테스트 검증

- scripts/coach/backtest_output_estimator.py로 신·구 모델 delta 비교.
- 신모델 max delta를 보고. 구모델 baseline 대비 개선폭 명기.
- PASS 기준: 신모델 max delta가 구모델 대비 유의미하게 감소
  (목표 수치는 보고 후 협의 — 강제 게이트 아님).

2-3. 테스트 (회귀 +예상 3~6)

- 신모델 단위 테스트. 경계 입력(chars=0, entry_point 미지정 → fallback) 검증.

───────────────────────────────────────────────────────────────
■ 작업 3 — 베이스라인 정정 & 신규 부채 등록
───────────────────────────────────────────────────────────────
3-1. 신규 부채 3건을 백로그 문서에 등록 (docs/portfolio/coach/ 경로)

- #61 3단 게이트 경계값 calibration (PS 2.5, Slice 14, 옵션B threshold와 통합)
  단서: "메모리상 '3단' 표현 기반, 경계값은 현재 placeholder"
- #62 estimator → CostGuard integration (PS 1.5, Slice 13 Step 0b에서 처리)
- #63 누적 비용 ledger 영속화 (PS 1.5, Slice 14+, #62와 비용인프라 묶음)

3-2. closing 보고서에 명기할 사항

- "$3.1196(S12 누적)은 ledger 부재로 미검증 — closing 보고서 기재값"
- slice13 분기 기준 = slice12 종결 commit <해시>
- 회귀 +1(668→669) 출처 git log 추적 결과

───────────────────────────────────────────────────────────────
■ Step 0a 종결 체크리스트
───────────────────────────────────────────────────────────────
□ 회귀 전체 PASS, 카운트 = 베이스라인 +11~18 범위 내
□ IDENTICAL 7/7 PASS (★ gate_tiers 미정의로 fixture 출력 해시 불변)
□ 기존 12 preset score 결과 불변 (gate_tiers=None 경로)
□ E1/E2/E5/E6 service kwarg 미전달 시 출력 불변 (하위호환)
□ estimator 백테스트 delta 보고 완료
□ 신규 부채 #61/#62/#63 등록 완료
□ 비용: LLM 호출 0 예상 → $0 (fit은 데이터 파일 기반, 호출 없음)

■ 산출물

- 코드: preset_spec.py / scoring/base.py / E1·E2·E5·E6 service /
  estimator_v3.py / 신규 테스트 파일들
- 문서: 백로그 갱신 + step0a_closing.md
- 보고: 위 체크리스트 결과 + 회귀 카운트 + IDENTICAL 상태 + 백테스트 delta

※ IDENTICAL 7/7이 깨지면 ADDITIVE 원칙 위반 신호다. 즉시 작업 중단하고
어느 변경에서 깨졌는지 보고할 것. 진행 강행 금지.
═══════════════════════════════════════════════════════════════
