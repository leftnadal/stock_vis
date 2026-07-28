// 전역 내비 6칸+아바타+My 서브탭 검증 (MON-P3-S3)
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

import Header from '@/components/layout/Header'

beforeEach(() => {
  pathname = '/'
  window.localStorage.clear()
})

describe('Header 6칸 내비', () => {
  it('공용 5칸 + My = 6칸 (포트폴리오·마이페이지 top nav 제거)', () => {
    render(<Header />)
    expect(screen.getByText('대시보드')).toBeInTheDocument()
    expect(screen.getByText('Market Pulse')).toBeInTheDocument()
    expect(screen.getByText('Chain Sight')).toBeInTheDocument()
    expect(screen.getByText('뉴스')).toBeInTheDocument()
    expect(screen.getByText('스크리너')).toBeInTheDocument()
    expect(screen.getByText('My')).toBeInTheDocument()
    // top nav에 포트폴리오·마이페이지 없음
    expect(screen.queryByText('포트폴리오')).toBeNull()
    expect(screen.queryByText('마이페이지')).toBeNull()
  })

  it('My 링크는 기본 /watchlist', () => {
    render(<Header />)
    expect(screen.getByText('My').closest('a')).toHaveAttribute('href', '/watchlist')
  })

  it('아바타 메뉴(로그인 사용자) 표시', () => {
    render(<Header />)
    expect(screen.getByLabelText('계정 메뉴')).toBeInTheDocument()
  })

  it('공용 페이지(/)에선 My 서브탭 미표시', () => {
    render(<Header />)
    expect(screen.queryByTestId('tab-watchlist')).toBeNull()
  })

  it('My 페이지(/monitor)에선 서브탭 표시', () => {
    pathname = '/monitor'
    render(<Header />)
    expect(screen.getByTestId('tab-monitor')).toBeInTheDocument()
  })
})
