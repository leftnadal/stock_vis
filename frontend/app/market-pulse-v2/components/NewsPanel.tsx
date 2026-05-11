'use client'

import { useRefreshNews } from '@/hooks/useMarketPulseV2'
import { translate } from '@/lib/i18n/marketPulse'
import type { NewsItem } from '@/lib/api/marketPulseV2'

const CATEGORY_TONE: Record<string, string> = {
  MACRO: 'bg-indigo-100 text-indigo-700',
  GEOPOLITICS: 'bg-rose-100 text-rose-700',
  SECTOR: 'bg-emerald-100 text-emerald-700',
  INDEX: 'bg-sky-100 text-sky-700',
  MAG7: 'bg-amber-100 text-amber-700',
  SMART_MONEY: 'bg-fuchsia-100 text-fuchsia-700',
}

function formatTime(iso: string): string {
  try {
    const d = new Date(iso)
    return d.toLocaleString('ko-KR', { month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' })
  } catch {
    return iso
  }
}

export function NewsPanel({ items, labels }: { items: NewsItem[]; labels?: Record<string, string> }) {
  const refresh = useRefreshNews()
  return (
    <section className="mt-4">
      <header className="flex items-center justify-between mb-2">
        <h2 className="font-semibold text-slate-800">News · 시장 뉴스</h2>
        <button
          type="button"
          onClick={() => refresh.mutate()}
          disabled={refresh.isPending}
          className="text-xs text-slate-500 hover:text-slate-800 disabled:opacity-50"
        >
          {refresh.isPending ? '갱신 중…' : '다른 뉴스'}
        </button>
      </header>
      {items.length === 0 ? (
        <p className="text-sm text-slate-400">표시할 뉴스가 없습니다.</p>
      ) : (
        <ul className="grid gap-2">
          {items.map((n) => (
            <li key={n.id} className="rounded-md border border-slate-200 p-3 hover:border-slate-300 transition">
              <a href={n.url} target="_blank" rel="noopener noreferrer" className="block">
                <div className="flex items-center gap-2 mb-1">
                  <span className={`text-xs px-2 py-0.5 rounded ${CATEGORY_TONE[n.category] ?? 'bg-slate-100'}`}>
                    {translate(`news.${n.category}`, labels, n.category)}
                  </span>
                  <span className="text-xs text-slate-400">{n.publisher || '—'}</span>
                  <span className="text-xs text-slate-400 ml-auto">{formatTime(n.published_at)}</span>
                </div>
                <p className="text-sm font-medium text-slate-900 leading-snug">{n.title}</p>
                {n.summary ? <p className="text-xs text-slate-500 mt-1 line-clamp-2">{n.summary}</p> : null}
              </a>
            </li>
          ))}
        </ul>
      )}
    </section>
  )
}
