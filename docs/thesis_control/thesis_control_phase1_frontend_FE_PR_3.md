# FE-PR-3: 대화형 빌더 — 가설 설립 플로우 — 구현 계획 (v1)

> 버전: v1
> 작성일: 2026-03-12
> 범위: `app/thesis/new/page.tsx` 실제 구현 + 채팅 UI + 빌더 컴포넌트
> 전제조건: FE-PR-2 머지 완료
> 목표: 설계 문서 2.3~2.5 구현. 투자자가 AI와 대화하며 가설을 설립하는 채팅 인터페이스.
> 참조: `thesis_control_phase1_frontend_prompts.md` (FE-PR-3 섹션)

---

## 0. PR-2 완료 자산 & 백엔드 API 발견사항

### 0.1 PR-2에서 물려받는 자산

| 자산 | 사용 위치 |
|------|----------|
| `lib/thesis/mock.ts` (USE_MOCK 패턴) | Mock 대화 데이터 확장 |
| `lib/thesis/types.ts` (ConversationResponse, ConversationButton) | 빌더 상태 관리 |
| `lib/thesis/api.ts` (startConversation, sendMessage) | API 호출 |
| `lib/thesis/utils.ts` (relativeTime, stateToDisplay) | 완료 화면 |
| `components/thesis/list/EntryPointGrid.tsx` | 진입점 → `/thesis/new?entry={source}` |
| 임시 Toast (showTemporaryToast) | FE-PR-3에서 sonner로 교체 |

### 0.2 백엔드 API 시그니처 불일치 (Critical)

**프론트엔드 현재 (`api.ts`)**:
```ts
sendMessage: (data: { session_id: string; message: string }) =>
  POST<ConversationResponse>('/thesis/conversation/respond/', data)
```

**백엔드 실제 (`ConversationRespondView`)**:
```python
# Request
{ "conversation_state": { conv_id, entry_source, step, collected, ... }, "user_input": string|list }

# Response
{ conversation_state, message, buttons, selection_mode, step, total_steps,
  preview?, thesis_id?, done?, counter_thesis_id? }
```

→ `api.ts`의 `sendMessage` 시그니처를 백엔드에 맞춰 수정 필요.

### 0.3 ConversationResponse 타입 불완전

현재 `types.ts`:
```ts
conversation_state: string  // ❌ 실제로는 object
```

백엔드 실제:
```ts
conversation_state: {
  conv_id: string
  entry_source: string
  step: number
  collected: Record<string, unknown>
  source_news_id?: string
}
```

→ `ConversationState` 인터페이스 신규 정의 + `ConversationResponse` 타입 확장 필요.

### 0.4 백엔드 대화 플로우 구조

#### 뉴스 경로 (_process_news_path)

| step | 질문 | 선택지 | selection_mode |
|------|------|--------|---------------|
| 1 | 방향 선택 | `bullish`, `bearish`, `neutral` | single |
| 2 | 이유 선택 (neutral 아님) | REASON_CHOICES 8개 + custom | multi |
| 2 | 양쪽 추적? (neutral) | both/pick | single |
| 3 | 시점 선택 | TIMEFRAME_CHOICES 5개 | single |
| 4 | 강도 선택 | MAGNITUDE_CHOICES 4개 | single |
| 5 | 미리보기 확인 | confirm/modify | single |
| 6 | 가설 생성 | done=true | — |

#### 자유입력 경로 (_process_free_input_path)

| step | 질문 | 처리 | selection_mode |
|------|------|------|---------------|
| 1 | 텍스트 입력 | Gemini 파싱 | text |
| 2 | 정리 확인 | confirm/modify/add_premise | single |
| 3 | 전제 추가 (선택) | REASON_CHOICES | multi |
| 4 | 시점 선택 | TIMEFRAME_CHOICES | single |
| 5 | 강도 선택 | MAGNITUDE_CHOICES | single |
| 6 | 미리보기 확인 | confirm/modify | single |

#### 선택지 상수

```python
DIRECTION_CHOICES = [
  { id: 'bullish', label: '계속 오른다' },
  { id: 'bearish', label: '곧 꺾인다' },
  { id: 'neutral', label: '잘 모르겠어' },
]

REASON_CHOICES = [
  { id: 'election', label: '선거/정치 기대감 소멸', category: 'sentiment' },
  { id: 'earnings', label: '기업 실적 부진', category: 'company' },
  # ... 6개 더 ...
  { id: 'custom', label: '다른 이유', type: 'text_input' },
]

TIMEFRAME_CHOICES = [
  { id: 'short', label: '1개월 이내' },
  { id: 'medium', label: '1~3개월' },
  { id: 'half', label: '하반기 중' },
  { id: 'year', label: '연말쯤' },
  { id: 'skip', label: '모르겠어' },
]

MAGNITUDE_CHOICES = [
  { id: 'mild', label: '살짝 조정' },
  { id: 'moderate', label: '꽤 빠진다' },
  { id: 'severe', label: '크게 빠진다' },
  { id: 'skip', label: '모르겠어' },
]
```

---

## 0.5 전문가 리뷰 반영 결정사항

### UI/UX 리뷰 (P1 반영)

| # | 이슈 | 결정 | 이유 |
|---|------|------|------|
| U1 | 멀티 선택 시 완료 버튼 필요 | `selection_mode='multi'` → 하단 `[선택 완료 →]` 버튼 고정 | 선택 즉시 전송은 사고 유발 |
| U2 | OptionButton single vs multi 시각 차이 | single: 일반 버튼, multi: 왼쪽 체크박스 원형 | 모드 혼동 방지 |
| U3 | AI 로딩 상태 | Dots 애니메이션 (● ● ●, 순차 fade) | 채팅 맥락과 일치 |
| U4 | 롱프레스 근거 설명 | CSS 바텀시트 (Framer Motion 미사용) | 의존성 추가 지양 |
| U5 | 진행 표시기 | 상단 얇은 progress bar (2px, 텍스트 없음) | "아직 N단계 남았네" 부담 방지 |
| U6 | 지표 설정 분기 CTA 계층 | Primary(달아줘) + Secondary(직접) + Text link(나중에) | 핵심 경로 강조 |
| U7 | PremiseCard extraction_level 시각 구분 | explicit: gray, implicit: blue 뱃지, ai_suggested: purple 뱃지 | 사용자/AI 구분 |
| U8 | 전제 삭제 방식 | 인라인 [✕] 버튼 (스와이프 비채택) | 발견 가능성 우선 |

