// Slice 20b-f1 — 매수일 선택화 + 미입력 폴백 힌트 (모달 플로우).
// 기존 WalletPage.test 패턴 답습: walletService mock + WalletPage 렌더로 모달 구동.
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import type { Holding } from '@/types/wallet'

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
    investment_thesis: '',
    current_price: '180.00',
    ...overrides,
  }
}

beforeEach(() => {
  ;[listHoldings, createHolding, updateHolding, deleteHolding, listCash, upsertCash, deleteCash].forEach(
    (m) => m.mockReset(),
  )
})

function renderPage() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={qc}>
      <WalletPage />
    </QueryClientProvider>,
  )
}

async function openAddModal(user: ReturnType<typeof userEvent.setup>) {
  listHoldings.mockResolvedValue([])
  listCash.mockResolvedValue([])
  renderPage()
  await waitFor(() => expect(screen.getByTestId('holdings-empty')).toBeInTheDocument())
  await user.click(screen.getByTestId('add-holding-button'))
  return screen.getByTestId('holding-modal')
}

describe('Slice 20b-f1 — 매수일 선택화', () => {
  it('매수일 라벨 (선택) + 미입력 폴백 힌트 노출', async () => {
    const user = userEvent.setup()
    const modal = await openAddModal(user)
    expect(within(modal).getByLabelText('최초 매수일 (선택)')).toBeInTheDocument()
    expect(within(modal).getByTestId('buydate-fallback-hint')).toHaveTextContent('입력일부터 KRW 추적')
  })

  it('매수일 미입력 제출 → createHolding에 first_bought_at omit', async () => {
    const user = userEvent.setup()
    createHolding.mockResolvedValue(holding({ symbol: 'NVDA', first_bought_at: null }))
    const modal = await openAddModal(user)
    await user.type(within(modal).getByLabelText('종목 심볼 *'), 'nvda')
    await user.type(within(modal).getByLabelText('수량 *'), '5')
    await user.type(within(modal).getByLabelText('평단 *'), '120')
    // 매수일 미입력 상태로 제출
    await user.click(within(modal).getByRole('button', { name: '추가' }))

    await waitFor(() => expect(createHolding).toHaveBeenCalledTimes(1))
    const arg = createHolding.mock.calls[0][0]
    expect(arg.symbol).toBe('NVDA')
    expect('first_bought_at' in arg).toBe(false) // 빈 값은 omit(백엔드 spot 캡처)
  })

  it('매수일 입력 시 → 힌트 사라지고 first_bought_at 전달', async () => {
    const user = userEvent.setup()
    createHolding.mockResolvedValue(holding({ symbol: 'MSFT' }))
    const modal = await openAddModal(user)
    await user.type(within(modal).getByLabelText('종목 심볼 *'), 'msft')
    await user.type(within(modal).getByLabelText('수량 *'), '3')
    await user.type(within(modal).getByLabelText('평단 *'), '400')
    await user.type(within(modal).getByLabelText('최초 매수일 (선택)'), '2025-03-15')

    expect(within(modal).queryByTestId('buydate-fallback-hint')).not.toBeInTheDocument()
    await user.click(within(modal).getByRole('button', { name: '추가' }))

    await waitFor(() => expect(createHolding).toHaveBeenCalledTimes(1))
    expect(createHolding.mock.calls[0][0].first_bought_at).toBe('2025-03-15')
  })
})
