/**
 * Slice 17 Part 4 P4-C — CommentaryCard 조합 통합 테스트.
 *
 * CommentaryCard는 P4-A 완료 시점에 순수 조립부(인라인 렌더 0). 본 테스트는
 * 조립부로서의 책임 — Section 배치 순서·optional 미렌더·BaseCard 헤더 위임 —을
 * 검증한다. 분할 누적 회귀 0의 최종 게이트.
 *
 * 시나리오:
 *   1. 4 Section 전부 데이터 보유 → 4 섹션 모두 렌더 + 배치 순서 보장
 *   2. E5형 (action_items + quoted_metrics + key_observations, risk_flags 없음)
 *      → RiskFlagsSection만 미렌더
 *   3. base only (E4Output 형태이나 카드 사용 가정) → BaseCard 헤더만
 *   4. action_items만 있는 경우 → ActionItemsSection만
 *   5. CommentaryCard testId='commentary-card' (BaseCard 노출 위임 확인)
 */

import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import CommentaryCard from '@/components/coach/CommentaryCard'
import type { CommentaryCardData } from '@/lib/coach/types'

const FULL: CommentaryCardData = {
  summary: '포트폴리오 종합 진단 요약',
  confidence: 'medium',
  key_observations: ['관찰 A', '관찰 B'],
  action_items: [
    {
      title: '액션 1',
      description: '설명 1',
      priority: 'high',
      category: 'rebalance',
    },
  ],
  quoted_metrics: { metric_x: 0.5, metric_y: '대형' },
  risk_flags: ['리스크 A'],
}

const E5_LIKE: CommentaryCardData = {
  summary: 'E5형 (risk_flags 없음)',
  confidence: 'high',
  key_observations: ['관찰 C'],
  action_items: [
    {
      title: '액션 2',
      description: '설명 2',
      priority: 'medium',
      category: 'monitor',
    },
  ],
  quoted_metrics: { dividend_yield: '3.45%' },
}

const BASE_ONLY: CommentaryCardData = {
  summary: 'base only',
  confidence: 'low',
}

describe('CommentaryCard — 조립부 통합 테스트', () => {
  it('testId="commentary-card" — BaseCard 노출 위임 확인', () => {
    render(<CommentaryCard output={BASE_ONLY} />)
    expect(screen.getByTestId('commentary-card')).toBeInTheDocument()
  })

  it('FULL — 4 Section 모두 렌더 + 헤더 + 신뢰도 배지', () => {
    render(<CommentaryCard output={FULL} />)
    // BaseCard 헤더
    expect(screen.getByText('포트폴리오 종합 진단 요약')).toBeInTheDocument()
    expect(screen.getByTestId('confidence-badge')).toBeInTheDocument()
    // 4 Section
    expect(screen.getByText('핵심 관찰')).toBeInTheDocument()
    expect(screen.getByText('추천 액션')).toBeInTheDocument()
    expect(screen.getByText('인용 지표')).toBeInTheDocument()
    expect(screen.getByText('리스크')).toBeInTheDocument()
    // 데이터 전달 확인
    expect(screen.getByText('관찰 A')).toBeInTheDocument()
    expect(screen.getByText('액션 1')).toBeInTheDocument()
    expect(screen.getByText('metric_x')).toBeInTheDocument()
    expect(screen.getByText('리스크 A')).toBeInTheDocument()
  })

  it('FULL — Section 배치 순서: KeyObservations → ActionItems → QuotedMetrics → RiskFlags', () => {
    render(<CommentaryCard output={FULL} />)
    // 4 섹션 헤더의 DOM 순서를 확인 (인라인 시점 순서 보존)
    const sectionTitles = ['핵심 관찰', '추천 액션', '인용 지표', '리스크']
    const headings = sectionTitles.map((t) => screen.getByText(t))
    for (let i = 1; i < headings.length; i++) {
      // DOCUMENT_POSITION_FOLLOWING (4): headings[i]가 headings[i-1]보다 뒤에
      expect(headings[i - 1].compareDocumentPosition(headings[i]) & 4).toBe(4)
    }
  })

  it('E5형 (risk_flags 없음) → RiskFlagsSection만 미렌더', () => {
    render(<CommentaryCard output={E5_LIKE} />)
    expect(screen.getByText('핵심 관찰')).toBeInTheDocument()
    expect(screen.getByText('추천 액션')).toBeInTheDocument()
    expect(screen.getByText('인용 지표')).toBeInTheDocument()
    expect(screen.queryByText('리스크')).not.toBeInTheDocument()
  })

  it('BASE_ONLY → BaseCard 헤더만, 4 섹션 모두 미렌더 (graceful)', () => {
    render(<CommentaryCard output={BASE_ONLY} />)
    expect(screen.getByText('base only')).toBeInTheDocument()
    expect(screen.getByTestId('confidence-badge')).toBeInTheDocument()
    expect(screen.queryByText('핵심 관찰')).not.toBeInTheDocument()
    expect(screen.queryByText('추천 액션')).not.toBeInTheDocument()
    expect(screen.queryByText('인용 지표')).not.toBeInTheDocument()
    expect(screen.queryByText('리스크')).not.toBeInTheDocument()
  })

  it('action_items만 있는 경우 → ActionItemsSection만 렌더', () => {
    const onlyActions: CommentaryCardData = {
      summary: 's',
      confidence: 'medium',
      action_items: [
        {
          title: '액션 단독',
          description: '설명',
          priority: 'low',
          category: null,
        },
      ],
    }
    render(<CommentaryCard output={onlyActions} />)
    expect(screen.getByText('추천 액션')).toBeInTheDocument()
    expect(screen.getByText('액션 단독')).toBeInTheDocument()
    expect(screen.queryByText('핵심 관찰')).not.toBeInTheDocument()
    expect(screen.queryByText('인용 지표')).not.toBeInTheDocument()
    expect(screen.queryByText('리스크')).not.toBeInTheDocument()
  })
})
