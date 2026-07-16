'use client'

// My 영역 서브탭 (M-3): Watchlist → Monitor → Wallet(자리예약) → Portfolio.
// Monitor 배지(위험 개수) = 기존 useMonitors 리스트 재사용(배지 전용 엔드포인트 신설 안 함).
import Link from 'next/link'
import { usePathname } from 'next/navigation'

import { useMonitors } from '@/hooks/useMonitor'
import type { MonitorState } from '@/types/monitor'

const DANGER_STATES: MonitorState[] = ['critical', 'expired', 'needs_review']

export const MY_SUBPAGES = ['/watchlist', '/monitor', '/advisory', '/portfolio'] as const

export function isMyPage(pathname: string): boolean {
  return MY_SUBPAGES.some((p) => pathname === p || pathname.startsWith(p + '/'))
}

interface Tab {
  label: string
  href: string | null // null = 비활성(자리예약)
  match?: string
}

const TABS: Tab[] = [
  { label: 'Watchlist', href: '/watchlist' },
  { label: 'Monitor', href: '/monitor' },
  { label: '코치', href: '/advisory' }, // Slice 20a — 권유 읽기 화면(My 탭 진입점)
  { label: 'Wallet', href: null }, // 자리예약 — 금융 API 연동은 별도 트랙(MON-WALLET)
  { label: 'Portfolio', href: '/portfolio' },
]

export function MySubNav() {
  const pathname = usePathname()
  const { data: monitors } = useMonitors()

  const dangerCount = (monitors ?? []).filter((m) =>
    DANGER_STATES.includes(m.current_state)
  ).length

  return (
    <div className="border-t border-gray-100 dark:border-gray-800">
      <nav className="mx-auto flex max-w-7xl gap-1 px-4 sm:px-6 lg:px-8">
        {TABS.map((tab) => {
          const active = tab.href
            ? pathname === tab.href || pathname.startsWith(tab.href + '/')
            : false
          const badge = tab.label === 'Monitor' && dangerCount > 0 ? dangerCount : null

          const content = (
            <span className="flex items-center gap-1.5">
              {tab.label}
              {badge !== null && (
                <span
                  className="rounded-full bg-red-500 px-1.5 text-[10px] font-semibold leading-4 text-white"
                  data-testid="monitor-badge"
                >
                  {badge}
                </span>
              )}
              {tab.href === null && (
                <span className="text-[10px] text-gray-400">준비 중</span>
              )}
            </span>
          )

          if (tab.href === null) {
            return (
              <span
                key={tab.label}
                className="cursor-not-allowed px-3 py-2.5 text-sm text-gray-300 dark:text-gray-600"
                aria-disabled="true"
                data-testid="tab-wallet"
              >
                {content}
              </span>
            )
          }

          return (
            <Link
              key={tab.label}
              href={tab.href}
              className={`border-b-2 px-3 py-2.5 text-sm transition ${
                active
                  ? 'border-blue-600 font-medium text-blue-600 dark:text-blue-400'
                  : 'border-transparent text-gray-600 hover:text-gray-900 dark:text-gray-400'
              }`}
              data-testid={`tab-${tab.label.toLowerCase()}`}
            >
              {content}
            </Link>
          )
        })}
      </nav>
    </div>
  )
}
