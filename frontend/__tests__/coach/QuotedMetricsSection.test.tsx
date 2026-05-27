/**
 * Slice 17 Part 2 — QuotedMetricsSection 단위 테스트.
 *
 * Group B 첫 추출 컴포넌트. 헤더 + entries 렌더 + formatQuotedMetricValue
 * 값 포맷 검증. 조건부 미렌더는 호출처(CardSection visible) 책임이라 본
 * 컴포넌트는 빈 객체에서도 dl 빈 채로 정상 렌더.
 */

import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import QuotedMetricsSection, {
  formatQuotedMetricValue,
} from '@/components/coach/QuotedMetricsSection'

describe('QuotedMetricsSection', () => {
  it('entries 있을 때 헤더 + key/value 리스트 렌더', () => {
    render(
      <QuotedMetricsSection
        quotedMetrics={{ dividend_yield: '3.45%', beta: 1.12, tech_weight: 0.65 }}
      />,
    )
    expect(screen.getByText('인용 지표')).toBeInTheDocument()
    expect(screen.getByText('dividend_yield')).toBeInTheDocument()
    expect(screen.getByText('3.45%')).toBeInTheDocument()
    expect(screen.getByText('beta')).toBeInTheDocument()
    expect(screen.getByText('1.12')).toBeInTheDocument()
    expect(screen.getByText('tech_weight')).toBeInTheDocument()
    // formatQuotedMetricValue: 정수 아닌 number는 toFixed(2)
    expect(screen.getByText('0.65')).toBeInTheDocument()
  })

  it('빈 객체일 때도 dl과 헤더는 렌더 (가시성은 호출처 책임)', () => {
    const { container } = render(<QuotedMetricsSection quotedMetrics={{}} />)
    expect(screen.getByText('인용 지표')).toBeInTheDocument()
    const dl = container.querySelector('dl')
    expect(dl).not.toBeNull()
    expect(dl!.children).toHaveLength(0)
  })

  it('SectionHeader BarChart3 아이콘 보존 (h-4 w-4 text-indigo-500)', () => {
    const { container } = render(
      <QuotedMetricsSection quotedMetrics={{ x: 1 }} />,
    )
    const heading = container.querySelector('h3')
    expect(heading).not.toBeNull()
    // SectionHeader가 icon prop으로 받은 svg
    const svg = heading!.querySelector('svg')
    expect(svg).not.toBeNull()
    expect(svg!.classList.toString()).toContain('text-indigo-500')
  })
})

describe('formatQuotedMetricValue', () => {
  it('null/undefined → "-"', () => {
    expect(formatQuotedMetricValue(null)).toBe('-')
    expect(formatQuotedMetricValue(undefined)).toBe('-')
  })

  it('정수 number → 그대로 문자열', () => {
    expect(formatQuotedMetricValue(42)).toBe('42')
    expect(formatQuotedMetricValue(0)).toBe('0')
  })

  it('실수 number → toFixed(2)', () => {
    expect(formatQuotedMetricValue(3.14159)).toBe('3.14')
    expect(formatQuotedMetricValue(0.6)).toBe('0.60')
  })

  it('string / boolean → String()', () => {
    expect(formatQuotedMetricValue('3.45%')).toBe('3.45%')
    expect(formatQuotedMetricValue(true)).toBe('true')
    expect(formatQuotedMetricValue(false)).toBe('false')
  })

  it('object 등 기타 → JSON.stringify', () => {
    expect(formatQuotedMetricValue({ a: 1 })).toBe('{"a":1}')
    expect(formatQuotedMetricValue([1, 2])).toBe('[1,2]')
  })
})
