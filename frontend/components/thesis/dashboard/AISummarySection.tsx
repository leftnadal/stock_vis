'use client'

import { Bot } from 'lucide-react'
import { formatAsofDate } from '@/lib/thesis/utils'

interface Props {
  summary: string
  snapshotDate?: string | null
}

export function AISummarySection({ summary, snapshotDate }: Props) {
  if (!summary) return null

  const dateLabel = formatAsofDate(snapshotDate)

  return (
    <div className="bg-gray-900/50 border border-gray-800 rounded-xl p-4">
      <div className="flex items-start gap-3">
        <Bot size={16} className="text-blue-400 flex-shrink-0 mt-0.5" />
        <div className="min-w-0 flex-1">
          <div className="flex items-baseline justify-between gap-2 mb-1">
            <p className="text-gray-500 text-xs font-medium">AI 분석</p>
            {dateLabel && (
              <span className="text-[10px] text-gray-600 whitespace-nowrap">
                {dateLabel} 기준
              </span>
            )}
          </div>
          <p className="text-sm text-gray-300 leading-relaxed">{summary}</p>
        </div>
      </div>
    </div>
  )
}
