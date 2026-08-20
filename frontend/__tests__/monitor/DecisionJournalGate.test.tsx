// 결정 일지 게이트 (RECON-SWAP-0813 3-B, 불변 요소) — 1문장 입력 전 마감/재커밋 버튼 비활성.
// 입력 품질 검증(최소 글자수 등)은 하지 않는다(ADR §6) — 공백 아닌 1글자만으로도 활성화되어야 한다.
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import type { ReactNode } from 'react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

const listDecisionJournalEntries = vi.fn()
const createDecisionJournalEntry = vi.fn()

vi.mock('@/services/monitorService', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@/services/monitorService')>()
  return {
    ...actual,
    monitorService: {
      ...actual.monitorService,
      listDecisionJournalEntries: (...a: unknown[]) => listDecisionJournalEntries(...a),
      createDecisionJournalEntry: (...a: unknown[]) => createDecisionJournalEntry(...a),
    },
  }
})

import { DecisionJournalGate } from '@/components/monitor/duel/DecisionJournalGate'

function wrapper({ children }: { children: ReactNode }) {
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  })
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>
}

beforeEach(() => {
  listDecisionJournalEntries.mockReset()
  createDecisionJournalEntry.mockReset()
  listDecisionJournalEntries.mockResolvedValue([])
})

describe('DecisionJournalGate', () => {
  it('문장이 비어 있으면 마감·재커밋 버튼이 비활성이다', async () => {
    render(
      <DecisionJournalGate claimId="c1" onClosed={vi.fn()} onRecommitted={vi.fn()} />,
      { wrapper }
    )
    await waitFor(() => expect(screen.getByTestId('decision-journal-close-button')).toBeDisabled())
    expect(screen.getByTestId('decision-journal-recommit-button')).toBeDisabled()
  })

  it('문장을 입력하면 버튼이 활성화된다(최소 글자수 검증 없음)', async () => {
    render(
      <DecisionJournalGate claimId="c1" onClosed={vi.fn()} onRecommitted={vi.fn()} />,
      { wrapper }
    )
    fireEvent.change(screen.getByTestId('decision-journal-sentence'), { target: { value: 'ㅇ' } })
    expect(screen.getByTestId('decision-journal-close-button')).not.toBeDisabled()
    expect(screen.getByTestId('decision-journal-recommit-button')).not.toBeDisabled()
  })

  it('마감 클릭 시 kind=close로 기록하고 onClosed를 호출한다', async () => {
    createDecisionJournalEntry.mockResolvedValue({ id: 'j1' })
    const onClosed = vi.fn()
    render(
      <DecisionJournalGate claimId="c1" onClosed={onClosed} onRecommitted={vi.fn()} />,
      { wrapper }
    )
    fireEvent.change(screen.getByTestId('decision-journal-sentence'), {
      target: { value: '근거 소멸로 마감한다' },
    })
    fireEvent.click(screen.getByTestId('decision-journal-close-button'))

    await waitFor(() => expect(createDecisionJournalEntry).toHaveBeenCalledTimes(1))
    const [payload] = createDecisionJournalEntry.mock.calls[0]
    expect(payload).toMatchObject({ claim: 'c1', kind: 'close', sentence: '근거 소멸로 마감한다' })
    await waitFor(() => expect(onClosed).toHaveBeenCalledTimes(1))
  })

  it('재커밋 클릭 시 kind=recommit으로 기록하고 onRecommitted를 호출한다', async () => {
    createDecisionJournalEntry.mockResolvedValue({ id: 'j2' })
    const onRecommitted = vi.fn()
    render(
      <DecisionJournalGate claimId="c1" onClosed={vi.fn()} onRecommitted={onRecommitted} />,
      { wrapper }
    )
    fireEvent.change(screen.getByTestId('decision-journal-sentence'), {
      target: { value: '목표 상향 재도전' },
    })
    fireEvent.click(screen.getByTestId('decision-journal-recommit-button'))

    await waitFor(() => expect(createDecisionJournalEntry).toHaveBeenCalledTimes(1))
    const [payload] = createDecisionJournalEntry.mock.calls[0]
    expect(payload.kind).toBe('recommit')
    await waitFor(() => expect(onRecommitted).toHaveBeenCalledTimes(1))
  })
})
