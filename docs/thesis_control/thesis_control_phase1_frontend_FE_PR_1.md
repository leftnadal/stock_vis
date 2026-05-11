# FE-PR-1: 라우팅 + 공통 컴포넌트 — 최종 구현 계획 (v4)

> 버전: v4 (최종)
> 작성일: 2026-03-10
> 범위: 공통 유틸 + 공유 UI 컴포넌트 + 라우팅 skeleton
> 전제조건: 없음 (백엔드 없이 시작 가능)
> 목표: 다른 FE PR들이 임포트해서 쓸 공통 기반 구축

---

## 0. 기존 프로젝트 패턴 분석

### 0.1 API 클라이언트 패턴 (3가지 공존)

| 패턴 | 파일 | 방식 | 인증 | 사용처 |
|------|------|------|------|--------|
| A | `services/*.ts` | `fetch` + `API_URL` | 없음 | newsService, eodService (공개 API) |
| B | `contexts/AuthContext.tsx` | 모듈 스코프 `axios.create()` + JWT 인터셉터 | O | 로그인/회원가입/토큰 검증 |
| C | `lib/api/client.ts` | `ApiClient` 클래스 + axios | 없음 | stocks 일부 |

**thesis는 인증 필요** (사용자별 가설) → 패턴 B의 인터셉터 방식을 따르되,
AuthContext의 `api` 인스턴스는 **export되지 않으므로** `lib/api/authAxios.ts`에
공통 모듈을 추출하여 AuthContext와 thesis가 모두 공유.

### 0.2 Query Hook 패턴

`hooks/useEODDashboard.ts` 기준:

```ts
const QUERY_KEYS = {
  dashboard: ['eod-dashboard'] as const,
  signalDetail: (id: string) => ['eod-signal-detail', id] as const,
} as const

export function useEODDashboard() {
  return useQuery<EODDashboardData>({
    queryKey: QUERY_KEYS.dashboard,
    queryFn: () => eodService.getDashboard(),
    staleTime: Infinity,   // 전역과 다를 때만 override
    retry: 1,
  })
}
```

### 0.3 QueryProvider 전역 설정과 thesis override 전략

| 옵션 | 전역 값 | thesis 필요 값 | 결정 |
|------|---------|---------------|------|
| `staleTime` | 5분 | 5분 | **상속 (생략)** |
| `gcTime` | 30분 | — | **상속** |
| `refetchOnWindowFocus` | `false` | `true` | **thesis hook에서 override** |
| `retry` | `2` | `1` | **thesis hook에서 override** |
| `retryDelay` | exponential backoff | — | **상속** |
| `refetchOnReconnect` | `true` | — | **상속** |

`queries.ts`에서 새 QueryClient를 생성하지 않음. 각 hook에서 개별 override만.

### 0.4 Skeleton 패턴

`components/eod/EODSkeleton.tsx` 기준:

```tsx
function SkeletonBox({ className = '' }: { className?: string }) {
  return <div className={`bg-gray-200 dark:bg-gray-700 rounded animate-pulse ${className}`} />
}
```

thesis는 다크 전용이므로 `dark:` 없이 `bg-gray-700 rounded animate-pulse` 사용.

### 0.5 라우팅 불일치

| 위치 | 경로 |
|------|------|
| `Header.tsx` L60, L174 | `/thesis-control` |
| 요청 명세 | `app/thesis/` |

**결정**: `app/thesis/`로 생성, Header 링크를 `/thesis`로 수정.

### 0.6 animate-fadeIn 존재 확인

`globals.css:49`에 이미 정의됨:

```css
@keyframes fadeIn {
  from { opacity: 0; transform: scale(0.95); }
  to { opacity: 1; transform: scale(1); }
}
.animate-fadeIn {
  animation: fadeIn 0.15s ease-out forwards;
}
```

추가 작업 불필요. layout.tsx에서 그대로 사용.

### 0.7 Django JWT 설정 확인

```python
# config/settings.py:334-338
SIMPLE_JWT = {
    'ROTATE_REFRESH_TOKENS': True,       # 갱신 시 새 refresh 발급
    'BLACKLIST_AFTER_ROTATION': True,    # 구 refresh 즉시 무효화
}
```

`data.refresh`를 저장하지 않으면 영구 로그아웃 발생. authAxios에서 반드시 대응.

---

## 1. 파일 목록 (총 21개)

### 신규 생성 (19개)

```
frontend/
├── lib/
│   ├── api/
│   │   └── authAxios.ts                 # [A] 공통 인증 axios
│   └── thesis/
│       ├── types.ts                      # [1] TypeScript 타입
│       ├── utils.ts                      # [2] 유틸리티 함수
│       ├── api.ts                        # [3] API 클라이언트
│       └── queries.ts                    # [4] TanStack Query hooks
├── components/thesis/
│   ├── common/
│   │   ├── ArrowIndicator.tsx            # [5] 화살표 컴포넌트
│   │   ├── MoonPhase.tsx                 # [6] 달 위상 (SVG)
│   │   ├── IndicatorCard.tsx             # [7] 지표 카드
│   │   ├── ThesisBadge.tsx               # [8] 가설 상태 뱃지
│   │   └── AlertBell.tsx                 # [9] 알림 벨 (Client Island)
│   ├── skeleton/
│   │   └── ThesisSkeleton.tsx            # [10] shimmer skeleton 모음
│   └── index.ts                          # [11] barrel re-export
├── app/thesis/
│   ├── layout.tsx                        # [12] 공통 레이아웃 (Server Component)
│   ├── page.tsx                          # [13] 첫 화면
│   ├── new/page.tsx                      # [14] 대화형 빌더
│   ├── [thesisId]/page.tsx               # [15] 관제실 대시보드
│   ├── [thesisId]/indicators/page.tsx    # [16] 지표 설정
│   ├── [thesisId]/close/page.tsx         # [17] 가설 마감
│   └── alerts/page.tsx                   # [18] 알림 목록
```

