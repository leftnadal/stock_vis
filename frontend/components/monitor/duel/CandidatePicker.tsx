'use client'

// 후보 선택 — 감시 등록 종목(scope=stock) 중 현재 모니터를 제외한 목록에서 사용자가 고른다.
import type { Monitor } from '@/types/monitor'

interface CandidatePickerProps {
  monitors: Monitor[]
  excludeId: string
  value: string
  onChange: (id: string) => void
}

export function CandidatePicker({ monitors, excludeId, value, onChange }: CandidatePickerProps) {
  const options = monitors.filter((m) => m.scope === 'stock' && m.id !== excludeId)

  return (
    <label className="flex flex-col gap-1 text-sm text-gray-600 dark:text-gray-300">
      교체 후보
      <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        data-testid="candidate-picker"
        className="rounded-lg border border-gray-300 px-3 py-2 dark:border-gray-700 dark:bg-gray-900"
      >
        <option value="">후보를 선택하세요</option>
        {options.map((m) => (
          <option key={m.id} value={m.id}>
            {m.target_ref} · {m.name}
          </option>
        ))}
      </select>
      {options.length === 0 && (
        <span className="text-xs text-gray-400">
          비교할 다른 종목 모니터가 없어요 — 먼저 후보를 등록하세요.
        </span>
      )}
    </label>
  )
}
