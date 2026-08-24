// D1-SCOREBOARD 3b — SignalCard (증거 바 + 판정 문장) 4 상태 렌더.
import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import { SignalCard } from '@/components/scorecard/SignalCard'
import { sigHit, sigMiss, sigNoTarget, sigPending, sigUnscoreable } from '@/lib/scorecard/fixtures'

describe('SignalCard', () => {
  it('적중: 문장 + 증거 바 3눈금', () => {
    render(<SignalCard signal={sigHit} />)
    expect(screen.getByTestId('signal-sentence')).toHaveTextContent('상승 전망 → +15.0% 상승 (적중)')
    expect(screen.getByTestId('evidence-bar')).toBeInTheDocument()
    expect(screen.getByTestId('evidence-mark-spot')).toBeInTheDocument()
    expect(screen.getByTestId('evidence-mark-close')).toBeInTheDocument()
    expect(screen.getByTestId('evidence-mark-target')).toBeInTheDocument()
  })

  it('빗나감: 반대 방향 문장', () => {
    render(<SignalCard signal={sigMiss} />)
    expect(screen.getByTestId('signal-sentence')).toHaveTextContent('하락 전망이었으나 +6.3% 상승')
    expect(screen.getByTestId('signal-verdict-chip')).toHaveTextContent('miss')
  })

  it('대기: 증거 바 없음, D-day 문장', () => {
    render(<SignalCard signal={sigPending} />)
    expect(screen.getByTestId('signal-sentence')).toHaveTextContent('만기 D-24 대기 중')
    expect(screen.queryByTestId('evidence-bar')).not.toBeInTheDocument()
  })

  it('채점 불가: 증거 바 없음, 사유 문장', () => {
    render(<SignalCard signal={sigUnscoreable} />)
    expect(screen.getByTestId('signal-sentence')).toHaveTextContent('분할')
    expect(screen.queryByTestId('evidence-bar')).not.toBeInTheDocument()
  })

  it('무목표가: 바 숨김(강등), 문장만', () => {
    render(<SignalCard signal={sigNoTarget} />)
    expect(screen.getByTestId('signal-sentence')).toHaveTextContent('목표가 미제시')
    expect(screen.queryByTestId('evidence-bar')).not.toBeInTheDocument()
  })
})
