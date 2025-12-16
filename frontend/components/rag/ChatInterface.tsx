'use client'

import { useState, useRef, useEffect } from 'react'
import { Send, Loader2, AlertCircle } from 'lucide-react'
import { MessageList } from './MessageList'
import { SuggestionChips } from './SuggestionChips'
import { BasketActionCard } from './BasketActionCard'
import { LLMProgressIndicator } from './LLMProgressIndicator'
import { AutoMessage } from './AutoMessage'
import type { Message, Suggestion, BasketAction, Basket } from '@/types/rag'
import { DATA_TYPE_INFO } from '@/types/rag'

interface ChatInterfaceProps {
  sessionId: number | null
  messages: Message[]
  isStreaming: boolean
  streamedContent: string
  suggestions: Suggestion[]
  basketActions: BasketAction[]
  basket: Basket | null
  error: Error | null
  currentPhase: string
  onSendMessage: (message: string) => void
  onAddToBasket: (symbol: string, dataTypes: string[]) => Promise<void>
  onContinueChat?: (message: string) => void
}

export function ChatInterface({
  sessionId,
  messages,
  isStreaming,
  streamedContent,
  suggestions,
  basketActions,
  basket,
  error,
  currentPhase,
  onSendMessage,
  onAddToBasket,
  onContinueChat,
}: ChatInterfaceProps) {
  const [input, setInput] = useState('')
  const textareaRef = useRef<HTMLTextAreaElement>(null)
  const [showAutoMessage, setShowAutoMessage] = useState(false)
  const [addedDataTypes, setAddedDataTypes] = useState<Array<{ type: string; label: string; units: number }>>([])

  // 자동 높이 조절
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto'
      textareaRef.current.style.height = `${textareaRef.current.scrollHeight}px`
    }
  }, [input])

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!input.trim() || isStreaming || !sessionId) return

    onSendMessage(input.trim())
    setInput('')

    // 높이 초기화
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto'
    }
  }

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSubmit(e)
    }
  }

  const handleSuggestionClick = (symbol: string, reason: string) => {
    const message = `${symbol} 종목에 대해 분석해주세요. (${reason})`
    onSendMessage(message)
  }

  const handleAddToBasket = async (symbol: string, dataTypes: string[]) => {
    // 원래 onAddToBasket 호출
    await onAddToBasket(symbol, dataTypes)

    // 추가된 데이터 타입 정보 저장
    const dataInfo = dataTypes.map(type => ({
      type,
      label: DATA_TYPE_INFO[type]?.label || type,
      units: DATA_TYPE_INFO[type]?.units || 0,
    }))
    setAddedDataTypes(dataInfo)

    // 자동 메시지 표시
    setShowAutoMessage(true)

    // 100ms 후 자동으로 메시지 전송
    setTimeout(() => {
      if (onContinueChat) {
        onContinueChat('방금 추가한 데이터로 분석을 계속해주세요')
      }
      // 메시지 전송 후 자동 메시지 숨김
      setTimeout(() => {
        setShowAutoMessage(false)
      }, 500)
    }, 100)
  }

  return (
    <div className="flex h-full flex-col">
      {/* 메시지 리스트 */}
      <MessageList
        messages={messages}
        streamedContent={streamedContent}
        isStreaming={isStreaming}
      />

      {/* LLM 진행 단계 표시 */}
      <LLMProgressIndicator currentPhase={currentPhase} isStreaming={isStreaming} />

      {/* 자동 메시지 */}
      {showAutoMessage && <AutoMessage addedDataTypes={addedDataTypes} />}

      {/* 제안 칩 */}
      {suggestions.length > 0 && !isStreaming && (
        <SuggestionChips
          suggestions={suggestions}
          onSelect={handleSuggestionClick}
          disabled={!sessionId}
        />
      )}

      {/* 바구니 액션 카드 */}
      {basketActions.length > 0 && !isStreaming && (
        <div className="px-4 space-y-2">
          <h3 className="text-sm font-semibold text-[#C9D1D9] mb-2">
            추천 데이터 추가
          </h3>
          {basketActions.map((action, idx) => (
            <BasketActionCard
              key={`${action.symbol}-${idx}`}
              action={action}
              remainingUnits={basket?.remaining_units || 0}
              onAdd={handleAddToBasket}
              onContinueChat={onContinueChat}
            />
          ))}
        </div>
      )}

      {/* 에러 표시 */}
      {error && (
        <div className="mx-4 mb-2 rounded-lg border border-red-200 bg-red-50 p-3 dark:border-red-800 dark:bg-red-950/50">
          <div className="flex items-start gap-2">
            <AlertCircle className="h-4 w-4 flex-shrink-0 text-red-600 dark:text-red-400" />
            <div className="flex-1">
              <p className="text-sm font-medium text-red-900 dark:text-red-200">
                오류가 발생했습니다
              </p>
              <p className="mt-1 text-xs text-red-700 dark:text-red-300">
                {error.message}
              </p>
            </div>
          </div>
        </div>
      )}

      {/* 입력창 */}
      <div className="border-t border-slate-200 bg-white p-4 dark:border-slate-700 dark:bg-slate-900">
        {/* 입력 폼 */}
        <form onSubmit={handleSubmit} className="flex gap-2">
          <div className="relative flex-1">
            <textarea
              ref={textareaRef}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder={
                sessionId
                  ? '질문을 입력하세요... (Shift + Enter로 줄바꿈)'
                  : '먼저 세션을 생성해주세요'
              }
              disabled={isStreaming || !sessionId}
              rows={1}
              className="w-full resize-none rounded-lg border border-slate-300 bg-white px-4 py-3 pr-12 text-sm text-slate-900 placeholder-slate-400 focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-500/20 disabled:cursor-not-allowed disabled:bg-slate-50 disabled:text-slate-500 dark:border-slate-600 dark:bg-slate-800 dark:text-slate-100 dark:placeholder-slate-500 dark:focus:border-blue-400 dark:disabled:bg-slate-900"
              style={{ maxHeight: '200px' }}
            />

            {/* 글자 수 */}
            {input.length > 0 && (
              <span className="absolute bottom-2 right-2 text-xs text-slate-400">
                {input.length}
              </span>
            )}
          </div>

          <button
            type="submit"
            disabled={!input.trim() || isStreaming || !sessionId}
            className="flex h-[52px] w-[52px] flex-shrink-0 items-center justify-center rounded-lg bg-blue-600 text-white transition-all hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500/50 disabled:cursor-not-allowed disabled:bg-slate-300 dark:bg-blue-500 dark:hover:bg-blue-600 dark:disabled:bg-slate-700"
            aria-label="전송"
          >
            {isStreaming ? (
              <Loader2 className="h-5 w-5 animate-spin" />
            ) : (
              <Send className="h-5 w-5" />
            )}
          </button>
        </form>

        {/* 힌트 */}
        <p className="mt-2 text-xs text-slate-500 dark:text-slate-400">
          바구니에 데이터를 추가하면 더 정확한 분석을 받을 수 있습니다.
        </p>
      </div>
    </div>
  )
}
