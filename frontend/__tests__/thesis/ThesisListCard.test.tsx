import { render, screen } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'
import { ThesisListCard } from '@/components/thesis/list/ThesisListCard'
import type { Thesis } from '@/lib/thesis/types'

vi.mock('next/navigation', () => ({
  useRouter: () => ({ push: vi.fn() }),
}))

function makeThesis(overrides: Partial<Thesis> = {}): Thesis {
  return {
    id: 'mock-1',
    title: 'AI 반도체 수요 증가로 NVIDIA 상승 지속',
    direction: 'bullish',
    target: 'NVDA',
    thesis_type: 'sector_trend',
    status: 'active',
    current_state: 'strengthening',
    current_score: 0.72,
    overall_label: '지지 신호 증가',
    created_at: '2025-03-01T09:00:00Z',
    closed_at: null,
    expected_timeframe: '2025-06-01',
    ai_summary: null,
    user: 1,
    entry_source: 'free_input',
    outcome: null,
    outcome_note: '',
    ...overrides,
  }
}

describe('ThesisListCard', () => {
  it('가설 제목과 타겟 심볼을 렌더링한다', () => {
    render(<ThesisListCard thesis={makeThesis()} />)

    expect(screen.getByText('AI 반도체 수요 증가로 NVIDIA 상승 지속')).toBeInTheDocument()
    expect(screen.getByText(/NVDA/)).toBeInTheDocument()
  })

  it('올바른 상세 페이지 링크를 생성한다', () => {
    render(<ThesisListCard thesis={makeThesis({ id: 'thesis-42' })} />)

    const link = screen.getByRole('link')
    expect(link).toHaveAttribute('href', '/thesis/thesis-42')
  })

  it('상태 배지가 올바른 라벨을 표시한다', () => {
    render(
      <ThesisListCard thesis={makeThesis({ current_state: 'critical' })} />,
    )

    // stateToDisplay('critical') → label: '주의 필요'
    expect(screen.getByText('주의 필요')).toBeInTheDocument()
  })

  it('target이 빈 문자열이면 심볼 없이 추적 일수만 표시한다', () => {
    render(
      <ThesisListCard thesis={makeThesis({ target: '' })} />,
    )

    // target이 비어있으면 'NVDA · ' 부분이 없어야 함
    expect(screen.queryByText(/NVDA/)).not.toBeInTheDocument()
    // 추적 일수는 여전히 표시
    expect(screen.getByText(/추적 중/)).toBeInTheDocument()
  })
})
