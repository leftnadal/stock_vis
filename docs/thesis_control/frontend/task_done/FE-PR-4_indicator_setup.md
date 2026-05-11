# FE-PR-4: 지표 설정 — 완료 보고서

> 완료일: 2026-03-13
> 브랜치: `feat/eod-dashboard-and-improvements`
> 설계 문서: `docs/thesis_control/thesis_control_phase1_frontend_FE_PR_4.md` (v2)

---

## 1. 구현 완료 파일 목록 (12개)

### 신규 생성 (5개)

| # | 파일 | 역할 | 줄 수 |
|---|------|------|-------|
| 1 | `components/thesis/indicators/IndicatorSetupCard.tsx` | 지표 카드 (토글/삭제 + 화살표 + 라벨) | 80 |
| 2 | `components/thesis/indicators/RecommendCard.tsx` | AI 추천 지표 카드 (Sparkles + 이유 + 추가 버튼) | 60 |
| 3 | `components/thesis/indicators/AddIndicatorSheet.tsx` | AI 추천 바텀시트 (추천 목록 + 전체 추가) | 83 |
| 4 | `lib/thesis/indicatorMutations.ts` | 지표 mutation 훅 3개 (add/remove/toggle) | 51 |
| 5 | `app/thesis/(list)/layout.tsx` | 목록 전용 레이아웃 (헤더 + AlertBell) | 19 |

### 기존 파일 수정 (5개)

| # | 파일 | 변경 내용 |
|---|------|----------|
| 6 | `lib/thesis/types.ts` | `ThesisIndicator` 확장 (data_source, data_params, weight, is_paused, current_score, created_at), `RecommendedIndicator`, `IndicatorCreatePayload`, `AutoRecommendResponse`, `TYPE_LABELS`, `DIRECTION_LABELS` 추가 |
| 7 | `lib/thesis/api.ts` | `autoRecommend`, `addIndicator`, `removeIndicator`, `toggleIndicator` 4개 메서드 추가 |
| 8 | `lib/thesis/queries.ts` | `useIndicators(thesisId)` 훅 추가, QUERY_KEYS에 `indicators` 키 추가 |
| 9 | `lib/thesis/mock.ts` | `MOCK_INDICATORS` (3개), `MOCK_RECOMMENDATIONS` (3개) 추가 |
| 10 | `app/thesis/layout.tsx` | 헤더 제거 → Toaster + fadeIn만 유지 (레이아웃 분리) |

### 전면 교체 (1개)

| # | 파일 | 변경 내용 | 줄 수 |
|---|------|----------|-------|
| 11 | `app/thesis/[thesisId]/indicators/page.tsx` | placeholder → 전체 구현 | 326 |

### 이동 (1개)

| # | 파일 | 변경 내용 |
|---|------|----------|
| 12 | `app/thesis/page.tsx` → `app/thesis/(list)/page.tsx` | Route Group 분리 (이중 헤더 방지) |

---

## 2. 핵심 구조 변경: Route Group 분리

### 2.1 변경 전 (PR-3)

```
app/thesis/
├── layout.tsx          ← 공유 헤더 (모든 /thesis/* 적용)
├── page.tsx            ← 목록
├── alerts/page.tsx     ← 알림
├── new/page.tsx        ← 빌더 (자체 헤더)
└── [thesisId]/
    ├── page.tsx        ← 대시보드 (자체 헤더)
    ├── indicators/     ← 지표 설정 (자체 헤더)
    └── close/          ← 마감 (자체 헤더)
```

**문제**: `layout.tsx`의 공유 헤더가 `new/`, `[thesisId]/` 등 자체 헤더가 있는 페이지에도 적용 → 이중 헤더.

### 2.2 변경 후 (PR-4)

```
app/thesis/
├── layout.tsx          ← Toaster + fadeIn만 (헤더 없음)
├── (list)/
│   ├── layout.tsx      ← 목록 전용 헤더 + AlertBell
│   ├── page.tsx        ← 목록
│   └── alerts/page.tsx ← 알림
├── new/page.tsx        ← 빌더 (자체 헤더, 풀스크린)
└── [thesisId]/
    ├── page.tsx        ← 대시보드 (자체 헤더, 풀스크린)
    ├── indicators/     ← 지표 설정 (자체 헤더, 풀스크린)
    └── close/          ← 마감 (자체 헤더, 풀스크린)
```

`(list)` Route Group은 URL에 영향 없이 레이아웃만 분리.

---

## 3. 컴포넌트 설계 상세

### 3.1 IndicatorSetupCard

| 영역 | 내용 |
|------|------|
| 좌측 | `ArrowIndicator` (current_arrow_degree 시각화) |
| 중앙 상단 | 지표명 + TYPE_LABELS 배지 + DIRECTION_LABELS 배지 |
| 중앙 하단 | "현재: {current_label}" |
| 우측 | Power 토글 (blue/gray) + Trash2 삭제 |

- `is_active=false` 시 전체 카드 `opacity-60`
- 삭제/토글 중 `disabled` 처리

### 3.2 RecommendCard

| 영역 | 내용 |
|------|------|
| 상단 | Sparkles + 지표명 + TYPE_LABELS 배지 + DIRECTION_LABELS 배지 |
| 중단 | AI 추천 이유 (reason 텍스트) |
| 우측 | Plus → Check 아이콘 (추가 전/후) |

### 3.3 AddIndicatorSheet

- BottomSheet 래퍼 사용
- 로딩: 3-dot bounce 애니메이션 + "AI가 지표를 고르는 중..."
- 빈 상태: "추천할 지표가 없어요."
- "전체 추가 (N개)" 버튼: 미추가 지표만 카운트
- 전부 추가 완료 시 → "완료" 버튼으로 전환

