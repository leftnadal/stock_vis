// Monitor 상세 일지(journal) 계약 (MON-DETAIL-P1 T2, D-MON-DETAIL-LAYOUT-B).
// JournalEntry = { kind, asof, payload } + kind별 렌더러 레지스트리(components/monitor/journal).
// P1 구현 kind 3종(snapshot·transition·open) + P4-LA 구현 kind 1종(advisor) + 예약 kind 2종
// (theme·memo — 타입 슬롯만). 소스 = monitor-scoped alerts·monitor+claim + 점수 정본 시계열
// (snapshots, MON-P2B T1) + ADVISOR L-A 브리핑(advisor_notes, MON-P4-LA T3).
// snapshot entry는 MonitorSnapshot 정본(BE 계산 delta 그대로 소비) — sparkline(추세 곡선,
// 재산출)은 여기서 더 이상 쓰지 않는다(무접촉 대상은 StateBandSparkline만).
import type {
  AdvisorNote,
  AlertEvent,
  Claim,
  Monitor,
  ScenarioType,
  SnapshotSeriesResponse,
} from '@/types/monitor'

// P1 구현 3종 + P4-LA 구현 1종(advisor) + 예약 2종(theme·memo, 레지스트리 미등록 → 안전 무시).
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

// ADVISOR L-A 브리핑 (MON-P4-LA T3, A안 원장 동형 — BE AdvisorNote 그대로 소비, FE 가공 금지).
// id = localStorage 펼침 키(엔트리별 독립 펼침, AdvisorEntry). is_latest = buildJournal이 계산
// (BE advisor_notes 응답이 이미 최신순 — 원본 배열 0번째만 true) — 일지 자동 펼침(D3)의 유일한 소스.
export interface AdvisorPayload {
  id: string
  headline: string
  body: string
  coverage_n: number
  coverage_total: number
  model_id: string
  asof: string
  is_latest: boolean
}

export interface JournalEntry {
  kind: JournalKind
  asof: string // YYYY-MM-DD (정렬·표시 기준 = EOD asof)
  payload: unknown // kind별 렌더러가 좁힌다
}

// 동일 asof 내 정렬 우선순위: 전이 > 스냅샷 > advisor (낮을수록 위, 기존 순서 존중 + advisor는 뒤).
const KIND_ORDER: Record<string, number> = { transition: 0, snapshot: 1, advisor: 2 }

function dateOf(iso: string): string {
  return iso.slice(0, 10)
}

interface BuildInput {
  snapshots?: SnapshotSeriesResponse | null
  alerts?: AlertEvent[] | null // monitor 스코프(억제 포함) 권장
  monitor: Monitor
  claims?: Claim[] | null
  advisorNotes?: AdvisorNote[] | null // MON-P4-LA T3, surface=L-A 최신순
}

// 기존 엔드포인트 조합을 일지 항목으로 합성. 정렬: asof desc, 동일 asof는 transition>snapshot>advisor,
// open(관제 개시)은 항상 최하단 고정.
export function buildJournal({
  snapshots,
  alerts,
  monitor,
  claims,
  advisorNotes,
}: BuildInput): JournalEntry[] {
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

  // advisor ← advisor_notes (BE 응답 = 최신순, order_by('-asof')). idx=0(최초 원소)만
  // is_latest=true — 일지 자동 펼침(D3, AdvisorEntry)의 유일한 판단 소스. FE 재정렬/재계산 금지.
  ;(advisorNotes ?? []).forEach((note, idx) => {
    entries.push({
      kind: 'advisor',
      asof: dateOf(note.asof),
      payload: {
        id: note.id,
        headline: note.headline,
        body: note.body,
        coverage_n: note.coverage_n,
        coverage_total: note.coverage_total,
        model_id: note.model_id,
        asof: dateOf(note.asof),
        is_latest: idx === 0,
      } satisfies AdvisorPayload,
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