### 기존 파일 수정 (2개)

```
frontend/
├── contexts/AuthContext.tsx              # [19] authAxios 마이그레이션
└── components/layout/Header.tsx          # [20] /thesis-control → /thesis
```

---

## 2. 각 파일 상세 명세

---

### [A] `lib/api/authAxios.ts` — 공통 인증 Axios 인스턴스

핵심 역할: JWT 인터셉터 단일 소스. AuthContext와 thesis API가 공유.
3가지 방어: (1) 단일 탭 Race Condition, (2) 다중 탭 토큰 동기화, (3) Token Rotation.

```ts
import axios, { type InternalAxiosRequestConfig } from 'axios'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1'

export const authAxios = axios.create({
  baseURL: API_URL,
  headers: { 'Content-Type': 'application/json' },
})

// ── 토큰 유틸 (SSR 안전) ──
// TODO: 향후 SSR 데이터 페칭이 필요해지면 HTTP-Only Cookie 기반으로 전환.
//       tokenUtils를 단일 소스로 유지했으므로 이 파일만 수정하면 전환 가능.
export const tokenUtils = {
  getAccess:  () => typeof window !== 'undefined'
    ? localStorage.getItem('access_token') : null,
  getRefresh: () => typeof window !== 'undefined'
    ? localStorage.getItem('refresh_token') : null,
  setTokens: (access: string, refresh: string) => {
    if (typeof window === 'undefined') return
    localStorage.setItem('access_token', access)
    localStorage.setItem('refresh_token', refresh)
  },
  setAccess: (access: string) => {
    if (typeof window !== 'undefined') localStorage.setItem('access_token', access)
  },
  clear: () => {
    if (typeof window === 'undefined') return
    localStorage.removeItem('access_token')
    localStorage.removeItem('refresh_token')
  },
}

// ── 요청 인터셉터 ──
authAxios.interceptors.request.use((config) => {
  const token = tokenUtils.getAccess()
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

// ── 응답 인터셉터 ──
// 방어 (1): 단일 탭 Race Condition — isRefreshing + pendingQueue
// 방어 (2): 다중 탭 동기화 — refresh 전 localStorage 재확인 + storage 이벤트
// 방어 (3): Token Rotation — data.refresh 저장

let isRefreshing = false
let pendingQueue: {
  resolve: (token: string) => void
  reject: (err: unknown) => void
}[] = []

function processQueue(error: unknown, token: string | null) {
  pendingQueue.forEach(({ resolve, reject }) => {
    error ? reject(error) : resolve(token!)
  })
  pendingQueue = []
}

// ── 다중 탭 동기화: 다른 탭에서 토큰이 갱신/삭제되면 감지 ──
if (typeof window !== 'undefined') {
  window.addEventListener('storage', (e) => {
    if (e.key === 'access_token' && e.newValue) {
      // 다른 탭에서 갱신 완료 → 대기 중인 요청들에 새 토큰 전달
      processQueue(null, e.newValue)
    }
    if (e.key === 'access_token' && !e.newValue) {
      // 다른 탭에서 로그아웃 → 대기 중인 요청들 reject
      processQueue(new Error('Logged out in another tab'), null)
    }
  })
}

authAxios.interceptors.response.use(
  (res) => res,
  async (error) => {
    const originalRequest = error.config as InternalAxiosRequestConfig & { _retry?: boolean }

    if (error.response?.status !== 401 || originalRequest._retry) {
      return Promise.reject(error)
    }

    // _retry를 큐 진입 전에 설정 — 재요청이 또 401이면 무한루프 방지
    originalRequest._retry = true

    // ── 방어 (2): 다른 탭이 이미 갱신했는지 확인 ──
    // 실패한 요청의 토큰과 현재 localStorage의 토큰을 비교
    const currentAccess = tokenUtils.getAccess()
    const failedToken = originalRequest.headers.Authorization
      ?.toString().replace('Bearer ', '')

    if (currentAccess && currentAccess !== failedToken) {
      // 다른 탭이 이미 갱신 → 새 토큰으로 즉시 재시도 (refresh 호출 스킵)
      originalRequest.headers.Authorization = `Bearer ${currentAccess}`
      return authAxios(originalRequest)
    }

    // ── 방어 (1): 이 탭에서 이미 갱신 중이면 큐 대기 ──
    if (isRefreshing) {
      return new Promise<string>((resolve, reject) => {
        pendingQueue.push({ resolve, reject })
      }).then((newToken) => {
        originalRequest.headers.Authorization = `Bearer ${newToken}`
        return authAxios(originalRequest)
      })
    }

    isRefreshing = true

    try {
      const refresh = tokenUtils.getRefresh()
      if (!refresh) throw new Error('No refresh token')

      const { data } = await axios.post(`${API_URL}/users/jwt/refresh/`, { refresh })

      // ── 방어 (3): ROTATE_REFRESH_TOKENS=True 대응 ──
      if (data.refresh) {
        tokenUtils.setTokens(data.access, data.refresh)
      } else {
        tokenUtils.setAccess(data.access)
      }

      processQueue(null, data.access)

      originalRequest.headers.Authorization = `Bearer ${data.access}`
      return authAxios(originalRequest)
    } catch (refreshError) {
      processQueue(refreshError, null)
      tokenUtils.clear()
      if (typeof window !== 'undefined') window.location.href = '/login'
      return Promise.reject(refreshError)
    } finally {
      isRefreshing = false
    }
  }
)
```

**단일 탭 Race Condition 시나리오**:
```
대시보드 진입 → 4개 API 동시 호출 → 토큰 만료 → 4개 모두 401
→ A: _retry=true, isRefreshing=true, /refresh/ 호출
→ B,C,D: _retry=true, 큐에 push
→ /refresh/ 성공 → processQueue → B,C,D 새 토큰으로 재요청
→ 만약 재요청이 또 401: _retry=true이므로 즉시 reject (무한루프 차단)
```

