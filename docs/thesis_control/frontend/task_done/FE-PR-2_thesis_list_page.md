# FE-PR-2: 첫 화면 — 가설 목록 + 오늘의 변화 + 진입점 — 완료 보고서

> 완료일: 2026-03-11
> 브랜치: `feat/eod-dashboard-and-improvements`
> 설계 문서: `docs/thesis_control/thesis_control_phase1_frontend_FE_PR_2.md` (v2.1)

---

## 1. 구현 완료 파일 목록 (10개)

### 신규 생성 (4개)

| # | 파일 | 역할 | 줄 수 |
|---|------|------|-------|
| 1 | `lib/thesis/mock.ts` | Mock 데이터 (3개 가설 + 3개 알림) + `USE_MOCK` 환경변수 플래그 | 95 |
| 2 | `components/thesis/list/ThesisListCard.tsx` | 가설 카드 (달 위상 + 배지 + target·추적일수 보조 정보) | 45 |
| 3 | `components/thesis/list/TodayChangeCard.tsx` | 오늘의 변화 알림 카드 (relativeTime 사용) | 33 |
| 4 | `components/thesis/list/EntryPointGrid.tsx` | 새 가설 진입점 버튼 그리드 (활성 2 + 준비 중 1) + 임시 Toast | 98 |

### 기존 파일 수정 (6개)

| # | 파일 | 변경 내용 | 스펙 항목 |
|---|------|----------|----------|
| 5 | `lib/thesis/types.ts` | `ThesisStateIconKey` union type 추가 (10개 키) | M6 |
| 6 | `lib/thesis/utils.ts` | stateToDisplay 용어+색상+icon 리팩토링, relativeTime 추가, sortThesesByPriority 추가 | R2, M6, M7, M8, P3, P4 |
| 7 | `lib/thesis/queries.ts` | useThesisList, useAlerts에 `options?: { enabled?: boolean }` 파라미터 추가 | M1, P2 |
| 8 | `components/thesis/common/ThesisBadge.tsx` | 이모지 → lucide-react 아이콘 + Record 타입 안전 매핑 | R1, M6 |
| 9 | `app/thesis/layout.tsx` | 헤더 sticky + backdrop-blur 적용 | R3 |
| 10 | `app/thesis/page.tsx` | skeleton placeholder → 3섹션 실제 구현으로 전면 교체 | M1, M4, M8, P5, P6 |

---

## 2. PR-1 리뷰 반영 상세

PR-1 완료 보고서의 전문가 리뷰에서 제기된 이슈들을 이 PR에서 해소.

### 2.1 즉시 반영 항목 (R1~R5)

| # | 이슈 | 변경 전 | 변경 후 | 파일 |
|---|------|---------|---------|------|
| R1 | ThesisBadge 이모지 렌더링 불일치 | `📈`, `📉`, `→` 이모지 | `TrendingUp`, `TrendingDown`, `Minus` 등 lucide 아이콘 | `ThesisBadge.tsx` |
| R2 | ThesisBadge gray 3개 상태 동일 | warming_up/expired/closed_neutral 모두 같은 gray | 각각 `text-gray-400 bg-gray-800`, `text-amber-400 bg-amber-900/30`, `text-gray-500 bg-gray-800/50` | `utils.ts` |
| R3 | 헤더 sticky 미적용 | 스크롤 시 사라짐 | `sticky top-0 z-10 bg-gray-950/95 backdrop-blur-sm` | `layout.tsx` |
| R4 | 중립 회색 대비 부족 | `#9CA3AF` (대비 ~3.2:1) | `#D1D5DB` (대비 ~5:1) | `utils.ts` (PR-2 이전 수정) |
| R5 | 강한 반박 빨강 대비 부족 | `#DC2626` (대비 ~3.8:1) | `#EF4444` (대비 ~5:1) | `utils.ts` (PR-2 이전 수정) |

> R4, R5는 PR-2 직전 커밋에서 이미 반영됨. 이 PR에서 utils.ts 전면 재작성 시 유지 확인 완료.

### 2.2 용어 개선 (투자 도메인 리뷰 반영)

