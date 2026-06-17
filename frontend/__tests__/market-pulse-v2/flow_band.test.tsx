/**
 * MP-UX-S5 Part A — 자금흐름(Concentration·Sector) 의미밴드 회귀 테스트.
 *
 * 검증:
 *   1. concentrationBand: 경계값(0.30/0.35/0.40) 전후 인덱스, null→대기, 비유한→graceful
 *      (임계는 top10_weight 기준; 0.40=R02 grounded 앵커, meaning.ts 단일소스)
 *   2. concentrationSentence: 밴드별 문장 + trend 유/무 괄호 처리
 *   3. sectorFlow / sectorSentence: 유입/유출/flat 분류, 부분/빈 데이터 graceful
 *   4. 카드 렌더: 의미밴드+문장 노출, null→대기 미렌더(0 변환 0), 원시값 펼침 잔존
 */
import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import type { ConcentrationCard, SectorCard } from '@/lib/api/marketPulseV2'
import {
  concentrationBand,
  concentrationSentence,
  sectorFlow,
  sectorSentence,
} from '@/app/market-pulse-v2/meaning'
import { ConcentrationCardSummary } from '@/app/market-pulse-v2/cards/ConcentrationCardSummary'
import { SectorCardSummary } from '@/app/market-pulse-v2/cards/SectorCardSummary'

describe('concentrationBand — top10_weight 경계 전환', () => {
  it('0.29 → 분산(index 0)', () => {
    expect(concentrationBand(0.29)?.key).toBe('dispersed')
    expect(concentrationBand(0.29)?.index).toBe(0)
  })
  it('경계 0.30 → 약한 쏠림(index 1, 이상 포함)', () => {
    expect(concentrationBand(0.3)?.key).toBe('weak')
  })
  it('경계 0.35 → 중간 쏠림(index 2)', () => {
    expect(concentrationBand(0.35)?.key).toBe('mid')
  })
  it('경계 0.40 → 강한 쏠림(index 3, R02 grounded 앵커)', () => {
    expect(concentrationBand(0.4)?.key).toBe('strong')
    expect(concentrationBand(0.41)?.key).toBe('strong')
  })
  it('null/undefined → null(대기, 0 변환 금지)', () => {
    expect(concentrationBand(null)).toBeNull()
    expect(concentrationBand(undefined)).toBeNull()
  })
  it('비유한(NaN/Infinity) → null(graceful)', () => {
    expect(concentrationBand(Number.NaN)).toBeNull()
    expect(concentrationBand(Number.POSITIVE_INFINITY)).toBeNull()
  })
})

describe('concentrationSentence — 밴드별 문장 + 추세 괄호', () => {
  it('강한 쏠림 + 추세 없음 → 괄호 생략', () => {
    const band = concentrationBand(0.42)!
    expect(concentrationSentence(band)).toBe('소수 대형주에 강하게 쏠림')
  })
  it('강한 쏠림 + 추세 ↑ → 괄호 포함', () => {
    const band = concentrationBand(0.42)!
    expect(concentrationSentence(band, '↑')).toBe('소수 대형주에 강하게 쏠림(최근 ↑)')
  })
  it('분산 → "자금이 고르게 분산"', () => {
    expect(concentrationSentence(concentrationBand(0.1)!)).toBe('자금이 고르게 분산')
  })
})

describe('sectorFlow — 유입/유출/flat 분류', () => {
  it('양(+) rel_strength → 유입(in)', () => {
    expect(sectorFlow(1.23).dir).toBe('in')
  })
  it('음(-) rel_strength → 유출(out)', () => {
    expect(sectorFlow(-0.95).dir).toBe('out')
  })
  it('epsilon 안쪽(≈0) → flat', () => {
    expect(sectorFlow(0.05).dir).toBe('flat')
    expect(sectorFlow(-0.05).dir).toBe('flat')
  })
  it('null/비유한 → flat(graceful)', () => {
    expect(sectorFlow(null).dir).toBe('flat')
    expect(sectorFlow(Number.NaN).dir).toBe('flat')
  })
})

describe('sectorSentence — 유입/유출 문장', () => {
  it('양쪽 존재 → "A·B로 유입, C서 유출"', () => {
    expect(sectorSentence(['기술', '반도체'], ['경기소비재'])).toBe('기술·반도체로 유입, 경기소비재서 유출')
  })
  it('유입만 존재(부분 데이터) → 있는 쪽만', () => {
    expect(sectorSentence(['기술'], [])).toBe('기술로 유입')
  })
  it('양쪽 빈 입력 → null(문장 생략 = 대기)', () => {
    expect(sectorSentence([], [])).toBeNull()
  })
})

describe('ConcentrationCardSummary 렌더', () => {
  const data: ConcentrationCard = {
    universe: 'SPY',
    top5_weight: 0.28,
    top10_weight: 0.41,
    hhi: 0.0521,
    top_holdings: [{ symbol: 'AAPL', weight: 0.071 }],
  }
  it('의미밴드 문장 + 활성 밴드(● 강한 쏠림) 노출', () => {
    render(<ConcentrationCardSummary data={data} />)
    expect(screen.getByText('소수 대형주에 강하게 쏠림')).toBeInTheDocument()
    expect(screen.getByText('● 강한 쏠림')).toBeInTheDocument()
  })
  it('원시값(top10=41.00%)은 펼침 영역에 보존', () => {
    render(<ConcentrationCardSummary data={data} />)
    expect(screen.getByText('41.00%')).toBeInTheDocument()
  })
  it('top10_weight 미존재 양상(대기) — null 밴드 → 값/바 미렌더', () => {
    // @ts-expect-error 의도적 결측(런타임 graceful 경로 검증)
    render(<ConcentrationCardSummary data={{ ...data, top10_weight: null }} />)
    expect(screen.getByText('집중도 데이터 수집 대기 중')).toBeInTheDocument()
    expect(screen.queryByText(/강하게 쏠림/)).not.toBeInTheDocument()
  })
})

describe('SectorCardSummary 렌더', () => {
  const data: SectorCard = {
    leaders: [{ symbol: 'XLK', rel_strength: 1.23, rank: 1, momentum_1d: 0.8 }],
    laggards: [{ symbol: 'XLE', rel_strength: -0.95, rank: 11, momentum_1d: -0.6 }],
    cross_dispersion: 0.314,
    rotation_index: 0.072,
  }
  it('유입/유출 문장 노출(라벨 미제공 시 symbol fallback)', () => {
    render(<SectorCardSummary data={data} />)
    expect(screen.getByText('XLK로 유입, XLE서 유출')).toBeInTheDocument()
  })
  it('빈 리더/후행 → 문장 생략(대기). 섹션 헤더는 잔존', () => {
    render(<SectorCardSummary data={{ ...data, leaders: [], laggards: [] }} />)
    // 한 줄 의미 문장("…로 유입/…서 유출")만 사라지고, 섹션 헤더(유입/유출)는 남는다.
    expect(screen.queryByText(/로 유입/)).not.toBeInTheDocument()
    expect(screen.queryByText(/서 유출/)).not.toBeInTheDocument()
  })
})
