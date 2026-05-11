'use client'

export type AlertFilter = 'all' | 'unread' | 'read'

interface Props {
  current: AlertFilter
  onChange: (filter: AlertFilter) => void
  unreadCount: number
}

export function AlertFilterTabs({ current, onChange, unreadCount }: Props) {
  const tabs: { key: AlertFilter; label: string }[] = [
    { key: 'all', label: '전체' },
    { key: 'unread', label: `안읽은 알림${unreadCount > 0 ? ` (${unreadCount})` : ''}` },
    { key: 'read', label: '읽은 알림' },
  ]

  return (
    <div className="flex gap-2 mb-4">
      {tabs.map((tab) => (
        <button
          key={tab.key}
          onClick={() => onChange(tab.key)}
          className={`px-3 py-1.5 text-xs rounded-full transition-colors ${
            current === tab.key
              ? 'bg-blue-600 text-white'
              : 'bg-gray-800 text-gray-400 hover:text-gray-300'
          }`}
        >
          {tab.label}
        </button>
      ))}
    </div>
  )
}
