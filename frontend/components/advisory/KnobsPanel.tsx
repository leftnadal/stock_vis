'use client'

// 손잡이 5종 + 목표 수익률 편집 패널 (Slice 20b — 20a 읽기전용 → 슬라이더 편집 승격).
// 슬라이더 범위·스텝 = apps/portfolio/models_my.py UserGoal 검증기(KNOB_RANGES) 1:1.
// 저장 = PATCH advisory/knobs/. **저장 ≠ 진단 실행**(D2 — [지금 진단] 별도 경유).
// 서버측 full_clean이 범위 진실 소스 — 슬라이더 클램프는 UX 보조.
import { useEffect, useState } from 'react'

import { useUpdateKnobs } from '@/hooks/useAdvisory'
import type { KnobsRead, KnobsUpdateInput } from '@/types/advisory'

type KnobKey =
  | 'aggressiveness_offset'
  | 'growth_boost'
  | 'diversification_weight'
  | 'concentration_limit'
  | 'exploration_ratio'

interface KnobSpec {
  key: KnobKey
  label: string
  min: number
  max: number
  step: number
  unit: string
  desc: string
}

// 범위·스텝 = 검증기 정본(A 0~7 · G 0~7 · w 0~0.20 · L 15~100 · E 0~30)
const KNOB_SPECS: KnobSpec[] = [
  { key: 'aggressiveness_offset', label: '공격성 오프셋 A', min: 0, max: 7, step: 1, unit: '%p',
    desc: '평소 매수 여력에 상시 더하는 오프셋. 높을수록 기본이 공격적.' },
  { key: 'growth_boost', label: '성장 부스트 G', min: 0, max: 7, step: 1, unit: '%p',
    desc: '신고점 국면에서만 여력에 가산. 상승장 추격 강도.' },
  { key: 'diversification_weight', label: '분산 가중 w', min: 0, max: 0.2, step: 0.01, unit: '',
    desc: '코어 랭킹의 분산 성분 가중. 최대 0.20(신뢰도 지배 상한).' },
  { key: 'concentration_limit', label: '집중도 한도 L', min: 15, max: 100, step: 1, unit: '%',
    desc: 'L 100 = TRIM 소멸(무제한). 낮출수록 한 종목 비중 상한이 타이트.' },
  { key: 'exploration_ratio', label: '탐험 비율 E', min: 0, max: 30, step: 1, unit: '%',
    desc: '여력 중 젊은 후보(탐험 레인)에 배정할 비율.' },
]

function toNum(v: number | string | undefined, fallback: number): number {
  if (v === undefined || v === null || v === '') return fallback
  const n = Number(v)
  return Number.isNaN(n) ? fallback : n
}

interface KnobsPanelProps {
  knobs: KnobsRead
}

