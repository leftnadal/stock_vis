'use client'

import { translate } from '@/lib/i18n/marketPulse'
import type { RegimeHistoryPoint } from '@/lib/api/marketPulseV2'
import { REGIME_TERM, TRANSITION_DIR, regimeTone, stageOrder } from '../meaning'

export interface RegimeSegment {
  stage: string
  startDate: string
  endDate: string
  count: number
  widthPct: number
}

/** 연속 동일 단계 병합 → 세그먼트. width = count/total (가짜 0 패딩 없음). date 오름차순 전제. */
export function groupSegments(history: RegimeHistoryPoint[]): RegimeSegment[] {
  const segs: RegimeSegment[] = []
  for (const e of history) {
    const last = segs[segs.length - 1]
    if (!last || last.stage !== e.stage) {
      segs.push({ stage: e.stage, startDate: e.date, endDate: e.date, count: 1, widthPct: 0 })
    } else {
      last.count += 1
      last.endDate = e.date
    }
  }
  const total = history.length || 1
  for (const s of segs) s.widthPct = (s.count / total) * 100
  return segs
}

export function RegimeTimeline({
  history,
  labels,
}: {
  history: RegimeHistoryPoint[]
  labels?: Record<string, string>
}) {
  if (!history || history.length === 0) {
    return <p className="text-xs text-slate-400">{REGIME_TERM} 이력 데이터 없음</p>
  }

  const segs = groupSegments(history)
  const ko = (stage: string) => translate(`regime.${stage}`, labels, stage)

  // 미지 enum graceful 경고 (crash 0 — regimeTone/ko가 fallback 처리)
  for (const s of segs) {
    if (stageOrder(s.stage) === null && typeof console !== 'undefined') {
      console.warn(`[RegimeTimeline] unknown regime stage: ${s.stage} (fallback neutral)`)
    }
  }

  // 범례: 윈도우 등장 단계(등장 순서 유지, 중복 제거)
  const seen = new Set<string>()
  const legend = segs.map((s) => s.stage).filter((st) => {
    if (seen.has(st)) return false
    seen.add(st)
    return true
  })

  // 최근 전환 주석
  let annotation: string
  if (segs.length <= 1) {
    annotation = `${history.length}일간 ${ko(segs[0].stage)} 유지`
  } else {
    const cur = segs[segs.length - 1]
    const prev = segs[segs.length - 2]
    const co = stageOrder(cur.stage)
    const po = stageOrder(prev.stage)
    const dir = co !== null && po !== null ? (co > po ? TRANSITION_DIR.worsen : TRANSITION_DIR.improve) : ''
    annotation = `${cur.count}일 전 ${ko(prev.stage)} → ${ko(cur.stage)}${dir ? `로 ${dir}` : ''}`
  }

  return (
    <div className="grid gap-1.5">
      <p className="text-xs text-slate-500">최근 {history.length}일 {REGIME_TERM}</p>
      <div
        className="flex h-[22px] w-full overflow-hidden rounded border border-slate-200"
        role="img"
        aria-label={`${REGIME_TERM} 타임라인`}
      >
        {segs.map((s, i) => (
          <div
            key={`${s.stage}-${s.startDate}-${i}`}
            className={`h-full ${regimeTone(s.stage)}`}
            style={{ width: `${s.widthPct}%` }}
            title={`${ko(s.stage)} ${s.startDate}~${s.endDate} (${s.count}일)`}
            aria-label={`${ko(s.stage)} ${s.startDate}~${s.endDate} (${s.count}일)`}
          />
        ))}
      </div>
      <div className="flex justify-between text-[10px] text-slate-400">
        <span>{history[0].date}</span>
        <span>{history[history.length - 1].date} (오늘)</span>
      </div>
      {/* 접근성: 색만으로 구분 금지 → 범례(색칩 + KO 라벨) */}
      <ul className="flex flex-wrap gap-x-3 gap-y-1 text-[11px]">
        {legend.map((st) => (
          <li key={st} className="flex items-center gap-1">
            <span className={`inline-block h-2.5 w-2.5 rounded-sm border ${regimeTone(st)}`} aria-hidden="true" />
            <span className="text-slate-600">{ko(st)}</span>
          </li>
        ))}
      </ul>
      <p className="text-xs text-slate-700">{annotation}</p>
    </div>
  )
}