**다중 탭 토큰 충돌 시나리오**:
```
탭 A, B 모두 access_token 만료 상태

1. 탭 A: API 호출 → 401 → /refresh/ 호출 → 새 토큰 발급
   → localStorage에 새 access_token, refresh_token 저장
   → 구 refresh_token은 백엔드에서 블랙리스트 처리

2. 탭 B: API 호출 → 401
   → 방어 (2): localStorage에서 currentAccess 읽기
   → 탭 A가 저장한 새 토큰 발견 (failedToken과 다름)
   → /refresh/ 호출 없이 새 토큰으로 즉시 재시도
   → 블랙리스트된 구 refresh 사용 안 함 → 로그아웃 방지
```

---

### [19] `contexts/AuthContext.tsx` 수정

```diff
- import axios from 'axios'
+ import axios from 'axios'  // login/signup 직접 호출용 유지
+ import { authAxios as api, tokenUtils } from '@/lib/api/authAxios'

// 삭제: 약 50줄
- const API_URL = ...
- const api = axios.create({ ... })
- const tokenUtils = { ... }
- api.interceptors.request.use(...)
- api.interceptors.response.use(...)

// login 변경:
- const response = await axios.post(`${API_URL}/users/jwt/login/`, { ... })
+ const response = await api.post('/users/jwt/login/', { ... })

// signup 변경:
- const response = await axios.post(`${API_URL}/users/jwt/signup/`, userData)
+ const response = await api.post('/users/jwt/signup/', userData)

// refreshToken 변경:
- const response = await axios.post(`${API_URL}/users/jwt/refresh/`, { refresh })
- const { access } = response.data
- if (typeof window !== 'undefined') localStorage.setItem('access_token', access)
+ const { data } = await api.post('/users/jwt/refresh/', { refresh })
+ if (data.refresh) {
+   tokenUtils.setTokens(data.access, data.refresh)
+ } else {
+   tokenUtils.setAccess(data.access)
+ }
```

변경 범위: import 문 2줄 추가 + 기존 axios/인터셉터/tokenUtils 약 50줄 삭제 + 함수 내부 3곳 수정.

---

### [1] `lib/thesis/types.ts`

```ts
// ═══ 열거형 ═══

export type Direction = 'bullish' | 'bearish' | 'neutral'

export type ThesisStatus = 'setting_up' | 'active' | 'closed' | 'paused'

export type ThesisState =
  | 'warming_up' | 'active' | 'strengthening' | 'weakening'
  | 'critical' | 'needs_review' | 'expired'
  | 'closed_correct' | 'closed_incorrect' | 'closed_neutral'

export type IndicatorType =
  | 'market_data' | 'macro' | 'sentiment' | 'technical' | 'custom'

export type SupportDirection = 'positive' | 'negative'

// ═══ 엔티티 ═══

export interface Thesis {
  id: string
  user: number
  title: string
  direction: Direction
  target: string
  thesis_type: string            // 'event' | 'trend' | 'comparison' | 'divergence' | 'custom'
  status: ThesisStatus
  current_state: ThesisState
  current_score: number | null   // null = warming_up
  overall_label: string
  ai_summary: string | null
  expected_timeframe: string | null
  source_entry: string           // 'news' | 'free_input' | 'popular' | 'template' | 'chainsight'
  created_at: string             // ISO 8601
  closed_at: string | null
  outcome: string | null         // 'correct' | 'incorrect' | 'neutral'
  outcome_note: string
}

export interface ThesisPremise {
  id: string
  content: string
  extraction_level: 'explicit' | 'implicit' | 'ai_suggested'
  is_active: boolean
  current_score: number          // -1.0 ~ 1.0
  current_label: string
  order: number
}

export interface ThesisIndicator {
  id: string
  name: string
  indicator_type: IndicatorType
  support_direction: SupportDirection
  current_arrow_degree: number   // 0 ~ 180
  current_label: string
  current_color: string          // hex 색상 코드
  is_active: boolean
  premise: string | null         // premise id
}

export interface ThesisAlert {
  id: string
  thesis: string                 // thesis id
  indicator: string | null       // ThesisIndicator id, 지표 무관 알림이면 null
  alert_type: string             // 'indicator_change' | 'threshold_cross' | 'news_event' | 'target_date' | 'daily_summary'
  title: string
  message: string
  is_read: boolean
  created_at: string
}

// ═══ API 응답 ═══

export interface DashboardResponse {
  thesis: Thesis
  premises: (ThesisPremise & { indicators: ThesisIndicator[] })[]
  recent_alerts: ThesisAlert[]
  moon_phase: {
    phase: string                // 'full_moon' | 'waxing' | 'half_moon' | 'waning' | 'new_moon'
    label: string
  }
  overall_score: number          // -1.0 ~ 1.0
}

export interface ConversationButton {
  id: string
  label: string
  type?: 'text_input'
  long_press_hint?: boolean
}

export interface ConversationResponse {
  message: string
  buttons: ConversationButton[]
  selection_mode: 'single' | 'multi'
  long_press_explanations?: Record<string, string>
  conversation_state: string
  step: number
  total_steps: number
  thesis?: Thesis                // 가설 완성 시 포함
}
```

---

### [2] `lib/thesis/utils.ts`

