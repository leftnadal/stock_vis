// 손잡이 편집 패널 검증 (Slice 20b) — 슬라이더 범위/스텝 = 검증기 1:1, 저장 PATCH, 에러.
// 훅(useUpdateKnobs)을 mock — 컴포넌트 단위 검증(React Query 실 머신 우회).
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import type { KnobsRead } from '@/types/advisory'

const mutateAsync = vi.fn()
let mutationState = { isPending: false }

vi.mock('@/hooks/useAdvisory', () => ({
  useUpdateKnobs: () => ({
    mutateAsync,
    isPending: mutationState.isPending,
    isError: false,
  }),
}))

import { KnobsPanel } from '@/components/advisory/KnobsPanel'

function knobs(overrides: Partial<KnobsRead> = {}): KnobsRead {
  return {
    available: true,
    target_return_pct: '10.00',
    aggressiveness_offset: 2,
    growth_boost: 1,
    diversification_weight: '0.10',
    concentration_limit: 30,
    exploration_ratio: 10,
    ...overrides,
  }
}

beforeEach(() => {
  mutateAsync.mockReset()
  mutationState = { isPending: false }
})

describe('KnobsPanel 슬라이더 스펙', () => {
  it('슬라이더 5종의 min/max/step이 검증기 정본과 1:1', () => {
    render(<KnobsPanel knobs={knobs()} />)
    const specs: [string, string, string, string][] = [
      ['aggressiveness_offset', '0', '7', '1'],
      ['growth_boost', '0', '7', '1'],
      ['diversification_weight', '0', '0.2', '0.01'],
      ['concentration_limit', '15', '100', '1'],
      ['exploration_ratio', '0', '30', '1'],
    ]
    for (const [key, min, max, step] of specs) {
      const slider = screen.getByTestId(`knob-slider-${key}`)
      expect(slider).toHaveAttribute('min', min)
      expect(slider).toHaveAttribute('max', max)
      expect(slider).toHaveAttribute('step', step)
    }
  })

  it('현재값·목표 수익률을 프리필한다', () => {
    render(<KnobsPanel knobs={knobs()} />)
    expect(screen.getByTestId('knob-value-aggressiveness_offset')).toHaveTextContent('2%p')
    expect(screen.getByTestId('knob-value-diversification_weight')).toHaveTextContent('0.10')
    expect(screen.getByTestId('knob-target-return')).toHaveValue(10)
  })

  it('각 손잡이에 한 줄 설명이 있다 (L 100 = TRIM 소멸 포함)', () => {
    render(<KnobsPanel knobs={knobs()} />)
    expect(screen.getByTestId('knob-concentration_limit')).toHaveTextContent('TRIM 소멸')
  })
})

describe('KnobsPanel 저장 플로우', () => {
  it('슬라이더 조정 → 저장 → mutateAsync(string 페이로드) + 저장 피드백', async () => {
    mutateAsync.mockResolvedValue(knobs({ aggressiveness_offset: 4 }))
    render(<KnobsPanel knobs={knobs()} />)

    const slider = screen.getByTestId('knob-slider-aggressiveness_offset')
    fireEvent.change(slider, { target: { value: '4' } }) // range는 jsdom 키보드 불가
    expect(screen.getByTestId('knob-value-aggressiveness_offset')).toHaveTextContent('4%p')

    fireEvent.click(screen.getByTestId('knobs-save-button'))
    await waitFor(() => expect(mutateAsync).toHaveBeenCalledTimes(1))
    const payload = mutateAsync.mock.calls[0][0]
    expect(payload.aggressiveness_offset).toBe('4')
    expect(payload.target_return_pct).toBe('10.00')
    expect(typeof payload.concentration_limit).toBe('string') // 전부 string 전송

    await waitFor(() => expect(screen.getByTestId('knobs-saved')).toBeInTheDocument())
  })

  it('저장 실패 시 인라인 에러 표시(성공 피드백 없음)', async () => {
    mutateAsync.mockRejectedValue(new Error('400'))
    render(<KnobsPanel knobs={knobs()} />)
    fireEvent.click(screen.getByTestId('knobs-save-button'))
    await waitFor(() => expect(screen.getByTestId('knobs-error')).toBeInTheDocument())
    expect(screen.queryByTestId('knobs-saved')).not.toBeInTheDocument()
  })
})