| 변경 전 | 변경 후 | 적용 위치 |
|---------|---------|----------|
| "관제 중" | "추적 중" | `stateToDisplay`, page.tsx 섹션 타이틀 |
| "강화 추세" | "지지 신호 증가" | `stateToDisplay` |
| "약화 추세" | "반박 신호 증가" | `stateToDisplay` |
| "미적중" | "빗나감" | `stateToDisplay` |
| "중립 마감" | "미확정" | `stateToDisplay` |

---

## 3. v2→v2.1 핵심 변경사항 반영 상세

### M1: Mock 모드 네트워크 요청 차단

**문제**: Mock 데이터 사용 시에도 TanStack Query가 실제 API 호출 → 401 에러 콘솔 노이즈.

**해결**:
```ts
// queries.ts — optional 파라미터 추가
export function useThesisList(options?: { enabled?: boolean }) {
  return useQuery({
    queryKey: QUERY_KEYS.list,
    queryFn: () => thesisApi.list(),
    ...THESIS_DEFAULTS,
    ...options,  // enabled: false 시 queryFn 실행 차단
  })
}

// page.tsx — 호출부
const { data, isLoading, isError, refetch } = useThesisList({
  enabled: !USE_MOCK,
})
const theses = USE_MOCK ? MOCK_THESES : data
```

**하위 호환 (P2)**: 기존 호출부 `useThesisList()`, `useAlerts()`, `useAlerts(thesisId)` 시그니처 변경 없음. options는 새 호출부에서만 사용.

### M6: ThesisStateIconKey 타입 안전 체인

```
types.ts                     utils.ts                        ThesisBadge.tsx
ThesisStateIconKey  →  stateToDisplay() icon 필드  →  stateIconMap[icon] 인덱싱
(10개 union)            Record<ThesisState, ...>        Record<ThesisStateIconKey, Component>
```

어느 단계에서든 오타(`'trending_UP'` 등) 발생 시 `tsc`가 즉시 컴파일 에러로 잡아줌.

### M7: relativeTime 유틸 분리

TodayChangeCard 내부 함수에서 `lib/thesis/utils.ts`로 추출.

```ts
export function relativeTime(dateStr: string): string {
  const diff = Date.now() - new Date(dateStr).getTime()
  if (diff < 0) return '방금 전'  // P3: 미래 시간 방어
  const minutes = Math.floor(diff / 60000)
  if (minutes < 1)  return '방금 전'
  if (minutes < 60) return `${minutes}분 전`
  const hours = Math.floor(minutes / 60)
  if (hours < 24)   return `${hours}시간 전`
  const days = Math.floor(hours / 24)
  if (days < 7)     return `${days}일 전`
  return new Date(dateStr).toLocaleDateString('ko-KR', { month: 'short', day: 'numeric' })
}
```

재사용처: TodayChangeCard (이번 PR), 알림 목록 (FE-PR-6), 대시보드 (FE-PR-5).

### M8 + P4 + P5: 가설 정렬

```ts
const STATE_PRIORITY: Record<ThesisState, number> = {
  critical: 0, needs_review: 1, weakening: 2, strengthening: 3,
  active: 4, warming_up: 5, expired: 6,
  closed_correct: 7, closed_incorrect: 7, closed_neutral: 7,
}

export function sortThesesByPriority<T extends { current_state: ThesisState; created_at: string }>(
  theses: T[]
): T[] {
  return [...theses].sort(
    (a, b) =>
      (STATE_PRIORITY[a.current_state] ?? 99) - (STATE_PRIORITY[b.current_state] ?? 99) ||
      new Date(b.created_at).getTime() - new Date(a.created_at).getTime()  // P4: 2차 정렬
  )
}
```

- `Record<ThesisState, number>`: 새 상태 추가 시 `tsc` 누락 감지
- P4: 동순위 시 `created_at` 최신순 → 목록 순서 안정성
- P5: page.tsx에서 `useMemo`로 감싸 불필요한 재정렬 방지

```ts
// page.tsx
const sorted = useMemo(
  () => sortThesesByPriority(activeTheses),
  [JSON.stringify(activeTheses)]  // 배열 참조 안정화
)
```

---

## 4. 컴포넌트별 설계 상세

