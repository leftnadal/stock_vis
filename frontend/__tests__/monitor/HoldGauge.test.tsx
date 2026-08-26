// P-1 보류 계기판 — 1회째는 누적 미표시, 2회째부터 누적 일수 + 양측 참고 성과 표시.
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import type { ReactNode } from 'react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

const listSwapHoldLogs = vi.fn()
const createSwapHoldLog = vi.fn()

vi.mock('@/services/monitorService', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@/services/monitorService')>()
  return {
    ...actual,
    monitorService: {
      ...actual.monitorService,
      listSwapHoldLogs: (...a: unknown[]) => listSwapHoldLogs(...a),
      createSwapHoldLog: (...a: unknown[]) => createSwapHoldLog(...a),
    },
  }
})

import { HoldGauge } from '@/components/monitor/duel/HoldGauge'

function wrapper({ children }: { children: ReactNode }) {
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  })
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>
}

beforeEach(() => {
  listSwapHoldLogs.mockReset()
  createSwapHoldLog.mockReset()
})

describe('HoldGauge', () => {
  it('보류 로그 0건이면 카운트/누적을 표시하지 않는다', async () => {
    listSwapHoldLogs.mockResolvedValue([])
    render(<HoldGauge claimId="c1" candidateRef="MSFT" />, { wrapper })
    await waitFor(() => expect(screen.getByTestId('hold-gauge')).toBeInTheDocument())
    expect(screen.queryByTestId('hold-gauge-count')).not.toBeInTheDocument()
    expect(screen.queryByTestId('hold-gauge-cumulative')).not.toBeInTheDocument()
  })

  it('1회째면 카운트만 표시하고 누적 패널은 숨긴다', async () => {
    listSwapHoldLogs.mockResolvedValue([
      {
        id: '1',
        claim: 'c1',
        held_at: '2026-08-01T00:00:00Z',
        candidate_ref: 'MSFT',
        hold_price: null,
        candidate_price: null,
        note: '',
      },
    ])
    render(<HoldGauge claimId="c1" candidateRef="MSFT" />, { wrapper })
    await waitFor(() => expect(screen.getByTestId('hold-gauge-count')).toHaveTextContent('1회째'))
    expect(screen.queryByTestId('hold-gauge-cumulative')).not.toBeInTheDocument()
  })

  it('2회째부터 누적 일수와 스냅샷 기반 양측 성과·격차를 표시한다', async () => {
    listSwapHoldLogs.mockResolvedValue([
      {
        id: '1',
        claim: 'c1',
        held_at: '2026-08-01T00:00:00Z',
        candidate_ref: 'MSFT',
        hold_price: '100',
        candidate_price: '50',
        note: '',
      },
      {
        id: '2',
        claim: 'c1',
        held_at: '2026-08-05T00:00:00Z',
        candidate_ref: 'MSFT',
        hold_price: '105',
        candidate_price: '52',
        note: '',
      },
    ])
    render(
      <HoldGauge
        claimId="c1"
        candidateRef="MSFT"
        holdPnlPct={5.2}
        holdCurrentPrice="120"
        candidateCurrentPrice="55"
      />,
      { wrapper }
    )
    await waitFor(() => expect(screen.getByTestId('hold-gauge-cumulative')).toBeInTheDocument())
    expect(screen.getByTestId('hold-gauge-cumulative')).toHaveTextContent('+5.20%')
    // 앵커 = 최초 로그(100/50) 대비 현재가(120/55) → 보유 +20.0%, 후보 +10.0%, 격차 +10.0%p
    expect(screen.getByTestId('hold-gauge-hold-performance')).toHaveTextContent('+20.00%')
    expect(screen.getByTestId('hold-gauge-candidate-performance')).toHaveTextContent('+10.00%')
    expect(screen.getByTestId('hold-gauge-gap')).toHaveTextContent('+10.00%p')
  })

  it('앵커 스냅샷 가격이 없는 구 기록이면 "성과 앵커 없음(구 기록)"으로 정직 표기한다', async () => {
    listSwapHoldLogs.mockResolvedValue([
      {
        id: '1',
        claim: 'c1',
        held_at: '2026-08-01T00:00:00Z',
        candidate_ref: 'MSFT',
        hold_price: null,
        candidate_price: null,
        note: '',
      },
      {
        id: '2',
        claim: 'c1',
        held_at: '2026-08-05T00:00:00Z',
        candidate_ref: 'MSFT',
        hold_price: '105',
        candidate_price: '52',
        note: '',
      },
    ])
    render(
      <HoldGauge
        claimId="c1"
        candidateRef="MSFT"
        holdCurrentPrice="120"
        candidateCurrentPrice="55"
      />,
      { wrapper }
    )
    await waitFor(() => expect(screen.getByTestId('hold-gauge-cumulative')).toBeInTheDocument())
    expect(screen.getByTestId('hold-gauge-hold-performance')).toHaveTextContent('성과 앵커 없음(구 기록)')
    expect(screen.getByTestId('hold-gauge-candidate-performance')).toHaveTextContent('성과 앵커 없음(구 기록)')
    expect(screen.getByTestId('hold-gauge-gap')).toHaveTextContent('산출 불가')
  })

  it('후보 현재가 소스가 없으면(감시 등록만·미보유) "현재가 데이터 없음"으로 표기하고 보유측은 산출한다', async () => {
    listSwapHoldLogs.mockResolvedValue([
      {
        id: '1',
        claim: 'c1',
        held_at: '2026-08-01T00:00:00Z',
        candidate_ref: 'MSFT',
        hold_price: '100',
        candidate_price: '50',
        note: '',
      },
      {
        id: '2',
        claim: 'c1',
        held_at: '2026-08-05T00:00:00Z',
        candidate_ref: 'MSFT',
        hold_price: '105',
        candidate_price: '52',
        note: '',
      },
    ])
    render(<HoldGauge claimId="c1" candidateRef="MSFT" holdCurrentPrice="110" />, { wrapper })
    await waitFor(() => expect(screen.getByTestId('hold-gauge-cumulative')).toBeInTheDocument())
    expect(screen.getByTestId('hold-gauge-hold-performance')).toHaveTextContent('+10.00%')
    expect(screen.getByTestId('hold-gauge-candidate-performance')).toHaveTextContent('현재가 데이터 없음')
    expect(screen.getByTestId('hold-gauge-gap')).toHaveTextContent('산출 불가')
  })

  // PART C-4 — BE가 held_at 스냅샷→DailyPrice로 계산한 성과가 있으면 Wallet 현재가 없이도
  // 후보 성과를 보여준다("현재가 데이터 없음" 오표기 해소, 후보가 감시 등록만 되어있어도 됨).
  it('BE 산출 성과 필드가 있으면 후보 현재가(Wallet)가 없어도 "현재가 데이터 없음"이 사라진다', async () => {
    listSwapHoldLogs.mockResolvedValue([
      {
        id: '1',
        claim: 'c1',
        held_at: '2026-08-01T00:00:00Z',
        candidate_ref: 'MSFT',
        hold_price: '100',
        candidate_price: '50',
        note: '',
        hold_performance_pct: 20,
        candidate_performance_pct: 10,
      },
      {
        id: '2',
        claim: 'c1',
        held_at: '2026-08-05T00:00:00Z',
        candidate_ref: 'MSFT',
        hold_price: '105',
        candidate_price: '52',
        note: '',
      },
    ])
    // candidateCurrentPrice 미전달(후보 미보유) — 그래도 BE 필드가 있으면 산출돼야 한다.
    render(<HoldGauge claimId="c1" candidateRef="MSFT" holdCurrentPrice="120" />, { wrapper })
    await waitFor(() => expect(screen.getByTestId('hold-gauge-cumulative')).toBeInTheDocument())
    expect(screen.getByTestId('hold-gauge-hold-performance')).toHaveTextContent('+20.00%')
    expect(screen.getByTestId('hold-gauge-candidate-performance')).toHaveTextContent('+10.00%')
    expect(screen.getByTestId('hold-gauge-candidate-performance')).not.toHaveTextContent(
      '현재가 데이터 없음'
    )
    expect(screen.getByTestId('hold-gauge-gap')).toHaveTextContent('+10.00%p')
  })

  it('보류 버튼 클릭 시 candidate_ref·hold_price·candidate_price와 함께 createSwapHoldLog를 호출한다', async () => {
    listSwapHoldLogs.mockResolvedValue([])
    createSwapHoldLog.mockResolvedValue({ id: 'new' })
    render(
      <HoldGauge
        claimId="c1"
        candidateRef="MSFT"
        holdCurrentPrice="110"
        candidateCurrentPrice="55"
      />,
      { wrapper }
    )
    await waitFor(() => expect(screen.getByTestId('hold-gauge-submit')).toBeInTheDocument())

    fireEvent.click(screen.getByTestId('hold-gauge-submit'))

    await waitFor(() => expect(createSwapHoldLog).toHaveBeenCalledTimes(1))
    const [payload] = createSwapHoldLog.mock.calls[0]
    expect(payload).toMatchObject({
      claim: 'c1',
      candidate_ref: 'MSFT',
      hold_price: '110',
      candidate_price: '55',
    })
  })

  it('후보 현재가가 없으면 candidate_price를 undefined로 전송한다(지어내지 않음)', async () => {
    listSwapHoldLogs.mockResolvedValue([])
    createSwapHoldLog.mockResolvedValue({ id: 'new' })
    render(<HoldGauge claimId="c1" candidateRef="MSFT" holdCurrentPrice="110" />, { wrapper })
    await waitFor(() => expect(screen.getByTestId('hold-gauge-submit')).toBeInTheDocument())

    fireEvent.click(screen.getByTestId('hold-gauge-submit'))

    await waitFor(() => expect(createSwapHoldLog).toHaveBeenCalledTimes(1))
    const [payload] = createSwapHoldLog.mock.calls[0] as [Record<string, unknown>]
    expect(payload.hold_price).toBe('110')
    expect(payload.candidate_price).toBeUndefined()
  })
})
