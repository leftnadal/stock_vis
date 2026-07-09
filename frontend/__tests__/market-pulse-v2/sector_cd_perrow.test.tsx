/**
 * MP2-SECTOR-CD S3 보완 — per-row 회전 맵 진입 (D-SECTOR-NAV 이행 결함 수정).
 *
 * 각 섹터 행 탭 → rotation?from=<그 행 symbol>. 비-리더 행이 리더가 아닌 자기 symbol을
 * 전달하는지(구별 케이스)로 결함 수정 증명. 상단 CTA는 전체 보기(from=리더) 유지.
 */
import { render } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import type { SectorDetail as Detail, SectorRow } from '@/lib/api/marketPulseV2'
import { SectorCdPanel } from '@/app/market-pulse-v2/details/SectorCdPanel'

function row(
  symbol: string, rel: number, mom5: number, rank: number,
  cd_state: SectorRow['cd_state'], rel5: number | null = rel,
): SectorRow {
  // CD-STAB A′: rel_strength_5d = 판단 계열(카드 근거) x축. 기본 = rel(1일).
  return {
    symbol, rel_strength: rel, rel_strength_5d: rel5,
    momentum_1d: 0, momentum_5d: mom5, momentum_20d: 0, flow_proxy: 0, rank, cd_state,
  }
}

const LABELS: Record<string, string> = { 'sector.XLK': '기술', 'sector.XLE': '에너지', 'sector.XLF': '금융' }

function mkPayload(): Detail {
  return {
    available: true,
    date: '2026-07-09',
    cd_rel_strength_baseline: 0,
    cd_momentum_baseline: 0,
    sectors: [
      row('XLK', 0.8, 0.5, 1, 'leading_strengthening'), // 리더(rank-1)
      row('XLE', -0.6, -0.4, 2, 'lagging_deteriorating'), // 비-리더
      row('XLF', 0.2, -0.1, 3, 'leading_weakening'), // 비-리더
    ],
    sector_history: [],
  }
}

describe('SectorCdPanel — per-row 회전 맵 진입', () => {
  it('비-리더 행(XLE, rank-2) 탭 → from=XLE (리더 XLK 아님, 결함 수정 증명)', () => {
    const { getByTestId } = render(<SectorCdPanel payload={mkPayload()} labels={LABELS} />)
    const link = getByTestId('cd-row-link-XLE')
    expect(link.getAttribute('href')).toBe('/market-pulse-v2/rotation?from=XLE')
    // 리더(XLK)로 잘못 가지 않음을 명시 확인
    expect(link.getAttribute('href')).not.toContain('from=XLK')
  })

  it('또 다른 비-리더 행(XLF, rank-3) → from=XLF', () => {
    const { getByTestId } = render(<SectorCdPanel payload={mkPayload()} labels={LABELS} />)
    expect(getByTestId('cd-row-link-XLF').getAttribute('href')).toBe('/market-pulse-v2/rotation?from=XLF')
  })

  it('리더 행(XLK, rank-1) → from=XLK', () => {
    const { getByTestId } = render(<SectorCdPanel payload={mkPayload()} labels={LABELS} />)
    expect(getByTestId('cd-row-link-XLK').getAttribute('href')).toBe('/market-pulse-v2/rotation?from=XLK')
  })

  it('각 행은 독립적으로 자기 symbol을 from으로 전달', () => {
    const { getByTestId } = render(<SectorCdPanel payload={mkPayload()} labels={LABELS} />)
    for (const sym of ['XLK', 'XLE', 'XLF']) {
      expect(getByTestId(`cd-row-link-${sym}`).getAttribute('href')).toBe(`/market-pulse-v2/rotation?from=${sym}`)
    }
  })
})

describe('SectorCdPanel — 상단 CTA 회귀(전체 보기, from=리더)', () => {
  it('상단 CTA는 리더(rank-1) from 유지 + 라벨 "전체 보기"', () => {
    const { getByTestId } = render(<SectorCdPanel payload={mkPayload()} labels={LABELS} />)
    const cta = getByTestId('rrg-cta')
    expect(cta.getAttribute('href')).toBe('/market-pulse-v2/rotation?from=XLK')
    expect(cta.textContent).toContain('전체 보기')
  })
})

describe('SectorCdPanel — 기존 판단 카드 회귀', () => {
  it('미니맵·뱃지·문구·근거값 유지(행 링크化 무영향)', () => {
    const { getByTestId } = render(<SectorCdPanel payload={mkPayload()} labels={LABELS} />)
    expect(getByTestId('cd-minimap')).toBeInTheDocument()
    expect(getByTestId('cd-badge-XLE').textContent).toBe('부진·악화')
    expect(getByTestId('cd-stance-XLE')).toBeInTheDocument()
    expect(getByTestId('cd-rel-XLE').textContent).toContain('-0.60%')
    expect(getByTestId('cd-mom-XLE').textContent).toContain('-0.40%')
  })
})
