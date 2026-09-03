// 상세 페이지 렌더 검증: pending Claim=마감 버튼 / resolved Claim=VerdictBadge (MON-CLOSE-UI Phase 2)
import { Suspense } from 'react'

import { act, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import type { Claim, Monitor } from '@/types/monitor'
import type { ChainFeed } from '@/types/chainFeed'

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

// C-2: 상단 스트립 배지·CTA 배선만 검증 대상 — EvidenceModal 내부는 EvidenceModal.test.tsx가 담당.
vi.mock('@/components/monitor/evidence/EvidenceModal', () => ({
  EvidenceModal: ({ claimId, onClose }: { claimId: string; onClose: () => void }) => (
    <div data-testid="evidence-modal-stub" data-claim-id={claimId}>
      <button onClick={onClose}>evidence-stub-close</button>
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
  indicator_coverage: null,
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
    scenario_type: 'new_entry',
    entry_price: null,
    target_price: null,
    stop_price: null,
    purchase_price: null,
    purchase_date: null,
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
// C-2: 상단 스트립 근거 상태 배지 소스 — 기본은 미상태(data: undefined), 개별 테스트가 override.
const useEvidenceStatusMock = vi.fn()

vi.mock('@/hooks/useMonitor', () => ({
  useMonitor: (id: string) => useMonitorMock(id),
  useMonitorClaims: (id: string) => useMonitorClaimsMock(id),
  useMonitorAlerts: () => ({ data: [] }),
  useIndicators: () => ({ data: [{ id: 'i1', name: 'EOD 종합', latest_value: null }] }),
  useClosePreview: () => ({ data: undefined }),
  useSparkline: () => ({ data: null }),
  useSnapshots: () => ({ data: null }),
  useAdvisorNotes: () => ({ data: null }),
  useEvidenceStatus: (...a: unknown[]) => useEvidenceStatusMock(...a),
}))

// EVT-CHAIN-1: ChainSection이 쓰는 useChainFeed — 기본은 미상태(附加 섹션 미표시).
type ChainHookResult = { data: ChainFeed | undefined; isError: boolean }
const useChainFeedMock = vi.fn((): ChainHookResult => ({ data: undefined, isError: false }))
vi.mock('@/hooks/useEventCalendar', () => ({
  useChainFeed: () => useChainFeedMock(),
}))

import MonitorDetailPage from '@/app/monitor/[id]/page'

beforeEach(() => {
  useMonitorMock.mockReset()
  useMonitorClaimsMock.mockReset()
  useEvidenceStatusMock.mockReset()
  useEvidenceStatusMock.mockReturnValue({ data: undefined })
  useChainFeedMock.mockReset()
  useChainFeedMock.mockReturnValue({ data: undefined, isError: false })
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
    // 근거 관리는 시나리오 종류와 무관하게 항상 노출(RECON-SWAP-0813 3-A).
    expect(screen.getByTestId('claim-evidence-button')).toBeInTheDocument()
    // 교체 검토는 hold 시나리오에서만 노출 — 기본 makeClaim()은 new_entry.
    expect(screen.queryByTestId('claim-swap-review-link')).not.toBeInTheDocument()
  })

  it('hold 시나리오 pending Claim은 교체 검토 링크를 /monitor/{id}/swap로 보여준다', async () => {
    useMonitorMock.mockReturnValue({ data: monitor, isLoading: false, isError: false, error: null })
    useMonitorClaimsMock.mockReturnValue({ data: [makeClaim({ scenario_type: 'hold' })] })
    await renderDetail()

    await waitFor(() => expect(screen.getByTestId('claim-swap-review-link')).toBeInTheDocument())
    expect(screen.getByTestId('claim-swap-review-link')).toHaveAttribute('href', '/monitor/m1/swap')
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

  it('B안: 슬림 스트립 6토큰 + 일지 영역이 렌더된다', async () => {
    useMonitorMock.mockReturnValue({ data: monitor, isLoading: false, isError: false, error: null })
    useMonitorClaimsMock.mockReturnValue({ data: [makeClaim()] })
    await renderDetail()

    await waitFor(() => expect(screen.getByTestId('slim-strip')).toBeInTheDocument())
    // 6토큰 전부
    for (const t of [
      'token-state',
      'token-zone',
      'token-score',
      'token-stop-distance',
      'token-dday',
      'token-danger',
    ]) {
      expect(screen.getByTestId(t)).toBeInTheDocument()
    }
    // 일지 영역 + open 항목(첫 claim 사전 커밋)
    expect(screen.getByTestId('detail-journal')).toBeInTheDocument()
    expect(screen.getByTestId('journal-entry-open')).toBeInTheDocument()
  })

  // C-2 — 상단 스트립 근거 상태 배지 + 근거 관리 진입(저노출 링크는 claim 행에 유지).
  describe('C-2 — 상단 근거 상태 배지 + 근거 관리 진입', () => {
    it('근거 0건이면 "근거 0건" 배지를 표시한다', async () => {
      useMonitorMock.mockReturnValue({ data: monitor, isLoading: false, isError: false, error: null })
      useMonitorClaimsMock.mockReturnValue({ data: [makeClaim()] })
      useEvidenceStatusMock.mockReturnValue({
        data: { claim_id: 'c1', as_of: '2026-08-11', total: 0, alive: 0, results: [] },
      })
      await renderDetail()

      await waitFor(() => expect(screen.getByTestId('strip-evidence-badge')).toBeInTheDocument())
      expect(screen.getByTestId('strip-evidence-badge')).toHaveTextContent('근거 0건')
    })

    it('근거가 있으면 "근거 alive/total" 배지를 표시한다', async () => {
      useMonitorMock.mockReturnValue({ data: monitor, isLoading: false, isError: false, error: null })
      useMonitorClaimsMock.mockReturnValue({ data: [makeClaim()] })
      useEvidenceStatusMock.mockReturnValue({
        data: {
          claim_id: 'c1',
          as_of: '2026-08-11',
          total: 3,
          alive: 2,
          results: [],
        },
      })
      await renderDetail()

      await waitFor(() => expect(screen.getByTestId('strip-evidence-badge')).toBeInTheDocument())
      expect(screen.getByTestId('strip-evidence-badge')).toHaveTextContent('근거 2/3')
    })

    it('근거 관리 CTA 클릭 시 근거 관리 모달이 활성 claim으로 열린다', async () => {
      useMonitorMock.mockReturnValue({ data: monitor, isLoading: false, isError: false, error: null })
      useMonitorClaimsMock.mockReturnValue({ data: [makeClaim({ id: 'c-active' })] })
      await renderDetail()

      await waitFor(() => expect(screen.getByTestId('strip-evidence-cta')).toBeInTheDocument())
      expect(screen.queryByTestId('evidence-modal-stub')).not.toBeInTheDocument()

      fireEvent.click(screen.getByTestId('strip-evidence-cta'))

      expect(screen.getByTestId('evidence-modal-stub')).toHaveAttribute('data-claim-id', 'c-active')
    })
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

  // EVT-CHAIN-1: scope 게이팅
  it('scope=stock + 이웃 데이터 → 관계망 섹션 렌더', async () => {
    useMonitorMock.mockReturnValue({ data: monitor, isLoading: false, isError: false, error: null })
    useMonitorClaimsMock.mockReturnValue({ data: [makeClaim()] })
    useChainFeedMock.mockReturnValue({
      data: {
        seed: 'AAPL',
        as_of: '2026-09-03T00:00:00-04:00',
        seed_events: [],
        seed_next_event: null,
        neighbors: [{ symbol: 'MSFT', relation_type: 'PEER_OF', truth_score: 0.9 }],
        items: [],
        after_count: 0,
        params: {},
      },
      isError: false,
    })
    await renderDetail()
    await waitFor(() => expect(screen.getByTestId('chain-section')).toBeInTheDocument())
  })

  it('scope!=stock → 관계망 섹션 미표시', async () => {
    useMonitorMock.mockReturnValue({
      data: { ...monitor, scope: 'theme', target_ref: 'ai-infra' },
      isLoading: false,
      isError: false,
      error: null,
    })
    useMonitorClaimsMock.mockReturnValue({ data: [makeClaim()] })
    await renderDetail()
    await waitFor(() => expect(screen.getByText('애플 감시')).toBeInTheDocument())
    expect(screen.queryByTestId('chain-section')).not.toBeInTheDocument()
  })
})
