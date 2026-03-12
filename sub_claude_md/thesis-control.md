# Thesis Control (가설 통제실)

## 개요

투자자가 자신의 투자 가설을 세우고, AI가 관련 지표를 추적하여 가설의 유효성을 시각적으로 보여주는 시스템.
숫자가 아닌 **방향성, 색상, 흐름**으로 투자 판단을 돕는다.

> 설계 문서: `docs/thesis_control/thesis_control_design.md`
> FE-PR-1 완료 보고서: `docs/thesis_control/frontend/task_done/FE-PR-1_routing_common_components.md`
> FE-PR-2 완료 보고서: `docs/thesis_control/frontend/task_done/FE-PR-2_thesis_list_page.md`

---

## 핵심 개념

| 개념 | 설명 |
|------|------|
| 가설 (Thesis) | 투자자의 투자 관점 ("KOSPI 상승", "반도체 섹터 강세" 등) |
| 전제 (Premise) | 가설을 뒷받침하는 하위 논리 ("외국인 매수 지속", "환율 안정" 등) |
| 지표 (Indicator) | 전제를 추적하는 데이터 포인트 (외국인 순매수, VIX 등) |
| 화살표 시스템 | 0°(강하게 지지) ~ 180°(강하게 반박), 5색상 단계 |
| 달 위상 | overall_score(-1~1)를 달 밝기로 시각화 |

---

## 아키텍처

### 백엔드 (Django)

- 앱: `thesis_control/`
- 모델: `Thesis`, `ThesisPremise`, `ThesisIndicator`, `ThesisAlert`
- 대화형 빌더: `ThesisConversationBuilder` (AI 가이드 가설 생성)
- API: `/api/v1/thesis/*`

### 프론트엔드 (Next.js)

```
frontend/
├── lib/
│   ├── api/authAxios.ts          # 공통 JWT Axios (AuthContext와 공유)
│   └── thesis/
│       ├── types.ts               # 전체 타입 정의
│       ├── utils.ts               # 색상/라벨/점수/relativeTime/정렬 매핑
│       ├── api.ts                 # thesisApi 클라이언트
│       ├── queries.ts             # TanStack Query hooks 7개
│       └── mock.ts                # Mock 데이터 (USE_MOCK 환경변수)
├── components/thesis/
│   ├── common/                    # ArrowIndicator, MoonPhase, IndicatorCard, ThesisBadge, AlertBell
│   ├── list/                      # ThesisListCard, TodayChangeCard, EntryPointGrid
│   ├── skeleton/                  # ThesisListSkeleton, ThesisDashboardSkeleton, ThesisAlertsSkeleton
│   └── index.ts                   # barrel (skeleton 미포함)
└── app/thesis/                    # 7개 라우트 (layout + 6 pages)
```

---

## 화살표 색상 체계

```
0°~35°   → #2563EB (진한 파랑)  → 강하게 지지
36°~71°  → #60A5FA (연한 파랑)  → 지지하는 편
72°~107° → #D1D5DB (밝은 회색)  → 중립          ← WCAG 대비 5:1
108°~143°→ #FB923C (주황)       → 약화하는 편
144°~180°→ #EF4444 (밝은 빨강)  → 강하게 반박    ← WCAG 대비 5:1
```

모든 경계값은 `<` 기준 통일. `Math.max(0, Math.min(180, degree))` 클램프.

---

## authAxios 공유 모듈

`lib/api/authAxios.ts` — JWT 인터셉터 단일 소스.

**3가지 방어:**
1. 단일 탭 Race Condition: `isRefreshing` + `pendingQueue`
2. 다중 탭 동기화: refresh 전 localStorage 재확인 + `storage` 이벤트
3. Token Rotation: `ROTATE_REFRESH_TOKENS=True` → `data.refresh` 저장

**공유 사용처:** `contexts/AuthContext.tsx`, `lib/thesis/api.ts`

---

## TanStack Query 전략

- 전역 설정 상속: staleTime=5min, gcTime=30min, retry=2
- thesis override: `refetchOnWindowFocus: true`, `retry: 1`
- `alertsCount` queryKey 분리 (staleTime 10분, alerts와 독립 캐시)

---

## 프론트엔드 PR 구조

| PR | 내용 | 상태 |
|----|------|------|
| FE-PR-1 | 라우팅 + 공통 컴포넌트 + authAxios | **완료** |
| FE-PR-2 | 가설 목록 + 오늘의 변화 + 진입점 + Mock + lucide 아이콘 | **완료** |
| FE-PR-3 | 대화형 빌더 | 예정 |
| FE-PR-4 | 지표 설정 | 예정 |
| FE-PR-5 | 관제실 대시보드 | 예정 |
| FE-PR-6 | 알림 + 마감 | 예정 |

---

## PR-2 추가 유틸

### stateToDisplay (리팩토링)

- 반환 타입: `{ label, colorClass, icon: ThesisStateIconKey }`
- 10개 상태 각각 고유 색상 + border 클래스 포함
- `ThesisStateIconKey` union type: 오타 컴파일 타임 방지

### relativeTime

- `lib/thesis/utils.ts` — 상대 시간 포맷 ("3시간 전", "2일 전" 등)
- 미래 시간 방어: `diff < 0` → "방금 전"
- 재사용: TodayChangeCard, 알림 목록(PR-6), 대시보드(PR-5)

### sortThesesByPriority

- `STATE_PRIORITY: Record<ThesisState, number>` — critical(0) ~ closed(7)
- 2차 정렬: `created_at` 최신순 (동순위 안정성)
- `useMemo`로 감싸서 불필요한 재정렬 방지

### Mock 모드

- `NEXT_PUBLIC_USE_MOCK=true` → `enabled: !USE_MOCK`으로 query 비활성화
- **주의**: Mock 데이터에 `Date.now()` 사용 금지 (hydration 불일치, 버그 #24)

---

## 주의사항

- `AuthContext.tsx`는 `authAxios` 공유 모듈을 import. 독자적인 axios/인터셉터 없음.
- tokenUtils 메서드명: `getAccess()`, `getRefresh()`, `setTokens()`, `setAccess()`, `clear()` (기존 `getAccessToken`/`clearTokens` 아님)
- skeleton은 barrel(`index.ts`)에 미포함 → 직접 import: `from '@/components/thesis/skeleton/ThesisSkeleton'`
- Header.tsx의 thesis 경로: `/thesis` (이전 `/thesis-control` 제거됨)
- **Next.js Client Component는 서버에서도 실행됨** — 모듈 레벨 `Date.now()`, `Math.random()` 사용 금지 (hydration 불일치)
