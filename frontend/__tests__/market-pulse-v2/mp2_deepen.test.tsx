/**
 * D-MP2-DEEPEN — 전조 블록 + 원인 근거 칩 테스트.
 *
 * 커버리지:
 *   1. RegimeCardSummary — NextStageBlock: 전환 임박/여유 분기, stance_ok 가드, null 가드.
 *   2. AnomalyPanel — EvidenceChips: 칩 렌더, hot 강조, null 생략, paired_news 링크.
 *   3. 기존 동작 회귀 보존.
 *
 * QueryClient / MSW 불필요 — 두 컴포넌트 모두 순수 렌더 (no hooks/queries).
 */
import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import { RegimeCardSummary } from '@/app/market-pulse-v2/cards/RegimeCardSummary'
import { AnomalyPanel } from '@/app/market-pulse-v2/components/AnomalyPanel'
import type { AnomalySection } from '@/lib/api/marketPulseV2'
import { overviewFixture } from './fixtures'

// ── 1. 전조 블록 — RegimeCardSummary ────────────────────────────
describe('전조 블록 — RegimeCardSummary', () => {
  const baseData = { ...overviewFixture.cards.regime!, stance_ok: true, stance_copy: '테스트' }

  it('next_stage_closest 있음 → 전환까지 … 텍스트 렌더', () => {
    const data = {
      ...baseData,
      stance_ok: true as const,
      next_stage_closest: {
        indicator: 'VIX',
        op: '>=',
        threshold: 25,
        actual: 22,
        to_threshold: 3,
      },
      next_stage: 'LATE_BULL',
    }
    render(<RegimeCardSummary data={data} />)

    expect(screen.getByTestId('next-stage-info')).toBeInTheDocument()
    expect(screen.getByTestId('next-stage-info').textContent).toContain('VIX 22/25')
  })

  it('to_threshold <= 20% of threshold → 앰버 "전환 임박"', () => {
    // near case: threshold=25, to_threshold=4 → 4 <= 0.2*25=5 → near
    const data = {
      ...baseData,
      stance_ok: true as const,
      next_stage_closest: {
        indicator: 'VIX',
        op: '>=',
        threshold: 25,
        actual: 21,
        to_threshold: 4,
      },
      next_stage: 'LATE_BULL',
    }
    render(<RegimeCardSummary data={data} />)

    expect(screen.getByTestId('next-stage-imminent')).toBeInTheDocument()
    expect(screen.queryByTestId('next-stage-margin')).not.toBeInTheDocument()
  })

  it('to_threshold > 20% of threshold → 담백 "전환 여유"', () => {
    // NOT near: threshold=25, to_threshold=8 → 8 > 0.2*25=5 → not near
    const data = {
      ...baseData,
      stance_ok: true as const,
      next_stage_closest: {
        indicator: 'VIX',
        op: '>=',
        threshold: 25,
        actual: 17,
        to_threshold: 8,
      },
      next_stage: 'LATE_BULL',
    }
    render(<RegimeCardSummary data={data} />)

    expect(screen.getByTestId('next-stage-margin')).toBeInTheDocument()
    expect(screen.queryByTestId('next-stage-imminent')).not.toBeInTheDocument()
  })

  it('stance_ok=false → 전조 블록 숨김', () => {
    const data = {
      ...baseData,
      stance_ok: false as const,
      next_stage_closest: {
        indicator: 'VIX',
        op: '>=',
        threshold: 25,
        actual: 21,
        to_threshold: 4,
      },
      next_stage: 'LATE_BULL',
    }
    render(<RegimeCardSummary data={data} />)

    expect(screen.queryByTestId('next-stage-info')).not.toBeInTheDocument()
    expect(screen.queryByTestId('next-stage-imminent')).not.toBeInTheDocument()
    expect(screen.queryByTestId('next-stage-margin')).not.toBeInTheDocument()
  })

  it('next_stage_closest null → 전조 블록 미렌더', () => {
    const data = {
      ...baseData,
      stance_ok: true as const,
      next_stage_closest: null,
    }
    render(<RegimeCardSummary data={data} />)

    expect(screen.queryByTestId('next-stage-info')).not.toBeInTheDocument()
  })

  it('기존 hero stance·5단계 게이지 회귀 보존', () => {
    // stance_ok=true → stance-copy + 게이지
    const trueData = {
      ...baseData,
      stance_ok: true as const,
      stance_copy: '추세 추종 유리',
      next_stage_closest: null,
    }
    render(<RegimeCardSummary data={trueData} />)
    expect(screen.getByTestId('stance-copy')).toBeInTheDocument()
    expect(screen.getByLabelText(/국면 게이지/)).toBeInTheDocument()
  })

  it('기존 hero stance·5단계 게이지 회귀 보존 — stance_ok=false', () => {
    // stance_ok=false → stance-fallback + 게이지 숨김
    const falseData = {
      ...baseData,
      stance_ok: false as const,
      next_stage_closest: null,
    }
    render(<RegimeCardSummary data={falseData} />)
    expect(screen.getByTestId('stance-fallback')).toBeInTheDocument()
    expect(screen.queryByLabelText(/국면 게이지/)).not.toBeInTheDocument()
  })
})

