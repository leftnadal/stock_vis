'use client'

/**
 * PlaybookCard (1.6-S1) — 거시 플레이북 카드 (순수 뷰).
 *
 * 판단·상태·서사·점등은 전부 BE(engine) 판정 — 이 컴포넌트는 **표시만**(FE 재판정 0).
 * 색은 기존 `stressAlert` 토큰 재사용(신규 hex 0, D-MPS-COLOR 경보 프레임 일관).
 *   dormant=slate(무채)/partial=amber(주의)/active=rose(점등)/pending=slate("데이터 대기").
 * weekly 체인(financial_tightening)은 "주간 · MM-DD 기준" 배지로 정직 표기(죽은 줄 아님).
 * 판정 불가(pending) 체인은 "데이터 대기"(오판정 렌더 금지).
 */
import type { PlaybookPayload, PlaybookState, StressLevelBand } from '@/lib/api/marketPulseV2'

import { stressBandBadgeClass } from '../stressAlert'
import { CardShell } from './CardShell'

const STATE_TO_BAND: Record<PlaybookState, StressLevelBand> = {
  dormant: 'stable',
  partial: 'caution',
  active: 'severe',
  pending: 'stable',
}

function pill(state: PlaybookState): string {
  return `inline-flex shrink-0 items-center rounded-full border px-2 py-0.5 text-xs font-medium ${stressBandBadgeClass(STATE_TO_BAND[state])}`
}

function asOfShort(iso: string | null): string {
  if (!iso) return ''
  // YYYY-MM-DD → MM-DD
  const m = /^\d{4}-(\d{2}-\d{2})$/.exec(iso)
  return m ? m[1] : iso
}

export function PlaybookCard({ data }: { data: PlaybookPayload | null }) {
  if (!data || !data.chains?.length) {
    return (
      <CardShell titleEn="Macro Playbook" titleKo="거시 플레이북">
        <p className="text-sm text-slate-400">플레이북 데이터 미생성</p>
      </CardShell>
    )
  }
  const { chains, summary } = data
  return (
    <CardShell titleEn="Macro Playbook" titleKo="거시 플레이북">
      <p className="text-xs text-slate-500">돈이 어디로 가는가</p>
      {summary?.top_chain ? (
        <p className="mt-1 text-sm text-slate-700" data-testid="playbook-summary">
          체인 {summary.total}개 중 {summary.total_lit}개 점등
          {summary.total_lit > 0 ? ` · 최다 점등 ${summary.top_chain.name}` : ''}
        </p>
      ) : null}
      <ul className="mt-3 space-y-2">
        {chains.map((c) => (
          <li key={c.id} data-testid={`playbook-row-${c.id}`} className="flex items-start justify-between gap-2">
            <div className="min-w-0">
              <div className="flex items-center gap-1.5">
                <span className="text-sm font-medium text-slate-900">{c.name}</span>
                {c.cadence === 'weekly' ? (
                  <span
                    data-testid={`playbook-weekly-${c.id}`}
                    className="inline-flex shrink-0 items-center rounded border border-slate-200 bg-slate-50 px-1.5 py-0.5 text-[10px] text-slate-500"
                  >
                    주간{c.data_as_of ? ` · ${asOfShort(c.data_as_of)} 기준` : ''}
                  </span>
                ) : null}
              </div>
              <p className="text-xs text-slate-500">{c.narrative}</p>
            </div>
            {c.state === 'pending' ? (
              <span data-testid={`playbook-pill-${c.id}`} className={pill('pending')}>데이터 대기</span>
            ) : (
              <span data-testid={`playbook-pill-${c.id}`} className={pill(c.state)}>
                {c.lit_count}/{c.total}
              </span>
            )}
          </li>
        ))}
      </ul>
    </CardShell>
  )
}
