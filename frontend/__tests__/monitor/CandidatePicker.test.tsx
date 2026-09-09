// SWAP-P1 애든덤 D-2 — 검색 응답 경쟁 조건 가드: 오래된 질의의 지연 응답이 최신 결과를 덮어쓰지 않는다.
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

const searchStocks = vi.fn()

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

import { CandidatePicker } from '@/components/monitor/duel/CandidatePicker'

function deferred<T>() {
  let resolve!: (v: T) => void
  const promise = new Promise<T>((r) => {
    resolve = r
  })
  return { promise, resolve }
}

beforeEach(() => {
  searchStocks.mockReset()
})

describe('CandidatePicker D-2 경쟁 조건 가드', () => {
  it('먼저 보낸 질의의 지연 응답이 나중 질의의 결과를 덮어쓰지 않는다', async () => {
    const first = deferred<unknown[]>() // 'NV' 질의(seq 1) — 나중에 resolve
    const second = deferred<unknown[]>() // 'NVDA' 질의(seq 2) — 먼저 resolve
    searchStocks.mockReturnValueOnce(first.promise).mockReturnValueOnce(second.promise)

    render(
      <CandidatePicker monitors={[]} excludeSymbol="AAPL" value="" onChange={vi.fn()} />
    )
    const input = screen.getByTestId('candidate-picker')

    fireEvent.change(input, { target: { value: 'NV' } })
    await new Promise((r) => setTimeout(r, 350)) // 디바운스 경과 → 'NV' 검색 발화(seq 1)
    fireEvent.change(input, { target: { value: 'NVDA' } })
    await new Promise((r) => setTimeout(r, 350)) // 디바운스 경과 → 'NVDA' 검색 발화(seq 2)

    // 최신(seq 2) 응답을 먼저 resolve → 반영됨
    second.resolve([{ symbol: 'NVDA', stock_name: 'NVIDIA', real_time_price: '900' }])
    await waitFor(() =>
      expect(screen.getByTestId('candidate-option-NVDA')).toBeInTheDocument()
    )

    // 오래된(seq 1) 응답을 뒤늦게 resolve → 무시되어야 함
    first.resolve([{ symbol: 'NVAX', stock_name: 'Novavax', real_time_price: '10' }])
    await new Promise((r) => setTimeout(r, 50))

    expect(screen.queryByTestId('candidate-option-NVAX')).not.toBeInTheDocument()
    expect(screen.getByTestId('candidate-option-NVDA')).toBeInTheDocument()
  })
})
