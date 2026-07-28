// My 탭 권유 읽기 화면 검증 (Slice 20a) — 4-상태(로딩/에러/빈/성공) + [지금 진단] 플로우.
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import type { AssetSummary, KnobsRead, LatestAdvisory } from '@/types/advisory'

vi.mock('@/components/auth/AuthGuard', () => ({
  AuthGuard: ({ children }: { children: React.ReactNode }) => <>{children}</>,
}))

vi.mock('@/contexts/AuthContext', () => ({
  useAuth: () => ({ user: { username: 'jinie545' }, isAuthenticated: true, loading: false }),
}))

const getLatest = vi.fn()
const getSummary = vi.fn()
const getKnobs = vi.fn()
const run = vi.fn()
const updateKnobs = vi.fn()

vi.mock('@/services/advisoryService', () => ({
  advisoryService: {
    getLatest: (...a: unknown[]) => getLatest(...a),
    getSummary: (...a: unknown[]) => getSummary(...a),
    getKnobs: (...a: unknown[]) => getKnobs(...a),
    run: (...a: unknown[]) => run(...a),
    updateKnobs: (...a: unknown[]) => updateKnobs(...a),
  },
}))

import AdvisoryPage from '@/app/advisory/page'

function makeOutput(overrides: Partial<LatestAdvisory['output']> = {}): NonNullable<LatestAdvisory['output']> {
  return {
    mode: 'BUY',
    summary: {
      goal_target_return_pct: '10.00',
      numeraire: 'KRW',
      cost_basis_note: '취득원가 우선순위: exact',
      dial: {
        dd: '0.00',
        a: '0.02',
        buffer: '0.08',
        is_new_high: true,
        headroom_frac: '0.05',
        deployable_krw_total: '500000',
        frozen: false,
        window_days: 90,
        by_currency: {},
      },
      knobs: { A: 2, G: 1, w: '0.10', L: 30, E: 10 },
      max_concentration: null,
      notes: [],
      progress_gap: {
        return_pct: '4.50',
        gap_pct: '-5.50',
        cost_krw: '10000000',
        value_krw: '10450000',
        by_currency: {},
      },
      allocation_gap: {
        cash_krw: '2000000',
        holdings_value_krw: '8000000',
        idle_ratio: '0.20',
        by_currency: {},
      },
      fx_context: {},
    },
    recommendations: [
      {
        action: 'BUY',
        symbol: 'AAPL',
        currency: 'USD',
        score: '0.7321',
        lane: 'core',
        rationale: '신뢰도 높은 코어 종목, 여력 배치',
      },
      {
        action: 'TRIM',
        symbol: 'TSLA',
        currency: 'USD',
        score: null,
        lane: 'core',
        rationale: '집중도 한도 초과',
      },
      {
        action: 'BUY',
        symbol: 'NVDA',
        currency: 'USD',
        score: '0.5012',
        lane: 'exploration',
        rationale: '탐험 레인 배정 대상',
      },
    ],
    disclaimer: '본 권유는 참고용이며 투자 손실에 대한 책임은 본인에게 있습니다.',
    ...overrides,
  } as NonNullable<LatestAdvisory['output']>
}

function makeSummary(overrides: Partial<AssetSummary> = {}): AssetSummary {
  return {
    available: true,
    date: '2026-07-15',
    total_krw: '12450000',
    by_currency: {},
    price_as_of: '2026-07-15',
    progress_gap: { gap_pct: '-5.50' },
    allocation_gap: { idle_ratio: '0.20' },
    mode: 'BUY',
    ...overrides,
  }
}

function makeKnobs(overrides: Partial<KnobsRead> = {}): KnobsRead {
  return {
    available: true,
    aggressiveness_offset: 2,
    growth_boost: 1,
    diversification_weight: '0.10',
    concentration_limit: 30,
    exploration_ratio: 10,
    ...overrides,
  }
}

beforeEach(() => {
  getLatest.mockReset()
  getSummary.mockReset()
  getKnobs.mockReset()
  run.mockReset()
})

function renderPage() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={qc}>
      <AdvisoryPage />
    </QueryClientProvider>
  )
}

