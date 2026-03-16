'use client'

import { useRouter } from 'next/navigation'
import { MessageSquare, Newspaper, Link2 } from 'lucide-react'
import { toast } from 'sonner'

interface EntryPoint {
  key: string
  label: string
  icon: React.ComponentType<{ size?: number; className?: string }>
  source: string
  enabled: boolean
}

const VISIBLE_ENTRY_POINTS: EntryPoint[] = [
  { key: 'free_input', label: '내 생각',         icon: MessageSquare, source: 'free_input', enabled: true },
  { key: 'news',       label: '오늘 이슈',       icon: Newspaper,     source: 'news',       enabled: true },
  { key: 'chainsight', label: 'Chain Sight에서', icon: Link2,         source: 'chainsight', enabled: false },
]

export function EntryPointGrid() {
  const router = useRouter()

  const handleClick = (entry: EntryPoint) => {
    if (!entry.enabled) {
      toast('곧 열릴 기능이에요!')
      return
    }
    router.push(`/thesis/new?entry=${entry.source}`)
  }

  return (
    <div className="grid grid-cols-2 gap-3">
      {VISIBLE_ENTRY_POINTS.map((entry) => {
        const Icon = entry.icon
        return (
          <button
            key={entry.key}
            onClick={() => handleClick(entry)}
            className={`flex items-center gap-3 bg-gray-900 border rounded-xl p-4
                       text-left transition-all active:scale-[0.97]
                       ${entry.enabled
                         ? 'border-gray-700 hover:border-gray-600 text-white'
                         : 'border-gray-800 text-gray-500 opacity-60'}
                       ${entry.key === 'chainsight' ? 'col-span-2' : ''}`}
          >
            <Icon
              size={20}
              className={entry.enabled ? 'text-blue-400' : 'text-gray-600'}
            />
            <span className="text-sm font-medium">{entry.label}</span>
            {!entry.enabled && (
              <span className="ml-auto text-[10px] text-gray-600 bg-gray-800 px-2 py-0.5 rounded-full">
                준비 중
              </span>
            )}
          </button>
        )
      })}
    </div>
  )
}
