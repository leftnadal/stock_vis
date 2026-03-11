# FE-PR-1: 라우팅 + 공통 컴포넌트 — 완료 보고서

> 완료일: 2026-03-11
> 브랜치: `feat/eod-dashboard-and-improvements`
> 설계 문서: `docs/thesis_control/thesis_control_phase1_frontend_FE_PR_1.md` (v4)

---

## 1. 구현 완료 파일 목록 (19개)

### 신규 생성 (17개)

| # | 파일 | 역할 |
|---|------|------|
| A | `lib/api/authAxios.ts` | 공통 인증 Axios 인스턴스 (JWT 인터셉터 단일 소스) |
| 1 | `lib/thesis/types.ts` | TypeScript 타입/인터페이스 전체 |
| 2 | `lib/thesis/utils.ts` | degreeToColor/Arrow/Label, scoreToPhaseMeta, stateToDisplay, daysWatching |
| 3 | `lib/thesis/api.ts` | thesisApi 클라이언트 (CRUD, 대화형 빌더, 지표, 알림, 마감) |
| 4 | `lib/thesis/queries.ts` | TanStack Query hooks 7개 (useThesisList, useThesis, useDashboard, useIndicators, useAlerts, useUnreadAlertCount) |
| 5 | `components/thesis/common/ArrowIndicator.tsx` | 화살표 각도 지표 (0~180deg, CSS rotate) |
| 6 | `components/thesis/common/MoonPhase.tsx` | 달 위상 점수 시각화 (lucide Moon SVG + clip-path) |
| 7 | `components/thesis/common/IndicatorCard.tsx` | 지표 카드 (ArrowIndicator + 이름 + 라벨) |
| 8 | `components/thesis/common/ThesisBadge.tsx` | 가설 상태 뱃지 (10개 상태) |
| 9 | `components/thesis/common/AlertBell.tsx` | 알림 벨 Client Island (useUnreadAlertCount) |
| 10 | `components/thesis/skeleton/ThesisSkeleton.tsx` | shimmer skeleton 3종 (List, Dashboard, Alerts) |
| 11 | `components/thesis/index.ts` | barrel re-export (skeleton 미포함) |
| 12 | `app/thesis/layout.tsx` | Server Component 레이아웃 (ArrowLeft + 타이틀 + AlertBell) |
| 13 | `app/thesis/page.tsx` | 가설 목록 skeleton 페이지 |
| 14 | `app/thesis/new/page.tsx` | 새 가설 만들기 placeholder |
| 15 | `app/thesis/[thesisId]/page.tsx` | 관제실 대시보드 skeleton 페이지 |
| 16 | `app/thesis/[thesisId]/indicators/page.tsx` | 지표 설정 placeholder |
| 17 | `app/thesis/[thesisId]/close/page.tsx` | 가설 마감 placeholder |
| 18 | `app/thesis/alerts/page.tsx` | 알림 목록 skeleton 페이지 |

### 기존 파일 수정 (2개)

| # | 파일 | 변경 내용 |
|---|------|----------|
| 19 | `contexts/AuthContext.tsx` | authAxios 공유 모듈 마이그레이션 + Token Rotation 대응 + createContext 추가 |
| 20 | `components/layout/Header.tsx` | `/thesis-control` -> `/thesis` (데스크톱 L60 + 모바일 L174) |

---

## 2. AuthContext 마이그레이션 상세

가장 위험도 높은 변경. 기존 AuthContext 내부의 axios 인스턴스 + tokenUtils + 인터셉터(약 50줄)를 `lib/api/authAxios.ts`로 추출.

### 변경된 메서드 매핑

| 기존 (AuthContext 내부) | 신규 (authAxios.ts) |
|------------------------|---------------------|
| `tokenUtils.getAccessToken()` | `tokenUtils.getAccess()` |
| `tokenUtils.getRefreshToken()` | `tokenUtils.getRefresh()` |
| `tokenUtils.clearTokens()` | `tokenUtils.clear()` |
| `tokenUtils.setTokens(a, r)` | `tokenUtils.setTokens(a, r)` (동일) |
| `axios.post(\`${API_URL}/...\`)` | `api.post('/...')` |
| `localStorage.setItem('access_token', access)` | `tokenUtils.setAccess(access)` |

