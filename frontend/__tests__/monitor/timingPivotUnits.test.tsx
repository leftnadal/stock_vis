// TIMING-P2 단위 검증 — verdict 라벨 중앙화 · zone lib · 가격 사다리/칩.
import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import {
  MiniPriceLadder,
  PriceLadder,
  ZoneChip,
} from '@/components/monitor/PriceLadder'
import { priceVsEntryPct } from '@/lib/monitor/zone'
import { VERDICT_META, VERDICT_OPTIONS, verdictMeta } from '@/lib/monitor/verdictLabels'
import type { ZoneDisplay } from '@/types/monitor'

const ZD: ZoneDisplay = {
  zone: 'entry',
  label: '진입 구간',
  close: 95,
  boundaries: { stop: 90, entry: 100, approach_ceiling: 103, target: 120 },
}

describe('verdictLabels 중앙 모듈', () => {
  it('5종 라벨을 행동어로 매핑한다', () => {
    expect(VERDICT_META.validated.label).toBe('익절')
    expect(VERDICT_META.partial.label).toBe('부분 실현')
    expect(VERDICT_META.invalidated.label).toBe('손절')
    expect(VERDICT_META.expired.label).toBe('기한만료')
    expect(VERDICT_META.inconclusive.label).toBe('불명확')
  })

  it('verdictMeta는 미지값을 불명확으로 방어한다', () => {
    // @ts-expect-error 의도적 미지값
    expect(verdictMeta('bogus').label).toBe('불명확')
  })

  it('마감 선택지에 기한만료 포함(4종)', () => {
    const keys = VERDICT_OPTIONS.map((o) => o.key)
    expect(keys).toEqual(['validated', 'partial', 'invalidated', 'expired'])
  })
})

describe('zone lib', () => {
  it('priceVsEntryPct: 진입가 대비 %', () => {
    expect(priceVsEntryPct(ZD)).toBeCloseTo(-5, 5) // (95-100)/100
  })
  it('close 없으면 null', () => {
    expect(priceVsEntryPct({ ...ZD, close: null })).toBeNull()
  })
})

describe('ZoneChip', () => {
  it('zone 있으면 라벨 + % 렌더', () => {
    render(<ZoneChip zoneDisplay={ZD} />)
    const chip = screen.getByTestId('zone-chip')
    expect(chip).toHaveAttribute('data-zone', 'entry')
    expect(chip).toHaveTextContent('진입 구간')
    expect(chip).toHaveTextContent('-5.0%')
  })
  it('zone null이면 미표시', () => {
    render(<ZoneChip zoneDisplay={{ ...ZD, zone: null, label: null }} />)
    expect(screen.queryByTestId('zone-chip')).toBeNull()
  })
})

describe('MiniPriceLadder (카드 수평)', () => {
  it('5구간 밴드 + 마커 + 3틱 렌더', () => {
    render(<MiniPriceLadder zoneDisplay={ZD} />)
    expect(screen.getByTestId('mini-price-ladder')).toBeInTheDocument()
    expect(screen.getByTestId('mini-ladder-marker')).toBeInTheDocument()
    expect(screen.getByText(/손절 90/)).toBeInTheDocument()
    expect(screen.getByText(/목표 120/)).toBeInTheDocument()
  })
})

describe('PriceLadder (상세 수직)', () => {
  it('5밴드 + 경계값 + 활성 구간 렌더', () => {
    render(<PriceLadder zoneDisplay={ZD} />)
    expect(screen.getByTestId('price-ladder')).toBeInTheDocument()
    // 활성 밴드(entry)에 라벨·현재가
    expect(screen.getByTestId('ladder-band-entry')).toHaveTextContent('진입 구간')
    // 경계값 4종 노출
    expect(screen.getByText('접근 상한')).toBeInTheDocument()
    expect(screen.getByText('103')).toBeInTheDocument()
  })
})
