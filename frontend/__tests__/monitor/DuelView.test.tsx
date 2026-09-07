// 2종 대결 화면 통합 — 레인 안내(불변 요소) + 후보 검색 지정(SWAP-P1) + 미등록/등록 분기 + candidate_ref 심볼 저장.
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import type { ReactNode } from 'react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

vi.mock('next/navigation', () => ({
  useRouter: () => ({ push: vi.fn() }),
}))

const get = vi.fn()
const listClaims = vi.fn()
const list = vi.fn()
const listHoldings = vi.fn()
const searchStocks = vi.fn()
const getEvidenceStatus = vi.fn()
const listSwapHoldLogs = vi.fn()
const createSwapHoldLog = vi.fn()
const getWatchlists = vi.fn()
const getWatchlistStocks = vi.fn()
const listDecisionJournalEntries = vi.fn()

vi.mock('@/services/monitorService', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@/services/monitorService')>()
  return {
    ...actual,
    monitorService: {
      ...actual.monitorService,
      get: (...a: unknown[]) => get(...a),
      listClaims: (...a: unknown[]) => listClaims(...a),
      list: (...a: unknown[]) => list(...a),
      getEvidenceStatus: (...a: unknown[]) => getEvidenceStatus(...a),
      listSwapHoldLogs: (...a: unknown[]) => listSwapHoldLogs(...a),
      createSwapHoldLog: (...a: unknown[]) => createSwapHoldLog(...a),
      listDecisionJournalEntries: (...a: unknown[]) => listDecisionJournalEntries(...a),
    },
  }
})

vi.mock('@/services/walletService', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@/services/walletService')>()
  return {
    ...actual,
    walletService: {
      ...actual.walletService,
      listHoldings: (...a: unknown[]) => listHoldings(...a),
    },
  }
})

vi.mock('@/services/stock', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@/services/stock')>()
  return {
    ...actual,
    stockService: {
      ...actual.stockService,
      searchStocks: (...a: unknown[]) => searchStocks(...a),
    },
  }
})

vi.mock('@/services/watchlistService', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@/services/watchlistService')>()
  return {
    ...actual,
    watchlistService: {
      ...actual.watchlistService,
      getWatchlists: (...a: unknown[]) => getWatchlists(...a),
      getWatchlistStocks: (...a: unknown[]) => getWatchlistStocks(...a),
    },
  }
})

import { DuelView } from '@/components/monitor/duel/DuelView'
import type { Claim, Monitor } from '@/types/monitor'

function wrapper({ children }: { children: ReactNode }) {
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  })
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>
}

const HOLD_MONITOR: Monitor = {
  id: 'm1',
  scope: 'stock',
  target_ref: 'AAPL',
  name: 'Apple',
  status: 'active',
  current_state: 'active',
  target_date_end: null,
  resolved_label: 'Apple Inc.',
  latest_score: 0.2,
  display: null,
  indicator_count: 2,
  indicator_coverage: null,
  next_deadline: null,
  has_claim: true,
  close_suggested: false,
  danger_streak: 0,
  created_at: '2026-01-01T00:00:00Z',
  updated_at: '2026-01-01T00:00:00Z',
}

const CANDIDATE_MONITOR: Monitor = { ...HOLD_MONITOR, id: 'm2', target_ref: 'MSFT', name: 'Microsoft' }

const HOLD_CLAIM = {
  id: 'c1',
  monitor: 'm1', // useMonitorClaims는 listClaims() 결과를 c.monitor===id로 필터한다
  status: 'active',
  scenario_type: 'hold',
  zone_display: { zone: 'normal', pnl_pct: 1.0 },
} as unknown as Claim

beforeEach(() => {
  get.mockReset()
  listClaims.mockReset()
  list.mockReset()
  listHoldings.mockReset()
  searchStocks.mockReset()
  getEvidenceStatus.mockReset()
  listSwapHoldLogs.mockReset()
  createSwapHoldLog.mockReset()
  getWatchlists.mockReset()
  getWatchlistStocks.mockReset()
  listDecisionJournalEntries.mockReset()
  listDecisionJournalEntries.mockResolvedValue([])
  listHoldings.mockResolvedValue([])
  listClaims.mockResolvedValue([])
  searchStocks.mockResolvedValue([])
  getEvidenceStatus.mockResolvedValue({ as_of: '2026-09-07', results: [] })
  listSwapHoldLogs.mockResolvedValue([])
  createSwapHoldLog.mockResolvedValue({})
  getWatchlists.mockResolvedValue([])
  getWatchlistStocks.mockResolvedValue([])
})