### 수정된 함수 목록

- `verifyToken`: `getAccessToken` -> `getAccess`, `clearTokens` -> `clear`
- `login`: `axios.post` -> `api.post`, 경로 단축
- `signup`: `axios.post` -> `api.post`, 경로 단축
- `logout`: `getRefreshToken` -> `getRefresh`, `clearTokens` -> `clear`
- `refreshToken`: `getRefreshToken` -> `getRefresh`, `axios.post` -> `api.post`, Token Rotation 대응 추가 (`data.refresh` 저장)

### authAxios.ts 3가지 방어 메커니즘

| 방어 | 문제 | 해결 |
|------|------|------|
| (1) 단일 탭 Race Condition | 4개 API 동시 401 -> 4번 refresh 호출 | `isRefreshing` + `pendingQueue` |
| (2) 다중 탭 토큰 동기화 | 탭 A가 갱신한 토큰을 탭 B가 모름 | refresh 전 localStorage 재확인 + `storage` 이벤트 리스너 |
| (3) Token Rotation | `ROTATE_REFRESH_TOKENS=True` -> 구 refresh 블랙리스트 | `data.refresh` 존재 시 `setTokens()` 호출 |

---

## 3. 기술 검증 결과

| 검증 항목 | 결과 | 비고 |
|----------|------|------|
| `tsc --noEmit` | **통과** | TypeScript 에러 0개 |
| `npm run build` | **통과** | 19 pages, 모든 thesis 라우트 등록 |
| HTTP 200 체크 (6개 라우트) | **모두 통과** | `/thesis`, `/new`, `/alerts`, `/[thesisId]`, `/indicators`, `/close` |
| 브라우저 렌더링 | **정상** | 레이아웃, 헤더, AlertBell, placeholder 텍스트 확인 |
| 콘솔 에러 | **0개** | Chrome DevTools 확인 |
| Header `/thesis` 링크 | **정상** | 데스크톱 nav에서 `href="/thesis"` 확인 |

---

## 4. 전문가 리뷰 결과

### 4.1 UI/UX 디자이너 리뷰

#### P1 (즉시 반영 권장 — 후속 PR에서 처리)

| # | 이슈 | 현재 | 개선 방향 | 대상 파일 |
|---|------|------|----------|----------|
| U1 | 색상 대비 부족 (중립 회색) | `#9CA3AF` (대비 ~3.2:1) | `#D1D5DB` (대비 ~5:1) | `utils.ts` |
| U2 | 색상 대비 부족 (강한 반박 빨강) | `#DC2626` (대비 ~3.8:1) | `#EF4444` (대비 ~5:1) | `utils.ts` |
| U3 | MoonPhase null vs -1 구분 약함 | 둘 다 어두운 달, opacity 차이만 | null: 점선 원 or 별도 아이콘, -1: 선명한 어두운 달 | `MoonPhase.tsx` |
| U4 | 헤더 sticky 미적용 | 스크롤 시 사라짐 | `sticky top-0 z-10 bg-gray-950` | `layout.tsx` |

#### P2 (후속 PR에서 개선)

| # | 이슈 | 개선 방향 |
|---|------|----------|
| U5 | IndicatorCard 정보 순서 역전 | 이름을 상단으로, 화살표를 중앙으로 재배치 |
| U6 | IndicatorCard 이름 truncate | `line-clamp-2` 허용 (한글 지표명 2줄) |
| U7 | is_active=false opacity-40 너무 어두움 | opacity-60 + 툴팁 "비활성 지표" |
| U8 | ThesisBadge gray 3개 상태 동일 | warming_up/expired/closed_neutral 색상 분리 |
| U9 | ThesisBadge 이모지 렌더링 불일치 | lucide-react 아이콘으로 교체 (CheckCircle, XCircle 등) |
| U10 | Skeleton MoonPhase 크기 불일치 | h-12(48px) -> h-8(32px)로 실제 사이즈 맞춤 |
| U11 | Safe area inset 미고려 | `pb-[calc(5rem+env(safe-area-inset-bottom))]` |
| U12 | 화살표 유니코드 -> SVG 교체 권장 | SVG 화살표로 Retina/대각선 선명도 보장 |
| U13 | MoonPhase clip-path 방식 한계 | 두 개 반원 SVG 또는 반원형 게이지 대안 검토 |

