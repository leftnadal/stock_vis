// SWAP-P1 애든덤 B — searchStocks URL 계약 회귀 가드.
// 단위 테스트가 searchStocks를 전부 mock하는 탓에 404(잘못된 URL)가 드러나지 않았다(라이브에서만 노출).
// 이 테스트는 stock.ts의 searchStocks 자체를 대상으로 실제 호출 URL을 고정한다.
import { afterEach, describe, expect, it, vi } from 'vitest'

import { stockService } from '@/services/stock'

afterEach(() => {
  vi.restoreAllMocks()
})

describe('stockService.searchStocks URL 계약', () => {
  it('searchStocks는 /stocks/search/?q= 를 호출한다(레거시 /stocks/api/search/ 아님)', async () => {
    const fetchSpy = vi
      .spyOn(globalThis, 'fetch')
      .mockResolvedValue(new Response(JSON.stringify({ results: [] }), { status: 200 }))

    await stockService.searchStocks('MSFT')

    const url = String(fetchSpy.mock.calls[0][0])
    expect(url).toContain('/stocks/search/?q=MSFT')
    expect(url).not.toContain('/stocks/api/search/') // 회귀 방지(404 경로)
  })
})
