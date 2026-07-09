// MonitorListCard 렌더 검증 (MON-P3-S1)
import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import { MonitorListCard } from '@/components/monitor/MonitorListCard'
import type { Monitor } from '@/types/monitor'

function makeMonitor(overrides: Partial<Monitor> = {}): Monitor {
  return {
    id: 'm1',
    scope: 'stock',
    target_ref: 'AAPL',
    name: '애플 감시',
    status: 'active',
    current_state: 'critical',
    target_date_end: null,
    resolved_label: 'Apple Inc. (AAPL)',
    latest_score: 0.5,
    indicator_count: 3,
    next_deadline: null,
    has_claim: false,
    created_at: '2026-07-01T00:00:00Z',
    updated_at: '2026-07-01T00:00:00Z',
    ...overrides,
  }
}

describe('MonitorListCard', () => {
  it('이름·상태 라벨·지표 수를 표시한다', () => {
    render(<MonitorListCard monitor={makeMonitor()} />)
    expect(screen.getByText('애플 감시')).toBeInTheDocument()
    expect(screen.getByText('주의 필요')).toBeInTheDocument() // critical → 위험 톤
    expect(screen.getByText('지표 3')).toBeInTheDocument()
    expect(screen.getByText('Apple Inc. (AAPL)')).toBeInTheDocument()
  })

  it('상세 링크로 연결된다', () => {
    render(<MonitorListCard monitor={makeMonitor({ id: 'abc' })} />)
    expect(screen.getByTestId('monitor-card')).toHaveAttribute('href', '/monitor/abc')
  })

  it('마감일이 있으면 D-day를 표시한다', () => {
    const d = new Date()
    d.setDate(d.getDate() + 3)
    const iso = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
    render(<MonitorListCard monitor={makeMonitor({ next_deadline: iso })} />)
    expect(screen.getByText('D-3')).toBeInTheDocument()
  })
})
