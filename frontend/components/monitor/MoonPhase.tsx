'use client'

import { Moon } from 'lucide-react'

import { scoreToPhaseMeta } from '@/lib/monitor/display'

interface Props {
  score: number | null
  size?: 'sm' | 'md' | 'lg'
  showLabel?: boolean
}

const SIZE_MAP = {
  sm: { icon: 20, text: 'text-xs' },
  md: { icon: 32, text: 'text-sm' },
  lg: { icon: 48, text: 'text-base' },
}

function scoreToFillPercent(score: number): number {
  return Math.round(((Math.max(-1, Math.min(1, score)) + 1) / 2) * 100)
}

export function MoonPhase({ score, size = 'md', showLabel = false }: Props) {
  const { icon: iconSize, text: textClass } = SIZE_MAP[size]

  // score=null(warming_up): 흐릿한 달, "데이터 수집 중"
  if (score === null) {
    return (
      <div className="flex flex-col items-center gap-1 opacity-40">
        <Moon size={iconSize} className="text-gray-700" fill="#374151" strokeWidth={1.5} />
        {showLabel && <span className={`text-gray-600 ${textClass}`}>데이터 수집 중</span>}
      </div>
    )
  }

  const meta = scoreToPhaseMeta(score)
  const fillPercent = scoreToFillPercent(score)
  const fillColor = fillPercent > 60 ? '#FBBF24' : fillPercent > 30 ? '#9CA3AF' : '#4B5563'

  return (
    <div className="flex flex-col items-center gap-1">
      <div className="relative" style={{ width: iconSize, height: iconSize }}>
        <Moon
          size={iconSize}
          className="text-gray-700 absolute inset-0"
          fill="#374151"
          strokeWidth={1.5}
        />
        {fillPercent > 0 && (
          <div
            className="absolute inset-0 overflow-hidden"
            style={{ clipPath: `inset(0 ${100 - fillPercent}% 0 0)` }}
          >
            <Moon size={iconSize} style={{ color: fillColor }} fill={fillColor} strokeWidth={1.5} />
          </div>
        )}
      </div>
      {showLabel && <span className={`text-gray-400 ${textClass}`}>{meta.label}</span>}
    </div>
  )
}