### 투자 도메인 리뷰 (P1 반영)

| # | 이슈 | 결정 | 이유 |
|---|------|------|------|
| I1 | 확증 편향 방지 | 백엔드가 처리 (이미 neutral 경로 양쪽 추적 지원) | 프론트는 백엔드 응답 그대로 렌더링 |
| I2 | "전제" → "근거" 용어 | 프론트 라벨에서 "근거"로 표시 | 초급자 이해도 70% vs 5% |
| I3 | 방향 선택 텍스트 | "계속 오른다" / "곧 꺾인다" / "잘 모르겠어" (백엔드 그대로) | 초급 이해도 95% |
| I4 | 근거 개수 제약 | 백엔드에서 처리 (프론트는 응답 그대로 표시) | AI가 2~3개로 자동 제한 |
| I5 | "가설 등록 완료!" 문구 | 백엔드 message 그대로 사용 (프론트 오버라이드 안 함) | 백엔드에서 톤 관리 |

### 기술 결정

| # | 결정 | 이유 |
|---|------|------|
| T1 | sonner 도입 (Toast 시스템) | 4KB, 다크테마 기본, PR-2 코드 주석에서 권장 |
| T2 | 바텀시트: CSS transform + transition | Framer Motion 의존성 추가 지양 (1인 개발 유지보수) |
| T3 | 대화 히스토리: 컴포넌트 state (sessionStorage 미사용) | 빌더는 단일 세션, 새로고침 시 처음부터 재시작이 자연스러움 |
| T4 | 뒤로가기: 첫 step에서만 `/thesis` 이동 확인 | 대화 중 step 롤백은 백엔드 미지원 → 복잡도 대비 이득 낮음 |

---

## 1. 파일 목록 (총 14개)

### 신규 생성 (9개)

```
frontend/
├── components/thesis/
│   └── builder/
│       ├── ChatBubble.tsx             # [1] AI/사용자 말풍선
│       ├── OptionButton.tsx           # [2] 선택 버튼 (single/multi)
│       ├── PremiseCard.tsx            # [3] 근거 카드 (삭제/뱃지)
│       ├── MultiSelectFooter.tsx      # [4] 멀티 선택 완료 버튼
│       ├── TextInput.tsx              # [5] 자유 텍스트 입력 영역
│       ├── BottomSheet.tsx            # [6] 바텀시트 (근거 설명)
│       └── ProgressBar.tsx            # [7] 상단 진행률 바
├── lib/thesis/
│   └── conversation.ts               # [8] 대화 상태 관리 유틸
└── app/thesis/
    └── new/
        └── page.tsx                   # [9] 대화형 빌더 페이지 (전면 교체)
```

### 기존 파일 수정 (5개)

```
frontend/
├── lib/thesis/
│   ├── types.ts                       # [10] ConversationState 타입 + ConversationResponse 확장
│   ├── api.ts                         # [11] sendMessage 시그니처 수정 (백엔드 일치)
│   └── mock.ts                        # [12] Mock 대화 데이터 추가
├── components/thesis/
│   └── list/EntryPointGrid.tsx        # [13] showTemporaryToast → sonner 교체
└── package.json                       # [14] sonner 의존성 추가
```

---

## 2. 각 파일 상세 명세

---

### [10] `lib/thesis/types.ts` — 수정

```ts
// ── 신규: 대화 상태 (백엔드 conversation_state echo) ──
export interface ConversationState {
  conv_id: string
  entry_source: string
  step: number
  collected: Record<string, unknown>
  source_news_id?: string
}

// ── 신규: 미리보기 (step 5/6에서 출현) ──
export interface ThesisPreview {
  title: string
  direction: Direction
  premises: string[]
  indicators: string[]
}

// ── 기존 ConversationButton 유지 ──
// (id, label, type?, long_press_hint? — 변경 없음)

// ── 기존 ConversationResponse 수정 ──
export interface ConversationResponse {
  message: string
  buttons: ConversationButton[]
  selection_mode: 'single' | 'multi'
  long_press_explanations?: Record<string, string>
  conversation_state: ConversationState  // ← string → ConversationState
  step: number
  total_steps: number
  input_type?: 'text'                    // ← 신규: 텍스트 입력 모드
  preview?: ThesisPreview                // ← 신규: 미리보기
  thesis_id?: string                     // ← 신규: 가설 생성 완료 시
  done?: boolean                         // ← 신규: 대화 완료 플래그
  counter_thesis_id?: string             // ← 신규: neutral → both 양쪽 생성 시
  thesis?: Thesis                        // 기존 유지
}
```

**하위 호환**: `conversation_state` 타입이 `string` → `ConversationState`로 변경. 이 필드를 사용하는 곳이 PR-1~2에 없으므로 영향 없음.

---

### [11] `lib/thesis/api.ts` — 수정

```ts
// ── 기존 startConversation 유지 (시그니처 호환) ──
startConversation: (data: { entry_source: string; news_id?: string }) =>
  POST<ConversationResponse>('/thesis/conversation/start/', data),

// ── sendMessage 시그니처 수정 (백엔드 일치) ──
// 변경 전: { session_id: string; message: string }
// 변경 후: { conversation_state: ConversationState; user_input: string | string[] }
sendMessage: (data: {
  conversation_state: ConversationState;
  user_input: string | string[];
}) => POST<ConversationResponse>('/thesis/conversation/respond/', data),
```

**주의**: `startConversation`의 `news_id`는 백엔드 `source_news_id`와 필드명 불일치. 백엔드 필드명에 맞춰 수정:

```ts
startConversation: (data: { entry_source: string; source_news_id?: string }) =>
  POST<ConversationResponse>('/thesis/conversation/start/', data),
```

---

### [12] `lib/thesis/mock.ts` — 수정

기존 MOCK_THESES, MOCK_ALERTS 유지. Mock 대화 응답 추가.

