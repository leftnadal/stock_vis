/**
 * MP-UX-S1 — 라벨 카탈로그(KO_LABELS) 매핑 회귀 테스트.
 *
 * 검증:
 *   1. translate() 폴백 체인 (labels 키 존재 / 부재→defaultText)
 *   2. 카드 내부 전문어 라벨이 labels 경유로 한글 렌더 (Part B)
 *   3. 값·포맷 보존 (라벨만 바뀌고 숫자/단위/소수자릿수 불변)
 *   4. status 단일소스 (Part C): labels 제공 시 한글, 미제공 시 raw enum
 *      → 컴포넌트에 한글 라벨이 숨어있지 않음(이중소스 해소) 증명
 */
import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import { translate } from '@/lib/i18n/marketPulse'
import type { ConcentrationCard, SectorCard } from '@/lib/api/marketPulseV2'
import { ConcentrationCardSummary } from '@/app/market-pulse-v2/cards/ConcentrationCardSummary'
import { SectorCardSummary } from '@/app/market-pulse-v2/cards/SectorCardSummary'
import { StatusBanner } from '@/app/market-pulse-v2/components/StatusBanner'

const LABELS: Record<string, string> = {
  'metric.top5': '상위5 비중',
  'metric.top10': '상위10 비중',
  'metric.hhi': '허핀달 지수',
  'metric.dispersion': '섹터 분산도',
  'metric.rotation': '로테이션 지수',
  'status.STALE': '데이터 오래됨',
}

describe('translate() 폴백 체인', () => {
  it('labels에 키가 있으면 카탈로그 값', () => {
    expect(translate('metric.top5', LABELS, 'top5')).toBe('상위5 비중')
  })
  it('labels에 키가 없으면 defaultText로 폴백(발명 0)', () => {
    expect(translate('metric.unknown', LABELS, 'raw-fallback')).toBe('raw-fallback')
  })
  it('labels 자체가 없으면 defaultText', () => {
    expect(translate('metric.top5', undefined, 'top5')).toBe('top5')
  })
})

describe('ConcentrationCardSummary 라벨 매핑 (Part B)', () => {
  const data: ConcentrationCard = {
    universe: 'SP500_MCAP',
    top5_weight: 0.28,
    top10_weight: 0.41,
    hhi: 0.0521,
    top_holdings: [{ symbol: 'AAPL', weight: 0.071 }],
  }

  it('전문어 top5/top10/HHI → 한글 라벨 렌더', () => {
    render(<ConcentrationCardSummary data={data} labels={LABELS} />)
    expect(screen.getByText('상위5 비중')).toBeInTheDocument()
    expect(screen.getByText('상위10 비중')).toBeInTheDocument()
    expect(screen.getByText('허핀달 지수')).toBeInTheDocument()
  })

  it('라벨만 바뀌고 값·포맷 불변 (top5=28.00% / HHI=0.0521 4자리)', () => {
    render(<ConcentrationCardSummary data={data} labels={LABELS} />)
    expect(screen.getByText('28.00%')).toBeInTheDocument()
    expect(screen.getByText('41.00%')).toBeInTheDocument()
    expect(screen.getByText('0.0521')).toBeInTheDocument()
  })

  it('labels 미제공 시 raw fallback (top5)', () => {
    render(<ConcentrationCardSummary data={data} />)
    expect(screen.getByText('top5')).toBeInTheDocument()
    expect(screen.getByText('HHI')).toBeInTheDocument()
  })
})

describe('SectorCardSummary 라벨 매핑 (Part B)', () => {
  const data: SectorCard = {
    leaders: [{ symbol: 'XLK', rel_strength: 1.23, rank: 1, momentum_1d: 0.8 }],
    laggards: [{ symbol: 'XLE', rel_strength: -0.95, rank: 11, momentum_1d: -0.6 }],
    cross_dispersion: 0.314,
    rotation_index: 0.072,
  }

  it('dispersion/rotation → 한글 + 값(.toFixed(3)) 보존', () => {
    render(<SectorCardSummary data={data} labels={LABELS} />)
    expect(screen.getByText(/섹터 분산도/)).toBeInTheDocument()
    expect(screen.getByText(/로테이션 지수/)).toBeInTheDocument()
    expect(screen.getByText(/0\.314/)).toBeInTheDocument()
    expect(screen.getByText(/0\.072/)).toBeInTheDocument()
  })
})

describe('StatusBanner 단일소스 (Part C)', () => {
  it('OK 상태는 배너 숨김', () => {
    render(<StatusBanner status="OK" labels={LABELS} />)
    expect(screen.queryByRole('status')).not.toBeInTheDocument()
  })

  it('labels 제공 시 status.* 한글 라벨 렌더', () => {
    render(<StatusBanner status="STALE" reason="스냅샷 2일 경과" labels={LABELS} />)
    expect(screen.getByText('데이터 오래됨')).toBeInTheDocument()
    expect(screen.getByText('스냅샷 2일 경과')).toBeInTheDocument()
  })

  it('labels 미제공 시 raw enum 렌더 — 컴포넌트에 한글 라벨 미내장(이중소스 해소 증명)', () => {
    render(<StatusBanner status="STALE" />)
    expect(screen.getByText('STALE')).toBeInTheDocument()
    expect(screen.queryByText('데이터 오래됨')).not.toBeInTheDocument()
  })
})
