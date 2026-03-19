'use client'

import { BarChart3 } from 'lucide-react'

interface Props {
  visible: boolean
  onToggle: () => void
}

export function ChartToggleButton({ visible, onToggle }: Props) {
  return (
    <button
      onClick={onToggle}
      className="w-full py-3 text-center text-sm text-gray-400
                 border border-gray-700 rounded-xl
                 hover:border-gray-500 transition-colors
                 flex items-center justify-center gap-2"
    >
      <BarChart3 size={14} />
      {visible ? '차트 숨기기' : '차트 보기'}
    </button>
  )
}
