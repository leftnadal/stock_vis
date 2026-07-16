'use client'

// 매수 시나리오 마감 모달 (MON-CLOSE-UI Phase 2 · TIMING-P2 어휘, 설계 0.1 A-1 단일 스크롤).
// 열기 → close-preview 프리필(proposed_verdict 프리셀렉트) → 제출 → close POST
// (미선택 지표는 indicator_results에서 제외) → 성공 시 닫고 캐시 무효화.
// 409(이미 마감)는 안내 후 닫고 재조회, 그 외 오류는 모달 유지 + 인라인 에러(입력 보존).
import { useEffect, useState } from 'react'

import { useQueryClient } from '@tanstack/react-query'
import { AlertTriangle, Loader2 } from 'lucide-react'

import { monitorKeys, useCloseClaim, useClosePreview } from '@/hooks/useMonitor'
import { VERDICT_META, VERDICT_OPTIONS } from '@/lib/monitor/verdictLabels'
import type { FactorTag, IndicatorResultValue, ProposedVerdict } from '@/types/monitor'

interface CloseModalProps {
  monitorId: string
  claimId: string
  onClose: () => void
}

const RESULT_CHIPS: { key: IndicatorResultValue; label: string }[] = [
  { key: 'hit', label: '맞음' },
  { key: 'partial', label: '부분' },
  { key: 'miss', label: '빗나감' },
  { key: 'na', label: 'N/A' },
]

const FACTOR_TAG_OPTIONS: { key: FactorTag; label: string }[] = [
  { key: 'timing', label: '타이밍' },
  { key: 'ext_shock', label: '외부충격' },
  { key: 'indicator_noise', label: '지표노이즈' },
  { key: 'luck', label: '운' },
]

function extractStatus(error: unknown): number | undefined {
  return (error as { response?: { status?: number } } | undefined)?.response?.status
}

