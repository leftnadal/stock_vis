# Thesis Control — Phase 1 프론트엔드 Claude Code 실행 프롬프트

> **기술 스택:** Next.js (TypeScript), Tailwind CSS, TanStack Query, dark theme
> **전제조건:** 백엔드 PR-3 (ViewSet + API) 머지 완료 후 시작
> **API Base URL:** `/api/v1/thesis/`
>
> **PR 목록 (6개)**
>
> ```
> FE-PR-1  라우팅 + 공통 컴포넌트 (화살표·달위상·색상 유틸)
> FE-PR-2  첫 화면 — 가설 목록 + 오늘의 변화 + 진입점
> FE-PR-3  대화형 빌더 — 5가지 진입 경로
> FE-PR-4  지표 설정 화면
> FE-PR-5  관제실 대시보드 (카드뷰)
> FE-PR-6  알림 처리 + 가설 마감 복기
> ```

---

## FE-PR-1: 라우팅 + 공통 컴포넌트

> **범위:** 공통 유틸 + 공유 UI 컴포넌트  
> **전제조건:** 없음 (백엔드 없이 시작 가능)  
> **목표:** 다른 FE PR들이 임포트해서 쓸 공통 기반 구축.

---

### 📋 프롬프트

```
docs/thesis_control/thesis_control_design.md (섹션 3.2~3.3)를 읽고,
Thesis Control 프론트엔드의 공통 유틸리티와 컴포넌트를 구현해줘.

─────────────────────────────────────────────
[1] 라우팅 구조 (Next.js App Router)
─────────────────────────────────────────────

아래 파일/폴더 구조를 생성:

app/thesis/
├── page.tsx                         # 첫 화면 (FE-PR-2)
├── layout.tsx                       # 공통 레이아웃
├── new/
│   └── page.tsx                     # 대화형 빌더 (FE-PR-3)
├── [thesisId]/
│   ├── page.tsx                     # 관제실 대시보드 (FE-PR-5)
│   ├── indicators/
│   │   └── page.tsx                 # 지표 설정 (FE-PR-4)
│   └── close/
│       └── page.tsx                 # 가설 마감 (FE-PR-6)
└── alerts/
    └── page.tsx                     # 알림 목록 (FE-PR-6)

components/thesis/
├── common/
│   ├── ArrowIndicator.tsx           # 화살표 컴포넌트
│   ├── MoonPhase.tsx                # 달 위상 아이콘
│   ├── IndicatorCard.tsx            # 지표 카드
│   └── ThesisBadge.tsx             # 가설 상태 뱃지
└── index.ts                         # re-export

lib/thesis/
├── types.ts                         # TypeScript 타입 정의
├── utils.ts                         # 색상·각도·라벨 유틸
└── api.ts                           # API 클라이언트 함수

이번 PR에서는 lib/ 와 components/thesis/common/ 만 구현.
app/thesis/ 페이지 파일들은 skeleton만 (return <div>TODO</div>).

─────────────────────────────────────────────
[2] lib/thesis/types.ts
─────────────────────────────────────────────

아래 타입을 정의:

export type Direction = 'bullish' | 'bearish' | 'neutral'
export type ThesisStatus = 'setting_up' | 'active' | 'closed' | 'paused'
export type ThesisState =
  | 'warming_up' | 'active' | 'strengthening' | 'weakening'
  | 'critical' | 'needs_review' | 'expired'
  | 'closed_correct' | 'closed_incorrect' | 'closed_neutral'

export type IndicatorType =
  | 'market_data' | 'macro' | 'sentiment' | 'technical' | 'custom'

export type SupportDirection = 'positive' | 'negative'

export interface Thesis {
  id: string
  title: string
  direction: Direction
  target: string
  thesis_type: string
  status: ThesisStatus
  current_state: ThesisState
  current_score: number | null
  overall_label: string
  created_at: string
  closed_at: string | null
  expected_timeframe: string | null
  ai_summary?: string | null
}

export interface ThesisPremise {
  id: string
  content: string
  extraction_level: 'explicit' | 'implicit' | 'ai_suggested'
  is_active: boolean
  current_score: number
  current_label: string
  order: number
}

export interface ThesisIndicator {
  id: string
  name: string
  indicator_type: IndicatorType
  support_direction: SupportDirection
  current_arrow_degree: number
  current_label: string
  current_color: string
  is_active: boolean
  premise?: string | null  // premise id
}

export interface ThesisAlert {
  id: string
  thesis: string
  alert_type: string
  title: string
  message: string
  is_read: boolean
  created_at: string
}

export interface DashboardResponse {
  thesis: Thesis
  premises: (ThesisPremise & { indicators: ThesisIndicator[] })[]
  recent_alerts: ThesisAlert[]
  moon_phase: {
    phase: string
    label: string
    icon: string
  }
  overall_score: number
}

─────────────────────────────────────────────
[3] lib/thesis/utils.ts
─────────────────────────────────────────────

설계 문서 3.3 화살표 시스템 + 섹션 3.2 달 위상 그대로 구현:

// ── 화살표 각도 → 색상 (hex) ──
export function degreeToColor(degree: number): string {
  // 0~36:   '#2563EB' (강하게 지지, 진한 파랑)
  // 36~72:  '#60A5FA' (지지하는 편, 연한 파랑)
  // 72~108: '#9CA3AF' (중립, 회색)
  // 108~144:'#FB923C' (약화하는 편, 주황)
  // 144~180:'#DC2626' (강하게 반박, 빨강)
  // ★ 설계 문서 3.3 색상 매핑 참조
  // ★ 단, 색상 방향에 주의: 0°(지지)=파랑, 180°(반박)=빨강
  //   (설계 문서 화살표 표의 색상 기호가 의미 전달 위해 반박=빨강으로 표기됨)
}

// ── 화살표 각도 → 이모지/심볼 ──
export function degreeToArrow(degree: number): string {
  // 0~22.5:   '↑'
  // 22.5~67.5:'↗'
  // 67.5~112.5:'→'
  // 112.5~157.5:'↘'
  // 157.5~180: '↓'
}

// ── 화살표 각도 → 라벨 ──
export function degreeToLabel(degree: number): string {
  // 0~36:   '강하게 지지'
  // 36~72:  '지지하는 편'
  // 72~108: '중립'
  // 108~144:'약화하는 편'
  // 144~180:'강하게 반박'
}

// ── 점수(-1~1) → 달 위상 ──
export function scoreToPhaseMeta(score: number): {
  phase: string; label: string; icon: string
} {
  //  > 0.6:  { phase:'full_moon',  label:'가설이 빛나고 있어요',       icon:'🌕' }
  //  > 0.2:  { phase:'waxing',     label:'조금씩 밝아지고 있어요',     icon:'🌔' }
  //  > -0.2: { phase:'half_moon',  label:'반반이에요',                 icon:'🌓' }
  //  > -0.6: { phase:'waning',     label:'조금씩 어두워지고 있어요',   icon:'🌒' }
  //  else:   { phase:'new_moon',   label:'가설이 힘을 잃고 있어요',    icon:'🌑' }
}

// ── 가설 상태 → 뱃지 텍스트/색상 ──
export function stateToDisplay(state: ThesisState): {
  label: string; colorClass: string
} {
  // warming_up → '데이터 수집 중' / gray
  // active → '관제 중' / blue
  // strengthening → '강화 추세' / green
  // weakening → '약화 추세' / orange
  // critical → '주의 필요' / red
  // needs_review → '점검 필요' / yellow
  // expired → '기간 만료' / gray
}

// ── 날짜 → 관제 N일째 ──
export function daysWatching(createdAt: string): number

─────────────────────────────────────────────
[4] lib/thesis/api.ts
─────────────────────────────────────────────

axios 또는 fetch 기반 API 클라이언트.
기존 프로젝트의 API 클라이언트 패턴 확인 후 동일 방식 사용.

export const thesisApi = {
  // 가설 목록
  list: () => GET('/api/v1/thesis/'),

  // 가설 상세
  get: (id: string) => GET(`/api/v1/thesis/${id}/`),

  // 대시보드
  dashboard: (id: string) => GET(`/api/v1/thesis/${id}/dashboard/`),

  // 가설 생성 (대화형 빌더)
  startConversation: (data: { entry_source: string; news_id?: string }) =>
    POST('/api/v1/thesis/conversation/start/', data),
  sendMessage: (data: { session_id: string; message: string }) =>
    POST('/api/v1/thesis/conversation/respond/', data),

  // 지표
  listIndicators: (thesisId: string) =>
    GET(`/api/v1/thesis/${thesisId}/indicators/`),
  autoRecommend: (thesisId: string) =>
    POST(`/api/v1/thesis/${thesisId}/indicators/auto-recommend/`, {}),

  // 알림
  listAlerts: (thesisId?: string) =>
    GET(thesisId ? `/api/v1/thesis/${thesisId}/alerts/` : '/api/v1/thesis/alerts/'),
  markAlertRead: (alertId: string) =>
    PATCH(`/api/v1/thesis/alerts/${alertId}/read/`, {}),

  // 가설 마감
  close: (id: string, data: { outcome: string; outcome_note?: string }) =>
    PATCH(`/api/v1/thesis/${id}/close/`, data),
}

─────────────────────────────────────────────
[5] lib/thesis/queries.ts  ★ TanStack Query 레이어
─────────────────────────────────────────────

@tanstack/react-query를 사용한 Custom Hook 모음.
lib/thesis/api.ts의 thesisApi를 내부적으로 호출.

패키지 설치 확인: package.json에 @tanstack/react-query가 없으면 추가.
  npm install @tanstack/react-query

QueryClient 설정 (app/providers.tsx 또는 기존 Provider 파일):
  new QueryClient({
    defaultOptions: {
      queries: {
        staleTime: 1000 * 60 * 5,    // 5분 — Celery 배치 특성상 잦은 재요청 불필요
        refetchOnWindowFocus: true,   // 탭 복귀 시 자동 최신화 (폴링 대체)
        retry: 1,
      }
    }
  })

// ── 가설 목록 ──
export function useThesisList() {
  return useQuery({
    queryKey: ['thesis', 'list'],
    queryFn: () => thesisApi.list(),
  })
}

// ── 가설 상세 ──
export function useThesis(thesisId: string) {
  return useQuery({
    queryKey: ['thesis', thesisId],
    queryFn: () => thesisApi.get(thesisId),
    enabled: !!thesisId,
  })
}

// ── 대시보드 ──
export function useDashboard(thesisId: string) {
  return useQuery({
    queryKey: ['thesis', thesisId, 'dashboard'],
    queryFn: () => thesisApi.dashboard(thesisId),
    enabled: !!thesisId,
  })
}

// ── 지표 목록 ──
export function useIndicators(thesisId: string) {
  return useQuery({
    queryKey: ['thesis', thesisId, 'indicators'],
    queryFn: () => thesisApi.listIndicators(thesisId),
    enabled: !!thesisId,
  })
}

// ── 알림 목록 ──
export function useAlerts(thesisId?: string) {
  return useQuery({
    queryKey: ['thesis', 'alerts', thesisId ?? 'all'],
    queryFn: () => thesisApi.listAlerts(thesisId),
  })
}

// ── 읽지 않은 알림 수 (레이아웃 벨 아이콘용) ──
export function useUnreadAlertCount() {
  const { data } = useAlerts()
  return data?.filter((a: ThesisAlert) => !a.is_read).length ?? 0
}

★ 각 페이지 컴포넌트에서 thesisApi를 직접 호출하지 말고
  위 Custom Hook을 사용할 것.
  isLoading, isError, data를 구조분해하여 로딩/에러 처리.

  예시:
  const { data: dashboard, isLoading, isError } = useDashboard(thesisId)
  if (isLoading) return <SkeletonUI />
  if (isError) return <ErrorBanner />

─────────────────────────────────────────────
[7] components/thesis/common/ArrowIndicator.tsx
─────────────────────────────────────────────

import { degreeToColor, degreeToArrow, degreeToLabel } from '@/lib/thesis/utils'

interface Props {
  degree: number        // 0~180
  size?: 'sm' | 'md' | 'lg'
  showLabel?: boolean
}

렌더링:
- 화살표 이모지/심볼을 degree에 맞게 CSS rotate로 실제 각도 표현
  (transform: rotate(${degree - 90}deg) — 90° 기본이 →이므로 보정)
- 색상: degreeToColor(degree)
- size에 따라 텍스트 크기 변경 (sm: text-lg, md: text-2xl, lg: text-4xl)
- showLabel=true이면 라벨 텍스트도 표시

─────────────────────────────────────────────
[8] components/thesis/common/MoonPhase.tsx
─────────────────────────────────────────────

interface Props {
  score: number | null   // -1~1, null이면 warming_up 취급
  size?: 'sm' | 'md' | 'lg'
  showLabel?: boolean
}

- scoreToPhaseMeta(score)로 icon/label 결정
- score null이면 icon='🌑', label='데이터 수집 중'
- showLabel=true이면 label 텍스트 표시
- size에 따라 이모지/텍스트 크기 조절

─────────────────────────────────────────────
[9] components/thesis/common/IndicatorCard.tsx
─────────────────────────────────────────────

설계 문서 3.1 지표 카드 UI 구현.

interface Props {
  indicator: ThesisIndicator
  onClick?: () => void
}

레이아웃 (다크 배경):
┌─────────────────┐
│  <ArrowIndicator degree={...} size="lg" /> │
│  지표명                                     │
│  라벨 (색상 텍스트)                          │
└─────────────────┘

- 카드 배경: bg-gray-900 border border-gray-700 rounded-xl
- 탭(onClick) 시 살짝 scale-up 애니메이션 (active:scale-95)
- is_active=false이면 opacity-40 처리

─────────────────────────────────────────────
[10] components/thesis/common/ThesisBadge.tsx
─────────────────────────────────────────────

interface Props {
  state: ThesisState
  direction: Direction
}

- stateToDisplay(state)로 라벨/색상 결정
- direction에 따라 📈/📉/→ 아이콘 앞에 표시
- rounded-full pill 형태, 다크 테마

─────────────────────────────────────────────
[주의사항]
─────────────────────────────────────────────
- 다크 테마 전용. bg-white, text-black 절대 사용하지 않음.
- Tailwind 컬러: gray-900(배경), gray-800(카드), gray-700(테두리),
  gray-400(보조 텍스트), white(주요 텍스트)
- 기존 프로젝트 컴포넌트 패턴 (shadcn/ui 등) 있으면 먼저 확인 후 일관성 유지
- components/thesis/index.ts에서 전체 re-export
```

