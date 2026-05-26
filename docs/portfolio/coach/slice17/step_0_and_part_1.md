# Slice 17 — CommentaryCard 분할 (BaseCard + EP별 Section)

## 0. 전제 / 사전 확정 사항

- 진입점: C 리팩터링 (CommentaryCard → BaseCard + EP별 Section). 가중합 4.04로 확정.
- 분기점: 실측 4-a 채택 — CommentaryCardData(수동 합집합 타입) 유지 + BaseCard/Section만
  추출. codegen 직접 사용(4-c) 금지(§3 일반화 무효화). EP별 Pick<> 좁힘(4-b)은 Slice 18+.
- E4 BaseCard 공유 범위: **안 B 확정** (가중합 4.41).
  - 공유 O: 스타일 토큰(CONFIDENCE_STYLE) + <ConfidenceBadge> 원자 컴포넌트.
  - 공유 X: 외형 컨테이너 — BaseCard wrapper(카드) / E4 말풍선 wrapper.
  - E4MessageBubble은 BaseCard를 import하지 않는다. <ConfidenceBadge>만 채택.
- 경계 규칙 (지시서 + closing §3 노트 명문화):
  "공유 가능 = confidence 배지처럼 EP 무관하게 동일 의미를 갖는 원자 표현 요소.
  공유 금지 = 카드 wrapper·말풍선 wrapper처럼 EP 표현 정체성을 결정하는 컨테이너."
- 회귀 게이트: vitest 25 files / 115 tests + tsc exit 0. (IDENTICAL은 백엔드 전용 —
  이 슬라이스와 무관, baseline 추적 대상 아님.)
- strangler 점진 분할: 한 번에 폭파 금지. EP 그룹마다 vitest 회귀 검문 → 깨지면 HALT.
- 비용: 프론트 리팩터링, LLM 호출 없음 → $0. cap 압박 없음.
- 브랜치: slice17 신규 생성 (from slice16 HEAD a621b50). 작업 시작 시 checkout 확인.

## 0.1 실측 확정 사실 (근거)

- CommentaryCard: frontend/components/coach/CommentaryCard.tsx (154줄)
  - props: { output: CommentaryCardData }
  - 내부 섹션 5건: header(항상) / key_observations / action_items /
    quoted_metrics / risk_flags (각 length>0 조건부)
