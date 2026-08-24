// D1-SCOREBOARD 3a — ScoreStrip (채점 N · 적중 요약 · 표본 라벨).
import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import { ScoreStrip } from '@/components/scorecard/ScoreStrip'
import { scorecardAllPending, scorecardFixture } from '@/lib/scorecard/fixtures'

describe('ScoreStrip', () => {
  it('채점 N·적중 요약·참고용 라벨을 표시한다', () => {
    render(<ScoreStrip board={scorecardFixture.board} />)
    expect(screen.getByTestId('strip-scored-n')).toHaveTextContent('4건')
    expect(screen.getByTestId('strip-hit-summary')).toHaveTextContent('1/2 · 50.0%')
    expect(screen.getByTestId('strip-sample-label')).toHaveTextContent('참고용 (표본 2/60)')
  })

  it('표본 0(전건 대기)이면 적중 요약 —', () => {
    render(<ScoreStrip board={scorecardAllPending.board} />)
    expect(screen.getByTestId('strip-scored-n')).toHaveTextContent('0건')
    expect(screen.getByTestId('strip-hit-summary')).toHaveTextContent('—')
  })
})
