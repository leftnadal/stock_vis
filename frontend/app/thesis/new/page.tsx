'use client'

import { useState, useEffect, useRef, Suspense } from 'react'
import { useSearchParams, useRouter } from 'next/navigation'
import { ArrowLeft } from 'lucide-react'
import Link from 'next/link'
import { thesisApi } from '@/lib/thesis/api'
import {
  USE_MOCK, MOCK_CONVERSATION_START_NEWS,
  MOCK_CONVERSATION_START_FREE, MOCK_NEWS_STEP_MAP, MOCK_FREE_STEP_MAP,
  MOCK_CONVERSATION_DONE,
  MOCK_LLM_START, MOCK_LLM_STEP_MAP,
} from '@/lib/thesis/mock'
import { ENTRY_SOURCES, type EntrySource, type ConversationButton } from '@/lib/thesis/types'
import { PresetSelector } from '@/components/thesis/PresetSelector'
import { IndicatorCard } from '@/components/thesis/IndicatorCard'
import {
  type BuilderState, INITIAL_BUILDER_STATE, applyResponse, selectionToLabel,
  generateMessageId, saveConvId, clearConvId,
} from '@/lib/thesis/conversation'
import { ChatBubble } from '@/components/thesis/builder/ChatBubble'
import { OptionButton } from '@/components/thesis/builder/OptionButton'
import { PremiseCard } from '@/components/thesis/builder/PremiseCard'
import { MultiSelectFooter } from '@/components/thesis/builder/MultiSelectFooter'
import { TextInput } from '@/components/thesis/builder/TextInput'
import { BottomSheet } from '@/components/thesis/common/BottomSheet'
import { ProgressBar } from '@/components/thesis/builder/ProgressBar'

function toEntrySource(value: string | null): EntrySource {
  if (value && (ENTRY_SOURCES as readonly string[]).includes(value)) return value as EntrySource
  return 'free_input'
}

export default function ThesisNewPage() {
  return (
    <Suspense fallback={
      <div className="flex flex-col h-[calc(100dvh-env(safe-area-inset-top))] bg-gray-950">
        <div className="flex items-center gap-3 px-4 py-3 border-b border-gray-800">
          <div className="p-1 text-gray-400"><ArrowLeft size={20} /></div>
          <h1 className="text-white text-base font-medium flex-1">가설 세우기</h1>
        </div>
        <div className="flex-1 flex items-center justify-center">
          <div className="flex gap-1.5">
            <span className="w-1.5 h-1.5 rounded-full bg-gray-500 animate-bounce [animation-delay:0ms]" />
            <span className="w-1.5 h-1.5 rounded-full bg-gray-500 animate-bounce [animation-delay:200ms]" />
            <span className="w-1.5 h-1.5 rounded-full bg-gray-500 animate-bounce [animation-delay:400ms]" />
          </div>
        </div>
      </div>
    }>
      <ThesisBuilder />
    </Suspense>
  )
}

