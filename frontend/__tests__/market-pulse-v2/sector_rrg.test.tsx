/**
 * MP2-SECTOR-CD Slice 3 — RRG 회전 맵 + 서브스크린 + CTA 테스트.
 *
 * RRGChart는 순수 SVG(react-query 무관) → 직접 렌더. 라우트 페이지는 훅 mock.
 * 핵심 규칙 검증: 기준선=서빙값(하드코딩 아님), 점 색=cd_state(좌표 재분류 금지), 꼬리 raw.
 */
import { fireEvent, render } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'

import type { SectorDetail as Detail, SectorRow } from '@/lib/api/marketPulseV2'
import { RRGChart } from '@/app/market-pulse-v2/details/RRGChart'
import { SectorCdPanel } from '@/app/market-pulse-v2/details/SectorCdPanel'

function row(
  symbol: string, rel: number, mom5: number, rank: number,
  cd_state: SectorRow['cd_state'], rel5: number | null = rel,
  cd_state_raw: SectorRow['cd_state_raw'] = cd_state,  // CD-READ: 기본 = cd_state(전환 아님).
): SectorRow {
  // CD-STAB A′: rel_strength_5d = RRG 점 x축(기본 = rel). 기존 rel_strength(1일)는 맥박.
  return {
    symbol, rel_strength: rel, rel_strength_5d: rel5,
    momentum_1d: 0, momentum_5d: mom5, momentum_20d: 0, flow_proxy: 0, rank, cd_state, cd_state_raw,
  }
}

// pts: [date, rel1d, mom5, rel5?] — rel5 기본 = rel1d. 꼬리 x = rel_strength_5d.
function hist(symbol: string, pts: [string, number, number, number?][]) {
  return {
    symbol,
    history: pts.map(([date, rel, m, rel5]) => ({
      date, rel_strength: rel, rel_strength_5d: rel5 ?? rel, rank: 1, momentum_5d: m,
    })),
  }
}

const LABELS: Record<string, string> = { 'sector.XLK': '기술', 'sector.XLE': '에너지' }

function mkPayload(over: Partial<Detail> = {}): Detail {
  return {
    available: true,
    date: '2026-07-09',
    cross_dispersion: 0.8,
    rotation_index: 1.5,
    cd_rel_strength_baseline: 0,
    cd_momentum_baseline: 0,
    sectors: [
      row('XLK', 0.8, 0.5, 1, 'leading_strengthening'),
      row('XLE', -0.6, -0.4, 2, 'lagging_deteriorating'),
    ],
    sector_history: [],
    ...over,
  }
}

const ROSE = '#f43f5e' // leading_strengthening
const SKY = '#0ea5e9' // lagging_deteriorating

describe('RRGChart — 기준선(서빙값)', () => {
  it('기준선 2축 data-value = 서빙 메타값(하드코딩 0 아님, S2 동형)', () => {
    const { getByTestId } = render(
      <RRGChart payload={mkPayload({ cd_rel_strength_baseline: 0.3, cd_momentum_baseline: 0.7 })} labels={LABELS} />,
    )
    expect(getByTestId('rrg-baseline-x').getAttribute('data-value')).toBe('0.3')
    expect(getByTestId('rrg-baseline-y').getAttribute('data-value')).toBe('0.7')
  })

  it('메타 미서빙 시 0 폴백(크래시 없음)', () => {
    const { getByTestId } = render(
      <RRGChart payload={mkPayload({ cd_rel_strength_baseline: undefined, cd_momentum_baseline: undefined })} />,
    )
    expect(getByTestId('rrg-baseline-x').getAttribute('data-value')).toBe('0')
  })
})

describe('RRGChart — 점 색 = 서빙 cd_state (재분류 금지)', () => {
  it('좌표가 다른 사분면이어도 색은 서빙 cd_state를 따른다(FE 재분류 없음)', () => {
    // XLK: 좌표(rel=-0.9, mom=-0.9)는 부진·악화(sky) 사분면이나 cd_state=leading_strengthening(rose)
    const payload = mkPayload({
      sectors: [row('XLK', -0.9, -0.9, 1, 'leading_strengthening')],
    })
    const { getByTestId } = render(<RRGChart payload={payload} labels={LABELS} />)
    // 좌표 재분류였다면 sky, 서빙 cd_state 소비면 rose
    expect(getByTestId('rrg-dot-XLK').getAttribute('fill')).toBe(ROSE)
  })

  it('11섹터 각 점 색 = cd_state 토큰', () => {
    const { getByTestId } = render(<RRGChart payload={mkPayload()} labels={LABELS} />)
    expect(getByTestId('rrg-dot-XLK').getAttribute('fill')).toBe(ROSE)
    expect(getByTestId('rrg-dot-XLE').getAttribute('fill')).toBe(SKY)
  })

  it('cd_state null → 유보 회색', () => {
    const payload = mkPayload({ sectors: [row('XLK', 0.1, 0.1, 1, null)] })
    const { getByTestId } = render(<RRGChart payload={payload} labels={LABELS} />)
    expect(getByTestId('rrg-dot-XLK').getAttribute('fill')).toBe('#cbd5e1')
  })
})

