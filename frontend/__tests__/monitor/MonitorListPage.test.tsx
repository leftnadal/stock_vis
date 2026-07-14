// 상태 세그먼트 필터(진행/마감/전체 × scope AND) + "n중 m 마감" 파생 검증 (MON-CLOSE-UI Phase 2)
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import type { Claim, Monitor } from '@/types/monitor'

vi.mock('@/components/auth/AuthGuard', () => ({
  AuthGuard: ({ children }: { children: React.ReactNode }) => <>{children}</>,
}))

vi.mock('@/contexts/AuthContext', () => ({
  useAuth: () => ({ user: { username: 'jinie545' } }),
}))

const list = vi.fn()
const listClaims = vi.fn()
const getSparkline = vi.fn()
vi.mock('@/services/monitorService', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@/services/monitorService')>()
  return {
    ...actual,
    monitorService: {
      ...actual.monitorService,
      list: (...a: unknown[]) => list(...a),
      listClaims: (...a: unknown[]) => listClaims(...a),
      getSparkline: (...a: unknown[]) => getSparkline(...a),
    },
  }
})

import MonitorListPage from '@/app/monitor/page'

function makeMonitor(overrides: Partial<Monitor> = {}): Monitor {
  return {
    id: 'm1',
    scope: 'stock',
    target_ref: 'AAPL',
    name: '애플 감시',
    status: 'active',
    current_state: 'active',
    target_date_end: null,
    resolved_label: 'Apple Inc. (AAPL)',
    latest_score: 0.2,
    display: {
      degree: 90,
      color: '#60A5FA',
      label: '중립',
      phase: 'half_moon',
      phase_label: '반달',
      phase_icon: '🌗',
    },
    indicator_count: 2,
    next_deadline: null,
    has_claim: true,
    close_suggested: false,
    danger_streak: 0,
    created_at: '2026-07-01T00:00:00Z',
    updated_at: '2026-07-01T00:00:00Z',
    ...overrides,
  }
}

function makeClaim(overrides: Partial<Claim> = {}): Claim {
  return {
    id: 'c1',
    monitor: 'm1',
    assertion: '반등한다',
    deadline: null,
    status: 'active',
    outcome: 'pending',
    proposed_verdict: null,
    resolved_by: null,
    factor_tags: [],
    retro_memo: '',
    closure_snapshot: null,
    created_at: '2026-07-01T00:00:00Z',
    resolved_at: null,
    ...overrides,
  }
}

beforeEach(() => {
  list.mockReset()
  listClaims.mockReset()
  getSparkline.mockReset()
  getSparkline.mockResolvedValue(null)
})

function renderPage() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={qc}>
      <MonitorListPage />
    </QueryClientProvider>
  )
}

describe('MonitorListPage 상태 세그먼트', () => {
  it('마감된 모니터가 없으면 세그먼트를 숨긴다', async () => {
    list.mockResolvedValue([makeMonitor({ id: 'm1', has_claim: false })])
    listClaims.mockResolvedValue([])
    renderPage()

    await waitFor(() => expect(screen.getByText('애플 감시')).toBeInTheDocument())
    expect(screen.queryByTestId('status-segment')).not.toBeInTheDocument()
  })

  it('기본값=진행 중: 전부 마감된 모니터는 숨기고, 부분 마감은 "n중 m 마감"을 표기한다', async () => {
    list.mockResolvedValue([
      makeMonitor({ id: 'fully-closed', name: '완전마감' }),
      makeMonitor({ id: 'partial', name: '부분마감' }),
      makeMonitor({ id: 'open', name: '진행중', has_claim: false }),
    ])
    listClaims.mockResolvedValue([
      makeClaim({ id: 'c1', monitor: 'fully-closed', outcome: 'validated', resolved_at: '2026-07-01T00:00:00Z' }),
      makeClaim({ id: 'c2', monitor: 'partial', outcome: 'validated', resolved_at: '2026-07-01T00:00:00Z' }),
      makeClaim({ id: 'c3', monitor: 'partial', outcome: 'pending' }),
    ])
    renderPage()

    await waitFor(() => expect(screen.getByTestId('status-segment')).toBeInTheDocument())

    // 기본 진행 중: 완전마감 카드는 숨고, 부분마감/진행중은 보인다.
    expect(screen.queryByText('완전마감')).not.toBeInTheDocument()
    expect(screen.getByText('부분마감')).toBeInTheDocument()
    expect(screen.getByText('진행중')).toBeInTheDocument()
    expect(screen.getByTestId('monitor-card-partial-closed')).toHaveTextContent('2중 1마감')

    // "마감" 세그먼트로 전환하면 완전마감만 보인다(동결 카드 렌더).
    fireEvent.click(screen.getByTestId('status-seg-closed'))
    await waitFor(() => expect(screen.getByText('완전마감')).toBeInTheDocument())
    expect(screen.queryByText('부분마감')).not.toBeInTheDocument()
    expect(screen.queryByText('진행중')).not.toBeInTheDocument()

    // "전체"로 전환하면 셋 다 보인다.
    fireEvent.click(screen.getByTestId('status-seg-all'))
    await waitFor(() => {
      expect(screen.getByText('완전마감')).toBeInTheDocument()
      expect(screen.getByText('부분마감')).toBeInTheDocument()
      expect(screen.getByText('진행중')).toBeInTheDocument()
    })
  })

  it('동결 카드는 live latest_score가 아닌 closure_snapshot 동결값을 렌더한다 (P1.5)', async () => {
    list.mockResolvedValue([makeMonitor({ id: 'fc', name: '동결카드', latest_score: 0.99 })])
    listClaims.mockResolvedValue([
      makeClaim({
        id: 'c1', monitor: 'fc', outcome: 'validated', resolved_at: '2026-07-10T00:00:00Z',
        closure_snapshot: { overall_score: 0.123, frozen_at: '2026-07-10T00:00:00Z', payload: {} },
      }),
    ])
    renderPage()
    await waitFor(() => expect(screen.getByTestId('status-seg-closed')).toBeInTheDocument())
    fireEvent.click(screen.getByTestId('status-seg-closed'))
    await waitFor(() => expect(screen.getByText('동결카드')).toBeInTheDocument())
    const meta = screen.getByTestId('monitor-card-frozen-meta')
    expect(meta).toHaveTextContent('동결 점수 0.123') // 동결값(snapshot)
    expect(meta).not.toHaveTextContent('0.990') // live latest_score 아님
  })

  it('scope 필터와 status 필터가 AND로 교차 적용된다', async () => {
    list.mockResolvedValue([
      makeMonitor({ id: 'stock-closed', name: '주식마감', scope: 'stock' }),
      makeMonitor({ id: 'market-closed', name: '시장마감', scope: 'market' }),
    ])
    listClaims.mockResolvedValue([
      makeClaim({ id: 'c1', monitor: 'stock-closed', outcome: 'validated', resolved_at: '2026-07-01T00:00:00Z' }),
      makeClaim({ id: 'c2', monitor: 'market-closed', outcome: 'validated', resolved_at: '2026-07-01T00:00:00Z' }),
    ])
    renderPage()

    await waitFor(() => expect(screen.getByTestId('status-segment')).toBeInTheDocument())
    fireEvent.click(screen.getByTestId('status-seg-closed'))
    fireEvent.click(screen.getByRole('button', { name: /^시장/ }))

    await waitFor(() => expect(screen.getByText('시장마감')).toBeInTheDocument())
    expect(screen.queryByText('주식마감')).not.toBeInTheDocument()
  })
})
