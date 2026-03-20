'use client'

interface PresetOption {
  id: string
  icon: string
  label: string
  description: string
}

const PRESETS: PresetOption[] = [
  {
    id: 'short',
    icon: '\u26A1',
    label: '단기 (1개월)',
    description: '빠른 변화 감지, 민감한 알림',
  },
  {
    id: 'medium',
    icon: '\uD83D\uDCC8',
    label: '중기 (1~3개월)',
    description: '균형 잡힌 추적, 적당한 알림',
  },
  {
    id: 'long',
    icon: '\uD83D\uDD2D',
    label: '장기 (6개월+)',
    description: '느긋한 추적, 중요 변화만 알림',
  },
]

interface PresetSelectorProps {
  onSelect: (presetId: string) => void
  disabled?: boolean
}

export function PresetSelector({ onSelect, disabled }: PresetSelectorProps) {
  return (
    <div className="px-4 py-3 space-y-2">
      <p className="text-xs text-gray-500 mb-1">모니터링 기간을 선택하세요</p>
      {PRESETS.map((preset) => (
        <button
          key={preset.id}
          onClick={() => onSelect(preset.id)}
          disabled={disabled}
          className="w-full flex items-center gap-3 p-3 bg-gray-900 border border-gray-700
                     rounded-xl text-left hover:border-blue-500/50 active:scale-[0.98]
                     transition-all disabled:opacity-50 disabled:cursor-not-allowed"
        >
          <span className="text-xl flex-shrink-0">{preset.icon}</span>
          <div className="min-w-0">
            <p className="text-sm text-white font-medium">{preset.label}</p>
            <p className="text-xs text-gray-400 mt-0.5">{preset.description}</p>
          </div>
        </button>
      ))}
    </div>
  )
}