```ts
import type { ConversationResponse, ConversationState } from './types'

// ── Mock 대화 시작 응답 (뉴스 경로) ──
export const MOCK_CONVERSATION_START_NEWS: ConversationResponse = {
  message: '이 흐름이 어떻게 될 것 같아요?',
  buttons: [
    { id: 'bullish', label: '계속 오른다' },
    { id: 'bearish', label: '곧 꺾인다' },
    { id: 'neutral', label: '잘 모르겠어' },
  ],
  selection_mode: 'single',
  conversation_state: {
    conv_id: 'mock-conv-1',
    entry_source: 'news',
    step: 1,
    collected: {},
  },
  step: 1,
  total_steps: 6,
}

// ── Mock 대화 시작 응답 (자유입력 경로) ──
export const MOCK_CONVERSATION_START_FREE: ConversationResponse = {
  message: '편하게 써주세요. 한 줄이어도 좋고, 길게 써도 돼요.',
  buttons: [],
  selection_mode: 'single',
  input_type: 'text',
  conversation_state: {
    conv_id: 'mock-conv-2',
    entry_source: 'free_input',
    step: 1,
    collected: {},
  },
  step: 1,
  total_steps: 6,
}

// ── Mock 이유 선택 응답 (step 2) ──
export const MOCK_REASON_STEP: ConversationResponse = {
  message: '그렇게 생각하는 이유를 골라주세요. 여러 개 선택할 수 있어요.',
  buttons: [
    { id: 'election', label: '선거/정치 기대감 소멸' },
    { id: 'earnings', label: '기업 실적 부진' },
    { id: 'supply', label: '수급 변화', long_press_hint: true },
    { id: 'policy', label: '정책/규제 변화' },
    { id: 'global', label: '글로벌 영향' },
    { id: 'custom', label: '다른 이유', type: 'text_input' as const },
  ],
  selection_mode: 'multi',
  long_press_explanations: {
    supply: '매수·매도 주문 비율의 변화를 뜻해요. 외국인·기관 매매 동향이 대표적입니다.',
  },
  conversation_state: {
    conv_id: 'mock-conv-1',
    entry_source: 'news',
    step: 2,
    collected: { direction: 'bearish' },
  },
  step: 2,
  total_steps: 6,
}

// ── Mock 완료 응답 ──
export const MOCK_CONVERSATION_DONE: ConversationResponse = {
  message: '가설이 등록되었습니다.\n\n이제 매일 이 지표들을 관제실에서 추적할 거예요.',
  buttons: [
    { id: 'auto', label: '좋아, 일단 달아줘' },
    { id: 'manual', label: '내가 직접 고를래' },
    { id: 'later', label: '나중에 할게' },
  ],
  selection_mode: 'single',
  conversation_state: {
    conv_id: 'mock-conv-1',
    entry_source: 'news',
    step: 6,
    collected: {},
  },
  step: 6,
  total_steps: 6,
  done: true,
  thesis_id: 'mock-thesis-new',
  preview: {
    title: 'KOSPI 하반기 하락 전환',
    direction: 'bearish',
    premises: ['선거 후 정치 기대감 소멸', '외국인 매도세 전환'],
    indicators: ['외국인 순매수', '원/달러 환율', 'KOSPI EPS'],
  },
}
```

