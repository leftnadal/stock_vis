/**
 * MP-UX-S2 — 의미 밴드 경계 전환 회귀 테스트.
 *
 * 검증:
 *   1. Regime 단계 → 의미 문구 밴드 + 단계별 색 경계 전환 (good ↔ bad)
 *   2. Anomaly 모드 → 의미 문구 (CALM/HYBRID/ANOMALY 경계)
 *   3. Anomaly rule actual ↔ 경보선(threshold) 표시 (FE 기바인딩, 임계 하드코딩 0)
 *
 * 카피·색은 meaning.ts 단일소스. 임계값은 fired[].threshold(백엔드)에서만 옴.
 */
import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import type { AnomalySection, RegimeCard } from '@/lib/api/marketPulseV2'
import { RegimeCardSummary } from '@/app/market-pulse-v2/cards/RegimeCardSummary'
import { AnomalyPanel } from '@/app/market-pulse-v2/components/AnomalyPanel'

function regime(overrides: Partial<RegimeCard>): RegimeCard {
  return {
    regime: 'BULL_EXPANSION',
    status: 'OK',
    coverage: 0.9,
    headline: '',
    fired_rules: [],
    transitioned: false,
    ...overrides,
  }
}

describe('Regime 의미 밴드 경계 전환', () => {
  it('강세 확장 → 의미 문구 + good(emerald) 색', () => {
    render(<RegimeCardSummary data={regime({ regime: 'BULL_EXPANSION' })} />)
    const band = screen.getByText('위험자산 우호 국면. 추세 추종 유리, 광범위 강세.')
    expect(band).toBeInTheDocument()
    expect(band.className).toContain('emerald')
  })

  it('위기 → 의미 문구 + bad(rose) 색 (경계 반대편)', () => {
    render(<RegimeCardSummary data={regime({ regime: 'CRISIS' })} />)
    const band = screen.getByText('시스템 스트레스. 현금·안전자산 비중, 급변동 대비.')
    expect(band).toBeInTheDocument()
    expect(band.className).toContain('rose')
  })

  it('전환 → 중립(slate) 색 (단계별 색이 실제로 갈림)', () => {
    render(<RegimeCardSummary data={regime({ regime: 'TRANSITION' })} />)
    const band = screen.getByText('방향 불확실·신호 혼재. 포지션 축소·관망 우위.')
    expect(band.className).toContain('slate')
  })
})

function anomaly(overrides: Partial<AnomalySection>): AnomalySection {
  return {
    mode: 'CALM',
    overview: '',
    sector_highlight: '',
    portfolio_action: '',
    fired: [],
    ...overrides,
  }
}

describe('Anomaly 모드 의미 밴드 경계', () => {
  it('CALM → "이상 신호 없음. 평상 범위."', () => {
    render(<AnomalyPanel data={anomaly({ mode: 'CALM' })} />)
    expect(screen.getByText('이상 신호 없음. 평상 범위.')).toBeInTheDocument()
  })

  it('HYBRID → "1개 신호 발동. 부분 경계."', () => {
    render(<AnomalyPanel data={anomaly({ mode: 'HYBRID' })} />)
    expect(screen.getByText('1개 신호 발동. 부분 경계.')).toBeInTheDocument()
  })

  it('ANOMALY → "2개 이상 동시 발동. 강한 경계."', () => {
    render(<AnomalyPanel data={anomaly({ mode: 'ANOMALY' })} />)
    expect(screen.getByText('2개 이상 동시 발동. 강한 경계.')).toBeInTheDocument()
  })
})

describe('Anomaly rule actual ↔ 경보선(threshold)', () => {
  it('R02 actual 0.42 / threshold 0.40 → 경보선 표시 (FE 기바인딩)', () => {
    render(
      <AnomalyPanel
        data={anomaly({
          mode: 'ANOMALY',
          fired: [
            {
              rule_id: 'R02',
              headline: '집중도 극단',
              threshold: { top10_weight: 0.4 },
              actual: 0.42,
              paired_news_id: null,
            },
          ],
        })}
      />,
    )
    expect(screen.getByText(/경보선 0\.4 초과/)).toBeInTheDocument()
    // actual은 기존 포맷(.toFixed(3)) 보존
    expect(screen.getByText('0.420')).toBeInTheDocument()
  })
})
