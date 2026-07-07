/**
 * MP-UX-BREADTH-BAND — 시장 폭 의미밴드 회귀 테스트.
 *
 * 검증: ① 강세/중립/약세 대표 입력 → 밴드·톤 ② 엇갈림 댐핑(내부신호 반대) 결정적 분기
 *      ③ 경계값 deterministic ④ 데이터 없음 → null ⑤ 카드 raw 숫자 회귀 0(밴드 additive)
 * 임계 = 0.5 중심 + sectorFlow epsilon 0.1 관례(TUNE, STEP 0 실분포 부족 — 발명 아님).
 */
import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import type { BreadthCard } from '@/lib/api/marketPulseV2'
import { breadthBand, BREADTH_THRESHOLDS } from '@/app/market-pulse-v2/meaning'
import { BreadthCardSummary } from '@/app/market-pulse-v2/cards/BreadthCardSummary'

function inp(over: Partial<BreadthCard>): BreadthCard {
  return {
    universe: 'SPY', advance: 0, decline: 0, unchanged: 0, total: 0,
    new_high_52w: 0, new_low_52w: 0, ad_line: 0, ad_line_change: 0, ...over,
  }
}

const KO = {
  'breadth.broad_strength': '광범위한 강세',
  'breadth.neutral': '중립·혼조',
  'breadth.broad_weakness': '광범위한 약세',
  'breadth.cue.high_lead': '신고가 우위',
}

describe('breadthBand', () => {
  it('광범위한 강세 (ratio≥0.70) → broad_strength', () => {
    const r = breadthBand(inp({ advance: 382, decline: 118, new_high_52w: 45, new_low_52w: 12, ad_line_change: 3 }))
    expect(r?.band).toBe('broad_strength')
    expect(r?.tone).toContain('rose') // 강세=긍정=rose(COLOR-STAGE2 한국축)
  })

  it('중립 (ratio 0.50) → neutral', () => {
    const r = breadthBand(inp({ advance: 250, decline: 250 }))
    expect(r?.band).toBe('neutral')
    expect(r?.tone).toContain('slate')
  })

  it('광범위한 약세 (ratio≤0.30) → broad_weakness', () => {
    const r = breadthBand(inp({ advance: 120, decline: 380, new_high_52w: 8, new_low_52w: 50, ad_line_change: -4 }))
    expect(r?.band).toBe('broad_weakness')
    expect(r?.tone).toContain('sky') // 약세=부정=sky(COLOR-STAGE2 한국축)
  })

  it('엇갈림 댐핑: 등락 강세(0.62)인데 신저가 우위+AD↓ → strength→neutral (1단계 ↓)', () => {
    // ratio 0.62 = strength(idx3). 내부 반대(hl<0, ad<0) → idx2 = neutral
    const r = breadthBand(inp({ advance: 310, decline: 190, new_high_52w: 5, new_low_52w: 40, ad_line_change: -2 }))
    expect(r?.band).toBe('neutral')
  })

  it('엇갈림 없으면 댐핑 안 함: 강세(0.62)+신고가 우위+AD↑ → strength 유지', () => {
    const r = breadthBand(inp({ advance: 310, decline: 190, new_high_52w: 40, new_low_52w: 5, ad_line_change: 2 }))
    expect(r?.band).toBe('strength')
  })

  it('경계값 deterministic: ratio=lean(0.60) → strength, =broad(0.70) → broad_strength', () => {
    expect(breadthBand(inp({ advance: 60, decline: 40 }))?.band).toBe('strength') // 0.60
    expect(breadthBand(inp({ advance: 70, decline: 30 }))?.band).toBe('broad_strength') // 0.70
    expect(BREADTH_THRESHOLDS.lean).toBe(0.6)
    expect(BREADTH_THRESHOLDS.broad).toBe(0.7)
  })

  it('데이터 없음 (advance+decline=0) → null (대기, 0 변환 금지)', () => {
    expect(breadthBand(inp({ advance: 0, decline: 0 }))).toBeNull()
    expect(breadthBand(null)).toBeNull()
  })
})

describe('BreadthCardSummary — 밴드 + raw 회귀', () => {
  it('밴드 1줄 + 보조 부제 + raw 숫자 유지', () => {
    render(
      <BreadthCardSummary
        data={inp({ advance: 382, decline: 118, new_high_52w: 45, new_low_52w: 12, ad_line: 1500, ad_line_change: 3 })}
        labels={KO}
      />,
    )
    expect(screen.getByText('광범위한 강세')).toBeInTheDocument() // 밴드
    expect(screen.getByText(/신고가 우위 · AD ↑/)).toBeInTheDocument() // 보조 부제
    expect(screen.getByText('382')).toBeInTheDocument() // raw 상승 유지(회귀 0)
    expect(screen.getByText('118')).toBeInTheDocument() // raw 하락
  })

  it('데이터 없으면 밴드 미렌더(기존 미생성 문구)', () => {
    render(<BreadthCardSummary data={null} labels={KO} />)
    expect(screen.getByText('Breadth 데이터 미생성')).toBeInTheDocument()
  })
})
