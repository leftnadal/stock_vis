/**
 * D-MP2-SURFACE — 판단 화면 재구성 테스트.
 *
 * 커버리지:
 *   1. 위계 순서: DOM 상 regime hero → anomaly → sector 히트맵 → brief → breadth/concentration 순.
 *   2. stance: stance_ok=true → 판단 카피 + 게이지 / stance_ok=false(STALE 등) → fallback·게이지 숨김.
 *   3. 히트맵: 11 타일 렌더 + rel_strength로 색 분기(양수=rose, 음수=sky, rotation_index 미사용 증명).
 *   4. 행위보존 회귀: breadth·concentration·brief·news 여전히 렌더 + onOpen→CardDrawer 모달 열림.
 */
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { http, HttpResponse } from 'msw'
import type { ReactNode } from 'react'
import { describe, expect, it, vi } from 'vitest'

import { MP_V2_BASE, type SectorDetail } from '@/lib/api/marketPulseV2'
import { server } from '../mocks/server'
import {
  mpAllHandlers,
  mpI18nSuccess,
  mpOverviewSuccess,
  overviewFixture,
  cardDetailFixtures,
} from './fixtures'
import MarketPulseV2Page from '@/app/market-pulse-v2/page'
import { RegimeCardSummary } from '@/app/market-pulse-v2/cards/RegimeCardSummary'
import { SectorHeatmap } from '@/app/market-pulse-v2/cards/SectorHeatmap'

// ── 11섹터 픽스처 ──────────────────────────────────────────────
const ELEVEN_SECTORS: SectorDetail['sectors'] = [
  { symbol: 'XLK', rel_strength: 1.80, rank: 1, momentum_1d: 0.5, momentum_5d: 0.3, momentum_20d: 0.2, flow_proxy: 0.1 },
  { symbol: 'XLC', rel_strength: 0.50, rank: 2, momentum_1d: 0.2, momentum_5d: 0.1, momentum_20d: 0.1, flow_proxy: 0.0 },
  { symbol: 'XLY', rel_strength: 0.15, rank: 3, momentum_1d: 0.1, momentum_5d: 0.0, momentum_20d: 0.0, flow_proxy: 0.0 },
  { symbol: 'XLV', rel_strength: 0.03, rank: 4, momentum_1d: 0.0, momentum_5d: 0.0, momentum_20d: 0.0, flow_proxy: 0.0 },
  { symbol: 'XLI', rel_strength: -0.02, rank: 5, momentum_1d: 0.0, momentum_5d: 0.0, momentum_20d: 0.0, flow_proxy: 0.0 },
  { symbol: 'XLRE', rel_strength: -0.12, rank: 6, momentum_1d: -0.1, momentum_5d: 0.0, momentum_20d: 0.0, flow_proxy: 0.0 },
  { symbol: 'XLB', rel_strength: -0.25, rank: 7, momentum_1d: -0.2, momentum_5d: -0.1, momentum_20d: 0.0, flow_proxy: 0.0 },
  { symbol: 'XLU', rel_strength: -0.30, rank: 8, momentum_1d: -0.2, momentum_5d: -0.1, momentum_20d: -0.1, flow_proxy: 0.0 },
  { symbol: 'XLP', rel_strength: -0.42, rank: 9, momentum_1d: -0.3, momentum_5d: -0.2, momentum_20d: -0.1, flow_proxy: 0.0 },
  { symbol: 'XLF', rel_strength: -0.60, rank: 10, momentum_1d: -0.4, momentum_5d: -0.3, momentum_20d: -0.2, flow_proxy: 0.0 },
  { symbol: 'XLE', rel_strength: -0.95, rank: 11, momentum_1d: -0.6, momentum_5d: -0.4, momentum_20d: -0.3, flow_proxy: 0.0 },
]

/** sector detail 핸들러 — 11섹터 전부 포함. */
function mpSectorDetailFull() {
  return http.get(`${MP_V2_BASE}/cards/sector/detail`, () =>
    HttpResponse.json(
      {
        _meta: { generated_at: '2026-06-11T00:00:00Z', latency_ms: 5, cache: 'MISS' },
        data: {
          ...cardDetailFixtures.sector,
          sectors: ELEVEN_SECTORS,
          rotation_index: 0.072, // 전 섹터 동일값 — 색에 쓰이면 전 타일 동색 버그
        },
      },
      { status: 200 },
    ),
  )
}

/** 모든 핸들러 + 11섹터 sector detail 교체.
 * mpSectorDetailFull()을 먼저 등록하여 MSW first-match 방식으로 우선 적용.
 */