### 4.1 ThesisListCard

| 영역 | 내용 |
|------|------|
| 왼쪽 | MoonPhase (sm) — 가설 점수 달 위상 |
| 중앙 상단 | 가설 제목 (truncate) |
| 중앙 중간 | ThesisBadge (방향 아이콘 + 상태 아이콘 + 라벨) |
| 중앙 하단 | 보조 정보: `{target} · {N}일째 추적 중` |
| 오른쪽 | ChevronRight → 상세 페이지 이동 |

**P1 target null-safe**: `thesis.target?.trim()` — null, undefined, 빈문자열, 공백문자열 모두 방어. target이 falsy이면 추적 일수만 표시.

### 4.2 TodayChangeCard

| 영역 | 내용 |
|------|------|
| 왼쪽 | Bell 아이콘 (yellow) |
| 중앙 상단 | 알림 제목 |
| 중앙 하단 | 알림 메시지 (line-clamp-1) |
| 오른쪽 | relativeTime — "3시간 전" 등 |

Link href: `/thesis/{thesisId}?highlight={alertId}` — 관제실에서 해당 알림 하이라이트.

### 4.3 EntryPointGrid

| 버튼 | 상태 | 동작 |
|------|------|------|
| 내 생각 (MessageSquare) | 활성 | `/thesis/new?entry=free_text` 이동 |
| 오늘 이슈 (Newspaper) | 활성 | `/thesis/new?entry=news` 이동 |
| Chain Sight에서 (Link2) | 준비 중 | Toast "곧 열릴 기능이에요!" |

- 활성 2개: `grid-cols-2`로 한 행에 배치
- Chain Sight: `col-span-2`로 전체 너비, `opacity-60`, "준비 중" 뱃지

**임시 Toast (M5)**: DOM 직접 조작 방식. FE-PR-3에서 `sonner` 등 toast 라이브러리 도입 시 교체 예정. 중복 누적 방지(`document.getElementById` 체크) + 2초 자동 제거.

### 4.4 page.tsx 3섹션 구조

```
ThesisPage
├── ActiveThesesSection      ← 추적 중 가설 목록 (정렬 + useMemo)
│   ├── isLoading → ThesisListSkeleton
│   ├── isError   → 에러 UI + 새로고침 버튼
│   ├── 0개       → EmptyTheses (MoonPhase null + 안내)
│   └── N개       → ul > li > ThesisListCard
├── TodayChangesSection      ← 오늘의 변화 알림
│   ├── 0개 → "새로운 변화가 아직 없어요." (M4)
│   └── N개 → ul > li > TodayChangeCard (최대 3개)
└── NewThesisSection         ← 새 가설 진입점
    └── EntryPointGrid
```

---

## 5. Mock 데이터 설계

### 5.1 MOCK_THESES (3개)

| id | 가설 | 방향 | target | current_state | current_score | 정렬 우선순위 |
|----|------|------|--------|---------------|--------------|--------------|
| mock-3 | 중국 경기 둔화로 원자재 약세 전환 | bearish | DBC | **critical** | -0.65 | **0** (최상단) |
| mock-1 | AI 반도체 수요 증가로 NVIDIA 상승 지속 | bullish | NVDA | **strengthening** | 0.72 | **3** |
| mock-2 | 금리 인하 기대감으로 부동산 REITs 반등 | bullish | VNQ | **active** | 0.15 | **4** |

3가지 다른 우선순위를 포함하여 정렬(M8) 결과가 눈에 보이도록 설계.

### 5.2 MOCK_ALERTS (3개)

| id | 가설 | 유형 | 시간 |
|----|------|------|------|
| alert-1 | mock-1 (NVIDIA) | indicator_shift | 3시간 전 |
| alert-2 | mock-3 (원자재) | state_change | 8시간 전 |
| alert-3 | mock-2 (REITs) | indicator_shift | 1일 전 |

고정 ISO 문자열 사용: `Date.now()` 동적 생성 시 SSR/CSR hydration 불일치 발생하여 변경. relativeTime 검증은 고정 날짜로도 충분 ("N일 전" 형태).

### 5.3 Mock 모드 활성화