---

## FE-PR-2: 첫 화면 — 가설 목록 + 진입점

> **범위:** `app/thesis/page.tsx`  
> **전제조건:** FE-PR-1 머지 완료  
> **목표:** 설계 문서 2.2 첫 화면 그대로 구현.

---

### 📋 프롬프트

```
docs/thesis_control/thesis_control_design.md (섹션 2.2)를 읽고,
Thesis Control 첫 화면을 구현해줘.

─────────────────────────────────────────────
[1] app/thesis/page.tsx
─────────────────────────────────────────────

'use client'

구성 (스크롤 가능한 단일 페이지, 모바일 우선):

────── 섹션 1: 관제 중 가설 목록 ──────
설계 문서 2.2 "관제 중" 섹션.

thesisApi.list() 호출 → status='active' 가설만 필터링.

각 가설 행:
  📌 {thesis.title}
  {<MoonPhase score={current_score} size="sm" />}  {overall_label}
  → 탭 시 /thesis/{id} 로 이동

가설 없으면: "아직 관제 중인 가설이 없어요. 첫 가설을 세워보세요!" 안내

────── 섹션 2: 오늘의 변화 ──────
설계 문서 2.2 "오늘의 변화" 섹션.

thesisApi.listAlerts() 호출 → is_read=false, 최신 3개.

각 알림:
  🔔 {alert.title}
  {alert.message 첫 줄}
  [확인하기] → /thesis/{alert.thesis}?highlight={alert.id} 로 이동

알림 없으면: "어젯밤 특별한 변화는 없었어요." 표시

────── 섹션 3: 새 가설 진입점 ──────
설계 문서 2.2 "새로운 가설" 5가지 버튼.

버튼 그리드 (2×2 + 1):
  [💬 내 생각]   [📰 오늘 이슈]
  [🔥 인기 가설] [📋 템플릿]
  [🔗 Chain Sight에서]

각 버튼 → /thesis/new?entry={source} 로 이동:
  내 생각   → entry=free_text
  오늘 이슈 → entry=news
  인기 가설 → entry=popular
  템플릿    → entry=template
  체인사이트 → entry=chain_sight

─────────────────────────────────────────────
[2] 로딩/에러 처리
─────────────────────────────────────────────

로딩 중: 각 섹션별 skeleton UI (gray-800 rounded-lg animate-pulse)
에러 시: "데이터를 불러오지 못했어요. 새로고침 해주세요." + 새로고침 버튼

─────────────────────────────────────────────
[3] app/thesis/layout.tsx
─────────────────────────────────────────────

- 상단: "가설 통제실" 타이틀 + 오른쪽에 알림 벨 아이콘 (읽지 않은 알림 수 뱃지)
- 하단 패딩: pb-20 (모바일 하단 nav바 고려)
- 배경: bg-gray-950

─────────────────────────────────────────────
[주의사항]
─────────────────────────────────────────────
- 인기 가설/템플릿 버튼은 Phase 1에서 "준비 중이에요" toast만 표시
- Chain Sight 버튼은 기존 Chain Sight 페이지에서 thesis/new?entry=chain_sight로
  오는 경우를 위한 수신 처리도 고려 (query param 읽기)
```

