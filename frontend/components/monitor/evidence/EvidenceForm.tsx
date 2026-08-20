'use client'

// 근거 입력 폼 (RECON-SWAP-0813 3-A) — 자동형(지표+연산자+임계+유예)/수동형(서술+재확인주기) 토글.
// POST /monitor/claim-evidences/. 고지 2건(관측 불가능 근거·갭 체질 배지)은 EvidenceModal이 감싼다.
import { useState } from 'react'
import { Loader2 } from 'lucide-react'

import { useCreateClaimEvidence, useIndicators } from '@/hooks/useMonitor'
import type { EvidenceKind, EvidenceOperator } from '@/types/monitor'

interface EvidenceFormProps {
  claimId: string
  monitorId: string
  onCreated?: () => void
  // 반론 채택 프리필 (P-2a, RECON-SWAP-0813 갭 1) — 지정 시 초기 kind/서술을 덮어쓴다.
  // 마운트 시 1회만 반영(제어값 아님) — 사용자가 이후 자유롭게 고쳐 쓸 수 있다.
  initialKind?: EvidenceKind
  initialDescription?: string
}

const OPERATORS: { key: EvidenceOperator; label: string }[] = [
  { key: 'gte', label: '≥' },
  { key: 'lte', label: '≤' },
  { key: 'gt', label: '>' },
  { key: 'lt', label: '<' },
]

