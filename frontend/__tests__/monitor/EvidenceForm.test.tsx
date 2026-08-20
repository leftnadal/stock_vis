// 근거 입력 폼 렌더·검증 (RECON-SWAP-0813 3-A) — 자동형/수동형 토글, 필수값 없으면 제출 비활성.
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import type { ReactNode } from 'react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

const listIndicators = vi.fn()
const createClaimEvidence = vi.fn()

vi.mock('@/services/monitorService', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@/services/monitorService')>()
  return {
    ...actual,
    monitorService: {
      ...actual.monitorService,
      listIndicators: (...a: unknown[]) => listIndicators(...a),
      createClaimEvidence: (...a: unknown[]) => createClaimEvidence(...a),
    },
  }
})

import { EvidenceForm } from '@/components/monitor/evidence/EvidenceForm'

function wrapper({ children }: { children: ReactNode }) {
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  })
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>
}

beforeEach(() => {
  listIndicators.mockReset()
  createClaimEvidence.mockReset()
  listIndicators.mockResolvedValue([{ id: 'ind1', name: '12-1 모멘텀' }])
})

describe('EvidenceForm', () => {
  it('자동형: 지표·임계 미입력이면 제출 버튼이 비활성이다', async () => {
    render(<EvidenceForm claimId="c1" monitorId="m1" />, { wrapper })
    await waitFor(() => expect(screen.getByTestId('evidence-form-submit')).toBeDisabled())
  })

  it('자동형: 지표 선택 + 임계 입력 후 제출하면 createClaimEvidence를 호출한다', async () => {
    createClaimEvidence.mockResolvedValue({ id: 'e1' })
    render(<EvidenceForm claimId="c1" monitorId="m1" />, { wrapper })

    await waitFor(() => expect(screen.getByText('12-1 모멘텀')).toBeInTheDocument())
    fireEvent.change(screen.getByTestId('evidence-indicator-select'), {
      target: { value: 'ind1' },
    })
    fireEvent.change(screen.getByTestId('evidence-threshold-input'), {
      target: { value: '0.3' },
    })
    expect(screen.getByTestId('evidence-form-submit')).not.toBeDisabled()
    fireEvent.click(screen.getByTestId('evidence-form-submit'))

    await waitFor(() => expect(createClaimEvidence).toHaveBeenCalledTimes(1))
    const [payload] = createClaimEvidence.mock.calls[0]
    expect(payload).toMatchObject({ claim: 'c1', kind: 'auto', indicator: 'ind1', threshold: 0.3 })
  })

  it('수동형: 서술 없으면 비활성, 입력하면 활성화되고 제출 시 kind=manual로 호출한다', async () => {
    createClaimEvidence.mockResolvedValue({ id: 'e2' })
    render(<EvidenceForm claimId="c1" monitorId="m1" />, { wrapper })

    fireEvent.click(screen.getByTestId('evidence-kind-manual'))
    expect(screen.getByTestId('evidence-form-submit')).toBeDisabled()

    fireEvent.change(screen.getByTestId('evidence-description-input'), {
      target: { value: 'AI 인프라 테마 열기 지속' },
    })
    expect(screen.getByTestId('evidence-form-submit')).not.toBeDisabled()
    fireEvent.click(screen.getByTestId('evidence-form-submit'))

    await waitFor(() => expect(createClaimEvidence).toHaveBeenCalledTimes(1))
    const [payload] = createClaimEvidence.mock.calls[0]
    expect(payload).toMatchObject({ claim: 'c1', kind: 'manual', description: 'AI 인프라 테마 열기 지속' })
  })
})
