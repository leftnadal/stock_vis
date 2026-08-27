/**
 * GUIDE-S1C — 실제 Market Pulse v2 페이지 위에서 오버레이 7영역이 모두 앵커에 붙는지.
 *
 * 앵커 계약 테스트(guideAnchors)는 "소스에 속성이 있다"만 증명한다. 이 테스트는
 * 실제 렌더 트리에서 7개 앵커가 전부 해소되는지 = 배지가 하나도 누락되지 않는지를 본다.
 * (조건부 미렌더 컴포넌트에 앵커를 잘못 달면 여기서 잡힌다.)
 */
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import type { ReactNode } from 'react'
import { describe, expect, it, vi } from 'vitest'

vi.mock('next/navigation', () => ({
  usePathname: () => '/market-pulse-v2',
  useRouter: () => ({ push: vi.fn() }),
}))

import { server } from '../mocks/server'
import { mpAllHandlers } from '../market-pulse-v2/fixtures'
import GuideOverlay from '@/components/guide/GuideOverlay'
import MarketPulseV2Page from '@/app/market-pulse-v2/page'
import { getGuideForRoute } from '@/lib/guide'

function wrap(ui: ReactNode) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  })
  return render(<QueryClientProvider client={client}>{ui}</QueryClientProvider>)
}

describe('Market Pulse v2 위의 가이드 오버레이', () => {
  it('7개 영역 앵커가 실제 렌더 트리에서 전부 해소된다', async () => {
    server.use(...mpAllHandlers())
    wrap(
      <>
        <MarketPulseV2Page />
        <GuideOverlay />
      </>
    )

    const guide = getGuideForRoute('/market-pulse-v2')!
    expect(guide.regions).toHaveLength(7)

    // 페이지가 데이터로 렌더될 때까지 대기(앵커는 happy-path에서만 존재)
    await waitFor(() =>
      expect(document.querySelector('[data-guide="marketPulse.regime"]')).not.toBeNull()
    )
    for (const r of guide.regions) {
      expect(
        document.querySelector(`[data-guide="${r.anchor}"]`),
        `앵커 미해소: ${r.anchor}`
      ).not.toBeNull()
    }

    // 오버레이를 열면 7개 배지가 전부 붙는다
    fireEvent.click(screen.getByTestId('guide-toggle'))
    await waitFor(() =>
      expect(screen.getByTestId('guide-badge-marketPulse.regime')).toBeInTheDocument()
    )
    for (const r of guide.regions) {
      expect(
        screen.getByTestId(`guide-badge-${r.anchor}`),
        `배지 미표시: ${r.anchor}`
      ).toBeInTheDocument()
    }
  })
})
