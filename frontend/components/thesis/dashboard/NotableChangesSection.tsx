'use client'

import { Activity, AlertTriangle, Info } from 'lucide-react'
import type { NotableChange } from '@/lib/thesis/types'
import { formatAsofDate } from '@/lib/thesis/utils'

interface Props {
  changes: NotableChange[]
  snapshotDate?: string | null
  fallbackText?: string
}

export function NotableChangesSection({ changes, snapshotDate, fallbackText }: Props) {
  const dateLabel = formatAsofDate(snapshotDate)

  return (
    <div className="bg-gray-900/50 border border-gray-800 rounded-xl p-4">
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <Activity size={16} className="text-blue-400" />
          <p className="text-gray-500 text-xs font-medium">
            오늘의 변화 ({changes.length}건)
          </p>
        </div>
        {dateLabel && (
          <span className="text-[10px] text-gray-600">
            {dateLabel}
          </span>
        )}
      </div>

      {changes.length === 0 ? (
        <p className="text-gray-600 text-sm">
          {fallbackText || '오늘은 특별한 변화가 없어요'}
        </p>
      ) : (
        <div className="space-y-2">
          {changes.map((c, i) => {
            const isWarning = c.severity === 'warning'
            const Icon = isWarning ? AlertTriangle : Info
            return (
              <div key={i} className="flex items-start gap-2">
                <Icon
                  size={14}
                  className={`flex-shrink-0 mt-0.5 ${
                    isWarning ? 'text-orange-400' : 'text-gray-500'
                  }`}
                />
                <div className="min-w-0">
                  <span className={`text-xs font-medium ${
                    isWarning ? 'text-orange-400' : 'text-gray-400'
                  }`}>
                    {c.indicator_name}
                  </span>
                  <p className="text-xs text-gray-500">{c.description}</p>
                </div>
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}
