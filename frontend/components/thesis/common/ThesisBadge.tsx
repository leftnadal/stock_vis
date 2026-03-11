'use client'

import { stateToDisplay } from '@/lib/thesis/utils'
import type { ThesisState, Direction } from '@/lib/thesis/types'

interface Props {
  state: ThesisState
  direction: Direction
}

function getDirectionIcon(state: ThesisState, direction: Direction): string {
  if (state === 'closed_correct')   return '\u2705'
  if (state === 'closed_incorrect') return '\u274C'
  if (state === 'closed_neutral')   return '\u2796'
  if (direction === 'bullish')  return '\uD83D\uDCC8'
  if (direction === 'bearish')  return '\uD83D\uDCC9'
  return '\u2192'
}

export function ThesisBadge({ state, direction }: Props) {
  const { label, colorClass } = stateToDisplay(state)
  const icon = getDirectionIcon(state, direction)

  return (
    <span className={`
      inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-medium
      ${colorClass}
    `}>
      <span>{icon}</span>
      <span>{label}</span>
    </span>
  )
}