describe('RRGChart — 점 x축 = rel_strength_5d (CD-STAB A′, 구별값)', () => {
  it('x 좌표는 rel_strength_5d 순서를 따른다(1일 rel_strength 아님)', () => {
    // XLK: rel(1일)=+0.9, rel_5d=-0.9 / XLE: rel=-0.9, rel_5d=+0.9.
    //   5d 소비면 XLE가 XLK보다 오른쪽(cx 큼). 1일 소비였다면 반대.
    const payload = mkPayload({
      sectors: [
        row('XLK', 0.9, 0.5, 1, 'leading_strengthening', -0.9),
        row('XLE', -0.9, 0.5, 2, 'lagging_improving', 0.9),
      ],
    })
    const { getByTestId } = render(<RRGChart payload={payload} labels={LABELS} />)
    const cxK = Number(getByTestId('rrg-dot-XLK').getAttribute('cx'))
    const cxE = Number(getByTestId('rrg-dot-XLE').getAttribute('cx'))
    expect(cxE).toBeGreaterThan(cxK)  // rel_5d: XLE(+0.9) > XLK(-0.9)
  })

  it('rel_strength_5d null 섹터 → 점 미표시(판단 유보, 발명 0)', () => {
    const payload = mkPayload({ sectors: [row('XLK', 0.8, 0.5, 1, 'leading_strengthening', null)] })
    const { queryByTestId } = render(<RRGChart payload={payload} labels={LABELS} />)
    expect(queryByTestId('rrg-dot-XLK')).toBeNull()
  })
})

describe('RRGChart — 출발 섹터 하이라이트', () => {
  it('fromSymbol → 링 + 확대점(r=6)', () => {
    const { getByTestId, queryByTestId } = render(<RRGChart payload={mkPayload()} labels={LABELS} fromSymbol="XLK" />)
    expect(getByTestId('rrg-ring-XLK')).toBeInTheDocument()
    expect(getByTestId('rrg-dot-XLK').getAttribute('r')).toBe('6')
    // 비-출발 섹터는 링 없음 + r=4
    expect(queryByTestId('rrg-ring-XLE')).toBeNull()
    expect(getByTestId('rrg-dot-XLE').getAttribute('r')).toBe('4')
  })
})

