'use client'

import { stateToDisplay } from '@/lib/thesis/utils'
import type { ThesisState, Direction, ThesisStateIconKey } from '@/lib/thesis/types'
import {
  TrendingUp, TrendingDown, Minus, Eye, Loader,
  AlertTriangle, Clock, Timer, CheckCircle, XCircle, MinusCircle,
} from 'lucide-react'

// ── 상태 아이콘 맵: ThesisStateIconKey → lucide 컴포넌트 ──
const stateIconMap: Record<ThesisStateIconKey, React.ComponentType<{ size?: number }>> = {
  loader:         Loader,
  eye:            Eye,
  trending_up:    TrendingUp,
  trending_down:  TrendingDown,
  alert_triangle: AlertTriangle,
  clock:          Clock,
  timer:          Timer,
  check_circle:   CheckCircle,
  x_circle:       XCircle,
  minus_circle:   MinusCircle,
}

// ── 방향 아이콘 ──
const directionIconMap: Record<Direction, React.ComponentType<{ size?: number }>> = {
  bullish:  TrendingUp,
  bearish:  TrendingDown,
  neutral:  Minus,
}

interface Props {
  state: ThesisState
  direction: Direction
}

export function ThesisBadge({ state, direction }: Props) {
  const { label, colorClass, icon } = stateToDisplay(state)
  const StateIcon = stateIconMap[icon]
  const DirIcon = directionIconMap[direction]

  return (
    <span className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-full
                      text-xs font-medium border ${colorClass}`}>
      <DirIcon size={12} />
      <StateIcon size={12} />
      {label}
    </span>
  )
}
