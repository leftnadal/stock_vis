'use client'

// 2종 대결 화면 (RECON-SWAP-0813 3-B) — 보유 종목 vs 후보(감시 등록 종목 중 사용자 선택).
// 불변 요소 위치: 종합 도장 없음(어느 카드도 점수화하지 않음) · 반론 슬롯(SideColumn) ·
// 결정 일지 게이트(DecisionJournalGate) · 출처 3색 배지(evidence 입력 UI, 통계층 stat 톤) ·
// 판단 불가(SideColumn) · 레인 안내(하단 고정 1줄).
import { useMemo, useState } from 'react'

import { useRouter } from 'next/navigation'
import { AlertCircle } from 'lucide-react'

import { CloseModal } from '@/components/monitor/CloseModal'
import { CandidatePicker } from '@/components/monitor/duel/CandidatePicker'
import { DecisionJournalGate } from '@/components/monitor/duel/DecisionJournalGate'
import { HoldGauge } from '@/components/monitor/duel/HoldGauge'
import { SideColumn } from '@/components/monitor/duel/SideColumn'
import {
  useCreateDecisionJournalEntry,
  useMonitor,
  useMonitorClaims,
  useMonitors,
} from '@/hooks/useMonitor'
import { useHoldings } from '@/hooks/useWallet'
import { P2B_RECOMMIT_SENTENCE } from '@/lib/monitor/duel'
import type { Claim } from '@/types/monitor'

function findHoldClaim(claims: Claim[] | undefined): Claim | null {
  if (!claims) return null
  return (
    claims.find((c) => c.status === 'active' && c.scenario_type === 'hold') ??
    claims.find((c) => c.status === 'active') ??
    null
  )
}

function findHolding(holdings: { symbol: string; avg_cost: string; current_price: string }[] | undefined, symbol: string | undefined) {
  if (!holdings || !symbol) return undefined
  return holdings.find((h) => h.symbol.toUpperCase() === symbol.toUpperCase())
}

export function DuelView({ monitorId }: { monitorId: string }) {
  const router = useRouter()
  const { data: monitor } = useMonitor(monitorId)
  const { data: claims } = useMonitorClaims(monitorId)
  const { data: monitors } = useMonitors()
  const { data: holdings } = useHoldings()

  const [candidateId, setCandidateId] = useState('')
  const { data: candidateClaims } = useMonitorClaims(candidateId)
  const candidateMonitor = useMemo(
    () => (monitors ?? []).find((m) => m.id === candidateId),
    [monitors, candidateId]
  )

  const holdClaim = findHoldClaim(claims)
  const candidateClaim = findHoldClaim(candidateClaims)

  const holding = findHolding(holdings, monitor?.target_ref)
  const candidateHolding = findHolding(holdings, candidateMonitor?.target_ref)

  const [closingClaim, setClosingClaim] = useState<Claim | null>(null)
  const createEntry = useCreateDecisionJournalEntry()
  const [p2bBusy, setP2bBusy] = useState(false)

  const zoneReached = holdClaim?.zone_display?.zone === 'overheated'

  async function handleP2bRecommit() {
    if (!holdClaim) return
    if (!window.confirm('원 목표 도달로 재커밋 처리합니다. 기존 시나리오를 마감할까요?')) return
    setP2bBusy(true)
    try {
      await createEntry.mutateAsync({
        claim: holdClaim.id,
        kind: 'recommit',
        sentence: P2B_RECOMMIT_SENTENCE,
      })
      setClosingClaim(holdClaim)
    } finally {
      setP2bBusy(false)
    }
  }

  if (!monitor) {
    return (
      <div className="py-16 text-center text-gray-400" data-testid="duel-loading">
        불러오는 중…
      </div>
    )
  }

  return (
    <div className="mx-auto max-w-3xl px-4 py-6" data-testid="duel-view">
      <h1 className="mb-1 text-xl font-semibold text-gray-900 dark:text-gray-100">교체 검토</h1>
      <p className="mb-4 text-sm text-gray-500">
        {monitor.name} ({monitor.target_ref}) 보유 유지 여부를 후보와 나란히 비교해요.
      </p>

      <div className="mb-4">
        <CandidatePicker
          monitors={monitors ?? []}
          excludeId={monitorId}
          value={candidateId}
          onChange={setCandidateId}
        />
      </div>

      <div className="mb-4 grid grid-cols-1 gap-4 md:grid-cols-2">
        <SideColumn
          testKey="hold"
          label={`보유 · ${monitor.target_ref}`}
          targetRef={monitor.target_ref}
          claim={holdClaim}
          monitorId={monitorId}
          avgCost={holding?.avg_cost}
          currentPrice={holding?.current_price}
        />
        {candidateId ? (
          <SideColumn
            testKey="candidate"
            label={`후보 · ${candidateMonitor?.target_ref ?? candidateId}`}
            targetRef={candidateMonitor?.target_ref ?? ''}
            claim={candidateClaim}
            monitorId={candidateId}
            avgCost={candidateHolding?.avg_cost}
            currentPrice={candidateHolding?.current_price}
          />
        ) : (
          <div
            className="flex items-center justify-center rounded-xl border border-dashed border-gray-300 p-4 text-sm text-gray-400 dark:border-gray-700"
            data-testid="duel-column-candidate-empty"
          >
            비교할 후보를 선택해 주세요.
          </div>
        )}
      </div>

      {holdClaim && (
        <div className="mb-4 flex flex-col gap-4">
          <HoldGauge
            claimId={holdClaim.id}
            candidateRef={candidateMonitor?.target_ref ?? null}
            holdPnlPct={holdClaim.zone_display?.pnl_pct ?? null}
            holdCurrentPrice={holding?.current_price ?? null}
            candidateCurrentPrice={candidateHolding?.current_price ?? null}
          />

          {zoneReached && (
            <div
              className="flex items-center justify-between gap-3 rounded-lg border border-amber-300 bg-amber-50 px-3 py-2 text-sm text-amber-800 dark:border-amber-700 dark:bg-amber-900/20 dark:text-amber-300"
              data-testid="p2b-banner"
            >
              <span>목표가에 도달했어요 — 목표를 상향해 재커밋할까요?</span>
              <button
                type="button"
                onClick={handleP2bRecommit}
                disabled={p2bBusy}
                data-testid="p2b-recommit-button"
                className="flex-shrink-0 rounded bg-amber-600 px-2.5 py-1 text-xs font-medium text-white hover:bg-amber-700 disabled:opacity-40"
              >
                목표 상향 재커밋
              </button>
            </div>
          )}

          <DecisionJournalGate
            claimId={holdClaim.id}
            onClosed={() => setClosingClaim(holdClaim)}
            onRecommitted={() => router.push('/monitor/new')}
          />
        </div>
      )}

      {/* 레인 안내(v0 정적, 조건 없음) — 불변 요소 */}
      <p
        className="flex items-center gap-1.5 text-xs text-gray-400"
        data-testid="duel-lane-notice"
      >
        <AlertCircle size={12} />
        시장 전체의 이탈 판단은 market_pulse 소관
      </p>

      {closingClaim && (
        <CloseModal
          monitorId={monitorId}
          claimId={closingClaim.id}
          onClose={() => setClosingClaim(null)}
        />
      )}
    </div>
  )
}
