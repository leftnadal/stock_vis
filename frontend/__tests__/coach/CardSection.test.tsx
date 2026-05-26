/**
 * Slice 17 Step 0 — CardSection 단위 테스트.
 *
 * 조건부 wrapper로 graceful 미렌더 로직을 컴포넌트 내부에 박는다.
 * visible=false면 children을 렌더하지 않는다 (실측 (c)-1 위험 방어 — 페이지로
 * 로직 분산 방지).
 */

import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import CardSection from '@/components/coach/CardSection'

describe('CardSection', () => {
  it('visible=true → children 렌더', () => {
    render(
      <CardSection visible>
        <p data-testid="child">콘텐츠</p>
      </CardSection>,
    )
    expect(screen.getByTestId('child')).toHaveTextContent('콘텐츠')
  })

  it('visible=false → null 반환 (children 미렌더)', () => {
    render(
      <CardSection visible={false}>
        <p data-testid="hidden">숨김</p>
      </CardSection>,
    )
    expect(screen.queryByTestId('hidden')).not.toBeInTheDocument()
  })

  it('className prop으로 외부 wrapper 클래스 부여', () => {
    const { container } = render(
      <CardSection visible className="mb-5">
        <span>x</span>
      </CardSection>,
    )
    const section = container.querySelector('section')
    expect(section).not.toBeNull()
    expect(section!.className).toContain('mb-5')
  })
})
