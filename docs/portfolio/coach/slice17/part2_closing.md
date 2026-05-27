# Slice 17 Part 2 종결 — QuotedMetricsSection 추출 (Group B: E2·E6)

> 슬라이스: Slice 17 (CommentaryCard → BaseCard + EP별 Section 분할)
> 단계: Part 2 (Group B: quoted_metrics — E2·E6 동형, strangler 2순위)
> 베이스: Step 0 + Part 1 종결 `51ab468`
> 종결 commit: 본 문서 직전 P2-D 커밋
> Part 2 LLM 비용: **$0** (프론트 리팩터링)

---

## 0. 한 줄 결과

CommentaryCard L93-107의 quoted_metrics 인라인 블록을 `QuotedMetricsSection`으로 행위 보존 추출 + `formatQuotedMetricValue` 헬퍼를 단일 사용처로 응집. 외형 wrapper 신규 생성 0. 회귀 무손실(vitest 30 files / 140 tests, tsc exit 0). E2·E6 회귀 격리 통과 + E1·E3·E5 영향 0 확인.

---

## 1. Part 2 KPI 매트릭스 — 5/5 통과

| # | KPI | 결과 |
|---|---|---|
| P2-K1 | 기존 132 무손실 + 신규 +8 | vitest 132 → 140 (+8) ✅ |
| P2-K2 | tsc exit 0 | ✅ |
| P2-K3 | E2·E6 testId='commentary-card' 단언 무변경 | 전체 통과로 확인 ✅ |
| P2-K4 | E1·E3·E5 격리 (영향 0) | 전체 통과로 확인 ✅ |
| P2-K5 | formatQuotedMetricValue 응집 grep | QuotedMetricsSection 내부 1건만 ✅ |

---

## 2. P2-A — QuotedMetricsSection 추출

### 신규
- `frontend/components/coach/QuotedMetricsSection.tsx`
  - props: `{ quotedMetrics: Record<string, unknown> }`
  - SectionHeader(BarChart3 + '인용 지표') + 기존 dl/dt/dd 마크업 보존 (시각 회귀 0)
  - `formatQuotedMetricValue` 헬퍼를 본 컴포넌트 내부로 이동
  - 조건부 가시성은 호출처(CardSection visible)에 위임 — 단일 책임
  - **외형 wrapper 신규 생성 0** (지시서 §1-1 명시) — SectionHeader + dl만

### 변경
- `frontend/components/coach/CommentaryCard.tsx`
  - quoted_metrics 인라인 블록 → `<QuotedMetricsSection>` 치환
  - `formatQuotedMetricValue` 정의 제거 (단일 사용처로 이동)
  - `BarChart3` import 제거
  - props 시그니처 `{ output: CommentaryCardData }` 무변경
  - PRIORITY_STYLE / action_items / risk_flags / key_observations는 무변경 (Part 3/4 분리 예정)

### 단위 테스트 (8건)
| 그룹 | 케이스 수 | 검증 |
|------|---------|------|
| QuotedMetricsSection | 3 | entries 렌더 / 빈 객체 dl 빈 채로 / BarChart3 아이콘 보존 |
| formatQuotedMetricValue | 5 | null·undefined → '-' / 정수 / 실수 toFixed(2) / string·boolean / object JSON.stringify |

### 커밋
`2cf62ab` — `refactor(s17): QuotedMetricsSection 추출 (Group B: E2·E6) + CommentaryCard 재구성 (Part 2 P2-A)`

---

## 3. P2-B — 격리 검증 (커밋 없음 — P2-A 회귀로 흡수)

| 검증 | 결과 |
|------|------|
| E2 페이지 테스트 무변경 통과 | ✅ (`e2-page.test.tsx` 6건 모두) |
| E6 페이지 테스트 무변경 통과 | ✅ (`e6-page.test.tsx` 6건 모두) |
| E1 페이지 무영향 | ✅ |
| E3 페이지 무영향 | ✅ |
| E5 페이지 무영향 | ✅ (Part 4 조합 검증 대상 — 본 Part는 격리 확인까지) |

