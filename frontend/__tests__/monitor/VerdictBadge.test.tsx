// VerdictBadge 4상태 매핑 검증 (MON-CLOSE-UI Phase 2)
import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import { VerdictBadge } from '@/components/monitor/VerdictBadge'
import type { Verdict } from '@/types/monitor'

const EXPECTED: Record<Verdict, string> = {
  validated: '익절',
  partial: '부분 실현',
  invalidated: '손절',
  expired: '기한만료',
  inconclusive: '불명확',
}

describe('VerdictBadge', () => {
  it.each(Object.entries(EXPECTED) as [Verdict, string][])(
    '%s → "%s" 라벨과 data-verdict 속성을 렌더한다',
    (verdict, label) => {
      render(<VerdictBadge verdict={verdict} />)
      const badge = screen.getByTestId('verdict-badge')
      expect(badge).toHaveTextContent(label)
      expect(badge).toHaveAttribute('data-verdict', verdict)
    }
  )

  it('validated는 green 계열, invalidated는 red 계열 클래스를 사용한다(색 구분)', () => {
    const { rerender } = render(<VerdictBadge verdict="validated" />)
    expect(screen.getByTestId('verdict-badge').className).toContain('green')

    rerender(<VerdictBadge verdict="invalidated" />)
    expect(screen.getByTestId('verdict-badge').className).toContain('red')

    rerender(<VerdictBadge verdict="partial" />)
    expect(screen.getByTestId('verdict-badge').className).toMatch(/yellow|amber/)

    rerender(<VerdictBadge verdict="inconclusive" />)
    expect(screen.getByTestId('verdict-badge').className).toContain('gray')
  })
})
