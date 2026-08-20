'use client'

// P-1 보류 계기판 (RECON-SWAP-0813 3-B) — "보류" 클릭 이력을 집계 표시. 2회째부터 누적 일수 노출.
// 갭 2: SwapHoldLog가 보류 시점 hold_price/candidate_price 스냅샷을 기록 → 2회째부터
// 최초 보류 스냅샷 대비 현재가로 "양측 기간 성과·격차"를 실산출한다(computeHoldGaugePerformance).
// 스냅샷 신설 이전 구 기록(가격 null)은 "성과 앵커 없음(구 기록)"으로 정직 표기(조작 금지).
// 후보 현재가는 부모(DuelView)가 Wallet 보유분에서만 넘겨준다 — 후보를 보유하지 않으면 소스가
// 없어 "현재가 데이터 없음"으로 표기된다(감시 등록 종목 전용 가격 API 부재, 지어내지 않음).
import { Loader2 } from 'lucide-react'
import { useState } from 'react'

import { useCreateSwapHoldLog, useSwapHoldLogs } from '@/hooks/useMonitor'
import { computeHoldGaugePerformance, summarizeHoldGauge } from '@/lib/monitor/duel'

interface HoldGaugeProps {
  claimId: string
  candidateRef: string | null
  holdPnlPct?: number | null
  holdCurrentPrice?: string | null
  candidateCurrentPrice?: string | null
}

function formatPct(pct: number): string {
  return `${pct >= 0 ? '+' : ''}${pct.toFixed(1)}%`
}

export function HoldGauge({
  claimId,
  candidateRef,
  holdPnlPct,
  holdCurrentPrice,
  candidateCurrentPrice,
}: HoldGaugeProps) {
  const { data: logs } = useSwapHoldLogs(claimId)
  const createHoldLog = useCreateSwapHoldLog()
  const [note, setNote] = useState('')

  const summary = summarizeHoldGauge(logs ?? [])
  const performance = computeHoldGaugePerformance(logs ?? [], holdCurrentPrice, candidateCurrentPrice)

  async function handleHold() {
    await createHoldLog.mutateAsync({
      claim: claimId,
      candidate_ref: candidateRef ?? undefined,
      note: note.trim() || undefined,
      hold_price: holdCurrentPrice ?? undefined,
      candidate_price: candidateCurrentPrice ?? undefined,
    })
    setNote('')
  }

  return (
    <div
      className="rounded-xl border border-gray-200 p-4 dark:border-gray-700"
      data-testid="hold-gauge"
    >
      <div className="mb-2 flex items-center justify-between">
        <h3 className="font-medium text-gray-800 dark:text-gray-100">보류 계기판</h3>
        {summary.count > 0 && (
          <span
            data-testid="hold-gauge-count"
            className="rounded-full bg-gray-100 px-2 py-0.5 text-xs font-medium text-gray-600 dark:bg-gray-800 dark:text-gray-300"
          >
            {summary.count}회째 보류
          </span>
        )}
      </div>

      {summary.count >= 2 && (
        <div
          className="mb-3 flex flex-col gap-1 rounded-lg bg-gray-50 p-2.5 text-xs text-gray-600 dark:bg-gray-800 dark:text-gray-300"
          data-testid="hold-gauge-cumulative"
        >
          <p>누적 보류 {summary.cumulativeDays}일</p>
          <p>
            보유 · 매입 이후 손익(참고 — 보류 시점 기준 아님):{' '}
            {holdPnlPct != null ? `${holdPnlPct >= 0 ? '+' : ''}${holdPnlPct.toFixed(1)}%` : '데이터 없음'}
          </p>
          <div
            className="mt-1 flex flex-col gap-0.5 border-t border-gray-200 pt-1.5 dark:border-gray-700"
            data-testid="hold-gauge-performance"
          >
            <p className="text-[11px] font-medium text-gray-500">
              최초 보류 시점 스냅샷 대비 기간 성과
            </p>
            <p data-testid="hold-gauge-hold-performance">
              보유:{' '}
              {performance.holdPerformancePct != null
                ? formatPct(performance.holdPerformancePct)
                : performance.holdPerformanceReason === 'anchor_missing'
                  ? '성과 앵커 없음(구 기록)'
                  : '현재가 데이터 없음'}
            </p>
            <p data-testid="hold-gauge-candidate-performance">
              후보:{' '}
              {performance.candidatePerformancePct != null
                ? formatPct(performance.candidatePerformancePct)
                : performance.candidatePerformanceReason === 'anchor_missing'
                  ? '성과 앵커 없음(구 기록)'
                  : '현재가 데이터 없음'}
            </p>
            <p data-testid="hold-gauge-gap">
              격차(보유−후보): {performance.gapPct != null ? `${formatPct(performance.gapPct)}p` : '산출 불가'}
            </p>
          </div>
        </div>
      )}

      <div className="flex flex-col gap-2">
        <input
          value={note}
          onChange={(e) => setNote(e.target.value)}
          placeholder="보류 메모(선택)"
          data-testid="hold-gauge-note-input"
          className="rounded-lg border border-gray-300 px-3 py-1.5 text-sm dark:border-gray-700 dark:bg-gray-900"
        />
        <button
          type="button"
          onClick={handleHold}
          disabled={createHoldLog.isPending}
          data-testid="hold-gauge-submit"
          className="inline-flex w-fit items-center gap-2 rounded-lg border border-gray-300 px-4 py-1.5 text-sm font-medium text-gray-700 hover:bg-gray-50 disabled:opacity-40 dark:border-gray-700 dark:text-gray-200 dark:hover:bg-gray-800"
        >
          {createHoldLog.isPending && <Loader2 size={14} className="animate-spin" />}
          보류
        </button>
      </div>
    </div>
  )
}
