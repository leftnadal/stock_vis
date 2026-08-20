// 근거 관리 모달 — 고지 2건(관측 불가능 근거·갭 체질 배지) 고정 노출 검증 (RECON-SWAP-0813 3-A).
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import type { ReactNode } from 'react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

const listClaimEvidences = vi.fn()
const listIndicators = vi.fn()

vi.mock('@/services/monitorService', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@/services/monitorService')>()
  return {
    ...actual,
    monitorService: {
      ...actual.monitorService,
      listClaimEvidences: (...a: unknown[]) => listClaimEvidences(...a),
      listIndicators: (...a: unknown[]) => listIndicators(...a),
    },
  }
})

import { EvidenceModal } from '@/components/monitor/evidence/EvidenceModal'

function wrapper({ children }: { children: ReactNode }) {
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  })
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>
}

beforeEach(() => {
  listClaimEvidences.mockReset()
  listIndicators.mockReset()
  listClaimEvidences.mockResolvedValue([])
  listIndicators.mockResolvedValue([])
})

describe('EvidenceModal', () => {
  it('고지 2건(관측 불가능 근거·갭 체질 배지)을 항상 표시한다', async () => {
    render(
      <EvidenceModal claimId="c1" monitorId="m1" targetRef="AAPL" onClose={vi.fn()} />,
      { wrapper }
    )
    expect(screen.getByTestId('evidence-notice-unobservable')).toHaveTextContent(
      '관측 불가능한 근거는 자동 감시되지 않습니다.'
    )
    expect(screen.getByTestId('evidence-notice-gap')).toBeInTheDocument()
    expect(screen.getByTestId('gap-badge')).toBeInTheDocument()
  })

  it('근거 없음 상태와 입력 폼을 함께 렌더한다', async () => {
    render(
      <EvidenceModal claimId="c1" monitorId="m1" targetRef="AAPL" onClose={vi.fn()} />,
      { wrapper }
    )
    await waitFor(() => expect(screen.getByTestId('evidence-list-empty')).toBeInTheDocument())
    expect(screen.getByTestId('evidence-form')).toBeInTheDocument()
  })

  it('닫기 버튼 클릭 시 onClose를 호출한다', async () => {
    const onClose = vi.fn()
    render(
      <EvidenceModal claimId="c1" monitorId="m1" targetRef="AAPL" onClose={onClose} />,
      { wrapper }
    )
    fireEvent.click(screen.getByTestId('evidence-modal-close'))
    expect(onClose).toHaveBeenCalledTimes(1)
  })
})
