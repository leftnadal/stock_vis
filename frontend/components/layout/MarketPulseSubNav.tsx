'use client'

// Market Pulse v2 서브탭 (HUB-V02-S2, D-MP2-SUBNAV = A 전역 헤더 서브탭).
// MySubNav 동형(border-b-2 active·"준비 중" 비활성) — 새 네비 패턴 발명 0.
// 탭: 개요 · 거시 근거 · 로테이션 · 무버스(비활성). fetch 0(Link만·배지·프리페치 금지).
import Link from 'next/link'
import { usePathname } from 'next/navigation'

// v2 라우트 단일소스. v1 '/market-pulse'는 포함하지 않는다(정확일치·접두 충돌 방지).
export const MP_V2_BASE = '/market-pulse-v2'

/**
 * v2 표면 판정 순수 함수. base 정확일치 또는 base 하위(base + '/')만 true.
 * ⚠ v1 '/market-pulse'는 false(=== base 아님 · base+'/' 접두 아님) — v1까지 잡아채지 않음.
 * '/market-pulse-v2extra' 같은 오접두도 false(슬래시 경계).
 */
export function isMarketPulseV2Page(pathname: string): boolean {
  return pathname === MP_V2_BASE || pathname.startsWith(MP_V2_BASE + '/')
}

interface Tab {
  label: string
  href: string | null // null = 비활성(준비 중)
  exact?: boolean // 개요는 정확일치(하위 탭에서 함께 활성 방지)
}

const TABS: Tab[] = [
  { label: '개요', href: MP_V2_BASE, exact: true },
  { label: '거시 근거', href: `${MP_V2_BASE}/macro` },
  { label: '로테이션', href: `${MP_V2_BASE}/rotation` },
  { label: '무버스', href: null }, // S4(준비 중)
]

function tabActive(pathname: string, tab: Tab): boolean {
  if (!tab.href) return false
  if (tab.exact) return pathname === tab.href
  return pathname === tab.href || pathname.startsWith(tab.href + '/')
}

export function MarketPulseSubNav() {
  const pathname = usePathname()

  return (
    <div className="border-t border-gray-100 dark:border-gray-800">
      <nav className="mx-auto flex max-w-7xl gap-1 px-4 sm:px-6 lg:px-8" aria-label="Market Pulse 하위 탭">
        {TABS.map((tab) => {
          const testId = `mp-tab-${tabSlug(tab.label)}`
          if (tab.href === null) {
            return (
              <span
                key={tab.label}
                className="cursor-not-allowed px-3 py-2.5 text-sm text-gray-300 dark:text-gray-600"
                aria-disabled="true"
                data-testid={testId}
              >
                <span className="flex items-center gap-1.5">
                  {tab.label}
                  <span className="text-[10px] text-gray-400">준비 중</span>
                </span>
              </span>
            )
          }
          const active = tabActive(pathname, tab)
          return (
            <Link
              key={tab.label}
              href={tab.href}
              aria-current={active ? 'page' : undefined}
              className={`border-b-2 px-3 py-2.5 text-sm transition ${
                active
                  ? 'border-blue-600 font-medium text-blue-600 dark:text-blue-400'
                  : 'border-transparent text-gray-600 hover:text-gray-900 dark:text-gray-400'
              }`}
              data-testid={testId}
            >
              {tab.label}
            </Link>
          )
        })}
      </nav>
    </div>
  )
}

// 라벨 → 안정적 testid 슬러그(한글 라벨 → 영문 키).
function tabSlug(label: string): string {
  switch (label) {
    case '개요':
      return 'overview'
    case '거시 근거':
      return 'macro'
    case '로테이션':
      return 'rotation'
    case '무버스':
      return 'movers'
    default:
      return label
  }
}
