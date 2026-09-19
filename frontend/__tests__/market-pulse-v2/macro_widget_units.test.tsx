/**
 * MACRO-FE1 — 거시 위젯의 단위·결측 회귀 가드.
 *
 * 두 가지 거짓말을 고정한다:
 *  ⑴ NFP 단위 — nfp_change는 FRED PAYEMS = 이미 천 명 단위인데 위젯이 /1000을 한 번 더
 *     나눠 162(=16.2만 명 증가)를 "+0K"로 보여줬다.
 *  ⑵ 결측을 하락으로 — `x && x >= 0` 검사는 값이 null일 때도 else로 떨어져
 *     "N/A"를 쓰면서 빨간 하락 화살표를 그렸다.
 *
 * 두 위젯은 v1 /market-pulse와 v2 허브가 함께 쓴다 — 여기가 깨지면 두 화면이 같이 거짓말한다.
 */
import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import EconomicIndicators from '@/components/macro/EconomicIndicators'
import GlobalMarketsCard from '@/components/macro/GlobalMarketsCard'
import type { GlobalMarketsDashboard, InflationDashboard } from '@/types/macro'

const econ = (nfp: number | null): InflationDashboard =>
  ({
    inflation: { cpi_yoy: 3.35, core_cpi_yoy: 2.45, pce_yoy: 3.7, fed_target: 2.0 },
    employment: { unemployment_rate: 4.1, nfp_change: nfp, initial_claims: 196000 },
    gdp: null,
  }) as unknown as InflationDashboard

const idx = (changePercent: number | null) => ({
  name: 'S&P 500 (SPY)',
  price: 762.6,
  change: 8.55,
  change_percent: changePercent,
  previous_close: 754.05,
})

const globalData = (changePercent: number | null): GlobalMarketsDashboard =>
  ({
    indices: { sp500: idx(changePercent), nasdaq: null, dow: null, russell2000: null },
    global_indices: {},
    sectors: {
      sectors: {
        XLK: { name: 'Technology', price: 1, change: 0, change_percent: changePercent },
      },
    },
    forex: {},
    commodities: {},
    dxy: null,
    vix: null,
  }) as unknown as GlobalMarketsDashboard

/**
 * lucide 아이콘은 클래스로 식별한다(svg에 testid가 없다).
 * ⚠ 범위를 좁히지 않으면 같은 카드의 물가·실업률 아이콘까지 잡힌다 — NFP 블록만 본다.
 */
const nfpBlock = (c: HTMLElement): HTMLElement => {
  const label = Array.from(c.querySelectorAll('span')).find(
    (s) => s.textContent === '비농업 고용 (NFP)',
  )
  expect(label, 'NFP 블록을 찾지 못했다').toBeTruthy()
  return label!.closest('div.rounded-lg') as HTMLElement
}
const upIcons = (c: HTMLElement) => c.querySelectorAll('svg.text-green-500')
const downIcons = (c: HTMLElement) => c.querySelectorAll('svg.text-red-500')

describe('EconomicIndicators — NFP 단위·결측 (MACRO-FE1)', () => {
  it('162(천 명)은 +162K로 보인다 — /1000 재나눗셈 없음', () => {
    render(<EconomicIndicators data={econ(162)} />)
    expect(screen.getByText('+162K')).toBeInTheDocument()
    // 회귀 방지: 이 값이 "+0K"로 보이던 것이 원래 결함이었다.
    expect(screen.queryByText('+0K')).toBeNull()
  })

  it('음수도 단위 그대로 — -50 → -50K', () => {
    render(<EconomicIndicators data={econ(-50)} />)
    expect(screen.getByText('-50K')).toBeInTheDocument()
  })

  it('0은 N/A가 아니라 0K — 결측과 실제 0을 가른다', () => {
    const { container } = render(<EconomicIndicators data={econ(0)} />)
    expect(screen.getByText('0K')).toBeInTheDocument()
    expect(screen.queryByText('N/A')).toBeNull()
    // 0은 방향이 없다 → NFP 블록에 상승·하락 아이콘 모두 없음
    const nfp = nfpBlock(container)
    expect(upIcons(nfp)).toHaveLength(0)
    expect(downIcons(nfp)).toHaveLength(0)
  })

  it('★결측은 N/A이고 하락 아이콘을 그리지 않는다', () => {
    const { container } = render(<EconomicIndicators data={econ(null)} />)
    expect(screen.getByText('N/A')).toBeInTheDocument()
    expect(downIcons(nfpBlock(container))).toHaveLength(0)
  })
})

describe('GlobalMarketsCard — 결측을 하락으로 읽지 않는다 (MACRO-FE1)', () => {
  it('★change_percent가 null이면 하락 아이콘이 없다', () => {
    const { container } = render(<GlobalMarketsCard data={globalData(null)} />)
    expect(screen.getAllByText('N/A').length).toBeGreaterThan(0)
    expect(downIcons(container)).toHaveLength(0)
  })

  it('양수면 상승 아이콘 + 초록', () => {
    const { container } = render(<GlobalMarketsCard data={globalData(1.13)} />)
    expect(screen.getAllByText('+1.13%').length).toBeGreaterThan(0)
    expect(upIcons(container).length).toBeGreaterThan(0)
  })

  it('음수면 하락 아이콘', () => {
    const { container } = render(<GlobalMarketsCard data={globalData(-0.4)} />)
    expect(screen.getAllByText('-0.40%').length).toBeGreaterThan(0)
    expect(downIcons(container).length).toBeGreaterThan(0)
  })

  it('★섹터 pill — change_percent가 null이면 빨간 pill이 아니다', () => {
    const { container } = render(<GlobalMarketsCard data={globalData(null)} />)
    const pill = Array.from(container.querySelectorAll('div')).find(
      (d) => d.className.includes('rounded-full') && d.textContent?.includes('Technology'),
    )
    expect(pill, '섹터 pill을 찾지 못했다').toBeTruthy()
    expect(pill!.className).not.toContain('bg-red-100')
    expect(pill!.className).toContain('bg-gray-100')
  })
})
