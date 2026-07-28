// StateBandSparkline 렌더 검증 (MON-P3-ALERT §6·§7-5)
import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import { StateBandSparkline } from '@/components/monitor/StateBandSparkline'
import type { SparklineBand, SparklinePoint } from '@/types/monitor'

// BE score_to_phase 경계(단일 소스)와 동일한 5밴드 — 테스트도 API 값을 그대로 주입(하드코딩 아님)
const BANDS: SparklineBand[] = [
  { phase: 'full_moon', label: '신호가 환하게 켜졌어요', min: 0.6, max: 1.0 },
  { phase: 'waxing', label: '신호가 밝아지고 있어요', min: 0.2, max: 0.6 },
  { phase: 'half_moon', label: '반반이에요', min: -0.2, max: 0.2 },
  { phase: 'waning', label: '신호가 어두워지고 있어요', min: -0.6, max: -0.2 },
  { phase: 'new_moon', label: '신호가 힘을 잃고 있어요', min: -1.0, max: -0.6 },
]

// 실제 AAPL 형태의 38 거래일 score 시계열(상승 추세)
function aaplSeries(n = 38): SparklinePoint[] {
  return Array.from({ length: n }, (_, i) => ({
    asof: `2026-0${5 + Math.floor(i / 20)}-${String((i % 20) + 1).padStart(2, '0')}`,
    score: Number((-0.5 + i / n).toFixed(4)),
  }))
}

describe('StateBandSparkline', () => {
  it('실 AAPL 시계열(38행)로 밴드+선을 렌더한다', () => {
    render(<StateBandSparkline series={aaplSeries(38)} bands={BANDS} />)
    expect(screen.getByTestId('state-band-sparkline')).toBeInTheDocument()
    // 5 상태 밴드 전부 렌더
    for (const b of BANDS) {
      expect(screen.getByTestId(`state-band-sparkline-band-${b.phase}`)).toBeInTheDocument()
    }
    // score 선
    expect(screen.getByTestId('state-band-sparkline-line')).toBeInTheDocument()
  })

  it('전이일 표식을 series 위치에 렌더한다', () => {
    const series = aaplSeries(38)
    const t = series[10].asof
    render(<StateBandSparkline series={series} bands={BANDS} transitions={[t]} />)
    expect(screen.getAllByTestId('state-band-sparkline-transition')).toHaveLength(1)
  })

  it('데이터 2개 미만이면 빈 상태 폴백', () => {
    render(<StateBandSparkline series={[{ asof: '2026-07-09', score: 0.1 }]} bands={BANDS} />)
    expect(screen.getByTestId('state-band-sparkline-empty')).toBeInTheDocument()
  })

  it('밴드가 비어도 series로 안전 폴백(하드코딩 임계값 없음)', () => {
    render(<StateBandSparkline series={aaplSeries(10)} bands={[]} />)
    expect(screen.getByTestId('state-band-sparkline')).toBeInTheDocument()
    expect(screen.getByTestId('state-band-sparkline-line')).toBeInTheDocument()
  })
})