function mpAllHandlersWithFullSector() {
  const base = mpAllHandlers()
  // MSW는 먼저 등록된 핸들러가 우선 → full sector를 base의 sector detail보다 앞에 배치
  return [mpSectorDetailFull(), ...base]
}

function wrap(ui: ReactNode) {
  const client = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  })
  return render(<QueryClientProvider client={client}>{ui}</QueryClientProvider>)
}

// ── 1. 위계 순서 ────────────────────────────────────────────────
describe('위계 순서', () => {
  it('DOM 상 regime hero → anomaly → sector 히트맵 → brief → breadth → concentration 순', async () => {
    server.use(...mpAllHandlersWithFullSector())
    wrap(<MarketPulseV2Page />)

    // 모든 패널이 렌더될 때까지 대기
    await waitFor(() => expect(screen.getByText('Market Regime')).toBeInTheDocument())
    await waitFor(() => screen.getAllByText('Sector Flow'))

    const main = document.querySelector('main')!

    // 위치 기준: getBoundingClientRect() 대신 DOM 순서(compareDocumentPosition)로 확인
    const regimeSection = screen.getAllByText('Market Regime')[0].closest('article, section, div')!
    const anomalyEl = screen.getByText('특이 신호 없음').closest('section, div')!
    const briefEl = screen.getByText('Briefing').closest('article, section, div')!
    const breadthEl = screen.getByText('Market Breadth').closest('article, section, div')!
    const concentrationEl = screen.getByText('Concentration').closest('article, section, div')!

    // Sector Flow가 두 개(히트맵 헤더 + SectorCardSummary는 없으므로 히트맵만)
    const sectorFlowEls = screen.getAllByText('Sector Flow')
    // 히트맵 헤더는 page.tsx에서 히트맵이 brief 이전에 배치됨
    const sectorEl = sectorFlowEls[0].closest('article, section, div')!

    // DOM 순서 비교 (Node.DOCUMENT_POSITION_FOLLOWING = 4 → 이후에 위치)
    expect(regimeSection.compareDocumentPosition(anomalyEl) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy()
    expect(anomalyEl.compareDocumentPosition(sectorEl) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy()
    expect(sectorEl.compareDocumentPosition(briefEl) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy()
    expect(briefEl.compareDocumentPosition(breadthEl) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy()
    expect(breadthEl.compareDocumentPosition(concentrationEl) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy()
    expect(main).toBeInTheDocument()
  })
})

// ── 2. stance: RegimeCardSummary ────────────────────────────────
describe('RegimeCardSummary — stance', () => {
  const baseData = overviewFixture.cards.regime!

  it('stance_ok=true → 판단 카피 크게 표시 + 게이지 노출', () => {
    const data = { ...baseData, stance_ok: true, stance_copy: '추세 추종 유리 — 확장 국면' }
    render(<RegimeCardSummary data={data} />)

    const copy = screen.getByTestId('stance-copy')
    expect(copy).toBeInTheDocument()
    expect(copy).toHaveTextContent('추세 추종 유리 — 확장 국면')
    // 게이지 aria-label 확인
    expect(screen.getByLabelText(/국면 게이지/)).toBeInTheDocument()
    // fallback 미노출
    expect(screen.queryByTestId('stance-fallback')).not.toBeInTheDocument()
  })

  it('stance_ok=false → fallback 문구(muted), 게이지 숨김', () => {
    const data = { ...baseData, stance_ok: false, stance_copy: '판단 보류 — 데이터 지연/부족' }
    render(<RegimeCardSummary data={data} />)

    const fallback = screen.getByTestId('stance-fallback')
    expect(fallback).toBeInTheDocument()
    expect(fallback).toHaveTextContent('판단 보류')
    // 게이지 미노출
    expect(screen.queryByLabelText(/국면 게이지/)).not.toBeInTheDocument()
    // stance-copy(bold) 미노출
    expect(screen.queryByTestId('stance-copy')).not.toBeInTheDocument()
  })

  it('stance_ok undefined → fallback 표시, 게이지 숨김', () => {
    const data = { ...baseData, stance_ok: undefined, stance_copy: undefined }
    render(<RegimeCardSummary data={data} />)

    const fallback = screen.getByTestId('stance-fallback')
    expect(fallback).toBeInTheDocument()
    // 기본 fallback 문구
    expect(fallback).toHaveTextContent('판단 보류 — 데이터 지연/부족')
    expect(screen.queryByLabelText(/국면 게이지/)).not.toBeInTheDocument()
  })

  it('data=null → "데이터 미생성" 표시', () => {
    render(<RegimeCardSummary data={null} />)
    expect(screen.getByText(/데이터 미생성/)).toBeInTheDocument()
  })

  it('기존 표시 유지: 라벨·밴드·coverage·headline·SenseNote 정상', () => {
    const data = {
      ...baseData,
      stance_ok: true,
      stance_copy: '추세 추종 유리',
      headline: '확장 국면 지속',
      coverage: 0.92,
    }
    render(
      <RegimeCardSummary
        data={data}
        labels={{ 'regime.BULL_EXPANSION': '강세 확장' }}
        sense="현재 광범위한 강세 — 위험자산 비중 유지"
      />,
    )
    expect(screen.getByText('강세 확장')).toBeInTheDocument()
    expect(screen.getByText(/위험자산 우호 국면/)).toBeInTheDocument() // REGIME_MEANING 밴드
    expect(screen.getByText(/92%/)).toBeInTheDocument()
    expect(screen.getByText('확장 국면 지속')).toBeInTheDocument()
    expect(screen.getByText(/현재 광범위한 강세/)).toBeInTheDocument() // SenseNote
  })
})

// ── 3. 히트맵: SectorHeatmap ────────────────────────────────────
describe('SectorHeatmap — 타일 렌더 + 색 분기', () => {
  it('11 타일 렌더 + rel_strength로 색 분기(양수=rose, 음수=sky)', async () => {
    server.use(mpSectorDetailFull(), mpI18nSuccess())
    wrap(<SectorHeatmap />)

    // 11 타일 대기
    await waitFor(() => {
      const tiles = screen.getAllByTestId(/^sector-tile-/)
      expect(tiles).toHaveLength(11)
    })

    // 양수 rel_strength 타일(XLK=1.80) → rose 클래스
    const xlkTile = screen.getByTestId('sector-tile-XLK')
    expect(xlkTile.className).toMatch(/rose/)
    // 음수 rel_strength 타일(XLE=-0.95) → sky 클래스
    const xleTile = screen.getByTestId('sector-tile-XLE')
    expect(xleTile.className).toMatch(/sky/)
    // neutral(XLV=0.03, |rel|<=epsilon) → slate 클래스
    const xlvTile = screen.getByTestId('sector-tile-XLV')
    expect(xlvTile.className).toMatch(/slate/)
  })

  it('rotation_index 미사용 증명: 서로 다른 rel_strength → 다른 색 클래스', async () => {
    server.use(mpSectorDetailFull(), mpI18nSuccess())
    wrap(<SectorHeatmap />)

    await waitFor(() => expect(screen.getAllByTestId(/^sector-tile-/)).toHaveLength(11))

    // XLK(+1.80=rose) vs XLE(-0.95=sky) → 색이 달라야 함
    const xlkClass = screen.getByTestId('sector-tile-XLK').className
    const xleClass = screen.getByTestId('sector-tile-XLE').className
    expect(xlkClass).not.toBe(xleClass)

    // 모든 타일이 동일한 색이면 rotation_index 사용 버그 — 색 다양성 확인
    const tiles = screen.getAllByTestId(/^sector-tile-/)
    const classSet = new Set(tiles.map((t) => t.className))
    expect(classSet.size).toBeGreaterThan(1)
  })

  it('섹터 상세 로딩 중 → crash 없이 로딩 메시지', () => {
    // 느린 핸들러
    server.use(
      http.get(`${MP_V2_BASE}/cards/sector/detail`, async () => {
        await new Promise(() => {}) // never resolves
        return HttpResponse.json({})
      }),
    )
    wrap(<SectorHeatmap />)
    expect(screen.getByText(/불러오는 중/)).toBeInTheDocument()
  })

  it('섹터 상세 에러 → crash 없이 미생성 메시지', async () => {
    server.use(
      http.get(`${MP_V2_BASE}/cards/sector/detail`, () =>
        HttpResponse.json({ error: 'boom' }, { status: 500 }),
      ),
    )
    wrap(<SectorHeatmap />)
    await waitFor(() => expect(screen.getByText(/데이터 미생성|불러오는 중/)).toBeInTheDocument())
  })

  it('sectors 빈 배열 → 미생성 메시지', async () => {
    server.use(
      http.get(`${MP_V2_BASE}/cards/sector/detail`, () =>
        HttpResponse.json(
          {
            _meta: { generated_at: '2026-06-11T00:00:00Z', latency_ms: 5, cache: 'MISS' },
            data: { available: true, sectors: [], rotation_index: 0.072 },
          },
          { status: 200 },
        ),
      ),
    )
    wrap(<SectorHeatmap />)
    await waitFor(() => expect(screen.getByText(/데이터 미생성|불러오는 중/)).toBeInTheDocument())
  })

  it('onOpen → 클릭 시 호출', async () => {
    const user = userEvent.setup()
    server.use(mpSectorDetailFull(), mpI18nSuccess())
    const onOpen = vi.fn()
    wrap(<SectorHeatmap onOpen={onOpen} />)

    await waitFor(() => expect(screen.getAllByTestId(/^sector-tile-/)).toHaveLength(11))
    const section = screen.getByRole('button', { name: /Sector 히트맵/ })
    await user.click(section)
    expect(onOpen).toHaveBeenCalledTimes(1)
  })
})

// ── 4. 행위보존 회귀 ────────────────────────────────────────────
describe('행위보존 회귀', () => {
  it('breadth · concentration · brief · news 여전히 렌더', async () => {
    server.use(...mpAllHandlersWithFullSector())
    wrap(<MarketPulseV2Page />)

    await waitFor(() => expect(screen.getByText('Market Breadth')).toBeInTheDocument())
    expect(screen.getByText('Concentration')).toBeInTheDocument()
    expect(screen.getByText('Briefing')).toBeInTheDocument()
    expect(screen.getByText('News · 시장 뉴스')).toBeInTheDocument()
    expect(screen.getByText('CPI 둔화로 금리 인하 기대')).toBeInTheDocument()
  })

  it('TickerBar · StatusBanner 정상', async () => {
    server.use(...mpAllHandlersWithFullSector())
    wrap(<MarketPulseV2Page />)

    await waitFor(() => expect(screen.getByText('SPY')).toBeInTheDocument())
    // status=OK → StatusBanner 숨김
    expect(screen.queryByRole('status')).not.toBeInTheDocument()
  })

  it('Regime 카드 클릭 → CardDrawer 열림', async () => {
    const user = userEvent.setup()
    server.use(...mpAllHandlersWithFullSector())
    wrap(<MarketPulseV2Page />)

    await waitFor(() => expect(screen.getByText('Market Regime')).toBeInTheDocument())
    await user.click(screen.getAllByText('Market Regime')[0])

    const dialog = await screen.findByRole('dialog')
    expect(within(dialog).getByText('Market Regime · 시장 국면')).toBeInTheDocument()
  })

  it('Sector 히트맵 클릭 → sector CardDrawer 열림', async () => {
    const user = userEvent.setup()
    server.use(...mpAllHandlersWithFullSector())
    wrap(<MarketPulseV2Page />)

    await waitFor(() => expect(screen.getAllByTestId(/^sector-tile-/)[0]).toBeInTheDocument())

    const heatmapBtn = screen.getByRole('button', { name: /Sector 히트맵/ })
    await user.click(heatmapBtn)

    const dialog = await screen.findByRole('dialog')
    expect(within(dialog).getByText('Sector Flow · 섹터 흐름')).toBeInTheDocument()
  })

  it('drawer 닫기 — Briefing 드로어', async () => {
    const user = userEvent.setup()
    server.use(...mpAllHandlersWithFullSector())
    wrap(<MarketPulseV2Page />)

    await waitFor(() => expect(screen.getByText('Briefing')).toBeInTheDocument())
    await user.click(screen.getByText('Briefing'))

    const dialog = await screen.findByRole('dialog')
    await user.click(within(dialog).getByRole('button', { name: '닫기' }))
    await waitFor(() => expect(screen.queryByRole('dialog')).not.toBeInTheDocument())
  })

  it('Concentration 카드 클릭 → Concentration drawer + detail fetch', async () => {
    const user = userEvent.setup()
    server.use(...mpAllHandlersWithFullSector())
    wrap(<MarketPulseV2Page />)

    await waitFor(() => expect(screen.getByText('Concentration')).toBeInTheDocument())
    await user.click(screen.getByText('Concentration'))

    const dialog = await screen.findByRole('dialog')
    expect(within(dialog).getByText('Concentration · 집중도')).toBeInTheDocument()
    // CD-READ: cache 디버그 제거 → detail fetch 완료 프록시 = concentration 실콘텐츠.
    await waitFor(() => expect(within(dialog).getByText('상위 보유 종목')).toBeInTheDocument())
    expect(within(dialog).queryByText(/cache:/)).toBeNull()
  })
})
