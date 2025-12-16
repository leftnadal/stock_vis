'use client'

import { useState, useEffect } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { ShoppingBasket, Plus, Coins, Activity } from 'lucide-react'
import { ChatInterface } from '@/components/rag/ChatInterface'
import { DataBasket } from '@/components/rag/DataBasket'
import { TokenUsageDisplay } from '@/components/rag/TokenUsageDisplay'
import { MonitoringDashboard } from '@/components/rag/MonitoringDashboard'
import { basketService, sessionService } from '@/services/ragService'
import { useSSEStream } from '@/hooks/useSSEStream'
import type { Basket, Message } from '@/types/rag'

const QUERY_KEYS = {
  baskets: ['baskets'] as const,
  basket: (id: number) => ['baskets', id] as const,
  sessions: ['sessions'] as const,
  session: (id: number) => ['sessions', id] as const,
  messages: (sessionId: number) => ['sessions', sessionId, 'messages'] as const,
}

export default function AIAnalysisPage() {
  const queryClient = useQueryClient()
  const [isBasketOpen, setIsBasketOpen] = useState(false)
  const [isTokenPanelOpen, setIsTokenPanelOpen] = useState(false)
  const [isMonitoringOpen, setIsMonitoringOpen] = useState(false)
  const [currentBasketId, setCurrentBasketId] = useState<number | null>(null)
  const [currentSessionId, setCurrentSessionId] = useState<number | null>(null)
  const [sessionUsage, setSessionUsage] = useState({ input_tokens: 0, output_tokens: 0 })

  // 바구니 목록 조회
  const { data: baskets } = useQuery({
    queryKey: QUERY_KEYS.baskets,
    queryFn: basketService.getList,
  })

  // 현재 바구니 상세 조회
  const { data: currentBasket } = useQuery({
    queryKey: QUERY_KEYS.basket(currentBasketId!),
    queryFn: () => basketService.getDetail(currentBasketId!),
    enabled: !!currentBasketId,
  })

  // 메시지 목록 조회
  const { data: messages = [] } = useQuery({
    queryKey: QUERY_KEYS.messages(currentSessionId!),
    queryFn: () => sessionService.getMessages(currentSessionId!),
    enabled: !!currentSessionId,
    refetchInterval: false, // SSE로 실시간 업데이트하므로 비활성화
  })

  // SSE 스트리밍
  const {
    isStreaming,
    streamedContent,
    suggestions,
    basketActions,
    basketCleared,
    error: streamError,
    currentPhase,
    usage: currentUsage,
    complexity,
    startStream,
  } = useSSEStream(currentSessionId!)

  // 토큰 사용량 누적
  useEffect(() => {
    if (currentUsage && !isStreaming) {
      setSessionUsage(prev => ({
        input_tokens: prev.input_tokens + currentUsage.input_tokens,
        output_tokens: prev.output_tokens + currentUsage.output_tokens,
      }))
    }
  }, [currentUsage, isStreaming])

  // 바구니가 비워졌을 때 바구니 쿼리 갱신
  useEffect(() => {
    if (basketCleared && currentBasketId) {
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.basket(currentBasketId) })
    }
  }, [basketCleared, currentBasketId, queryClient])

  // 바구니 생성 뮤테이션
  const createBasketMutation = useMutation({
    mutationFn: basketService.create,
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.baskets })
      setCurrentBasketId(data.id)
    },
  })

  // 세션 생성 뮤테이션
  const createSessionMutation = useMutation({
    mutationFn: sessionService.create,
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.sessions })
      setCurrentSessionId(data.id)
    },
  })

  // 아이템 제거 뮤테이션
  const removeItemMutation = useMutation({
    mutationFn: ({ basketId, itemId }: { basketId: number; itemId: number }) =>
      basketService.removeItem(basketId, itemId),
    onSuccess: () => {
      if (currentBasketId) {
        queryClient.invalidateQueries({ queryKey: QUERY_KEYS.basket(currentBasketId) })
      }
    },
  })

  // 바구니 비우기 뮤테이션
  const clearBasketMutation = useMutation({
    mutationFn: (basketId: number) => basketService.clear(basketId),
    onSuccess: () => {
      if (currentBasketId) {
        queryClient.invalidateQueries({ queryKey: QUERY_KEYS.basket(currentBasketId) })
      }
    },
  })

  // 초기 설정: 바구니와 세션 자동 생성
  useEffect(() => {
    const initializeSession = async () => {
      try {
        // 유효한 바구니가 있는지 확인
        const validBaskets = Array.isArray(baskets) ? baskets.filter(b => b && b.id) : []

        if (validBaskets.length === 0) {
          // 바구니가 없으면 생성
          const basket = await createBasketMutation.mutateAsync({
            name: '기본 바구니',
            description: 'AI 분석용 기본 바구니',
          })
          setCurrentBasketId(basket.id)

          // 세션 생성
          const session = await createSessionMutation.mutateAsync({
            basket: basket.id,
            title: `분석 세션 ${new Date().toLocaleString('ko-KR')}`,
          })
          setCurrentSessionId(session.id)
        } else {
          // 기존 바구니 사용
          const firstBasket = validBaskets[0]
          setCurrentBasketId(firstBasket.id)

          // 세션 생성
          const session = await createSessionMutation.mutateAsync({
            basket: firstBasket.id,
            title: `분석 세션 ${new Date().toLocaleString('ko-KR')}`,
          })
          setCurrentSessionId(session.id)
        }
      } catch (error) {
        console.error('Failed to initialize session:', error)
      }
    }

    if (!currentBasketId && baskets !== undefined) {
      initializeSession()
    }
  }, [baskets, currentBasketId])

  // 메시지 전송 핸들러
  const handleSendMessage = async (message: string) => {
    if (!currentSessionId) return

    // 낙관적 업데이트: 사용자 메시지 추가
    const tempUserMessage: Message = {
      id: Date.now(),
      session: currentSessionId,
      role: 'user',
      content: message,
      created_at: new Date().toISOString(),
    }

    queryClient.setQueryData<Message[]>(
      QUERY_KEYS.messages(currentSessionId),
      (old = []) => [...old, tempUserMessage]
    )

    // SSE 스트리밍 시작
    await startStream(message)

    // 스트리밍 완료 후 메시지 목록 갱신
    queryClient.invalidateQueries({ queryKey: QUERY_KEYS.messages(currentSessionId) })
  }

  // 아이템 제거 핸들러
  const handleRemoveItem = (itemId: number) => {
    if (!currentBasketId) return
    removeItemMutation.mutate({ basketId: currentBasketId, itemId })
  }

  // 바구니 비우기 핸들러
  const handleClearBasket = () => {
    if (!currentBasketId) return
    if (confirm('바구니의 모든 아이템을 삭제하시겠습니까?')) {
      clearBasketMutation.mutate(currentBasketId)
    }
  }

  // 바구니에 데이터 추가 핸들러
  const handleAddToBasket = async (symbol: string, dataTypes: string[]) => {
    if (!currentBasketId) {
      console.error('바구니가 선택되지 않았습니다.')
      return
    }

    try {
      const result = await basketService.addStockData(currentBasketId, symbol, dataTypes)
      console.log('Added to basket:', result)

      // 바구니 갱신
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.basket(currentBasketId) })
    } catch (error) {
      console.error('Failed to add to basket:', error)
      throw error // BasketActionCard에서 에러 처리
    }
  }

  // 자동 대화 계속 핸들러
  const handleContinueChat = async (message: string) => {
    if (!currentSessionId) return
    // 약간의 딜레이 후 메시지 전송 (바구니 갱신 대기)
    setTimeout(() => {
      handleSendMessage(message)
    }, 500)
  }

  return (
    <div className="relative flex h-screen flex-col bg-slate-50 dark:bg-slate-900">
      {/* 헤더 */}
      <header className="border-b border-slate-200 bg-white px-6 py-4 dark:border-slate-700 dark:bg-slate-800">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-slate-900 dark:text-slate-100">
              AI 투자 분석
            </h1>
            <p className="mt-1 text-sm text-slate-600 dark:text-slate-400">
              Claude AI 기반 실시간 투자 인사이트
            </p>
          </div>

          <div className="flex items-center gap-2">
            {/* 모니터링 버튼 */}
            <button
              onClick={() => setIsMonitoringOpen(!isMonitoringOpen)}
              className={`flex items-center gap-2 rounded-lg border px-4 py-2 text-sm font-medium transition-all ${
                isMonitoringOpen
                  ? 'border-blue-500 bg-blue-50 text-blue-700 dark:border-blue-400 dark:bg-blue-900/30 dark:text-blue-300'
                  : 'border-slate-300 bg-white text-slate-700 hover:bg-slate-50 dark:border-slate-600 dark:bg-slate-800 dark:text-slate-300 dark:hover:bg-slate-700'
              }`}
            >
              <Activity className="h-4 w-4" />
              <span className="hidden sm:inline">모니터링</span>
            </button>

            {/* 토큰 사용량 버튼 */}
            <button
              onClick={() => setIsTokenPanelOpen(!isTokenPanelOpen)}
              className="flex items-center gap-2 rounded-lg border border-slate-300 bg-white px-4 py-2 text-sm font-medium text-slate-700 transition-all hover:bg-slate-50 dark:border-slate-600 dark:bg-slate-800 dark:text-slate-300 dark:hover:bg-slate-700"
            >
              <Coins className="h-4 w-4" />
              <span className="hidden sm:inline">토큰</span>
              {sessionUsage.input_tokens + sessionUsage.output_tokens > 0 && (
                <span className="text-xs text-yellow-600 dark:text-yellow-400 font-mono">
                  {((sessionUsage.input_tokens + sessionUsage.output_tokens) / 1000).toFixed(1)}k
                </span>
              )}
            </button>

            {/* 바구니 버튼 */}
            <button
              onClick={() => setIsBasketOpen(true)}
              className="flex items-center gap-2 rounded-lg border border-slate-300 bg-white px-4 py-2 text-sm font-medium text-slate-700 transition-all hover:bg-slate-50 dark:border-slate-600 dark:bg-slate-800 dark:text-slate-300 dark:hover:bg-slate-700"
            >
              <ShoppingBasket className="h-4 w-4" />
              <span>바구니</span>
              {currentBasket && currentBasket.items.length > 0 && (
                <span className="flex h-5 w-5 items-center justify-center rounded-full bg-blue-600 text-xs text-white dark:bg-blue-500">
                  {currentBasket.items.length}
                </span>
              )}
            </button>
          </div>
        </div>
      </header>

      {/* 모니터링 대시보드 패널 */}
      {isMonitoringOpen && (
        <div className="absolute left-4 top-20 z-50 w-96">
          <MonitoringDashboard
            isOpen={isMonitoringOpen}
            onClose={() => setIsMonitoringOpen(false)}
          />
        </div>
      )}

      {/* 토큰 사용량 패널 */}
      {isTokenPanelOpen && (
        <div className="absolute right-4 top-20 z-50 w-80">
          <TokenUsageDisplay
            currentUsage={currentUsage}
            sessionUsage={sessionUsage}
            model="gemini-2.5-flash"
            complexity={complexity}
            onClose={() => setIsTokenPanelOpen(false)}
          />
        </div>
      )}

      {/* 메인 콘텐츠 */}
      <main className="flex-1 overflow-hidden">
        <div className="mx-auto h-full max-w-5xl">
          <div className="flex h-full flex-col rounded-lg border border-slate-200 bg-white shadow-sm dark:border-slate-700 dark:bg-slate-800">
            <ChatInterface
              sessionId={currentSessionId}
              messages={messages}
              isStreaming={isStreaming}
              streamedContent={streamedContent}
              suggestions={suggestions}
              basketActions={basketActions}
              basket={currentBasket || null}
              error={streamError}
              currentPhase={currentPhase}
              onSendMessage={handleSendMessage}
              onAddToBasket={handleAddToBasket}
              onContinueChat={handleContinueChat}
            />
          </div>
        </div>
      </main>

      {/* 데이터 바구니 패널 */}
      <DataBasket
        basket={currentBasket || null}
        isOpen={isBasketOpen}
        onClose={() => setIsBasketOpen(false)}
        onRemoveItem={handleRemoveItem}
        onClear={handleClearBasket}
      />
    </div>
  )
}
