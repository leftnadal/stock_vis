'use client'

// 렌더 전용: degree·color·label은 API(monitor.display)에서 받는다. FE 재계산 없음.
interface Props {
  degree: number // 0~180 (API 제공)
  color: string // hex (API 제공)
  label: string // (API 제공)
  size?: 'sm' | 'md' | 'lg'
  showLabel?: boolean
}

const SIZE_MAP = {
  sm: { fontSize: '1.125rem', text: 'text-xs' },
  md: { fontSize: '1.5rem', text: 'text-xs' },
  lg: { fontSize: '2.25rem', text: 'text-sm' },
}

export function ArrowIndicator({ degree, color, label, size = 'md', showLabel = false }: Props) {
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
