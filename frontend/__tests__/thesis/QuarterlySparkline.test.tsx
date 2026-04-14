import { render, screen, fireEvent } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'
import { QuarterlySparkline } from '@/components/thesis/dashboard/QuarterlySparkline'
import type { QuarterlyPoint } from '@/lib/thesis/types'

vi.mock('next/navigation', () => ({
  useRouter: () => ({ push: vi.fn() }),
}))

const SAMPLE_HISTORY: QuarterlyPoint[] = [
  { fy: 2025, fq: 1, value: 100 },
  { fy: 2025, fq: 2, value: 150 },
  { fy: 2025, fq: 3, value: 120 },
  { fy: 2025, fq: 4, value: 200 },
]

describe('QuarterlySparkline', () => {
  it('각 분기 라벨(Q1~Q4)을 렌더링한다', () => {
    render(<QuarterlySparkline history={SAMPLE_HISTORY} />)

    expect(screen.getByText('Q1')).toBeInTheDocument()
    expect(screen.getByText('Q2')).toBeInTheDocument()
    expect(screen.getByText('Q3')).toBeInTheDocument()
    expect(screen.getByText('Q4')).toBeInTheDocument()
  })

  it('빈 배열이면 아무것도 렌더링하지 않는다', () => {
    const { container } = render(<QuarterlySparkline history={[]} />)
    expect(container.innerHTML).toBe('')
  })

  it('history가 undefined면 아무것도 렌더링하지 않는다', () => {
    const { container } = render(
      // @ts-expect-error: 의도적으로 undefined 전달하여 방어 로직 테스트
      <QuarterlySparkline history={undefined} />,
    )
    expect(container.innerHTML).toBe('')
  })

  it('마우스 호버 시 툴팁에 값을 표시한다', () => {
    render(<QuarterlySparkline history={SAMPLE_HISTORY} unit="%" />)

    // Q2 바에 호버
    const q2Bar = screen.getByText('Q2').parentElement!
    fireEvent.mouseEnter(q2Bar)

    // 툴팁: "Q2 2025: 150.0%"
    expect(screen.getByText(/Q2 2025: 150\.0%/)).toBeInTheDocument()

    // 마우스 떠나면 툴팁 사라짐
    fireEvent.mouseLeave(q2Bar)
    expect(screen.queryByText(/Q2 2025: 150\.0%/)).not.toBeInTheDocument()
  })
})
