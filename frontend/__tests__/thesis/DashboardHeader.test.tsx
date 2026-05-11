import { render, screen } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'
import { DashboardHeader } from '@/components/thesis/dashboard/DashboardHeader'
import type { DashboardThesis } from '@/lib/thesis/types'

vi.mock('next/navigation', () => ({
  useRouter: () => ({ push: vi.fn() }),
}))

function makeThesis(overrides: Partial<DashboardThesis> = {}): DashboardThesis {
  return {
    id: 'mock-1',
    title: 'AI 반도체 수요 증가로 NVIDIA 상승 지속',
    direction: 'bullish',
    status: 'active',
    days_active: 32,
    overall_score: 0.45,
    overall_label: '조금씩 밝아지고 있어요',
    overall_phase: 'waxing',
    recent_change: '외국인 순매수가 3일 연속 증가',
    overall_delta: null,
    ai_summary: 'AI 분석 요약',
    notable_changes: [],
    snapshot_date: '2026-03-18',
    ...overrides,
  }
}

describe('DashboardHeader', () => {
  it('가설 제목과 관제 일수를 렌더링한다', () => {
    render(<DashboardHeader thesis={makeThesis()} />)

    expect(screen.getByText('AI 반도체 수요 증가로 NVIDIA 상승 지속')).toBeInTheDocument()
    expect(screen.getByText('32일째 관제 중')).toBeInTheDocument()
  })

  it('score > 0.2이면 ThesisBadge가 strengthening 상태로 렌더링된다', () => {
    render(<DashboardHeader thesis={makeThesis({ overall_score: 0.5 })} />)

    // stateToDisplay('strengthening') → label: '지지 신호 증가'
    expect(screen.getByText('지지 신호 증가')).toBeInTheDocument()
  })

  it('score < -0.2이면 ThesisBadge가 weakening 상태로 렌더링된다', () => {
    render(<DashboardHeader thesis={makeThesis({ overall_score: -0.5 })} />)

    // stateToDisplay('weakening') → label: '반박 신호 증가'
    expect(screen.getByText('반박 신호 증가')).toBeInTheDocument()
  })

  it('score가 중립 범위면 ThesisBadge가 active 상태로 렌더링된다', () => {
    render(<DashboardHeader thesis={makeThesis({ overall_score: 0.0 })} />)

    // stateToDisplay('active') → label: '추적 중'
    expect(screen.getByText('추적 중')).toBeInTheDocument()
  })
})
