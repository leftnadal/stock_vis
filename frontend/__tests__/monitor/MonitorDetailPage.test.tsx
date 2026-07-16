// 상세 페이지 렌더 검증: pending Claim=마감 버튼 / resolved Claim=VerdictBadge (MON-CLOSE-UI Phase 2)
import { Suspense } from 'react'

import { act, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import type { Claim, Monitor } from '@/types/monitor'

vi.mock('@/components/auth/AuthGuard', () => ({
  AuthGuard: ({ children }: { children: React.ReactNode }) => <>{children}</>,
}))

vi.mock('@/contexts/AuthContext', () => ({
  useAuth: () => ({ user: { username: 'jinie545' } }),
}))

vi.mock('@/components/monitor/CloseModal', () => ({
  CloseModal: ({ claimId, onClose }: { claimId: string; onClose: () => void }) => (
    <div data-testid="close-modal-stub" data-claim-id={claimId}>
      <button onClick={onClose}>close-stub</button>
    </div>
  ),
}))

const monitor: Monitor = {
  id: 'm1',
  scope: 'stock',
  target_ref: 'AAPL',
  name: '애플 감시',
  status: 'active',
  current_state: 'active',
  target_date_end: null,
  resolved_label: 'Apple Inc. (AAPL)',
  latest_score: 0.4,
  display: {
    degree: 100,
    color: '#60A5FA',
    label: '지지',
    phase: 'waxing',
    phase_label: '차오르는 중',
    phase_icon: '🌔',
  },
  indicator_count: 1,
  next_deadline: null,
  has_claim: true,
  close_suggested: false,
  danger_streak: 0,
  created_at: '2026-07-01T00:00:00Z',
  updated_at: '2026-07-01T00:00:00Z',
}

function makeClaim(overrides: Partial<Claim> = {}): Claim {
  return {
    id: 'c1',
    monitor: 'm1',
    assertion: '실적 개선으로 반등한다',
    deadline: null,
    status: 'active',
    outcome: 'pending',
    proposed_verdict: null,
    resolved_by: null,
    factor_tags: [],
    retro_memo: '',
    closure_snapshot: null,
    entry_price: null,
    target_price: null,
    stop_price: null,
    fair_value_low: null,
    fair_value_high: null,
    last_price_zone: null,
    entry_reached_at: null,
    zone_display: null,
    created_at: '2026-07-01T00:00:00Z',
    resolved_at: null,
    ...overrides,
  }
}

const useMonitorMock = vi.fn()
const useMonitorClaimsMock = vi.fn()

vi.mock('@/hooks/useMonitor', () => ({
  useMonitor: (id: string) => useMonitorMock(id),
  useMonitorClaims: (id: string) => useMonitorClaimsMock(id),
  useIndicators: () => ({ data: [{ id: 'i1', name: 'EOD 종합', latest_value: null }] }),
  useClosePreview: () => ({ data: undefined }),
  useSparkline: () => ({ data: null }),
}))

import MonitorDetailPage from '@/app/monitor/[id]/page'

beforeEach(() => {
  useMonitorMock.mockReset()
  useMonitorClaimsMock.mockReset()
})

// use(params)가 Promise를 언랩하며 1회 suspend한다 — act(async)로 마이크로태스크를 흘려보낸다.
async function renderDetail() {
  let utils: ReturnType<typeof render>
  await act(async () => {
    utils = render(
      <Suspense fallback={<div>route-loading</div>}>
        <MonitorDetailPage params={Promise.resolve({ id: 'm1' })} />
      </Suspense>
    )
  })
  return utils!
}

describe('MonitorDetailPage', () => {
  it('pending Claim은 마감 버튼을 보여준다', async () => {
    useMonitorMock.mockReturnValue({ data: monitor, isLoading: false, isError: false, error: null })
    useMonitorClaimsMock.mockReturnValue({ data: [makeClaim()] })
    await renderDetail()

    await waitFor(() => expect(screen.getByText('애플 감시')).toBeInTheDocument())
    expect(screen.getByTestId('claim-close-button')).toBeInTheDocument()
    expect(screen.queryByTestId('verdict-badge')).not.toBeInTheDocument()
  })

  it('resolved Claim은 VerdictBadge를 보여주고 마감 버튼은 없다', async () => {
    useMonitorMock.mockReturnValue({ data: monitor, isLoading: false, isError: false, error: null })
    useMonitorClaimsMock.mockReturnValue({
      data: [makeClaim({ outcome: 'validated', resolved_at: '2026-07-05T00:00:00Z' })],
    })
    await renderDetail()

    await waitFor(() => expect(screen.getByTestId('verdict-badge')).toBeInTheDocument())
    expect(screen.queryByTestId('claim-close-button')).not.toBeInTheDocument()
    expect(screen.getByTestId('claim-row-closure-summary')).toHaveTextContent('판정자 jinie545')
  })

  it('마감 버튼 클릭 시 CloseModal이 해당 claim id로 열린다', async () => {
    useMonitorMock.mockReturnValue({ data: monitor, isLoading: false, isError: false, error: null })
    useMonitorClaimsMock.mockReturnValue({ data: [makeClaim({ id: 'c-target' })] })
    await renderDetail()

    await waitFor(() => expect(screen.getByTestId('claim-close-button')).toBeInTheDocument())
    fireEvent.click(screen.getByTestId('claim-close-button'))

    expect(screen.getByTestId('close-modal-stub')).toHaveAttribute('data-claim-id', 'c-target')
  })

  it('로딩 중에는 로딩 표시를, 404 에러 시 안내 문구를 보여준다', async () => {
    useMonitorMock.mockReturnValue({ data: undefined, isLoading: true, isError: false, error: null })
    useMonitorClaimsMock.mockReturnValue({ data: [] })
    await renderDetail()
    await waitFor(() => expect(screen.getByTestId('monitor-detail-loading')).toBeInTheDocument())

    useMonitorMock.mockReturnValue({
      data: undefined,
      isLoading: false,
      isError: true,
      error: { response: { status: 404 } },
    })
    await renderDetail()
    await waitFor(() =>
      expect(screen.getByText('찾을 수 없는 모니터입니다.')).toBeInTheDocument()
    )
  })
})
