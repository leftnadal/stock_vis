// CloseModal 프리필·판정 필수·미선택 지표 제외·409 핸들링 검증 (MON-CLOSE-UI Phase 2)
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import type { ReactNode } from 'react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

const closePreview = vi.fn()
const closeClaim = vi.fn()

vi.mock('@/services/monitorService', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@/services/monitorService')>()
  return {
    ...actual,
    monitorService: {
      ...actual.monitorService,
      closePreview: (...a: unknown[]) => closePreview(...a),
      closeClaim: (...a: unknown[]) => closeClaim(...a),
    },
  }
})

import { CloseModal } from '@/components/monitor/CloseModal'

function wrapper({ children }: { children: ReactNode }) {
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  })
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>
}

const PREVIEW_TWO_INDICATORS = {
  proposed_verdict: 'validated' as const,
  overall_score: 0.5,
  indicators: [
    { id: 'i1', name: '지표A', latest_value: 12.3 },
    { id: 'i2', name: '지표B', latest_value: null },
  ],
}

beforeEach(() => {
  closePreview.mockReset()
  closeClaim.mockReset()
})

describe('CloseModal', () => {
  it('close-preview의 proposed_verdict를 프리셀렉트한다', async () => {
    closePreview.mockResolvedValue(PREVIEW_TWO_INDICATORS)
    render(<CloseModal monitorId="m1" claimId="c1" onClose={vi.fn()} />, { wrapper })

    await waitFor(() =>
      expect(screen.getByTestId('close-modal-proposal-banner')).toHaveTextContent('적중')
    )
    expect(screen.getByTestId('close-modal-verdict-validated')).toHaveAttribute(
      'aria-pressed',
      'true'
    )
    expect(screen.getByTestId('close-modal-verdict-partial')).toHaveAttribute(
      'aria-pressed',
      'false'
    )
  })

  it('preview 로딩 중에는 제출 버튼이 존재하지 않는다(판정 없이 제출 불가)', async () => {
    let resolvePreview: (v: typeof PREVIEW_TWO_INDICATORS) => void = () => {}
    closePreview.mockReturnValue(
      new Promise((resolve) => {
        resolvePreview = resolve
      })
    )
    render(<CloseModal monitorId="m1" claimId="c1" onClose={vi.fn()} />, { wrapper })

    expect(screen.queryByTestId('close-modal-submit')).not.toBeInTheDocument()

    resolvePreview(PREVIEW_TWO_INDICATORS)
    await waitFor(() => expect(screen.getByTestId('close-modal-submit')).toBeInTheDocument())
    // 프리필로 verdict가 채워진 뒤에는 활성화된다.
    expect(screen.getByTestId('close-modal-submit')).not.toBeDisabled()
  })

  it('선택하지 않은 지표는 indicator_results에서 제외하고 제출한다', async () => {
    closePreview.mockResolvedValue(PREVIEW_TWO_INDICATORS)
    closeClaim.mockResolvedValue({ id: 'c1', outcome: 'validated' })
    const onClose = vi.fn()
    render(<CloseModal monitorId="m1" claimId="c1" onClose={onClose} />, { wrapper })

    await waitFor(() => expect(screen.getByTestId('close-modal-submit')).toBeInTheDocument())

    // i1만 'hit' 선택, i2는 미선택 상태로 둔다.
    fireEvent.click(screen.getByTestId('close-modal-indicator-i1-hit'))
    fireEvent.click(screen.getByTestId('close-modal-submit'))

    await waitFor(() => expect(closeClaim).toHaveBeenCalledTimes(1))
    const [claimId, payload] = closeClaim.mock.calls[0]
    expect(claimId).toBe('c1')
    expect(payload.final_verdict).toBe('validated')
    expect(payload.indicator_results).toEqual([{ indicator_id: 'i1', result: 'hit' }])
    await waitFor(() => expect(onClose).toHaveBeenCalled())
  })

  it('409 응답 시 이미 마감 안내를 보여주고 확인 클릭 시 닫는다', async () => {
    closePreview.mockResolvedValue(PREVIEW_TWO_INDICATORS)
    closeClaim.mockRejectedValue({ response: { status: 409 } })
    const onClose = vi.fn()
    render(<CloseModal monitorId="m1" claimId="c1" onClose={onClose} />, { wrapper })

    await waitFor(() => expect(screen.getByTestId('close-modal-submit')).toBeInTheDocument())
    fireEvent.click(screen.getByTestId('close-modal-submit'))

    await waitFor(() => expect(screen.getByText('이미 마감된 가설입니다.')).toBeInTheDocument())
    expect(onClose).not.toHaveBeenCalled()

    fireEvent.click(screen.getByTestId('close-modal-ack'))
    expect(onClose).toHaveBeenCalledTimes(1)
  })

  it('네트워크 오류 시 모달이 유지되고 인라인 에러를 보여준다', async () => {
    closePreview.mockResolvedValue(PREVIEW_TWO_INDICATORS)
    closeClaim.mockRejectedValue(new Error('network down'))
    const onClose = vi.fn()
    render(<CloseModal monitorId="m1" claimId="c1" onClose={onClose} />, { wrapper })

    await waitFor(() => expect(screen.getByTestId('close-modal-submit')).toBeInTheDocument())
    fireEvent.click(screen.getByTestId('close-modal-submit'))

    await waitFor(() => expect(screen.getByTestId('close-modal-error')).toBeInTheDocument())
    expect(onClose).not.toHaveBeenCalled()
    expect(screen.getByTestId('close-modal')).toBeInTheDocument()
  })
})
