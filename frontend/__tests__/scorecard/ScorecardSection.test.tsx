// D1-SCOREBOARD 3a — ScorecardSection 훅 통합 (로딩/에러/빈/성공) — MSW 실경로.
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, waitFor } from '@testing-library/react'
import { delay, http, HttpResponse } from 'msw'
import { describe, expect, it } from 'vitest'

import { server } from '../mocks/server'
import { API_BASE_URL } from '@/lib/api/config'
import { ScorecardSection } from '@/components/scorecard/ScorecardSection'
import { scorecardEmpty, scorecardFixture } from '@/lib/scorecard/fixtures'

const SCORECARD_URL = `${API_BASE_URL}/coach/analyst-scorecard/`

function renderSection() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={qc}>
      <ScorecardSection />
    </QueryClientProvider>
  )
}

describe('ScorecardSection', () => {
  it('로딩 상태를 표시한다', async () => {
    server.use(
      http.get(SCORECARD_URL, async () => {
        await delay(50)
        return HttpResponse.json(scorecardEmpty)
      })
    )
    renderSection()
    expect(screen.getByTestId('scorecard-loading')).toBeInTheDocument()
    await waitFor(() => expect(screen.queryByTestId('scorecard-loading')).not.toBeInTheDocument())
  })

  it('에러 상태를 표시한다', async () => {
    server.use(http.get(SCORECARD_URL, () => HttpResponse.json({}, { status: 500 })))
    renderSection()
    await waitFor(() => expect(screen.getByTestId('scorecard-error')).toBeInTheDocument())
  })

  it('심볼 0이면 빈 상태를 표시한다', async () => {
    server.use(http.get(SCORECARD_URL, () => HttpResponse.json(scorecardEmpty)))
    renderSection()
    await waitFor(() => expect(screen.getByTestId('scorecard-empty')).toBeInTheDocument())
    expect(screen.queryByTestId('score-strip')).not.toBeInTheDocument()
  })

  it('성공 시 스트립 + 보드를 렌더한다', async () => {
    server.use(http.get(SCORECARD_URL, () => HttpResponse.json(scorecardFixture)))
    renderSection()
    await waitFor(() => expect(screen.getByTestId('score-strip')).toBeInTheDocument())
    expect(screen.getByTestId('scoreboard-board')).toBeInTheDocument()
    expect(screen.getByTestId('strip-scored-n')).toHaveTextContent('4건')
  })

  it('h=21 쿼리로 요청한다', async () => {
    let seenH: string | null = null
    server.use(
      http.get(SCORECARD_URL, ({ request }) => {
        seenH = new URL(request.url).searchParams.get('h')
        return HttpResponse.json(scorecardEmpty)
      })
    )
    renderSection()
    await waitFor(() => expect(screen.getByTestId('scorecard-empty')).toBeInTheDocument())
    expect(seenH).toBe('21')
  })
})
