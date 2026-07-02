/**
 * MP2-SECTOR-COLOR — sector 색 유틸 + cross-surface 일관성 회귀 테스트.
 *
 * 검증:
 *   ⒜ sectorDivergingDir: up/down/flat 판정 (epsilon 경계 포함)
 *   ⒝ 상승 값 → rose 계열, 하락 → sky 계열 (sectorTileClass/sectorTextClass/sectorBarFill 일관)
 *   ⒞ cross-surface: 동일 rel_strength에 대해 SectorHeatmap 타일과 SectorDetail이
 *      같은 방향색(요약↔상세 뒤집힘 0 — up 둘 다 rose, down 둘 다 sky)
 *   ⒟ 단일소스: sector 컴포넌트에 인라인 emerald/`16 185 129` 색 리터럴 잔존 0
 *      (파일 grep 방식)
 *   sense: SectorHeatmap에 sense 주면 sense-note 렌더 / null이면 미렌더
 */
import { render, screen, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import type { ReactNode } from 'react'
import { describe, expect, it } from 'vitest'
import * as fs from 'node:fs'
import * as path from 'node:path'

import {
  sectorDivergingDir,
  sectorTileClass,
  sectorTextClass,
  sectorBarFill,
} from '@/app/market-pulse-v2/sectorColor'
import type { SectorDetail as Detail, SectorRow } from '@/lib/api/marketPulseV2'
import { SectorDetail } from '@/app/market-pulse-v2/details/SectorDetail'
import { server } from '../mocks/server'
import { mpCardDetailSuccess } from './fixtures'

// ── ⒜ sectorDivergingDir 판정 ──────────────────────────────────────────────

describe('sectorDivergingDir — up/down/flat 판정', () => {
  it('v > epsilon → up', () => {
    expect(sectorDivergingDir(0.5)).toBe('up')
    expect(sectorDivergingDir(0.11)).toBe('up')
  })
  it('v < -epsilon → down', () => {
    expect(sectorDivergingDir(-0.5)).toBe('down')
    expect(sectorDivergingDir(-0.11)).toBe('down')
  })
  it('|v| <= epsilon → flat', () => {
    expect(sectorDivergingDir(0)).toBe('flat')
    expect(sectorDivergingDir(0.1)).toBe('flat')
    expect(sectorDivergingDir(-0.1)).toBe('flat')
    expect(sectorDivergingDir(0.05)).toBe('flat')
  })
  it('custom epsilon', () => {
    expect(sectorDivergingDir(0.3, 0.5)).toBe('flat')
    expect(sectorDivergingDir(0.6, 0.5)).toBe('up')
    expect(sectorDivergingDir(-0.6, 0.5)).toBe('down')
  })
})

// ── ⒝ 색 계열 일관성 ──────────────────────────────────────────────────────

describe('sectorTileClass — 상승=rose, 하락=sky', () => {
  it('상승 값(mild) → rose-100 계열', () => {
    expect(sectorTileClass(0.3)).toContain('rose-100')
    expect(sectorTileClass(0.3)).not.toContain('sky')
    expect(sectorTileClass(0.3)).not.toContain('emerald')
  })
  it('상승 값(strong>0.4) → rose-300 계열', () => {
    expect(sectorTileClass(0.5)).toContain('rose-300')
  })
  it('하락 값(mild) → sky-100 계열', () => {
    expect(sectorTileClass(-0.3)).toContain('sky-100')
    expect(sectorTileClass(-0.3)).not.toContain('rose')
    expect(sectorTileClass(-0.3)).not.toContain('emerald')
  })
  it('하락 값(strong<-0.4) → sky-300 계열', () => {
    expect(sectorTileClass(-0.5)).toContain('sky-300')
  })
  it('flat → slate', () => {
    expect(sectorTileClass(0.05)).toContain('slate-100')
  })
})

describe('sectorTextClass — 상승=rose, 하락=sky', () => {
  it('상승 → text-rose-600', () => {
    expect(sectorTextClass(1.0)).toBe('text-rose-600')
    expect(sectorTextClass(1.0)).not.toContain('emerald')
  })
  it('하락 → text-sky-600', () => {
    expect(sectorTextClass(-1.0)).toBe('text-sky-600')
    expect(sectorTextClass(-1.0)).not.toContain('rose')
  })
  it('flat → text-slate-400', () => {
    expect(sectorTextClass(0.05)).toBe('text-slate-400')
  })
})

describe('sectorBarFill — 상승=rose-500 hex, 하락=sky-500 hex', () => {
  it('상승 → #f43f5e (rose-500)', () => {
    expect(sectorBarFill(1.0)).toBe('#f43f5e')
    expect(sectorBarFill(1.0)).not.toBe('#10b981') // emerald-500
  })
  it('하락 → #0ea5e9 (sky-500)', () => {
    expect(sectorBarFill(-1.0)).toBe('#0ea5e9')
    expect(sectorBarFill(-1.0)).not.toBe('#f43f5e') // not rose
  })
  it('flat → #94a3b8 (slate-400)', () => {
    expect(sectorBarFill(0.0)).toBe('#94a3b8')
  })
})

// ── ⒞ cross-surface: SectorDetail 색 방향 검증 ──────────────────────────

function row(symbol: string, rel: number, rank: number): SectorRow {
  return { symbol, rel_strength: rel, momentum_1d: 0, momentum_5d: 0, momentum_20d: 0, flow_proxy: 0, rank }
}

const LABELS: Record<string, string> = {
  'sector.XLK': '기술',
  'sector.XLE': '에너지',
}

describe('cross-surface: SectorDetail 색 방향 (up=rose, down=sky)', () => {
  const payload: Detail = {
    available: true,
    date: '2026-06-11',
    cross_dispersion: 0.3,
    rotation_index: 0.07,
    sectors: [row('XLK', 1.23, 1), row('XLE', -0.95, 2)],
    sector_history: [
      { symbol: 'XLK', history: [{ date: '2026-06-11', rel_strength: 1.23 }] },
      { symbol: 'XLE', history: [{ date: '2026-06-11', rel_strength: -0.95 }] },
    ],
  }

  it('상승 섹터(XLK rel=+1.23) → rel 텍스트가 rose 계열 클래스 보유', () => {
    const { container } = render(<SectorDetail payload={payload} labels={LABELS} />)
    const items = container.querySelectorAll('ul > li')
    // XLK는 rank1이므로 items[0]
    const xlkSpan = items[0].querySelector('span.text-rose-600')
    expect(xlkSpan).not.toBeNull()
    expect(xlkSpan!.textContent).toContain('+1.23%')
  })

  it('하락 섹터(XLE rel=-0.95) → rel 텍스트가 sky 계열 클래스 보유', () => {
    const { container } = render(<SectorDetail payload={payload} labels={LABELS} />)
    const items = container.querySelectorAll('ul > li')
    // XLE는 rank2이므로 items[1]
    const xleSpan = items[1].querySelector('span.text-sky-600')
    expect(xleSpan).not.toBeNull()
    expect(xleSpan!.textContent).toContain('-0.95%')
  })

  it('SectorDetail rel Bar Cell fill — 상승 hex=rose, 하락 hex=sky (sectorBarFill 위임)', () => {
    // sectorBarFill 직접 확인으로 cross-surface fill 일관성 보증
    expect(sectorBarFill(1.23)).toBe('#f43f5e') // rose-500
    expect(sectorBarFill(-0.95)).toBe('#0ea5e9') // sky-500
  })
})

// ── ⒟ 인라인 색 리터럴 잔존 0 검증 ─────────────────────────────────────

const SECTOR_COMPONENT_FILES = [
  'frontend/app/market-pulse-v2/cards/SectorHeatmap.tsx',
  'frontend/app/market-pulse-v2/details/SectorDetail.tsx',
  'frontend/app/market-pulse-v2/details/SectorSparkline.tsx',
  'frontend/app/market-pulse-v2/cards/SectorCardSummary.tsx',
]

// emerald hex (rgb(16 185 129)) and emerald tailwind class in sector components
const BANNED_PATTERNS = [
  /16\s+185\s+129/,        // rgb(16 185 129) — emerald-500 hex
  /text-emerald-\d+/,      // inline emerald text class
  /bg-emerald-\d+/,        // inline emerald bg class
  /fill-emerald-\d+/,      // inline emerald fill class
]

describe('단일소스 보증: sector 컴포넌트 인라인 색 리터럴 잔존 0', () => {
  const root = path.resolve(__dirname, '../../..')

  for (const relPath of SECTOR_COMPONENT_FILES) {
    const absPath = path.join(root, relPath)
    it(`${path.basename(relPath)} — emerald 인라인 잔존 0`, () => {
      const content = fs.readFileSync(absPath, 'utf-8')
      for (const pattern of BANNED_PATTERNS) {
        expect(content).not.toMatch(pattern)
      }
    })
  }
})

// ── sense: SectorHeatmap sense-note 렌더 ────────────────────────────────

function wrap(ui: ReactNode) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  })
  return render(<QueryClientProvider client={client}>{ui}</QueryClientProvider>)
}

