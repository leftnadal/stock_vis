/**
 * Slice 17 Part 3 — RiskFlagsSection 단위 테스트.
 *
 * Group A 두 번째 추출. 헤더 + 항목 리스트 + amber 색상 보존 검증. 조건부
 * 미렌더는 호출처(CardSection visible) 책임이라 본 컴포넌트는 빈 배열에서도
 * ul 빈 채로 정상 렌더.
 */

import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import RiskFlagsSection from '@/components/coach/RiskFlagsSection'

const SAMPLE = [
  '단일 종목 집중도 60% — 충격 시 30%+ 손실 위험',
  'Tech 섹터 100% — 금리·규제 위험 동시 노출',
]

describe('RiskFlagsSection', () => {
  it('riskFlags 있을 때 헤더 + 각 항목 렌더', () => {
    render(<RiskFlagsSection riskFlags={SAMPLE} />)
    expect(screen.getByText('리스크')).toBeInTheDocument()
    expect(
      screen.getByText('단일 종목 집중도 60% — 충격 시 30%+ 손실 위험'),
    ).toBeInTheDocument()
    expect(
      screen.getByText('Tech 섹터 100% — 금리·규제 위험 동시 노출'),
    ).toBeInTheDocument()
  })

  it('빈 배열일 때도 헤더 + 빈 ul은 렌더 (가시성은 호출처 책임)', () => {
    const { container } = render(<RiskFlagsSection riskFlags={[]} />)
    expect(screen.getByText('리스크')).toBeInTheDocument()
    const ul = container.querySelector('ul')
    expect(ul).not.toBeNull()
    expect(ul!.children).toHaveLength(0)
  })

  it('SectionHeader AlertTriangle 아이콘 보존 (h-4 w-4 text-amber-500)', () => {
    const { container } = render(<RiskFlagsSection riskFlags={[SAMPLE[0]]} />)
    const heading = container.querySelector('h3')
    expect(heading).not.toBeNull()
    const svg = heading!.querySelector('svg')
    expect(svg).not.toBeNull()
    expect(svg!.classList.toString()).toContain('text-amber-500')
  })

  it('본문 ul amber-800 색상 보존 (시각 회귀 0)', () => {
    const { container } = render(<RiskFlagsSection riskFlags={[SAMPLE[0]]} />)
    const ul = container.querySelector('ul')
    expect(ul).not.toBeNull()
    expect(ul!.className).toContain('text-amber-800')
  })
})