---

## FE-PR-3: 대화형 빌더 — 가설 설립 플로우

> **범위:** `app/thesis/new/page.tsx`  
> **전제조건:** FE-PR-2 머지 완료  
> **목표:** 설계 문서 2.3 경로 1(오늘 이슈)과 경로 2(내 생각) 구현.
> 경로 3(인기), 4(템플릿)은 Phase 1에서 스킵.

---

### 📋 프롬프트

```
docs/thesis_control/thesis_control_design.md (섹션 2.3, 2.4, 2.5)를 읽고,
가설 설립 대화형 빌더를 구현해줘.

Phase 1에서 구현할 경로:
  - 경로 1: 오늘 이슈 (entry=news)
  - 경로 2: 내 생각  (entry=free_text)
  - 경로 3, 4: "준비 중이에요" 안내 후 경로 2로 fallback

─────────────────────────────────────────────
[1] 전체 구조 — 채팅 인터페이스
─────────────────────────────────────────────

설계 문서의 AI 대화 플로우를 채팅 UI로 구현.

레이아웃:
  상단: 뒤로가기 + "가설 세우기" 타이틀
  중간: 메시지 스크롤 영역 (AI 말풍선 + 사용자 응답)
  하단: 고정 입력 영역 (탭 버튼 or 텍스트 입력)

메시지 타입:
  - AI 말풍선: 좌측 정렬, gray-800 배경
  - 사용자 선택/입력: 우측 정렬, blue-600 배경
  - 옵션 버튼들: 전체 너비, 한 줄씩 스택

─────────────────────────────────────────────
[2] 대화 상태 관리
─────────────────────────────────────────────

interface ConversationState {
  sessionId: string | null
  messages: Message[]
  step: ConversationStep
  thesisId: string | null   // 가설 생성 완료 후 설정
  isLoading: boolean
}

type ConversationStep =
  | 'entry_select'     // 진입 경로 선택
  | 'news_select'      // 오늘 이슈 선택
  | 'direction_select' // 방향 선택 (bullish/bearish)
  | 'ai_building'      // AI가 전제 구조화 중
  | 'premise_confirm'  // 전제 확인/수정
  | 'indicator_choice' // 지표 자동 vs 직접
  | 'complete'         // 가설 생성 완료

─────────────────────────────────────────────
[3] 경로 1: 오늘 이슈 (entry=news)
─────────────────────────────────────────────

설계 문서 2.3 경로 1 플로우:

Step 1 — 이슈 목록 표시:
  thesisApi.getDailyIssues() 호출 (없으면 mock 데이터로 대체)
  → AI 말풍선: "오늘의 시장 이슈예요."
  → 버튼 목록: 국내 이슈 + 글로벌 이슈 (각 [이걸로 시작] 버튼)

Step 2 — 방향 선택:
  선택한 이슈 → AI 말풍선: "{이슈 헤드라인}으로 어떤 생각이 드세요?"
  → [📈 오른다 (Bullish)] [📉 내린다 (Bearish)] [🤔 잘 모르겠어]

Step 3 — AI 전제 구조화:
  thesisApi.startConversation({
    entry_source: 'news',
    news_id: selectedNewsId,
    direction: selectedDirection
  })
  → AI가 전제 정리해서 응답

Step 4 — 전제 확인:
  AI 응답의 전제들을 카드 형태로 표시
  각 전제 옆 [빼기] 버튼
  하단 [+ 전제 추가하기] 텍스트 입력
  [이대로 괜찮아요 →] 버튼

Step 5 — 지표 설정 분기:
  설계 문서 2.5:
  AI 말풍선: "가설 등록 완료! 🎯 AI가 추천 지표 3개를 자동으로 달아둘까요?"
  [좋아, 일단 달아줘] → 자동 추천 실행 → 관제실로 이동
  [내가 직접 고를래] → /thesis/{id}/indicators 로 이동
  [나중에 할게]       → /thesis 로 이동

─────────────────────────────────────────────
[4] 경로 2: 내 생각 (entry=free_text)
─────────────────────────────────────────────

설계 문서 2.3 경로 2 플로우:

Step 1 — 자유 입력:
  AI 말풍선: "편하게 써주세요. 한 줄이어도 좋고, 길게 써도 돼요."
  → 텍스트 입력창 (멀티라인, placeholder: "시장에 대한 생각을 자유롭게...")
  → [전송] 버튼

Step 2 이후: 경로 1의 Step 3~5와 동일.
  (startConversation에 entry_source='free_text', message=입력텍스트)

─────────────────────────────────────────────
[5] [근거] 팝업 — 용어 설명
─────────────────────────────────────────────

설계 문서 2.4:

전제 카드 롱프레스 or [근거] 버튼 탭 시:
  바텀 시트로 설명 표시.
  내용: thesisApi.getPremiseExplanation(premiseId) 호출
  로딩 중에는 spinner.

─────────────────────────────────────────────
[6] components/thesis/builder/ 신규 컴포넌트
─────────────────────────────────────────────

ChatBubble.tsx:
  interface Props {
    role: 'ai' | 'user'
    children: React.ReactNode
    isLoading?: boolean   // true면 말풍선 대신 dots 애니메이션
  }

OptionButton.tsx:
  interface Props {
    label: string
    icon?: string
    onClick: () => void
    variant?: 'primary' | 'secondary' | 'danger'
  }
  - 전체 너비 버튼, 크고 탭하기 쉽게 (min-height: 52px)

PremiseCard.tsx:
  interface Props {
    content: string
    extraction_level: 'explicit' | 'implicit' | 'ai_suggested'
    onRemove: () => void
    onLongPress?: () => void
  }
  - extraction_level별 아이콘:
    explicit → 💬 (사용자가 말한 것)
    implicit → 💡 (AI가 추론)
    ai_suggested → 🤖 (AI 제안)

─────────────────────────────────────────────
[주의사항]
─────────────────────────────────────────────
- 롱프레스: onMouseDown 시작 + 500ms 후 실행 + onMouseUp으로 취소
  (터치 이벤트도 동일하게 onTouchStart/onTouchEnd)
- AI 응답 로딩 중에는 ChatBubble isLoading=true로 dots 애니메이션
- 대화 히스토리는 sessionStorage에 저장 (새로고침 시 유지)
- startConversation 실패 시 "연결에 문제가 생겼어요. 다시 시도해주세요." 표시
- 경로 3, 4 버튼은 toast("곧 열릴 기능이에요!") 표시 후 스킵
```