```ts
import { differenceInDays } from 'date-fns'
import type { ThesisState } from './types'

// ── 화살표 각도 -> 색상 (< 기준 통일, 0=파랑=지지, 180=빨강=반박) ──
export function degreeToColor(degree: number): string {
  const d = Math.max(0, Math.min(180, degree))
  if (d < 36)  return '#2563EB'   // 강하게 지지, blue-600
  if (d < 72)  return '#60A5FA'   // 지지하는 편, blue-400
  if (d < 108) return '#9CA3AF'   // 중립, gray-400
  if (d < 144) return '#FB923C'   // 약화하는 편, orange-400
  return '#DC2626'                 // 강하게 반박, red-600
}

// ── 화살표 각도 -> 심볼 (< 기준 통일) ──
export function degreeToArrow(degree: number): string {
  const d = Math.max(0, Math.min(180, degree))
  if (d < 22.5)  return '\u2191'   // ↑
  if (d < 67.5)  return '\u2197'   // ↗
  if (d < 112.5) return '\u2192'   // →
  if (d < 157.5) return '\u2198'   // ↘
  return '\u2193'                   // ↓
}

// ── 화살표 각도 -> 라벨 (< 기준 통일) ──
export function degreeToLabel(degree: number): string {
  const d = Math.max(0, Math.min(180, degree))
  if (d < 36)  return '강하게 지지'
  if (d < 72)  return '지지하는 편'
  if (d < 108) return '중립'
  if (d < 144) return '약화하는 편'
  return '강하게 반박'
}

// ── 점수(-1~1) -> 달 위상 ──
export function scoreToPhaseMeta(score: number): {
  phase: string; label: string
} {
  if (score > 0.6)  return { phase: 'full_moon', label: '가설이 빛나고 있어요' }
  if (score > 0.2)  return { phase: 'waxing',    label: '조금씩 밝아지고 있어요' }
  if (score > -0.2) return { phase: 'half_moon', label: '반반이에요' }
  if (score > -0.6) return { phase: 'waning',    label: '조금씩 어두워지고 있어요' }
  return { phase: 'new_moon', label: '가설이 힘을 잃고 있어요' }
}

// ── 가설 상태 -> 뱃지 (다크 전용 colorClass) ──
export function stateToDisplay(state: ThesisState): {
  label: string; colorClass: string
} {
  switch (state) {
    case 'warming_up':       return { label: '데이터 수집 중', colorClass: 'text-gray-400 bg-gray-800' }
    case 'active':           return { label: '관제 중',       colorClass: 'text-blue-400 bg-blue-900/50' }
    case 'strengthening':    return { label: '강화 추세',     colorClass: 'text-green-400 bg-green-900/50' }
    case 'weakening':        return { label: '약화 추세',     colorClass: 'text-orange-400 bg-orange-900/50' }
    case 'critical':         return { label: '주의 필요',     colorClass: 'text-red-400 bg-red-900/50' }
    case 'needs_review':     return { label: '점검 필요',     colorClass: 'text-yellow-400 bg-yellow-900/50' }
    case 'expired':          return { label: '기간 만료',     colorClass: 'text-gray-500 bg-gray-800' }
    case 'closed_correct':   return { label: '적중',          colorClass: 'text-green-400 bg-green-900/50' }
    case 'closed_incorrect': return { label: '미적중',        colorClass: 'text-red-400 bg-red-900/50' }
    case 'closed_neutral':   return { label: '중립 마감',     colorClass: 'text-gray-400 bg-gray-800' }
    default:                 return { label: '알 수 없음',    colorClass: 'text-gray-500 bg-gray-800' }
  }
}

// ── 관제 N일째 (음수 방지) ──
export function daysWatching(createdAt: string): number {
  return Math.max(0, differenceInDays(new Date(), new Date(createdAt)))
}
```

---

### [3] `lib/thesis/api.ts`

```ts
import { authAxios } from '@/lib/api/authAxios'
import type {
  Thesis, ThesisAlert, ThesisIndicator,
  DashboardResponse, ConversationResponse,
} from './types'

const GET   = <T>(url: string) => authAxios.get<T>(url).then(r => r.data)
const POST  = <T>(url: string, data?: unknown) => authAxios.post<T>(url, data).then(r => r.data)
const PATCH = <T>(url: string, data?: unknown) => authAxios.patch<T>(url, data).then(r => r.data)

export const thesisApi = {
  // 가설 CRUD
  list:      ()           => GET<Thesis[]>('/thesis/'),
  get:       (id: string) => GET<Thesis>(`/thesis/${id}/`),
  dashboard: (id: string) => GET<DashboardResponse>(`/thesis/${id}/dashboard/`),

  // 대화형 빌더
  startConversation: (data: { entry_source: string; news_id?: string }) =>
    POST<ConversationResponse>('/thesis/conversation/start/', data),
  sendMessage: (data: { session_id: string; message: string }) =>
    POST<ConversationResponse>('/thesis/conversation/respond/', data),

  // 지표
  listIndicators: (thesisId: string) =>
    GET<ThesisIndicator[]>(`/thesis/${thesisId}/indicators/`),
  autoRecommend:  (thesisId: string) =>
    POST<ThesisIndicator[]>(`/thesis/${thesisId}/indicators/auto-recommend/`, {}),

  // 알림
  listAlerts:    (thesisId?: string) =>
    GET<ThesisAlert[]>(thesisId ? `/thesis/${thesisId}/alerts/` : '/thesis/alerts/'),
  markAlertRead: (alertId: string) =>
    PATCH<void>(`/thesis/alerts/${alertId}/read/`, {}),

  // 알림 카운트 (벨 아이콘 전용 경량 엔드포인트)
  unreadAlertCount: () =>
    GET<{ count: number }>('/thesis/alerts/unread-count/'),

  // 마감
  close: (id: string, data: { outcome: string; outcome_note?: string }) =>
    PATCH<Thesis>(`/thesis/${id}/close/`, data),
}
```

**unreadAlertCount 엔드포인트 설계 근거**:
- 전체 알림 배열을 다운로드하여 `.filter().length`하는 방식은 알림 누적 시 대역폭 낭비
- `GET /thesis/alerts/unread-count/` → `{"count": 3}` 만 반환하는 경량 API
- 백엔드 미구현 시 404 → `?? 0` fallback으로 안전
- 백엔드 PR 의존: thesis 백엔드에서 해당 엔드포인트 추가 필요
```

---

### [4] `lib/thesis/queries.ts`

```ts
import { useQuery } from '@tanstack/react-query'
import { thesisApi } from './api'
import type { ThesisAlert } from './types'

