'use client'

import { degreeToColor, degreeToLabel } from '@/lib/monitor/display'

interface Props {
  degree: number // 0~180
  size?: 'sm' | 'md' | 'lg'
  showLabel?: boolean
}

const SIZE_MAP = {
  sm: { fontSize: '1.125rem', text: 'text-xs' },
  md: { fontSize: '1.5rem', text: 'text-xs' },
  lg: { fontSize: '2.25rem', text: 'text-sm' },
}

export function ArrowIndicator({ degree, size = 'md', showLabel = false }: Props) {
  const color = degreeToColor(degree)
  const label = degreeToLabel(degree)
  const { fontSize, text: textClass } = SIZE_MAP[size]

  return (
    <div className="flex flex-col items-center gap-1">
      <span
        style={{
          color,
          fontSize,
          transform: `rotate(${degree - 90}deg)`,
          display: 'inline-block',
          lineHeight: 1,
        }}
        role="img"
        aria-label={label}
      >
        {'→'}
      </span>
      {showLabel && (
        <span style={{ color }} className={textClass}>
          {label}
        </span>
      )}
    </div>
  )
}
