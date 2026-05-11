'use client'

import { useState } from 'react'
import type { QuarterlyPoint } from '@/lib/thesis/types'

interface Props {
  history: QuarterlyPoint[]
  unit?: string
}

export function QuarterlySparkline({ history, unit = '' }: Props) {
  const [hoveredIdx, setHoveredIdx] = useState<number | null>(null)

  if (!history || history.length === 0) return null

  // 정규화 (0~1 범위)
  const values = history.map((h) => h.value)
  const min = Math.min(...values)
  const max = Math.max(...values)
  const range = max - min || 1  // 전부 같은 값이면 1로

  const formatValue = (v: number): string => {
    if (unit === '%') return `${v.toFixed(1)}%`
    if (unit === '$') return `$${v.toFixed(2)}`
    const abs = Math.abs(v)
    if (abs >= 1e9) return `${(v / 1e9).toFixed(1)}B`
    if (abs >= 1e6) return `${(v / 1e6).toFixed(1)}M`
    if (abs >= 100) return v.toLocaleString('ko-KR', { maximumFractionDigits: 0 })
    return v.toFixed(2)
  }

  return (
    <div className="relative flex items-end gap-1 h-10">
      {history.map((point, idx) => {
        const normalized = (point.value - min) / range
        const heightPct = Math.max(15, normalized * 100)  // 최소 15%
        const isLatest = idx === history.length - 1
        const isHovered = hoveredIdx === idx

        return (
          <div
            key={`${point.fy}-${point.fq}`}
            className="relative flex-1"
            onMouseEnter={() => setHoveredIdx(idx)}
            onMouseLeave={() => setHoveredIdx(null)}
          >
            <div
              className={`rounded-sm transition-colors ${
                isLatest ? 'bg-blue-500' : 'bg-gray-600'
              } ${isHovered ? 'opacity-80' : ''}`}
              style={{ height: `${heightPct}%` }}
            />
            {/* 분기 라벨 */}
            <span className="block text-center text-[8px] text-gray-500 mt-0.5">
              Q{point.fq}
            </span>
            {/* 호버 툴팁 */}
            {isHovered && (
              <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-1 px-1.5 py-0.5 bg-gray-800 border border-gray-600 rounded text-[10px] text-white whitespace-nowrap z-10">
                Q{point.fq} {point.fy}: {formatValue(point.value)}
              </div>
            )}
          </div>
        )
      })}
    </div>
  )
}