---

## 4. 검증 grep (행위 보존 + 응집 확인)

| 대상 | 결과 |
|------|------|
| `formatQuotedMetricValue` 정의/사용처 | QuotedMetricsSection.tsx 내부만 (CommentaryCard 잔재 0) |
| `BarChart3` in `coach/` | QuotedMetricsSection.tsx만 (CommentaryCard import 제거) |
| CommentaryCard quoted_metrics 인라인 마크업 | 0 (변수명·주석만 잔재) |

---

## 5. 회귀 매트릭스

| 트랙 | Step 0 + Part 1 종결 (`51ab468`) | Part 2 종결 (`2cf62ab` + 본 커밋) | 변동 |
|------|----------------------------------|----------------------------------|------|
| vitest test files | 29 | **30** | +1 |
| vitest tests | 132 | **140** | +8 |
| tsc --noEmit | exit 0 | exit 0 | 0 |
| 행위 보존 (기존 132) | baseline | 132 무손실 | 0 회귀 |

---

## 6. 커밋 (Part 2, 2건)

| Commit | 단계 | 의미 |
|---|---|---|
| `2cf62ab` | P2-A | refactor: QuotedMetricsSection 추출 + CommentaryCard 재구성 + 단위 테스트 |
| (본 커밋) | P2-D | docs: Slice 17 Part 2 closing |

---

## 7. 안 B 경계 규칙 정합 (누적)

| 검증 항목 | 결과 |
|----------|------|
| QuotedMetricsSection이 외형 wrapper(card/bubble) 흡수 금지 | ✅ SectionHeader + dl만 |
| E4MessageBubble은 quoted_metrics 사용처 아님 (E4Output 미보유) | ✅ 영향 0 |
| 공유 = 원자(ConfidenceBadge) + 섹션(QuotedMetricsSection) 단위 | ✅ |
| 카드 wrapper(BaseCard)와 말풍선 wrapper는 여전히 분리 | ✅ |

---

## 8. HALT 발동 이력 (Part 2)

| 시점 | 유형 | 결과 |
|------|------|------|
| (없음) | 기존 132 무손실 + 격리 확인 + grep 통과 모두 정상 | — |

---

## 9. Part 3 진입 메모

지시서 §이후 Part 예고 + 본 Part §3:
- **Part 3**: E1·E3 → `<ActionItemsSection>` + `<RiskFlagsSection>` 추출 (Group A)
- **PRIORITY_STYLE 동반 이동** — CommentaryCard L36-40에서 ActionItemsSection 내부로 응집 (formatQuotedMetricValue 패턴 그대로)
- 회귀 위험: 중간 — 2 section 동시 추출 + priority 배지 스타일 응집
- E5는 양쪽(action_items + quoted_metrics) 보유 → Part 4 조합 검증의 자연 게이트

Part 3 진입 시 baseline:
- HEAD = 본 P2-D 커밋
- vitest 30 files / 140 tests + tsc exit 0
- working tree clean

---

## 10. 누적 진행 (Slice 17, Part 2 종결 시점)

| Part | 신규 자산 | 단위 테스트 | vitest 누적 | 누적 commit |
|------|----------|------------|------------|------------|
| Step 0 | styles + ConfidenceBadge + BaseCard + SectionHeader + CardSection (5) | 15 | 130 | 1 (`4065fc2`) |
| Part 1 | (E4 ConfidenceBadge 채택 + size variant) | 2 | 132 | 2 (`51ab468`) |
| **Part 2** | **QuotedMetricsSection + formatQuotedMetricValue 응집** | **8** | **140** | **4 (`2cf62ab` + 본 P2-D)** |
| (예고) Part 3 | ActionItemsSection + RiskFlagsSection + PRIORITY_STYLE 응집 | — | — | — |
| (예고) Part 4 | E5 조합 검증 | — | — | — |
| (예고) Closing | §3 경계 명문화 + #21 deprecated 판단 + #71 해소 검토 | — | — | — |

누적 LLM 비용: **$0** (프론트 리팩터링).