#### 색상 체계 논의 (결정 필요)

현재: 파랑(지지) -> 빨강(반박)
대안 A (금융 컨벤션): 초록(지지) -> 빨강(반박) — Bloomberg/HTS 친숙
대안 B (현재 유지 + 라벨 강화): 파랑/주황 유지, 텍스트 라벨 필수 병기

> 색약 접근성: 파랑-주황은 제2색맹 OK. 초록-빨강은 적록색맹 문제 -> 형태(화살표 굵기) 병행 필요

---

### 4.2 투자 도메인 전문가 리뷰

#### 최우선 이슈 3가지

| # | 이슈 | 심각도 | 개선 방향 | 반영 시점 |
|---|------|--------|----------|----------|
| I1 | 확증 편향 강화 위험 | 높음 | 달 위상 라벨을 감성 -> 객관으로 변경 ("가설이 빛나고 있어요" -> "지표들이 가설 방향으로 움직이고 있어요") | FE-PR-5 (관제실) |
| I2 | 반박 신호 시각적 약함 | 높음 | 반박 지표에 경고 아이콘 추가, 색상 대비 강화 | FE-PR-5 |
| I3 | 대안 가설 자동 추천 부재 | 높음 | 가설 생성 후 "반대 가설도 만들까요?" AI 제안 | FE-PR-3 (빌더) |

#### 용어 개선 제안

| 현재 | 개선안 | 이유 |
|------|--------|------|
| "관제 중" | "추적 중" | 초급자 이해도 향상 |
| "강화 추세" | "지지 신호 증가" | 객관적 + 구체적 |
| "약화 추세" | "반박 신호 증가" | 객관적 |
| "전제" (Premise) | "배경" 또는 "근거" | 초급자 친화 |
| "중립 마감" | "미확정" | 의미 명확화 |

#### 추가 정보 요구 (중급자 이상)

| 항목 | 현재 | 필요 |
|------|------|------|
| 변화 속도 | 미표시 | "어제 대비 +5°" 같은 추세 방향 |
| 신뢰도 | 미표시 | "10개 지표 중 7개 지지" |
| 이전 상태 | 미표시 | 탭 시 카드 확장 -> 이전 vs 현재 비교 |

#### 투자자별 평가

| 투자자 | 현재 만족도 | 핵심 부족 |
|--------|-----------|----------|
| 초급 | 4/5 | 용어 모호 ("관제", "전제") |
| 중급 | 3/5 | 변화 속도, 신뢰도 정보 부족 |
| 고급 | 2.5/5 | 원본 데이터, 데이터 소스, 모멘텀 분석 부족 |

---

## 5. 설계 문서 vs 구현 차이점

