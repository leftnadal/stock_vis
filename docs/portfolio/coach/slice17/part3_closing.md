# Slice 17 Part 3 종결 — ActionItemsSection + RiskFlagsSection 추출 (Group A: E1·E3)

> 슬라이스: Slice 17 (CommentaryCard → BaseCard + EP별 Section 분할)
> 단계: Part 3 (Group A: action_items + risk_flags — E1·E3 동형, strangler 3순위)
> 베이스: Part 2 종결 `909bb34`
> 종결 commit: 본 문서 직전 P3-D 커밋
> Part 3 LLM 비용: **$0** (프론트 리팩터링)

---

## 0. 한 줄 결과

CommentaryCard에서 action_items(L63-87) + risk_flags(L94-105) 두 인라인 블록을 ActionItemsSection / RiskFlagsSection으로 행위 보존 추출 + PRIORITY_STYLE 사전을 ActionItemsSection으로 응집(Part 2 formatQuotedMetricValue 패턴 재사용). 외형 wrapper 신규 생성 0, priority/confidence 별개 원자 분리 유지(안 B 정합). 회귀 무손실(vitest 32 files / 152 tests, tsc exit 0). E1·E3 회귀 격리 + E2·E5·E6 영향 0.

---

## 1. Part 3 KPI 매트릭스 — 6/6 통과

| # | KPI | 결과 |
|---|---|---|
| P3-K1 | 기존 140 무손실 + 신규 +12 | vitest 140 → 152 (+12) ✅ |
| P3-K2 | tsc exit 0 | ✅ |
| P3-K3 | E1·E3 testId='commentary-card' 단언 무변경 | 전체 통과 ✅ |
| P3-K4 | E2·E6 무영향, E5 격리 (action_items 보유하나 자동 수혜) | 전체 통과 ✅ |
| P3-K5 | PRIORITY_STYLE grep — ActionItemsSection 내부 1건만 | ✅ |
| P3-K6 | ListChecks / AlertTriangle grep — 각 Section 컴포넌트로만 | ✅ |

---

## 2. P3-A — ActionItemsSection 추출 + PRIORITY_STYLE 응집

### 신규
- `frontend/components/coach/ActionItemsSection.tsx`
  - props: `{ actionItems: CommentaryActionItem[] }`
  - SectionHeader(ListChecks + '추천 액션') + 항목 li/priority 배지 마크업 보존
  - **PRIORITY_STYLE 사전 흡수** — CommentaryCard L36-40에서 이전, 단일 사용처 응집
  - priority 배지는 action_items 전용 원자 — ConfidenceBadge와 통합 금지(안 B 정합)
  - 조건부 가시성은 호출처(CardSection visible)에 위임

### 변경
- `frontend/components/coach/CommentaryCard.tsx`
  - action_items 인라인 블록 → `<ActionItemsSection>` 치환
  - PRIORITY_STYLE 정의 / ListChecks import / CommentaryActionItem·CommentaryActionPriority 타입 import 제거
  - 변수명 단순화 (actionItems 타입 추론)

### 단위 테스트 (8건)
| 케이스 | 검증 |
|------|------|
| 항목 title/description 렌더 | 3 항목 모두 출력 |
| priority 3 라벨 (즉시 / 단기 / 장기) | 라벨 텍스트 |
| priority high 배지 | bg-red-50 text-red-700 border-red-200 |
| priority medium 배지 | bg-yellow-50 text-yellow-700 border-yellow-200 |
| priority low 배지 | bg-blue-50 text-blue-700 border-blue-200 |
| 빈 배열 헤더만 | ul 빈 채로 렌더 |
| SectionHeader ListChecks | text-emerald-500 보존 |
| 항목 li + priority 배지 같은 컨테이너 | 시각 회귀 0 |

### 커밋
`9412246` — `refactor(s17): ActionItemsSection 추출 + PRIORITY_STYLE 응집 (Group A: E1·E3, Part 3 P3-A)`

---

## 3. P3-B — RiskFlagsSection 추출

### 신규
- `frontend/components/coach/RiskFlagsSection.tsx`
  - props: `{ riskFlags: string[] }`
  - SectionHeader(AlertTriangle + '리스크') + ul amber-800 색상 보존
  - 단일 책임 — 가시성은 호출처에 위임

### 변경
- `frontend/components/coach/CommentaryCard.tsx`
  - risk_flags 인라인 블록 → `<RiskFlagsSection>` 치환
  - AlertTriangle import 제거 (Target만 남음 — Part 4에서 정리 후보)

### 단위 테스트 (4건)
| 케이스 | 검증 |
|------|------|
| 항목 렌더 | 2 항목 출력 |
| 빈 배열 헤더만 | ul 빈 채로 |
| SectionHeader AlertTriangle | text-amber-500 보존 |
| ul amber-800 색상 | 시각 회귀 0 |

### 커밋
`76a513b` — `refactor(s17): RiskFlagsSection 추출 (Group A: E1·E3·E6, Part 3 P3-B)`

---

## 4. P3-C — 격리 검증 (커밋 없음 — P3-A/B 회귀로 흡수)

| 검증 | 결과 |
|------|------|
| E1 페이지 테스트 무변경 통과 | ✅ |
| E3 페이지 테스트 무변경 통과 | ✅ |
| E2 페이지 영향 0 | ✅ (action_items / risk_flags 미보유) |
| E6 페이지 영향 0 | ✅ (risk_flags 보유 — 자동 수혜, 단언 무변경) |
| E5 페이지 무변경 (action_items 보유) | ✅ (자동 수혜, Part 4 조합 검증 자연 게이트) |