```ts
export const USE_MOCK = process.env.NEXT_PUBLIC_USE_MOCK === 'true'
```

`.env.local`에 `NEXT_PUBLIC_USE_MOCK=true` 추가. 백엔드 연동 후 `false`로 전환.

---

## 6. stateToDisplay 전면 리팩토링

### 6.1 변경 전 (PR-1)

```ts
export function stateToDisplay(state: ThesisState): { label: string; colorClass: string } {
  switch (state) {
    case 'warming_up':       return { label: '데이터 수집 중', colorClass: 'text-gray-400 bg-gray-800' }
    case 'active':           return { label: '관제 중',       colorClass: 'text-blue-400 bg-blue-900/50' }
    // ...
    default:                 return { label: '알 수 없음',    colorClass: 'text-gray-500 bg-gray-800' }
  }
}
```

**문제점**: (1) 반환 타입에 `icon` 필드 없음 (2) 용어 부정확 (3) gray 상태 3개 동일 색상 (4) `default` fallback이 `tsc` 누락 감지 차단 (5) `border` 클래스 미포함

### 6.2 변경 후 (PR-2)

```ts
interface StateDisplayInfo {
  label: string
  colorClass: string
  icon: ThesisStateIconKey  // string이 아닌 union type (M6)
}

export function stateToDisplay(state: ThesisState): StateDisplayInfo {
  const map: Record<ThesisState, StateDisplayInfo> = {
    warming_up:       { label: '데이터 수집 중', colorClass: 'text-gray-400 bg-gray-800 border-gray-700',       icon: 'loader' },
    active:           { label: '추적 중',        colorClass: 'text-blue-400 bg-blue-900/30 border-blue-800',     icon: 'eye' },
    strengthening:    { label: '지지 신호 증가', colorClass: 'text-green-400 bg-green-900/30 border-green-800',  icon: 'trending_up' },
    weakening:        { label: '반박 신호 증가', colorClass: 'text-orange-400 bg-orange-900/30 border-orange-800', icon: 'trending_down' },
    critical:         { label: '주의 필요',      colorClass: 'text-red-400 bg-red-900/30 border-red-800',        icon: 'alert_triangle' },
    needs_review:     { label: '점검 필요',      colorClass: 'text-yellow-400 bg-yellow-900/30 border-yellow-800', icon: 'clock' },
    expired:          { label: '기간 만료',      colorClass: 'text-amber-400 bg-amber-900/30 border-amber-800',  icon: 'timer' },
    closed_correct:   { label: '적중',           colorClass: 'text-green-400 bg-green-900/30 border-green-800',  icon: 'check_circle' },
    closed_incorrect: { label: '빗나감',         colorClass: 'text-red-400 bg-red-900/30 border-red-800',        icon: 'x_circle' },
    closed_neutral:   { label: '미확정',         colorClass: 'text-gray-500 bg-gray-800/50 border-gray-700',     icon: 'minus_circle' },
  }
  return map[state] ?? map.active
}
```

**개선 요약**:
- `Record<ThesisState, StateDisplayInfo>`: 새 상태 추가 시 `tsc` 누락 감지
- `icon: ThesisStateIconKey`: 오타 컴파일 타임 방지
- `border-*` 클래스 포함: ThesisBadge에서 `border` 속성 별도 추가 불필요
- 10개 상태 각각 고유 색상: warming_up(gray-400), expired(amber-400), closed_neutral(gray-500) 분리

---

## 7. ThesisBadge lucide 아이콘 전환 상세

### 7.1 아이콘 매핑

| 상태 | 변경 전 (이모지) | 변경 후 (lucide) |
|------|----------------|-----------------|
| warming_up | — | `Loader` |
| active | — | `Eye` |
| strengthening | — | `TrendingUp` |
| weakening | — | `TrendingDown` |
| critical | — | `AlertTriangle` |
| needs_review | — | `Clock` |
| expired | — | `Timer` |
| closed_correct | ✅ | `CheckCircle` |
| closed_incorrect | ❌ | `XCircle` |
| closed_neutral | ➖ | `MinusCircle` |

### 7.2 방향 아이콘 (별도)

