/**
 * MP2-SUBPAGES S1 — market-pulse-v2 홈의 거시 허브 CTA 2곳(링크만·fetch 무증가).
 *
 * mpAllHandlers만 등록(macro/pulse 핸들러 없음) + MSW onUnhandledRequest:'error' →
 * 페이지가 macro/pulse를 호출하면 테스트가 실패한다 = "홈 fetch 표면 0 증가"의 회귀 가드.
 */
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, waitFor } from '@testing-library/react'
import type { ReactNode } from 'react'
import { describe, expect, it } from 'vitest'

import { server } from '../mocks/server'
import { mpAllHandlers } from './fixtures'
import MarketPulseV2Page from '@/app/market-pulse-v2/page'

function wrap(ui: ReactNode) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(<QueryClientProvider client={client}>{ui}</QueryClientProvider>)
}

describe('홈 거시 허브 CTA (MP2-SUBPAGES S1)', () => {
  it('CTA ①(거시 근거 보기)·②(금리·지표) 렌더 + 올바른 href, macro/pulse 호출 없음', async () => {
    server.use(...mpAllHandlers())
    wrap(<MarketPulseV2Page />)

    // happy-path 렌더 완료(overview) — 이 시점까지 미핸들 요청(macro/pulse)이 있었다면 MSW가 이미 에러
    await waitFor(() => expect(screen.getByText('확장 국면 지속')).toBeInTheDocument())

    // CTA ① — 허브 진입 카드
    const cta1 = screen.getByRole('link', { name: /거시 근거 보기/ })
    expect(cta1).toHaveAttribute('href', '/market-pulse-v2/macro')

    // CTA ② — 금리·지표 딥링크
    const cta2 = screen.getByRole('link', { name: '금리·지표 →' })
    expect(cta2).toHaveAttribute('href', '/market-pulse-v2/macro?tab=rates')
  })
})