const QUERY_KEYS = {
  list:        ['thesis', 'list'] as const,
  detail:      (id: string) => ['thesis', id] as const,
  dashboard:   (id: string) => ['thesis', id, 'dashboard'] as const,
  indicators:  (id: string) => ['thesis', id, 'indicators'] as const,
  alerts:      (id?: string) => ['thesis', 'alerts', id ?? 'all'] as const,
  alertsCount: ['thesis', 'alerts-count'] as const,
} as const

// 전역 QueryProvider: staleTime=5min, retry=2, refetchOnWindowFocus=false
// thesis 전용 차이점만 override
const THESIS_DEFAULTS = {
  refetchOnWindowFocus: true as const,
  retry: 1,
}

export function useThesisList() {
  return useQuery({
    queryKey: QUERY_KEYS.list,
    queryFn: () => thesisApi.list(),
    ...THESIS_DEFAULTS,
  })
}

export function useThesis(thesisId: string) {
  return useQuery({
    queryKey: QUERY_KEYS.detail(thesisId),
    queryFn: () => thesisApi.get(thesisId),
    enabled: !!thesisId,
    ...THESIS_DEFAULTS,
  })
}

export function useDashboard(thesisId: string) {
  return useQuery({
    queryKey: QUERY_KEYS.dashboard(thesisId),
    queryFn: () => thesisApi.dashboard(thesisId),
    enabled: !!thesisId,
    ...THESIS_DEFAULTS,
  })
}

export function useIndicators(thesisId: string) {
  return useQuery({
    queryKey: QUERY_KEYS.indicators(thesisId),
    queryFn: () => thesisApi.listIndicators(thesisId),
    enabled: !!thesisId,
    ...THESIS_DEFAULTS,
  })
}

export function useAlerts(thesisId?: string) {
  return useQuery({
    queryKey: QUERY_KEYS.alerts(thesisId),
    queryFn: () => thesisApi.listAlerts(thesisId),
    ...THESIS_DEFAULTS,
  })
}

// 벨 아이콘 전용 — 경량 카운트 엔드포인트 사용
// alertsCount와 alerts는 다른 queryKey이므로 staleTime 충돌 없음
export function useUnreadAlertCount() {
  const { data } = useQuery({
    queryKey: QUERY_KEYS.alertsCount,
    queryFn: () => thesisApi.unreadAlertCount(),  // GET /thesis/alerts/unread-count/ → {"count": 3}
    staleTime: 1000 * 60 * 10,          // 10분 — 벨 아이콘용은 자주 갱신 불필요
    refetchOnWindowFocus: true,
    retry: 1,
  })
  return data?.count ?? 0
}
```

**queryKey 분리 + 경량 엔드포인트 근거**:
- useAlerts()와 useUnreadAlertCount()가 동일 키를 쓰면 TanStack Query v5에서
  가장 최근 마운트된 observer의 staleTime이 적용되어 의도 불일치.
- alertsCount 키를 분리하면 각자 독립 캐시, staleTime 충돌 없음.
- 전체 알림 배열 대신 `{"count": 3}`만 반환하는 경량 엔드포인트로 대역폭 절약.
- 알림 1만개 누적 시에도 벨 아이콘은 O(1) 응답.

---

### [5] `components/thesis/common/ArrowIndicator.tsx`

```tsx
'use client'

import { degreeToColor, degreeToLabel } from '@/lib/thesis/utils'

interface Props {
  degree: number        // 0~180
  size?: 'sm' | 'md' | 'lg'
  showLabel?: boolean
}

const SIZE_MAP = {
  sm: { fontSize: '1.125rem', text: 'text-xs' },    // text-lg
  md: { fontSize: '1.5rem',   text: 'text-xs' },    // text-2xl
  lg: { fontSize: '2.25rem',  text: 'text-sm' },    // text-4xl
}

export function ArrowIndicator({ degree, size = 'md', showLabel = false }: Props) {
  const color = degreeToColor(degree)
  const label = degreeToLabel(degree)
  const { fontSize, text: textClass } = SIZE_MAP[size]

  return (
    <div className="flex flex-col items-center gap-1">
      <span
        style={{
          color,
          fontSize,
          transform: `rotate(${degree - 90}deg)`,
          display: 'inline-block',
          lineHeight: 1,
        }}
        role="img"
        aria-label={label}
      >
        {'\u2192'} {/* → 문자를 CSS rotate로 실제 각도 표현 */}
      </span>
      {showLabel && (
        <span style={{ color }} className={textClass}>
          {label}
        </span>
      )}
    </div>
  )
}
```

---

### [6] `components/thesis/common/MoonPhase.tsx`

lucide-react Moon SVG + CSS clip-path 방식. score=null과 score=-1 시각 구분.

```tsx
'use client'

import { Moon } from 'lucide-react'
import { scoreToPhaseMeta } from '@/lib/thesis/utils'

interface Props {
  score: number | null
  size?: 'sm' | 'md' | 'lg'
  showLabel?: boolean
}

const SIZE_MAP = {
  sm: { icon: 20, text: 'text-xs' },
  md: { icon: 32, text: 'text-sm' },
  lg: { icon: 48, text: 'text-base' },
}

function scoreToFillPercent(score: number): number {
  return Math.round(((Math.max(-1, Math.min(1, score)) + 1) / 2) * 100)
}