| 방향 | 변경 전 | 변경 후 |
|------|---------|---------|
| bullish | 📈 | `TrendingUp` |
| bearish | 📉 | `TrendingDown` |
| neutral | → | `Minus` |

### 7.3 타입 안전 매핑

```ts
const stateIconMap: Record<ThesisStateIconKey, React.ComponentType<{ size?: number }>> = {
  loader: Loader, eye: Eye, trending_up: TrendingUp, ...
}

const directionIconMap: Record<Direction, React.ComponentType<{ size?: number }>> = {
  bullish: TrendingUp, bearish: TrendingDown, neutral: Minus,
}
```

두 맵 모두 `Record<K, V>` 사용 — 키 누락 시 `tsc` 컴파일 에러.

---

## 8. 기술 검증 결과

### 8.1 빌드 검증

| 검증 항목 | 결과 | 비고 |
|----------|------|------|
| `tsc --noEmit` | **통과** | TypeScript 에러 0개 |
| `npm run build` | **통과** | 19 pages, 모든 thesis 라우트 정상 등록 |
| HTTP 200 체크 (`/thesis`) | **통과** | `curl -s -o /dev/null -w "%{http_code}" http://localhost:3000/thesis` → 200 |

### 8.2 Mock 모드 검증 (M1)

| 시나리오 | 결과 | 비고 |
|---------|------|------|
| `NEXT_PUBLIC_USE_MOCK=true` 가설 카드 렌더링 | **통과** | 3개 카드, critical → strengthening → active 순 |
| `NEXT_PUBLIC_USE_MOCK=true` 알림 카드 렌더링 | **통과** | 3개 알림, "3시간 전", "8시간 전", "1일 전" |
| 콘솔 thesis API 요청/에러 | **0건** | Mock 모드에서 `enabled: false` 작동 확인 |

### 8.3 브라우저 UI 검증

| 시나리오 | 결과 | 비고 |
|---------|------|------|
| 가설 카드 target 표시 | **통과** | "NVDA · 375일째 추적 중" 등 |
| 가설 목록 순서 | **통과** | critical(mock-3) → strengthening(mock-1) → active(mock-2) |
| ThesisBadge lucide 아이콘 | **통과** | 이모지 없음, 모든 상태 아이콘 렌더링 |
| 시맨틱 HTML | **통과** | 가설/알림 목록 모두 `ul`/`li` (list/listitem) |
| 진입점 3개 표시 | **통과** | "내 생각", "오늘 이슈", "Chain Sight에서" (준비 중) |
| 헤더 sticky | **통과** | 스크롤 시 고정 유지 |
| relativeTime | **통과** | "3시간 전", "8시간 전", "1일 전" 올바르게 표시 |

### 8.4 접근성 검증

| 항목 | 결과 | 비고 |
|------|------|------|
| 중립 회색 `#D1D5DB` WCAG AA | **충족** | 대비 ~5:1 on `bg-gray-950` |
| 강한 반박 `#EF4444` WCAG AA | **충족** | 대비 ~5:1 on `bg-gray-950` |
| 시맨틱 HTML (`ul`/`li`) | **충족** | 스크린 리더에서 목록으로 인식 |
| 터치 타겟 | **충족** | 카드 전체 영역 `p-4` (최소 44×44px 이상) |

---

## 9. 설계 문서 vs 구현 차이점

| 항목 | 설계 문서 (v2.1) | 실제 구현 | 이유 |
|------|-----------------|----------|------|
| useMemo 의존성 | `[activeTheses]` | `[JSON.stringify(activeTheses)]` | `activeTheses`가 매 렌더마다 새 배열 참조 → JSON 문자열로 안정화 필요 |
| mock.ts Thesis 필드 | 설계 문서에 일부 필드만 명시 | `user`, `source_entry`, `outcome`, `outcome_note` 등 전체 필드 포함 | TypeScript strict mode에서 `Thesis` 인터페이스 전체 필드 필수 |
| mock.ts ThesisAlert 필드 | `indicator` 필드 미명시 | `indicator: null` 포함 | `ThesisAlert` 인터페이스에 `indicator` 필드 존재 |
| mock.ts 알림 타임스탬프 | `Date.now() - N` 동적 생성 | 고정 ISO 문자열 (`'2026-03-11T07:00:00Z'` 등) | `Date.now()` SSR/CSR 시점 차이 → hydration 불일치 에러 발생. 고정값으로 원천 해결 |
| `useUnreadAlertCount` | 설계 문서에서 수정 범위 밖 | 수정하지 않음 (PR-2 이전에 이미 `listAlerts()` + filter로 롤백 완료) | 기존 동작 유지 |

