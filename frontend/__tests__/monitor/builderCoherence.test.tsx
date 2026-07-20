// TIMING-P2.5 빌더 정합 — 프리필(빈 칸만) · 정합 힌트(양방향·자동 개서 금지) · R:R.
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

const push = vi.fn()
vi.mock('next/navigation', () => ({ useRouter: () => ({ push }) }))
vi.mock('@tanstack/react-query', () => ({ useQueryClient: () => ({ invalidateQueries: vi.fn() }) }))
vi.mock('@/components/auth/AuthGuard', () => ({
  AuthGuard: ({ children }: { children: React.ReactNode }) => <>{children}</>,
}))

// 프리필 소스 — 4필드 + 캡션 모두 제공.
const PREFILL = {
  available: true,
  symbol: 'MSFT',
  entry_suggest: 349.2,
  target_suggest: 420,
  stop_suggest: 324.94,
  deadline_suggest: '2026-11-01',
  rr_suggest: 2.1,
  captions: { entry: '스윙 저점', stop: 'ATR×2', target: '스윙 고점', deadline: '변동성 기준 ~6주' },
  basis: 'prefill basis',
}
vi.mock('@/hooks/useMonitor', () => ({
  monitorKeys: { lists: () => ['monitor', 'list'] },
  useIndicatorCatalog: () => ({ data: [] }),
  useScenarioSuggest: () => ({ data: PREFILL }),
}))

// 재계산: 마지막 수정 필드에 따라 coherence 반환.
const scenarioSuggest = vi.fn(async (_sym: string, params?: Record<string, string>) => {
  if (params?.target) {
    return { coherence: { symbol: 'MSFT', sigma: 0.018, note: '변동성 기준 정합 · 예측 아님',
      basis: '목표 500이면 변동성 기준 ~12주', coherent_horizon_days: 84, coherent_deadline: '2027-01-10', rr: 3.0 } }
  }
  if (params?.deadline) {
    return { coherence: { symbol: 'MSFT', sigma: 0.018, note: '변동성 기준 정합 · 예측 아님',
      basis: '기한 ~10주면 목표 410', coherent_target: '410' } }
  }
  return { available: false, symbol: 'MSFT' }
})
vi.mock('@/services/monitorService', () => ({
  monitorService: {
    create: vi.fn(async () => ({ id: 'm1' })),
    createIndicator: vi.fn(),
    createClaim: vi.fn(),
    scenarioSuggest: (s: string, p?: Record<string, string>) => scenarioSuggest(s, p),
  },
}))

import MonitorBuilderPage from '@/app/monitor/new/page'

function gotoStep4() {
  render(<MonitorBuilderPage />)
  fireEvent.click(screen.getByText('다음'))
  fireEvent.change(screen.getByPlaceholderText('심볼 (예: AAPL)'), { target: { value: 'msft' } })
  fireEvent.change(screen.getByPlaceholderText('이 모니터의 이름'), { target: { value: 'x' } })
  fireEvent.click(screen.getByText('다음'))
  fireEvent.click(screen.getByText('다음'))
}

beforeEach(() => {
  push.mockReset()
  scenarioSuggest.mockClear()
})

describe('TIMING-P2.5 빌더 정합', () => {
  it('4단계 진입 시 4필드 프리필 + 캡션', () => {
    gotoStep4()
    expect(screen.getByTestId('scenario-entry-price')).toHaveValue(349.2)
    expect(screen.getByTestId('scenario-target-price')).toHaveValue(420)
    expect(screen.getByTestId('scenario-stop-price')).toHaveValue(324.94)
    expect(screen.getByTestId('scenario-deadline')).toHaveValue('2026-11-01')
    expect(screen.getByText('스윙 저점')).toBeInTheDocument()
    expect(screen.getByText('변동성 기준 ~6주')).toBeInTheDocument()
  })

  it('R:R 표시 + "예측 아님" 고지', () => {
    gotoStep4()
    // (420-349.2)/(349.2-324.94) = 70.8/24.26 = 2.9
    expect(screen.getByTestId('scenario-rr')).toHaveTextContent('손익비 2.9 : 1')
    expect(screen.getByTestId('scenario-rr')).toHaveTextContent('예측 아님')
  })

  it('목표가 수정 → 기한 힌트 표시 + [재제안 적용]', async () => {
    gotoStep4()
    fireEvent.change(screen.getByTestId('scenario-target-price'), { target: { value: '500' } })
    await waitFor(() => expect(screen.getByTestId('scenario-deadline-hint')).toBeInTheDocument(), { timeout: 1500 })
    expect(screen.getByTestId('scenario-deadline-hint')).toHaveTextContent('~12주')
    // [재제안 적용] → 기한이 정합값으로 (자동 아님 — 클릭해야)
    fireEvent.click(screen.getByTestId('scenario-deadline-hint-apply'))
    expect(screen.getByTestId('scenario-deadline')).toHaveValue('2027-01-10')
  })

  it('기한 수정 → 목표 힌트 표시 + [적용]', async () => {
    gotoStep4()
    fireEvent.change(screen.getByTestId('scenario-deadline'), { target: { value: '2027-02-01' } })
    await waitFor(() => expect(screen.getByTestId('scenario-target-hint')).toBeInTheDocument(), { timeout: 1500 })
    expect(screen.getByTestId('scenario-target-hint')).toHaveTextContent('목표 410')
    fireEvent.click(screen.getByTestId('scenario-target-hint-apply'))
    expect(screen.getByTestId('scenario-target-price')).toHaveValue(410)
  })

  it('디바운스: 연속 입력 중 마지막 1회만 호출', async () => {
    gotoStep4()
    scenarioSuggest.mockClear()
    const t = screen.getByTestId('scenario-target-price')
    fireEvent.change(t, { target: { value: '500' } })
    fireEvent.change(t, { target: { value: '510' } })
    fireEvent.change(t, { target: { value: '520' } })
    await waitFor(() => expect(screen.getByTestId('scenario-deadline-hint')).toBeInTheDocument(), { timeout: 1500 })
    // 디바운스로 마지막 값만 호출(3회 아님)
    const targetCalls = scenarioSuggest.mock.calls.filter((c) => c[1]?.target)
    expect(targetCalls.length).toBe(1)
    expect(targetCalls[0][1]?.target).toBe('520')
  })
})
