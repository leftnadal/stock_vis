/**
 * Slice 17 Part 4 — KeyObservationsSection 단위 테스트.
 *
 * 5 카드형 EP 공통(6 EP 전체 optional). 헤더 + 항목 리스트 + Target 아이콘 +
 * slate-700 색상 보존 검증. 조건부 미렌더는 호출처(CardSection visible) 책임.
 */

import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import KeyObservationsSection from '@/components/coach/KeyObservationsSection'

const SAMPLE = [
  'HHI 0.40 — 통상 0.25 이상은 집중도 주의 구간',
  'Tech 65% — 단일 섹터 충격 노출도 높음',
  'Top3 종목 80% — 분산 효과 제한적',
]

describe('KeyObservationsSection', () => {
  it('keyObservations 있을 때 헤더 + 각 항목 렌더', () => {
    render(<KeyObservationsSection keyObservations={SAMPLE} />)
    expect(screen.getByText('핵심 관찰')).toBeInTheDocument()
    for (const obs of SAMPLE) {
      expect(screen.getByText(obs)).toBeInTheDocument()
    }
  })

  it('빈 배열일 때도 헤더 + 빈 ul은 렌더 (가시성은 호출처 책임)', () => {
    const { container } = render(<KeyObservationsSection keyObservations={[]} />)
    expect(screen.getByText('핵심 관찰')).toBeInTheDocument()
    const ul = container.querySelector('ul')
    expect(ul).not.toBeNull()
    expect(ul!.children).toHaveLength(0)
  })

  it('SectionHeader Target 아이콘 보존 (h-4 w-4 text-blue-500)', () => {
    const { container } = render(<KeyObservationsSection keyObservations={[SAMPLE[0]]} />)
    const heading = container.querySelector('h3')
    expect(heading).not.toBeNull()
    const svg = heading!.querySelector('svg')
    expect(svg).not.toBeNull()
    expect(svg!.classList.toString()).toContain('text-blue-500')
  })

  it('본문 ul slate-700 색상 보존 (시각 회귀 0)', () => {
    const { container } = render(<KeyObservationsSection keyObservations={[SAMPLE[0]]} />)
    const ul = container.querySelector('ul')
    expect(ul).not.toBeNull()
    expect(ul!.className).toContain('text-slate-700')
  })
})