---

## 5. 검증 grep (Part 3 KPI K5·K6)

| 대상 | 결과 |
|------|------|
| `PRIORITY_STYLE` 정의/사용처 | ActionItemsSection.tsx 1건만 (CommentaryCard 제거 확인) |
| `ListChecks` in `coach/` | ActionItemsSection.tsx만 (CommentaryCard import 제거) |
| `AlertTriangle` in `coach/` | RiskFlagsSection.tsx만 (CommentaryCard import 제거) |
| CommentaryCard action/risk 인라인 마크업 | 0 (주석만 잔재) |
| `ConfidenceBadge`에 `PRIORITY` 0건 | ✅ priority/confidence 별개 원자 (안 B 정합) |

---

## 6. 회귀 매트릭스

| 트랙 | Part 2 종결 (`909bb34`) | Part 3 종결 (P3-A `9412246` + P3-B `76a513b` + 본 P3-D) | 변동 |
|------|--------------------------|---------------------------------------------------------|------|
| vitest test files | 30 | **32** | +2 |
| vitest tests | 140 | **152** | +12 |
| tsc --noEmit | exit 0 | exit 0 | 0 |
| 행위 보존 | 140 baseline | 140 무손실 | 0 회귀 |

---

## 7. 커밋 (Part 3, 3건)

| Commit | 단계 | 의미 |
|---|---|---|
| `9412246` | P3-A | refactor: ActionItemsSection + PRIORITY_STYLE 응집 + 8 테스트 |
| `76a513b` | P3-B | refactor: RiskFlagsSection + 4 테스트 |
| (본 커밋) | P3-D | docs: Slice 17 Part 3 closing |

---

## 8. 안 B 경계 규칙 정합 (누적, Part 3 시점)

| 검증 항목 | 결과 |
|----------|------|
| ActionItemsSection / RiskFlagsSection이 외형 wrapper 흡수 금지 | ✅ SectionHeader + 본문 마크업만 |
| priority 배지가 ConfidenceBadge와 별개 원자 | ✅ 통합 금지 정합 (grep 0건) |
| E4MessageBubble은 action/risk 사용처 아님 (E4Output 미보유) | ✅ 영향 0 |
| 공유 = 원자(ConfidenceBadge) + 4 섹션(Quoted/Action/Risk/...) 단위 | ✅ |
| 카드 wrapper(BaseCard)와 말풍선 wrapper 분리 유지 | ✅ |

---

## 9. CommentaryCard 잔여 상태 (Part 3 종결 시점)

```tsx
<BaseCard summary confidence>
  ── 핵심 관찰 ──            ← key_observations 인라인 (5 EP 공통)
  <CardSection><SectionHeader Target/> + ul ...>

  <CardSection><ActionItemsSection .../>           ← 추출 완료
  <CardSection><QuotedMetricsSection .../>         ← 추출 완료
  <CardSection><RiskFlagsSection .../>             ← 추출 완료
</BaseCard>
```

- 인라인 잔재: `key_observations` 1건 (Target 아이콘 + ul)
- import 잔재: `Target` lucide 아이콘 1건 (Part 4 또는 closing에서 KeyObservationsSection 추출 시 정리)

---

## 10. HALT 발동 이력 (Part 3)

| 시점 | 유형 | 결과 |
|------|------|------|
| (없음) | 140 무손실 + 격리 + grep 5건 모두 정상 | — |

---

## 11. Part 4 진입 메모

지시서 §이후 Part 예고 + 본 Part §3·9:
- **Part 4**: E5 두 section(action_items + quoted_metrics) 조합 검증 = 분할 최종 게이트
  - E5는 Group A·B 양쪽 보유 — 본 Part까지의 분리 완성도가 자연 검증됨
  - `e5-page.test.tsx` 8건이 무변경 통과하는지 명시 검증
- **KeyObservationsSection 추출 검토** — 잔재 인라인 블록 정리. 5 EP 공통이라
  자체로 가치 있음 (Part 4 또는 closing에서 결정)
- **Closing 후보 작업**: §3 경계 명문화 + #21 metrics_table deprecated 판단 + #71 해소 검토

Part 4 진입 시 baseline:
- HEAD = 본 P3-D 커밋
- vitest 32 files / 152 tests + tsc exit 0
- working tree clean

---

## 12. 누적 진행 (Slice 17, Part 3 종결 시점)

| Part | 신규 자산 | 단위 테스트 | vitest 누적 | 누적 commit |
|------|----------|------------|------------|------------|
| Step 0 | styles + ConfidenceBadge + BaseCard + SectionHeader + CardSection (5) | 15 | 130 | 1 (`4065fc2`) |
| Part 1 | (E4 ConfidenceBadge 채택 + size variant) | 2 | 132 | 2 (`51ab468`) |
| Part 2 | QuotedMetricsSection + formatQuotedMetricValue 응집 | 8 | 140 | 4 (`2cf62ab` + `909bb34`) |
| **Part 3** | **ActionItemsSection + RiskFlagsSection + PRIORITY_STYLE 응집** | **12** | **152** | **7 (`9412246` + `76a513b` + 본 P3-D)** |
| (예고) Part 4 | E5 조합 검증 (+ KeyObservationsSection 후보) | — | — | — |
| (예고) Closing | §3 명문화 + #21 / #71 정리 | — | — | — |

누적 LLM 비용: **$0** (프론트 리팩터링).
