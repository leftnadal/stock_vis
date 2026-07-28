// My 서브탭(M-3) 검증 (MON-P3-S3)
import { render, screen } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

let pathname = '/monitor'
vi.mock('next/navigation', () => ({ usePathname: () => pathname }))

const monitorsData = vi.fn()
vi.mock('@/hooks/useMonitor', () => ({
  useMonitors: () => ({ data: monitorsData() }),
}))

import { MySubNav, isMyPage } from '@/components/layout/MySubNav'

beforeEach(() => {
  pathname = '/monitor'
  monitorsData.mockReturnValue([])
})

describe('isMyPage', () => {
  it('My 서브페이지 판정', () => {
    expect(isMyPage('/watchlist')).toBe(true)
    expect(isMyPage('/monitor')).toBe(true)
    expect(isMyPage('/monitor/abc')).toBe(true)
    expect(isMyPage('/portfolio')).toBe(true)
    expect(isMyPage('/wallet')).toBe(true) // Slice 20b — 지갑 활성화
    expect(isMyPage('/chainsight')).toBe(false)
    expect(isMyPage('/')).toBe(false)
  })
})

describe('MySubNav', () => {
  it('5개 탭 렌더, Wallet은 /wallet 링크로 활성(Slice 20b)', () => {
    render(<MySubNav />)
    expect(screen.getByTestId('tab-watchlist')).toBeInTheDocument()
    expect(screen.getByTestId('tab-monitor')).toBeInTheDocument()
    expect(screen.getByTestId('tab-portfolio')).toBeInTheDocument()
    const wallet = screen.getByTestId('tab-wallet')
    expect(wallet).not.toHaveAttribute('aria-disabled')
    expect(wallet).toHaveAttribute('href', '/wallet')
    expect(wallet.textContent).not.toContain('준비 중')
  })

  it('Monitor 배지 = 위험 상태 개수 (기존 리스트 재사용)', () => {
    monitorsData.mockReturnValue([
      { id: '1', current_state: 'critical' },
      { id: '2', current_state: 'needs_review' },
      { id: '3', current_state: 'active' }, // 위험 아님
    ])
    render(<MySubNav />)
    expect(screen.getByTestId('monitor-badge').textContent).toBe('2')
  })

  it('위험 0이면 배지 없음', () => {
    monitorsData.mockReturnValue([{ id: '1', current_state: 'active' }])
    render(<MySubNav />)
    expect(screen.queryByTestId('monitor-badge')).toBeNull()
  })
})