---

## FE-PR-4: 지표 설정 화면

> **범위:** `app/thesis/[thesisId]/indicators/page.tsx`  
> **전제조건:** FE-PR-3 머지 완료  
> **목표:** 설계 문서 섹션 2.5, 5.4의 지표 설정 UX.

---

### 📋 프롬프트

```
docs/thesis_control/thesis_control_design.md (섹션 2.5, 3.6)와
docs/thesis_control/thesis_control_math_model_final.md (섹션 12.5)를 읽고,
지표 설정 화면을 구현해줘.

─────────────────────────────────────────────
[1] app/thesis/[thesisId]/indicators/page.tsx
─────────────────────────────────────────────

'use client'

화면 구성:

────── 상단: 가설 요약 ──────
{thesis.title} {📈/📉}
"어떤 지표를 추적할까요?"

────── 전제별 지표 목록 ──────
전제마다 섹션 구분:

[전제 1] {premise.content}
  └ 지표 카드들 (수평 스크롤)
      ┌───────────┐
      │  ← 추천   │   ← 이미 추가된 것
      │  외국인    │
      │  순매수    │
      │  [제거]   │
      └───────────┘
      ┌───────────┐   ← 추가 가능한 것
      │  + 추가   │
      │  원/달러  │
      │  환율     │
      └───────────┘

────── 하단: 방향 확인 배너 ──────
수학 모델 12.5 "support_direction 실수 방지":
각 지표에 대해 배너 표시:
  "{indicator.name}가 오르면 가설에 유리한가요?"
  [유리해요 ✅] [불리해요 ❌]
  → PATCH /{thesisId}/indicators/{iid}/direction-check/

────── 완료 버튼 ──────
[관제 시작하기 →] → /thesis/{thesisId}

─────────────────────────────────────────────
[2] 지표 추가 플로우
─────────────────────────────────────────────

[+ 추가] 탭 → 바텀 시트 열림:
  "이 전제에 맞는 지표를 고르세요"
  → thesisApi.listRecommendedIndicators(thesisId, premiseId) 호출
  → 추천 지표 목록 표시 (tier 뱃지 없음 - Phase 1은 단순 목록)
  → 지표 탭 → 즉시 추가

커스텀 지표 [직접 입력]:
  지표명 입력 + 데이터 소스 선택 (드롭다운)
  → POST /indicators/ 로 추가

─────────────────────────────────────────────
[3] 자동 추천 모드
─────────────────────────────────────────────

빌더에서 [좋아, 일단 달아줘] 선택 시 이 페이지로 넘어오는 경우:
  URL: /thesis/{id}/indicators?auto=true

auto=true이면:
  진입 즉시 thesisApi.autoRecommend(thesisId) 호출
  로딩 중: "AI가 지표를 고르는 중이에요..." spinner
  완료 후: 자동으로 추가된 지표들 + 방향 확인 배너 표시
  → [관제 시작하기 →] 버튼 강조

─────────────────────────────────────────────
[4] components/thesis/indicators/ 컴포넌트
─────────────────────────────────────────────

IndicatorSetupCard.tsx:
  interface Props {
    indicator: ThesisIndicator
    mode: 'added' | 'suggestion'
    onAdd?: () => void
    onRemove?: () => void
  }
  - mode='added': 제거 버튼 표시, 체크마크
  - mode='suggestion': 추가 버튼 표시

DirectionConfirmBanner.tsx:
  interface Props {
    indicator: ThesisIndicator
    thesisTitle: string
    onConfirm: (direction: SupportDirection) => void
  }
  - 배너 형태, 노란색 테두리 (경고성)
  - "↑ {indicator.name}가 오르면 '{thesisTitle}'에..."
  - [유리해요 ✅] [불리해요 ❌]

─────────────────────────────────────────────
[주의사항]
─────────────────────────────────────────────
- 지표 추가/제거는 낙관적 업데이트 (TanStack Query useMutation 사용):
    onMutate: queryClient.getQueryData(['thesis', thesisId, 'indicators'])로
              이전 상태 스냅샷 저장 후 UI 즉시 반영
    onError:  queryClient.setQueryData(...)로 스냅샷 복원 + "변경에 실패했어요" toast
    onSettled: queryClient.invalidateQueries(['thesis', thesisId, 'indicators'])
- 방향 확인 배너: 지표 추가 후 처음 7일간만 표시
  (indicator.created_at 기준으로 7일 이내이면 표시)
- 각 전제 섹션은 수평 스크롤 (overflow-x-auto)
- 지표 0개인 전제에는 "지표를 추가하면 이 전제를 추적할 수 있어요" 안내
```

