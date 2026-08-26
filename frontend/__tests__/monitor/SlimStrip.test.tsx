// 슬림 스트립 (MON-DETAIL-P1 T1): 6토큰 · 손절여유 위험 강조(기존 신호 게이팅) · 펼침 localStorage.
import { fireEvent, render, screen, within } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { SlimStrip } from '@/components/monitor/SlimStrip'
import type { Claim, Monitor, MonitorIndicator, ZoneDisplay } from '@/types/monitor'

// PriceLadder는 스트립 대상 아님 — 스텁으로 격리.
vi.mock('@/components/monitor/PriceLadder', () => ({
  PriceLadder: () => <div data-testid="price-ladder-stub" />,
}))

function makeMonitor(o: Partial<Monitor> = {}): Monitor {
  return {
    id: 'm1',
    scope: 'stock',
    target_ref: 'AAPL',
    name: '애플',
    status: 'active',
    current_state: 'active',
    target_date_end: null,
    resolved_label: 'Apple (AAPL)',
    latest_score: 0.42,
    display: null,
    indicator_count: 1,
    indicator_coverage: null,
    next_deadline: '2026-09-01',
    has_claim: true,
    close_suggested: false,
    danger_streak: 0,
    created_at: '2026-07-01T00:00:00Z',
    updated_at: '2026-07-01T00:00:00Z',
    ...o,
  }
}

const zoneDisplay = {
  zone: 'entry',
  label: '보유',
  close: 110,
  boundaries: { stop: 90, entry: 100, approach_ceiling: 116, target: 120 },
  stop_distance_pct: 18.1818,
  pnl_pct: 10,
} as unknown as ZoneDisplay

function makeClaim(zd: ZoneDisplay | null): Claim {
  return { id: 'c1', monitor: 'm1', status: 'active', zone_display: zd } as unknown as Claim
}

const indicators = [
  { id: 'i1', name: 'EOD 종합' },
  { id: 'i2', name: '거래량비' },
] as unknown as MonitorIndicator[]

beforeEach(() => {
  window.localStorage.clear()
})

describe('SlimStrip', () => {
  it('6토큰이 모두 렌더된다', () => {
    render(
      <SlimStrip
        monitor={makeMonitor()}
        zoneClaim={makeClaim(zoneDisplay)}
        scoreDelta={0.03}
        indicators={indicators}
        latestValueById={new Map()}
      />
    )
    for (const t of [
      'token-state',
      'token-zone',
      'token-score',
      'token-stop-distance',
      'token-dday',
      'token-danger',
    ]) {
      expect(screen.getByTestId(t)).toBeInTheDocument()
    }
    expect(within(screen.getByTestId('token-stop-distance')).getByText('18.18%')).toBeInTheDocument()
    expect(screen.getByTestId('tracking-day')).toHaveTextContent('관제')
  })

  it('손절여유 위험 강조는 기존 신호(danger_streak)로만 게이팅', () => {
    // 위험 없음 → 적색 아님
    const { rerender } = render(
      <SlimStrip
        monitor={makeMonitor({ danger_streak: 0 })}
        zoneClaim={makeClaim(zoneDisplay)}
        scoreDelta={null}
        indicators={indicators}
        latestValueById={new Map()}
      />
    )
    expect(within(screen.getByTestId('token-stop-distance')).getByText('18.18%').className).not.toContain(
      'text-red-600'
    )
    // danger_streak>0 → 적색
    rerender(
      <SlimStrip
        monitor={makeMonitor({ danger_streak: 2 })}
        zoneClaim={makeClaim(zoneDisplay)}
        scoreDelta={null}
        indicators={indicators}
        latestValueById={new Map()}
      />
    )
    expect(within(screen.getByTestId('token-stop-distance')).getByText('18.18%').className).toContain(
      'text-red-600'
    )
  })

  it('신호 패널 토글 시 펼침 + localStorage 저장', () => {
    render(
      <SlimStrip
        monitor={makeMonitor()}
        zoneClaim={makeClaim(zoneDisplay)}
        scoreDelta={null}
        indicators={indicators}
        latestValueById={new Map([['i1', 0.5]])}
      />
    )
    // 접힘 기본
    expect(screen.queryByTestId('panel-signals')).not.toBeInTheDocument()
    fireEvent.click(screen.getByTestId('panel-toggle-signals'))
    expect(screen.getByTestId('panel-signals')).toBeInTheDocument()
    expect(window.localStorage.getItem('monitor-detail:panel:signals')).toBe('1')
  })

  it('zone_display 없으면 가격 패널 미표시 · 존 토큰 —', () => {
    render(
      <SlimStrip
        monitor={makeMonitor()}
        zoneClaim={makeClaim(null)}
        scoreDelta={null}
        indicators={indicators}
        latestValueById={new Map()}
      />
    )
    expect(screen.queryByTestId('panel-toggle-price')).not.toBeInTheDocument()
    expect(within(screen.getByTestId('token-zone')).getByText('—')).toBeInTheDocument()
  })

  it('MON-P2A T3: 점수 커버리지 접미(6/9) + 부분데이터 경고톤', () => {
    render(
      <SlimStrip
        monitor={makeMonitor({ indicator_coverage: { sufficient: 6, total: 9 } })}
        zoneClaim={makeClaim(zoneDisplay)}
        scoreDelta={null}
        indicators={indicators}
        latestValueById={new Map()}
      />
    )
    const c = screen.getByTestId('token-score-coverage')
    expect(c).toHaveTextContent('6/9')
    expect(c.className).toContain('text-amber-600') // sufficient<total → 경고톤
  })

  it('MON-P2B T1: scoreDelta=0은 무표시가 아니라 ·0.000으로 표시(중립색, ▲0.00 자기모순 제거)', () => {
    render(
      <SlimStrip
        monitor={makeMonitor()}
        zoneClaim={makeClaim(zoneDisplay)}
        scoreDelta={0}
        indicators={indicators}
        latestValueById={new Map()}
      />
    )
    const delta = screen.getByTestId('token-score-delta')
    expect(delta).toHaveTextContent('·0.000')
    expect(delta.className).not.toContain('text-green-600')
    expect(delta.className).not.toContain('text-red-600')
  })

  it('MON-P2A T3: 신호 패널에 부족 배지(sufficientById=false)', () => {
    render(
      <SlimStrip
        monitor={makeMonitor()}
        zoneClaim={makeClaim(zoneDisplay)}
        scoreDelta={null}
        indicators={indicators}
        latestValueById={new Map()}
        sufficientById={new Map([['i1', true], ['i2', false]])}
      />
    )
    fireEvent.click(screen.getByTestId('panel-toggle-signals'))
    // i2만 부족 배지 1개
    expect(screen.getAllByTestId('signal-insufficient-badge')).toHaveLength(1)
  })
})
