'use client'

import { X } from 'lucide-react'
import type { PreviewPremise } from '@/lib/thesis/types'

interface Props {
  premise: PreviewPremise
  onRemove?: () => void
}

const CATEGORY_CONFIG: Record<string, { label: string; className: string }> = {
  sentiment:  { label: '심리',       className: 'text-orange-400 bg-orange-900/30' },
  company:    { label: '기업',       className: 'text-green-400 bg-green-900/30' },
  macro:      { label: '매크로',     className: 'text-blue-400 bg-blue-900/30' },
  policy:     { label: '정책',       className: 'text-purple-400 bg-purple-900/30' },
  technical:  { label: '기술적',     className: 'text-cyan-400 bg-cyan-900/30' },
  global:     { label: '글로벌',     className: 'text-yellow-400 bg-yellow-900/30' },
  supply:     { label: '수급',       className: 'text-pink-400 bg-pink-900/30' },
  valuation:  { label: '밸류에이션', className: 'text-emerald-400 bg-emerald-900/30' },
}
const DEFAULT_CATEGORY = { label: '기타', className: 'text-gray-400 bg-gray-800' }

export function PremiseCard({ premise, onRemove }: Props) {
  const config = CATEGORY_CONFIG[premise.category] ?? DEFAULT_CATEGORY

  return (
    <div className="relative bg-gray-900 border border-gray-700 rounded-xl p-4">
      <span className={`text-[10px] px-2 py-0.5 rounded-full mb-2 inline-block ${config.className}`}>
        {config.label}
      </span>
      <p className="text-gray-200 text-sm pr-8">{premise.content}</p>
      {onRemove && (
        <button
          onClick={onRemove}
          className="absolute top-3 right-3 p-1 text-gray-600 hover:text-gray-400
                     transition-colors"
          aria-label="근거 삭제"
        >
          <X size={14} />
        </button>
      )}
    </div>
  )
}
