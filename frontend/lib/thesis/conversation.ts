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

// ── 메시지 id 생성 헬퍼 ──
export function generateMessageId(state: BuilderState, prefix: 'ai' | 'user' | 'error'): string {
  return `${prefix}-${state.messageCounter}`
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
    lastRequest: null,
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
