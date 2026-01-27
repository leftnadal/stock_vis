'use client'

import { Sparkles } from 'lucide-react'
import type { Suggestion } from '@/types/rag'

interface SuggestionChipsProps {
  suggestions: Suggestion[]
  onSelect: (symbol: string, reason: string) => void
  disabled?: boolean
}

export function SuggestionChips({
  suggestions,
  onSelect,
  disabled = false,
}: SuggestionChipsProps) {
  if (suggestions.length === 0) return null

  return (
    <div className="border-t border-slate-200 bg-slate-50 px-4 py-3 dark:border-slate-700 dark:bg-slate-800/50">
      <div className="flex items-center gap-2 mb-2">
        <Sparkles className="h-4 w-4 text-blue-600 dark:text-blue-400" />
        <h3 className="text-sm font-medium text-slate-700 dark:text-slate-300">
          추천 종목 탐색
        </h3>
      </div>

      <div className="flex flex-wrap gap-2">
        {suggestions.map((suggestion) => (
          <button
            key={suggestion.symbol}
            onClick={() => onSelect(suggestion.symbol, suggestion.reason)}
            disabled={disabled}
            className="group relative inline-flex items-center gap-1.5 rounded-full border border-slate-200 bg-white px-3 py-1.5 text-sm font-medium text-slate-700 transition-all hover:border-blue-300 hover:bg-blue-50 hover:text-blue-700 disabled:cursor-not-allowed disabled:opacity-50 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-300 dark:hover:border-blue-600 dark:hover:bg-blue-950/50 dark:hover:text-blue-400"
          >
            <span className="font-semibold">{suggestion.symbol}</span>
            <span className="text-slate-500 group-hover:text-blue-600 dark:text-slate-400 dark:group-hover:text-blue-400">
              •
            </span>
            <span className="max-w-[150px] truncate text-xs">
              {suggestion.reason}
            </span>

            {/* 호버 툴팁 */}
            <div className="pointer-events-none absolute bottom-full left-1/2 z-10 mb-2 hidden -translate-x-1/2 rounded-lg bg-slate-900 px-3 py-2 text-xs text-white opacity-0 shadow-lg transition-opacity group-hover:block group-hover:opacity-100 dark:bg-slate-700">
              <div className="max-w-xs whitespace-normal">
                <p className="font-semibold">{suggestion.symbol}</p>
                <p className="mt-1 text-slate-300 dark:text-slate-400">
                  {suggestion.reason}
                </p>
              </div>
              {/* 화살표 */}
              <div className="absolute left-1/2 top-full -translate-x-1/2 border-4 border-transparent border-t-slate-900 dark:border-t-slate-700" />
            </div>
          </button>
        ))}
      </div>
    </div>
  )
}
