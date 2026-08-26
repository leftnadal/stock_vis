'use client'

// 대결 화면 한 편(보유 또는 후보) — 계약층/마찰층/통계층 + 반론 의무 슬롯 (RECON-SWAP-0813 3-B).
// 종합 도장 없음(불변 요소) — 여기서 산출하는 값은 전부 사실 나열이지 판정이 아니다.
// P-2a(갭 1): 반론 슬롯에 "이 반론을 감시 근거로 등록" CTA를 추가 — 반론을 홀드 사유로
// 채택하면 그 즉시 관측 가능 조건(근거)으로 등록하는 흐름으로 유도한다(공짜 홀드 금지, ADR §3.8).
import { useState } from 'react'
import { AlertTriangle, ShieldPlus } from 'lucide-react'

import { SourceBadge } from '@/components/monitor/SourceBadge'
import { EvidenceForm } from '@/components/monitor/evidence/EvidenceForm'
import { EvidenceModal } from '@/components/monitor/evidence/EvidenceModal'
import { useEvidenceStatus } from '@/hooks/useMonitor'
import { gapMultiplierFor } from '@/constants/gapProfile'
import {
  buildCounterArgument,
  checkJudgmentAvailability,
  estimateFriction,
  summarizeEvidenceStatus,
} from '@/lib/monitor/duel'
import { EVIDENCE_STATUS_META } from '@/lib/monitor/evidence'
import type { Claim } from '@/types/monitor'
import { formatPctRule } from '@/utils/formatters'

interface SideColumnProps {
  testKey: string // testid 접미(안정적 영문 키 — label은 한글일 수 있어 별도 전달)
  label: string
  targetRef: string
  claim: Claim | null | undefined
  monitorId?: string // 반론 채택 시 EvidenceForm 지표 카탈로그 조회용(P-2a)
  avgCost?: string | null
  currentPrice?: string | null
}