| 항목 | 설계 문서 | 실제 구현 | 이유 |
|------|----------|----------|------|
| 화살표 색상 0° | 진한 빨강 | 진한 파랑 (#2563EB) | 코드 레벨에서 "파랑=지지" 컨벤션 채택 |
| MoonPhase 아이콘 | 이모지 (🌕) | lucide Moon SVG | 크로스 플랫폼 렌더링 일관성 |
| layout.tsx | Client Component | Server Component + AlertBell Client Island | 성능 최적화 (Server Component 유지) |
| useUnreadAlertCount | 전체 알림 fetch -> filter | 경량 `/alerts/unread-count/` 엔드포인트 | 대역폭 절약 (알림 누적 시 O(1)) |
| alertsCount queryKey | alerts와 공유 | 별도 `['thesis', 'alerts-count']` | TanStack Query v5 staleTime observer 충돌 방지 |

---

## 6. 후속 PR 의존성

| PR | 이 PR에서 사용할 것 | 추가 작업 필요 |
|----|-------------------|---------------|
| FE-PR-2 (가설 목록) | ThesisBadge, MoonPhase, useThesisList, ThesisListSkeleton | 목록 카드 컴포넌트 구현 |
| FE-PR-3 (대화형 빌더) | thesisApi.startConversation/sendMessage, ConversationResponse 타입 | 빌더 UI 구현 |
| FE-PR-4 (지표 설정) | IndicatorCard, ArrowIndicator, useIndicators | 지표 추가/삭제/수정 UI |
| FE-PR-5 (관제실) | useDashboard, MoonPhase, IndicatorCard, ThesisBadge, ThesisDashboardSkeleton | 대시보드 레이아웃 |
| FE-PR-6 (알림+마감) | useAlerts, ThesisAlertsSkeleton, thesisApi.close/markAlertRead | 알림 목록 + 마감 폼 |

### 백엔드 의존

| 엔드포인트 | 사용 위치 | 상태 |
|-----------|----------|------|
| `GET /thesis/alerts/unread-count/` | `useUnreadAlertCount` (AlertBell) | 백엔드 미구현 -> 404 시 `?? 0` fallback |
| 기타 thesis API 전체 | `thesisApi.*` | 백엔드 PR 완료 후 연동 |

---

## 7. 기술 부채

| 부채 | 영향 | 전환 비용 | 전환 시점 |
|------|------|----------|----------|
| localStorage 기반 인증 | SSR 데이터 페칭 불가 | `tokenUtils` 1파일 + 백엔드 미들웨어 | SEO/SSR 필요 시 |
| 이모지 아이콘 (ThesisBadge) | OS별 렌더링 차이 | lucide-react 아이콘 교체 | FE-PR-2 이전 |
| 화살표 유니코드 | 대각선 흐릿, 폰트 의존 | SVG 화살표 교체 | FE-PR-4~5 |

---

## 8. 버그 수정 이력 (v1~v4 + 구현 중)

| # | 내용 | 심각도 | 발견 시점 |
|---|------|--------|----------|
| 1 | `_retry` 플래그 큐 진입 전 설정 (무한루프 방지) | Critical | v2 설계 리뷰 |
| 2 | `useUnreadAlertCount` queryKey 분리 (staleTime 충돌) | Critical | v2 설계 리뷰 |
| 3 | layout.tsx Server Component + AlertBell Client Island | Medium | v2 설계 리뷰 |
| 4 | Thesis 인터페이스 전체 필드 명시 | Medium | v2 설계 리뷰 |
| 5 | degreeToColor/Label/Arrow `<` 기준 통일 | Medium | v2 설계 리뷰 |
| 6 | daysWatching `Math.max(0, ...)` 음수 방지 | Medium | v2 설계 리뷰 |
| 7 | MoonPhase score=null vs score=-1 시각 구분 (opacity-40) | Medium | v2 설계 리뷰 |
| 8 | ROTATE_REFRESH_TOKENS 대응: `data.refresh` 저장 | Critical | v2 설계 리뷰 |
| 9 | barrel에 skeleton 미포함, 직접 import | Medium | v2 설계 리뷰 |
| 10 | ThesisAlert `indicator: string \| null` 필드 추가 | Critical | v3 설계 리뷰 |
| 11 | animate-fadeIn 존재 확인 (globals.css:49) | Info | v3 설계 리뷰 |
| 12 | 다중 탭 토큰 충돌 방어 (localStorage 재확인 + storage 이벤트) | Critical | v4 설계 리뷰 |
| 13 | unreadAlertCount 경량 엔드포인트 전환 | Medium | v4 설계 리뷰 |
| 14 | localStorage/SSR 한계 기술 부채 문서화 | Info | v4 설계 리뷰 |
| 15 | AuthContext `createContext` 누락 -> 추가 | Critical | 구현 중 발견 |
| 16 | AuthContext refreshToken 함수 Token Rotation 미대응 -> 수정 | Critical | 구현 중 발견 |