---

## FE-PR-5: 관제실 대시보드 — 카드뷰

> **범위:** `app/thesis/[thesisId]/page.tsx`  
> **전제조건:** FE-PR-4 머지 완료  
> **목표:** 설계 문서 3.1~3.6의 관제실 카드뷰. (히트맵/그래프는 Phase 2 FE에서)

---

### 📋 프롬프트

```
docs/thesis_control/thesis_control_design.md (섹션 3.1~3.6, 3.9)를 읽고,
관제실 대시보드 카드뷰를 구현해줘.

─────────────────────────────────────────────
[1] app/thesis/[thesisId]/page.tsx
─────────────────────────────────────────────

'use client'

thesisApi.dashboard(thesisId) 호출 → DashboardResponse 사용.

────── 섹션 1: 가설 헤더 ──────
{thesis.title}
등록: {날짜} | {daysWatching(thesis.created_at)}일째 관제 중
<ThesisBadge state={current_state} direction={direction} />

────── 섹션 2: 전체 흐름 (Moon Phase) ──────
설계 문서 3.1, 3.2:
  가운데 정렬, 크게:
  <MoonPhase score={overall_score} size="lg" showLabel />

  라벨 아래에 ai_summary가 있으면 표시:
  "{ai_summary}"
  (없으면 숨김)

────── 섹션 3: 뷰 전환 탭 ──────
[카드뷰] [히트맵] [그래프]

Phase 1에서:
  카드뷰 → 현재 페이지
  히트맵 → "Phase 2에서 열릴 기능이에요" toast
  그래프 → "Phase 2에서 열릴 기능이에요" toast

────── 섹션 4: 지표 카드 그리드 ──────
설계 문서 3.1:

전제별 그룹핑. 각 그룹에 전제명 소제목.
지표 카드 3열 그리드:

  <IndicatorCard
    indicator={ind}
    onClick={() => openIndicatorDetail(ind)}
  />

────── 섹션 5: 최근 변화 ──────
설계 문서 3.1 "최근 변화" 섹션:

recent_alerts 중 is_read=false인 것, 최대 2개:
  🔔 {alert.title}

없으면 "최근 특별한 변화가 없었어요."

────── 섹션 6: 하단 액션 버튼 ──────
[📊 지표 수정] → /thesis/{id}/indicators
[🏁 가설 마감] → /thesis/{id}/close

─────────────────────────────────────────────
[2] 지표 탭 → 상세 해석 바텀 시트
─────────────────────────────────────────────

설계 문서 3.6:

IndicatorCard 탭 시 바텀 시트 열림.

내용:
  {indicator.name}
  <ArrowIndicator degree={current_arrow_degree} size="lg" />
  {current_label}

  --- 해석 텍스트 ---
  thesisApi.getIndicatorContext(thesisId, indicatorId) 로 불러오기
  로딩 중: "해석을 가져오는 중이에요..."

  아래 버튼:
  [근거] → thesisApi.getIndicatorRationale() 로 [근거] 텍스트 표시
  [일단 지켜볼래] → 시트 닫기

─────────────────────────────────────────────
[3] 가설 기간 만료/점검 알림
─────────────────────────────────────────────

설계 문서 3.8:

current_state가 'expired' 또는 'needs_review'이면
페이지 상단에 배너 표시:

  expired:
    "예상하신 시점이 됐어요."
    [적중이에요 ✅] [빗나갔어요 ❌] [좀 더 지켜볼게요]

  needs_review:
    "이 가설을 세운 지 90일이 지났어요. 아직 지켜보시나요?"
    [연장할래요 (+90일)] [마감할래요] [계속 볼게요]

─────────────────────────────────────────────
[4] 실시간 새로고침
─────────────────────────────────────────────

설계 문서 3.5 "쉐이크":
  - 모바일 쉐이크 감지: DeviceMotionEvent 리스너
    (가속도 > 15 감지 시) → 데이터 refetch + "새로고침했어요!" toast
  - 상단 pull-to-refresh: overscroll-behavior-y 활용

─────────────────────────────────────────────
[5] components/thesis/dashboard/ 컴포넌트
─────────────────────────────────────────────

IndicatorDetailSheet.tsx:
  interface Props {
    indicator: ThesisIndicator | null
    thesisId: string
    onClose: () => void
  }
  - Framer Motion or CSS로 바텀 시트 슬라이드 업 애니메이션
  - 배경 오버레이 클릭 시 닫힘

ThesisExpiredBanner.tsx:
  interface Props {
    state: 'expired' | 'needs_review'
    onAction: (action: string) => void
  }

─────────────────────────────────────────────
[주의사항]
─────────────────────────────────────────────
- 데이터 동기화: 폴링(useInterval) 사용하지 않음.
  useDashboard()의 refetchOnWindowFocus: true로 처리.
  → 사용자가 다른 앱 보다가 돌아올 때 자동 최신화.
  → Celery 배치(18:30)와 맞물려 불필요한 서버 요청 0.
  수동 새로고침: 쉐이크 / pull-to-refresh 시 queryClient.invalidateQueries(['thesis', thesisId, 'dashboard']) 호출.
- 지표 0개인 가설: "아직 지표가 없어요. 지표를 추가해보세요!" + [지표 추가하기] 버튼
- warming_up 상태 (current_score null): MoonPhase 회색 + "데이터가 쌓이는 중이에요. 5일 후부터 흐름이 보여요."
```

