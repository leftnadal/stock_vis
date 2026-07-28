'use client'

// 전역 헤더 벨 (MON-P3-ALERT §4). leaf 규칙: 카운트만 표시하고 클릭 시 알림 패널로
// 화면 전환한다(monitor 내부 컴포넌트를 결합하지 않는다 — 링크/네비게이션만).
import Link from 'next/link'
import { Bell } from 'lucide-react'

import { useAuth } from '@/contexts/AuthContext'
import { useAlertSummary } from '@/hooks/useMonitor'

export function AlertBell() {
  const { user } = useAuth()
  const { data } = useAlertSummary(!!user)

  // 미인증 시 벨 미표시.
  if (!user) return null

  const count = data?.unread_deterioration_count ?? 0

  return (
    <Link
      href="/monitor/alerts"
      aria-label="알림"
      className="relative flex h-9 w-9 items-center justify-center rounded-full text-gray-600 hover:bg-gray-100 dark:text-gray-300 dark:hover:bg-gray-800"
    >
      <Bell className="h-5 w-5" />
      {count > 0 && (
        <span
          data-testid="alert-bell-badge"
          className="absolute -right-0.5 -top-0.5 flex h-4 min-w-[16px] items-center justify-center rounded-full bg-red-500 px-1 text-[10px] font-semibold leading-none text-white"
        >
          {count > 99 ? '99+' : count}
        </span>
      )}
    </Link>
  )
}
