# Slice 17 Part 2 — QuotedMetricsSection 추출 (Group B: E2·E6)

## 0. 전제

- 브랜치: slice17, HEAD 51ab468 (작업 시작 시 checkout 확인)
- baseline: vitest 29 files / 132 tests + tsc exit 0
- 분할 순서: 실측 2순위 (Group B = quoted_metrics 보유 E2·E6 동형)
- 회귀 위험: 낮음 — quoted_metrics만 떼는 단일 책임, E5 영향 없음
- 비용: $0 (프론트 리팩터링, LLM 호출 없음)
- 안 B 경계 규칙 유지: 외형 컨테이너 공유 금지 / 원자·섹션 단위 공유 OK
- 회귀 게이트: 기존 132 무손실 + tsc exit 0. 감소 시 즉시 HALT.

## 0.1 실측 확정 사실

- quoted_metrics: CommentaryCard L120-135, 조건 Object.entries.length>0,
  아이콘 BarChart3, 보유 EP = E2·E6 (E5도 보유하나 Part 4에서 조합 검증)
- formatQuotedMetricValue: CommentaryCard L40-45, quoted_metrics 단독 사용 헬퍼
- Step 0 산출 자산: SectionHeader, CardSection 사용 가능
- CommentaryCardData.quoted_metrics: Record<string, unknown>, optional

## 1. P2-A — QuotedMetricsSection 컴포넌트 추출 (커밋: refactor: QuotedMetricsSection 추출)

대상: frontend/components/coach/

1. components/coach/QuotedMetricsSection.tsx 신규
   - props: { quotedMetrics: Record<string, unknown> }
   - CommentaryCard L120-135 quoted_metrics 렌더 블록 이전
   - SectionHeader(icon=BarChart3, title) 사용
   - formatQuotedMetricValue 헬퍼를 이 컴포넌트 내부로 이동
     (CommentaryCard L40-45 에서 제거 — quoted_metrics 단독 사용이므로 응집)
   - 조건부 렌더(entries.length>0)는 CardSection으로 감싸는 기존 패턴 유지
   - ⚠ 외형 wrapper 신규 생성 금지 — SectionHeader + 기존 마크업만

2. CommentaryCard.tsx 재구성
   - quoted_metrics 인라인 블록 → <QuotedMetricsSection> 치환
   - props 시그니처 { output: CommentaryCardData } 무변경
   - E2·E6 page.tsx 무수정 (CommentaryCard 호출부 그대로)
   - ⚠ key_observations / action_items / risk_flags 섹션은 이 Part에서 건드리지 않음

3. 단위 테스트 — **tests**/coach/QuotedMetricsSection.test.tsx 신규
   - entries 있을 때 렌더 / 빈 객체일 때 미렌더
   - formatQuotedMetricValue 값 포맷 단언

## 2. P2-B — Group B 화면 회귀 확인 (커밋 없음 — P2-A에 포함 가능)

- E2·E6 page 테스트의 testId='commentary-card' 단언 무변경 통과 확인
- quoted_metrics 렌더 결과가 Part 2 이전과 동일(행위 보존)
- E1·E3·E5 화면 테스트 영향 0 확인 (회귀 격리 검증)

## 3. P2-D — Part 2 closing (커밋: docs: Slice 17 Part 2 closing)

1. docs/portfolio/coach/slice17/part_2/closing.md 작성
   - P2-A 산출 요약, KPI 결과, vitest 통과 수 갱신
2. Part 3 예고 메모 (E1·E3 → ActionItemsSection + RiskFlagsSection,
   PRIORITY_STYLE 동반 이동)

## KPI

- vitest 기존 132 무손실 + QuotedMetricsSection 테스트 +N
- tsc exit 0
- E2·E6 testId='commentary-card' 단언 무변경 통과
- E1·E3·E5 화면 테스트 무영향 (격리 확인)
- formatQuotedMetricValue grep — QuotedMetricsSection 내부 1건만 (CommentaryCard에서 제거 확인)

## HALT 규칙

- 기존 132 통과 수 감소 시 즉시 HALT.
- CommentaryCardData 타입 계약 변경 발견 시 HALT (Slice 18+ 범위).
- quoted_metrics 외 섹션(action_items 등)에 손이 가면 HALT (Part 범위 일탈).
