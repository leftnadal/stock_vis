/**
 * PlaybookCard (1.6-S1) 렌더 테스트 — 상태별 점등·weekly 배지·pending 대기·부재.
 * FE 재판정 0(BE state 그대로)·색 토큰 재사용(신규 hex 0)을 렌더로 고정.
 */
import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import { PlaybookCard } from '@/app/market-pulse-v2/cards/PlaybookCard'
import type { PlaybookPayload } from '@/lib/api/marketPulseV2'

const PAYLOAD: PlaybookPayload = {
  chains: [
    { id: 'risk_off', name: '위험회피', narrative: '위험회피 국면', cadence: 'daily', lit_count: 3, total: 3, state: 'active', data_as_of: '2026-08-24' },
    { id: 'rate_shock', name: '금리충격', narrative: '금리 충격 국면', cadence: 'daily', lit_count: 1, total: 3, state: 'partial', data_as_of: '2026-08-20' },
    { id: 'curve_shift', name: '커브 전환', narrative: '커브 전환 국면', cadence: 'daily', lit_count: 0, total: 2, state: 'dormant', data_as_of: '2026-08-21' },
    { id: 'financial_tightening', name: '금융환경 긴축', narrative: '조임 진행 국면', cadence: 'weekly', lit_count: 0, total: 2, state: 'pending', data_as_of: '2026-08-14' },
  ],
  summary: { total: 4, total_lit: 1, top_chain: { id: 'risk_off', name: '위험회피' } },
}

describe('PlaybookCard', () => {
  it('active/partial/dormant = n/m 점등 필 + 상태색(stressAlert 토큰)', () => {
    render(<PlaybookCard data={PAYLOAD} />)
    expect(screen.getByTestId('playbook-pill-risk_off')).toHaveTextContent('3/3')
    expect(screen.getByTestId('playbook-pill-risk_off').className).toContain('rose') // active
    expect(screen.getByTestId('playbook-pill-rate_shock')).toHaveTextContent('1/3')
    expect(screen.getByTestId('playbook-pill-rate_shock').className).toContain('amber') // partial
    expect(screen.getByTestId('playbook-pill-curve_shift').className).toContain('slate') // dormant
  })

  it('pending = "데이터 대기"(오판정 렌더 금지)', () => {
    render(<PlaybookCard data={PAYLOAD} />)
    const pill = screen.getByTestId('playbook-pill-financial_tightening')
    expect(pill).toHaveTextContent('데이터 대기')
    expect(pill).not.toHaveTextContent('/') // n/m 미표시
  })

  it('weekly 체인 = 주간 배지 + 기준일(정직 표기)', () => {
    render(<PlaybookCard data={PAYLOAD} />)
    const badge = screen.getByTestId('playbook-weekly-financial_tightening')
    expect(badge).toHaveTextContent('주간')
    expect(badge).toHaveTextContent('08-14 기준')
    // daily 체인엔 weekly 배지 없음
    expect(screen.queryByTestId('playbook-weekly-risk_off')).not.toBeInTheDocument()
  })

  it('요약 줄 = N개 점등 + 최다 점등', () => {
    render(<PlaybookCard data={PAYLOAD} />)
    const s = screen.getByTestId('playbook-summary')
    expect(s).toHaveTextContent('4개 중 1개 점등')
    expect(s).toHaveTextContent('최다 점등 위험회피')
  })

  it('서사에 위기 프레이밍 없음(카피 게이트)', () => {
    render(<PlaybookCard data={PAYLOAD} />)
    expect(screen.queryByText(/위기/)).not.toBeInTheDocument()
  })

  it('부재 = 미생성 렌더', () => {
    render(<PlaybookCard data={null} />)
    expect(screen.getByText(/미생성/)).toBeInTheDocument()
  })
})