describe('AdvisoryPage 성공 상태', () => {
  it('요약 스트립·권유 목록·손잡이·예상수익률 빈 슬롯을 렌더한다', async () => {
    getLatest.mockResolvedValue({
      available: true,
      trigger: 'manual',
      run_at: '2026-07-15T09:00:00Z',
      output: makeOutput(),
    })
    getSummary.mockResolvedValue(makeSummary())
    getKnobs.mockResolvedValue(makeKnobs())

    renderPage()

    await waitFor(() => expect(screen.getByTestId('advisory-summary-strip')).toBeInTheDocument())

    // 요약 스트립
    expect(screen.getByTestId('summary-total-krw')).toHaveTextContent('12,450,000')
    expect(screen.getByTestId('summary-mode-badge')).toHaveTextContent('BUY')

    // 권유 목록 3건
    const cards = screen.getAllByTestId('recommendation-card')
    expect(cards).toHaveLength(3)
    expect(screen.getByText('AAPL')).toBeInTheDocument()
    expect(screen.getByText('TSLA')).toBeInTheDocument()
    expect(screen.getByText('NVDA')).toBeInTheDocument()

    // score는 BUY만, "배치 우선순위" + "기대수익 아님" 명시
    const scores = screen.getAllByTestId('recommendation-score')
    expect(scores).toHaveLength(2) // AAPL, NVDA(BUY) — TSLA(TRIM)는 score null
    expect(scores[0]).toHaveTextContent('배치 우선순위')
    expect(scores[0]).toHaveTextContent('기대수익 아님')

    // 탐험 레인 배지 (NVDA만)
    expect(screen.getAllByTestId('lane-badge')).toHaveLength(1)

    // 예상수익률 빈 슬롯 — placeholder만, 값 없음
    const returnSlot = screen.getByTestId('expected-return-slot')
    expect(returnSlot).toHaveTextContent('예측 인프라 준비 중')

    // 손잡이 5종 편집 슬라이더 (Slice 20b — 읽기전용 → 편집 승격)
    expect(screen.getByTestId('knob-value-aggressiveness_offset')).toHaveTextContent('2%p')
    expect(screen.getByTestId('knob-value-concentration_limit')).toHaveTextContent('30%')
    // 슬라이더 5종 + 저장 버튼 존재(편집 가능)
    expect(
      screen.getByTestId('knobs-panel').querySelectorAll('input[type="range"]')
    ).toHaveLength(5)
    expect(screen.getByTestId('knobs-save-button')).toBeInTheDocument()

    // 근거 문구
    expect(screen.getByTestId('advisory-disclaimer')).toHaveTextContent('참고용')
    expect(screen.getByTestId('advisory-disclaimer')).toHaveTextContent('예측이 아닙니다')
  })

  it('유령 필드(analyst_target_price 등)를 참조하지 않는다', async () => {
    getLatest.mockResolvedValue({
      available: true,
      trigger: 'manual',
      run_at: '2026-07-15T09:00:00Z',
      output: makeOutput(),
    })
    getSummary.mockResolvedValue(makeSummary())
    getKnobs.mockResolvedValue(makeKnobs())

    renderPage()
    await waitFor(() => expect(screen.getByTestId('advisory-summary-strip')).toBeInTheDocument())

    expect(screen.queryByText(/analyst/i)).not.toBeInTheDocument()
    expect(screen.queryByText(/forward.?pe/i)).not.toBeInTheDocument()
  })
})

describe('AdvisoryPage 빈 상태', () => {
  it('available=false면 안내 문구를 표시한다', async () => {
    getLatest.mockResolvedValue({ available: false, trigger: null, run_at: null, output: null })
    getSummary.mockResolvedValue({ available: false })
    getKnobs.mockResolvedValue({ available: false })

    renderPage()

    await waitFor(() => expect(screen.getByTestId('empty-state')).toBeInTheDocument())
    expect(screen.getByTestId('empty-state')).toHaveTextContent('지금 진단')
    expect(screen.queryByTestId('recommendation-card')).not.toBeInTheDocument()
  })
})

describe('AdvisoryPage 에러 상태', () => {
  it('요청 실패 시 에러 문구를 표시한다', async () => {
    getLatest.mockRejectedValue(new Error('network error'))
    getSummary.mockResolvedValue(makeSummary())
    getKnobs.mockResolvedValue(makeKnobs())

    renderPage()

    await waitFor(() => expect(screen.getByTestId('error-state')).toBeInTheDocument())
    expect(screen.queryByTestId('advisory-summary-strip')).not.toBeInTheDocument()
  })
})

describe('AdvisoryPage [지금 진단] 플로우', () => {
  it('버튼 클릭 시 run()을 호출하고 성공하면 목록을 갱신한다', async () => {
    const user = userEvent.setup()
    getLatest
      .mockResolvedValueOnce({ available: false, trigger: null, run_at: null, output: null })
      .mockResolvedValueOnce({
        available: true,
        trigger: 'manual',
        run_at: '2026-07-15T09:10:00Z',
        output: makeOutput(),
      })
    getSummary.mockResolvedValue(makeSummary())
    getKnobs.mockResolvedValue(makeKnobs())
    run.mockResolvedValue({
      available: true,
      trigger: 'manual',
      run_at: '2026-07-15T09:10:00Z',
      output: makeOutput(),
    })

    renderPage()

    await waitFor(() => expect(screen.getByTestId('empty-state')).toBeInTheDocument())

    const button = screen.getByTestId('run-advisory-button')
    await user.click(button)

    expect(run).toHaveBeenCalledTimes(1)

    await waitFor(() => expect(screen.getAllByTestId('recommendation-card')).toHaveLength(3))
  })

  it('진단 중에는 버튼이 비활성화된다', async () => {
    const user = userEvent.setup()
    getLatest.mockResolvedValue({ available: false, trigger: null, run_at: null, output: null })
    getSummary.mockResolvedValue({ available: false })
    getKnobs.mockResolvedValue({ available: false })
    let resolveRun: (v: LatestAdvisory) => void = () => {}
    run.mockReturnValue(
      new Promise<LatestAdvisory>((resolve) => {
        resolveRun = resolve
      })
    )

    renderPage()
    await waitFor(() => expect(screen.getByTestId('empty-state')).toBeInTheDocument())

    const button = screen.getByTestId('run-advisory-button')
    await user.click(button)

    await waitFor(() => expect(button).toBeDisabled())

    resolveRun({ available: true, trigger: 'manual', run_at: 't', output: makeOutput() })
  })
})
