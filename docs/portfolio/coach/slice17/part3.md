# Slice 17 Part 3 — ActionItemsSection + RiskFlagsSection 추출 (Group A: E1·E3)

## 0. 전제

- 브랜치: slice17, HEAD 909bb34 (작업 시작 시 checkout 확인, working tree clean)
- baseline: vitest 30 files / 140 tests + tsc exit 0
- 분할 순서: 실측 3순위 (Group A = action_items + risk_flags 동형 보유 E1·E3)
- 회귀 위험: 중간 — 2 section 동시 추출 + PRIORITY_STYLE 응집. Part 1·2보다 한 단계 위.
- 비용: $0 (프론트 리팩터링, LLM 호출 없음)
- 안 B 경계 규칙 유지: 외형 wrapper 신규 생성 금지 / 섹션·원자 단위 공유 OK
- 회귀 게이트: 기존 140 무손실 + tsc exit 0. 감소 시 즉시 HALT.

## 0.1 실측 확정 사실

- action_items: CommentaryCard L89-117, 조건 actionItems.length>0, 아이콘 ListChecks
- risk_flags: CommentaryCard L138-150, 조건 riskFlags.length>0, 아이콘 AlertTriangle
- PRIORITY_STYLE: CommentaryCard L34-38, action_items 단독 사용 (Step 0에서 의도적으로
  미이동 — Part 3에서 ActionItemsSection으로 응집 예정)
- 보유 EP: action_items = E1·E3·E5 / risk_flags = E1·E3·E6
  → 이번 Part 대상은 E1·E3 (E5·E6는 Part 4에서 조합·잔여 검증)
- CommentaryActionItem[] 타입, CommentaryCardData.action_items / risk_flags optional
- Step 0 산출 자산: SectionHeader, CardSection 사용 가능

## 1. P3-A — ActionItemsSection 추출 (커밋: refactor: ActionItemsSection 추출)

대상: frontend/components/coach/

1. components/coach/ActionItemsSection.tsx 신규
   - props: { actionItems: CommentaryActionItem[] }
   - CommentaryCard L89-117 action_items 렌더 블록 이전
   - SectionHeader(icon=ListChecks, title) 사용
   - PRIORITY_STYLE(L34-38)을 이 컴포넌트 내부로 이동
     (CommentaryCard에서 제거 — action_items 단독 사용이므로 응집)
   - priority 배지 마크업도 함께 이전
   - 조건부 렌더는 CardSection 패턴 유지
   - ⚠ priority 배지는 action_items 전용 — ConfidenceBadge와 별개. 통합 금지.
2. CommentaryCard.tsx 재구성 — action_items 인라인 블록 → <ActionItemsSection> 치환
   - ListChecks import 제거 확인
3. 단위 테스트 — **tests**/coach/ActionItemsSection.test.tsx 신규
   - actionItems 있을 때 렌더 / 빈 배열 미렌더 / priority 배지 스타일 단언

## 2. P3-B — RiskFlagsSection 추출 (커밋: refactor: RiskFlagsSection 추출)

대상: frontend/components/coach/

1. components/coach/RiskFlagsSection.tsx 신규
   - props: { riskFlags: string[] }
   - CommentaryCard L138-150 risk_flags 렌더 블록 이전
   - SectionHeader(icon=AlertTriangle, title) 사용
   - 조건부 렌더는 CardSection 패턴 유지
2. CommentaryCard.tsx 재구성 — risk_flags 인라인 블록 → <RiskFlagsSection> 치환
   - AlertTriangle import 제거 확인
3. 단위 테스트 — **tests**/coach/RiskFlagsSection.test.tsx 신규
   - riskFlags 있을 때 렌더 / 빈 배열 미렌더

## 3. P3-C — Group A 화면 회귀 확인

- E1·E3 page 테스트 testId='commentary-card' 단언 무변경 통과
- action_items / risk_flags 렌더 결과가 Part 3 이전과 동일 (행위 보존)
- E2·E6 무영향 확인 / E5는 action_items 보유 → 미영향 단언으로 격리 확인
  (E5 action_items는 여전히 CommentaryCard 경유 — ActionItemsSection이
  CommentaryCard 내부에 있으므로 E5도 자동 수혜, 단 E5 page 테스트 무변경 확인)

## 4. P3-D — Part 3 closing (커밋: docs: Slice 17 Part 3 closing)

1. docs/portfolio/coach/slice17/part_3/closing.md — P3-A/B/C 산출, KPI, vitest 갱신
2. Part 4 예고 — E5 두 section(action+quoted) 조합 검증 = 분할 최종 게이트
   - CommentaryCard 잔여 섹션 점검(key_observations / header만 남았는지)

## KPI

- vitest 기존 140 무손실 + ActionItemsSection·RiskFlagsSection 테스트 +N
- tsc exit 0
- E1·E3 testId='commentary-card' 단언 무변경 통과
- E2·E6 무영향, E5 page 테스트 무변경 (격리 확인)
- PRIORITY_STYLE grep — ActionItemsSection 내부 1건만 (CommentaryCard에서 제거 확인)
- ListChecks / AlertTriangle grep — 각 Section 컴포넌트로만 이동 확인

## HALT 규칙

- 기존 140 통과 수 감소 시 즉시 HALT.
- priority 배지를 ConfidenceBadge와 통합하려는 변경 발견 시 HALT (별개 원자 — 안 B 정합).
- CommentaryCardData 타입 계약 변경 발견 시 HALT (Slice 18+ 범위).
- action_items / risk_flags 외 섹션(key_observations 등)에 손이 가면 HALT (범위 일탈).
