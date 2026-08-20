// 2종 대결 화면 통합 — 레인 안내(불변 요소, 정적 1줄) + 후보 선택 + hold claim 없을 때 판단 불가.
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

vi.mock('@/services/monitorService', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@/services/monitorService')>()
  return {
    ...actual,
    monitorService: {
      ...actual.monitorService,
      get: (...a: unknown[]) => get(...a),
      listClaims: (...a: unknown[]) => listClaims(...a),
      list: (...a: unknown[]) => list(...a),
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

import { DuelView } from '@/components/monitor/duel/DuelView'
import type { Monitor } from '@/types/monitor'

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

beforeEach(() => {
  get.mockReset()
  listClaims.mockReset()
  list.mockReset()
  listHoldings.mockReset()
  listHoldings.mockResolvedValue([])
  listClaims.mockResolvedValue([])
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

  it('후보 선택 전에는 후보 칸이 빈 상태 안내를 보여주고, 선택하면 후보 칸이 렌더된다', async () => {
    get.mockResolvedValue(HOLD_MONITOR)
    list.mockResolvedValue([HOLD_MONITOR, CANDIDATE_MONITOR])
    render(<DuelView monitorId="m1" />, { wrapper })

    await waitFor(() => expect(screen.getByTestId('candidate-picker')).toBeInTheDocument())
    expect(screen.getByTestId('duel-column-candidate-empty')).toBeInTheDocument()

    fireEvent.change(screen.getByTestId('candidate-picker'), { target: { value: 'm2' } })

    await waitFor(() => expect(screen.getByTestId('duel-column-candidate')).toBeInTheDocument())
  })
})
