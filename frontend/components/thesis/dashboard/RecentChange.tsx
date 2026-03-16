'use client'

import { Activity } from 'lucide-react'

interface Props {
  text: string | null
}

export function RecentChange({ text }: Props) {
  if (!text) return null

  return (
    <div className="bg-gray-900 border border-gray-800 rounded-xl p-4">
      <div className="flex items-start gap-3">
        <Activity
          size={16}
          className="text-blue-400 flex-shrink-0 mt-0.5"
        />
        <div>
          <p className="text-gray-500 text-xs font-medium mb-1">최근 변화</p>
          <p className="text-gray-300 text-sm leading-relaxed">{text}</p>
        </div>
      </div>
    </div>
  )
}