// ── 2. 원인 근거 칩 — AnomalyPanel ──────────────────────────────
describe('원인 근거 칩 — AnomalyPanel', () => {
  const baseFired = {
    rule_id: 'R02' as const,
    headline: '집중도 이상',
    threshold: { cross_dispersion: 1.5 },
    actual: 1.58,
    paired_news_id: null,
  }

  it('evidence 있을 때 모든 칩 렌더', () => {
    const data: AnomalySection = {
      mode: 'ANOMALY',
      overview: '이상 감지',
      sector_highlight: '기술주',
      portfolio_action: '방어적',
      fired: [
        {
          ...baseFired,
          actual: 1.58,
          evidence: {
            top10_weight: 0.41,
            vix_change_pct: 12.3,
            max_abs_sector_z: 2.1,
            sector_extreme_symbol: 'XLK',
          },
        },
      ],
    }
    render(<AnomalyPanel data={data} />)

    // 분산 칩: actual=1.58 >= threshold=1.5 → hot
    expect(screen.getByText(/분산 1.58\/1.5/)).toBeInTheDocument()
    // 상위10 칩
    expect(screen.getByText(/상위10 41.0%/)).toBeInTheDocument()
    // VIX 칩 (양수 → + 부호)
    expect(screen.getByText(/VIX \+12.3%/)).toBeInTheDocument()
    // 섹터z 칩
    expect(screen.getByText(/섹터z 2.10/)).toBeInTheDocument()
    // 급등섹터 칩 (label fallback = symbol): 칩 span 안에 있는 XLK
    const xlkSpans = screen.getAllByText('XLK')
    expect(xlkSpans.some((el) => el.tagName === 'SPAN')).toBe(true)
  })

  it('hot 강조: 분산 칩 actual>=threshold → rose 클래스, sector_extreme → rose 클래스', () => {
    const data: AnomalySection = {
      mode: 'ANOMALY',
      overview: '이상 감지',
      sector_highlight: '',
      portfolio_action: '',
      fired: [
        {
          ...baseFired,
          actual: 1.58,
          evidence: {
            top10_weight: null,
            vix_change_pct: null,
            max_abs_sector_z: null,
            sector_extreme_symbol: 'XLK',
          },
        },
      ],
    }
    render(<AnomalyPanel data={data} />)

    // 분산 칩: actual=1.58 >= threshold=1.5 → rose
    const dispersionChip = screen.getByText(/분산 1.58\/1.5/)
    expect(dispersionChip.className).toMatch(/rose/)

    // XLK 칩 (sector_extreme → always hot → rose)
    const xlkChip = screen.getByText('XLK')
    expect(xlkChip.className).toMatch(/rose/)
  })

  it('null evidence 칩 생략', () => {
    const data: AnomalySection = {
      mode: 'ANOMALY',
      overview: '이상 감지',
      sector_highlight: '',
      portfolio_action: '',
      fired: [
        {
          ...baseFired,
          actual: 1.58,
          evidence: {
            top10_weight: null,
            vix_change_pct: null,
            max_abs_sector_z: null,
            sector_extreme_symbol: null,
          },
        },
      ],
    }
    render(<AnomalyPanel data={data} />)

    // 분산 칩만 있어야 함 (threshold exists)
    expect(screen.getByText(/분산 1.58\/1.5/)).toBeInTheDocument()
    // null인 칩은 미렌더
    expect(screen.queryByText(/상위10/)).not.toBeInTheDocument()
    expect(screen.queryByText(/VIX/)).not.toBeInTheDocument()
    expect(screen.queryByText(/섹터z/)).not.toBeInTheDocument()
  })

  it('paired_news_title 있으면 링크 렌더', () => {
    const data: AnomalySection = {
      mode: 'ANOMALY',
      overview: '이상 감지',
      sector_highlight: '',
      portfolio_action: '',
      fired: [
        {
          ...baseFired,
          paired_news_title: '테스트 뉴스',
          paired_news_url: 'https://example.com/n',
        },
      ],
    }
    render(<AnomalyPanel data={data} />)

    const link = screen.getByRole('link', { name: /테스트 뉴스/ })
    expect(link).toHaveAttribute('href', 'https://example.com/n')
    expect(link).toHaveAttribute('target', '_blank')
  })

  it('CALM mode → 칩 없음 (fired=[])', () => {
    const data: AnomalySection = {
      mode: 'CALM',
      overview: '안정',
      sector_highlight: '',
      portfolio_action: '',
      fired: [],
    }
    render(<AnomalyPanel data={data} />)

    expect(screen.queryByText(/분산/)).not.toBeInTheDocument()
    expect(screen.queryByText(/상위10/)).not.toBeInTheDocument()
    expect(screen.queryByText(/VIX/)).not.toBeInTheDocument()
    expect(screen.queryByText(/섹터z/)).not.toBeInTheDocument()
  })

  it('기존 AnomalyPanel mode/fired 회귀 보존', () => {
    const data: AnomalySection = {
      mode: 'ANOMALY',
      overview: '이상 감지 요약',
      sector_highlight: '기술주 강세',
      portfolio_action: '방어적 포지션',
      fired: [{ ...baseFired }],
    }
    render(<AnomalyPanel data={data} />)

    // mode header: 1개 시그널
    expect(screen.getByText(/1개 시그널/)).toBeInTheDocument()
    // 기존 dl 라벨
    expect(screen.getByText('총평')).toBeInTheDocument()
    expect(screen.getByText('주목 섹터')).toBeInTheDocument()
    expect(screen.getByText('포트폴리오')).toBeInTheDocument()
  })
})
