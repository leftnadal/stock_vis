'use client'

// D1-SCOREBOARD 3a — 성적판 본문 (헤더 3카드 + 심볼 행 + 펼침 상세).
// 자립 컴포넌트: scorecard 전문만 받으면 렌더. 펼침 시 SignalCard(3b) 재사용.
import { useState } from 'react'
import { ChevronDown, ChevronRight } from 'lucide-react'

import type { AnalystScorecard, ScorecardSymbol } from '@/types/scorecard'
import { fmtPct, hitRatePct, sampleLabel } from '@/lib/scorecard/present'
import { SignalCard } from './SignalCard'

interface ScoreboardBoardProps {
  scorecard: AnalystScorecard
}

function HeaderCard({ label, value, sub }: { label: string; value: string; sub?: string }) {
  return (
    <div className="flex flex-col rounded-xl border border-gray-200 bg-white p-4 shadow-sm dark:border-gray-800 dark:bg-gray-900">
      <span className="text-[11px] text-gray-400">{label}</span>
      <span className="text-xl font-semibold text-gray-900 dark:text-gray-100">{value}</span>
      {sub && <span className="mt-0.5 text-[11px] text-gray-400">{sub}</span>}
    </div>
  )
}

function SymbolRow({ sym }: { sym: ScorecardSymbol }) {
  const [open, setOpen] = useState(false)
  const rate = sym.hit ? hitRatePct(sym.hit.hits, sym.hit.total) : null
  return (
    <div data-testid="symbol-row" className="rounded-lg border border-gray-100 dark:border-gray-800">
      <button
        type="button"
        data-testid={`symbol-toggle-${sym.symbol}`}
        onClick={() => setOpen((v) => !v)}
        className="flex w-full items-center justify-between gap-3 px-3 py-2.5 text-left hover:bg-gray-50 dark:hover:bg-gray-800/60"
      >
        <span className="flex items-center gap-2">
          {open ? <ChevronDown className="h-4 w-4 text-gray-400" /> : <ChevronRight className="h-4 w-4 text-gray-400" />}
          <span className="font-medium text-gray-900 dark:text-gray-100">{sym.symbol}</span>
        </span>
        <span className="flex items-center gap-3 text-xs text-gray-500 dark:text-gray-400">
          <span data-testid="row-counts">
            채점 {sym.counts.scored} · 대기 {sym.counts.pending} · 불가 {sym.counts.unscoreable}
          </span>
          <span data-testid="row-hit">{sym.hit ? `적중 ${sym.hit.hits}/${sym.hit.total}` : '—'}</span>
          <span data-testid="row-tp">{sym.avg_target_progress != null ? fmtPct(sym.avg_target_progress) : '—'}</span>
          {rate != null && <span className="hidden sm:inline">{fmtPct(rate)}</span>}
        </span>
      </button>
      {open && (
        <div data-testid={`symbol-signals-${sym.symbol}`} className="flex flex-col gap-2 border-t border-gray-100 p-3 dark:border-gray-800">
          {sym.signals.length === 0 ? (
            <p className="text-xs text-gray-400">신호 없음</p>
          ) : (
            sym.signals.map((s, i) => <SignalCard key={`${sym.symbol}-${s.captured_at}-${i}`} signal={s} />)
          )}
        </div>
      )}
    </div>
  )
}

export function ScoreboardBoard({ scorecard }: ScoreboardBoardProps) {
  const { board, symbols, reproduction, horizon } = scorecard
  const rate = hitRatePct(board.direction_hit.hits, board.direction_hit.total)

  return (
    <div data-testid="scoreboard-board" className="flex flex-col gap-4">
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
        <HeaderCard
          label={`방향 적중률 (h=${horizon}d)`}
          value={
            board.direction_hit.total > 0
              ? `${fmtPct(rate)}`
              : '—'
          }
          sub={
            board.direction_hit.total > 0
              ? `${board.direction_hit.hits}/${board.direction_hit.total} · ${sampleLabel(board)}`
              : sampleLabel(board)
          }
        />
        <HeaderCard
          label="평균 목표 진행률"
          value={board.avg_target_progress != null ? fmtPct(board.avg_target_progress) : '—'}
          sub={board.avg_target_progress == null ? '표본 미도달' : undefined}
        />
        <HeaderCard
          label="횡단면 IC"
          value={board.cross_sectional_ic != null ? board.cross_sectional_ic.toFixed(3) : '—'}
          sub={board.cross_sectional_ic == null ? board.cross_sectional_ic_reason ?? '표본 미도달' : undefined}
        />
      </div>

      <div className="flex flex-col gap-2">
        {symbols.map((sym) => (
          <SymbolRow key={sym.symbol} sym={sym} />
        ))}
      </div>

      {/* 재현 각주 (reproduction 6필드 + computed_at) */}
      <p data-testid="scorecard-reproduction" className="text-[11px] leading-relaxed text-gray-400">
        재현: as_of {reproduction.as_of} · v{reproduction.scoring_version} · git {reproduction.git_head} ·
        신호 {reproduction.input_rows?.ass_rows ?? '—'}행 · 가격 {reproduction.input_rows?.daily_price_rows ?? '—'}행 ·
        분할 {reproduction.splits_input_rows ?? '—'}행
        {reproduction.computed_at ? ` · 산출 ${reproduction.computed_at}` : ''}
      </p>
    </div>
  )
}
