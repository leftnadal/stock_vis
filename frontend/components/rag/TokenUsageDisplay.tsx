'use client'

import { X } from 'lucide-react'

// LLM API 가격 (2025.01 기준, per 1M tokens)
const PRICING = {
  'gemini-2.5-flash': {
    input: 0.15,    // $0.15/1M input tokens
    output: 0.60,   // $0.60/1M output tokens (without thinking)
    name: 'Gemini 2.5 Flash',
  },
  'gemini-2.5-flash-thinking': {
    input: 0.15,    // $0.15/1M input tokens
    output: 3.50,   // $3.50/1M output tokens (with thinking)
    name: 'Gemini 2.5 Flash (Thinking)',
  },
  'gemini-2.5-pro': {
    input: 1.25,    // $1.25/1M input tokens
    output: 10.00,  // $10/1M output tokens
    name: 'Gemini 2.5 Pro',
  },
  'claude-3-5-sonnet': {
    input: 3.00,    // $3/1M input tokens
    output: 15.00,  // $15/1M output tokens
    name: 'Claude 3.5 Sonnet',
  },
  'claude-3-5-haiku': {
    input: 0.80,    // $0.80/1M input tokens
    output: 4.00,   // $4/1M output tokens
    name: 'Claude 3.5 Haiku',
  },
}

type ModelType = keyof typeof PRICING

interface TokenUsage {
  input_tokens: number
  output_tokens: number
  cached?: boolean
  cost_usd?: number
}

interface Complexity {
  level: 'simple' | 'moderate' | 'complex'
  score: number
}

interface TokenUsageDisplayProps {
  currentUsage: TokenUsage | null
  sessionUsage: TokenUsage
  model?: ModelType
  complexity?: Complexity | null
  onClose?: () => void
}

