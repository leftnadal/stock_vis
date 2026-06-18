/**
 * MP-UX-B3 — 다음 단계 전체 게이지(5지표 부호화 양방향) 회귀 테스트.
 *
 * 핵심 함정 봉인: op `<`/`>` 혼재가 BE to_threshold 단일축으로 방향 일관(아직=왼쪽).
 * 검증: ① op 혼재 방향 일관 ② 돌파(to_threshold<=0) 강조/오른쪽 ③ isClosest 강조만 1건
 *      ④ allNull "대기" 분기 회귀 0 ⑤ to_threshold null 행은 게이지 제외(요약 유지)
 */
import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import type { RegimeDetail as Detail } from '@/lib/api/marketPulseV2'
import { RegimeNextStage } from '@/app/market-pulse-v2/details/RegimeDetail'
import { NextStageGauge } from '@/app/market-pulse-v2/details/NextStageGauge'

const KO = {
  'regime.TRANSITION': '전환',
  'indicator.hy_oas': 'HY 스프레드',
  'indicator.vix': 'VIX (변동성)',
}

function detail(over: Partial<Detail>): Detail {
  return { available: true, next_stage: 'TRANSITION', margins: [], ...over }
}

function row(container: HTMLElement, indicator: string): HTMLElement {
  const el = container.querySelector(`li[data-indicator="${indicator}"]`)
  if (!el) throw new Error(`gauge row not found: ${indicator}`)
  return el as HTMLElement
}

describe('NextStageGauge (단일 행)', () => {
  it('op "<" (t10y2y)와 op ">" (vix) 모두 아직 → 같은 왼쪽 방향 (함정 봉인)', () => {
    const { container: c1 } = render(
      <ul>
        <NextStageGauge
          margin={{ indicator: 't10y2y_pct', op: '<', threshold: 0, actual: 0.4, to_threshold: 0.4 }}
          isClosest={false}
          nextStage="TRANSITION"
          scaleRef={7.32}
          indicatorLabel="t10y2y"
        />
      </ul>,
    )
    const { container: c2 } = render(
      <ul>
        <NextStageGauge
          margin={{ indicator: 'vix', op: '>=', threshold: 25, actual: 17.68, to_threshold: 7.32 }}
          isClosest={false}
          nextStage="TRANSITION"
          scaleRef={7.32}
          indicatorLabel="VIX"
        />
      </ul>,
    )
    // op 다르지만 to_threshold>0 → 둘 다 'left'(아직), breached=false
    expect(row(c1, 't10y2y_pct').dataset.direction).toBe('left')
    expect(row(c2, 'vix').dataset.direction).toBe('left')
    expect(row(c1, 't10y2y_pct').dataset.breached).toBe('false')
    expect(row(c2, 'vix').dataset.breached).toBe('false')
  })

  it('to_threshold <= 0 → 돌파(오른쪽 + 강조)', () => {
    const { container } = render(
      <ul>
        <NextStageGauge
          margin={{ indicator: 'nfci', op: '>', threshold: 0, actual: 0.2, to_threshold: -0.2 }}
          isClosest={false}
          nextStage="TRANSITION"
          scaleRef={1}
          indicatorLabel="NFCI"
        />
      </ul>,
    )
    const el = row(container, 'nfci')
    expect(el.dataset.breached).toBe('true')
    expect(el.dataset.direction).toBe('right')
    expect(screen.getByText('돌파')).toBeInTheDocument()
  })
})

describe('RegimeNextStage (5지표 전체 게이지)', () => {
  const fullMargins = detail({
    margins: [
      { indicator: 'hy_oas_pct', op: '>=', threshold: 3.5, actual: 2.71, to_threshold: 0.79 },
      { indicator: 'vix', op: '>=', threshold: 25, actual: 17.68, to_threshold: 7.32 },
      { indicator: 'nfci', op: '>', threshold: 0, actual: -0.506, to_threshold: 0.506 },
      { indicator: 't10y2y_pct', op: '<', threshold: 0, actual: 0.4, to_threshold: 0.4 },
      { indicator: 't10y3m_pct', op: '<', threshold: 0, actual: 0.68, to_threshold: 0.68 },
    ],
    next_stage_closest: { indicator: 't10y2y_pct', op: '<', threshold: 0, actual: 0.4, to_threshold: 0.4 },
  })

  it('margins 5지표 전부 게이지 렌더', () => {
    const { container } = render(<RegimeNextStage payload={fullMargins} labels={KO} />)
    expect(container.querySelectorAll('li[data-indicator]')).toHaveLength(5)
  })

  it('isClosest = next_stage_closest 지표만 강조(1건)', () => {
    const { container } = render(<RegimeNextStage payload={fullMargins} labels={KO} />)
    const closest = container.querySelectorAll('li[data-closest="true"]')
    expect(closest).toHaveLength(1)
    expect((closest[0] as HTMLElement).dataset.indicator).toBe('t10y2y_pct')
  })

  it('allNull → "수집 대기" 분기 유지(게이지 미렌더, 회귀 0)', () => {
    const { container } = render(
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
    expect(screen.getByText(/지표 데이터 수집 대기 중/)).toBeInTheDocument()
    expect(container.querySelectorAll('li[data-indicator]')).toHaveLength(0)
  })

  it('부분 데이터: to_threshold null 행은 게이지 제외(요약 라인은 유지)', () => {
    const { container } = render(
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
    // 게이지는 non-null 1건만, 요약 라인은 유지
    expect(container.querySelectorAll('li[data-indicator]')).toHaveLength(1)
    expect(screen.getByText(/가장 가까운 지표 HY 스프레드 0\.7 남음/)).toBeInTheDocument()
  })
})