---

## FE-PR-6: 알림 처리 + 가설 마감 복기

> **범위:** `app/thesis/alerts/page.tsx`, `app/thesis/[thesisId]/close/page.tsx`  
> **전제조건:** FE-PR-5 머지 완료  
> **목표:** 설계 문서 3.7, 3.9 구현. Phase 1 마무리.

---

### 📋 프롬프트

```
docs/thesis_control/thesis_control_design.md (섹션 3.7, 3.9)를 읽고,
알림 목록 화면과 가설 마감 복기 화면을 구현해줘.

─────────────────────────────────────────────
[1] app/thesis/alerts/page.tsx
─────────────────────────────────────────────

'use client'

thesisApi.listAlerts() 호출 → 전체 알림 목록.

────── 오늘의 변화 섹션 ──────
is_read=false인 알림, 최신순.

각 알림:
  🔔 {alert.title}
  {alert.message}
  {시간 상대표시: "3시간 전", "어제" 등}
  [확인하기] → 해당 가설 대시보드로 이동 + 자동 is_read=true 처리

[모두 읽음 처리] 버튼

────── 이전 알림 섹션 ──────
is_read=true인 알림, 최신 20개.
흐리게 표시 (opacity-50).

─────────────────────────────────────────────
[2] 알림 → 대시보드 이동 시 변화 하이라이트
─────────────────────────────────────────────

설계 문서 3.7:

/thesis/{id}?highlight={alertId} 로 이동 시:
  대시보드에서 해당 알림과 연관된 지표 카드를 1초간 pulse 애니메이션.
  (alert.indicator 필드로 카드 식별)

─────────────────────────────────────────────
[3] app/thesis/[thesisId]/close/page.tsx
─────────────────────────────────────────────

설계 문서 3.9:

'use client'

thesisApi.get(thesisId) + thesisApi.dashboard(thesisId) 호출.

────── 복기 화면 ──────
AI 말풍선 스타일로 순차 표시:

"가설을 마감합니다."

📌 {thesis.title} — {daysWatching}일간 관제
방향: {direction}

"결과가 어떠셨나요?"
[맞았어요 ✅] [빗나갔어요 ❌] [판단하기 어려워요 →]

→ 선택 후:

"가장 유용했던 지표는 어느 것인가요?"
→ 지표 목록 멀티 선택 (최대 3개 선택 가능)
  (체크박스 스타일, 탭으로 토글)

"한 줄 소감 (선택사항)"
→ 텍스트 입력 (placeholder: "이 경험에서 배운 것은...")

[가설 마감하기] →
  thesisApi.close(thesisId, { outcome, outcome_note })
  완료 후 → /thesis 로 이동 + "기록으로 남았어요 🎯" toast

────── 마감 요약 표시 ──────
AI 말풍선 형식 (설계 문서 3.9):

"가장 유용했던 지표:"
  · {선택한 지표들}

"예상과 달랐던 부분:"
  · 낮은 점수 지표들 (current_score < -0.3)을 자동으로 표시

"이 경험이 기록으로 남았어요."
[새 가설 세우기] [관제실로 돌아가기]

─────────────────────────────────────────────
[4] components/thesis/close/ 컴포넌트
─────────────────────────────────────────────

OutcomeSelector.tsx:
  interface Props {
    onSelect: (outcome: 'correct' | 'incorrect' | 'neutral') => void
  }
  - 세 버튼, 각각 이모지 + 텍스트
  - 선택 시 selected 강조 (border-white)

ClosingSummary.tsx:
  interface Props {
    thesis: Thesis
    topIndicators: ThesisIndicator[]
    weakIndicators: ThesisIndicator[]
  }
  - AI 말풍선 형식 순차 페이드인 애니메이션

─────────────────────────────────────────────
[주의사항]
─────────────────────────────────────────────
- 마감 확인: "정말 마감하시겠어요?" confirm 다이얼로그 필수
  (실수로 마감 방지)
- outcome_note는 선택사항 — 빈 문자열이어도 API 전송 OK
- 마감된 가설은 첫 화면 "관제 중" 목록에서 자동으로 사라짐
- 알림 읽음 처리: [확인하기] 탭과 동시에 markAlertRead() 호출 (비동기, 응답 기다리지 않음)
```

