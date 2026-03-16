'use client'

import { Bell } from 'lucide-react'
import type { AlertFilter } from './AlertFilterTabs'

const MESSAGES: Record<AlertFilter, string> = {
  all: '아직 알림이 없어요',
  unread: '읽지 않은 알림이 없어요',
  read: '읽은 알림이 없어요',
}

interface Props {
  filter: AlertFilter
}

export function EmptyAlerts({ filter }: Props) {
  return (
    <div className="flex flex-col items-center justify-center py-16 text-gray-500">
      <Bell size={32} className="mb-3 text-gray-600" />
      <p className="text-sm">{MESSAGES[filter]}</p>
    </div>
  )
}
