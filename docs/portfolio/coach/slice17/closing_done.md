# Slice 17 종결 보고서 — CommentaryCard 분할 완성 + 부채 정리

> 슬라이스: Slice 17 (CommentaryCard → BaseCard + EP별 Section 분할)
> 베이스: slice16 종결 `a621b50` (외부 자동화 `61cbb7f` 격리, 직접 분기)
> 종결 commit: 본 문서 직전 C-D 커밋
> 누적 LLM 비용: **$0** (프론트 리팩터링)
> 누적 commit: **12건** (Step 0 1 + Part 1 1 + Part 2 2 + Part 3 3 + Part 4 3 + Closing 2)
> ⚠ Slice 17 closing 지시서 본문은 `closing.md`에 보존됨. 본 문서는 종결 보고서로
> 별도 파일(`closing_done.md`)로 작성.

---

## 1줄 요약

CommentaryCard 154줄 비대 컴포넌트를 5 Part 점진 분할(Step 0 + Part 1~4)로 **순수 조립부 + 9 컴포넌트 + 47 테스트**로 재구성. 안 B 경계 규칙(원자·섹션 공유 OK / 외형 wrapper 비공유) 정착 + 코드 주석 박음(`component_boundaries.md` 영구 노트). 회귀 0(vitest 25/115 → 34/162, +9 files / +47 tests), tsc 전 구간 exit 0, HALT 0회. 부채 정리: #71 조건부 close + #21 부분 close + #21-b·#73 신규.

---

## 핵심 수치

| 항목 | 값 |
|------|-----|
| 누적 commit | 12 |
| 누적 LLM 비용 | $0 |
| 회귀 시작 (Slice 16 종결) | vitest 25 files / 115 tests, tsc exit 0 |
| 회귀 종결 | vitest **34 files / 162 tests**, tsc exit 0 |
| 행위 보존 (기존 115) | 전 구간 무손실 ✅ |
| vitest 누적 변동 | +9 files / +47 tests |
| 신규 컴포넌트 | 9 (5 Step 0 + 0 Part 1 + 1 Part 2 + 2 Part 3 + 1 Part 4) |
| 신규 테스트 | 47 (15 Step 0 + 2 Part 1 + 8 Part 2 + 12 Part 3 + 10 Part 4) |
| HALT 발동 | 0회 |
| IDENTICAL 31/31 | 백엔드 전용 / Slice 17 무관 (추적 대상 아님 명시) |

---

## 단계별 매트릭스

