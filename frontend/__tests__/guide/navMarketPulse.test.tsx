// D-MP-V2-NAV(옵션 B, GUIDE-S1C) — 네비 목적지 v2 전환 + v1 존치 + active 판정 실측
import { render, screen } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

let pathname = '/'
vi.mock('next/navigation', () => ({
  usePathname: () => pathname,
  useRouter: () => ({ push: vi.fn() }),
}))
vi.mock('@/contexts/AuthContext', () => ({
  useAuth: () => ({ user: { user_name: 'kim', nick_name: '김' }, logout: vi.fn() }),
}))
vi.mock('@/hooks/useMonitor', () => ({
  useMonitors: () => ({ data: [] }),
  useAlertSummary: () => ({ data: { unread_deterioration_count: 0 } }),
}))

/** 활성 여부 = 클래스 '토큰' 일치. 부분문자열은 hover:text-blue-600에 오탐한다. */
const isActive = (el: Element) => el.className.split(/\s+/).includes('text-blue-600')

import Header from '@/components/layout/Header'
import MobileNav from '@/components/layout/MobileNav'

beforeEach(() => {
  pathname = '/'
  window.localStorage.clear()
})

describe('Market Pulse 네비 목적지 = v2', () => {
  it('Header의 Market Pulse는 /market-pulse-v2로 간다 (라벨 불변)', () => {
    render(<Header />)
    expect(screen.getByText('Market Pulse').closest('a')).toHaveAttribute(
      'href',
      '/market-pulse-v2'
    )
  })

  it('MobileNav의 Market Pulse도 /market-pulse-v2로 간다', () => {
    render(<MobileNav />)
    expect(screen.getByLabelText('Market Pulse')).toHaveAttribute('href', '/market-pulse-v2')
  })
})

describe('active 표시 실측 (코드로 억지 통일하지 않음 — 관측값 고정)', () => {
  it('v2에서는 Header·MobileNav 모두 활성', () => {
    pathname = '/market-pulse-v2'
    const { unmount } = render(<Header />)
    expect(isActive(screen.getByText('Market Pulse'))).toBe(true)
    unmount()
    render(<MobileNav />)
    expect(isActive(screen.getByLabelText('Market Pulse'))).toBe(true)
  })

  it('v1 직접 접근 시: Header는 비활성(href가 v2라 startsWith 불성립), MobileNav는 활성(prefix 하드코딩)', () => {
    pathname = '/market-pulse'
    const { unmount } = render(<Header />)
    expect(isActive(screen.getByText('Market Pulse'))).toBe(false)
    unmount()
    render(<MobileNav />)
    expect(isActive(screen.getByLabelText('Market Pulse'))).toBe(true)
  })
})
