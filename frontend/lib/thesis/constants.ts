import { TrendingUp, TrendingDown, Minus } from 'lucide-react'
import type { LucideIcon } from 'lucide-react'
import type { ChartPeriod } from './types'

// ── Trend 설정 ──
export interface TrendMeta {
  icon: LucideIcon
  label: string           // 한글 라벨 (카드 내)
  labelWithDelta: string  // 전일 대비 방향 포함 라벨
  className: string       // Tailwind 색상 클래스
}

export const TREND_CONFIG: Record<
  'strengthening' | 'weakening' | 'stable',
  TrendMeta
> = {
  strengthening: {
    icon: TrendingUp,
    label: '강화',
    labelWithDelta: '강화 중 (전일 대비 ↑)',
    className: 'text-green-400',
  },
  weakening: {
    icon: TrendingDown,
    label: '약화',
    labelWithDelta: '약화 중 (전일 대비 ↓)',
    className: 'text-orange-400',
  },
  stable: {
    icon: Minus,
    label: '유지',
    labelWithDelta: '유지 중',
    className: 'text-gray-500',
  },
} as const

// ── Phase 3: 차트 색상 ──
export const CHART_COLORS = [
  '#60A5FA', '#F97316', '#A78BFA', '#34D399',
  '#F472B6', '#FBBF24', '#818CF8', '#2DD4BF',
] as const

export const PERIOD_OPTIONS: { value: ChartPeriod; label: string }[] = [
  { value: 7, label: '7D' },
  { value: 14, label: '14D' },
  { value: 30, label: '30D' },
]