export function EvidenceForm({
  claimId,
  monitorId,
  onCreated,
  initialKind,
  initialDescription,
}: EvidenceFormProps) {
  const { data: indicators } = useIndicators(monitorId)
  const createEvidence = useCreateClaimEvidence()

  const [kind, setKind] = useState<EvidenceKind>(initialKind ?? 'auto')
  const [indicatorId, setIndicatorId] = useState('')
  const [operator, setOperator] = useState<EvidenceOperator>('gte')
  const [threshold, setThreshold] = useState('')
  const [graceDays, setGraceDays] = useState('5')
  const [description, setDescription] = useState(initialDescription ?? '')
  const [recheckDays, setRecheckDays] = useState('90')
  const [error, setError] = useState<string | null>(null)

  const canSubmit =
    kind === 'auto'
      ? indicatorId !== '' && threshold.trim() !== '' && !Number.isNaN(Number(threshold))
      : description.trim() !== ''

  async function handleSubmit() {
    if (!canSubmit) return
    setError(null)
    try {
      if (kind === 'auto') {
        await createEvidence.mutateAsync({
          claim: claimId,
          kind: 'auto',
          indicator: indicatorId,
          operator,
          threshold: Number(threshold),
          grace_days: Number(graceDays) || 5,
        })
      } else {
        await createEvidence.mutateAsync({
          claim: claimId,
          kind: 'manual',
          description: description.trim(),
          recheck_period_days: Number(recheckDays) || 90,
        })
      }
      setIndicatorId('')
      setThreshold('')
      setDescription('')
      onCreated?.()
    } catch {
      setError('근거 저장에 실패했어요. 다시 시도해 주세요.')
    }
  }

  return (
    <div className="flex flex-col gap-3" data-testid="evidence-form">
      <div className="grid grid-cols-2 gap-1.5" data-testid="evidence-kind-toggle">
        <button
          type="button"
          onClick={() => setKind('auto')}
          data-testid="evidence-kind-auto"
          aria-pressed={kind === 'auto'}
          className={`rounded-lg border px-2 py-1.5 text-xs font-medium transition ${
            kind === 'auto'
              ? 'border-blue-500 bg-blue-50 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300'
              : 'border-gray-200 text-gray-600 dark:border-gray-700 dark:text-gray-300'
          }`}
        >
          자동형(지표)
        </button>
        <button
          type="button"
          onClick={() => setKind('manual')}
          data-testid="evidence-kind-manual"
          aria-pressed={kind === 'manual'}
          className={`rounded-lg border px-2 py-1.5 text-xs font-medium transition ${
            kind === 'manual'
              ? 'border-purple-500 bg-purple-50 text-purple-700 dark:bg-purple-900/30 dark:text-purple-300'
              : 'border-gray-200 text-gray-600 dark:border-gray-700 dark:text-gray-300'
          }`}
        >
          수동형(서술)
        </button>
      </div>

      {kind === 'auto' ? (
        <div className="flex flex-col gap-2" data-testid="evidence-auto-fieldset">
          <label className="text-xs text-gray-500">
            지표
            <select
              value={indicatorId}
              onChange={(e) => setIndicatorId(e.target.value)}
              data-testid="evidence-indicator-select"
              className="mt-1 w-full rounded-lg border border-gray-300 px-2 py-1.5 text-sm dark:border-gray-700 dark:bg-gray-900"
            >
              <option value="">선택</option>
              {(indicators ?? []).map((ind) => (
                <option key={ind.id} value={ind.id}>
                  {ind.name}
                </option>
              ))}
            </select>
          </label>
          <div className="grid grid-cols-3 gap-2">
            <label className="text-xs text-gray-500">
              연산자
              <select
                value={operator}
                onChange={(e) => setOperator(e.target.value as EvidenceOperator)}
                data-testid="evidence-operator-select"
                className="mt-1 w-full rounded-lg border border-gray-300 px-2 py-1.5 text-sm dark:border-gray-700 dark:bg-gray-900"
              >
                {OPERATORS.map((o) => (
                  <option key={o.key} value={o.key}>
                    {o.label}
                  </option>
                ))}
              </select>
            </label>
            <label className="text-xs text-gray-500">
              임계 z
              <input
                type="number"
                inputMode="decimal"
                value={threshold}
                onChange={(e) => setThreshold(e.target.value)}
                data-testid="evidence-threshold-input"
                placeholder="0.3"
                className="mt-1 w-full rounded-lg border border-gray-300 px-2 py-1.5 text-sm dark:border-gray-700 dark:bg-gray-900"
              />
            </label>
            <label className="text-xs text-gray-500">
              유예(거래일)
              <input
                type="number"
                inputMode="numeric"
                value={graceDays}
                onChange={(e) => setGraceDays(e.target.value)}
                data-testid="evidence-grace-days-input"
                className="mt-1 w-full rounded-lg border border-gray-300 px-2 py-1.5 text-sm dark:border-gray-700 dark:bg-gray-900"
              />
            </label>
          </div>
          {(indicators ?? []).length === 0 && (
            <p className="text-[11px] text-gray-400">
              이 모니터에 부착된 지표가 없어요 — 먼저 지표를 추가해야 자동형 근거를 만들 수 있어요.
            </p>
          )}
        </div>
      ) : (
        <div className="flex flex-col gap-2" data-testid="evidence-manual-fieldset">
          <label className="text-xs text-gray-500">
            서술
            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              data-testid="evidence-description-input"
              placeholder="예: AI 인프라 테마 열기 지속"
              rows={2}
              className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 text-sm dark:border-gray-700 dark:bg-gray-900"
            />
          </label>
          <label className="text-xs text-gray-500">
            재확인 주기(일)
            <input
              type="number"
              inputMode="numeric"
              value={recheckDays}
              onChange={(e) => setRecheckDays(e.target.value)}
              data-testid="evidence-recheck-days-input"
              className="mt-1 w-24 rounded-lg border border-gray-300 px-2 py-1.5 text-sm dark:border-gray-700 dark:bg-gray-900"
            />
          </label>
        </div>
      )}

      {error && (
        <p className="text-xs text-red-500" data-testid="evidence-form-error">
          {error}
        </p>
      )}

      <button
        type="button"
        onClick={handleSubmit}
        disabled={!canSubmit || createEvidence.isPending}
        data-testid="evidence-form-submit"
        className="inline-flex items-center justify-center gap-2 self-start rounded-lg bg-blue-600 px-4 py-1.5 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-40"
      >
        {createEvidence.isPending && <Loader2 size={14} className="animate-spin" />}
        근거 추가
      </button>
    </div>
  )
}
