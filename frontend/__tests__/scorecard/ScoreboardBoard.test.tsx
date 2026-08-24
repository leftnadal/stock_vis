// D1-SCOREBOARD 3a — ScoreboardBoard (헤더 3카드 + 심볼 행 + 펼침 + 재현 각주).
import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it } from 'vitest'

import { ScoreboardBoard } from '@/components/scorecard/ScoreboardBoard'
import { scorecardFixture } from '@/lib/scorecard/fixtures'

describe('ScoreboardBoard', () => {
  it('헤더 카드·심볼 행·재현 각주를 렌더한다', () => {
    render(<ScoreboardBoard scorecard={scorecardFixture} />)
    // 헤더: 방향 적중률(1/2=50%), IC 사유
    expect(screen.getByTestId('scoreboard-board')).toHaveTextContent('방향 적중률')
    expect(screen.getByTestId('scoreboard-board')).toHaveTextContent('50.0%')
    expect(screen.getByTestId('scoreboard-board')).toHaveTextContent('횡단면 IC')
    // 심볼 행 4개
    expect(screen.getAllByTestId('symbol-row')).toHaveLength(4)
    // 재현 각주
    expect(screen.getByTestId('scorecard-reproduction')).toHaveTextContent('git abc1234')
    expect(screen.getByTestId('scorecard-reproduction')).toHaveTextContent('신호 139행')
  })

  it('심볼 펼치면 신호 카드가 나온다', async () => {
    const user = userEvent.setup()
    render(<ScoreboardBoard scorecard={scorecardFixture} />)
    // 펼치기 전 신호 미노출
    expect(screen.queryByTestId('symbol-signals-AAPL')).not.toBeInTheDocument()
    await user.click(screen.getByTestId('symbol-toggle-AAPL'))
    const panel = screen.getByTestId('symbol-signals-AAPL')
    // AAPL = 적중 1 + 대기 1 → 신호 카드 2
    expect(within(panel).getAllByTestId('signal-card')).toHaveLength(2)
  })

  it('채점 불가 심볼(NVDA)은 적중 —', () => {
    render(<ScoreboardBoard scorecard={scorecardFixture} />)
    const rows = screen.getAllByTestId('symbol-row')
    const nvda = rows.find((r) => within(r).queryByText('NVDA'))!
    expect(within(nvda).getByTestId('row-hit')).toHaveTextContent('—')
    expect(within(nvda).getByTestId('row-counts')).toHaveTextContent('불가 1')
  })
})