export function MoonPhase({ score, size = 'md', showLabel = false }: Props) {
  const { icon: iconSize, text: textClass } = SIZE_MAP[size]

  // score=null(warming_up): 흐릿한 달, "데이터 수집 중"
  // score=-1(강한 반박): 선명하지만 어두운 달, "가설이 힘을 잃고 있어요"
  if (score === null) {
    return (
      <div className="flex flex-col items-center gap-1 opacity-40">
        <Moon size={iconSize} className="text-gray-700" fill="#374151" strokeWidth={1.5} />
        {showLabel && <span className={`text-gray-600 ${textClass}`}>데이터 수집 중</span>}
      </div>
    )
  }

  const meta = scoreToPhaseMeta(score)
  const fillPercent = scoreToFillPercent(score)
  const fillColor = fillPercent > 60 ? '#FBBF24'
    : fillPercent > 30 ? '#9CA3AF'
    : '#4B5563'

  return (
    <div className="flex flex-col items-center gap-1">
      <div className="relative" style={{ width: iconSize, height: iconSize }}>
        <Moon
          size={iconSize}
          className="text-gray-700 absolute inset-0"
          fill="#374151"
          strokeWidth={1.5}
        />
        {fillPercent > 0 && (
          <div
            className="absolute inset-0 overflow-hidden"
            style={{ clipPath: `inset(0 ${100 - fillPercent}% 0 0)` }}
          >
            <Moon
              size={iconSize}
              style={{ color: fillColor }}
              fill={fillColor}
              strokeWidth={1.5}
            />
          </div>
        )}
      </div>
      {showLabel && <span className={`text-gray-400 ${textClass}`}>{meta.label}</span>}
    </div>
  )
}
```

---

### [7] `components/thesis/common/IndicatorCard.tsx`

```tsx
'use client'

import { ArrowIndicator } from './ArrowIndicator'
import { degreeToColor } from '@/lib/thesis/utils'
import type { ThesisIndicator } from '@/lib/thesis/types'

interface Props {
  indicator: ThesisIndicator
  onClick?: () => void
}

export function IndicatorCard({ indicator, onClick }: Props) {
  const color = degreeToColor(indicator.current_arrow_degree)

  return (
    <button
      onClick={onClick}
      disabled={!indicator.is_active}
      className={`
        w-full bg-gray-900 border border-gray-700 rounded-xl p-4
        flex flex-col items-center gap-2
        transition-transform active:scale-95
        ${!indicator.is_active
          ? 'opacity-40 cursor-not-allowed'
          : 'hover:border-gray-500 cursor-pointer'
        }
      `}
    >
      <ArrowIndicator degree={indicator.current_arrow_degree} size="lg" />
      <span className="text-white text-sm font-medium truncate w-full text-center">
        {indicator.name}
      </span>
      <span className="text-xs" style={{ color }}>
        {indicator.current_label}
      </span>
    </button>
  )
}
```

disabled prop 사용: 키보드 접근 차단 + 스크린리더 "비활성화" 상태 전달.

---

### [8] `components/thesis/common/ThesisBadge.tsx`

```tsx
'use client'

import { stateToDisplay } from '@/lib/thesis/utils'
import type { ThesisState, Direction } from '@/lib/thesis/types'

interface Props {
  state: ThesisState
  direction: Direction
}

function getDirectionIcon(state: ThesisState, direction: Direction): string {
  if (state === 'closed_correct')   return '\u2705'   // ✅
  if (state === 'closed_incorrect') return '\u274C'   // ❌
  if (state === 'closed_neutral')   return '\u2796'   // ➖
  if (direction === 'bullish')  return '\uD83D\uDCC8' // 📈
  if (direction === 'bearish')  return '\uD83D\uDCC9' // 📉
  return '\u2192'                                      // →
}

export function ThesisBadge({ state, direction }: Props) {
  const { label, colorClass } = stateToDisplay(state)
  const icon = getDirectionIcon(state, direction)

  return (
    <span className={`
      inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-medium
      ${colorClass}
    `}>
      <span>{icon}</span>
      <span>{label}</span>
    </span>
  )
}
```

---

### [9] `components/thesis/common/AlertBell.tsx` — Client Island

```tsx
'use client'

import Link from 'next/link'
import { Bell } from 'lucide-react'
import { useUnreadAlertCount } from '@/lib/thesis/queries'

export function AlertBell() {
  const unreadCount = useUnreadAlertCount()

  return (
    <Link
      href="/thesis/alerts"
      className="relative p-2 -mr-2 text-gray-400 hover:text-white transition-colors"
    >
      <Bell size={20} />
      {unreadCount > 0 && (
        <span className="absolute -top-0.5 -right-0.5 flex items-center justify-center
          min-w-[18px] h-[18px] px-1 rounded-full
          bg-red-500 text-white text-[10px] font-bold">
          {unreadCount > 99 ? '99+' : unreadCount}
        </span>
      )}
    </Link>
  )
}
```

---

### [10] `components/thesis/skeleton/ThesisSkeleton.tsx`

EODSkeleton.tsx 패턴 준수. 다크 전용이므로 `bg-gray-700 rounded animate-pulse`.

```tsx
'use client'

function S({ className = '' }: { className?: string }) {
  return <div className={`bg-gray-700 rounded animate-pulse ${className}`} />
}

// ═══ 가설 목록 페이지 ═══
export function ThesisListSkeleton() {
  return (
    <div className="space-y-6">
      {/* 관제 중 */}
      <div>
        <S className="h-4 w-20 mb-3" />
        <div className="space-y-3">
          {Array.from({ length: 2 }).map((_, i) => (
            <div key={i} className="bg-gray-800 rounded-xl p-4 border border-gray-700">
              <div className="flex items-center justify-between mb-2">
                <S className="h-5 w-32" />
                <S className="h-6 w-20 rounded-full" />
              </div>
              <S className="h-3 w-48 mb-2" />
              <div className="flex items-center gap-2">
                <S className="h-8 w-8 rounded-full" />
                <S className="h-3 w-36" />
              </div>
            </div>
          ))}
        </div>
      </div>
      {/* 오늘의 변화 */}
      <div>
        <S className="h-4 w-24 mb-3" />
        <div className="bg-gray-800 rounded-xl p-4 border border-gray-700">
          <S className="h-4 w-full mb-2" />
          <S className="h-3 w-3/4 mb-3" />
          <S className="h-8 w-24 rounded-lg" />
        </div>
      </div>
      {/* 새로운 가설 버튼 */}
      <div>
        <S className="h-4 w-24 mb-3" />
        <div className="grid grid-cols-2 gap-3">
          {Array.from({ length: 4 }).map((_, i) => (
            <S key={i} className="h-14 rounded-xl" />
          ))}
        </div>
      </div>
    </div>
  )
}