// SectorHeatmap은 useCardDetail로 sector card detail을 fetch하므로 MSW 핸들러 필요.
import { SectorHeatmap } from '@/app/market-pulse-v2/cards/SectorHeatmap'

describe('SectorHeatmap — sense-note 렌더', () => {
  it('sense 문자열 주입 시 data-testid=sense-note 렌더', async () => {
    server.use(mpCardDetailSuccess('sector'))
    wrap(<SectorHeatmap sense="기술이 앞서고 있어요." />)
    await waitFor(() =>
      expect(screen.getByTestId('sense-note')).toBeInTheDocument(),
    )
    expect(screen.getByTestId('sense-note').textContent).toBe('기술이 앞서고 있어요.')
  })

  it('sense=null이면 sense-note 미렌더(빈 박스 금지)', async () => {
    server.use(mpCardDetailSuccess('sector'))
    wrap(<SectorHeatmap sense={null} />)
    // sense-note 없음 확인
    await waitFor(() =>
      expect(screen.queryByTestId('sense-note')).toBeNull(),
    )
  })

  it('sense 미전달(undefined)이면 sense-note 미렌더', async () => {
    server.use(mpCardDetailSuccess('sector'))
    wrap(<SectorHeatmap />)
    await waitFor(() =>
      expect(screen.queryByTestId('sense-note')).toBeNull(),
    )
  })
})