---

## 실행 순서 요약

```
FE-PR-1  공통 유틸 + 컴포넌트 기반 구축
  ↓ 머지
FE-PR-2  첫 화면 (가설 목록 + 진입점)
  ↓ 머지
FE-PR-3  대화형 빌더 (가설 설립)
  ↓ 머지
FE-PR-4  지표 설정 화면
  ↓ 머지
FE-PR-5  관제실 대시보드 카드뷰
  ↓ 머지
FE-PR-6  알림 목록 + 가설 마감 복기
  ↓ 머지

Phase 1 프론트엔드 완료 체크리스트:
✅ 공통 화살표·달위상 컴포넌트 (FE-PR-1)
✅ 색상·각도·라벨 유틸 (FE-PR-1)
✅ API 클라이언트 (FE-PR-1)
✅ 첫 화면 — 가설 목록 + 오늘의 변화 + 5가지 진입점 (FE-PR-2)
✅ 대화형 빌더 — 오늘 이슈 + 내 생각 경로 (FE-PR-3)
✅ [근거] 팝업 (FE-PR-3)
✅ 지표 설정 + 방향 확인 배너 (FE-PR-4)
✅ 관제실 카드뷰 + 달 위상 + AI 요약 (FE-PR-5)
✅ 지표 탭 → 해석 바텀 시트 (FE-PR-5)
✅ 알림 목록 + 읽음 처리 (FE-PR-6)
✅ 가설 마감 복기 플로우 (FE-PR-6)

Phase 2 프론트엔드에서 추가될 것:
⬜ 히트맵 뷰
⬜ 그래프 뷰
⬜ DNA 슬라이더 UI
⬜ 인기 가설 / 템플릿 경로 (3, 4)
⬜ 스냅샷 히스토리 화면
```

---

## 백엔드-프론트엔드 연결 순서

```
백엔드 PR-1~2 (모델 + 스코어링 엔진)
  ↓
백엔드 PR-3 (ViewSet + API)  ← 프론트엔드 시작 가능 시점
  ↓
FE-PR-1 ~ FE-PR-6 (병렬 가능한 부분은 병렬 진행)
  ↓
백엔드 PR-4 (Celery 태스크)  ← 이 시점부터 실제 데이터 흐름
  ↓
백엔드 PR-5 (테스트)
```

> FE-PR-1~2는 API 없이 mock 데이터로 개발 가능.  
> FE-PR-3부터 백엔드 PR-3이 있어야 실제 연동 테스트 가능.
