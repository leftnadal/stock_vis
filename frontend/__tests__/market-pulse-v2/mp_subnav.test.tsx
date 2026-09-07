/**
 * HUB-V02-S2 — Market Pulse v2 전역 서브탭(D-MP2-SUBNAV) 테스트.
 *
 * 커버리지:
 *   1. isMarketPulseV2Page — v2 base·하위는 true / v1 '/market-pulse'·My·오접두는 false(미렌더 계약)
 *   2. 3라우트 렌더 + active(aria-current) 정확 + 개요 정확일치(하위서 비활성)
 *   3. 무버스 비활성("준비 중")
 */
import { render, screen, cleanup } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { usePathname } from 'next/navigation'
import { MarketPulseSubNav, isMarketPulseV2Page } from '@/components/layout/MarketPulseSubNav'

vi.mock('next/navigation', () => ({ usePathname: vi.fn() }))
const mockPath = usePathname as unknown as ReturnType<typeof vi.fn>

afterEach(cleanup)

describe('isMarketPulseV2Page — v1 미포획(미렌더 계약)', () => {
  it('v2 base·하위 → true', () => {
    expect(isMarketPulseV2Page('/market-pulse-v2')).toBe(true)
    expect(isMarketPulseV2Page('/market-pulse-v2/macro')).toBe(true)
    expect(isMarketPulseV2Page('/market-pulse-v2/rotation')).toBe(true)
    // usePathname은 쿼리 문자열을 포함하지 않음(순수 경로) — 하위 경로는 전부 true.
  })
  it('v1 · My · 오접두 → false', () => {
    expect(isMarketPulseV2Page('/market-pulse')).toBe(false) // ★v1 미포획
    expect(isMarketPulseV2Page('/watchlist')).toBe(false)
    expect(isMarketPulseV2Page('/monitor')).toBe(false)
    expect(isMarketPulseV2Page('/market-pulse-v2extra')).toBe(false) // 슬래시 경계
    expect(isMarketPulseV2Page('/')).toBe(false)
  })
})

describe('MarketPulseSubNav 렌더/active', () => {
  it('4탭 렌더(개요·거시 근거·로테이션·무버스)', () => {
    mockPath.mockReturnValue('/market-pulse-v2')
    render(<MarketPulseSubNav />)
    expect(screen.getByTestId('mp-tab-overview')).toBeInTheDocument()
    expect(screen.getByTestId('mp-tab-macro')).toBeInTheDocument()
    expect(screen.getByTestId('mp-tab-rotation')).toBeInTheDocument()
    expect(screen.getByTestId('mp-tab-movers')).toBeInTheDocument()
  })

  it('개요는 정확일치 — 하위 탭에서 비활성', () => {
    mockPath.mockReturnValue('/market-pulse-v2/macro')
    render(<MarketPulseSubNav />)
    expect(screen.getByTestId('mp-tab-macro')).toHaveAttribute('aria-current', 'page')
    expect(screen.getByTestId('mp-tab-overview')).not.toHaveAttribute('aria-current')
  })

  it('개요는 base에서만 active', () => {
    mockPath.mockReturnValue('/market-pulse-v2')
    render(<MarketPulseSubNav />)
    expect(screen.getByTestId('mp-tab-overview')).toHaveAttribute('aria-current', 'page')
    expect(screen.getByTestId('mp-tab-rotation')).not.toHaveAttribute('aria-current')
  })

  it('로테이션 하위서 로테이션 active', () => {
    mockPath.mockReturnValue('/market-pulse-v2/rotation')
    render(<MarketPulseSubNav />)
    expect(screen.getByTestId('mp-tab-rotation')).toHaveAttribute('aria-current', 'page')
  })

  it('무버스 비활성(준비 중·aria-disabled)', () => {
    mockPath.mockReturnValue('/market-pulse-v2')
    render(<MarketPulseSubNav />)
    const movers = screen.getByTestId('mp-tab-movers')
    expect(movers).toHaveAttribute('aria-disabled', 'true')
    expect(movers).toHaveTextContent('준비 중')
  })
})
