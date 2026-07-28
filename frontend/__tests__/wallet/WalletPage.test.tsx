// 지갑 화면 + 모달 검증 (Slice 20b) — 4-상태 + 보유/현금 CRUD 플로우.
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import type { CashBalance, Holding } from '@/types/wallet'

vi.mock('@/components/auth/AuthGuard', () => ({
  AuthGuard: ({ children }: { children: React.ReactNode }) => <>{children}</>,
}))

const listHoldings = vi.fn()
const createHolding = vi.fn()
const updateHolding = vi.fn()
const deleteHolding = vi.fn()
const listCash = vi.fn()
const upsertCash = vi.fn()
const deleteCash = vi.fn()

vi.mock('@/services/walletService', () => ({
  walletService: {
    listHoldings: (...a: unknown[]) => listHoldings(...a),
    createHolding: (...a: unknown[]) => createHolding(...a),
    updateHolding: (...a: unknown[]) => updateHolding(...a),
    deleteHolding: (...a: unknown[]) => deleteHolding(...a),
    listCash: (...a: unknown[]) => listCash(...a),
    upsertCash: (...a: unknown[]) => upsertCash(...a),
    deleteCash: (...a: unknown[]) => deleteCash(...a),
  },
}))

import WalletPage from '@/app/wallet/page'

function holding(overrides: Partial<Holding> = {}): Holding {
  return {
    id: 'h1',
    symbol: 'AAPL',
    name: 'Apple',
    currency: 'USD',
    shares: '10',
    avg_cost: '150.00',
    first_bought_at: '2026-01-10',
    acquisition_fx_rate: null,
    investment_thesis: '아이폰 생태계',
    current_price: '180.00',
    ...overrides,
  }
}

function cash(currency: 'USD' | 'KRW', amount: string): CashBalance {
  return { currency, amount }
}

beforeEach(() => {
  listHoldings.mockReset()
  createHolding.mockReset()
  updateHolding.mockReset()
  deleteHolding.mockReset()
  listCash.mockReset()
  upsertCash.mockReset()
  deleteCash.mockReset()
})

function renderPage() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={qc}>
      <WalletPage />
    </QueryClientProvider>
  )
}

describe('WalletPage 상태', () => {
  it('빈 상태 — 보유 empty + 현금 카드 2종(+입력)', async () => {
    listHoldings.mockResolvedValue([])
    listCash.mockResolvedValue([])
    renderPage()
    await waitFor(() => expect(screen.getByTestId('holdings-empty')).toBeInTheDocument())
    expect(screen.getByTestId('cash-card-USD')).toHaveTextContent('+ 입력')
    expect(screen.getByTestId('cash-card-KRW')).toHaveTextContent('+ 입력')
  })

  it('성공 상태 — 보유 목록 + 현금 금액 렌더', async () => {
    listHoldings.mockResolvedValue([holding()])
    listCash.mockResolvedValue([cash('USD', '1000'), cash('KRW', '700000')])
    renderPage()
    await waitFor(() => expect(screen.getByTestId('holdings-list')).toBeInTheDocument())
    expect(screen.getByTestId('holding-row-AAPL')).toHaveTextContent('AAPL')
    expect(screen.getByTestId('holding-row-AAPL')).toHaveTextContent('아이폰 생태계')
    expect(screen.getByTestId('cash-card-USD')).toHaveTextContent('1,000')
    expect(screen.getByTestId('cash-card-KRW')).toHaveTextContent('700,000')
  })

  it('에러 상태', async () => {
    listHoldings.mockRejectedValue(new Error('boom'))
    listCash.mockResolvedValue([])
    renderPage()
    await waitFor(() => expect(screen.getByTestId('error-state')).toBeInTheDocument())
  })
})

