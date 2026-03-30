import type {
  ConversationState, ConversationResponse, ConversationButton,
  ThesisPreview, BuilderPhase, LLMIndicatorRecommendation,
  ThesisSuggestion, SuggestResponse,
} from './types'

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

// ── 마지막 요청 저장 (에러 시 재시도용) ──
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
  messageCounter: number
  lastRequest: LastRequest | null
  // LLM mode extensions
  mode: 'llm' | 'wizard'
  phase: BuilderPhase | null
  confidence: 'high' | 'medium' | 'low' | null
  indicatorRecommendations: LLMIndicatorRecommendation[]
  createdThesis: { thesis_id: string; title: string; dashboard_url: string } | null
  // Suggestion mode
  suggestions: ThesisSuggestion[]
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
  mode: 'wizard',
  phase: null,
  confidence: null,
  indicatorRecommendations: [],
  createdThesis: null,
  suggestions: [],
}

// ── 메시지 id 생성 헬퍼 ──
export function generateMessageId(state: BuilderState, prefix: 'ai' | 'user' | 'error'): string {
  return `${prefix}-${state.messageCounter}`
}

// ── LLM phase → step 매핑 ──
const PHASE_STEP_MAP: Record<string, number> = {
  suggestions: 1,
  proposal: 1,
  preset: 2,
  confirm: 3,
  complete: 3,
  fallback: 1,
}

// ── API 응답 → AI 메시지 추가 ──
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

  // LLM 모드 감지
  const isLLM = response.conversation_state?.mode === 'llm' || !!response.phase
  const phase = response.phase ?? state.phase

  return {
    ...state,
    messages: newMessages,
    conversationState: response.conversation_state,
    step: isLLM ? (PHASE_STEP_MAP[phase ?? ''] ?? 1) : response.step,
    totalSteps: isLLM ? 3 : response.total_steps,
    isLoading: false,
    thesisId: response.thesis_id ?? response.created_thesis?.thesis_id ?? state.thesisId,
    counterThesisId: response.counter_thesis_id ?? state.counterThesisId,
    isDone: response.done ?? response.is_complete ?? false,
    preview: response.preview ?? state.preview,
    messageCounter: state.messageCounter + 1,
    lastRequest: null,
    // LLM extensions
    mode: isLLM ? 'llm' : state.mode,
    phase: phase ?? null,
    confidence: response.confidence ?? state.confidence,
    indicatorRecommendations: response.indicator_recommendations ?? state.indicatorRecommendations,
    createdThesis: response.created_thesis ?? state.createdThesis,
  }
}

// ── 사용자 선택을 라벨로 변환 ──
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
const CONV_STORAGE_KEY = 'thesis_builder_conv_id'

export function saveConvId(convId: string): void {
  try { sessionStorage.setItem(CONV_STORAGE_KEY, convId) } catch { /* SSR */ }
}

export function clearConvId(): void {
  try { sessionStorage.removeItem(CONV_STORAGE_KEY) } catch { /* SSR */ }
}

// ── Suggest 응답 처리 ──
export function applySuggestResponse(
  state: BuilderState,
  response: SuggestResponse,
): BuilderState {
  if (response.entry_mode === 'fallback_start') {
    // fallback → 기존 start 응답 처리
    return applyResponse(state, response as unknown as ConversationResponse)
  }

  // suggestions 모드
  return {
    ...state,
    conversationState: response.conversation_state,
    suggestions: response.suggestions,
    phase: 'suggestions',
    mode: 'llm',
    step: 1,
    totalSteps: 3,
    isLoading: false,
    messageCounter: state.messageCounter + 1,
  }
}
