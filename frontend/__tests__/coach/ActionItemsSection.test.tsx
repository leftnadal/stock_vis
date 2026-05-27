/**
 * Slice 17 Part 3 — ActionItemsSection 단위 테스트.
 *
 * Group A 첫 추출. 헤더 + actionItems 렌더 + priority 배지 3 단계 스타일 +
 * action_items 전용 응집 검증. 조건부 미렌더는 호출처(CardSection visible)
 * 책임이라 본 컴포넌트는 빈 배열에서도 ul 빈 채로 정상 렌더.
 */

import { render, screen, within } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import ActionItemsSection from '@/components/coach/ActionItemsSection'
import type { CommentaryActionItem } from '@/lib/coach/types'

const SAMPLE: CommentaryActionItem[] = [
  {
    title: 'AAPL 비중 축소',
    description: '60%에서 40%로 점진 리밸런싱.',
    priority: 'high',
    category: 'rebalance',
  },
  {
    title: '비-Tech 섹터 편입',
    description: 'Healthcare/Financial 1종 이상 추가.',
    priority: 'medium',
    category: 'rebalance',
  },
  {
    title: '장기 관찰',
    description: '분기 1회 점검.',
    priority: 'low',
    category: 'monitor',
  },
]

describe('ActionItemsSection', () => {
  it('actionItems 있을 때 헤더 + 각 항목 title/description 렌더', () => {
    render(<ActionItemsSection actionItems={SAMPLE} />)
    expect(screen.getByText('추천 액션')).toBeInTheDocument()
    expect(screen.getByText('AAPL 비중 축소')).toBeInTheDocument()
    expect(screen.getByText('60%에서 40%로 점진 리밸런싱.')).toBeInTheDocument()
    expect(screen.getByText('비-Tech 섹터 편입')).toBeInTheDocument()
    expect(screen.getByText('장기 관찰')).toBeInTheDocument()
  })

  it('priority 3 단계 라벨 (즉시 / 단기 / 장기) 렌더', () => {
    render(<ActionItemsSection actionItems={SAMPLE} />)
    expect(screen.getByText('즉시')).toBeInTheDocument()
    expect(screen.getByText('단기')).toBeInTheDocument()
    expect(screen.getByText('장기')).toBeInTheDocument()
  })

  it('priority high 배지 — 적색 스타일 (bg-red-50 text-red-700 border-red-200)', () => {
    render(<ActionItemsSection actionItems={[SAMPLE[0]]} />)
    const badge = screen.getByText('즉시')
    for (const cls of ['bg-red-50', 'text-red-700', 'border-red-200']) {
      expect(badge.className).toContain(cls)
    }
  })

  it('priority medium 배지 — 노란 스타일 (bg-yellow-50 text-yellow-700 border-yellow-200)', () => {
    render(<ActionItemsSection actionItems={[SAMPLE[1]]} />)
    const badge = screen.getByText('단기')
    for (const cls of ['bg-yellow-50', 'text-yellow-700', 'border-yellow-200']) {
      expect(badge.className).toContain(cls)
    }
  })

  it('priority low 배지 — 청색 스타일 (bg-blue-50 text-blue-700 border-blue-200)', () => {
    render(<ActionItemsSection actionItems={[SAMPLE[2]]} />)
    const badge = screen.getByText('장기')
    for (const cls of ['bg-blue-50', 'text-blue-700', 'border-blue-200']) {
      expect(badge.className).toContain(cls)
    }
  })

  it('빈 배열일 때도 헤더 + 빈 ul은 렌더 (가시성은 호출처 책임)', () => {
    const { container } = render(<ActionItemsSection actionItems={[]} />)
    expect(screen.getByText('추천 액션')).toBeInTheDocument()
    const ul = container.querySelector('ul')
    expect(ul).not.toBeNull()
    expect(ul!.children).toHaveLength(0)
  })

  it('SectionHeader ListChecks 아이콘 보존 (h-4 w-4 text-emerald-500)', () => {
    const { container } = render(<ActionItemsSection actionItems={[SAMPLE[0]]} />)
    const heading = container.querySelector('h3')
    expect(heading).not.toBeNull()
    const svg = heading!.querySelector('svg')
    expect(svg).not.toBeNull()
    expect(svg!.classList.toString()).toContain('text-emerald-500')
  })

  it('항목 본문 li가 priority 배지와 같은 컨테이너 안에 렌더 (시각 회귀 0)', () => {
    render(<ActionItemsSection actionItems={[SAMPLE[0]]} />)
    const li = screen.getByText('AAPL 비중 축소').closest('li')
    expect(li).not.toBeNull()
    expect(within(li as HTMLElement).getByText('즉시')).toBeInTheDocument()
    expect(within(li as HTMLElement).getByText('60%에서 40%로 점진 리밸런싱.')).toBeInTheDocument()
  })
})
