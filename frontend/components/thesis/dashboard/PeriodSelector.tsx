'use client'

import type { ChartPeriod } from '@/lib/thesis/types'
import { PERIOD_OPTIONS } from '@/lib/thesis/constants'

interface Props {
  period: ChartPeriod
  onChange: (p: ChartPeriod) => void
}

export function PeriodSelector({ period, onChange }: Props) {
  return (
    <div className="flex gap-2">
      {PERIOD_OPTIONS.map((opt) => (
        <button
          key={opt.value}
          onClick={() => onChange(opt.value)}
          className={`px-3 py-1.5 text-xs rounded-lg transition-colors ${
            period === opt.value
              ? 'bg-blue-600 text-white'
              : 'bg-gray-800 text-gray-400 hover:bg-gray-700'
          }`}
        >
          {opt.label}
        </button>
      ))}
    </div>
  )
}