// 복잡도 표시 정보
const COMPLEXITY_INFO = {
  simple: { label: '단순', color: 'bg-green-100 text-green-700 dark:bg-green-900/50 dark:text-green-300' },
  moderate: { label: '보통', color: 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/50 dark:text-yellow-300' },
  complex: { label: '복잡', color: 'bg-red-100 text-red-700 dark:bg-red-900/50 dark:text-red-300' },
}

export function TokenUsageDisplay({
  currentUsage,
  sessionUsage,
  model = 'gemini-2.5-flash',
  complexity,
  onClose
}: TokenUsageDisplayProps) {
  const pricing = PRICING[model]

  // 비용 계산 (달러) - cost_usd가 있으면 그것을 사용
  const calculateCost = (usage: TokenUsage): number => {
    if (usage.cost_usd !== undefined) {
      return usage.cost_usd
    }
    const inputCost = (usage.input_tokens / 1_000_000) * pricing.input
    const outputCost = (usage.output_tokens / 1_000_000) * pricing.output
    return inputCost + outputCost
  }

  // 원화 환산 (대략 1400원/달러)
  const toKRW = (usd: number): number => usd * 1400

  const sessionCost = calculateCost(sessionUsage)
  const currentCost = currentUsage ? calculateCost(currentUsage) : 0

  return (
    <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-600 rounded-xl p-4 shadow-2xl text-sm">
      {/* 헤더 */}
      <div className="flex items-center justify-between mb-4 pb-3 border-b border-slate-200 dark:border-slate-700">
        <div>
          <h3 className="text-base font-semibold text-slate-900 dark:text-white">
            토큰 사용량
          </h3>
          <span className="text-xs text-slate-500 dark:text-slate-400">
            {pricing.name}
          </span>
        </div>
        {onClose && (
          <button
            onClick={onClose}
            className="p-1 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors"
          >
            <X className="w-5 h-5 text-slate-500" />
          </button>
        )}
      </div>

      {/* 현재 메시지 */}
      {currentUsage && (
        <div className="mb-4 pb-3 border-b border-slate-200 dark:border-slate-700">
          <div className="flex items-center justify-between mb-2">
            <div className="text-xs font-medium text-slate-500 dark:text-slate-400 uppercase tracking-wide">
              이번 응답
            </div>
            <div className="flex items-center gap-2">
              {/* 복잡도 표시 */}
              {complexity && (
                <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${COMPLEXITY_INFO[complexity.level]?.color || COMPLEXITY_INFO.moderate.color}`}>
                  {COMPLEXITY_INFO[complexity.level]?.label || '보통'} ({(complexity.score * 100).toFixed(0)}%)
                </span>
              )}
              {/* 캐시 히트 표시 */}
              {currentUsage.cached && (
                <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800 dark:bg-green-900/50 dark:text-green-300">
                  ⚡ 캐시 히트
                </span>
              )}
            </div>
          </div>
          {currentUsage.cached ? (
            <div className="bg-green-50 dark:bg-green-900/30 rounded-lg p-3 text-center">
              <div className="text-green-700 dark:text-green-300 font-medium">
                캐시된 응답 사용
              </div>
              <div className="text-xs text-green-600 dark:text-green-400 mt-1">
                토큰 소모 없음 - 비용 절감!
              </div>
            </div>
          ) : (
            <>
              <div className="grid grid-cols-2 gap-3">
                <div className="bg-blue-50 dark:bg-blue-900/30 rounded-lg p-2">
                  <div className="text-xs text-blue-600 dark:text-blue-400">입력</div>
                  <div className="text-lg font-bold text-blue-700 dark:text-blue-300 font-mono">
                    {currentUsage.input_tokens.toLocaleString()}
                  </div>
                </div>
                <div className="bg-emerald-50 dark:bg-emerald-900/30 rounded-lg p-2">
                  <div className="text-xs text-emerald-600 dark:text-emerald-400">출력</div>
                  <div className="text-lg font-bold text-emerald-700 dark:text-emerald-300 font-mono">
                    {currentUsage.output_tokens.toLocaleString()}
                  </div>
                </div>
              </div>
              <div className="mt-2 text-right">
                <span className="text-amber-600 dark:text-amber-400 font-mono font-semibold">
                  ${currentCost.toFixed(4)}
                </span>
                <span className="text-slate-500 dark:text-slate-400 ml-2 text-xs">
                  ≈ ₩{Math.round(toKRW(currentCost)).toLocaleString()}
                </span>
              </div>
            </>
          )}
        </div>
      )}

      {/* 세션 누적 */}
      <div className="mb-4">
        <div className="text-xs font-medium text-slate-500 dark:text-slate-400 uppercase tracking-wide mb-2">
          세션 누적
        </div>
        <div className="grid grid-cols-2 gap-3">
          <div className="bg-blue-50 dark:bg-blue-900/30 rounded-lg p-2">
            <div className="text-xs text-blue-600 dark:text-blue-400">입력</div>
            <div className="text-lg font-bold text-blue-700 dark:text-blue-300 font-mono">
              {sessionUsage.input_tokens.toLocaleString()}
            </div>
          </div>
          <div className="bg-emerald-50 dark:bg-emerald-900/30 rounded-lg p-2">
            <div className="text-xs text-emerald-600 dark:text-emerald-400">출력</div>
            <div className="text-lg font-bold text-emerald-700 dark:text-emerald-300 font-mono">
              {sessionUsage.output_tokens.toLocaleString()}
            </div>
          </div>
        </div>
      </div>

      {/* 총 비용 */}
      <div className="bg-gradient-to-r from-amber-50 to-orange-50 dark:from-amber-900/30 dark:to-orange-900/30 rounded-lg p-3">
        <div className="flex items-center justify-between">
          <div>
            <div className="text-xs text-amber-700 dark:text-amber-400 font-medium">세션 총 비용</div>
            <div className="text-2xl font-bold text-amber-600 dark:text-amber-300 font-mono">
              ${sessionCost.toFixed(4)}
            </div>
          </div>
          <div className="text-right">
            <div className="text-xs text-slate-500 dark:text-slate-400">원화 환산</div>
            <div className="text-lg font-semibold text-slate-700 dark:text-slate-200">
              ₩{Math.round(toKRW(sessionCost)).toLocaleString()}
            </div>
          </div>
        </div>
      </div>

      {/* 총 토큰 */}
      <div className="mt-3 pt-3 border-t border-slate-200 dark:border-slate-700 flex justify-between items-center text-sm">
        <span className="text-slate-600 dark:text-slate-400">총 토큰</span>
        <span className="text-slate-900 dark:text-white font-mono font-semibold">
          {(sessionUsage.input_tokens + sessionUsage.output_tokens).toLocaleString()}
        </span>
      </div>
    </div>
  )
}

// 간단한 인라인 표시용 컴포넌트
export function TokenUsageBadge({
  usage,
  model = 'gemini-2.5-flash'
}: {
  usage: TokenUsage | null
  model?: ModelType
}) {
  if (!usage) return null

  const pricing = PRICING[model]
  const cost = (usage.input_tokens / 1_000_000) * pricing.input +
               (usage.output_tokens / 1_000_000) * pricing.output

  return (
    <span className="inline-flex items-center gap-1.5 text-xs">
      <span className="text-blue-600 dark:text-blue-400 font-mono">{usage.input_tokens.toLocaleString()}</span>
      <span className="text-slate-400">/</span>
      <span className="text-emerald-600 dark:text-emerald-400 font-mono">{usage.output_tokens.toLocaleString()}</span>
      <span className="text-amber-600 dark:text-amber-400 font-mono ml-1">${cost.toFixed(4)}</span>
    </span>
  )
}
