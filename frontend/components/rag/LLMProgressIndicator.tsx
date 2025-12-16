'use client'

import { useEffect, useState } from 'react'
import { Loader2 } from 'lucide-react'

interface LLMProgressIndicatorProps {
  currentPhase: string
  isStreaming: boolean
}

const PHASE_TEXT: Record<string, string> = {
  preparing: '준비 중...',
  context_ready: '컨텍스트 로딩...',
  analyzing: '분석 중...',
  streaming: '답변 생성 중...',
}

export function LLMProgressIndicator({ currentPhase, isStreaming }: LLMProgressIndicatorProps) {
  const [elapsedSeconds, setElapsedSeconds] = useState(0)

  useEffect(() => {
    if (!isStreaming) {
      setElapsedSeconds(0)
      return
    }

    const interval = setInterval(() => {
      setElapsedSeconds((prev) => prev + 0.1)
    }, 100)

    return () => clearInterval(interval)
  }, [isStreaming])

  if (!isStreaming) return null

  const getTimeColor = () => {
    if (elapsedSeconds < 5) return 'text-slate-400'
    if (elapsedSeconds < 10) return 'text-orange-400'
    return 'text-red-400'
  }

  const phaseText = PHASE_TEXT[currentPhase] || '처리 중...'

  return (
    <div className="px-4 py-2 border-b border-slate-700 bg-slate-800/50">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Loader2 className="h-3 w-3 animate-spin text-blue-400" />
          <span className="text-xs text-slate-300">
            AI가 분석 중이에요 - {phaseText}
          </span>
        </div>
        <span className={`text-xs font-mono ${getTimeColor()}`}>
          {elapsedSeconds.toFixed(1)}s
        </span>
      </div>
    </div>
  )
}