---

## 10. 파일별 변경 줄 수

| 파일 | 변경 유형 | 변경 전 줄 | 변경 후 줄 | 순 변경 |
|------|----------|-----------|-----------|--------|
| `lib/thesis/types.ts` | 수정 (추가) | 101 | 117 | +16 |
| `lib/thesis/utils.ts` | 전면 재작성 | 61 | 105 | +44 |
| `lib/thesis/queries.ts` | 수정 | 75 | 77 | +2 |
| `lib/thesis/mock.ts` | 신규 | 0 | 95 | +95 |
| `components/thesis/common/ThesisBadge.tsx` | 전면 재작성 | 33 | 51 | +18 |
| `components/thesis/list/ThesisListCard.tsx` | 신규 | 0 | 45 | +45 |
| `components/thesis/list/TodayChangeCard.tsx` | 신규 | 0 | 33 | +33 |
| `components/thesis/list/EntryPointGrid.tsx` | 신규 | 0 | 98 | +98 |
| `app/thesis/layout.tsx` | 수정 | 20 | 22 | +2 |
| `app/thesis/page.tsx` | 전면 교체 | 12 | 119 | +107 |
| **합계** | | **302** | **762** | **+460** |

---

## 11. 의존성 그래프

```
lib/thesis/types.ts (수정: ThesisStateIconKey 추가)
    │
    ├→ lib/thesis/utils.ts (수정: stateToDisplay, relativeTime, sortThesesByPriority)
    │       │
    │       ├→ components/thesis/common/ThesisBadge.tsx (수정: lucide 아이콘)
    │       │       │
    │       │       └→ components/thesis/list/ThesisListCard.tsx (신규)
    │       │
    │       ├→ components/thesis/list/TodayChangeCard.tsx (신규)
    │       │
    │       └→ app/thesis/page.tsx (전면 교체)
    │
    └→ lib/thesis/queries.ts (수정: enabled 옵션)

lib/thesis/mock.ts (신규, types만 의존)
    │
    └→ app/thesis/page.tsx

components/thesis/list/EntryPointGrid.tsx (신규, 독립)
    │
    └→ (page.tsx에서 import)

app/thesis/layout.tsx (수정: sticky, 독립)
```

---

## 12. 버그 수정 이력

| # | 내용 | 심각도 | 발견 시점 |
|---|------|--------|----------|
| 1 | MOCK_ALERTS `Date.now()` 동적 생성 → SSR/CSR hydration 불일치 | **Critical** | 구현 후 브라우저 테스트 |

**상세**: `mock.ts`에서 `new Date(Date.now() - 3 * 60 * 60 * 1000).toISOString()`으로 알림 타임스탬프를 생성. Next.js App Router는 `'use client'` 컴포넌트도 서버에서 pre-render하므로, 모듈 레벨의 `Date.now()`가 SSR 시점과 CSR hydration 시점에 다른 값을 생성. `relativeTime()` 결과가 서버("3시간 전")와 클라이언트("5시간 전")에서 달라져 hydration 불일치 에러 발생.

**해결**: 고정 ISO 문자열 (`'2026-03-11T07:00:00Z'` 등)로 교체. Mock 데이터 목적(UI 레이아웃 검증)에 동적 시간이 불필요하며, `relativeTime()`은 고정 날짜에서도 "N일 전" 형태로 정상 작동.

**교훈**: Next.js Client Component에서 모듈 레벨 `Date.now()`, `Math.random()` 등 비결정적 값 사용 금지. `useEffect` 또는 `suppressHydrationWarning`으로 우회하거나, 고정값 사용.

---

## 13. 기술 부채