| 단계 | 커밋 | 신규 자산 | 단위/통합 테스트 | vitest 누적 | 핵심 |
|------|------|----------|------------------|------------|------|
| Step 0 | 1 (`4065fc2`) | styles + ConfidenceBadge + BaseCard + SectionHeader + CardSection (5) | 15 | 130 | 공통 자산 행위보존 추출, testId 위임 |
| Part 1 | 1 (`51ab468`) | (E4 ConfidenceBadge 채택 + size variant) | 2 | 132 | 안 B 핵심 — size variant로 카드/말풍선 시각 회귀 0 |
| Part 2 | 2 (`2cf62ab` + `909bb34`) | QuotedMetricsSection + formatQuotedMetricValue 응집 | 8 | 140 | Group B, 회귀 위험 낮음 |
| Part 3 | 3 (`9412246` + `76a513b` + `d7626fb`) | ActionItemsSection + RiskFlagsSection + PRIORITY_STYLE 응집 | 12 | 152 | Group A, priority vs confidence 별개 원자 유지 |
| Part 4 | 3 (`9edd0c9` + `663290c` + `09c76f2`) | KeyObservationsSection + 조립부 통합 테스트 | 10 | 162 | 분할 최종 — CommentaryCard 인라인 0건 + E5 4-Section 조합 검증 |
| Closing | 2 (`02eefdb` + 본 C-D) | (#21 부분 close + 부채 정리 + §3 명문화) | 0 | 162 | 안 B 정합 박음, 백엔드 무변경 |

---

## 컴포넌트 최종 구조

```
frontend/components/coach/
├── BaseCard.tsx              [Step 0]   카드 wrapper, 5 카드형 EP 전용
├── E4MessageBubble.tsx       [Slice 16 + Part 1]  말풍선 wrapper, E4 전용
├── CardSection.tsx           [Step 0]   조건부 wrapper (graceful 미렌더)
├── SectionHeader.tsx         [Step 0]   icon + h3 패턴
├── ConfidenceBadge.tsx       [Step 0 + Part 1] 원자 + size variant (md/sm)
├── KeyObservationsSection.tsx [Part 4]  ⭐ 6 EP 공통
├── ActionItemsSection.tsx    [Part 3]   E1·E3·E5 (PRIORITY_STYLE 흡수)
├── QuotedMetricsSection.tsx  [Part 2]   E2·E5·E6 (formatQuotedMetricValue 흡수)
├── RiskFlagsSection.tsx      [Part 3]   E1·E3·E6
└── CommentaryCard.tsx        [재구성]   순수 조립부 (인라인 0)

frontend/lib/coach/
└── styles.ts                 [Step 0]   CONFIDENCE_STYLE 단일 소스
```

---

## CommentaryCard 최종 (분할 완성 시점)

```tsx
<BaseCard summary confidence>
  <CardSection visible={observations.length > 0}>
    <KeyObservationsSection .../>
  </CardSection>
  <CardSection visible={actionItems.length > 0}>
    <ActionItemsSection .../>
  </CardSection>
  <CardSection visible={hasQuotedMetrics}>
    <QuotedMetricsSection .../>
  </CardSection>
  <CardSection visible={riskFlags.length > 0}>
    <RiskFlagsSection .../>
  </CardSection>
</BaseCard>
```

- 인라인 렌더 0건 (lucide / ul / li / map 모두 0)
- props 시그니처 `{ output: CommentaryCardData }` 무변경 (5 화면 호출부 무수정)
- Section 배치 순서: KeyObservations → ActionItems → QuotedMetrics → RiskFlags

---

## 안 B 경계 규칙 (Slice 17 영구 명문화)

> 공유 가능 = EP 무관 동일 의미의 원자(ConfidenceBadge) + 단일 책임 섹션(5건).
> 공유 금지 = 카드/말풍선 wrapper 등 EP 표현 정체성 결정 외형 컨테이너.

상세는 `docs/portfolio/coach/component_boundaries.md` 영구 노트 참조. 향후 신규 진입점/리팩터링은 본 규칙을 단일 진실로 사용.

명시 금지 누적:
1. E4MessageBubble → BaseCard import 금지
2. priority 배지 → ConfidenceBadge 통합 금지
3. Section 컴포넌트 → 외형 wrapper 신규 생성 금지
4. graceful 미렌더 로직 → 페이지로 분산 금지 (CardSection 내부 박음)

---

## 부채 변동 (Slice 17 전체)

### close
| # | 처리 | 사유 |
|---|------|------|
| #71 | 조건부 close | iron-trading 폴더 분리 회피책 + Slice 16+17 무재발(32 commit) — Slice 16 closing 정의 조건 충족. ⚠ 근본 해결 아님 |
| #21 | 부분 close | CommentaryCardData.metrics_table 프론트 제거. 백엔드 잔여는 #21-b로 분리 |

### 신규
| # | PS | 사유 |
|---|----|------|
| #21-b | 1.0 | metrics_table 백엔드 스키마 잔여 — Slice 18+ 백엔드 트랙 |
| #73 | 0.5 | pre-commit hook 화이트리스트 슬라이스마다 수동 추가 (편의 부채) |

### 변동 net
- close 2건(#71 + #21) + 신규 2건(#21-b + #73) → 수 net 0
- 단 #21 부분 close라 PS 가중치 감소 (실질 부채 감소)

---

## 회귀 매트릭스 (전 구간)

| 단계 | vitest files | vitest tests | tsc | 행위 보존 (기존 115) |
|------|--------------|--------------|-----|---------------------|
| 진입 (slice16 `a621b50`) | 25 | 115 | exit 0 | baseline |
| Step 0 종결 | 29 | 130 | exit 0 | 115 무손실 |
| Part 1 종결 | 29 | 132 | exit 0 | 115 무손실 |
| Part 2 종결 | 30 | 140 | exit 0 | 115 무손실 |
| Part 3 종결 | 32 | 152 | exit 0 | 115 무손실 |
| Part 4 종결 | 34 | 162 | exit 0 | 115 무손실 |
| **Closing 종결** | **34** | **162** | **exit 0** | **115 무손실** |

전 구간 행위 보존 무손실. HALT 0회.

---

## 커밋 (Slice 17, 12건)

| Commit | 단계 | 의미 |
|---|---|---|
| `4065fc2` | Step 0 | refactor: BaseCard 공통 자산 추출 (styles + 4 컴포넌트) + CommentaryCard 재구성 |
| `51ab468` | Part 1 | refactor: E4MessageBubble ConfidenceBadge 채택 + size variant |
| `2cf62ab` | Part 2 P2-A | refactor: QuotedMetricsSection 추출 + formatQuotedMetricValue 응집 |
| `909bb34` | Part 2 P2-D | docs: Part 2 closing |
| `9412246` | Part 3 P3-A | refactor: ActionItemsSection + PRIORITY_STYLE 응집 |
| `76a513b` | Part 3 P3-B | refactor: RiskFlagsSection 추출 |
| `d7626fb` | Part 3 P3-D | docs: Part 3 closing |
| `9edd0c9` | Part 4 P4-A | refactor: KeyObservationsSection + CommentaryCard 인라인 0건화 |
| `663290c` | Part 4 P4-C | test: 조립부 통합 테스트 6 시나리오 |
| `09c76f2` | Part 4 P4-D | docs: Part 4 closing |
| `02eefdb` | Closing C-A | refactor: metrics_table 프론트 타입 제거 (#21 부분 close) |
| (본 커밋) | Closing C-D | docs: §3 명문화 + 부채 갱신 + 종결 보고서 |

---

## 핵심 학습 (Slice 17)

### 1. Strangler 점진 분할의 효과
한 번에 폭파 없이 5 Part로 점진 추출. 각 단계에서 행위 보존 + 회귀 0 검증 → 누적 회귀 위험 0. Part 4 시점 E5 4-Section 조합 통합 테스트로 분할 완성 검증.

### 2. 응집 패턴 정립 (3회 적용)
- Part 2: `formatQuotedMetricValue` → QuotedMetricsSection 흡수
- Part 3: `PRIORITY_STYLE` → ActionItemsSection 흡수
- (Step 0): `CONFIDENCE_STYLE` → 별도 styles.ts (양쪽 소비)

단독 사용 헬퍼는 사용처로 응집, 양쪽 소비는 별도 단일 소스 — 두 패턴이 안정적.

### 3. 안 B(size variant) 효과
CommentaryCard 배지(md, px-3 py-1 text-xs)와 E4 말풍선 배지(sm, px-2 py-0.5 text-[11px])의 시각 차이를 size prop 도입으로 통합 + 시각 회귀 0 동시 달성. "동일 의미 / 다른 컨텍스트" 원자 컴포넌트의 표준 패턴.

### 4. CommentaryCardData 수동 합집합의 안정성
codegen 직접 사용 대신 수동 합집합을 유지한 덕에 metrics_table 제거를 프론트 단독으로 진행 가능(structural compat). 백엔드 스키마 영향 0. Slice 16 §3 일반화 결정의 효과 누적 입증.

### 5. testId 위임 패턴
BaseCard가 `testId='commentary-card'`를 노출 → CommentaryCard 5 화면 기존 테스트 단언이 자연스럽게 통과. 컴포넌트 분리 시 부모 testid를 자식 wrapper로 위임하는 패턴이 회귀 안전망.

### 6. 외부 자동화 격리 패턴
Slice 17 진입 시 외부 자동화 commit(`61cbb7f`)가 a621b50 위에 추가됐으나 slice17 브랜치를 a621b50에서 직접 분기 → 격리. 코드 영향 0, 회귀 0. #71 monitoring 패턴 유효성 재확인.

---

## Slice 18+ 후보 (closing에서 정리, 가중합은 다음 슬라이스 진입 시)

| 후보 | PS | 근거 |
|------|----|------|
| 응답 지연 UX 차별화 (E3 진행률) | 2.0 | Slice 16 closing 예약분, E3 ~30s 사용자 체감 큼 |
| #21-b metrics_table 백엔드 스키마 제거 | 1.0 | 본 슬라이스 분리 신규 |
| Pick<CommentaryCardData,...> EP별 타입 좁힘 | 1.5 | Slice 17 Part 4 예고분, 타입 안전성 ↑ |
| E4 대화 영속화 (zustand) | 1.0 | 실수요 신호 확인 후, 현재 useState 의도적 |
| codegen 직접 사용 검토 | 1.0 | CommentaryCardData 폐기 가능성 — 안전성 검증 필요 |
| 신규 EP 패턴 검증 | 1.0 | Section 추가만으로 흡수 가능한지 (안 B 규칙 적용성) |
| #73 pre-commit hook 자동 갱신 | 0.5 | 편의 부채, 우선순위 낮음 |

⚠ **로드맵 메모**: Slice 18은 종착점 아님. 후속 트랙 정리 시 ~Slice 20대 초반, Phase 2(#12 분석엔진 + Tier 2) 진입 시 그 이상. "MVP 종료 vs Phase 2 진입" 결정은 Slice 18 진입점 결정 시 별도 판단 필요.

---

## 종결 선언

✅ **CommentaryCard 분할 완성** (인라인 0건, 순수 조립부)
✅ **9 컴포넌트 + 47 테스트 신규** (회귀 0)
✅ **안 B 경계 규칙 영구 명문화** (`component_boundaries.md`)
✅ **부채 정리** (#71 조건부 close + #21 부분 close + #21-b·#73 신규)
✅ **백엔드 무변경** (commentary_output.py diff 0, IDENTICAL 31/31 무관)
✅ **비용 cap 0%** (LLM 호출 0)
✅ **HALT 0회**

Slice 17 종결.
