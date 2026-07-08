/**
 * Phase 1.5 S4 — translations fallback 3상태 회귀 테스트(핵심).
 *
 * 검증(deterministic):
 *   1. 정상(senses 4키) → 4카드 sense 렌더
 *   2. 부분(일부 키) → 있는 카드만 sense, 나머지 카드 정상 + sense 미렌더, 에러/빈줄 없음
 *   3. 전무(translations null) → 전 카드 sense 0개, 카드 자체는 정상 렌더
 *   - 밴드·raw가 세 상태 모두 불변(additive 회귀 가드)
 *
 * selector 순수 함수 단위 검증도 포함.
 */
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, waitFor } from '@testing-library/react'
import type { ReactNode } from 'react'
import { describe, expect, it } from 'vitest'

import type { Translations } from '@/lib/api/marketPulseV2'
import { selectSense } from '@/app/market-pulse-v2/translationSelector'
import { server } from '../mocks/server'
import { mpI18nSuccess, mpNewsRefreshSuccess, mpOverviewSuccess } from './fixtures'
import MarketPulseV2Page from '@/app/market-pulse-v2/page'

function wrap(ui: ReactNode) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  })
  return render(<QueryClientProvider client={client}>{ui}</QueryClientProvider>)
}

const FULL: Translations = {
  senses: {
    regime: '강세장 후반부, 경계가 필요한 국면이에요.',
    breadth: '오르는 종목이 더 많아 참여가 폭넓습니다.',
    sector: '기술이 앞서고 유틸리티는 뒤처져 있어요.',
    concentration: '상위 종목 쏠림이 다소 높은 편입니다.',
  },
  model_version: 'gemini-2.5-flash',
  generated_at: '2026-06-18T00:00:00Z',
  status: 'OK',
}

// 밴드·raw 불변 가드용 앵커(overviewFixture: regime=BULL_EXPANSION, breadth.advance=320).
const BAND_ANCHOR = '위험자산 우호 국면. 추세 추종 유리, 광범위 강세.'

async function renderWith(translations: Translations | null) {
  server.use(
    mpOverviewSuccess({ translations }),
    mpI18nSuccess(),
    mpNewsRefreshSuccess(),
  )
  wrap(<MarketPulseV2Page />)
  await waitFor(() => expect(screen.getByText('Market Regime')).toBeInTheDocument())
}

describe('translations fallback 3상태', () => {
  // sector sense 복원: SectorHeatmap에 sense prop 추가 → 히트맵 아래 sense-note 렌더.
  // 따라서 정상 상태에서 sense-note는 4개(regime, breadth, sector, concentration).
  it('상태1 정상: 4카드 sense 렌더 + 밴드/raw 불변 (sector sense SectorHeatmap으로 복원)', async () => {
    await renderWith(FULL)
    expect(screen.getAllByTestId('sense-note')).toHaveLength(4)
    expect(screen.getByText(FULL.senses.regime)).toBeInTheDocument()
    // sector sense가 SectorHeatmap 아래에 렌더됨
    expect(screen.getByText(FULL.senses.sector)).toBeInTheDocument()
    // additive 가드: 밴드·raw 그대로
    expect(screen.getByText(BAND_ANCHOR)).toBeInTheDocument()
    expect(screen.getByText('320')).toBeInTheDocument()
  })

  it('상태2 부분: 있는 카드만 sense, 나머지 정상 + 에러 없음', async () => {
    await renderWith({
      ...FULL,
      senses: { regime: FULL.senses.regime, breadth: FULL.senses.breadth },
    })
    expect(screen.getAllByTestId('sense-note')).toHaveLength(2)
    expect(screen.getByText(FULL.senses.regime)).toBeInTheDocument()
    // 누락 카드(sector/concentration) sense 미렌더
    expect(screen.queryByText(FULL.senses.sector)).not.toBeInTheDocument()
    expect(screen.queryByText(FULL.senses.concentration)).not.toBeInTheDocument()
    // 카드 자체는 정상 + 밴드 불변
    expect(screen.getByText('Concentration')).toBeInTheDocument()
    expect(screen.getByText(BAND_ANCHOR)).toBeInTheDocument()
  })

  it('상태3 전무(null): sense 0개, 카드 정상 렌더', async () => {
    await renderWith(null)
    expect(screen.queryAllByTestId('sense-note')).toHaveLength(0)
    // 4카드 전부 정상 렌더 + 밴드/raw 불변
    expect(screen.getByText('Market Regime')).toBeInTheDocument()
    expect(screen.getByText('Market Breadth')).toBeInTheDocument()
    expect(screen.getByText('Sector Flow')).toBeInTheDocument()
    expect(screen.getByText('Concentration')).toBeInTheDocument()
    expect(screen.getByText(BAND_ANCHOR)).toBeInTheDocument()
    expect(screen.getByText('320')).toBeInTheDocument()
  })
})

describe('selectSense 셀렉터', () => {
  it('키 존재 → 문자열 반환', () => {
    expect(selectSense(FULL, 'regime')).toBe(FULL.senses.regime)
  })
  it('키 없음 → null', () => {
    expect(selectSense({ ...FULL, senses: { regime: 'x' } }, 'sector')).toBeNull()
  })
  it('translations null/undefined → null', () => {
    expect(selectSense(null, 'regime')).toBeNull()
    expect(selectSense(undefined, 'breadth')).toBeNull()
  })
  it('빈 문자열/공백 → null', () => {
    expect(selectSense({ ...FULL, senses: { regime: '   ' } }, 'regime')).toBeNull()
  })
})
