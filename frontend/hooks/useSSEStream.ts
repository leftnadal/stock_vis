import { useState, useCallback, useRef } from 'react'
import { streamAnalysis } from '@/services/ragService'
import type { SSEEvent, CompleteData, Suggestion, BasketAction, CacheInfo } from '@/types/rag'

type ComplexityLevel = 'simple' | 'moderate' | 'complex'

interface UseSSEStreamReturn {
  isStreaming: boolean
  currentPhase: string
  streamedContent: string
  error: Error | null
  suggestions: Suggestion[]
  basketActions: BasketAction[]
  basketCleared: boolean
  usage: { input_tokens: number; output_tokens: number; cached?: boolean; cost_usd?: number } | null
  latencyMs: number | null
  cacheInfo: CacheInfo | null
  complexity: { level: ComplexityLevel; score: number } | null
  startStream: (message: string) => Promise<void>
  reset: () => void
}

export function useSSEStream(sessionId: number): UseSSEStreamReturn {
  const [isStreaming, setIsStreaming] = useState(false)
  const [currentPhase, setCurrentPhase] = useState<string>('')
  const [streamedContent, setStreamedContent] = useState('')
  const [error, setError] = useState<Error | null>(null)
  const [suggestions, setSuggestions] = useState<Suggestion[]>([])
  const [basketActions, setBasketActions] = useState<BasketAction[]>([])
  const [basketCleared, setBasketCleared] = useState(false)
  const [usage, setUsage] = useState<{ input_tokens: number; output_tokens: number; cached?: boolean; cost_usd?: number } | null>(null)
  const [latencyMs, setLatencyMs] = useState<number | null>(null)
  const [cacheInfo, setCacheInfo] = useState<CacheInfo | null>(null)
  const [complexity, setComplexity] = useState<{ level: ComplexityLevel; score: number } | null>(null)

  // 중복 호출 방지를 위한 ref
  const isStreamingRef = useRef(false)

  const startStream = useCallback(async (message: string) => {
    // 이미 스트리밍 중이면 무시
    if (isStreamingRef.current) {
      console.warn('Stream already in progress')
      return
    }

    isStreamingRef.current = true
    setIsStreaming(true)
    setStreamedContent('')
    setError(null)
    setSuggestions([])
    setBasketActions([])
    setBasketCleared(false)
    setUsage(null)
    setLatencyMs(null)
    setCacheInfo(null)
    setComplexity(null)

    try {
      await streamAnalysis(
        sessionId,
        message,
        (event: SSEEvent) => {
          setCurrentPhase(event.phase)

          switch (event.phase) {
            case 'cache_check':
              // 캐시 확인 중
              if (event.message) {
                console.log(`[cache_check] ${event.message}`)
              }
              break

            case 'cache_hit':
              // 캐시 히트! - 즉시 응답
              if (event.data) {
                const data: CompleteData = event.data
                setStreamedContent(data.content)
                setSuggestions(data.suggestions)
                setBasketActions(data.basket_actions || [])
                setUsage({
                  ...data.usage,
                  cached: true
                })
                setLatencyMs(data.latency_ms)
                // 캐시 정보 저장
                if (data.cache_info) {
                  setCacheInfo(data.cache_info)
                }
              }
              console.log('[cache_hit] 캐시된 응답 사용!')
              setIsStreaming(false)
              isStreamingRef.current = false
              break

            case 'preparing':
            case 'context_ready':
              // 준비 단계 - 메시지만 표시
              if (event.message) {
                console.log(`[${event.phase}] ${event.message}`)
              }
              break

            case 'analyzing':
              // 분석 시작 - 복잡도 정보 캡처
              if (event.message) {
                console.log(`[${event.phase}] ${event.message}`)
              }
              // 복잡도 정보가 있으면 저장
              if (event.complexity) {
                setComplexity({
                  level: event.complexity as ComplexityLevel,
                  score: event.complexity_score || 0.5
                })
                console.log(`[analyzing] complexity: ${event.complexity} (score: ${event.complexity_score})`)
              }
              break

            case 'streaming':
              // 청크 단위로 내용 추가
              if (event.chunk) {
                setStreamedContent(prev => prev + event.chunk)
              }
              break

            case 'complete':
              // 완료 - 최종 데이터 설정
              if (event.data) {
                const data: CompleteData = event.data
                setStreamedContent(data.content)
                setSuggestions(data.suggestions)
                setBasketActions(data.basket_actions || [])
                setUsage({
                  ...data.usage,
                  cached: false,
                  cost_usd: data.usage?.cost_usd
                })
                setLatencyMs(data.latency_ms)
                // 복잡도 정보 (complete 이벤트에서도 제공)
                if (data.complexity) {
                  setComplexity({
                    level: data.complexity as ComplexityLevel,
                    score: data.complexity_score || 0.5
                  })
                }
              }
              setIsStreaming(false)
              isStreamingRef.current = false
              break

            case 'error':
              // 에러 발생
              const errorMsg = event.error?.message || '분석 중 오류가 발생했습니다.'
              setError(new Error(errorMsg))
              setIsStreaming(false)
              isStreamingRef.current = false
              break

            case 'basket_cleared':
              // 바구니가 비워졌음
              setBasketCleared(true)
              console.log('[basket_cleared] 바구니가 비워졌습니다.')
              break
          }
        },
        (err: Error) => {
          console.error('Stream error:', err)
          setError(err)
          setIsStreaming(false)
          isStreamingRef.current = false
        }
      )
    } catch (err) {
      console.error('Failed to start stream:', err)
      setError(err as Error)
      setIsStreaming(false)
      isStreamingRef.current = false
    }
  }, [sessionId])

  const reset = useCallback(() => {
    setIsStreaming(false)
    setCurrentPhase('')
    setStreamedContent('')
    setError(null)
    setSuggestions([])
    setBasketActions([])
    setBasketCleared(false)
    setUsage(null)
    setLatencyMs(null)
    setCacheInfo(null)
    setComplexity(null)
    isStreamingRef.current = false
  }, [])

  return {
    isStreaming,
    currentPhase,
    streamedContent,
    error,
    suggestions,
    basketActions,
    basketCleared,
    usage,
    latencyMs,
    cacheInfo,
    complexity,
    startStream,
    reset,
  }
}
