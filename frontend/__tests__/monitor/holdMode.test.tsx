// HOLD-P1 보유 모드 (FE) — 사다리 zone_display 소비(하드코딩 제거 회귀) · 토글 · 필수검증 · pnl 배지.
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { MiniPriceLadder, PriceLadder, ZoneChip } from '@/components/monitor/PriceLadder'
import type { ZoneDisplay } from '@/types/monitor'

// BE build_zone_display(hold) 형태 미러 — 매입가 100 · 목표 120 · 손절 90 · 현재가 110(수익).
const HOLD_ZD: ZoneDisplay = {
  zone: 'waiting',
  label: '보유',
  close: 110,
  mode: 'hold',
  mode_label: '보유 관리',
  pnl_pct: 10,
  marker_fraction: (110 - 90) / (120 - 90),
  anchor_fraction: (100 - 90) / (120 - 90),
  boundaries: { stop: 90, entry: 100, approach_ceiling: 116.4, target: 120 },
  bands: [
    { key: 'exited', tone: 'exited', active: false },
    { key: 'holding', tone: 'waiting', active: true },
    { key: 'near_target', tone: 'approach', active: false },
    { key: 'reached', tone: 'overheated', active: false },
  ],
  ticks: [
    { label: '손절', value: 90 },
    { label: '매입가', value: 100 },
    { label: '목표', value: 120 },
  ],
  rows: [
    { label: '목표', value: 120 },
    { label: '익절 접근', value: 116.4 },
    { label: '매입가', value: 100 },
    { label: '손절', value: 90 },
  ],
}

// 구 응답(폴백) — new_entry 기존 표시 재현.
const LEGACY_ZD: ZoneDisplay = {
  zone: 'entry',
  label: '진입 구간',
  close: 95,
  boundaries: { stop: 90, entry: 100, approach_ceiling: 103, target: 120 },
}

describe('사다리 zone_display 소비 (하드코딩 제거 회귀)', () => {
  it('MiniPriceLadder(hold): 매입가 틱 + 매입가 마커 + 4밴드', () => {
    render(<MiniPriceLadder zoneDisplay={HOLD_ZD} />)
    expect(screen.getByText(/매입가 100/)).toBeInTheDocument() // BE ticks 소비(하드코딩 '진입' 아님)
    expect(screen.getByTestId('mini-ladder-anchor')).toBeInTheDocument() // 매입가 금색 마커
    expect(screen.getByTestId('mini-ladder-marker')).toBeInTheDocument()
  })

  it('PriceLadder(hold): 익절 접근 행 + 활성 밴드 라벨 = zone_display.label', () => {
    render(<PriceLadder zoneDisplay={HOLD_ZD} />)
    expect(screen.getByText('익절 접근')).toBeInTheDocument()
    expect(screen.getByTestId('ladder-band-holding')).toHaveTextContent('보유')
  })

  it('ZoneChip(hold): 손익%(pnl_pct) 표시', () => {
    render(<ZoneChip zoneDisplay={HOLD_ZD} />)
    const chip = screen.getByTestId('zone-chip')
    expect(chip).toHaveTextContent('보유')
    expect(chip).toHaveTextContent('+10.0%')
  })

  it('폴백(구 응답): new_entry 기존 5구간/틱 재현', () => {
    render(<MiniPriceLadder zoneDisplay={LEGACY_ZD} />)
    expect(screen.getByText(/손절 90/)).toBeInTheDocument()
    expect(screen.getByText(/진입 100/)).toBeInTheDocument()
    expect(screen.getByText(/목표 120/)).toBeInTheDocument()
  })

  it('ZoneChip(new_entry): 진입가 대비 %', () => {
    render(<ZoneChip zoneDisplay={LEGACY_ZD} />)
    expect(screen.getByTestId('zone-chip')).toHaveTextContent('-5.0%') // (95-100)/100
  })
})

// ── 빌더 토글 + 보유 필수 검증 + pnl 배지 ────────────────────────────────────

const push = vi.fn()
vi.mock('next/navigation', () => ({ useRouter: () => ({ push }) }))

const invalidateQueries = vi.fn()
vi.mock('@tanstack/react-query', () => ({ useQueryClient: () => ({ invalidateQueries }) }))

vi.mock('@/components/auth/AuthGuard', () => ({
  AuthGuard: ({ children }: { children: React.ReactNode }) => <>{children}</>,
}))

vi.mock('@/hooks/useMonitor', () => ({
  monitorKeys: { lists: () => ['monitor', 'list'] },
  useIndicatorCatalog: () => ({ data: [] }),
  useScenarioSuggest: () => ({ data: { available: false } }),
}))

const create = vi.fn()
const createClaim = vi.fn()
// hold 제안: 현재가 110 반환(pnl 계산용). available=false로 프리필은 억제.
const scenarioSuggest = vi.fn(async (_sym: string, params?: Record<string, string>) => {
  if (params?.mode === 'hold') return { available: true, mode: 'hold', close: 110, captions: {} }
  return { available: false }
})
vi.mock('@/services/monitorService', () => ({
  monitorService: {
    create: (...a: unknown[]) => create(...a),
    createIndicator: vi.fn(),
    createClaim: (...a: unknown[]) => createClaim(...a),
    scenarioSuggest: (...a: [string, Record<string, string>?]) => scenarioSuggest(...a),
  },
}))