export function SideColumn({
  testKey,
  label,
  targetRef,
  claim,
  monitorId,
  avgCost,
  currentPrice,
}: SideColumnProps) {
  const claimId = claim?.id ?? ''
  const { data: status } = useEvidenceStatus(claimId, undefined, !!claimId)
  const [adopting, setAdopting] = useState(false)
  // C-1: "판단 불가" 카드에서 바로 근거 관리 모달을 열기 위한 로컬 토글.
  const [evidenceOpen, setEvidenceOpen] = useState(false)
  const summary = summarizeEvidenceStatus(status)
  const judgment = checkJudgmentAvailability({
    hasClaim: !!claim,
    evidenceTotal: summary.total,
    unknownCount: summary.unknownCount,
  })

  if (!judgment.available) {
    return (
      <div
        data-testid={`duel-column-${testKey}`}
        className="flex flex-col gap-3 rounded-xl border border-dashed border-gray-300 p-4 dark:border-gray-700"
      >
        <h3 className="font-medium text-gray-800 dark:text-gray-100">{label}</h3>
        <div
          data-testid="judgment-unavailable"
          className="flex flex-col gap-2 rounded-lg bg-gray-50 p-3 text-sm text-gray-600 dark:bg-gray-800 dark:text-gray-300"
        >
          <p className="font-medium">판단 불가</p>
          <ul className="list-disc pl-4 text-xs text-gray-500">
            {judgment.reasons.map((r) => (
              <li key={r}>{r}</li>
            ))}
          </ul>
          <p className="text-xs font-medium text-gray-600 dark:text-gray-300">다음 관측 조건</p>
          <ul className="list-disc pl-4 text-xs text-gray-500">
            {judgment.nextConditions.map((c) => (
              <li key={c}>{c}</li>
            ))}
          </ul>
          {/* C-1 — claim은 있으나 근거가 부족/없어서 판단 불가인 경우, 근거 관리로 바로 유도 */}
          {claim && monitorId && (
            <button
              type="button"
              onClick={() => setEvidenceOpen(true)}
              data-testid="judgment-unavailable-evidence-cta"
              className="mt-1 inline-flex w-fit items-center gap-1 rounded border border-gray-300 px-2 py-1 text-[11px] font-medium text-gray-600 hover:bg-gray-100 dark:border-gray-700 dark:text-gray-300 dark:hover:bg-gray-700"
            >
              <ShieldPlus size={12} /> 근거 관리
            </button>
          )}
        </div>
        {evidenceOpen && claim && monitorId && (
          <EvidenceModal
            claimId={claim.id}
            monitorId={monitorId}
            targetRef={targetRef}
            onClose={() => setEvidenceOpen(false)}
          />
        )}
      </div>
    )
  }

  const friction = estimateFriction(avgCost, currentPrice)
  const gapMultiplier = gapMultiplierFor(targetRef)
  const counter = buildCounterArgument({
    sideLabel: label,
    evidenceTotal: summary.total,
    evidenceAlive: summary.alive,
    manualCount: summary.manualCount,
    deadOrExpiredCount: summary.deadOrExpiredCount,
    gapMultiplier,
    friction: friction.direction,
  })

  return (
    <div
      data-testid={`duel-column-${testKey}`}
      className="flex flex-col gap-3 rounded-xl border border-gray-200 p-4 dark:border-gray-700"
    >
      <h3 className="font-medium text-gray-800 dark:text-gray-100">{label}</h3>

      {/* 계약층 — 근거 생사(evidence-status) */}
      <div
        data-testid="layer-contract"
        className="rounded-lg border border-gray-100 p-3 dark:border-gray-800"
      >
        <p className="mb-1 text-xs font-semibold text-gray-500">계약층</p>
        <p className="text-sm text-gray-700 dark:text-gray-300">
          근거 생존 {summary.alive}/{summary.total}
        </p>
        {(status?.results ?? [])
          .filter((r) => r.status !== 'alive')
          .map((r) => (
            <div key={r.evidence_id} className="mt-1 flex items-start gap-1.5 text-xs">
              <span className={`flex-shrink-0 rounded px-1 py-0.5 ${EVIDENCE_STATUS_META[r.status].cls}`}>
                {EVIDENCE_STATUS_META[r.status].label}
              </span>
              <span className="text-gray-500">
                {r.indicator_name ?? (r.description || '근거')}
                {r.status === 'dead' && ` · ${r.dead_streak_days}거래일 연속 위반`}
                {r.kind === 'manual' && r.status === 'expired' && ' · 수동 재확인 필요'}
              </span>
            </div>
          ))}
      </div>

      {/* 마찰층 — 간이 어림(정식 산식 SPIN-2) */}
      <div
        data-testid="layer-friction"
        className="rounded-lg border border-gray-100 p-3 dark:border-gray-800"
      >
        <div className="mb-1 flex items-center gap-1.5">
          <p className="text-xs font-semibold text-gray-500">마찰층</p>
          <span
            data-testid="friction-approx-badge"
            className="rounded bg-yellow-100 px-1 py-0.5 text-[10px] font-medium text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-300"
          >
            어림
          </span>
        </div>
        <p className="text-sm text-gray-700 dark:text-gray-300">{friction.note}</p>
        {friction.unrealizedPct != null && (
          <p className="mt-0.5 text-xs text-gray-400">
            평가손익 {formatPctRule(friction.unrealizedPct, { signed: true })}
          </p>
        )}
      </div>

      {/* 통계층 — v0 미장착(추천 엔진·통계 실장 금지) */}
      <div
        data-testid="layer-stats"
        className="rounded-lg border border-dashed border-gray-200 p-3 dark:border-gray-700"
      >
        <div className="mb-1 flex items-center gap-1.5">
          <p className="text-xs font-semibold text-gray-500">통계층</p>
          <SourceBadge tone="stat" />
        </div>
        <p className="text-xs text-gray-400" data-testid="layer-stats-unbuilt">
          미장착 (v1)
        </p>
      </div>

      {/* 반론 의무 슬롯 — 규칙 템플릿(LLM 금지), 양측 동일 형식으로 동분량 보장 */}
      <div
        data-testid="counter-argument"
        className="rounded-lg bg-red-50 p-3 text-xs text-red-800 dark:bg-red-900/10 dark:text-red-300"
      >
        <p className="mb-1 flex items-center gap-1 font-semibold">
          <AlertTriangle size={12} /> {counter.headline}
        </p>
        <ul className="list-disc pl-4">
          {counter.facts.map((f) => (
            <li key={f}>{f}</li>
          ))}
        </ul>

        {/* P-2a — 반론을 홀드 사유로 채택 → 관측 가능 조건(근거) 등록으로 유도(공짜 홀드 금지) */}
        {!adopting ? (
          <button
            type="button"
            onClick={() => setAdopting(true)}
            data-testid="counter-argument-adopt"
            className="mt-2 inline-flex items-center gap-1 rounded border border-red-300 px-2 py-1 text-[11px] font-medium text-red-700 hover:bg-red-100 dark:border-red-800 dark:text-red-300 dark:hover:bg-red-900/20"
          >
            <ShieldPlus size={12} /> 이 반론을 감시 근거로 등록
          </button>
        ) : (
          claim &&
          monitorId && (
            <div
              className="mt-2 rounded-lg border border-red-200 bg-white p-2.5 dark:border-red-900 dark:bg-gray-900"
              data-testid="counter-argument-evidence-form"
            >
              <p className="mb-1.5 text-[11px] text-gray-500">
                반론을 감시 근거로 등록해요 — 규칙 템플릿 반론은 지표 z 임계로 환원하기 어려워
                수동형(서술)으로 프리필했어요. 필요하면 자동형으로 바꿔 지표를 골라도 돼요.
              </p>
              <EvidenceForm
                claimId={claim.id}
                monitorId={monitorId}
                initialKind="manual"
                initialDescription={`${counter.headline}: ${counter.facts.join('; ')}`}
                onCreated={() => setAdopting(false)}
              />
            </div>
          )
        )}
      </div>
    </div>
  )
}
