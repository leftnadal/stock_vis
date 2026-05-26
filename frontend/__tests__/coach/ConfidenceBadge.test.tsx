/**
 * Slice 17 Step 0 — ConfidenceBadge 단위 테스트.
 *
 * 안 B 핵심 원자 컴포넌트. 3 confidence 라벨 + CONFIDENCE_STYLE 단일 소스
 * 일관성 검증.
 */

import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import ConfidenceBadge from '@/components/coach/ConfidenceBadge'
import { CONFIDENCE_STYLE } from '@/lib/coach/styles'

describe('ConfidenceBadge', () => {
  it('high — 라벨 "높음" + 녹색 스타일', () => {
    render(<ConfidenceBadge confidence="high" />)
    const badge = screen.getByTestId('confidence-badge')
    expect(badge).toHaveTextContent('신뢰도 높음')
    expect(badge.className).toContain(CONFIDENCE_STYLE.high.cls.split(' ')[0])
  })

  it('medium — 라벨 "보통" + 노란 스타일', () => {
    render(<ConfidenceBadge confidence="medium" />)
    expect(screen.getByTestId('confidence-badge')).toHaveTextContent('신뢰도 보통')
  })

  it('low — 라벨 "낮음" + 적색 스타일', () => {
    render(<ConfidenceBadge confidence="low" />)
    expect(screen.getByTestId('confidence-badge')).toHaveTextContent('신뢰도 낮음')
  })

  it('스타일 단일 소스 — styles.ts CONFIDENCE_STYLE에 정의된 클래스 그대로 사용', () => {
    render(<ConfidenceBadge confidence="high" />)
    const badge = screen.getByTestId('confidence-badge')
    // CONFIDENCE_STYLE.high.cls의 모든 클래스가 컴포넌트에 적용됐는지
    for (const cls of CONFIDENCE_STYLE.high.cls.split(' ')) {
      expect(badge.className).toContain(cls)
    }
  })
})
