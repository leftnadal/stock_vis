/**
 * MP-UX-S5-B (slice 2b) — 섹터 인라인 스파크라인 회귀 테스트.
 *
 * 검증:
 *   1. SectorSparkline: 다점 → polyline, 빈 → "—", 1점 graceful, 30점(cap) 정상
 *      (29 등 임의 일수 하드코딩 없음 — history.length 가변)
 *   2. SectorDetail 통합: sector_history 11섹터 전부 렌더(FE 절단 0),
 *      rank순 결합, KO 라벨 노출(심볼 fallback 아님)
 */
import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import type {
  SectorDetail as Detail,
  SectorHistory,
  SectorRow,
} from '@/lib/api/marketPulseV2'
import { SectorSparkline } from '@/app/market-pulse-v2/details/SectorSparkline'
import { SectorDetail } from '@/app/market-pulse-v2/details/SectorDetail'

function entry(symbol: string, rels: number[], startDay = 1): SectorHistory {
  return {
    symbol,
    history: rels.map((r, i) => ({ date: `2026-06-${String(startDay + i).padStart(2, '0')}`, rel_strength: r })),
  }
}

function row(symbol: string, rel: number, rank: number): SectorRow {
  return { symbol, rel_strength: rel, momentum_1d: 0, momentum_5d: 0, momentum_20d: 0, flow_proxy: 0, rank }
}

const SECTOR_LABELS: Record<string, string> = {
  'sector.XLK': '기술',
  'sector.XLE': '에너지',
  'sector.XLF': '금융',
}

describe('SectorSparkline', () => {
  it('다점 시계열 → polyline + 마지막점 강조', () => {
    const { container } = render(<SectorSparkline entry={entry('XLK', [0.5, 1.0, 1.8])} />)
    const line = container.querySelector('polyline')
    expect(line).not.toBeNull()
    expect(line!.getAttribute('points')!.split(' ')).toHaveLength(3)
    expect(container.querySelector('circle')).not.toBeNull()
  })

  it('빈 history → "—" graceful(polyline 미생성, 합성 0)', () => {
    const { container } = render(<SectorSparkline entry={entry('XLRE', [])} />)
    expect(screen.getByText('—')).toBeInTheDocument()
    expect(container.querySelector('polyline')).toBeNull()
  })

  it('1점 → 크래시 없이 렌더(polyline 없이 점만)', () => {
    const { container } = render(<SectorSparkline entry={entry('XLE', [-1.2])} />)
    expect(container.querySelector('circle')).not.toBeNull()
    expect(container.querySelector('polyline')).toBeNull()
  })

  it('30점(cap) → 정상 렌더 (29 하드코딩 없음, 가변 길이)', () => {
    const rels = Array.from({ length: 30 }, (_, i) => i * 0.1 - 1.5)
    const { container } = render(<SectorSparkline entry={entry('XLK', rels)} />)
    expect(container.querySelector('polyline')!.getAttribute('points')!.split(' ')).toHaveLength(30)
  })
})

describe('SectorDetail — 인라인 스파크라인 통합', () => {
  const payload: Detail = {
    available: true,
    date: '2026-06-11',
    cross_dispersion: 0.8,
    rotation_index: 1.5,
    sectors: [row('XLK', 1.8, 1), row('XLE', -1.2, 2), row('XLF', 0.3, 3)],
    sector_history: [
      entry('XLK', [0.5, 1.0, 1.8]), // rank1
      entry('XLE', [-0.4, -1.2]), // rank2
      entry('XLF', []), // rank3, 데이터 없음 → graceful
    ],
  }

  it('sector_history 전부 렌더(FE 절단 0) + rank순 결합', () => {
    const { container } = render(<SectorDetail payload={payload} labels={SECTOR_LABELS} />)
    const items = container.querySelectorAll('ul > li')
    expect(items).toHaveLength(3)
    // rank순: XLK(기술) → XLE(에너지) → XLF(금융)
    expect(items[0].textContent).toContain('기술')
    expect(items[1].textContent).toContain('에너지')
    expect(items[2].textContent).toContain('금융')
  })

  it('KO 라벨 노출 (심볼 fallback 아님)', () => {
    render(<SectorDetail payload={payload} labels={SECTOR_LABELS} />)
    expect(screen.getByText('기술')).toBeInTheDocument()
    expect(screen.queryByText('XLK')).toBeNull()
  })

  it('sector_history 없으면 인라인 섹션 미렌더(additive)', () => {
    const { container } = render(
      <SectorDetail payload={{ ...payload, sector_history: undefined }} labels={SECTOR_LABELS} />,
    )
    expect(container.querySelector('ul > li')).toBeNull()
  })
})
