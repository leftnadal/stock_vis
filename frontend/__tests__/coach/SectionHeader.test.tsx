/**
 * Slice 17 Step 0 — SectionHeader 단위 테스트.
 *
 * (icon + h3 title) 패턴의 통합 컴포넌트. 5 섹션이 모두 동일 헤더 마크업을
 * 사용하도록 보장.
 */

import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import SectionHeader from '@/components/coach/SectionHeader'

describe('SectionHeader', () => {
  it('title 텍스트를 h3로 렌더', () => {
    render(<SectionHeader icon={<svg data-testid="icon" />} title="핵심 관찰" />)
    const heading = screen.getByRole('heading', { level: 3 })
    expect(heading).toHaveTextContent('핵심 관찰')
  })

  it('icon은 heading 내부에 함께 렌더', () => {
    render(<SectionHeader icon={<svg data-testid="my-icon" />} title="추천 액션" />)
    expect(screen.getByTestId('my-icon')).toBeInTheDocument()
    // heading 안에 icon이 들어가야 (semantic 보장)
    const heading = screen.getByRole('heading', { level: 3 })
    expect(heading).toContainElement(screen.getByTestId('my-icon'))
  })

  it('Tailwind 라벨 클래스 보존 (text-sm font-semibold text-slate-700)', () => {
    render(<SectionHeader icon={null} title="t" />)
    const heading = screen.getByRole('heading', { level: 3 })
    for (const cls of ['text-sm', 'font-semibold', 'text-slate-700']) {
      expect(heading.className).toContain(cls)
    }
  })
})
