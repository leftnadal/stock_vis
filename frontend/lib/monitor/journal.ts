// Monitor 상세 일지(journal) 계약 (MON-DETAIL-P1 T2, D-MON-DETAIL-LAYOUT-B).
// JournalEntry = { kind, asof, payload } + kind별 렌더러 레지스트리(components/monitor/journal).
// P1 구현 kind 3종(snapshot·transition·open) + 예약 kind 3종(advisor·theme·memo — 타입 슬롯만).
// 소스 = monitor-scoped alerts·monitor+claim + 점수 정본 시계열(snapshots, MON-P2B T1).
// snapshot entry는 MonitorSnapshot 정본(BE 계산 delta 그대로 소비) — sparkline(추세 곡선,
// 재산출)은 여기서 더 이상 쓰지 않는다(무접촉 대상은 StateBandSparkline만).
import type { AlertEvent, Claim, Monitor, ScenarioType, SnapshotSeriesResponse } from '@/types/monitor'

// P1 구현 3종 + 예약 3종(레지스트리 미등록 → 안전 무시, 전방 호환).
export type JournalKind = 'snapshot' | 'transition' | 'open' | 'advisor' | 'theme' | 'memo'

export interface SnapshotPayload {
  score: number
  delta: number | null // 직전 스냅샷 대비 Δ (첫 점은 null)
}

export interface TransitionPayload {
  from_label: string
  to_label: string
  is_deterioration: boolean
  is_suppressed: boolean
}

export interface OpenPayload {
  name: string
  scenario_type: ScenarioType | null
  purchase_price: string | null
  entry_price: string | null
  target_price: string | null
  stop_price: string | null
  assertion: string | null
}

export interface JournalEntry {
  kind: JournalKind
  asof: string // YYYY-MM-DD (정렬·표시 기준 = EOD asof)
  payload: unknown // kind별 렌더러가 좁힌다
}

// 동일 asof 내 정렬 우선순위: 전이 > 스냅샷 (낮을수록 위).
const KIND_ORDER: Record<string, number> = { transition: 0, snapshot: 1 }

function dateOf(iso: string): string {
  return iso.slice(0, 10)
}

interface BuildInput {
  snapshots?: SnapshotSeriesResponse | null
  alerts?: AlertEvent[] | null // monitor 스코프(억제 포함) 권장
  monitor: Monitor
  claims?: Claim[] | null
}

// 기존 엔드포인트 조합을 일지 항목으로 합성. 정렬: asof desc, 동일 asof는 transition>snapshot,
// open(관제 개시)은 항상 최하단 고정.
export function buildJournal({ snapshots, alerts, monitor, claims }: BuildInput): JournalEntry[] {
  const entries: JournalEntry[] = []

  // snapshot ← snapshots.series (asc, 정본). delta는 BE 계산값을 그대로 소비(재계산 금지).
  const series = snapshots?.series ?? []
  series.forEach((pt) => {
    entries.push({
      kind: 'snapshot',
      asof: dateOf(pt.asof),
      payload: { score: pt.score, delta: pt.delta } satisfies SnapshotPayload,
    })
  })

  // transition ← monitor 스코프 alerts (억제 표기 포함).
  ;(alerts ?? []).forEach((a) => {
    entries.push({
      kind: 'transition',
      asof: dateOf(a.asof),
      payload: {
        from_label: a.from_label,
        to_label: a.to_label,
        is_deterioration: a.is_deterioration,
        is_suppressed: a.is_suppressed,
      } satisfies TransitionPayload,
    })
  })

  // asof desc, 동일 asof는 KIND_ORDER (transition 먼저).
  entries.sort((x, y) => {
    if (x.asof !== y.asof) return x.asof < y.asof ? 1 : -1
    return (KIND_ORDER[x.kind] ?? 9) - (KIND_ORDER[y.kind] ?? 9)
  })

  // open(관제 개시) ← monitor 생성 + 첫 claim 사전 커밋 요약. 항상 최하단 고정.
  const firstClaim = claims?.[0] ?? null
  entries.push({
    kind: 'open',
    asof: dateOf(monitor.created_at),
    payload: {
      name: monitor.name,
      scenario_type: firstClaim?.scenario_type ?? null,
      purchase_price: firstClaim?.purchase_price ?? null,
      entry_price: firstClaim?.entry_price ?? null,
      target_price: firstClaim?.target_price ?? null,
      stop_price: firstClaim?.stop_price ?? null,
      assertion: firstClaim?.assertion ?? null,
    } satisfies OpenPayload,
  })

  return entries
}