export function KnobsPanel({ knobs }: KnobsPanelProps) {
  const updateM = useUpdateKnobs()

  const [values, setValues] = useState<Record<KnobKey, number>>({
    aggressiveness_offset: toNum(knobs.aggressiveness_offset, 0),
    growth_boost: toNum(knobs.growth_boost, 0),
    diversification_weight: toNum(knobs.diversification_weight, 0),
    concentration_limit: toNum(knobs.concentration_limit, 30),
    exploration_ratio: toNum(knobs.exploration_ratio, 0),
  })
  const [target, setTarget] = useState<string>(knobs.target_return_pct ?? '')
  const [saved, setSaved] = useState(false)
  const [saveError, setSaveError] = useState<string | null>(null)

  // 서버 값 변경(저장 후 재검증) 시 로컬 동기화
  useEffect(() => {
    setValues({
      aggressiveness_offset: toNum(knobs.aggressiveness_offset, 0),
      growth_boost: toNum(knobs.growth_boost, 0),
      diversification_weight: toNum(knobs.diversification_weight, 0),
      concentration_limit: toNum(knobs.concentration_limit, 30),
      exploration_ratio: toNum(knobs.exploration_ratio, 0),
    })
    setTarget(knobs.target_return_pct ?? '')
  }, [knobs])

  const setKnob = (key: KnobKey, raw: number) => {
    setValues((prev) => ({ ...prev, [key]: raw }))
    setSaved(false)
  }

  const handleSave = async () => {
    setSaved(false)
    setSaveError(null)
    const payload: KnobsUpdateInput = {
      aggressiveness_offset: String(values.aggressiveness_offset),
      growth_boost: String(values.growth_boost),
      diversification_weight: String(values.diversification_weight),
      concentration_limit: String(values.concentration_limit),
      exploration_ratio: String(values.exploration_ratio),
    }
    if (target !== '') payload.target_return_pct = target
    try {
      await updateM.mutateAsync(payload)
      setSaved(true)
    } catch {
      // 로컬 state로 인라인 에러 표시 (CloseModal 관례)
      setSaveError('저장에 실패했어요. 값을 확인해 주세요.')
    }
  }

  return (
    <div
      data-testid="knobs-panel"
      className="flex flex-col gap-4 rounded-xl border border-gray-200 bg-white p-4 shadow-sm dark:border-gray-800 dark:bg-gray-900"
    >
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-300">성향 손잡이</h3>
        <span className="text-[11px] text-gray-400">저장은 진단을 실행하지 않아요</span>
      </div>

      {/* 목표 수익률 */}
      <div className="flex flex-col gap-1">
        <label htmlFor="knob-target" className="text-[11px] text-gray-400">
          목표 수익률 (연, %)
        </label>
        <input
          id="knob-target"
          data-testid="knob-target-return"
          type="number"
          step="0.5"
          value={target}
          onChange={(e) => {
            setTarget(e.target.value)
            setSaved(false)
          }}
          className="w-32 rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:ring-blue-500 dark:border-gray-600 dark:bg-gray-700 dark:text-white"
          placeholder="예: 12"
        />
      </div>

      {/* 손잡이 5종 슬라이더 */}
      <div className="flex flex-col gap-4">
        {KNOB_SPECS.map((spec) => {
          const v = values[spec.key]
          return (
            <div key={spec.key} data-testid={`knob-${spec.key}`} className="flex flex-col gap-1">
              <div className="flex items-center justify-between">
                <span className="text-xs font-medium text-gray-700 dark:text-gray-300">{spec.label}</span>
                <span
                  data-testid={`knob-value-${spec.key}`}
                  className="text-sm font-semibold tabular-nums text-gray-900 dark:text-gray-100"
                >
                  {spec.step < 1 ? v.toFixed(2) : v}
                  {spec.unit}
                </span>
              </div>
              <input
                type="range"
                data-testid={`knob-slider-${spec.key}`}
                aria-label={spec.label}
                min={spec.min}
                max={spec.max}
                step={spec.step}
                value={v}
                onChange={(e) => setKnob(spec.key, Number(e.target.value))}
                className="w-full accent-blue-600"
              />
              <div className="flex justify-between text-[10px] text-gray-400">
                <span>{spec.min}{spec.unit}</span>
                <span>{spec.max}{spec.unit}</span>
              </div>
              <p className="text-[11px] text-gray-400">{spec.desc}</p>
            </div>
          )
        })}
      </div>

      {/* 저장 + 피드백 */}
      <div className="flex items-center gap-3">
        <button
          type="button"
          data-testid="knobs-save-button"
          onClick={handleSave}
          disabled={updateM.isPending}
          className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-semibold text-white hover:bg-blue-700 disabled:cursor-not-allowed disabled:bg-slate-300"
        >
          {updateM.isPending ? '저장 중...' : '손잡이 저장'}
        </button>
        {saved && !updateM.isPending && (
          <span data-testid="knobs-saved" className="text-sm text-green-600 dark:text-green-400">
            저장됐어요
          </span>
        )}
        {saveError && (
          <span data-testid="knobs-error" role="alert" className="text-sm text-red-600">
            {saveError}
          </span>
        )}
      </div>
    </div>
  )
}
