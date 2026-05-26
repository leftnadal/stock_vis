/**
 * Slice 17 Step 0 — BaseCard 단위 테스트.
 *
 * 5 카드형 EP 골격. testId='commentary-card' 노출(기존 5 화면 테스트 호환),
 * summary + ConfidenceBadge 헤더 + children 슬롯 검증.
 */

import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import BaseCard from '@/components/coach/BaseCard'

describe('BaseCard', () => {
  it('testId commentary-card 노출 — 기존 5 화면 테스트와 호환', () => {
    render(<BaseCard summary="요약" confidence="medium" />)
    expect(screen.getByTestId('commentary-card')).toBeInTheDocument()
  })

  it('summary + 진단 요약 라벨 렌더', () => {
    render(<BaseCard summary="포트폴리오 양호" confidence="high" />)
    expect(screen.getByText('진단 요약')).toBeInTheDocument()
    expect(screen.getByText('포트폴리오 양호')).toBeInTheDocument()
  })

  it('confidence ConfidenceBadge 헤더에 노출', () => {
    render(<BaseCard summary="s" confidence="low" />)
    const badge = screen.getByTestId('confidence-badge')
    expect(badge).toHaveTextContent('신뢰도 낮음')
  })

  it('children 슬롯에 임의 콘텐츠 렌더', () => {
    render(
      <BaseCard summary="s" confidence="medium">
        <div data-testid="child-content">EP 섹션</div>
      </BaseCard>,
    )
    expect(screen.getByTestId('child-content')).toHaveTextContent('EP 섹션')
  })

  it('children 미전달 시에도 카드 골격은 정상 렌더', () => {
    render(<BaseCard summary="s" confidence="medium" />)
    expect(screen.getByTestId('commentary-card')).toBeInTheDocument()
    expect(screen.getByTestId('confidence-badge')).toBeInTheDocument()
  })
})
