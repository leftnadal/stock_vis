// 대결 화면 한 편 렌더 — 판단 불가(claim 없음/근거 부족) + 정상 케이스(계약/마찰/통계/반론).
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import type { ReactNode } from 'react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

const getEvidenceStatus = vi.fn()
const listIndicators = vi.fn()
const createClaimEvidence = vi.fn()

vi.mock('@/services/monitorService', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@/services/monitorService')>()
  return {
    ...actual,
    monitorService: {
      ...actual.monitorService,
      getEvidenceStatus: (...a: unknown[]) => getEvidenceStatus(...a),
      listIndicators: (...a: unknown[]) => listIndicators(...a),
      createClaimEvidence: (...a: unknown[]) => createClaimEvidence(...a),
    },
  }
})

import { SideColumn } from '@/components/monitor/duel/SideColumn'
import type { Claim } from '@/types/monitor'

function wrapper({ children }: { children: ReactNode }) {
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  })
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>
}

const BASE_CLAIM: Claim = {
  id: 'c1',
  monitor: 'm1',
  assertion: '테스트',
  deadline: null,
  status: 'active',
  outcome: 'pending',
  proposed_verdict: null,
  resolved_by: null,
  factor_tags: [],
  retro_memo: '',
  closure_snapshot: null,
  scenario_type: 'hold',
  entry_price: null,
  target_price: null,
  stop_price: null,
  purchase_price: '100',
  purchase_date: '2026-01-01',
  fair_value_low: null,
  fair_value_high: null,
  last_price_zone: null,
  entry_reached_at: null,
  zone_display: null,
  created_at: '2026-01-01T00:00:00Z',
  resolved_at: null,
}

beforeEach(() => {
  getEvidenceStatus.mockReset()
  listIndicators.mockReset()
  createClaimEvidence.mockReset()
  listIndicators.mockResolvedValue([])
})

describe('SideColumn', () => {
  it('claim이 없으면 판단 불가를 표시한다', async () => {
    render(
      <SideColumn testKey="hold" label="보유" targetRef="AAPL" claim={null} />,
      { wrapper }
    )
    await waitFor(() => expect(screen.getByTestId('judgment-unavailable')).toBeInTheDocument())
    expect(screen.queryByTestId('layer-contract')).not.toBeInTheDocument()
  })

  it('근거 판정불가 비율이 절반 이상이면 판단 불가를 표시한다', async () => {
    getEvidenceStatus.mockResolvedValue({
      claim_id: 'c1',
      as_of: '2026-08-11',
      total: 2,
      alive: 0,
      results: [
        { evidence_id: 'e1', kind: 'auto', status: 'unknown', dead_streak_days: 0, indicator_name: 'X', description: '' },
        { evidence_id: 'e2', kind: 'auto', status: 'unknown', dead_streak_days: 0, indicator_name: 'Y', description: '' },
      ],
    })
    render(
      <SideColumn testKey="hold" label="보유" targetRef="AAPL" claim={BASE_CLAIM} />,
      { wrapper }
    )
    await waitFor(() => expect(screen.getByTestId('judgment-unavailable')).toBeInTheDocument())
  })

  it('근거가 충분하면 계약/마찰/통계 3개 층 + 반론 슬롯을 렌더한다', async () => {
    getEvidenceStatus.mockResolvedValue({
      claim_id: 'c1',
      as_of: '2026-08-11',
      total: 2,
      alive: 1,
      results: [
        { evidence_id: 'e1', kind: 'auto', status: 'alive', dead_streak_days: 0, indicator_name: 'X', description: '' },
        { evidence_id: 'e2', kind: 'manual', status: 'expired', dead_streak_days: 10, indicator_name: null, description: '서술 근거' },
      ],
    })
    render(
      <SideColumn
        testKey="hold"
        label="보유"
        targetRef="AAPL"
        claim={BASE_CLAIM}
        avgCost="100"
        currentPrice="120"
      />,
      { wrapper }
    )
    await waitFor(() => expect(screen.getByTestId('layer-contract')).toBeInTheDocument())
    expect(screen.getByTestId('layer-friction')).toBeInTheDocument()
    expect(screen.getByTestId('friction-approx-badge')).toHaveTextContent('어림')
    expect(screen.getByTestId('layer-stats')).toBeInTheDocument()
    expect(screen.getByTestId('layer-stats-unbuilt')).toHaveTextContent('미장착 (v1)')
    expect(screen.getByTestId('counter-argument')).toBeInTheDocument()
  })

  describe('P-2a — 반론 채택 → 근거 등록 유도', () => {
    beforeEach(() => {
      getEvidenceStatus.mockResolvedValue({
        claim_id: 'c1',
        as_of: '2026-08-11',
        total: 2,
        alive: 1,
        results: [
          { evidence_id: 'e1', kind: 'auto', status: 'alive', dead_streak_days: 0, indicator_name: 'X', description: '' },
          { evidence_id: 'e2', kind: 'manual', status: 'expired', dead_streak_days: 10, indicator_name: null, description: '서술 근거' },
        ],
      })
    })

    it('반론 슬롯에 채택 버튼이 있고, 클릭하면 근거 등록 폼이 열린다', async () => {
      render(
        <SideColumn
          testKey="hold"
          label="보유"
          targetRef="AAPL"
          claim={BASE_CLAIM}
          monitorId="m1"
          avgCost="100"
          currentPrice="120"
        />,
        { wrapper }
      )
      await waitFor(() => expect(screen.getByTestId('counter-argument-adopt')).toBeInTheDocument())
      expect(screen.queryByTestId('counter-argument-evidence-form')).not.toBeInTheDocument()

      fireEvent.click(screen.getByTestId('counter-argument-adopt'))

      expect(screen.getByTestId('counter-argument-evidence-form')).toBeInTheDocument()
      expect(screen.getByTestId('evidence-form')).toBeInTheDocument()
      // 규칙 템플릿 반론(집계 사실)은 지표 z 임계로 환원 불가 → 수동형(서술)으로 프리필
      expect(screen.getByTestId('evidence-kind-manual')).toHaveAttribute('aria-pressed', 'true')
      expect(screen.getByTestId('evidence-kind-auto')).toHaveAttribute('aria-pressed', 'false')
      const description = screen.getByTestId('evidence-description-input') as HTMLTextAreaElement
      expect(description.value).toContain('보유 반대 근거')
    })

    it('프리필된 서술로 제출하면 claim/kind=manual로 createClaimEvidence를 호출한다', async () => {
      createClaimEvidence.mockResolvedValue({ id: 'e-new' })
      render(
        <SideColumn
          testKey="hold"
          label="보유"
          targetRef="AAPL"
          claim={BASE_CLAIM}
          monitorId="m1"
          avgCost="100"
          currentPrice="120"
        />,
        { wrapper }
      )
      await waitFor(() => expect(screen.getByTestId('counter-argument-adopt')).toBeInTheDocument())
      fireEvent.click(screen.getByTestId('counter-argument-adopt'))

      fireEvent.click(screen.getByTestId('evidence-form-submit'))

      await waitFor(() => expect(createClaimEvidence).toHaveBeenCalledTimes(1))
      const [payload] = createClaimEvidence.mock.calls[0]
      expect(payload).toMatchObject({ claim: 'c1', kind: 'manual' })
      expect(payload.description).toContain('보유 반대 근거')
    })
  })
})