describe('RRGChart — 변형 H (포커스 디폴트 · 전체 꼬리 토글 · 탭 전환)', () => {
  function twoSector(over: Partial<Detail> = {}) {
    return mkPayload({
      sectors: [
        row('XLK', 0.8, 0.5, 1, 'leading_strengthening'),
        row('XLE', -0.6, -0.4, 2, 'lagging_deteriorating'),
      ],
      sector_history: [
        hist('XLK', [['2026-07-08', 0.1, 0.1], ['2026-07-09', 0.2, 0.2]]),
        hist('XLE', [['2026-07-08', -0.1, -0.1], ['2026-07-09', -0.2, -0.2]]),
      ],
      ...over,
    })
  }

  it('포커스 디폴트: from 섹터만 꼬리 + 링, 나머지 꼬리 부재', () => {
    const { getByTestId, queryByTestId } = render(<RRGChart payload={twoSector()} labels={LABELS} fromSymbol="XLK" />)
    expect(getByTestId('rrg-trail-XLK')).toBeInTheDocument()
    expect(getByTestId('rrg-ring-XLK')).toBeInTheDocument()
    expect(queryByTestId('rrg-trail-XLE')).toBeNull()
  })

  it('전체 꼬리 토글 OFF→ON → 전 섹터 꼬리 렌더', () => {
    const { getByTestId, queryByTestId } = render(<RRGChart payload={twoSector()} labels={LABELS} fromSymbol="XLK" />)
    const toggle = getByTestId('rrg-trail-toggle')
    expect(toggle.getAttribute('aria-pressed')).toBe('false')
    expect(queryByTestId('rrg-trail-XLE')).toBeNull()
    fireEvent.click(toggle)
    expect(toggle.getAttribute('aria-pressed')).toBe('true')
    expect(getByTestId('rrg-trail-XLE')).toBeInTheDocument()
    expect(getByTestId('rrg-trail-XLK')).toBeInTheDocument()
  })

  it('점 탭 → 포커스 전환(꼬리·링 이동) + onFocusChange 호출', () => {
    const onFocus = vi.fn()
    const { getByTestId, queryByTestId } = render(
      <RRGChart payload={twoSector()} labels={LABELS} fromSymbol="XLK" onFocusChange={onFocus} />,
    )
    expect(getByTestId('rrg-ring-XLK')).toBeInTheDocument()
    fireEvent.click(getByTestId('rrg-dot-XLE'))
    expect(onFocus).toHaveBeenCalledWith('XLE')
    expect(getByTestId('rrg-ring-XLE')).toBeInTheDocument()
    expect(queryByTestId('rrg-ring-XLK')).toBeNull()
    expect(getByTestId('rrg-trail-XLE')).toBeInTheDocument()
    expect(queryByTestId('rrg-trail-XLK')).toBeNull()
  })

  it('확인 중(cd_state≠cd_state_raw) 포커스 → 점선 링 + ⏳ 라벨', () => {
    const trans = mkPayload({
      sectors: [row('XLK', 0.5, 0.5, 1, 'lagging_deteriorating', 0.5, 'leading_strengthening')],
    })
    const { getByTestId } = render(<RRGChart payload={trans} labels={LABELS} fromSymbol="XLK" />)
    expect(getByTestId('rrg-ring-XLK').getAttribute('stroke-dasharray')).toBeTruthy()
    expect(getByTestId('rrg-label-XLK').textContent).toContain('⏳')
  })

  it('평시(cd_state==cd_state_raw) 포커스 → 실선 링, ⏳ 없음(무영향)', () => {
    const { getByTestId } = render(<RRGChart payload={twoSector()} labels={LABELS} fromSymbol="XLK" />)
    expect(getByTestId('rrg-ring-XLK').getAttribute('stroke-dasharray')).toBeFalsy()
    expect(getByTestId('rrg-label-XLK').textContent ?? '').not.toContain('⏳')
  })
})

describe('RRGChart — 꼬리(5일, raw)', () => {
  it('7일 히스토리 → 최근 5점만 폴리라인', () => {
    const payload = mkPayload({
      sector_history: [
        hist('XLK', [
          ['2026-07-01', 0.1, 0.1], ['2026-07-02', 0.2, 0.2], ['2026-07-03', 0.3, 0.3],
          ['2026-07-04', 0.4, 0.4], ['2026-07-05', 0.5, 0.5], ['2026-07-06', 0.6, 0.6],
          ['2026-07-07', 0.7, 0.7],
        ]),
      ],
    })
    const { getByTestId } = render(<RRGChart payload={payload} labels={LABELS} />)
    const poly = getByTestId('rrg-trail-XLK').getAttribute('points') ?? ''
    expect(poly.trim().split(/\s+/)).toHaveLength(5) // 최근 5일
  })

  it('꼬리 색 = 현재 상태색(과거 점 재분류 없음)', () => {
    const payload = mkPayload({
      sectors: [row('XLK', 0.8, 0.5, 1, 'leading_strengthening')],
      sector_history: [hist('XLK', [['2026-07-08', -0.5, -0.5], ['2026-07-09', 0.8, 0.5]])],
    })
    const { getByTestId } = render(<RRGChart payload={payload} labels={LABELS} />)
    expect(getByTestId('rrg-trail-XLK').getAttribute('stroke')).toBe(ROSE) // 현재 cd_state 색
  })

  it('히스토리 2점 미만 → 폴리라인 미생성(발명 0)', () => {
    const payload = mkPayload({ sector_history: [hist('XLK', [['2026-07-09', 0.8, 0.5]])] })
    const { queryByTestId } = render(<RRGChart payload={payload} labels={LABELS} />)
    expect(queryByTestId('rrg-trail-XLK')).toBeNull()
  })
})

describe('SectorCdPanel — 회전 맵 CTA', () => {
  it('CTA 렌더 + 출발 섹터(rank-1) href', () => {
    const { getByTestId } = render(<SectorCdPanel payload={mkPayload()} labels={LABELS} />)
    const cta = getByTestId('rrg-cta')
    expect(cta).toBeInTheDocument()
    expect(cta.getAttribute('href')).toBe('/market-pulse-v2/rotation?from=XLK')
  })

  it('기존 판단 카드 회귀 — 미니맵·범례·행 유지', () => {
    const { getByTestId } = render(<SectorCdPanel payload={mkPayload()} labels={LABELS} />)
    expect(getByTestId('cd-minimap')).toBeInTheDocument()
    expect(getByTestId('cd-badge-XLK')).toBeInTheDocument()
  })
})
