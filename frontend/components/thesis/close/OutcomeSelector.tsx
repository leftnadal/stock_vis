'use client'

import { CheckCircle, XCircle, MinusCircle } from 'lucide-react'

export type Outcome = 'correct' | 'incorrect' | 'neutral'

interface Props {
  value: Outcome | null
  onChange: (outcome: Outcome) => void
  disabled?: boolean
}

const OPTIONS: {
  key: Outcome
  icon: typeof CheckCircle
  label: string
  sub: string
  activeClass: string
}[] = [
  {
    key: 'correct',
    icon: CheckCircle,
    label: '적중',
    sub: '가설대로 흘러갔어요',
    activeClass: 'border-green-500 bg-green-900/20 text-green-400',
  },
  {
    key: 'incorrect',
    icon: XCircle,
    label: '빗나감',
    sub: '예상과 다르게 흘러갔어요',
    activeClass: 'border-red-500 bg-red-900/20 text-red-400',
  },
  {
    key: 'neutral',
    icon: MinusCircle,
    label: '미확정',
    sub: '아직 판단하기 어려워요',
    activeClass: 'border-gray-500 bg-gray-800/50 text-gray-400',
  },
]

export function OutcomeSelector({ value, onChange, disabled }: Props) {
  return (
    <div className="space-y-3">
      {OPTIONS.map((opt) => {
        const Icon = opt.icon
        const isSelected = value === opt.key
        return (
          <button
            key={opt.key}
            onClick={() => onChange(opt.key)}
            disabled={disabled}
            className={`w-full flex items-center gap-4 p-4 rounded-xl border transition-colors text-left ${
              isSelected
                ? opt.activeClass
                : 'border-gray-700 bg-gray-900 text-gray-400 hover:border-gray-600'
            } ${disabled ? 'opacity-50 cursor-not-allowed' : ''}`}
          >
            <Icon size={24} className={isSelected ? '' : 'text-gray-600'} />
            <div>
              <p className={`text-sm font-medium ${isSelected ? '' : 'text-gray-300'}`}>
                {opt.label}
              </p>
              <p className="text-xs text-gray-500 mt-0.5">{opt.sub}</p>
            </div>
          </button>
        )
      })}
    </div>
  )
}