| 부채 | 영향 | 해소 시점 |
|------|------|----------|
| 임시 Toast (DOM 직접 조작) | 테스트·접근성·애니메이션 제한 | FE-PR-3에서 sonner 등 toast 라이브러리 도입 |
| Mock 데이터 하드코딩 | 백엔드 연동 후 제거 필요 | 백엔드 연동 후 `USE_MOCK=false` + mock.ts 삭제 |
| 클라이언트 필터링 (`status === 'active'`) | 전체 가설 fetch 후 필터 | 백엔드 `?status=active` 쿼리 지원 시 서버 필터링 |
| relativeTime 실시간 갱신 누락 (P7) | 페이지 체류 시 시간 멈춤 | FE-PR-6에서 `setInterval` 또는 `timeago` 도입 |
| relativeTime 로케일 하드코딩 ('ko-KR') | 다국어 대응 불가 | 국제화 필요 시 i18n 유틸 전환 |
| ThesisBadge DirIcon + StateIcon 인지 부하 | 아이콘 2개 → 시각 혼잡 가능 | FE-PR-5에서 사용자 테스트 후 조정 검토 |
| "Chain Sight에서" 라벨 | 투자자에게 비직관적일 수 있음 | 추후 활성화 시 "연관 종목에서" 등으로 변경 검토 |
| useMemo 의존성 JSON.stringify | 대규모 배열 시 직렬화 비용 | 가설 수 수십 개 수준에서는 무시 가능, 확대 시 별도 비교 함수 |

---

## 14. 후속 PR 연결

| 이 PR에서 만든 것 | 사용하는 PR |
|------------------|------------|
| ThesisListCard | PR-2 전용 (재사용 없음) |
| TodayChangeCard | FE-PR-6 알림 목록에서 유사 패턴 재활용 |
| EntryPointGrid | FE-PR-3 빌더에서 `entry` 쿼리 파라미터 수신 처리 |
| Mock 데이터 | FE-PR-3~5에서 확장 (DashboardResponse mock 추가) |
| stateToDisplay 용어 변경 | 이후 모든 PR에서 자동 적용 |
| lucide 아이콘 (ThesisBadge) | 이후 모든 PR에서 자동 적용 |
| ThesisStateIconKey | FE-PR-5 대시보드에서 동일 타입 재사용 |
| relativeTime | FE-PR-5 대시보드, FE-PR-6 알림 목록에서 재사용 |
| sortThesesByPriority | FE-PR-5 대시보드 전제 정렬에 재사용 가능 |
| queries.ts enabled 옵션 패턴 | FE-PR-3~6에서 Mock 모드 동일 패턴 적용 |

---

## 15. 스펙 체크리스트 (v2.1 전항목)

| # | 항목 | 상태 |
|---|------|------|
| R1 | ThesisBadge 이모지 → lucide | ✅ |
| R2 | gray 3개 상태 색상 분리 | ✅ |
| R3 | 헤더 sticky | ✅ |
| R4 | 중립 회색 `#D1D5DB` | ✅ (PR-2 이전 반영) |
| R5 | 강한 반박 `#EF4444` | ✅ (PR-2 이전 반영) |
| M1 | Mock enabled:false | ✅ |
| M2 | 진입점 3개 축소 | ✅ |
| M3 | target + 추적 일수 표시 | ✅ |
| M4 | 시간 중립 문구 | ✅ |
| M5 | 임시 Toast 상세 주석 | ✅ |
| M6 | ThesisStateIconKey 타입 안전 | ✅ |
| M7 | relativeTime 유틸 분리 | ✅ |
| M8 | 상태 우선순위 정렬 | ✅ |
| P1 | target null-safe | ✅ |
| P2 | 기존 호출부 시그니처 불변 | ✅ |
| P3 | 미래 시간 방어 (diff < 0) | ✅ |
| P4 | 2차 정렬 (created_at) | ✅ |
| P5 | useMemo 감싸기 | ✅ |
| P6 | ul/li 시맨틱 HTML | ✅ |
| P7 | 실시간 갱신 부채 문서화 | ✅ (기술 부채 섹션) |

**전 항목 완료 (17/17 구현 + 2 사전반영 + 1 문서화 = 20/20)**
