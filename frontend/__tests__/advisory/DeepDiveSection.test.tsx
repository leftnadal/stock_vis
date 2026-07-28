// 심층 진단 섹션 검증 (Slice 20b, Part E) — E1~E6 타일이 올바른 coach 라우트로 연결.
import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import { DeepDiveSection } from '@/components/advisory/DeepDiveSection'

describe('DeepDiveSection', () => {
  it('E1~E6 6개 타일을 /coach/eN 라우트로 연결(딥링크 파라미터 없음)', () => {
    render(<DeepDiveSection />)
    const routes = ['e1', 'e2', 'e3', 'e4', 'e5', 'e6']
    for (const e of routes) {
      const tile = screen.getByTestId(`deep-dive-tile-${e}`)
      expect(tile).toHaveAttribute('href', `/coach/${e}`)
      // 딥링크 쿼리파라미터 없음(D4 섹션만)
      expect(tile.getAttribute('href')).not.toContain('?')
    }
  })

  it('섹션 제목·설명을 렌더한다', () => {
    render(<DeepDiveSection />)
    expect(screen.getByTestId('deep-dive-section')).toHaveTextContent('심층 진단')
    expect(screen.getByText('집중도 분석')).toBeInTheDocument()
  })
})