**설계 포인트**:
- 고정 데이터만 사용 (Date.now() 금지 — 버그 #24)
- Mock에서도 `conversation_state`를 echo하는 패턴 유지
- `long_press_hint`, `long_press_explanations` Mock 포함 (근거 설명 테스트)

---

### [7] `components/thesis/builder/ProgressBar.tsx` — 신규

```tsx
'use client'

interface Props {
  step: number
  totalSteps: number
}

export function ProgressBar({ step, totalSteps }: Props) {
  const percent = Math.round((step / totalSteps) * 100)

  return (
    <div className="h-0.5 bg-gray-800 w-full">
      <div
        className="h-full bg-blue-500 transition-all duration-500 ease-out"
        style={{ width: `${percent}%` }}
      />
    </div>
  )
}
```

---

### [1] `components/thesis/builder/ChatBubble.tsx` — 신규

```tsx
'use client'

interface Props {
  role: 'ai' | 'user'
  children: React.ReactNode
  isLoading?: boolean
}

export function ChatBubble({ role, children, isLoading }: Props) {
  if (isLoading) {
    return (
      <div className="flex justify-start mb-3">
        <div className="bg-gray-800 rounded-2xl rounded-tl-sm px-4 py-3 max-w-[85%]
                        flex items-center gap-1.5 min-h-[44px]">
          <span className="w-1.5 h-1.5 rounded-full bg-gray-500 animate-bounce [animation-delay:0ms]" />
          <span className="w-1.5 h-1.5 rounded-full bg-gray-500 animate-bounce [animation-delay:200ms]" />
          <span className="w-1.5 h-1.5 rounded-full bg-gray-500 animate-bounce [animation-delay:400ms]" />
        </div>
      </div>
    )
  }

  const isAi = role === 'ai'

  return (
    <div className={`flex ${isAi ? 'justify-start' : 'justify-end'} mb-3`}>
      <div className={`rounded-2xl px-4 py-3 max-w-[85%] text-sm leading-relaxed
                       whitespace-pre-line
                       ${isAi
                         ? 'bg-gray-800 text-gray-200 rounded-tl-sm'
                         : 'bg-blue-600 text-white rounded-tr-sm'}`}>
        {children}
      </div>
    </div>
  )
}
```

**설계 포인트**:
- `whitespace-pre-line`: 백엔드 message의 `\n` 줄바꿈 표시
- AI 말풍선: 좌측 정렬, `rounded-tl-sm` (좌상단 각진 꼬리)
- 사용자 말풍선: 우측 정렬, `rounded-tr-sm`
- 로딩: dots bounce 애니메이션 (3개, 200ms 간격)

---

### [2] `components/thesis/builder/OptionButton.tsx` — 신규

```tsx
'use client'

import type { ConversationButton } from '@/lib/thesis/types'

interface Props {
  button: ConversationButton
  mode: 'single' | 'multi'
  selected?: boolean
  onClick: () => void
  onLongPress?: () => void
}

export function OptionButton({ button, mode, selected, onClick, onLongPress }: Props) {
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  const handlePressStart = () => {
    if (!onLongPress) return
    timerRef.current = setTimeout(() => {
      onLongPress()
      timerRef.current = null
    }, 500)
  }

  const handlePressEnd = () => {
    if (timerRef.current) {
      clearTimeout(timerRef.current)
      timerRef.current = null
    }
  }

  const handleClick = () => {
    // 롱프레스가 실행된 경우 클릭 무시
    if (timerRef.current === null && onLongPress) return
    onClick()
  }

  // 텍스트 입력 트리거 버튼
  if (button.type === 'text_input') {
    return (
      <button
        onClick={onClick}
        className="w-full flex items-center gap-3 border border-dashed border-gray-600
                   rounded-xl px-5 py-4 text-left text-gray-400 text-sm
                   hover:border-gray-500 transition-colors active:scale-[0.98]"
      >
        <Pencil size={16} />
        {button.label}
      </button>
    )
  }

  return (
    <button
      onClick={onClick}
      onMouseDown={handlePressStart}
      onMouseUp={handlePressEnd}
      onMouseLeave={handlePressEnd}
      onTouchStart={handlePressStart}
      onTouchEnd={handlePressEnd}
      className={`w-full flex items-center gap-3 rounded-xl px-5 text-left
                  text-sm transition-all active:scale-[0.98]
                  ${mode === 'multi' ? 'min-h-[52px] py-3' : 'min-h-[56px] py-4'}
                  ${selected
                    ? 'border border-blue-500 bg-blue-900/20 text-blue-300'
                    : 'border border-gray-700 bg-transparent text-gray-200 hover:border-gray-600'}`}
    >
      {mode === 'multi' && (
        <div className={`w-5 h-5 rounded-full border-2 flex items-center justify-center flex-shrink-0
                         ${selected ? 'border-blue-500 bg-blue-500' : 'border-gray-600'}`}>
          {selected && <Check size={12} className="text-white" />}
        </div>
      )}
      <span className="flex-1">{button.label}</span>
      {button.long_press_hint && (
        <span className="text-[10px] text-gray-600">꾹 누르면 설명</span>
      )}
    </button>
  )
}
```

> import: `useRef` from 'react', `Pencil`, `Check` from 'lucide-react'

**설계 포인트**:
- `mode='single'`: 일반 버튼, min-h-[56px]
- `mode='multi'`: 좌측 체크박스 원형, min-h-[52px]
- `type='text_input'`: 점선 테두리, 연필 아이콘 (커스텀 입력 트리거)
- 롱프레스: 500ms 후 실행, mouseUp/touchEnd로 취소
- `long_press_hint`: "꾹 누르면 설명" 힌트 텍스트

---

### [3] `components/thesis/builder/PremiseCard.tsx` — 신규

```tsx
'use client'

import { X } from 'lucide-react'

interface Props {
  content: string
  extractionLevel: 'explicit' | 'implicit' | 'ai_suggested'
  onRemove?: () => void
}

const LEVEL_CONFIG = {
  explicit:     { badge: null,       border: 'border-gray-700' },
  implicit:     { badge: 'AI 추론',  border: 'border-blue-800/50' },
  ai_suggested: { badge: 'AI 제안',  border: 'border-purple-800/50' },
} as const

export function PremiseCard({ content, extractionLevel, onRemove }: Props) {
  const config = LEVEL_CONFIG[extractionLevel]

  return (
    <div className={`relative bg-gray-900 border ${config.border} rounded-xl p-4`}>
      {config.badge && (
        <span className={`text-[10px] px-2 py-0.5 rounded-full mb-2 inline-block
                          ${extractionLevel === 'implicit'
                            ? 'text-blue-400 bg-blue-900/30'
                            : 'text-purple-400 bg-purple-900/30'}`}>
          {config.badge}
        </span>
      )}
      <p className="text-gray-200 text-sm pr-8">{content}</p>
      {onRemove && (
        <button
          onClick={onRemove}
          className="absolute top-3 right-3 p-1 text-gray-600 hover:text-gray-400
                     transition-colors"
          aria-label="근거 삭제"
        >
          <X size={14} />
        </button>
      )}
    </div>
  )
}
```

**설계 포인트**:
- explicit: 뱃지 없음 (사용자 것이 기본)
- implicit: `AI 추론` 파란색 뱃지
- ai_suggested: `AI 제안` 보라색 뱃지 (Chain Sight 색상 체계 일관성)
- 인라인 [✕] 삭제 버튼 (스와이프 비채택 — 발견 가능성 우선)

---

### [4] `components/thesis/builder/MultiSelectFooter.tsx` — 신규

```tsx
'use client'

interface Props {
  selectedCount: number
  onConfirm: () => void
}

export function MultiSelectFooter({ selectedCount, onConfirm }: Props) {
  return (
    <div className="border-t border-gray-800 bg-gray-950 px-4 py-3">
      <button
        onClick={onConfirm}
        disabled={selectedCount === 0}
        className={`w-full py-3.5 rounded-xl text-sm font-medium transition-all
                    ${selectedCount > 0
                      ? 'bg-blue-600 text-white active:scale-[0.98]'
                      : 'bg-gray-800 text-gray-600 cursor-not-allowed'}`}
      >
        {selectedCount > 0
          ? `선택 완료 (${selectedCount}개) →`
          : '하나 이상 선택해주세요'}
      </button>
    </div>
  )
}
```

---

### [5] `components/thesis/builder/TextInput.tsx` — 신규

```tsx
'use client'

import { useState } from 'react'
import { Send } from 'lucide-react'

interface Props {
  placeholder?: string
  onSubmit: (text: string) => void
  disabled?: boolean
}

export function TextInput({ placeholder, onSubmit, disabled }: Props) {
  const [text, setText] = useState('')

  const handleSubmit = () => {
    const trimmed = text.trim()
    if (!trimmed || disabled) return
    onSubmit(trimmed)
    setText('')
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSubmit()
    }
  }

  return (
    <div className="border-t border-gray-800 bg-gray-950 px-4 py-3">
      <div className="flex items-end gap-2">
        <textarea
          value={text}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={placeholder ?? '시장에 대한 생각을 자유롭게...'}
          disabled={disabled}
          rows={1}
          className="flex-1 bg-gray-900 border border-gray-700 rounded-xl px-4 py-3
                     text-white text-sm placeholder-gray-600 resize-none
                     focus:outline-none focus:border-gray-600
                     min-h-[44px] max-h-[120px]"
          style={{ height: 'auto' }}
        />
        <button
          onClick={handleSubmit}
          disabled={!text.trim() || disabled}
          className={`p-3 rounded-xl transition-colors flex-shrink-0
                      ${text.trim() && !disabled
                        ? 'bg-blue-600 text-white'
                        : 'bg-gray-800 text-gray-600'}`}
        >
          <Send size={18} />
        </button>
      </div>
    </div>
  )
}
```

---

### [6] `components/thesis/builder/BottomSheet.tsx` — 신규

```tsx
'use client'

import { useEffect, useCallback } from 'react'

interface Props {
  isOpen: boolean
  onClose: () => void
  title?: string
  children: React.ReactNode
}

export function BottomSheet({ isOpen, onClose, title, children }: Props) {
  const handleEscape = useCallback((e: KeyboardEvent) => {
    if (e.key === 'Escape') onClose()
  }, [onClose])

  useEffect(() => {
    if (isOpen) {
      document.addEventListener('keydown', handleEscape)
      document.body.style.overflow = 'hidden'
    }
    return () => {
      document.removeEventListener('keydown', handleEscape)
      document.body.style.overflow = ''
    }
  }, [isOpen, handleEscape])

  if (!isOpen) return null

  return (
    <div className="fixed inset-0 z-50">
      {/* 오버레이 */}
      <div
        className="absolute inset-0 bg-black/60 transition-opacity"
        onClick={onClose}
      />
      {/* 시트 */}
      <div className="absolute bottom-0 left-0 right-0
                       bg-gray-900 rounded-t-2xl max-h-[50vh] overflow-y-auto
                       animate-slideUp">
        {/* 드래그 핸들 */}
        <div className="flex justify-center py-3">
          <div className="w-8 h-1 bg-gray-600 rounded-full" />
        </div>
        <div className="px-5 pb-8">
          {title && (
            <h3 className="text-white text-base font-medium mb-3">{title}</h3>
          )}
          {children}
        </div>
      </div>
    </div>
  )
}
```

**주의**: `animate-slideUp` 키프레임이 `globals.css`에 필요:
```css
@keyframes slideUp {
  from { transform: translateY(100%); }
  to   { transform: translateY(0); }
}
.animate-slideUp {
  animation: slideUp 0.3s ease-out;
}
```

---

### [8] `lib/thesis/conversation.ts` — 신규

대화 상태 관리 유틸. 컴포넌트와 상태 로직 분리.

```ts
import type { ConversationState, ConversationResponse, ConversationButton } from './types'

// ── 메시지 타입 ──
export interface ChatMessage {
  id: string
  role: 'ai' | 'user'
  content: string
  buttons?: ConversationButton[]
  selectionMode?: 'single' | 'multi'
  inputType?: 'text'
  longPressExplanations?: Record<string, string>
}

// ── 빌더 전체 상태 ──
export interface BuilderState {
  messages: ChatMessage[]
  conversationState: ConversationState | null
  step: number
  totalSteps: number
  isLoading: boolean
  thesisId: string | null
  counterThesisId: string | null
  isDone: boolean
}

// ── 초기 상태 ──
export const INITIAL_BUILDER_STATE: BuilderState = {
  messages: [],
  conversationState: null,
  step: 0,
  totalSteps: 6,
  isLoading: false,
  thesisId: null,
  counterThesisId: null,
  isDone: false,
}

// ── API 응답 → 상태 업데이트 ──
export function applyResponse(
  state: BuilderState,
  response: ConversationResponse,
  userMessage?: string,
): BuilderState {
  const newMessages = [...state.messages]

  // 사용자 메시지 추가 (있으면)
  if (userMessage) {
    newMessages.push({
      id: `user-${Date.now()}`,
      role: 'user',
      content: userMessage,
    })
  }

  // AI 메시지 추가
  newMessages.push({
    id: `ai-${response.step}`,
    role: 'ai',
    content: response.message,
    buttons: response.buttons,
    selectionMode: response.selection_mode,
    inputType: response.input_type,
    longPressExplanations: response.long_press_explanations,
  })

  return {
    ...state,
    messages: newMessages,
    conversationState: response.conversation_state,
    step: response.step,
    totalSteps: response.total_steps,
    isLoading: false,
    thesisId: response.thesis_id ?? state.thesisId,
    counterThesisId: response.counter_thesis_id ?? state.counterThesisId,
    isDone: response.done ?? false,
  }
}

// ── 사용자 선택을 라벨로 변환 ──
export function selectionToLabel(
  input: string | string[],
  buttons: ConversationButton[],
): string {
  if (typeof input === 'string') {
    const btn = buttons.find(b => b.id === input)
    return btn?.label ?? input
  }
  return input
    .map(id => buttons.find(b => b.id === id)?.label ?? id)
    .join(', ')
}
```

---

### [9] `app/thesis/new/page.tsx` — 전면 교체

이 파일이 가장 크고 복잡합니다. 핵심 구조만 명세합니다.

```tsx
'use client'

import { useState, useEffect, useRef } from 'react'
import { useSearchParams, useRouter } from 'next/navigation'
import { thesisApi } from '@/lib/thesis/api'
import { USE_MOCK, MOCK_CONVERSATION_START_NEWS,
         MOCK_CONVERSATION_START_FREE, MOCK_REASON_STEP,
         MOCK_CONVERSATION_DONE } from '@/lib/thesis/mock'
import type { ConversationResponse, ConversationButton } from '@/lib/thesis/types'
import {
  BuilderState, INITIAL_BUILDER_STATE, applyResponse, selectionToLabel,
} from '@/lib/thesis/conversation'
import { ChatBubble } from '@/components/thesis/builder/ChatBubble'
import { OptionButton } from '@/components/thesis/builder/OptionButton'
import { MultiSelectFooter } from '@/components/thesis/builder/MultiSelectFooter'
import { TextInput } from '@/components/thesis/builder/TextInput'
import { BottomSheet } from '@/components/thesis/builder/BottomSheet'
import { ProgressBar } from '@/components/thesis/builder/ProgressBar'
import { ArrowLeft } from 'lucide-react'
import Link from 'next/link'

export default function ThesisNewPage() {
  const searchParams = useSearchParams()
  const router = useRouter()
  const entry = searchParams.get('entry') ?? 'free_text'

  const [state, setState] = useState<BuilderState>(INITIAL_BUILDER_STATE)
  const [selectedIds, setSelectedIds] = useState<string[]>([])
  const [sheetContent, setSheetContent] = useState<{
    title: string; text: string
  } | null>(null)

  const scrollRef = useRef<HTMLDivElement>(null)

  // ── 대화 시작 ──
  useEffect(() => {
    startConversation(entry)
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  async function startConversation(entrySource: string) {
    setState(s => ({ ...s, isLoading: true }))

    if (USE_MOCK) {
      const mockResponse = entrySource === 'news'
        ? MOCK_CONVERSATION_START_NEWS
        : MOCK_CONVERSATION_START_FREE
      setState(s => applyResponse(s, mockResponse))
      return
    }

    try {
      const response = await thesisApi.startConversation({
        entry_source: entrySource,
      })
      setState(s => applyResponse(s, response))
    } catch {
      setState(s => ({
        ...s,
        isLoading: false,
        messages: [...s.messages, {
          id: 'error',
          role: 'ai' as const,
          content: '연결에 문제가 생겼어요. 다시 시도해주세요.',
        }],
      }))
    }
  }

  // ── 응답 전송 (single/text) ──
  async function sendResponse(input: string | string[], label: string) {
    if (!state.conversationState) return

    // 사용자 메시지를 먼저 표시
    setState(s => ({
      ...s,
      isLoading: true,
      messages: [...s.messages, {
        id: `user-${Date.now()}`,
        role: 'user',
        content: label,
      }],
    }))

    if (USE_MOCK) {
      // Mock: step에 따라 다음 응답 결정
      setTimeout(() => {
        const mockNext = state.step < 5 ? MOCK_REASON_STEP : MOCK_CONVERSATION_DONE
        setState(s => applyResponse(s, mockNext))
      }, 800)
      return
    }

    try {
      const response = await thesisApi.sendMessage({
        conversation_state: state.conversationState,
        user_input: input,
      })
      setState(s => applyResponse(s, response))
    } catch {
      setState(s => ({
        ...s,
        isLoading: false,
        messages: [...s.messages, {
          id: `error-${Date.now()}`,
          role: 'ai' as const,
          content: '연결에 문제가 생겼어요. 다시 시도해주세요.',
        }],
      }))
    }
  }

  // ── 단일 선택 핸들러 ──
  function handleSingleSelect(button: ConversationButton) {
    sendResponse(button.id, button.label)
  }

  // ── 멀티 선택 토글 ──
  function handleMultiToggle(buttonId: string) {
    setSelectedIds(prev =>
      prev.includes(buttonId)
        ? prev.filter(id => id !== buttonId)
        : [...prev, buttonId],
    )
  }

  // ── 멀티 선택 완료 ──
  function handleMultiConfirm() {
    if (selectedIds.length === 0) return
    const lastMsg = state.messages[state.messages.length - 1]
    const label = selectionToLabel(selectedIds, lastMsg?.buttons ?? [])
    sendResponse(selectedIds, label)
    setSelectedIds([])
  }

  // ── 텍스트 전송 ──
  function handleTextSubmit(text: string) {
    sendResponse(text, text)
  }

  // ── 롱프레스 (근거 설명) ──
  function handleLongPress(buttonId: string) {
    const lastMsg = state.messages[state.messages.length - 1]
    const explanations = lastMsg?.longPressExplanations
    if (explanations?.[buttonId]) {
      const btn = lastMsg?.buttons?.find(b => b.id === buttonId)
      setSheetContent({
        title: btn?.label ?? '설명',
        text: explanations[buttonId],
      })
    }
  }

  // ── 완료 후 네비게이션 ──
  function handleComplete(action: string) {
    if (!state.thesisId) {
      router.push('/thesis')
      return
    }
    switch (action) {
      case 'auto':
        router.push(`/thesis/${state.thesisId}/indicators?auto=true`)
        break
      case 'manual':
        router.push(`/thesis/${state.thesisId}/indicators`)
        break
      default:
        router.push('/thesis')
    }
  }

  // ── 스크롤 최하단 유지 ──
  useEffect(() => {
    scrollRef.current?.scrollTo({
      top: scrollRef.current.scrollHeight,
      behavior: 'smooth',
    })
  }, [state.messages, state.isLoading])

  // ── 마지막 메시지의 버튼/모드 추출 ──
  const lastMessage = state.messages[state.messages.length - 1]
  const activeButtons = (!state.isLoading && lastMessage?.role === 'ai')
    ? lastMessage.buttons ?? []
    : []
  const activeMode = lastMessage?.selectionMode ?? 'single'
  const showTextInput = lastMessage?.inputType === 'text' && !state.isLoading

  return (
    <div className="flex flex-col h-[calc(100dvh-env(safe-area-inset-top))]
                    bg-gray-950">
      {/* ── 상단 헤더 ── */}
      <div className="flex items-center gap-3 px-4 py-3 border-b border-gray-800">
        <Link href="/thesis" className="p-1 text-gray-400 hover:text-white">
          <ArrowLeft size={20} />
        </Link>
        <h1 className="text-white text-base font-medium flex-1">가설 세우기</h1>
      </div>

      {/* ── 진행률 바 ── */}
      <ProgressBar step={state.step} totalSteps={state.totalSteps} />

      {/* ── 메시지 스크롤 영역 ── */}
      <div ref={scrollRef} className="flex-1 overflow-y-auto px-4 pt-4 pb-4">
        {state.messages.map((msg) => (
          <ChatBubble key={msg.id} role={msg.role}>
            {msg.content}
          </ChatBubble>
        ))}

        {/* AI 로딩 중 */}
        {state.isLoading && <ChatBubble role="ai" isLoading />}
      </div>

      {/* ── 하단 고정 영역 ── */}
      <div className="flex-shrink-0">
        {/* 버튼 선택지 (single 또는 multi) */}
        {activeButtons.length > 0 && !state.isDone && (
          <div className="border-t border-gray-800 bg-gray-950 px-4 py-3 space-y-2">
            {activeButtons.map((btn) => (
              <OptionButton
                key={btn.id}
                button={btn}
                mode={activeMode}
                selected={activeMode === 'multi' ? selectedIds.includes(btn.id) : undefined}
                onClick={() => {
                  if (activeMode === 'multi') {
                    handleMultiToggle(btn.id)
                  } else {
                    handleSingleSelect(btn)
                  }
                }}
                onLongPress={btn.long_press_hint ? () => handleLongPress(btn.id) : undefined}
              />
            ))}
          </div>
        )}

        {/* 멀티 선택 완료 버튼 */}
        {activeMode === 'multi' && activeButtons.length > 0 && !state.isDone && (
          <MultiSelectFooter
            selectedCount={selectedIds.length}
            onConfirm={handleMultiConfirm}
          />
        )}

        {/* 텍스트 입력 */}
        {showTextInput && (
          <TextInput
            onSubmit={handleTextSubmit}
            disabled={state.isLoading}
          />
        )}

        {/* 완료 분기 (지표 설정) */}
        {state.isDone && activeButtons.length > 0 && (
          <div className="border-t border-gray-800 bg-gray-950 px-4 py-4 space-y-2">
            {/* Primary CTA */}
            <button
              onClick={() => handleComplete('auto')}
              className="w-full py-4 bg-blue-600 text-white text-sm font-medium
                         rounded-xl active:scale-[0.98] transition-transform"
            >
              좋아, 일단 달아줘
            </button>
            {/* Secondary */}
            <button
              onClick={() => handleComplete('manual')}
              className="w-full py-3.5 border border-gray-600 text-gray-200 text-sm
                         rounded-xl active:scale-[0.98] transition-transform"
            >
              내가 직접 고를래
            </button>
            {/* Tertiary (텍스트 링크) */}
            <button
              onClick={() => handleComplete('later')}
              className="w-full py-2 text-gray-500 text-sm text-center"
            >
              나중에 할게
            </button>
          </div>
        )}
      </div>

      {/* ── 바텀시트 (롱프레스 근거 설명) ── */}
      <BottomSheet
        isOpen={!!sheetContent}
        onClose={() => setSheetContent(null)}
        title={sheetContent?.title}
      >
        <p className="text-gray-300 text-sm leading-relaxed">
          {sheetContent?.text}
        </p>
        <button
          onClick={() => setSheetContent(null)}
          className="mt-4 w-full py-3 bg-gray-800 text-gray-300 text-sm rounded-xl"
        >
          이해했어
        </button>
      </BottomSheet>
    </div>
  )
}
```

---

### [13] `components/thesis/list/EntryPointGrid.tsx` — 수정

`showTemporaryToast` → sonner의 `toast` 교체.

```diff
+ import { toast } from 'sonner'

  const handleClick = (entry: EntryPoint) => {
    if (!entry.enabled) {
-     showTemporaryToast('곧 열릴 기능이에요!')
+     toast('곧 열릴 기능이에요!')
      return
    }
    router.push(`/thesis/new?entry=${entry.source}`)
  }

- // showTemporaryToast 함수 전체 삭제 (80줄 → 0줄)
```

**주의**: sonner의 `<Toaster />` 를 `app/thesis/layout.tsx`에 추가 필요:

```tsx
import { Toaster } from 'sonner'

// layout return에 추가:
<Toaster position="bottom-center" theme="dark" />
```

### [14] `package.json` — 수정

```bash
npm install sonner
```

---

## 3. 의존성 그래프

```
lib/thesis/types.ts (수정: ConversationState, ThesisPreview 추가)
    │
    ├→ lib/thesis/api.ts (수정: sendMessage 시그니처)
    │
    ├→ lib/thesis/conversation.ts (신규: ChatMessage, BuilderState, applyResponse)
    │
    └→ lib/thesis/mock.ts (수정: Mock 대화 데이터 추가)

components/thesis/builder/ (신규 7개)
    │
    ├→ ChatBubble.tsx (독립)
    ├→ OptionButton.tsx (types 의존)
    ├→ PremiseCard.tsx (독립)
    ├→ MultiSelectFooter.tsx (독립)
    ├→ TextInput.tsx (독립)
    ├→ BottomSheet.tsx (독립)
    └→ ProgressBar.tsx (독립)

app/thesis/new/page.tsx (전면 교체 — 모든 builder 컴포넌트 + conversation.ts 의존)

components/thesis/list/EntryPointGrid.tsx (수정: sonner 교체)
app/thesis/layout.tsx (수정: Toaster 추가)
```

---

## 4. 구현 순서

```
Phase A (독립, 병렬):
  |- lib/thesis/types.ts 수정 (ConversationState, ThesisPreview, ConversationResponse 확장)
  |- lib/thesis/conversation.ts 신규 (ChatMessage, BuilderState, applyResponse)
  |- npm install sonner

Phase B (Phase A 의존, 병렬):
  |- lib/thesis/api.ts 수정 (sendMessage 시그니처)
  |- lib/thesis/mock.ts 수정 (Mock 대화 데이터)
  |- components/thesis/builder/ChatBubble.tsx
  |- components/thesis/builder/OptionButton.tsx
  |- components/thesis/builder/PremiseCard.tsx
  |- components/thesis/builder/MultiSelectFooter.tsx
  |- components/thesis/builder/TextInput.tsx
  |- components/thesis/builder/BottomSheet.tsx
  |- components/thesis/builder/ProgressBar.tsx

Phase C (Phase B 의존):
  |- globals.css에 slideUp 키프레임 추가
  |- app/thesis/layout.tsx에 Toaster 추가
  |- components/thesis/list/EntryPointGrid.tsx sonner 교체

Phase D (Phase C 의존):
  |- app/thesis/new/page.tsx 전면 교체

Phase E (Phase D 의존):
  |- tsc --noEmit + npm run build 검증
  |- 브라우저 Mock 모드 테스트
```

---

## 5. 검증 체크리스트

### 5.1 빌드 검증

| 검증 항목 | 명령어 | 기대 결과 |
|----------|--------|----------|
| TypeScript 타입 체크 | `tsc --noEmit` | 에러 0개 |
| Next.js 빌드 | `npm run build` | 성공 |
| 기존 기능 회귀 | `/thesis` 목록 페이지 | Mock 정상 동작 |

### 5.2 Mock 검증

| 시나리오 | 기대 동작 |
|---------|----------|
| `/thesis/new?entry=free_text` | 텍스트 입력 UI 표시 |
| `/thesis/new?entry=news` | 방향 선택 버튼 3개 표시 |
| 버튼 클릭 | 사용자 말풍선 + AI 로딩 dots + AI 응답 |
| 멀티 선택 | 체크박스 토글 + 선택 완료 버튼 |
| 텍스트 입력 후 전송 | 사용자 말풍선 + AI 응답 |
| 대화 완료 | 3개 CTA (Primary/Secondary/Text link) |
| 콘솔 API 에러 | 0건 (Mock 모드) |

### 5.3 UI 검증

| 시나리오 | 기대 동작 |
|---------|----------|
| 진행률 바 | step 변경 시 부드럽게 채워짐 |
| 스크롤 | 새 메시지 추가 시 자동 최하단 스크롤 |
| 롱프레스 (500ms) | 바텀시트 열림 + 설명 텍스트 |
| 바텀시트 오버레이 클릭 | 시트 닫힘 |
| ESC 키 | 바텀시트 닫힘 |
| 텍스트 입력 Enter | 전송 (Shift+Enter는 줄바꿈) |
| 빈 텍스트 전송 버튼 | 비활성화 (회색) |
| 에러 발생 시 | "연결에 문제가 생겼어요" AI 말풍선 |

### 5.4 접근성 검증

| 항목 | 기대 |
|------|------|
| 터치 타겟 | 모든 버튼 min-h-[52px] 이상 |
| 삭제 버튼 | aria-label="근거 삭제" |
| 키보드 | ESC로 바텀시트 닫기 |
| 다크 테마 | bg-white, text-black 0개 |

---

## 6. 리스크 및 완화

| # | 리스크 | 심각도 | 완화 |
|---|--------|--------|------|
| 1 | sendMessage 시그니처 변경 (기존 호출부 파손) | 낮음 | PR-1~2에서 sendMessage 미사용. 첫 사용처가 이 PR |
| 2 | ConversationResponse.conversation_state 타입 변경 | 낮음 | PR-1~2에서 이 필드 미참조 |
| 3 | sonner 의존성 추가 | 낮음 | 4KB, zero-config, 다크테마 기본 |
| 4 | Mock 대화 흐름이 백엔드 실제와 다를 수 있음 | 중간 | Mock은 UI 레이아웃 검증용. 백엔드 연동 시 실제 응답으로 전환 |
| 5 | iOS Safari 키보드로 하단 영역 가림 | 중간 | `100dvh` 사용 + `env(safe-area-inset-top)` |
| 6 | 롱프레스가 클릭과 충돌 | 낮음 | timerRef null 체크로 분리 |
| 7 | animate-slideUp 미정의 시 바텀시트 깨짐 | 낮음 | globals.css에 키프레임 추가 필수 체크 |

---

## 7. 기술 부채

| 부채 | 영향 | 해소 시점 |
|------|------|----------|
| Mock 대화 흐름 하드코딩 | 백엔드 연동 후 제거 필요 | 백엔드 PR-3 연동 시 |
| sessionStorage 미사용 | 새로고침 시 대화 초기화 | Phase 2에서 필요 시 추가 |
| step 롤백 (뒤로가기) 미지원 | 대화 중 이전 선택 수정 불가 | 백엔드 step rollback API 추가 시 |
| PremiseCard 프론트 전용 | 백엔드 preview에서 전제 목록 제공 시 활용 | FE-PR-4 지표 설정에서 확장 |
| 바텀시트 드래그 닫기 미구현 | 오버레이 클릭/ESC만 닫기 | Phase 2에서 touch gesture 추가 |
| Toast (sonner) thesis 전용 | 다른 페이지는 여전히 toast 없음 | 글로벌 layout에 Toaster 이동 시 |

---

## 8. 후속 PR 연결

| 이 PR에서 만든 것 | 사용하는 PR |
|------------------|------------|
| ChatBubble | FE-PR-6 가설 마감 복기에서 재사용 |
| OptionButton | FE-PR-6 마감 선택지에서 재사용 |
| PremiseCard | FE-PR-5 대시보드 전제 표시에서 재사용 |
| BottomSheet | FE-PR-4 지표 추가 시트, FE-PR-5 지표 상세 시트에서 재사용 |
| TextInput | FE-PR-6 마감 소감 입력에서 재사용 |
| ProgressBar | FE-PR-3 전용 (재사용 없음) |
| conversation.ts | FE-PR-3 전용 (재사용 없음) |
| sonner Toast | FE-PR-4~6에서 동일 패턴 사용 |
| ConversationState 타입 | 이후 모든 대화 관련 코드에서 사용 |
| api.ts sendMessage 수정 | 이후 대화 API 호출 시 정확한 시그니처 |

---

## 9. Claude Code 실행 프롬프트

```
FE-PR-3 구현 계획서(docs/thesis_control/thesis_control_phase1_frontend_FE_PR_3.md) v1을 읽고,
Thesis Control 대화형 빌더를 구현해줘.

─────────────────────────────────────────────
[구현 순서]
─────────────────────────────────────────────

1단계: 의존성 + 타입 수정
  - npm install sonner
  - lib/thesis/types.ts: ConversationState, ThesisPreview, ConversationResponse 확장
  - lib/thesis/api.ts: sendMessage 시그니처 수정 (conversation_state + user_input)
  - lib/thesis/conversation.ts: ChatMessage, BuilderState, applyResponse, selectionToLabel
  - lib/thesis/mock.ts: Mock 대화 응답 4개 추가

2단계: 빌더 컴포넌트 (7개, 병렬 생성)
  - components/thesis/builder/ChatBubble.tsx
  - components/thesis/builder/OptionButton.tsx (롱프레스 + single/multi)
  - components/thesis/builder/PremiseCard.tsx (extraction_level 3단계)
  - components/thesis/builder/MultiSelectFooter.tsx
  - components/thesis/builder/TextInput.tsx
  - components/thesis/builder/BottomSheet.tsx (CSS animation, Framer Motion 미사용)
  - components/thesis/builder/ProgressBar.tsx

3단계: 글로벌 설정
  - globals.css: slideUp 키프레임 추가
  - app/thesis/layout.tsx: <Toaster /> 추가
  - components/thesis/list/EntryPointGrid.tsx: showTemporaryToast → sonner toast 교체

4단계: 페이지 교체
  - app/thesis/new/page.tsx: 전면 교체
    · useSearchParams로 entry 파라미터 읽기
    · startConversation → Mock/실제 분기
    · sendResponse → single/multi/text 분기
    · handleComplete → auto/manual/later 네비게이션
    · 스크롤 자동 최하단 (useEffect + scrollRef)
    · 바텀시트 롱프레스 근거 설명

─────────────────────────────────────────────
[핵심 주의사항]
─────────────────────────────────────────────
- 다크 테마 전용. bg-white, text-black 절대 사용하지 않음.
- sendMessage의 시그니처: { conversation_state, user_input } (백엔드 일치).
- Mock 데이터에 Date.now() 사용 금지 (hydration 불일치 버그 #24).
- selection_mode='multi' 시 하단 [선택 완료] 버튼 필수.
- 완료 분기 3개 CTA: Primary(bg-blue-600) + Secondary(border) + Text link(text-gray-500).
- BottomSheet는 CSS transform + transition (Framer Motion 의존성 추가하지 않음).
- 롱프레스: 500ms, onMouseDown/Up + onTouchStart/End 모두 처리.
- 에러 시 "연결에 문제가 생겼어요" AI 말풍선으로 표시 (alert/modal 아님).
- EntryPointGrid의 showTemporaryToast 함수 + 주석 80줄 전체 삭제 후 sonner 교체.
- 구현 후 tsc --noEmit + npm run build 검증 필수.
```
