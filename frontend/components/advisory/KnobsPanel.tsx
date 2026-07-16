// 손잡이 5종 읽기 전용 패널 (Slice 20a §2 절대 규칙 — 슬라이더/input 없음, 값 표시만).
// 쓰기 UI(PUT/PATCH)는 20b. 라벨·범위는 apps/portfolio/models_my.py UserGoal 필드 help_text 미러.
import type { KnobsRead } from '@/types/advisory'

type KnobValueKey = Exclude<keyof KnobsRead, 'available'>

interface KnobRow {
  key: KnobValueKey
  label: string
  format: (v: number | string) => string
}

const KNOB_ROWS: KnobRow[] = [
  { key: 'aggressiveness_offset', label: '공격성 오프셋 A', format: (v) => `${v}%p` },
  { key: 'growth_boost', label: '성장 부스트 G', format: (v) => `${v}%p` },
  { key: 'diversification_weight', label: '분산 가중 w', format: (v) => `${v}` },
  { key: 'concentration_limit', label: '집중도 한도 L', format: (v) => `${v}%` },
  { key: 'exploration_ratio', label: '탐험 비율 E', format: (v) => `${v}%` },
]

interface KnobsPanelProps {
  knobs: KnobsRead
}

export function KnobsPanel({ knobs }: KnobsPanelProps) {
  return (
    <div
      data-testid="knobs-panel"
      className="grid grid-cols-2 gap-3 rounded-xl border border-gray-200 bg-white p-4 shadow-sm dark:border-gray-800 dark:bg-gray-900 sm:grid-cols-5"
    >
      {KNOB_ROWS.map((row) => {
        const value = knobs[row.key]
        return (
          <div key={row.key} data-testid={`knob-${row.key}`} className="flex flex-col">
            <span className="text-[11px] text-gray-400">{row.label}</span>
            <span className="text-sm font-semibold text-gray-900 dark:text-gray-100">
              {value != null ? row.format(value) : '—'}
            </span>
          </div>
        )
      })}
    </div>
  )
}