// ═══ 관제실 대시보드 ═══
export function ThesisDashboardSkeleton() {
  return (
    <div className="space-y-6">
      <div className="text-center space-y-2">
        <S className="h-6 w-40 mx-auto" />
        <S className="h-4 w-28 mx-auto" />
      </div>
      <div className="flex flex-col items-center gap-2">
        <S className="h-12 w-12 rounded-full" />
        <S className="h-4 w-48" />
      </div>
      <div className="grid grid-cols-3 gap-3">
        {Array.from({ length: 3 }).map((_, i) => (
          <div key={i} className="bg-gray-800 rounded-xl p-4 border border-gray-700">
            <div className="flex flex-col items-center gap-2">
              <S className="h-9 w-9 rounded-full" />
              <S className="h-3 w-16" />
              <S className="h-3 w-12" />
            </div>
          </div>
        ))}
      </div>
      <div className="bg-gray-800 rounded-xl p-4 border border-gray-700">
        <S className="h-4 w-20 mb-2" />
        <S className="h-3 w-full mb-1" />
        <S className="h-3 w-2/3" />
      </div>
    </div>
  )
}

// ═══ 알림 목록 ═══
export function ThesisAlertsSkeleton() {
  return (
    <div className="space-y-3">
      {Array.from({ length: 4 }).map((_, i) => (
        <div key={i} className="bg-gray-800 rounded-xl p-4 border border-gray-700">
          <div className="flex items-start gap-3">
            <S className="h-5 w-5 rounded-full flex-shrink-0 mt-0.5" />
            <div className="flex-1">
              <S className="h-4 w-3/4 mb-2" />
              <S className="h-3 w-full mb-1" />
              <S className="h-3 w-1/2" />
            </div>
          </div>
        </div>
      ))}
    </div>
  )
}
```

---

### [11] `components/thesis/index.ts`

```ts
// 공통 UI 컴포넌트
export { ArrowIndicator } from './common/ArrowIndicator'
export { MoonPhase } from './common/MoonPhase'
export { IndicatorCard } from './common/IndicatorCard'
export { ThesisBadge } from './common/ThesisBadge'
export { AlertBell } from './common/AlertBell'

// skeleton은 barrel 미포함 — 실제 구현으로 교체될 임시 파일
// import { ThesisListSkeleton } from '@/components/thesis/skeleton/ThesisSkeleton'
```

---

### [12] `app/thesis/layout.tsx` — Server Component

```tsx
import Link from 'next/link'
import { ArrowLeft } from 'lucide-react'
import { AlertBell } from '@/components/thesis/common/AlertBell'

export default function ThesisLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-screen bg-gray-950 animate-fadeIn">
      <div className="max-w-lg mx-auto px-4 pt-4 pb-20">
        <div className="flex items-center justify-between mb-6">
          <Link href="/" className="p-2 -ml-2 text-gray-400 hover:text-white transition-colors">
            <ArrowLeft size={20} />
          </Link>
          <h1 className="text-white text-lg font-bold">가설 통제실</h1>
          <AlertBell />
        </div>
        {children}
      </div>
    </div>
  )
}
```

---

### [13~18] 라우팅 skeleton 페이지

| 파일 | skeleton | placeholder 텍스트 |
|------|----------|-------------------|
| `app/thesis/page.tsx` | `ThesisListSkeleton` | 가설 목록 -- FE-PR-2에서 구현 |
| `app/thesis/[thesisId]/page.tsx` | `ThesisDashboardSkeleton` | 관제실 -- FE-PR-5에서 구현 |
| `app/thesis/alerts/page.tsx` | `ThesisAlertsSkeleton` | 알림 -- FE-PR-6에서 구현 |
| `app/thesis/new/page.tsx` | 없음 | 새 가설 만들기 -- FE-PR-3에서 구현 |
| `app/thesis/[thesisId]/indicators/page.tsx` | 없음 | 지표 설정 -- FE-PR-4에서 구현 |
| `app/thesis/[thesisId]/close/page.tsx` | 없음 | 가설 마감 -- FE-PR-6에서 구현 |

skeleton이 있는 페이지:

```tsx
import { Suspense } from 'react'
import { ThesisListSkeleton } from '@/components/thesis/skeleton/ThesisSkeleton'

export default function ThesisPage() {
  return (
    <Suspense fallback={<ThesisListSkeleton />}>
      <div className="text-gray-500 text-center py-20">
        <p className="text-lg">가설 목록 -- FE-PR-2에서 구현</p>
      </div>
    </Suspense>
  )
}
```

skeleton이 없는 페이지:

```tsx
export default function ThesisNewPage() {
  return (
    <div className="text-gray-500 text-center py-20">
      <p className="text-lg">새 가설 만들기 -- FE-PR-3에서 구현</p>
    </div>
  )
}
```

---

### [20] `components/layout/Header.tsx` 수정

```diff
- href="/thesis-control"
+ href="/thesis"

- pathname.startsWith('/thesis-control')
+ pathname.startsWith('/thesis')
```

데스크톱 nav (L60)과 모바일 nav (L174) 두 곳 모두 수정.

---

## 3. 의존성 그래프

```
lib/api/authAxios.ts           <- 의존성 없음 (최우선)
    |
    +-> contexts/AuthContext.tsx     <- authAxios import (기존 코드 교체)
    |
    +-> lib/thesis/api.ts           <- authAxios + types
         |
         +-> lib/thesis/queries.ts  <- api + types
              |
              +-> components/thesis/common/AlertBell.tsx  <- queries
                   |
                   +-> app/thesis/layout.tsx  <- AlertBell (Server Component)

