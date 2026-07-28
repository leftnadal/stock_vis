// 가격 구간축 표시 유틸 (TIMING-P2 §5) — **렌더 전용**.
// ⚠️ 라벨·경계값의 진실 = API zone_display(BE 완결). FE는 색 톤과 사다리 기하만 담당.
import type { PriceZone, ZoneDisplay } from '@/types/monitor'

export interface ZoneTone {
  chip: string // 칩 클래스
  bar: string // 사다리 밴드 배경
  marker: string // 현재가 마커 색
}

// 구간별 톤: 진입(파랑=행동)·접근(하늘)·관망(회색)·과열(주황)·이탈(빨강).
export const ZONE_TONE: Record<PriceZone, ZoneTone> = {
  entry: {
    chip: 'bg-blue-50 text-blue-700 border-blue-300 dark:bg-blue-900/30 dark:text-blue-300 dark:border-blue-700',
    bar: 'bg-blue-400/70',
    marker: 'bg-blue-600',
  },
  approach: {
    chip: 'bg-sky-50 text-sky-700 border-sky-200 dark:bg-sky-900/25 dark:text-sky-300 dark:border-sky-800',
    bar: 'bg-sky-300/60',
    marker: 'bg-sky-500',
  },
  waiting: {
    chip: 'bg-gray-100 text-gray-600 border-gray-200 dark:bg-gray-800 dark:text-gray-300 dark:border-gray-700',
    bar: 'bg-gray-300/50 dark:bg-gray-600/40',
    marker: 'bg-gray-500',
  },
  overheated: {
    chip: 'bg-orange-50 text-orange-700 border-orange-200 dark:bg-orange-900/25 dark:text-orange-300 dark:border-orange-800',
    bar: 'bg-orange-300/60',
    marker: 'bg-orange-500',
  },
  exited: {
    chip: 'bg-red-50 text-red-700 border-red-300 dark:bg-red-900/25 dark:text-red-300 dark:border-red-700',
    bar: 'bg-red-400/60',
    marker: 'bg-red-600',
  },
}

// 사다리 밴드 순서(아래=이탈, 위=과열). low→high.
export const ZONE_LADDER_ORDER: PriceZone[] = [
  'exited',
  'entry',
  'approach',
  'waiting',
  'overheated',
]

// 진입가 대비 현재가 % (칩 보조 표시). zone_display.close·boundaries.entry 사용.
export function priceVsEntryPct(zd: ZoneDisplay): number | null {
  if (zd.close == null || !zd.boundaries?.entry) return null
  return ((zd.close - zd.boundaries.entry) / zd.boundaries.entry) * 100
}