describe('DuelView', () => {
  it('레인 안내 1줄을 항상 표시한다(불변 요소)', async () => {
    get.mockResolvedValue(HOLD_MONITOR)
    list.mockResolvedValue([HOLD_MONITOR, CANDIDATE_MONITOR])
    render(<DuelView monitorId="m1" />, { wrapper })

    await waitFor(() => expect(screen.getByTestId('duel-lane-notice')).toBeInTheDocument())
    expect(screen.getByTestId('duel-lane-notice')).toHaveTextContent(
      '시장 전체의 이탈 판단은 market_pulse 소관'
    )
  })

  it('hold 상태 Claim이 없으면 보유 편에 판단 불가를 표시하고 보류 계기판·일지 게이트는 숨긴다', async () => {
    get.mockResolvedValue(HOLD_MONITOR)
    list.mockResolvedValue([HOLD_MONITOR, CANDIDATE_MONITOR])
    render(<DuelView monitorId="m1" />, { wrapper })

    await waitFor(() =>
      expect(screen.getByTestId('duel-column-hold')).toContainElement(
        screen.getByTestId('judgment-unavailable')
      )
    )
    expect(screen.queryByTestId('hold-gauge')).not.toBeInTheDocument()
    expect(screen.queryByTestId('decision-journal-gate')).not.toBeInTheDocument()
  })

  it('후보 선택 전에는 후보 칸이 빈 상태 안내를 보여주고, 검색해 지정하면 후보 칸이 렌더된다', async () => {
    get.mockResolvedValue(HOLD_MONITOR)
    list.mockResolvedValue([HOLD_MONITOR, CANDIDATE_MONITOR])
    searchStocks.mockResolvedValue([
      { symbol: 'MSFT', stock_name: 'Microsoft', real_time_price: '400.00' },
    ])
    render(<DuelView monitorId="m1" />, { wrapper })

    await waitFor(() => expect(screen.getByTestId('candidate-picker')).toBeInTheDocument())
    expect(screen.getByTestId('duel-column-candidate-empty')).toBeInTheDocument()

    fireEvent.change(screen.getByTestId('candidate-picker'), { target: { value: 'MSFT' } })
    await waitFor(() => expect(screen.getByTestId('candidate-option-MSFT')).toBeInTheDocument())
    fireEvent.click(screen.getByTestId('candidate-option-MSFT'))

    await waitFor(() => expect(screen.getByTestId('duel-column-candidate')).toBeInTheDocument())
  })

  it('감시 미등록 심볼을 후보로 지정하면 "미등록" 문구를 표시한다', async () => {
    get.mockResolvedValue(HOLD_MONITOR)
    list.mockResolvedValue([HOLD_MONITOR]) // MSFT/NVDA 미등록
    searchStocks.mockResolvedValue([
      { symbol: 'NVDA', stock_name: 'NVIDIA', real_time_price: '900.00' },
    ])
    render(<DuelView monitorId="m1" />, { wrapper })

    await waitFor(() => expect(screen.getByTestId('candidate-picker')).toBeInTheDocument())
    fireEvent.change(screen.getByTestId('candidate-picker'), { target: { value: 'NVDA' } })
    await waitFor(() => expect(screen.getByTestId('candidate-option-NVDA')).toBeInTheDocument())
    fireEvent.click(screen.getByTestId('candidate-option-NVDA'))

    await waitFor(() =>
      expect(screen.getByTestId('unregistered-candidate-note')).toBeInTheDocument()
    )
  })

  it('감시 등록 심볼을 후보로 지정하면 미등록 문구 없이 후보 칸이 렌더된다(동등성)', async () => {
    get.mockResolvedValue(HOLD_MONITOR)
    list.mockResolvedValue([HOLD_MONITOR, CANDIDATE_MONITOR])
    searchStocks.mockResolvedValue([
      { symbol: 'MSFT', stock_name: 'Microsoft', real_time_price: '400.00' },
    ])
    render(<DuelView monitorId="m1" />, { wrapper })

    await waitFor(() => expect(screen.getByTestId('candidate-picker')).toBeInTheDocument())
    fireEvent.change(screen.getByTestId('candidate-picker'), { target: { value: 'MSFT' } })
    await waitFor(() => expect(screen.getByTestId('candidate-option-MSFT')).toBeInTheDocument())
    fireEvent.click(screen.getByTestId('candidate-option-MSFT'))

    await waitFor(() => expect(screen.getByTestId('duel-column-candidate')).toBeInTheDocument())
    expect(screen.queryByTestId('unregistered-candidate-note')).not.toBeInTheDocument()
  })

  it('보류 저장 시 SwapHoldLog.candidate_ref에 심볼(대문자)이 전달된다', async () => {
    get.mockResolvedValue(HOLD_MONITOR)
    list.mockResolvedValue([HOLD_MONITOR, CANDIDATE_MONITOR])
    listClaims.mockResolvedValue([HOLD_CLAIM])
    searchStocks.mockResolvedValue([
      { symbol: 'MSFT', stock_name: 'Microsoft', real_time_price: '400.00' },
    ])
    render(<DuelView monitorId="m1" />, { wrapper })

    await waitFor(() => expect(screen.getByTestId('candidate-picker')).toBeInTheDocument())
    fireEvent.change(screen.getByTestId('candidate-picker'), { target: { value: 'MSFT' } })
    await waitFor(() => expect(screen.getByTestId('candidate-option-MSFT')).toBeInTheDocument())
    fireEvent.click(screen.getByTestId('candidate-option-MSFT'))

    await waitFor(() => expect(screen.getByTestId('hold-gauge-submit')).toBeInTheDocument())
    fireEvent.click(screen.getByTestId('hold-gauge-submit'))

    await waitFor(() => expect(createSwapHoldLog).toHaveBeenCalled())
    expect(createSwapHoldLog).toHaveBeenCalledWith(
      expect.objectContaining({ claim: 'c1', candidate_ref: 'MSFT' })
    )
  })
})
