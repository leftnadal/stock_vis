# Coach Component Boundaries — 공유 경계 규칙 (§3 영구 노트)

> **확정 시점**: Slice 17 Closing (2026-05-27)
> **목적**: 신규 진입점 추가·기존 컴포넌트 리팩터링 시 경계 판단의 단일 진실.
> **계승**: Slice 16 Part 5 §3 노트 ("E4 표현은 의도적 분기 — 향후 통일 금지")
> **분할 완성 결과**: Slice 17 4-Part 강행으로 도출된 안 B 경계 규칙.

---

## 규칙 (한 줄)

**공유 가능 = EP 무관 동일 의미의 원자/섹션. 공유 금지 = EP 표현 정체성을 결정하는 외형 컨테이너.**

---

## 분류

| 단위 | 분류 | 예시 | 위치 |
|------|------|------|------|
| 원자 표현 요소 | **공유 OK** | `ConfidenceBadge` (size variant로 카드/말풍선 호환), confidence 라벨 / 색상 사전 | `components/coach/ConfidenceBadge.tsx`, `lib/coach/styles.ts:CONFIDENCE_STYLE` |
| 단일 책임 섹션 | **공유 OK** | `KeyObservationsSection` / `ActionItemsSection` (PRIORITY_STYLE 흡수) / `QuotedMetricsSection` (formatQuotedMetricValue 흡수) / `RiskFlagsSection` | `components/coach/{Section}.tsx` |
| 카드 wrapper | **공유 금지** | `BaseCard` — 5 카드형 EP(E1·E2·E3·E5·E6) 전용 외형 컨테이너 | `components/coach/BaseCard.tsx` |
| 말풍선 wrapper | **공유 금지** | `E4MessageBubble` — E4 대화 진입점 외형 컨테이너 | `components/coach/E4MessageBubble.tsx` |

---

## 명시 금지 사항

1. **E4MessageBubble은 BaseCard를 import하지 않는다.** 말풍선과 카드는 EP 표현 정체성이 본질적으로 다른 컨테이너 — 통일 시도 금지 (Slice 16 §3 노트 계승).
2. **priority 배지를 ConfidenceBadge와 통합하지 않는다.** 같은 시각적 형태(rounded-full border)라도 의미가 다른 원자(액션 우선순위 vs 진단 신뢰도).
3. **외형 wrapper를 신규 생성한 Section 컴포넌트는 추가하지 않는다.** Section은 헤더 + 본문 마크업만 — 카드/말풍선 wrapper는 호출처(CommentaryCard / E4MessageBubble) 책임.
4. **graceful 미렌더 로직(`length > 0` 등)을 페이지 컴포넌트로 옮기지 않는다.** `CardSection visible=...` wrapper에 박아 5 페이지 분기 분산을 차단.

---

## 결정 근거

| 항목 | 근거 |
|------|------|
| 안 B (size variant) 채택 | E4 말풍선과 5 카드의 시각 회귀 0 보장 — 동일 의미 / 다른 컨텍스트 |
| BaseCard / 말풍선 분리 | E4 대화 UX는 단발 카드 UX와 본질 차이 (Slice 16 Part 5 결정 — 말풍선 안 C 확정) |
| Section 컴포넌트 = 단일 책임 | 4 Part 분리 후 회귀 0 + 6 화면 testId 단언 무변경 (Slice 17 분할 완성 시점 입증) |

---

## 적용 사례 (Slice 17 분할 완성 시점)

```
frontend/components/coach/
├── BaseCard.tsx              [카드 wrapper, 공유 금지]
├── E4MessageBubble.tsx       [말풍선 wrapper, 공유 금지]
├── CardSection.tsx           [조건부 wrapper, 공유 OK]
├── SectionHeader.tsx         [원자, 공유 OK]
├── ConfidenceBadge.tsx       [원자 + size variant, 공유 OK]
├── KeyObservationsSection.tsx [섹션, 공유 OK]
├── ActionItemsSection.tsx    [섹션 + PRIORITY_STYLE 응집, 공유 OK]
├── QuotedMetricsSection.tsx  [섹션 + formatQuotedMetricValue 응집, 공유 OK]
├── RiskFlagsSection.tsx      [섹션, 공유 OK]
└── CommentaryCard.tsx        [순수 조립부, 인라인 0 — 공유 OK 위치 / 카드 외형은 BaseCard에 위임]
```

---

## 신규 진입점 / 컴포넌트 추가 시 체크리스트

- [ ] 외형 컨테이너인가 → 진입점 전용으로 신규, 다른 EP와 공유 금지
- [ ] 단일 의미의 원자 / 섹션인가 → 공유 후보, 위 5 자산과 중복 점검 후 추가
- [ ] graceful 미렌더 로직은 CardSection 또는 동등 wrapper 안에 위치하는가
- [ ] 페이지가 mutation.data.output을 패스스루로 전달하는가 (변환 가공 0)

---

## 관련 부채 / 결정

- **#21 metrics_table 프론트 제거** (Slice 17 Closing C-A 부분 close)
  - 잔여: `#21-b` 백엔드 스키마 — Slice 18+ 백엔드 트랙
- **CommentaryCardData 수동 합집합 유지** — codegen 직접 사용은 Slice 18+ (구조 안전성 검증 후)
- **Pick<CommentaryCardData, ...> EP별 타입 좁힘** — Slice 18+ 후보 (지시서 Part 4 예고분)
