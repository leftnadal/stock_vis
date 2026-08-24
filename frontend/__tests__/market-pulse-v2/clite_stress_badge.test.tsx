/**
 * C-lite (1.6-S0) — 히어로 스트레스 배지 렌더 테스트.
 *
 * 검증: ⑴ state 전 값(stable/caution/severe) 라벨+토큰 렌더 ⑵ 부재 시 비표시(히어로 오염 방지)
 *   ⑶ 판단 로직 신설 0(백엔드 band 그대로) — FE 재판정 없음을 배지 단순성으로 고정.
 */
import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import { RegimeCardSummary } from '@/app/market-pulse-v2/cards/RegimeCardSummary'
import { StressHeroBadge } from '@/app/market-pulse-v2/cards/StressHeroBadge'
import type { RegimeCard } from '@/lib/api/marketPulseV2'

const REGIME: RegimeCard = {
  regime: 'expansion',
  status: 'ok',
  coverage: 0.9,
  transitioned: false,
  headline: null,
  stance_ok: true,
  stance_copy: '확장 유지',
} as unknown as RegimeCard

describe('StressHeroBadge — state별 라벨·토큰', () => {
  it('stable = "스트레스 안정" + slate 토큰', () => {
    render(<StressHeroBadge band="stable" />)
    const el = screen.getByTestId('stress-hero-badge')
    expect(el).toHaveTextContent('스트레스 안정')
    expect(el.className).toContain('slate') // stressAlert 토큰 재사용(색 하드코딩 0)
  })

  it('caution = "스트레스 주의" + amber 토큰', () => {
    render(<StressHeroBadge band="caution" />)
    const el = screen.getByTestId('stress-hero-badge')
    expect(el).toHaveTextContent('스트레스 주의')
    expect(el.className).toContain('amber')
  })

  it('severe = "스트레스 심화"(위기 금지) + rose 토큰', () => {
    render(<StressHeroBadge band="severe" />)
    const el = screen.getByTestId('stress-hero-badge')
    expect(el).toHaveTextContent('스트레스 심화')
    expect(el).not.toHaveTextContent('위기') // D-MPS-BAND-NAME
    expect(el.className).toContain('rose')
  })
})

describe('RegimeCardSummary — 배지 가산·부재 비표시', () => {
  it('stressBand 전달 시 히어로에 배지 렌더', () => {
    render(<RegimeCardSummary data={REGIME} stressBand="stable" />)
    expect(screen.getByTestId('stress-hero-badge')).toBeInTheDocument()
    // 기존 국면 라벨도 유지(행위보존)
    expect(screen.getByText('expansion')).toBeInTheDocument()
  })

  it('stressBand 부재(null) 시 배지 미렌더 — 히어로 오염 방지', () => {
    render(<RegimeCardSummary data={REGIME} stressBand={null} />)
    expect(screen.queryByTestId('stress-hero-badge')).not.toBeInTheDocument()
  })

  it('stressBand 미전달(undefined) 시에도 배지 미렌더 — 기존 호출부 호환', () => {
    render(<RegimeCardSummary data={REGIME} />)
    expect(screen.queryByTestId('stress-hero-badge')).not.toBeInTheDocument()
  })
})