lib/thesis/types.ts            <- 의존성 없음
    |
    +-> lib/thesis/utils.ts    <- types (ThesisState)
         |
         +-> components/thesis/common/ArrowIndicator.tsx  <- utils
         +-> components/thesis/common/MoonPhase.tsx       <- utils
         +-> components/thesis/common/IndicatorCard.tsx   <- utils + types + ArrowIndicator
         +-> components/thesis/common/ThesisBadge.tsx     <- utils + types

components/thesis/skeleton/ThesisSkeleton.tsx  <- 의존성 없음 (순수 UI)
    |
    +-> app/thesis/**/page.tsx  <- skeleton (Suspense fallback)

components/thesis/index.ts     <- common/* re-export (skeleton 미포함)

Header.tsx                     <- 경로만 수정
```

---

## 4. 구현 순서 (병렬화)

```
Phase A (독립, 병렬):
  |- lib/api/authAxios.ts
  |- lib/thesis/types.ts
  |- components/thesis/skeleton/ThesisSkeleton.tsx

Phase B (Phase A 의존):
  |- contexts/AuthContext.tsx 수정      <- authAxios
  |- lib/thesis/utils.ts               <- types

Phase C (Phase A+B 의존, 병렬):
  |- lib/thesis/api.ts                 <- authAxios + types
  |- ArrowIndicator.tsx                <- utils
  |- MoonPhase.tsx                     <- utils
  |- IndicatorCard.tsx                 <- utils + types + ArrowIndicator
  |- ThesisBadge.tsx                   <- utils + types

Phase D (Phase C 의존):
  |- lib/thesis/queries.ts             <- api + types

Phase E (Phase D 의존):
  |- AlertBell.tsx                     <- queries
  |- components/thesis/index.ts        <- common/*

Phase F (Phase E 의존):
  |- app/thesis/layout.tsx             <- AlertBell
  |- app/thesis/**/page.tsx 6개        <- skeleton
  |- Header.tsx 수정                   <- 경로만
```

---

## 5. 리스크 및 완화

| # | 리스크 | 심각도 | 완화 |
|---|--------|--------|------|
| 1 | AuthContext 마이그레이션 시 기존 로그인 깨짐 | 높음 | 변경 후 로그인/로그아웃/토큰갱신 3시나리오 수동 테스트 |
| 2 | Token Rotation 미대응 시 영구 로그아웃 | 높음 | `data.refresh` 저장 로직 반영 완료 |
| 3 | _retry 위치 오류 시 무한 루프 | 높음 | 큐 진입 전 설정으로 수정 완료 |
| 4 | 다중 탭 토큰 충돌 → 영구 로그아웃 | 높음 | localStorage 재확인 + storage 이벤트 리스너 추가 |
| 5 | queryKey 충돌로 staleTime 무시 | 중간 | alertsCount 키 분리로 해결 |
| 6 | 전체 알림 fetch로 대역폭 낭비 | 중간 | `unreadAlertCount` 경량 엔드포인트 분리 (백엔드 의존) |
| 7 | Moon SVG clip-path 호환성 | 낮음 | Can I Use 97%+, IE 미지원이나 대상 아님 |
| 8 | localStorage SSR 미지원 | 기존 부채 | tokenUtils 단일 소스화로 향후 Cookie 전환 시 1곳만 수정. 현재 thesis는 CSR 위주로 문제 없음 |

### 기술 부채 (이번 PR 범위 밖, 문서화만)

| 부채 | 영향 | 전환 시점 | 전환 비용 |
|------|------|----------|----------|
| localStorage 기반 인증 → HTTP-Only Cookie | SSR 데이터 페칭 불가, SEO 제한 | SEO/SSR 최적화 필요 시 | `tokenUtils` 단일 소스 → 1파일 수정. 단, 백엔드 JWT 미들웨어도 변경 필요 |

---

## 6. 버그 수정 이력

| 버전 | 번호 | 내용 | 심각도 |
|------|------|------|--------|
| v2 | #1 | `_retry` 플래그를 큐 진입 전으로 이동 (무한루프 방지) | 🔴 |
| v2 | #2 | `useUnreadAlertCount` queryKey를 `alertsCount`로 분리 | 🔴 |
| v2 | #3 | layout.tsx Server Component 유지, AlertBell Client Island 분리 | 🟡 |
| v2 | #4 | Thesis 인터페이스 전체 필드 명시 | 🟡 |
| v2 | #5 | `degreeToColor/Label/Arrow` 경계값 `<` 기준 통일 | 🟡 |
| v2 | #6 | `daysWatching` `Math.max(0, ...)` 음수 방지 | 🟡 |
| v2 | #7 | MoonPhase `score=null` vs `score=-1` 시각 구분 (opacity-40) | 🟡 |
| v2 | #8 | ROTATE_REFRESH_TOKENS 대응: `data.refresh` 저장 | 🔴 |
| v2 | #9 | barrel에 skeleton 미포함, 직접 import 규칙 | 🟡 |
| v3 | #10 | ThesisAlert에 `indicator: string \| null` 필드 추가 | 🔴 |
| v3 | #11 | `animate-fadeIn` 존재 확인 완료 (globals.css:49) | 확인 |
| v4 | #12 | 다중 탭 토큰 충돌 방어: localStorage 재확인 + storage 이벤트 | 🔴 |
| v4 | #13 | `unreadAlertCount` 경량 엔드포인트로 전환 (대역폭 절약) | 🟡 |
| v4 | #14 | localStorage/SSR 한계 기술 부채 문서화 | 📝 |
