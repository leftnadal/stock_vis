'use client'

import Link from 'next/link'
import { Bell } from 'lucide-react'
import { useUnreadAlertCount } from '@/lib/thesis/queries'

export function AlertBell() {
  const unreadCount = useUnreadAlertCount()

  return (
    <Link
      href="/thesis/alerts"
      className="relative p-2 -mr-2 text-gray-400 hover:text-white transition-colors"
    >
      <Bell size={20} />
      {unreadCount > 0 && (
        <span className="absolute -top-0.5 -right-0.5 flex items-center justify-center
          min-w-[18px] h-[18px] px-1 rounded-full
          bg-red-500 text-white text-[10px] font-bold">
          {unreadCount > 99 ? '99+' : unreadCount}
        </span>
      )}
    </Link>
  )
}