- CommentaryCardData: types.ts:77-92 (수동 정의)
  - required: summary, confidence('high'|'medium'|'low')
  - optional: key_observations, action_items, risk_flags, quoted_metrics,
    metrics_table(deprecated #21)
- 6 화면 사용: E1·E2·E3·E5·E6 = CommentaryCard 패스스루 / E4 = E4MessageBubble 전용
- CommentaryCard 비테스트 사용처 0건 → strangler 안전
- 공통 자산 후보: CONFIDENCE_STYLE(CommentaryCard L28-32 ↔ E4MessageBubble L27-31
  완전 중복) / confidence 배지 마크업(유사 중복) / SectionHeader 패턴(5회 반복) /
  Article wrapper / PRIORITY_STYLE / formatQuotedMetricValue
- Section 그룹: A(action+risk)=E1·E3 / B(quoted_metrics)=E2·E6 / E5=양쪽 보유 / E4=base-only
- vitest baseline: 25 files / 115 tests passed

---

## STEP 0 — 공통 자산 행위보존 추출 (커밋: refactor: BaseCard 공통 자산 추출)

목표: 동작을 1픽셀도 바꾸지 않고 공통 자산만 추출(행위 보존 리팩터링).
5 화면 prop 시그니처 무변경. 이 단계 후 화면 렌더 결과가 Step 0 이전과 동일해야 함.

대상: frontend/components/coach/ + frontend/lib/coach/

1. lib/coach/styles.ts 신규 — CONFIDENCE_STYLE 단일화
   - CommentaryCard L28-32 / E4MessageBubble L27-31 의 CONFIDENCE_STYLE 제거
   - styles.ts로 이전, 양쪽이 import
   - PRIORITY_STYLE은 이 단계에서 건드리지 않음 (action_items section 분리 시 함께 이동)

2. components/coach/ConfidenceBadge.tsx 신규 — 안 B 핵심
   - props 최소: { confidence: 'high'|'medium'|'low' }
   - CommentaryCard L65-70 배지 마크업 + E4MessageBubble L43-50 배지 마크업을
     이 컴포넌트로 통합 (양쪽이 ConfidenceBadge 사용)
   - styles.ts의 CONFIDENCE_STYLE 소비
   - ⚠ 외형 컨테이너 아님 — 배지(원자 요소)만. BaseCard/말풍선 wrapper는 건드리지 않음

3. components/coach/BaseCard.tsx 신규 — 5개 카드형 화면 전용 골격
   - 추출 범위: Article wrapper(CommentaryCard L55-58 rounded-2xl border...) +
     header(summary + ConfidenceBadge, L60-71)
   - props: { summary: string, confidence, children: ReactNode }
   - children 자리에 EP별 section들이 들어옴 (Step 0에서는 CommentaryCard가
     기존 5 섹션을 children으로 넘김)
   - ⚠ E4MessageBubble은 BaseCard를 import하지 않는다 (안 B 경계 규칙)

4. components/coach/SectionHeader.tsx 신규
   - props: { icon, title }
   - CommentaryCard 내 5회 반복되는 (icon + h3) 패턴 통합
   - 5 섹션이 모두 SectionHeader 사용하도록 치환

5. components/coach/CardSection.tsx 신규 — 조건부 wrapper
   - graceful 미렌더 로직을 한 곳에 박음 (length>0 / entries>0 조건)
   - ⚠ 이 로직을 페이지로 옮기지 말 것 — 5 페이지에 조건 분기 분산됨(실측 (c)-1)
   - CommentaryCard 내부에서 각 optional 섹션을 CardSection으로 감쌈

6. CommentaryCard.tsx 재구성
   - 위 자산들을 사용하도록 내부 재작성: <BaseCard>{<CardSection>...섹션들}</BaseCard>
   - props 시그니처 { output: CommentaryCardData } 무변경
   - 5 화면 page.tsx 무수정 (CommentaryCard 호출부 그대로)

Step 0 KPI:

- vitest 25 files / 115 tests 전건 통과 (행위 보존 — 신규 자산 테스트로 인한
  +N은 허용, 기존 115 감소 0)
- tsc exit 0
- testId='commentary-card' 단언 5 화면 무변경 통과
- 신규 자산 단위 테스트: ConfidenceBadge / BaseCard / SectionHeader / CardSection

---

## PART 1 — E4 ConfidenceBadge 채택 (커밋: refactor: E4MessageBubble ConfidenceBadge 채택)

목표: E4MessageBubble이 Step 0에서 만든 ConfidenceBadge를 채택해
CONFIDENCE_STYLE + 배지 마크업 중복을 완전 해소. 말풍선 외형은 100% 보존.

대상: frontend/components/coach/E4MessageBubble.tsx

1. E4MessageBubble 내 confidence 배지 부분을 <ConfidenceBadge>로 치환
   - assistant 말풍선 안 confidence 표시 위치에 ConfidenceBadge 삽입
2. ⚠ 보존 필수 — E4 말풍선 wrapper(좌/우 정렬, bubble 마크업)는 그대로.
   BaseCard import 금지. summary/key_observations 렌더 방식 무변경
3. Step 0에서 E4MessageBubble의 CONFIDENCE_STYLE 로컬 정의가 이미 제거됐는지 확인
   (Step 0-1에서 처리 — Part 1은 배지 컴포넌트 치환만)

Part 1 KPI:

- vitest 전건 통과, tsc exit 0
- testId='e4-bubble-assistant' / 'e4-bubble-user' 단언 무변경 통과
- E4 말풍선 시각 회귀 0 — 말풍선 정렬/외형 테스트로 확인
- CONFIDENCE_STYLE·배지 마크업 중복 grep 0건 확인

---

## 이후 Part (이 지시서 범위 밖 — 예고)

- Part 2: E2·E6 → <QuotedMetricsSection> 추출 (Group B, 회귀 낮음)
- Part 3: E1·E3 → <ActionItemsSection> + <RiskFlagsSection> (Group A, PRIORITY_STYLE 동반)
- Part 4: E5 → 두 section 조합 검증 (Group A+B 동시 보유 — 조합 회귀 게이트)
- Closing: §3 노트 갱신(경계 규칙 명문화) + #21 metrics_table deprecated 처리 판단
  - #71 무재발 확인 → 해소 검토

## 회귀 / HALT 규칙

- 작업 시작 시 vitest baseline 재확인 (25 files / 115 tests).
- 행위 보존 단계(Step 0)는 기존 115 통과 수 감소 0이 절대 조건. 감소 시 즉시 HALT.
- 타입 계약(CommentaryCardData) 변경·codegen 직접 사용 발견 시 즉시 HALT 후 보고.
- E4MessageBubble이 BaseCard를 import하게 되는 변경 발견 시 HALT (안 B 위반).