export function CloseModal({ monitorId, claimId, onClose }: CloseModalProps) {
  const qc = useQueryClient()
  const { data: preview, isLoading, isError: previewError } = useClosePreview(claimId, true)
  const closeClaim = useCloseClaim()

  const [verdict, setVerdict] = useState<ProposedVerdict | null>(null)
  const [results, setResults] = useState<Record<string, IndicatorResultValue>>({})
  const [tags, setTags] = useState<Set<FactorTag>>(new Set())
  const [memo, setMemo] = useState('')
  const [alreadyClosed, setAlreadyClosed] = useState(false)
  const [submitError, setSubmitError] = useState<string | null>(null)

  // 프리필: proposed_verdict를 최초 1회만 프리셀렉트(사용자가 이후 바꾼 선택을 덮지 않음).
  useEffect(() => {
    if (preview && verdict === null) {
      setVerdict(preview.proposed_verdict)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [preview])

  function toggleResult(indicatorId: string, value: IndicatorResultValue) {
    setResults((prev) => {
      const next = { ...prev }
      if (next[indicatorId] === value) delete next[indicatorId]
      else next[indicatorId] = value
      return next
    })
  }

  function toggleTag(tag: FactorTag) {
    setTags((prev) => {
      const next = new Set(prev)
      if (next.has(tag)) next.delete(tag)
      else next.add(tag)
      return next
    })
  }

  async function handleSubmit() {
    if (!verdict) return
    setSubmitError(null)
    try {
      await closeClaim.mutateAsync({
        claimId,
        monitorId,
        payload: {
          final_verdict: verdict,
          factor_tags: Array.from(tags),
          retro_memo: memo.trim() || undefined,
          indicator_results: Object.entries(results).map(([indicator_id, result]) => ({
            indicator_id,
            result,
          })),
        },
      })
      onClose()
    } catch (e: unknown) {
      if (extractStatus(e) === 409) {
        // 이미 마감됨 — 안내 후 닫고 재조회(로컬 입력 보존 불필요, 조회 무효화만).
        qc.invalidateQueries({ queryKey: monitorKeys.claims() })
        qc.invalidateQueries({ queryKey: monitorKeys.detail(monitorId) })
        qc.invalidateQueries({ queryKey: monitorKeys.lists() })
        setAlreadyClosed(true)
      } else {
        setSubmitError('마감 처리 중 오류가 발생했어요. 다시 시도해 주세요.')
      }
    }
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-end justify-center bg-black/50 sm:items-center"
      data-testid="close-modal"
    >
      <div className="flex max-h-[90vh] w-full max-w-md flex-col overflow-hidden rounded-t-2xl bg-white dark:bg-gray-900 sm:rounded-2xl">
        {alreadyClosed ? (
          <div className="flex flex-col items-center gap-4 p-8 text-center">
            <p className="text-gray-800 dark:text-gray-100">이미 마감된 시나리오입니다.</p>
            <button
              type="button"
              onClick={onClose}
              data-testid="close-modal-ack"
              className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700"
            >
              확인
            </button>
          </div>
        ) : (
          <>
            <div className="flex-1 overflow-y-auto p-5">
              <h2 className="mb-4 font-semibold text-gray-900 dark:text-gray-100">
                매수 시나리오 마감
              </h2>

              {isLoading && <p className="py-8 text-center text-gray-400">불러오는 중…</p>}
              {previewError && (
                <p className="py-8 text-center text-red-500">
                  프리필 정보를 불러오지 못했어요.
                </p>
              )}

              {preview && (
                <>
                  {/* 1. 제안 배너 (expired면 기한만료 안내) */}
                  <div
                    className="mb-4 rounded-lg bg-blue-50 px-3 py-2 text-sm text-blue-800 dark:bg-blue-900/30 dark:text-blue-200"
                    data-testid="close-modal-proposal-banner"
                  >
                    시스템 제안: {VERDICT_META[preview.proposed_verdict].label}
                    <span className="ml-1 block text-xs text-blue-600 dark:text-blue-300">
                      {preview.proposed_verdict === 'expired'
                        ? '기한 경과 · 진입 구간 미도달'
                        : `overall_score ${preview.overall_score.toFixed(3)} · 밴드 [−0.333, +0.333]`}
                    </span>
                  </div>

                  {/* 2. 판정 버튼 (익절/부분 실현/손절/기한만료) */}
                  <div className="mb-5">
                    <p className="mb-2 text-sm font-medium text-gray-700 dark:text-gray-300">
                      판정
                    </p>
                    <div className="grid grid-cols-2 gap-2">
                      {VERDICT_OPTIONS.map((opt) => {
                        const active = verdict === opt.key
                        const suggested = preview.proposed_verdict === opt.key
                        return (
                          <button
                            key={opt.key}
                            type="button"
                            onClick={() => setVerdict(opt.key)}
                            data-testid={`close-modal-verdict-${opt.key}`}
                            aria-pressed={active}
                            className={`rounded-lg border px-2 py-2 text-sm transition ${
                              active
                                ? 'border-blue-500 bg-blue-50 ring-2 ring-blue-400 dark:bg-blue-900/30'
                                : 'border-gray-200 dark:border-gray-700'
                            }`}
                          >
                            {opt.label}
                            {suggested && (
                              <span className="mt-0.5 block text-[10px] text-gray-400">
                                시스템 제안
                              </span>
                            )}
                          </button>
                        )
                      })}
                    </div>
                  </div>

                  {/* 3. 지표별 결과 (6개 초과 시 이 섹션만 내부 스크롤) */}
                  {preview.indicators.length > 0 && (
                    <div className="mb-5">
                      <p className="mb-2 text-sm font-medium text-gray-700 dark:text-gray-300">
                        지표별 결과
                      </p>
                      <div
                        className={`flex flex-col gap-2 ${
                          preview.indicators.length > 6 ? 'max-h-56 overflow-y-auto pr-1' : ''
                        }`}
                        data-testid="close-modal-indicators"
                      >
                        {preview.indicators.map((ind) => (
                          <div key={ind.id} className="flex items-center justify-between gap-2">
                            <span className="min-w-0 flex-1 truncate text-sm text-gray-600 dark:text-gray-300">
                              {ind.name}
                            </span>
                            <div className="flex gap-1">
                              {RESULT_CHIPS.map((r) => (
                                <button
                                  key={r.key}
                                  type="button"
                                  onClick={() => toggleResult(ind.id, r.key)}
                                  data-testid={`close-modal-indicator-${ind.id}-${r.key}`}
                                  aria-pressed={results[ind.id] === r.key}
                                  className={`rounded px-1.5 py-0.5 text-[11px] ${
                                    results[ind.id] === r.key
                                      ? 'bg-blue-600 text-white'
                                      : 'bg-gray-100 text-gray-500 dark:bg-gray-800 dark:text-gray-400'
                                  }`}
                                >
                                  {r.label}
                                </button>
                              ))}
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* 4. 요인 태그 */}
                  <div className="mb-5">
                    <p className="mb-2 text-sm font-medium text-gray-700 dark:text-gray-300">
                      요인 태그 (선택)
                    </p>
                    <div className="flex flex-wrap gap-2">
                      {FACTOR_TAG_OPTIONS.map((t) => (
                        <button
                          key={t.key}
                          type="button"
                          onClick={() => toggleTag(t.key)}
                          data-testid={`close-modal-tag-${t.key}`}
                          aria-pressed={tags.has(t.key)}
                          className={`rounded-full px-3 py-1 text-xs ${
                            tags.has(t.key)
                              ? 'bg-blue-600 text-white'
                              : 'bg-gray-100 text-gray-600 dark:bg-gray-800 dark:text-gray-300'
                          }`}
                        >
                          {t.label}
                        </button>
                      ))}
                    </div>
                  </div>

                  {/* 5. 한 줄 회고 */}
                  <div>
                    <label
                      htmlFor="close-modal-memo-input"
                      className="mb-2 block text-sm font-medium text-gray-700 dark:text-gray-300"
                    >
                      한 줄 회고 (선택)
                    </label>
                    <input
                      id="close-modal-memo-input"
                      value={memo}
                      onChange={(e) => setMemo(e.target.value)}
                      placeholder="예: 실적 발표 타이밍이 예상보다 늦었다"
                      data-testid="close-modal-memo"
                      className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm dark:border-gray-700 dark:bg-gray-900"
                    />
                  </div>
                </>
              )}
            </div>

            {/* 6. 동결 경고 + 확정 — sticky 푸터(항상 노출) */}
            {preview && (
              <div className="sticky bottom-0 border-t border-gray-200 bg-white p-4 dark:border-gray-700 dark:bg-gray-900">
                {submitError && (
                  <p className="mb-2 text-xs text-red-500" data-testid="close-modal-error">
                    {submitError}
                  </p>
                )}
                <div className="mb-3 flex items-start gap-2 text-xs text-amber-700 dark:text-amber-400">
                  <AlertTriangle size={14} className="mt-0.5 flex-shrink-0" />
                  <span>
                    확정 시 현재 지표·점수·달 위상이 스냅샷으로 동결되며 되돌릴 수 없습니다.
                  </span>
                </div>
                <div className="flex gap-2">
                  <button
                    type="button"
                    onClick={onClose}
                    className="flex-1 rounded-lg border border-gray-300 px-4 py-2 text-sm text-gray-600 dark:border-gray-700 dark:text-gray-300"
                  >
                    취소
                  </button>
                  <button
                    type="button"
                    onClick={handleSubmit}
                    disabled={!verdict || closeClaim.isPending}
                    data-testid="close-modal-submit"
                    className="flex flex-1 items-center justify-center gap-2 rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white disabled:opacity-40"
                  >
                    {closeClaim.isPending && <Loader2 size={14} className="animate-spin" />}
                    마감 확정 · 동결
                  </button>
                </div>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  )
}
