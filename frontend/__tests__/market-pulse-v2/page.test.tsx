/**
 * MP-KL-F1 — Market Pulse v2 page.tsx 렌더 + 카드 라우팅 테스트.
 *
 * 커버리지:
 *   - overview 로딩 / 에러 / happy-path 렌더 (TickerBar · AnomalyPanel · NewsPanel · 5 카드)
 *   - StatusBanner: OK → 숨김 / non-OK → 표시
 *   - 5 카드 펼침 라우팅: 클릭 → CardDrawer(dialog) + 타이틀 매핑 + card detail fetch
 *   - drawer 닫기
 *
 * MSW: market-pulse-v2 전용 핸들러(fixtures.ts). page는 mount 시 overview + i18n
 *   두 쿼리를 발사하므로 두 핸들러를 항상 등록한다.
 */
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import type { ReactNode } from 'react'
import { describe, expect, it } from 'vitest'

import { server } from '../mocks/server'
import {
  mpAllHandlers,
  mpI18nSuccess,
  mpOverviewError,
  mpOverviewPending,
  mpOverviewSuccess,
} from './fixtures'
import MarketPulseV2Page from '@/app/market-pulse-v2/page'

function wrap(ui: ReactNode) {
  const client = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  })
  return render(<QueryClientProvider client={client}>{ui}</QueryClientProvider>)
}

describe('MarketPulseV2Page', () => {
  it('로딩 상태: overview pending 동안 "불러오는 중…" 표시', () => {
    server.use(mpOverviewPending(), mpI18nSuccess())
    wrap(<MarketPulseV2Page />)
    expect(screen.getByText('불러오는 중…')).toBeInTheDocument()
  })

  it('에러 상태: overview 500 → 에러 메시지 + "다시 시도" 버튼', async () => {
    server.use(mpOverviewError(), mpI18nSuccess())
    wrap(<MarketPulseV2Page />)

    await waitFor(() =>
      expect(screen.getByText('데이터를 불러오지 못했습니다.')).toBeInTheDocument(),
    )
    expect(screen.getByRole('button', { name: '다시 시도' })).toBeInTheDocument()
  })

  it('happy-path: 5 카드 + TickerBar + AnomalyPanel + NewsPanel 렌더', async () => {
    server.use(...mpAllHandlers())
    wrap(<MarketPulseV2Page />)

    // 5 카드 타이틀(영문) — CardShell이 titleEn을 렌더
    await waitFor(() => expect(screen.getByText('Market Regime')).toBeInTheDocument())
    expect(screen.getByText('Market Breadth')).toBeInTheDocument()
    expect(screen.getByText('Sector Flow')).toBeInTheDocument()
    expect(screen.getByText('Concentration')).toBeInTheDocument()
    expect(screen.getByText('Briefing')).toBeInTheDocument()

    // TickerBar
    expect(screen.getByText('SPY')).toBeInTheDocument()
    // AnomalyPanel(총평)
    expect(screen.getByText('특이 신호 없음')).toBeInTheDocument()
    // NewsPanel
    expect(screen.getByText('News · 시장 뉴스')).toBeInTheDocument()
    expect(screen.getByText('CPI 둔화로 금리 인하 기대')).toBeInTheDocument()
  })

  it('StatusBanner: status=OK 면 배너 숨김', async () => {
    server.use(...mpAllHandlers())
    wrap(<MarketPulseV2Page />)
    await waitFor(() => expect(screen.getByText('Market Regime')).toBeInTheDocument())
    expect(screen.queryByRole('status')).not.toBeInTheDocument()
  })

  it('StatusBanner: status=STALE 면 배너 표시(role=status)', async () => {
    server.use(
      mpOverviewSuccess({
        _meta: {
          status: 'STALE',
          status_reason: '스냅샷 2일 경과',
          generated_at: '2026-06-11T00:00:00Z',
          latency_ms: 12,
          data_finalized: false,
          cache: 'MISS',
        },
      }),
      mpI18nSuccess(),
    )
    // 카드를 펼치지 않으므로 card detail 핸들러 불필요 — overview + i18n 만으로 충분
    wrap(<MarketPulseV2Page />)

    await waitFor(() => {
      const banner = screen.getByRole('status')
      expect(banner).toBeInTheDocument()
      expect(within(banner).getByText('데이터 오래됨')).toBeInTheDocument()
    })
    expect(screen.getByText('스냅샷 2일 경과')).toBeInTheDocument()
  })

  it('라우팅: Concentration(flow) 카드 클릭 → drawer 열림 + 타이틀 매핑 + detail fetch', async () => {
    const user = userEvent.setup()
    server.use(...mpAllHandlers())
    wrap(<MarketPulseV2Page />)

    await waitFor(() => expect(screen.getByText('Concentration')).toBeInTheDocument())
    await user.click(screen.getByText('Concentration'))

    const dialog = await screen.findByRole('dialog')
    expect(dialog).toBeInTheDocument()
    // page.tsx CARD_TITLE['flow'] = 'Concentration · 집중도'
    expect(within(dialog).getByText('Concentration · 집중도')).toBeInTheDocument()
    // CardDetailContainer가 detail fetch 성공 시 cache 라인 렌더
    await waitFor(() =>
      expect(within(dialog).getByText(/cache:/)).toBeInTheDocument(),
    )
  })

  it.each([
    ['Market Regime', 'Market Regime · 시장 국면'],
    ['Market Breadth', 'Market Breadth · 시장 폭'],
    ['Sector Flow', 'Sector Flow · 섹터 흐름'],
    ['Concentration', 'Concentration · 집중도'],
    ['Briefing', 'Briefing · 브리핑'],
  ])('라우팅: %s 카드 → drawer 타이틀 "%s"', async (cardLabel, drawerTitle) => {
    const user = userEvent.setup()
    server.use(...mpAllHandlers())
    wrap(<MarketPulseV2Page />)

    await waitFor(() => expect(screen.getByText(cardLabel)).toBeInTheDocument())
    await user.click(screen.getByText(cardLabel))

    const dialog = await screen.findByRole('dialog')
    expect(within(dialog).getByText(drawerTitle)).toBeInTheDocument()
  })

  it('drawer 닫기: "닫기" 버튼 → dialog 사라짐', async () => {
    const user = userEvent.setup()
    server.use(...mpAllHandlers())
    wrap(<MarketPulseV2Page />)

    await waitFor(() => expect(screen.getByText('Briefing')).toBeInTheDocument())
    await user.click(screen.getByText('Briefing'))

    const dialog = await screen.findByRole('dialog')
    await user.click(within(dialog).getByRole('button', { name: '닫기' }))
    await waitFor(() => expect(screen.queryByRole('dialog')).not.toBeInTheDocument())
  })
})
