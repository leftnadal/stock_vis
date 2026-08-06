// 일지 kind → 렌더러 레지스트리 (MON-DETAIL-P1 T2).
// P1 구현 3종만 등록. 예약 kind(advisor·theme·memo)와 미등록 kind는 여기 없음 →
// JournalFeed가 안전 무시(전방 호환 — P4/P5/P1.5가 렌더러만 추가하면 점등).
import type { JournalEntry } from '@/lib/monitor/journal'

import { OpenEntry } from './OpenEntry'
import { SnapshotEntry } from './SnapshotEntry'
import { TransitionEntry } from './TransitionEntry'

export type JournalRenderer = (props: { entry: JournalEntry }) => React.ReactNode

export const JOURNAL_RENDERERS: Record<string, JournalRenderer> = {
  snapshot: SnapshotEntry,
  transition: TransitionEntry,
  open: OpenEntry,
}