### 3.4 indicators/page.tsx 주요 Flow

```
마운트
├── useThesis(thesisId)          → 가설 제목/방향 표시
├── useIndicators(thesisId)      → 기존 지표 목록
├── ?auto=true                   → useEffect + useRef로 1회 자동 추천
│   └── fetchRecommendations()   → API 호출 (Mock: 1.5s 딜레이)
│       └── setSheetOpen(true)   → AddIndicatorSheet 열기
├── 지표 토글/삭제               → mutation + 캐시 무효화
│   └── Mock: setState 즉시 반영
└── "관제 시작하기 →"            → /thesis/{id} 대시보드로 이동
```

---

## 4. API 엔드포인트 정리

| 메서드 | URL | 요청 | 응답 | 용도 |
|--------|-----|------|------|------|
| POST | `/thesis/{id}/indicators/auto/` | `{ premise_id? }` | `AutoRecommendResponse` | AI 추천 |
| POST | `/thesis/{id}/indicators/` | `IndicatorCreatePayload` | `ThesisIndicator` | 지표 추가 |
| DELETE | `/thesis/{id}/indicators/{indicatorId}/` | — | — | 지표 삭제 |
| PATCH | `/thesis/{id}/indicators/{indicatorId}/` | `{ is_active }` | `ThesisIndicator` | 지표 토글 |

---

## 5. 공유 상수

```ts
// types.ts
export const TYPE_LABELS: Record<string, string> = {
  market_data: '시장', macro: '매크로', sentiment: '심리',
  technical: '기술적', custom: '커스텀',
}

export const DIRECTION_LABELS: Record<string, { text: string; className: string }> = {
  positive: { text: '↑ 유리', className: 'text-blue-400 bg-blue-900/30' },
  negative: { text: '↑ 불리', className: 'text-orange-400 bg-orange-900/30' },
}
```

IndicatorSetupCard, RecommendCard 양쪽에서 재사용.

---

## 6. Mock 모드 설계

### 6.1 Mock 지표 (3개)

| id | 이름 | 유형 | 방향 | 활성 |
|----|------|------|------|------|
| ind-1 | 외국인 순매수 추이 | market_data | positive | true |
| ind-2 | 원/달러 환율 | macro | negative | true |
| ind-3 | VIX (공포지수) | macro | negative | false |

### 6.2 Mock 추천 (3개)

| 이름 | data_source | 유형 | 방향 |
|------|-------------|------|------|
| KOSPI 지수 | fmp | market_data | positive |
| 미국 기준금리 | fred | macro | negative |
| RSI (14일) | fmp | technical | positive |

### 6.3 Mock 토글/삭제 즉시 반영

```ts
const [mockIndicators, setMockIndicators] = useState(MOCK_INDICATORS)
// 토글 → setMockIndicators(prev => prev.map(...))
// 삭제 → setMockIndicators(prev => prev.filter(...))
```

TanStack Query 캐시가 아닌 로컬 상태 직접 조작.

---

## 7. 설계 결정

| 결정 | 선택 | 근거 |
|------|------|------|
| Route Group 분리 | `(list)` group | 이중 헤더 방지, URL 변경 없음 |
| 지표 수동 추가 폼 | 제외 | data_source/data_params가 초보 사용자에게 과도하게 기술적 |
| 중복 추가 방지 | `addedNames` Set | 기존 지표 + 추가된 지표 모두 추적 |
| auto=true 1회 실행 | `useRef` flag | StrictMode 이중 실행 방지 |
| Mutation 분리 파일 | `indicatorMutations.ts` | queries.ts 비대화 방지 (PR-6에서 mutations.ts로 통합) |

---

## 8. 기술 검증 결과

| 검증 항목 | 결과 |
|----------|------|
| `tsc --noEmit` | 에러 0건 |
| `npm run build` | 성공, 모든 라우트 정상 |
| Mock 지표 목록 렌더링 | 3개 카드, 비활성 1개 opacity 적용 |
| Mock AI 추천 시트 | 1.5s 로딩 → 3개 추천 카드 |
| Mock 지표 토글 | 즉시 UI 반영 + toast |
| Mock 지표 삭제 | 즉시 UI 반영 + toast |
| Mock 전체 추가 | 순차 추가 → "완료" 버튼 전환 |
| `?auto=true` | 마운트 시 시트 자동 오픈 (1회) |

---

## 9. 기술 부채

| 부채 | 영향 | 해소 시점 |
|------|------|----------|
| `is_paused` vs `is_active` 중복 | 두 필드의 의미 구분 불명확 | 백엔드와 협의 후 통합 |
| 지표 수동 추가 폼 미구현 | AI 추천으로만 추가 가능 | Phase 3 검토 |
| `indicatorMutations.ts` 분리 | 네이밍 혼란 | PR-6에서 mutations.ts 통합 |
| addedNames 초기화 타이밍 | `useEffect` displayIndicators.length 의존 | 안정적 작동 확인, 모니터링 |

---

## 10. 후속 PR 연결

| 이 PR에서 만든 것 | 사용하는 PR |
|------------------|------------|
| IndicatorSetupCard | PR-4 전용 |
| AddIndicatorSheet + RecommendCard | PR-4 전용 |
| Route Group `(list)` 구조 | PR-5, PR-6 모두 이 구조 위에 구축 |
| indicatorMutations.ts | PR-6에서 mutations.ts로 통합 |
| TYPE_LABELS, DIRECTION_LABELS | PR-5 대시보드에서도 재사용 가능 |
| useIndicators 훅 | PR-5 대시보드에서 재사용 |
| MOCK_INDICATORS, MOCK_RECOMMENDATIONS | PR-4 전용 |
