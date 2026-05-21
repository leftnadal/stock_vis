═══════════════════════════════════════════════════════════════
[슬라이스 13 / Step 0b] 작업 지시서
estimator → CostGuard integration (#62) — 위험 작업 단독 격리
═══════════════════════════════════════════════════════════════

■ 위치 / 전제

- 브랜치: slice13 (Step 0a 커밋 위에서 진행)
- 베이스라인: 회귀 695 passed, IDENTICAL 31/31 PASS
- 이 Step은 CostGuard(비용 안전장치) 동작을 건드린다. 단독 격리 단계이며,
  종료 시 독립 커밋한다. Part 작업과 절대 섞지 말 것.

■ 핵심 설계 원칙 (위반 금지)

1. CostGuard의 기존 cumulative_usd 누적·reset_for_slice·50콜 budget guard
   로직은 동작 의미를 바꾸지 말 것. 추정 경로는 ADDITIVE로 얹는다.
2. estimator 추정값은 "사전 추정(pre-call estimate)"이며, 실제 비용
   산정(post-call actual)을 대체하지 않는다. 두 값을 명확히 구분한다.
3. estimator max delta가 24.58%로 여전히 크다 → 사전 추정값을 그대로
   쓰지 말고 SAFETY BUFFER를 적용한다 (아래 1-2 참조).
4. IDENTICAL 7/7(31 테스트)이 깨지면 즉시 중단·보고. 강행 금지.

───────────────────────────────────────────────────────────────
■ 작업 1 — estimator → CostGuard 연결
───────────────────────────────────────────────────────────────
1-1. cost_guard.py — 사전 추정 메서드 신규 추가 (기존 메서드 수정 아님)

- 신규 메서드 `estimate_call_cost(input_text, expected_output_chars,
entry_point, model) -> float` 추가.
- 내부에서 estimator_v3의 input(count_tokens API) + output(multivariate)
  추정을 호출해 사전 예상 비용(USD)을 반환.
- 기존 누적/리셋/budget guard 코드는 한 줄도 수정 금지.

1-2. SAFETY BUFFER 적용

- estimator max delta 24.58% → 사전 추정 비용에 buffer 계수를 곱한다.
- 권장: buffer = 1.25 (관측 max delta 24.58%를 보수적으로 흡수).
- buffer 계수는 상수로 분리 + "# estimator P-level delta 기반, #61/#51
  개선 시 재조정" 주석. 하드코딩 산재 금지.

1-3. 사전 예산 체크 경로 (ADDITIVE, 비차단 우선)

- LLM 호출 직전 estimate_call_cost × buffer 결과를 budget guard가
  참조하도록 연결.
- ★ 이번 Step에서는 사전 추정으로 호출을 "차단"하지 말 것.
  추정 비용이 예산 초과를 가리키면 WARNING 로그만 남기는 non-blocking
  모드로 구현. (차단 로직은 실측 검증 후 별도 부채로 분리 — 아래 작업 3)
- 이유: 24.58% 오차 상태에서 차단까지 켜면 정상 호출을 오탐 차단할 위험.

───────────────────────────────────────────────────────────────
■ 작업 2 — 검증
───────────────────────────────────────────────────────────────
2-1. 단위 테스트 (mock 기반, 회귀 +예상 5~9)

- estimate_call_cost 정확성: 알려진 input/output → 예상 USD 검증.
- buffer 계수 적용 확인 (1.25× 곱).
- non-blocking 확인: 추정 초과 시 WARNING 로그만, 호출은 진행됨.
- 기존 CostGuard 동작 불변: cumulative_usd 누적·reset_for_slice·
  50콜 guard가 integration 전과 동일하게 작동.

2-2. ★ IDENTICAL 체크포인트 (독립)

- IDENTICAL 31 테스트 전체 재실행.
- 사전 추정은 non-blocking이므로 LLM 호출 횟수·출력에 영향 없어야 함
  → 해시 불변이어야 PASS.
- 깨지면: 사전 추정이 어딘가에서 호출을 막거나 경로를 바꾼 것. 즉시
  중단하고 어느 변경에서 깨졌는지 보고.

2-3. 실측 1회 (선택, 저비용)

- 진입점 1개(예: E1)로 real LLM 호출 1회 → 사전 추정값 vs 실측 비용
  delta를 보고. buffer가 실측을 덮는지(추정×1.25 ≥ 실측) 확인.
- 이 1회 호출 비용을 보고에 명기.

───────────────────────────────────────────────────────────────
■ 작업 3 — 부채 갱신
───────────────────────────────────────────────────────────────
3-1. #62를 close하되, "사전추정 기반 호출 차단(blocking 모드)"은 분리:

- #62 → close (estimator → CostGuard 연결 + non-blocking 경고 완료)
- #64 신규: 사전 추정 기반 blocking 차단 모드 (PS 1.0, Slice 14+)
  단서: "estimator delta 24.58% → #61 calibration 후 차단 안전"
- #61(게이트 calibration) 단서에 "estimator 정밀화와 함께 buffer
  계수 재조정 대상" 한 줄 추가.

───────────────────────────────────────────────────────────────
■ Step 0b 종결 체크리스트
───────────────────────────────────────────────────────────────
□ 회귀 전체 PASS, 카운트 = 695 +5~9 범위 내
□ IDENTICAL 31/31 PASS (★ non-blocking이므로 해시 불변)
□ 기존 CostGuard 동작 불변 (누적·리셋·50콜 guard)
□ estimate_call_cost + buffer 1.25 정상 작동
□ non-blocking 확인 (추정 초과 시 WARNING만)
□ 실측 1회 delta 보고 (선택)
□ #62 close, #64 신규 등록
□ 비용: 실측 1회 시 ~$0.005 미만, 미실시 시 $0

■ 산출물

- 코드: cost_guard.py / 신규 테스트 파일
- 문서: debts.md 갱신 + step0b_closing.md
- 보고: 체크리스트 결과 + 회귀 카운트 + IDENTICAL 상태 + 실측 delta(실시 시)

■ 종료 후 커밋
git commit -m "slice13: Step 0b — estimator→CostGuard integration (non-blocking)"

※ CostGuard는 비용 안전장치다. IDENTICAL이 깨지거나 기존 동작이 바뀌면
즉시 중단·보고. 0a 커밋으로 롤백 가능한 상태를 유지할 것.
═══════════════════════════════════════════════════════════════