import MonitorBuilderPage from '@/app/monitor/new/page'

const FUTURE = '2099-01-01'

function gotoStep4() {
  render(<MonitorBuilderPage />)
  fireEvent.click(screen.getByText('다음'))
  fireEvent.change(screen.getByPlaceholderText('심볼 (예: AAPL)'), { target: { value: 'aapl' } })
  fireEvent.change(screen.getByPlaceholderText('이 모니터의 이름'), { target: { value: '애플' } })
  fireEvent.click(screen.getByText('다음'))
  fireEvent.click(screen.getByText('다음'))
}

beforeEach(() => {
  push.mockReset()
  create.mockReset().mockResolvedValue({ id: 'mon-1' })
  createClaim.mockReset().mockResolvedValue({})
  scenarioSuggest.mockClear()
})

describe('빌더 보유 모드 토글·검증', () => {
  it('보유 관리 토글 → 필드셋 교체(entry↔hold)', () => {
    gotoStep4()
    expect(screen.getByTestId('entry-fieldset')).toBeInTheDocument()
    expect(screen.queryByTestId('hold-fieldset')).toBeNull()
    fireEvent.click(screen.getByTestId('scenario-mode-hold'))
    expect(screen.getByTestId('hold-fieldset')).toBeInTheDocument()
    expect(screen.queryByTestId('entry-fieldset')).toBeNull()
  })

  it('보유 필수 결측 → 에러 + 제출 차단', () => {
    gotoStep4()
    fireEvent.click(screen.getByTestId('scenario-mode-hold'))
    fireEvent.change(screen.getByTestId('hold-purchase-price'), { target: { value: '100' } })
    // 목표/손절/기한 미입력
    expect(screen.getByTestId('scenario-error')).toHaveTextContent('매입가·매입일·목표가·손절가·기한')
    expect(screen.getByText('만들기')).toBeDisabled()
  })

  it('보유 유효 → createClaim(scenario_type=hold + 매입가/매입일)', async () => {
    gotoStep4()
    fireEvent.click(screen.getByTestId('scenario-mode-hold'))
    fireEvent.change(screen.getByTestId('hold-purchase-price'), { target: { value: '100' } })
    fireEvent.change(screen.getByTestId('hold-purchase-date'), { target: { value: '2026-01-01' } })
    fireEvent.change(screen.getByTestId('hold-target-price'), { target: { value: '120' } })
    fireEvent.change(screen.getByTestId('hold-stop-price'), { target: { value: '90' } })
    fireEvent.change(screen.getByTestId('hold-deadline'), { target: { value: FUTURE } })
    expect(screen.queryByTestId('scenario-error')).toBeNull()
    fireEvent.click(screen.getByText('만들기'))
    await waitFor(() => expect(createClaim).toHaveBeenCalled())
    expect(createClaim).toHaveBeenCalledWith(
      expect.objectContaining({
        scenario_type: 'hold',
        purchase_price: '100',
        purchase_date: '2026-01-01',
        target_price: '120',
        stop_price: '90',
        entry_price: null,
      })
    )
  })

  it('stop ≥ target → 에러', () => {
    gotoStep4()
    fireEvent.click(screen.getByTestId('scenario-mode-hold'))
    fireEvent.change(screen.getByTestId('hold-purchase-price'), { target: { value: '100' } })
    fireEvent.change(screen.getByTestId('hold-purchase-date'), { target: { value: '2026-01-01' } })
    fireEvent.change(screen.getByTestId('hold-target-price'), { target: { value: '120' } })
    fireEvent.change(screen.getByTestId('hold-stop-price'), { target: { value: '125' } })
    fireEvent.change(screen.getByTestId('hold-deadline'), { target: { value: FUTURE } })
    expect(screen.getByTestId('scenario-error')).toHaveTextContent('손절가 < 목표가')
  })

  it('pnl 배지 3상태(수익/손실/중립) — 현재가 110 기준', async () => {
    gotoStep4()
    fireEvent.click(screen.getByTestId('scenario-mode-hold'))
    // 수익: 매입 100 < 110
    fireEvent.change(screen.getByTestId('hold-purchase-price'), { target: { value: '100' } })
    await waitFor(() => expect(screen.getByTestId('hold-pnl-badge')).toHaveTextContent('수익'))
    // 손실: 매입 130 > 110
    fireEvent.change(screen.getByTestId('hold-purchase-price'), { target: { value: '130' } })
    await waitFor(() => expect(screen.getByTestId('hold-pnl-badge')).toHaveTextContent('손실'))
    // 중립: 매입 110 ≈ 110 (|pnl|<1%)
    fireEvent.change(screen.getByTestId('hold-purchase-price'), { target: { value: '110' } })
    await waitFor(() => expect(screen.getByTestId('hold-pnl-badge')).toHaveTextContent('중립'))
  })
})
