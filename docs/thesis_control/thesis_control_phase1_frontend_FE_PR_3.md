# FE-PR-3: 대화형 빌더 — 가설 설립 플로우 — 구현 계획 (v3)

> 버전: v3
> 작성일: 2026-03-12 (v2: 1차 리뷰, v3: 2차 리뷰 반영)
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

### 0.3.1 EntrySource 화이트리스트 불일치 (Critical)

백엔드 `ALLOWED_ENTRY_SOURCES`:
```python
ALLOWED_ENTRY_SOURCES = {'news', 'free_input', 'popular', 'template', 'chainsight'}
```

프론트 `page.tsx` 기본값: `'free_text'` ← **백엔드에 없는 값. 400 에러 발생.**

→ `types.ts`에 `EntrySource` union type 정의 + `page.tsx` 기본값 `'free_input'`으로 수정 필요.

### 0.3.2 Preview 응답 구조 (백엔드 확인 완료)

백엔드 `_build_thesis_summary()`가 반환하는 preview 구조:
```python
'preview': {
    'title': str,                          # 가설 제목
    'direction': str,                      # 'bullish' | 'bearish' | 'neutral'
    'premises': [{'content': str, 'category': str}, ...],   # 구조체 배열
    'indicators': [{'name': str, 'indicator_type': str}, ...],
}
```

→ `ThesisPreview` 타입의 `premises`를 `string[]` → `{content: string; category: string}[]`로 수정 필요.
→ Preview 단계에서 PremiseCard로 구조화된 렌더링 필요 (page.tsx에 포함).

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
| 6 | 가설 생성 완료 + 지표 설정 분기 | done=true, buttons=[] (CTA 프론트 하드코딩) | — |

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
| T3 | conv_id를 sessionStorage에 저장. 다음 진입 시 새 대화로 덮어씀 (cleanup에서 삭제하지 않음) | 백엔드 Redis 세션(30분 TTL) 활용. StrictMode 이중 실행 방지 |
| T4 | 뒤로가기: 첫 step에서만 `/thesis` 이동 확인 | 대화 중 step 롤백은 백엔드 미지원 → 복잡도 대비 이득 낮음 |
| T5 | `useLongPress` 커스텀 훅 분리 | 롱프레스/클릭 충돌 방지 로직 재사용성 + 훅 단위 테스트 가능 |
| T6 | `EntrySource` union type | 백엔드 화이트리스트와 프론트 상수 단일 소스 |
| T7 | 데스크톱 롱프레스 대체: info 아이콘 + BottomSheet | 롱프레스는 모바일 전용. 데스크톱 접근성 보장 |

---

## 0.6 리뷰 반영 이력

### v2 (1차 리뷰)

| # | v1 이슈 | v2 변경 |
|---|---------|---------|
| R1 | OptionButton 롱프레스/클릭 충돌 | `useLongPress` 커스텀 훅, `longPressTriggered` 플래그 |
| R2 | entry_source `'free_text'` vs `'free_input'` | `EntrySource` union type, `'free_input'` 통일 |
| R3 | Mock step 분기 부족 | step별 mock 응답 Map, selection_mode 명시 |
| R4 | `applyResponse` userMessage 미사용 | 파라미터 제거, AI 응답 추가만 담당 |
| R5 | PremiseCard 사용처 없음 | preview 단계 렌더링 추가 |
| R6 | OptionButton import 누락 | 모든 코드블록에 완전한 import |
| R7 | 대화 상태 영속성 미고려 | conv_id sessionStorage 저장 |
| R8 | Gemini 지연 대응 없음 | 로딩 dots + 재시도 버튼 |
| R9 | 데스크톱 롱프레스 접근성 | Info 아이콘 반응형 분기 |

### v3 (2차 리뷰)

