// 일지 kind=advisor 렌더러 (MON-P4-LA T3) — ADVISOR L-A 브리핑(headline·body·근거 커버리지).
// 펼침 상태 = SlimStrip.usePersistedToggle과 동일 관례(useSyncExternalStore + localStorage +
// 커스텀 이벤트, 재방문 복원). 단 여기는 엔트리별(advisor note id) 독립 키 + '미기록'과
// '명시적 접힘(0)'을 구분하는 3분기가 필요하다: 사용자가 한 번도 건드리지 않았으면 최신 1건만
// 자동 펼침(D3)하고, 사용자가 명시적으로 접거나 편 이력이 있으면 그 값이 항상 자동 펼침을
// 덮어쓴다(사용자 조작 > 자동).
'use client'

import { useCallback, useSyncExternalStore } from 'react'

import { ChevronDown, ChevronRight } from 'lucide-react'

import type { AdvisorPayload, JournalEntry } from '@/lib/monitor/journal'

const TOGGLE_EVENT = 'mon-detail-journal-advisor-toggle'

function readRaw(key: string): string | null {
  try {
    return window.localStorage.getItem(key)
  } catch {
    return null
  }
}

// raw 미기록(null) → autoDefault(최신 1건만 true, buildJournal의 is_latest). 기록 있으면
// ('1'/'0') 그 값을 그대로 따른다 — 사용자 조작이 자동 펼침을 항상 이긴다.
function useAdvisorExpanded(noteId: string, autoDefault: boolean): [boolean, () => void] {
  const key = `monitor-detail:journal:advisor:${noteId}`

  const subscribe = useCallback((cb: () => void) => {
    window.addEventListener('storage', cb)
    window.addEventListener(TOGGLE_EVENT, cb)
    return () => {
      window.removeEventListener('storage', cb)
      window.removeEventListener(TOGGLE_EVENT, cb)
    }
  }, [])

  const getSnapshot = useCallback(() => {
    const raw = readRaw(key)
    if (raw === '1') return true
    if (raw === '0') return false
    return autoDefault
  }, [key, autoDefault])

  const open = useSyncExternalStore(
    subscribe,
    getSnapshot,
    () => false // SSR·첫 렌더 = 접힘 기본(SlimStrip과 동일 관례) — 자동 펼침은 하이드레이션 후 재조정
  )

  const toggle = useCallback(() => {
    try {
      window.localStorage.setItem(key, open ? '0' : '1')
    } catch {
      /* 프라이버시 모드 무시 */
    }
    window.dispatchEvent(new Event(TOGGLE_EVENT))
  }, [key, open])

  return [open, toggle]
}

export function AdvisorEntry({ entry }: { entry: JournalEntry }) {
  const p = entry.payload as AdvisorPayload
  const [open, toggle] = useAdvisorExpanded(p.id, p.is_latest)

  return (
    <div data-testid="journal-advisor">
      <button
        type="button"
        onClick={toggle}
        aria-expanded={open}
        className="flex w-full items-start justify-between gap-2 text-left"
      >
        <span className="flex min-w-0 items-baseline gap-1.5">
          <span className="flex-shrink-0 rounded bg-purple-100 px-1.5 py-0.5 text-[11px] font-medium text-purple-700 dark:bg-purple-900/30 dark:text-purple-300">
            비서
          </span>
          <span className="min-w-0 truncate text-sm text-gray-800 dark:text-gray-100">
            {p.headline}
          </span>
        </span>
        {open ? (
          <ChevronDown size={14} className="mt-0.5 flex-shrink-0 text-gray-400" />
        ) : (
          <ChevronRight size={14} className="mt-0.5 flex-shrink-0 text-gray-400" />
        )}
      </button>
      {open && (
        <div className="mt-1.5 space-y-1 pl-1" data-testid="journal-advisor-body">
          <p className="text-sm text-gray-600 dark:text-gray-300">{p.body}</p>
          <p className="text-xs text-gray-400" data-testid="journal-advisor-meta">
            근거 지표 {p.coverage_n}/{p.coverage_total} · MonitorSnapshot {p.asof} · {p.model_id}
          </p>
        </div>
      )}
    </div>
  )
}