describe('보유 추가 모달 플로우', () => {
  it('[보유 추가] → 폼 입력 → createHolding 호출(대문자 정규화)', async () => {
    const user = userEvent.setup()
    listHoldings.mockResolvedValue([])
    listCash.mockResolvedValue([])
    createHolding.mockResolvedValue(holding({ symbol: 'NVDA' }))
    renderPage()
    await waitFor(() => expect(screen.getByTestId('holdings-empty')).toBeInTheDocument())

    await user.click(screen.getByTestId('add-holding-button'))
    const modal = screen.getByTestId('holding-modal')
    await user.type(within(modal).getByLabelText('종목 심볼 *'), 'nvda')
    await user.type(within(modal).getByLabelText('수량 *'), '5')
    await user.type(within(modal).getByLabelText('평단 *'), '120')
    await user.type(within(modal).getByLabelText('투자 논지 (선택)'), 'AI 가속')
    await user.click(within(modal).getByRole('button', { name: '추가' }))

    await waitFor(() => expect(createHolding).toHaveBeenCalledTimes(1))
    const arg = createHolding.mock.calls[0][0]
    expect(arg.symbol).toBe('NVDA')
    expect(arg.shares).toBe('5')
    expect(arg.avg_cost).toBe('120')
    expect(arg.investment_thesis).toBe('AI 가속')
  })

  it('수량 0 이하면 검증 에러(createHolding 미호출)', async () => {
    const user = userEvent.setup()
    listHoldings.mockResolvedValue([])
    listCash.mockResolvedValue([])
    renderPage()
    await waitFor(() => expect(screen.getByTestId('holdings-empty')).toBeInTheDocument())

    await user.click(screen.getByTestId('add-holding-button'))
    const modal = screen.getByTestId('holding-modal')
    await user.type(within(modal).getByLabelText('종목 심볼 *'), 'AAPL')
    await user.type(within(modal).getByLabelText('수량 *'), '0') // 0 = 검증 실패 대상
    await user.type(within(modal).getByLabelText('평단 *'), '100')
    await user.click(within(modal).getByRole('button', { name: '추가' }))
    expect(within(modal).getByRole('alert')).toHaveTextContent('수량은 0보다')
    expect(createHolding).not.toHaveBeenCalled()
  })
})

describe('보유 수정 모달 플로우', () => {
  it('행 클릭 → 프리필 + 심볼 disabled → updateHolding', async () => {
    const user = userEvent.setup()
    listHoldings.mockResolvedValue([holding()])
    listCash.mockResolvedValue([])
    updateHolding.mockResolvedValue(holding({ shares: '20' }))
    renderPage()
    await waitFor(() => expect(screen.getByTestId('holding-row-AAPL')).toBeInTheDocument())

    await user.click(screen.getByTestId('holding-row-AAPL'))
    const modal = screen.getByTestId('holding-modal')
    expect(within(modal).getByLabelText('종목 심볼 *')).toBeDisabled()
    const sharesInput = within(modal).getByLabelText('수량 *')
    await user.clear(sharesInput)
    await user.type(sharesInput, '20')
    await user.click(within(modal).getByRole('button', { name: '수정' }))

    await waitFor(() => expect(updateHolding).toHaveBeenCalledTimes(1))
    expect(updateHolding.mock.calls[0][0]).toBe('h1') // id
    expect(updateHolding.mock.calls[0][1].shares).toBe('20')
  })
})

describe('현금 모달 플로우', () => {
  it('빈 KRW 카드 클릭 → 프리셋 KRW → upsertCash', async () => {
    const user = userEvent.setup()
    listHoldings.mockResolvedValue([])
    listCash.mockResolvedValue([])
    upsertCash.mockResolvedValue(cash('KRW', '500000'))
    renderPage()
    await waitFor(() => expect(screen.getByTestId('cash-card-KRW')).toBeInTheDocument())

    await user.click(screen.getByTestId('cash-card-KRW'))
    const modal = screen.getByTestId('cash-modal')
    expect(within(modal).getByLabelText('통화 *')).toHaveValue('KRW')
    await user.type(within(modal).getByLabelText('금액 *'), '500000')
    await user.click(within(modal).getByRole('button', { name: '저장' }))

    await waitFor(() => expect(upsertCash).toHaveBeenCalledTimes(1))
    expect(upsertCash.mock.calls[0][0]).toEqual({ currency: 'KRW', amount: '500000' })
  })
})