| # | v2 이슈 | v3 변경 | 심각도 |
|---|---------|---------|--------|
| H1 | `loadConvId` 사용처 없음 (죽은 코드) | 제거. `saveConvId`/`clearConvId`만 유지 | **High** |
| H2 | useEffect cleanup clearConvId → StrictMode 이중 실행 | cleanup 제거. 다음 진입 시 덮어쓰기 방식 | **High** |
| H3 | retry가 항상 startConversation → 중간 진행 소실 | `lastRequest` 필드 (conversation.ts) + `handleSingleSelect` 내 `__retry__` 분기에서 재시도 (page.tsx) | **High** |
| H4 | setTimeout 안에서 stale closure (state.step) | `setState(s => ...)` 함수형 업데이트 | **High** |
| H5 | AI 메시지 id `ai-${step}` → modify 분기 충돌 | `messageCounter` 기반 + `generateMessageId` 헬퍼 | **High** |
| H6 | conversationState null일 때 버튼 노출 | `activeButtons`에 `conversationState !== null` + `!isErrorMessage` 가드. 에러 재시도 UI는 별도 분기 | **High** |
| M1 | textarea 자동 높이 조절 미작동 | `scrollHeight` 기반 auto-resize 로직 | Medium |
| M2 | step 6 mock buttons 죽은 데이터 | `buttons: []` + 주석 "완료 CTA 프론트 하드코딩" | Medium |
| M3 | CATEGORY_CONFIG 백엔드 카테고리 누락 | 8개 (sentiment, company, macro, policy, technical, global, supply, valuation) + `DEFAULT_CATEGORY` "기타" | Medium |
| M4 | BottomSheet 오버레이 이벤트 버블링 | `e.stopPropagation()` 추가 | Medium |
| M5 | ProgressBar 0% → "시작 안 한" 느낌 | page.tsx에서 `{state.step > 0 && <ProgressBar />}` 조건부 렌더링. ProgressBar.tsx 변경 없음 | Medium |
| M6 | selectedIds 에러 시에도 초기화 | `sendResponse` → `Promise<boolean>`. handleMultiConfirm: 성공 시만 `setSelectedIds([])`. handleSingleSelect/handleTextSubmit: 반환값 무시 | Medium |
| M7 | BottomSheet 닫기 애니메이션 없음 | 기술 부채 명시 "열기만 slideUp, 닫기 즉시" | Medium |
| M8 | whitespace-pre-line 과도한 여백 | 리스크에 기록. 연속 줄바꿈 정규화 옵션 | Medium |
| L1 | OptionButton hasExplanation 삼항 6줄 반복 | `pressHandlers` 객체 스프레드 | Low |
| L2 | EntrySource type/array 이중 관리 | `as const` 배열 → type 추출 단일 소스 | Low |
| L3 | selectionToLabel fallback이 영어 id 노출 | `(${input})` 괄호 감싸기 | Low |
| L4 | TextInput placeholder 톤 불일치 | 비반영: placeholder와 AI 메시지는 역할이 다름 (input hint vs 대화) | Low |
| L5 | useLongPress threshold 음수 방어 없음 | `Math.max(threshold, 100)` | Low |
| L6 | 파일 목록에 layout.tsx 누락 | 수정 7개 → 총 17개 | Low |
| L7 | 메시지 id 생성 로직 분산 | H5와 통합, `generateMessageId` 한 곳에서 관리 | Low |
| L8 | step 1 mock에 long_press 없어 테스트 불가 | `neutral`에 long_press_hint 추가 | Low |
| L9 | free_input 경로 체크리스트 누락 | 검증 시나리오 2개 추가 | Low |
| L10 | handleComplete 404 라우팅 | mock 모드: `/thesis` 고정 + TODO 주석 | Low |
| L12 | step 6 플로우 설명 부족 | "지표 설정 분기 (프론트 하드코딩)" 추가 | Low |
| N1 | MOCK_STEP_MAP이 news 전용, free_input 테스트 불가 | entry별 Mock Map 분리: `MOCK_NEWS_STEP_MAP` + `MOCK_FREE_STEP_MAP` + `MOCK_FREE_CONFIRM_STEP` | Medium |
| D1 | page.tsx가 "신규 생성" 카테고리 | "기존 파일 수정"으로 이동 | — |
| D2 | 기술 결정 T3 취소선 Claude Code 해석 불가 | v2에서 이미 취소선 제거하고 v2 결정만 남김 (확인) | — |
| D4 | 해결된 리스크(#6) 취소선 노이즈 | 삭제 | — |
| D5 | conversation.ts "재사용 없음" | "FE-PR-6 유사 패턴 참고 가능" | — |

---

## 1. 파일 목록 (총 17개)

### 신규 생성 (9개)

```
frontend/
├── hooks/
│   └── useLongPress.ts                # [1] 롱프레스 커스텀 훅 (재사용 가능)
├── components/thesis/
│   └── builder/
│       ├── ChatBubble.tsx             # [2] AI/사용자 말풍선
│       ├── OptionButton.tsx           # [3] 선택 버튼 (single/multi + useLongPress)
│       ├── PremiseCard.tsx            # [4] 근거 카드 (preview 단계 렌더링)
│       ├── MultiSelectFooter.tsx      # [5] 멀티 선택 완료 버튼
│       ├── TextInput.tsx              # [6] 자유 텍스트 입력 영역
│       ├── BottomSheet.tsx            # [7] 바텀시트 (근거 설명)
│       └── ProgressBar.tsx            # [8] 상단 진행률 바
└── lib/thesis/
    └── conversation.ts               # [9] 대화 상태 관리 유틸
```

### 기존 파일 수정 (8개)

```
frontend/
├── lib/thesis/
│   ├── types.ts                       # [10] ENTRY_SOURCES, EntrySource, ConversationState, ThesisPreview
│   ├── api.ts                         # [11] sendMessage 시그니처 수정 (백엔드 일치)
│   └── mock.ts                        # [12] step별 Mock 대화 응답 Map
├── components/thesis/
│   └── list/EntryPointGrid.tsx        # [13] showTemporaryToast → sonner 교체
├── app/thesis/
│   ├── layout.tsx                     # [14] <Toaster /> 추가
│   └── new/page.tsx                   # [15] 대화형 빌더 페이지 (전면 교체)
├── app/globals.css                    # [16] slideUp 키프레임 추가
└── package.json                       # [17] sonner 의존성 추가
```

---

## 2. 각 파일 상세 명세

---

### [10] `lib/thesis/types.ts` — 수정

```ts
// ── 신규: 진입점 소스 (백엔드 ALLOWED_ENTRY_SOURCES 화이트리스트) ──
// v3(L2): as const 배열에서 type 추출 — 단일 소스
export const ENTRY_SOURCES = ['news', 'free_input', 'popular', 'template', 'chainsight'] as const
export type EntrySource = (typeof ENTRY_SOURCES)[number]

// ── 신규: 대화 상태 (백엔드 conversation_state echo) ──
export interface ConversationState {
  conv_id: string
  entry_source: EntrySource
  step: number
  collected: Record<string, unknown>
  source_news_id?: string
}

// ── 신규: 미리보기 전제 (백엔드 구조체 일치) ──
export interface PreviewPremise {
  content: string
  category: string
}

// ── 신규: 미리보기 지표 ──
export interface PreviewIndicator {
  name: string
  indicator_type: string
}

// ── 신규: 미리보기 (step 5/6에서 출현) ──
export interface ThesisPreview {
  title: string
  direction: Direction
  premises: PreviewPremise[]       // ← string[] 아님! 백엔드 {content, category} 구조체
  indicators: PreviewIndicator[]   // ← string[] 아님! 백엔드 {name, indicator_type} 구조체
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

**하위 호환**: `conversation_state` 타입이 `string` → `ConversationState`로 변경. PR-1~2에서 미참조.
**EntrySource**: `ENTRY_SOURCES` 배열이 단일 소스. page.tsx의 `toEntrySource()`에서도 이 배열 import.

---

### [11] `lib/thesis/api.ts` — 수정

```ts
import type { ConversationResponse, ConversationState, EntrySource } from './types'

// ── startConversation: 필드명 백엔드 일치 ──
// 변경: news_id → source_news_id, entry_source: string → EntrySource
startConversation: (data: { entry_source: EntrySource; source_news_id?: string }) =>
  POST<ConversationResponse>('/thesis/conversation/start/', data),

// ── sendMessage 시그니처 수정 (백엔드 일치) ──
// 변경 전: { session_id: string; message: string }
// 변경 후: { conversation_state: ConversationState; user_input: string | string[] }
sendMessage: (data: {
  conversation_state: ConversationState;
  user_input: string | string[];
}) => POST<ConversationResponse>('/thesis/conversation/respond/', data),
```

---

### [12] `lib/thesis/mock.ts` — 수정

기존 MOCK_THESES, MOCK_ALERTS 유지. **step별 Mock 응답 Map** 추가.

**v2 변경**: 전 step 동일 응답 → step별 분기. selection_mode 명시로 single/multi 전환 프론트 로직 검증 가능.

```ts
import type { ConversationResponse } from './types'

// ── Mock 대화 시작 응답 (뉴스 경로) ──
export const MOCK_CONVERSATION_START_NEWS: ConversationResponse = {
  message: '이 흐름이 어떻게 될 것 같아요?',
  buttons: [
    { id: 'bullish', label: '계속 오른다' },
    { id: 'bearish', label: '곧 꺾인다' },
    { id: 'neutral', label: '잘 모르겠어', long_press_hint: true },  // v3(L8): step 1 롱프레스 테스트
  ],
  selection_mode: 'single',
  long_press_explanations: {
    neutral: '양쪽 시나리오를 동시에 추적하고 싶을 때 선택하세요.',
  },
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

// ── step 2: 이유 선택 (multi) ──
const MOCK_REASON_STEP: ConversationResponse = {
  message: '그렇게 생각하는 이유를 골라주세요. 여러 개 선택할 수 있어요.',
  buttons: [
    { id: 'election', label: '선거/정치 기대감 소멸' },
    { id: 'earnings', label: '기업 실적 부진' },
    { id: 'supply', label: '수급 변화', long_press_hint: true },
    { id: 'policy', label: '정책/규제 변화' },
    { id: 'global', label: '글로벌 영향' },
    { id: 'custom', label: '다른 이유', type: 'text_input' as const },
  ],
  selection_mode: 'multi',                    // ← multi 검증
  long_press_explanations: {
    supply: '매수·매도 주문 비율의 변화를 뜻해요. 외국인·기관 매매 동향이 대표적입니다.',
  },
  conversation_state: {
    conv_id: 'mock-conv-1', entry_source: 'news', step: 2,
    collected: { direction: 'bearish' },
  },
  step: 2,
  total_steps: 6,
}

// ── step 3: 시점 선택 (single) ──
const MOCK_TIMEFRAME_STEP: ConversationResponse = {
  message: '언제쯤 그런 흐름이 올 거라고 보시나요?',
  buttons: [
    { id: 'short', label: '1개월 이내' },
    { id: 'medium', label: '1~3개월' },
    { id: 'half', label: '하반기 중' },
    { id: 'year', label: '연말쯤' },
    { id: 'skip', label: '모르겠어' },
  ],
  selection_mode: 'single',                   // ← single 검증
  conversation_state: {
    conv_id: 'mock-conv-1', entry_source: 'news', step: 3,
    collected: { direction: 'bearish', reasons: ['election', 'supply'] },
  },
  step: 3,
  total_steps: 6,
}

// ── step 4: 강도 선택 (single) ──
const MOCK_MAGNITUDE_STEP: ConversationResponse = {
  message: '얼마나 크게 움직일 것 같아요?',
  buttons: [
    { id: 'mild', label: '살짝 조정' },
    { id: 'moderate', label: '꽤 빠진다' },
    { id: 'severe', label: '크게 빠진다' },
    { id: 'skip', label: '모르겠어' },
  ],
  selection_mode: 'single',                   // ← single 검증
  conversation_state: {
    conv_id: 'mock-conv-1', entry_source: 'news', step: 4,
    collected: { direction: 'bearish', reasons: ['election', 'supply'], timeframe: 'half' },
  },
  step: 4,
  total_steps: 6,
}

// ── step 5: 미리보기 확인 (single, preview 포함) ──
const MOCK_PREVIEW_STEP: ConversationResponse = {
  message: '이렇게 정리해봤어요. 확인해주세요.',
  buttons: [
    { id: 'confirm', label: '좋아, 이대로 가자' },
    { id: 'modify', label: '수정할 부분 있어' },
  ],
  selection_mode: 'single',
  conversation_state: {
    conv_id: 'mock-conv-1', entry_source: 'news', step: 5,
    collected: { direction: 'bearish', reasons: ['election', 'supply'], timeframe: 'half', magnitude: 'moderate' },
  },
  step: 5,
  total_steps: 6,
  preview: {
    title: 'KOSPI 하반기 하락 전환',
    direction: 'bearish',
    premises: [
      { content: '선거 후 정치 기대감 소멸', category: 'sentiment' },
      { content: '외국인 매도세 전환', category: 'macro' },
    ],
    indicators: [
      { name: '외국인 순매수', indicator_type: 'order_flow' },
      { name: '원/달러 환율', indicator_type: 'macro' },
      { name: 'KOSPI EPS', indicator_type: 'valuation' },
    ],
  },
}

// ── step 6: 완료 ──
// v3(M2): buttons 비움. 완료 CTA는 프론트 하드코딩 (page.tsx handleComplete)
const MOCK_CONVERSATION_DONE: ConversationResponse = {
  message: '가설이 등록되었습니다.\n\n이제 매일 이 지표들을 관제실에서 추적할 거예요.',
  buttons: [],
  selection_mode: 'single',
  conversation_state: {
    conv_id: 'mock-conv-1', entry_source: 'news', step: 6,
    collected: {},
  },
  step: 6,
  total_steps: 6,
  done: true,
  thesis_id: 'mock-thesis-new',
}

// ── free_input step 2: Gemini 파싱 결과 확인 (single) ──
// v3(N1): free_input 경로 전용. news 경로에서는 사용하지 않음.
const MOCK_FREE_CONFIRM_STEP: ConversationResponse = {
  message: '이렇게 정리해봤어요.\n\n"KOSPI가 하반기에 하락 전환할 것이다"\n\n맞나요?',
  buttons: [
    { id: 'confirm', label: '맞아, 이대로 가자' },
    { id: 'modify', label: '좀 다르게 바꿀래' },
    { id: 'add_premise', label: '근거를 더 추가할래' },
  ],
  selection_mode: 'single',
  conversation_state: {
    conv_id: 'mock-conv-2', entry_source: 'free_input', step: 2,
    collected: { raw_input: '코스피 하반기 하락' },
  },
  step: 2,
  total_steps: 6,
}

// ── v3(N1): entry_source별 Mock Map 분리 ──
// ⚠️ setTimeout 안에서 state.step 직접 참조 금지 — setState(s => ...) 사용 (H4)

// news 경로
export const MOCK_NEWS_STEP_MAP: Record<number, ConversationResponse> = {
  2: MOCK_REASON_STEP,        // multi-select
  3: MOCK_TIMEFRAME_STEP,     // single-select
  4: MOCK_MAGNITUDE_STEP,     // single-select
  5: MOCK_PREVIEW_STEP,       // single + preview 구조체
  6: MOCK_CONVERSATION_DONE,  // done=true
}

// free_input 경로
export const MOCK_FREE_STEP_MAP: Record<number, ConversationResponse> = {
  2: MOCK_FREE_CONFIRM_STEP,  // single (confirm/modify/add_premise)
  3: MOCK_REASON_STEP,        // multi-select (전제 추가)
  4: MOCK_TIMEFRAME_STEP,     // single-select
  5: MOCK_MAGNITUDE_STEP,     // single-select
  6: MOCK_PREVIEW_STEP,       // single + preview 구조체
  7: MOCK_CONVERSATION_DONE,  // done=true
}

// 하위 호환
export const MOCK_STEP_MAP = MOCK_NEWS_STEP_MAP
```

**설계 포인트**:
- 고정 데이터만 사용 (Date.now() 금지 — 버그 #24)
- Mock에서도 `conversation_state`를 echo하는 패턴 유지
- `long_press_hint`, `long_press_explanations` Mock 포함 (근거 설명 테스트)
- **v2**: step별 selection_mode 명시 → single/multi 전환 검증 가능
- **v2**: preview 구조체가 백엔드와 동일한 `{content, category}` 형태
- **v3(N1)**: entry_source별 Mock Map 분리 — `MOCK_NEWS_STEP_MAP` (news) + `MOCK_FREE_STEP_MAP` (free_input)
- **v3(N1)**: free_input step 2는 confirm/modify/add_premise (single). news step 2와 selection_mode 다름

---

### [1] `hooks/useLongPress.ts` — 신규

롱프레스/클릭 충돌 방지 커스텀 훅. **재사용 가능** (thesis 외 EOD 등에서도 사용 예정).

```ts
import { useRef, useCallback } from 'react'

interface UseLongPressOptions {
  /** 롱프레스 인식 시간 (ms). 기본값 500 */
  threshold?: number
  /** 롱프레스 콜백 */
  onLongPress: () => void
  /** 일반 클릭 콜백 */
  onClick: () => void
}

interface UseLongPressReturn {
  /** 버튼의 onClick에 바인딩 */
  handleClick: () => void
  /** onMouseDown / onTouchStart에 바인딩 */
  handlePressStart: () => void
  /** onMouseUp / onMouseLeave / onTouchEnd에 바인딩 */
  handlePressEnd: () => void
}

export function useLongPress({
  threshold = 500,
  onLongPress,
  onClick,
}: UseLongPressOptions): UseLongPressReturn {
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const longPressTriggeredRef = useRef(false)

  const safeThreshold = Math.max(threshold, 100)  // v3(L5): 음수/극소값 방어

  const handlePressStart = useCallback(() => {
    longPressTriggeredRef.current = false
    timerRef.current = setTimeout(() => {
      longPressTriggeredRef.current = true
      onLongPress()
    }, safeThreshold)
  }, [onLongPress, safeThreshold])

  const handlePressEnd = useCallback(() => {
    if (timerRef.current) {
      clearTimeout(timerRef.current)
      timerRef.current = null
    }
  }, [])

  const handleClick = useCallback(() => {
    if (longPressTriggeredRef.current) {
      longPressTriggeredRef.current = false
      return
    }
    onClick()
  }, [onClick])

  return { handleClick, handlePressStart, handlePressEnd }
}
```

**설계 포인트**:
- `longPressTriggeredRef` 플래그로 롱프레스 후 클릭 이벤트 무시 (v1 버그 수정)
- `useCallback`으로 안정적 참조 (부모 리렌더 시 불필요한 재생성 방지)
- `threshold` 기본 500ms, 커스터마이징 가능
- 훅 단위 `renderHook` 테스트 가능 (타이머 동작 검증)
- `onMouseLeave`도 `handlePressEnd`에 바인딩 — 버튼 바깥으로 드래그 시 타이머 취소

---

### [8] `components/thesis/builder/ProgressBar.tsx` — 신규

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

### [2] `components/thesis/builder/ChatBubble.tsx` — 신규

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

### [3] `components/thesis/builder/OptionButton.tsx` — 신규

```tsx
'use client'

import { Pencil, Check, Info } from 'lucide-react'
import type { ConversationButton } from '@/lib/thesis/types'
import { useLongPress } from '@/hooks/useLongPress'

interface Props {
  button: ConversationButton
  mode: 'single' | 'multi'
  selected?: boolean
  onClick: () => void
  onShowExplanation?: () => void
}

export function OptionButton({ button, mode, selected, onClick, onShowExplanation }: Props) {
  // 롱프레스 훅 (long_press_hint 있는 버튼만)
  const longPress = useLongPress({
    threshold: 500,
    onLongPress: () => onShowExplanation?.(),
    onClick,
  })

  const hasExplanation = !!button.long_press_hint && !!onShowExplanation

  // v3(L1): 이벤트 핸들러 객체로 정리 (삼항 6줄 반복 제거)
  const pressHandlers = hasExplanation ? {
    onClick: longPress.handleClick,
    onMouseDown: longPress.handlePressStart,
    onMouseUp: longPress.handlePressEnd,
    onMouseLeave: longPress.handlePressEnd,
    onTouchStart: longPress.handlePressStart,
    onTouchEnd: longPress.handlePressEnd,
  } : { onClick }

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
      {...pressHandlers}
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
      {hasExplanation && (
        <>
          {/* 모바일: 롱프레스 힌트 */}
          <span className="text-[10px] text-gray-600 sm:hidden">꾹 누르면 설명</span>
          {/* 데스크톱: info 아이콘 클릭 (롱프레스 대체) */}
          <button
            type="button"
            onClick={(e) => { e.stopPropagation(); onShowExplanation?.() }}
            className="hidden sm:flex p-1 text-gray-600 hover:text-gray-400 transition-colors"
            aria-label={`${button.label} 설명 보기`}
          >
            <Info size={14} />
          </button>
        </>
      )}
    </button>
  )
}
```

**설계 포인트 (v2 변경)**:
- **`useLongPress` 훅 사용**: 인라인 timerRef/handleClick 제거 → 훅으로 분리 (R1)
- **`longPressTriggered` 플래그**: 빠른 탭과 롱프레스 정확히 분리 (v1 버그 수정)
- **`hasExplanation` 가드**: long_press_hint 없는 버튼은 훅 바인딩 생략 (불필요한 이벤트 리스너 방지)
- **데스크톱 접근성 (R9)**: `sm:hidden` / `hidden sm:flex` 반응형 분기
  - 모바일: "꾹 누르면 설명" 텍스트 + 롱프레스
  - 데스크톱: `Info` 아이콘 클릭 + `e.stopPropagation()` (부모 onClick 방지)
- **prop 이름**: `onLongPress` → `onShowExplanation` (의도 명확화)
- `mode='single'`: 일반 버튼, min-h-[56px]
- `mode='multi'`: 좌측 체크박스 원형, min-h-[52px]
- `type='text_input'`: 점선 테두리, 연필 아이콘 (커스텀 입력 트리거)

---

### [4] `components/thesis/builder/PremiseCard.tsx` — 신규

**v2 변경**: preview 단계에서 백엔드 `{content, category}` 구조체 렌더링용.
`extractionLevel` 대신 `category`(sentiment, company, macro 등) 기반 뱃지.
삭제 버튼은 preview 단계에서는 modify 분기로 처리하므로 선택적.

```tsx
'use client'

import { X } from 'lucide-react'
import type { PreviewPremise } from '@/lib/thesis/types'

interface Props {
  premise: PreviewPremise
  onRemove?: () => void
}

// v3(M3): 백엔드 REASON_CHOICES category 전체 커버 + fallback "기타"
const CATEGORY_CONFIG: Record<string, { label: string; className: string }> = {
  sentiment:  { label: '심리',     className: 'text-orange-400 bg-orange-900/30' },
  company:    { label: '기업',     className: 'text-green-400 bg-green-900/30' },
  macro:      { label: '매크로',   className: 'text-blue-400 bg-blue-900/30' },
  policy:     { label: '정책',     className: 'text-purple-400 bg-purple-900/30' },
  technical:  { label: '기술적',   className: 'text-cyan-400 bg-cyan-900/30' },
  global:     { label: '글로벌',   className: 'text-yellow-400 bg-yellow-900/30' },
  supply:     { label: '수급',     className: 'text-pink-400 bg-pink-900/30' },
  valuation:  { label: '밸류에이션', className: 'text-emerald-400 bg-emerald-900/30' },
}
const DEFAULT_CATEGORY = { label: '기타', className: 'text-gray-400 bg-gray-800' }

export function PremiseCard({ premise, onRemove }: Props) {
  const config = CATEGORY_CONFIG[premise.category] ?? DEFAULT_CATEGORY

  return (
    <div className="relative bg-gray-900 border border-gray-700 rounded-xl p-4">
      <span className={`text-[10px] px-2 py-0.5 rounded-full mb-2 inline-block ${config.className}`}>
        {config.label}
      </span>
      <p className="text-gray-200 text-sm pr-8">{premise.content}</p>
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
- **v3**: `extractionLevel` 제거 → 백엔드 `category` 기반 뱃지 8종 (sentiment, company, macro, policy, technical, global, supply, valuation)
- **v2**: props가 `PreviewPremise` 타입 직접 수용 → 변환 로직 불필요
- 인라인 [✕] 삭제 버튼 (스와이프 비채택 — 발견 가능성 우선)
- preview 단계에서 onRemove 미전달 시 삭제 버튼 숨김
- FE-PR-5 대시보드에서도 재사용 가능

---

### [5] `components/thesis/builder/MultiSelectFooter.tsx` — 신규

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

### [6] `components/thesis/builder/TextInput.tsx` — 신규

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
          onChange={(e) => {
            setText(e.target.value)
            // v3(M1): auto-resize
            e.target.style.height = 'auto'
            e.target.style.height = `${Math.min(e.target.scrollHeight, 120)}px`
          }}
          onKeyDown={handleKeyDown}
          placeholder={placeholder ?? '시장에 대한 생각을 자유롭게...'}
          disabled={disabled}
          rows={1}
          className="flex-1 bg-gray-900 border border-gray-700 rounded-xl px-4 py-3
                     text-white text-sm placeholder-gray-600 resize-none
                     focus:outline-none focus:border-gray-600
                     min-h-[44px] max-h-[120px]"
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

### [7] `components/thesis/builder/BottomSheet.tsx` — 신규

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
      {/* 오버레이 — v3(M4): stopPropagation으로 아래 버튼 이벤트 방지 */}
      <div
        className="absolute inset-0 bg-black/60 transition-opacity"
        onClick={(e) => { e.stopPropagation(); onClose() }}
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

### [9] `lib/thesis/conversation.ts` — 신규

대화 상태 관리 유틸. 컴포넌트와 상태 로직 분리.

```ts
import type { ConversationState, ConversationResponse, ConversationButton, ThesisPreview } from './types'

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

// ── v3(H3): 마지막 요청 저장 (에러 시 재시도용) ──
export interface LastRequest {
  conversation_state: ConversationState
  user_input: string | string[]
  label: string
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
  preview: ThesisPreview | null
  messageCounter: number                // v3(H5): 메시지 id 충돌 방지 카운터
  lastRequest: LastRequest | null       // v3(H3): 에러 재시도용
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
  preview: null,
  messageCounter: 0,
  lastRequest: null,
}

// ── v3(H5, L7): 메시지 id 생성 헬퍼 — 한 곳에서 관리 ──
export function generateMessageId(state: BuilderState, prefix: 'ai' | 'user' | 'error'): string {
  return `${prefix}-${state.messageCounter}`
}

// ── API 응답 → AI 메시지 추가 ──
// 사용자 메시지는 page.tsx에서 직접 setState로 추가.
// 이 함수는 AI 응답 추가 + 상태 업데이트만 담당.
export function applyResponse(
  state: BuilderState,
  response: ConversationResponse,
): BuilderState {
  const newMessages = [...state.messages]

  newMessages.push({
    id: generateMessageId(state, 'ai'),
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
    preview: response.preview ?? state.preview,
    messageCounter: state.messageCounter + 1,
    lastRequest: null,  // 성공 시 초기화
  }
}

// ── 사용자 선택을 라벨로 변환 ──
// v3(L3): fallback에 괄호 감싸기 (영어 id 직접 노출 방지)
export function selectionToLabel(
  input: string | string[],
  buttons: ConversationButton[],
): string {
  if (typeof input === 'string') {
    const btn = buttons.find(b => b.id === input)
    return btn?.label ?? `(${input})`
  }
  return input
    .map(id => buttons.find(b => b.id === id)?.label ?? `(${id})`)
    .join(', ')
}

// ── conv_id 영속성 ──
// v3(H1): loadConvId 제거 (사용처 없음). 복원 API는 백엔드 추가 시 구현.
const CONV_STORAGE_KEY = 'thesis_builder_conv_id'

export function saveConvId(convId: string): void {
  try { sessionStorage.setItem(CONV_STORAGE_KEY, convId) } catch {}
}

export function clearConvId(): void {
  try { sessionStorage.removeItem(CONV_STORAGE_KEY) } catch {}
}
```

**v3 변경 포인트**:
- `messageCounter`: 메시지 id를 순번 기반으로 생성. `ai-${step}` → `ai-${counter}` (H5)
- `generateMessageId`: id 생성 로직 한 곳에서 관리 (L7)
- `lastRequest`: 에러 시 동일 요청 재시도 가능 (H3)
- `loadConvId` 제거: 사용처 없는 죽은 코드 (H1)
- `selectionToLabel` fallback: `(${id})` 괄호 감싸기 (L3)

---

### [15] `app/thesis/new/page.tsx` — 전면 교체

이 파일이 가장 크고 복잡합니다. 핵심 구조만 명세합니다.

**v3 변경점**: H2(cleanup 제거), H3(lastRequest 재시도), H4(stale closure), H5(messageCounter), H6(null 가드), M5(ProgressBar 숨김), M6(selectedIds 성공 시만 초기화), L10(mock handleComplete).

```tsx
'use client'

import { useState, useEffect, useRef } from 'react'
import { useSearchParams, useRouter } from 'next/navigation'
import { thesisApi } from '@/lib/thesis/api'
import { USE_MOCK, MOCK_CONVERSATION_START_NEWS,
         MOCK_CONVERSATION_START_FREE, MOCK_NEWS_STEP_MAP, MOCK_FREE_STEP_MAP,
         MOCK_CONVERSATION_DONE } from '@/lib/thesis/mock'
import { ENTRY_SOURCES, type EntrySource, type ConversationButton } from '@/lib/thesis/types'
import {
  type BuilderState, INITIAL_BUILDER_STATE, applyResponse, selectionToLabel,
  generateMessageId, saveConvId, clearConvId,
} from '@/lib/thesis/conversation'
import { ChatBubble } from '@/components/thesis/builder/ChatBubble'
import { OptionButton } from '@/components/thesis/builder/OptionButton'
import { PremiseCard } from '@/components/thesis/builder/PremiseCard'
import { MultiSelectFooter } from '@/components/thesis/builder/MultiSelectFooter'
import { TextInput } from '@/components/thesis/builder/TextInput'
import { BottomSheet } from '@/components/thesis/builder/BottomSheet'
import { ProgressBar } from '@/components/thesis/builder/ProgressBar'
import { ArrowLeft } from 'lucide-react'
import Link from 'next/link'

// ── v3(L2): ENTRY_SOURCES 배열 import로 검증 (이중 관리 방지) ──
function toEntrySource(value: string | null): EntrySource {
  if (value && (ENTRY_SOURCES as readonly string[]).includes(value)) return value as EntrySource
  return 'free_input'
}

export default function ThesisNewPage() {
  const searchParams = useSearchParams()
  const router = useRouter()
  const entry = toEntrySource(searchParams.get('entry'))

  const [state, setState] = useState<BuilderState>(INITIAL_BUILDER_STATE)
  const [selectedIds, setSelectedIds] = useState<string[]>([])
  const [sheetContent, setSheetContent] = useState<{
    title: string; text: string
  } | null>(null)

  const scrollRef = useRef<HTMLDivElement>(null)

  // ── 대화 시작 ──
  // v3(H2): cleanup에서 clearConvId 제거. StrictMode 이중 실행 방지.
  // 다음 진입 시 새 대화로 덮어씀.
  useEffect(() => {
    startConversation(entry)
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  async function startConversation(entrySource: EntrySource) {
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
      saveConvId(response.conversation_state.conv_id)
      setState(s => applyResponse(s, response))
    } catch {
      showError()
    }
  }

  // ── 에러 메시지 (재시도 UI는 JSX에서 별도 렌더링) ──
  // v3(H6): showError에서 buttons 제거. 에러 재시도 버튼은 activeButtons 밖에서 별도 분기.
  function showError() {
    setState(s => ({
      ...s,
      isLoading: false,
      messages: [...s.messages, {
        id: `error-${s.messageCounter}`,
        role: 'ai' as const,
        content: '연결에 문제가 생겼어요. 아래 버튼으로 다시 시도할 수 있어요.',
        // buttons 없음 — 재시도 UI는 page.tsx JSX에서 별도 렌더링
      }],
      messageCounter: s.messageCounter + 1,
    }))
  }

  // ── 응답 전송 — boolean 반환 (v3: M6 성공/실패 분기) ──
  async function sendResponse(input: string | string[], label: string): Promise<boolean> {
    if (!state.conversationState) return false

    // 사용자 메시지를 먼저 표시
    setState(s => ({
      ...s,
      isLoading: true,
      messages: [...s.messages, {
        id: generateMessageId(s, 'user'),
        role: 'user',
        content: label,
      }],
      messageCounter: s.messageCounter + 1,
      // v3(H3): 요청 저장 (에러 시 재시도용)
      lastRequest: {
        conversation_state: s.conversationState!,
        user_input: input,
        label,
      },
    }))

    if (USE_MOCK) {
      // v3(H4): setState 함수형 업데이트로 stale closure 방지
      // v3(N1): entry에 따라 올바른 Mock Map 선택
      setTimeout(() => {
        setState(s => {
          const nextStep = s.step + 1
          const stepMap = entry === 'free_input' ? MOCK_FREE_STEP_MAP : MOCK_NEWS_STEP_MAP
          const mockNext = stepMap[nextStep] ?? MOCK_CONVERSATION_DONE
          return applyResponse(s, mockNext)
        })
      }, 800)
      return true
    }

    try {
      const response = await thesisApi.sendMessage({
        conversation_state: state.conversationState,
        user_input: input,
      })
      setState(s => applyResponse(s, response))
      return true
    } catch {
      showError()  // v3(H3): 전송 실패 → 에러 메시지 + 재시도 UI
      return false
    }
  }

  // ── 단일 선택 핸들러 ──
  function handleSingleSelect(button: ConversationButton) {
    // v3(H3): 재시도 분기 — lastRequest 있으면 동일 요청 재전송
    if (button.id === '__retry__') {
      setState(s => ({
        ...s,
        messages: s.messages.filter(m => !m.id.startsWith('error-')),
      }))
      if (state.lastRequest) {
        sendResponse(state.lastRequest.user_input, state.lastRequest.label)
      } else {
        startConversation(entry)
      }
      return
    }
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

  // ── 멀티 선택 완료 — v3(M6): 성공 시에만 selectedIds 초기화 ──
  async function handleMultiConfirm() {
    if (selectedIds.length === 0) return
    const lastMsg = state.messages[state.messages.length - 1]
    const label = selectionToLabel(selectedIds, lastMsg?.buttons ?? [])
    const success = await sendResponse(selectedIds, label)
    if (success) setSelectedIds([])
  }

  // ── 텍스트 전송 ──
  function handleTextSubmit(text: string) {
    sendResponse(text, text)
  }

  // ── 근거 설명 표시 ──
  function handleShowExplanation(buttonId: string) {
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
    clearConvId()
    // v3(L10): mock 모드에서 /thesis/[id]/indicators는 404 (FE-PR-4 범위)
    if (USE_MOCK || !state.thesisId) {
      router.push('/thesis')
      return
    }
    switch (action) {
      case 'auto':
        // TODO: FE-PR-4에서 /thesis/[id]/indicators 구현 후 활성화
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
  // v3(H6): conversationState null이면 버튼 숨김. 에러 메시지의 재시도는 별도 분기.
  const lastMessage = state.messages[state.messages.length - 1]
  const isErrorMessage = !!lastMessage?.id?.startsWith('error-')
  const activeButtons = (
    !state.isLoading
    && lastMessage?.role === 'ai'
    && state.conversationState !== null
    && !isErrorMessage
  ) ? lastMessage.buttons ?? [] : []
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

      {/* ── 진행률 바 — v3(M5): step 0일 때 숨김 ── */}
      {state.step > 0 && (
        <ProgressBar step={state.step} totalSteps={state.totalSteps} />
      )}

      {/* ── 메시지 스크롤 영역 ── */}
      <div ref={scrollRef} className="flex-1 overflow-y-auto px-4 pt-4 pb-4">
        {state.messages.map((msg) => (
          <ChatBubble key={msg.id} role={msg.role}>
            {msg.content}
          </ChatBubble>
        ))}

        {/* Preview 카드 렌더링 */}
        {state.preview && (
          <div className="mb-3 space-y-2">
            <p className="text-xs text-gray-500 px-1">근거 ({state.preview.premises.length}개)</p>
            {state.preview.premises.map((premise, i) => (
              <PremiseCard key={i} premise={premise} />
            ))}
          </div>
        )}

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
                onShowExplanation={
                  btn.long_press_hint ? () => handleShowExplanation(btn.id) : undefined
                }
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

        {/* 에러 재시도 — v3(H6): activeButtons와 별도 분기 */}
        {!state.isLoading && isErrorMessage && (
          <div className="border-t border-gray-800 bg-gray-950 px-4 py-3">
            <button
              onClick={() => handleSingleSelect({ id: '__retry__', label: '다시 시도' })}
              className="w-full py-3.5 border border-gray-600 text-gray-200 text-sm
                         rounded-xl active:scale-[0.98] transition-transform"
            >
              다시 시도
            </button>
          </div>
        )}

        {/* 완료 분기 — 프론트 하드코딩 CTA (백엔드 buttons 미사용) */}
        {state.isDone && (
          <div className="border-t border-gray-800 bg-gray-950 px-4 py-4 space-y-2">
            <button
              onClick={() => handleComplete('auto')}
              className="w-full py-4 bg-blue-600 text-white text-sm font-medium
                         rounded-xl active:scale-[0.98] transition-transform"
            >
              좋아, 일단 달아줘
            </button>
            <button
              onClick={() => handleComplete('manual')}
              className="w-full py-3.5 border border-gray-600 text-gray-200 text-sm
                         rounded-xl active:scale-[0.98] transition-transform"
            >
              내가 직접 고를래
            </button>
            <button
              onClick={() => handleComplete('later')}
              className="w-full py-2 text-gray-500 text-sm text-center"
            >
              나중에 할게
            </button>
          </div>
        )}
      </div>

      {/* ── 바텀시트 (근거 설명) ── */}
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

**v3 변경 사항 요약**:
1. H2: useEffect cleanup에서 `clearConvId()` 제거. StrictMode 이중 실행 방지.
2. H3: `lastRequest` 저장 (sendResponse) + `handleSingleSelect` 내 `__retry__` 분기에서 재시도.
3. H4: Mock setTimeout 안에서 `setState(s => ...)` 함수형 업데이트.
4. H5: `generateMessageId(s, prefix)` 사용 (step 기반 → 카운터 기반).
5. H6: `activeButtons`에 `conversationState !== null` + `!isErrorMessage` 가드. 에러 재시도 UI 별도 분기.
6. M5: page.tsx에서 `{state.step > 0 && <ProgressBar />}` 조건부 렌더링. ProgressBar.tsx 변경 없음.
7. M6: `sendResponse` → `Promise<boolean>`. `handleMultiConfirm`: 성공 시만 `setSelectedIds([])`. `handleSingleSelect`/`handleTextSubmit`: 반환값 무시.
8. N1: entry별 Mock Map — `MOCK_NEWS_STEP_MAP` (news) + `MOCK_FREE_STEP_MAP` (free_input).
9. L2: `ENTRY_SOURCES` 배열 import로 `toEntrySource` 검증.
10. L10: Mock 모드에서 `handleComplete` → `/thesis` 고정.

---

### [14] `components/thesis/list/EntryPointGrid.tsx` — 수정

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

### [16] `app/globals.css` — 수정

BottomSheet 슬라이드 애니메이션 키프레임 추가:

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

### [17] `package.json` — 수정

```bash
npm install sonner
```

---

## 3. 의존성 그래프

```
lib/thesis/types.ts (수정: EntrySource, ConversationState, PreviewPremise, ThesisPreview)
    │
    ├→ lib/thesis/api.ts (수정: sendMessage + startConversation 시그니처)
    │
    ├→ lib/thesis/conversation.ts (신규: BuilderState, applyResponse, messageCounter, lastRequest, generateMessageId, conv_id 영속성)
    │
    └→ lib/thesis/mock.ts (수정: entry별 Mock Map — MOCK_NEWS_STEP_MAP + MOCK_FREE_STEP_MAP)

hooks/useLongPress.ts (신규: 독립)
    │
    └→ components/thesis/builder/OptionButton.tsx

components/thesis/builder/ (신규 7개)
    │
    ├→ ChatBubble.tsx (독립)
    ├→ OptionButton.tsx (types + useLongPress 의존)
    ├→ PremiseCard.tsx (types.PreviewPremise 의존)
    ├→ MultiSelectFooter.tsx (독립)
    ├→ TextInput.tsx (독립)
    ├→ BottomSheet.tsx (독립)
    └→ ProgressBar.tsx (독립)

app/thesis/new/page.tsx (전면 교체 — 모든 builder 컴포넌트 + conversation.ts + mock.ts)

components/thesis/list/EntryPointGrid.tsx (수정: sonner 교체)
app/thesis/layout.tsx (수정: Toaster 추가)
app/globals.css (수정: slideUp 키프레임)
```

---

## 4. 구현 순서

```
Phase A (독립, 병렬):
  |- lib/thesis/types.ts 수정 (EntrySource, ConversationState, PreviewPremise, ThesisPreview, ConversationResponse 확장)
  |- lib/thesis/conversation.ts 신규 (BuilderState + messageCounter + lastRequest, applyResponse, generateMessageId, saveConvId/clearConvId)
  |- hooks/useLongPress.ts 신규 (커스텀 훅, 독립)
  |- npm install sonner

Phase B (Phase A 의존, 병렬):
  |- lib/thesis/api.ts 수정 (sendMessage + startConversation 시그니처)
  |- lib/thesis/mock.ts 수정 (entry별 Mock Map — MOCK_NEWS_STEP_MAP + MOCK_FREE_STEP_MAP + MOCK_FREE_CONFIRM_STEP)
  |- components/thesis/builder/ChatBubble.tsx
  |- components/thesis/builder/OptionButton.tsx (useLongPress + onShowExplanation + Info 아이콘)
  |- components/thesis/builder/PremiseCard.tsx (PreviewPremise + category 뱃지)
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
    · toEntrySource() 검증 + 'free_input' 기본값
    · entry별 Mock Map (MOCK_NEWS_STEP_MAP / MOCK_FREE_STEP_MAP) 분기
    · saveConvId/clearConvId 영속성
    · showError() + __retry__ 재시도
    · state.preview + PremiseCard 렌더링
    · onShowExplanation prop

Phase E (Phase D 의존):
  |- tsc --noEmit + npm run build 검증
  |- 브라우저 Mock 모드 테스트 (single/multi 전환, preview, 에러 재시도)
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
| `/thesis/new?entry=free_input` | 텍스트 입력 UI 표시 |
| `/thesis/new?entry=news` | 방향 선택 버튼 3개 표시 (single) |
| `/thesis/new?entry=free_text` | `toEntrySource()` → `'free_input'`으로 보정 |
| `/thesis/new` (entry 없음) | `'free_input'` 기본값 |
| free_input step 1 | TextInput 표시, 버튼 없음, 전송 버튼 비활성화 |
| free_input step 1→2 | 텍스트 전송 → single 버튼 3개 (confirm/modify/add_premise) |
| free_input step 2→3 | confirm → multi-select (전제 추가) |
| step 1→2 전환 | single → **multi** 전환, 체크박스 UI 표시 |
| step 2→3 전환 | multi → **single** 전환, 체크박스 사라짐 |
| step 5 (preview) | PremiseCard 렌더링 + category 뱃지 (심리/매크로) |
| 대화 완료 (step 6) | 3개 CTA (Primary/Secondary/Text link) |
| Mock 완료 후 "좋아, 일단 달아줘" 클릭 | `/thesis`로 이동 (Mock에서는 `/thesis/[id]/indicators` 404 예상) |
| 콘솔 API 에러 | 0건 (Mock 모드) |

### 5.3 UI 검증

| 시나리오 | 기대 동작 |
|---------|----------|
| 진행률 바 | step 변경 시 부드럽게 채워짐 |
| 스크롤 | 새 메시지 추가 시 자동 최하단 스크롤 |
| 모바일 롱프레스 (500ms) | 바텀시트 열림 + 설명 텍스트 |
| 모바일 빠른 탭 (< 500ms) | 클릭 정상 동작 (롱프레스 오작동 없음) |
| 데스크톱 Info 아이콘 클릭 | 바텀시트 열림 (롱프레스 없이) |
| 바텀시트 오버레이 클릭 | 시트 닫힘 (즉시, 애니메이션 없음 — 열기만 slideUp) |
| ESC 키 | 바텀시트 닫힘 |
| ChatBubble bounce dots | `[animation-delay:*ms]` JIT 클래스 정상 동작 확인 |
| 텍스트 입력 Enter | 전송 (Shift+Enter는 줄바꿈) |
| 빈 텍스트 전송 버튼 | 비활성화 (회색) |
| 에러 발생 시 | "연결에 문제가 생겼어요" + **재시도 버튼** |
| 재시도 버튼 클릭 | 에러 메시지 제거 + 대화 재시작 |

### 5.4 접근성 검증

| 항목 | 기대 |
|------|------|
| 터치 타겟 | 모든 버튼 min-h-[52px] 이상 |
| 삭제 버튼 | aria-label="근거 삭제" |
| Info 아이콘 | aria-label="{label} 설명 보기" |
| 키보드 | ESC로 바텀시트 닫기 |
| 다크 테마 | bg-white, text-black 0개 |
| 반응형 | 모바일: "꾹 누르면 설명" / 데스크톱: Info 아이콘 |

### 5.5 영속성 검증 (v2 추가)

| 시나리오 | 기대 동작 |
|---------|----------|
| 대화 시작 시 | `sessionStorage`에 conv_id 저장 |
| 대화 완료 시 | `sessionStorage`에서 conv_id 삭제 |
| 페이지 언마운트 시 | conv_id 유지 (cleanup 삭제 안 함 — StrictMode 안전). 다음 진입 시 덮어씀 |

---

## 6. 리스크 및 완화

| # | 리스크 | 심각도 | 완화 |
|---|--------|--------|------|
| 1 | sendMessage 시그니처 변경 (기존 호출부 파손) | 낮음 | PR-1~2에서 sendMessage 미사용. 첫 사용처가 이 PR |
| 2 | ConversationResponse.conversation_state 타입 변경 | 낮음 | PR-1~2에서 이 필드 미참조 |
| 3 | sonner 의존성 추가 | 낮음 | 4KB, zero-config, 다크테마 기본 |
| 4 | Mock step Map이 백엔드 실제 흐름과 다를 수 있음 | 중간 | v2: step별 selection_mode 명시로 전환 로직 검증 가능 |
| 5 | iOS Safari 키보드로 하단 영역 가림 | 중간 | `100dvh` 사용 + `env(safe-area-inset-top)` |
| 7 | animate-slideUp 미정의 시 바텀시트 깨짐 | 낮음 | v2: globals.css 수정을 파일 목록 [16]에 명시 |
| 8 | Gemini 호출 지연 (2~5초, step 1 free_input) | 중간 | ChatBubble 로딩 dots 이미 표시 + v2 에러 재시도 버튼 |
| 9 | entry_source 오타로 400 에러 | 낮음 | v2: `toEntrySource()` 검증 함수 + `EntrySource` 타입 |
| 10 | whitespace-pre-line 과도한 여백 | 낮음 | 백엔드 message에 연속 `\n\n\n`이 오면 과도한 여백. 필요시 정규화: `msg.replace(/\n{3,}/g, '\n\n')` |

---

## 7. 기술 부채

| 부채 | 영향 | 해소 시점 |
|------|------|----------|
| Mock 대화 흐름 하드코딩 | 백엔드 연동 후 제거 필요 | 백엔드 PR-3 연동 시 |
| ~~sessionStorage 미사용~~ | ~~새로고침 시 대화 초기화~~ | **v2 해결**: conv_id 영속성 추가 |
| step 롤백 (뒤로가기) 미지원 | 대화 중 이전 선택 수정 불가 | 백엔드 step rollback API 추가 시 |
| ~~PremiseCard 프론트 전용~~ | ~~백엔드 preview에서 전제 목록 제공 시 활용~~ | **v2 해결**: preview 단계 렌더링 추가 |
| BottomSheet 닫기 애니메이션 없음 | 열기: slideUp 0.3s, 닫기: 즉시 사라짐 (opacity transition 미구현) | 기술 부채로 유지. Phase 2에서 exit animation 추가 |
| 바텀시트 드래그 닫기 미구현 | 오버레이 클릭/ESC만 닫기 | Phase 2에서 touch gesture 추가 |
| Toast (sonner) thesis 전용 | 다른 페이지는 여전히 toast 없음 | 글로벌 layout에 Toaster 이동 시 |
| `useLongPress` EOD 통합 미완 | SignalCard 인라인 로직과 중복 | EOD 리팩토링 시 SignalCard도 `useLongPress` 적용 |
| conv_id 복원(resume) 미구현 | sessionStorage에 저장만 함. `loadConvId` 제거(H1). 복원은 백엔드 API 필요 | 백엔드 conversation resume API 추가 시 |

---

## 8. 후속 PR 연결

| 이 PR에서 만든 것 | 사용하는 PR |
|------------------|------------|
| `useLongPress` 훅 | EOD SignalCard 리팩토링, FE-PR-6 마감 선택지 |
| ChatBubble | FE-PR-6 가설 마감 복기에서 재사용 |
| OptionButton | FE-PR-6 마감 선택지에서 재사용 |
| PremiseCard | FE-PR-5 대시보드 전제 표시에서 재사용 |
| BottomSheet | FE-PR-4 지표 추가 시트, FE-PR-5 지표 상세 시트에서 재사용 |
| TextInput | FE-PR-6 마감 소감 입력에서 재사용 |
| ProgressBar | FE-PR-3 전용 (재사용 없음) |
| conversation.ts | FE-PR-6 마감 대화에서 유사 패턴 참고 가능 (BuilderState, applyResponse 구조) |
| sonner Toast | FE-PR-4~6에서 동일 패턴 사용 |
| `EntrySource` 타입 | 이후 EntryPointGrid, 대화 관련 코드에서 사용 |
| `ConversationState` 타입 | 이후 모든 대화 관련 코드에서 사용 |
| api.ts sendMessage 수정 | 이후 대화 API 호출 시 정확한 시그니처 |

---

## 9. Claude Code 실행 프롬프트

```
FE-PR-3 구현 계획서(docs/thesis_control/thesis_control_phase1_frontend_FE_PR_3.md) v3를 읽고,
Thesis Control 대화형 빌더를 구현해줘.

─────────────────────────────────────────────
[구현 순서]
─────────────────────────────────────────────

1단계: 의존성 + 타입 + 훅
  - npm install sonner
  - lib/thesis/types.ts: EntrySource union, ConversationState, PreviewPremise, PreviewIndicator, ThesisPreview, ConversationResponse 확장
  - lib/thesis/conversation.ts: BuilderState(+messageCounter, lastRequest), applyResponse, generateMessageId, selectionToLabel, saveConvId/clearConvId (loadConvId 없음)
  - lib/thesis/api.ts: sendMessage({ conversation_state, user_input }), startConversation({ entry_source: EntrySource })
  - lib/thesis/mock.ts: entry별 Mock Map (MOCK_NEWS_STEP_MAP, MOCK_FREE_STEP_MAP) — news step 2 multi, free_input step 2 single(confirm/modify/add_premise)
  - hooks/useLongPress.ts: longPressTriggered 플래그 기반 커스텀 훅

2단계: 빌더 컴포넌트 (7개, 병렬 생성)
  - components/thesis/builder/ChatBubble.tsx
  - components/thesis/builder/OptionButton.tsx (useLongPress 훅 + onShowExplanation + 데스크톱 Info 아이콘)
  - components/thesis/builder/PremiseCard.tsx (PreviewPremise 타입 + category 뱃지 8종 + DEFAULT_CATEGORY)
  - components/thesis/builder/MultiSelectFooter.tsx
  - components/thesis/builder/TextInput.tsx
  - components/thesis/builder/BottomSheet.tsx (CSS animation, Framer Motion 미사용)
  - components/thesis/builder/ProgressBar.tsx
  ★ 모든 컴포넌트 파일은 상단에 완전한 import 문 포함

3단계: 글로벌 설정
  - globals.css: slideUp 키프레임 추가
  - app/thesis/layout.tsx: <Toaster /> 추가
  - components/thesis/list/EntryPointGrid.tsx: showTemporaryToast → sonner toast 교체

4단계: 페이지 교체
  - app/thesis/new/page.tsx: 전면 교체
    · toEntrySource() 검증 함수 — 'free_input' 기본값 (백엔드 ALLOWED_ENTRY_SOURCES 일치)
    · entry별 Mock Map 선택 (MOCK_NEWS_STEP_MAP / MOCK_FREE_STEP_MAP)
    · saveConvId/clearConvId — sessionStorage 영속성
    · showError() + __retry__ 버튼 — 에러 재시도
    · state.preview + PremiseCard — preview 단계 렌더링
    · onShowExplanation — 모바일 롱프레스 + 데스크톱 Info 아이콘
    · handleComplete → auto/manual/later 네비게이션 + clearConvId
    · 스크롤 자동 최하단 (useEffect + scrollRef)

─────────────────────────────────────────────
[핵심 주의사항 (v3)]
─────────────────────────────────────────────
- 다크 테마 전용. bg-white, text-black 절대 사용하지 않음.
- sendMessage의 시그니처: { conversation_state, user_input } (백엔드 일치).
- startConversation의 entry_source: EntrySource 타입 (string 아님).
- entry_source 기본값: 'free_input' (절대 'free_text' 아님 — 백엔드 400 에러).
- Mock 데이터에 Date.now() 사용 금지 (hydration 불일치 버그 #24).
- Mock은 entry_source별 분리: MOCK_NEWS_STEP_MAP (news), MOCK_FREE_STEP_MAP (free_input). free_input step 2는 confirm/modify/add_premise (single).
- selection_mode='multi' 시 하단 [선택 완료] 버튼 필수.
- 완료 분기 3개 CTA: Primary(bg-blue-600) + Secondary(border) + Text link(text-gray-500).
- BottomSheet는 CSS transform + transition (Framer Motion 의존성 추가하지 않음).
- 롱프레스: useLongPress 훅 사용 (인라인 timerRef 금지). longPressTriggered 플래그 필수.
- 데스크톱 접근성: OptionButton에 Info 아이콘 (sm:flex), 모바일에서는 "꾹 누르면 설명" (sm:hidden).
- 에러 시 "연결에 문제가 생겼어요" AI 말풍선 + 재시도 버튼 (__retry__). alert/modal 아님.
- applyResponse에 userMessage 파라미터 없음. 사용자 메시지는 page.tsx에서 직접 추가.
- preview 단계: ThesisPreview.premises는 {content, category} 구조체. PremiseCard로 렌더링.
- conv_id: startConversation 성공 시 sessionStorage 저장, 완료 시 삭제. useEffect cleanup에서는 삭제 안 함 (StrictMode 방지).
- EntryPointGrid의 showTemporaryToast 함수 + 주석 전체 삭제 후 sonner 교체.
- ⚠️ (H4) setTimeout/비동기 콜백 안에서 state.step 직접 참조 금지. 반드시 setState(s => { ... s.step ... }) 함수형 업데이트 사용. (stale closure)
- ⚠️ (H5) 메시지 id에 step 기반 사용 금지. generateMessageId(state, prefix) 또는 messageCounter 기반으로 생성. (modify 분기 충돌)
- ⚠️ (H6) conversationState가 null이면 activeButtons 비움. 에러 재시도 UI는 `isErrorMessage` 조건으로 별도 분기 (activeButtons 밖).
- sendResponse에서 API 호출 직전에 lastRequest 저장. __retry__ 핸들러에서 lastRequest 있으면 동일 요청 재시도, 없으면 startConversation.
- page.tsx sendResponse Mock 분기에서 entry에 따라 올바른 Map 선택 (MOCK_NEWS_STEP_MAP / MOCK_FREE_STEP_MAP).
- 구현 후 tsc --noEmit + npm run build 검증 필수.
```