function ThesisBuilder() {
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
  useEffect(() => {
    startConversation(entry)
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  async function startConversation(entrySource: EntrySource) {
    setState(s => ({ ...s, isLoading: true }))

    if (USE_MOCK) {
      // LLM mock이 활성화된 경우 LLM 시작 사용
      const mockResponse = MOCK_LLM_START.conversation_state.mode === 'llm'
        ? MOCK_LLM_START
        : entrySource === 'news'
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

  // ── 에러 메시지 ──
  function showError() {
    setState(s => ({
      ...s,
      isLoading: false,
      messages: [...s.messages, {
        id: `error-${s.messageCounter}`,
        role: 'ai' as const,
        content: '연결에 문제가 생겼어요. 아래 버튼으로 다시 시도할 수 있어요.',
      }],
      messageCounter: s.messageCounter + 1,
    }))
  }

  // ── 응답 전송 ──
  async function sendResponse(input: string | string[], label: string): Promise<boolean> {
    if (!state.conversationState) return false

    setState(s => ({
      ...s,
      isLoading: true,
      messages: [...s.messages, {
        id: generateMessageId(s, 'user'),
        role: 'user',
        content: label,
      }],
      messageCounter: s.messageCounter + 1,
      lastRequest: {
        conversation_state: s.conversationState!,
        user_input: input,
        label,
      },
    }))

    if (USE_MOCK) {
      setTimeout(() => {
        setState(s => {
          const nextStep = s.step + 1
          // LLM 모드 mock
          if (s.mode === 'llm') {
            const mockNext = MOCK_LLM_STEP_MAP[nextStep] ?? MOCK_CONVERSATION_DONE
            return applyResponse(s, mockNext)
          }
          // wizard 모드 mock
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
      showError()
      return false
    }
  }

  // ── 단일 선택 핸들러 ──
  function handleSingleSelect(button: ConversationButton) {
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

  // ── 멀티 선택 완료 ──
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

  // ── 프리셋 선택 (LLM 모드) ──
  function handlePresetSelect(presetId: string) {
    sendResponse(presetId, presetId)
  }

  // ── 완료 후 네비게이션 ──
  function handleComplete(action: string) {
    clearConvId()
    const thesisId = state.thesisId || state.createdThesis?.thesis_id
    if (USE_MOCK || !thesisId) {
      router.push('/thesis')
      return
    }
    switch (action) {
      case 'auto':
        router.push(`/thesis/${thesisId}/indicators?auto=true`)
        break
      case 'manual':
        router.push(`/thesis/${thesisId}/indicators`)
        break
      case 'dashboard':
        router.push(state.createdThesis?.dashboard_url ?? `/thesis/${thesisId}`)
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

  // ── 마지막 메시지 분석 ──
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
      {/* 상단 헤더 */}
      <div className="flex items-center gap-3 px-4 py-3 border-b border-gray-800">
        <Link href="/thesis" className="p-1 text-gray-400 hover:text-white">
          <ArrowLeft size={20} />
        </Link>
        <h1 className="text-white text-base font-medium flex-1">가설 세우기</h1>
      </div>

      {/* 진행률 바 */}
      {state.step > 0 && (
        <ProgressBar step={state.step} totalSteps={state.totalSteps} />
      )}

      {/* 메시지 스크롤 영역 */}
      <div ref={scrollRef} className="flex-1 overflow-y-auto px-4 pt-4 pb-4">
        {state.messages.map((msg) => (
          <ChatBubble key={msg.id} role={msg.role}>
            {msg.content}
          </ChatBubble>
        ))}

        {/* Preview 카드 렌더링 (wizard 모드) */}
        {state.preview && (
          <div className="mb-3 space-y-2">
            <p className="text-xs text-gray-500 px-1">근거 ({state.preview.premises.length}개)</p>
            {state.preview.premises.map((premise, i) => (
              <PremiseCard key={i} premise={premise} />
            ))}
          </div>
        )}

        {/* LLM 모드: 지표 추천 카드 */}
        {state.indicatorRecommendations.length > 0 && state.phase === 'preset' && (
          <div className="mb-3 space-y-2">
            <p className="text-xs text-gray-500 px-1">
              AI 추천 지표 ({state.indicatorRecommendations.length}개)
            </p>
            {state.indicatorRecommendations.map((rec, i) => (
              <IndicatorCard key={i} recommendation={rec} />
            ))}
          </div>
        )}

        {/* AI 로딩 중 */}
        {state.isLoading && <ChatBubble role="ai" isLoading />}
      </div>

      {/* 하단 고정 영역 */}
      <div className="flex-shrink-0">
        {/* LLM 모드: 프리셋 선택 */}
        {state.mode === 'llm' && state.phase === 'preset' && !state.isLoading && !state.isDone && (
          <PresetSelector
            onSelect={handlePresetSelect}
            disabled={state.isLoading}
          />
        )}

        {/* 버튼 선택지 (preset이 아닌 경우에만) */}
        {activeButtons.length > 0 && !state.isDone
          && !(state.mode === 'llm' && state.phase === 'preset') && (
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

        {/* 에러 재시도 */}
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

        {/* 완료 분기 — 프론트 하드코딩 CTA */}
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

      {/* 바텀시트 (근거 설명) */}
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
