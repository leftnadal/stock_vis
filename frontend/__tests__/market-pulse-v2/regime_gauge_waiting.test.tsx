/**
 * MP-UX-S4 Part B — 다음 단계 게이지 "대기" 상태.
 *
 * 거시 데이터공백(margins.actual 전 null) → "수집 대기"만, 값/바 미렌더.
 * null→0/임의값 변환 0. 부분 데이터면 closest 1건만.
 */
import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import type { RegimeDetail as Detail } from '@/lib/api/marketPulseV2'
import { RegimeNextStage } from '@/app/market-pulse-v2/details/RegimeDetail'

const KO = { 'regime.TRANSITION': '전환', 'indicator.hy_oas': 'HY 스프레드' }

function detail(over: Partial<Detail>): Detail {
  return { available: true, next_stage: 'TRANSITION', margins: [], ...over }
}

describe('RegimeNextStage (게이지 대기)', () => {
  it('margins 전부 actual null → "지표 데이터 수집 대기 중" (값/바 없음)', () => {
    render(
      <RegimeNextStage
        payload={detail({
          margins: [
            { indicator: 'vix', op: '>=', threshold: 25, actual: null, to_threshold: null },
            { indicator: 'hy_oas_pct', op: '>=', threshold: 3.5, actual: null, to_threshold: null },
          ],
          next_stage_closest: null,
        })}
        labels={KO}
      />,
    )
    expect(screen.getByText(/전환 · 지표 데이터 수집 대기 중/)).toBeInTheDocument()
    // 숫자 값 미렌더 (대기 문구만)
    expect(screen.queryByText(/남음/)).not.toBeInTheDocument()
  })

  it('부분 데이터 → 가장 가까운 지표 1건만 (closest)', () => {
    render(
      <RegimeNextStage
        payload={detail({
          margins: [
            { indicator: 'hy_oas_pct', op: '>=', threshold: 3.5, actual: 2.8, to_threshold: 0.7 },
            { indicator: 'vix', op: '>=', threshold: 25, actual: null, to_threshold: null },
          ],
          next_stage_closest: { indicator: 'hy_oas_pct', op: '>=', threshold: 3.5, actual: 2.8, to_threshold: 0.7 },
        })}
        labels={KO}
      />,
    )
    expect(screen.getByText(/가장 가까운 지표 HY 스프레드 0\.7 남음/)).toBeInTheDocument()
    expect(screen.queryByText(/대기 중/)).not.toBeInTheDocument()
  })

  it('next_stage 없음(CRISIS 등) → 렌더 0', () => {
    const { container } = render(<RegimeNextStage payload={detail({ next_stage: null })} labels={KO} />)
    expect(container).toBeEmptyDOMElement()
  })
})
