'use client'

import { ReactNode } from 'react'

export function CardShell({
  titleEn, titleKo, status, onOpen, children,
}: { titleEn: string; titleKo: string; status?: string; onOpen?: () => void; children: ReactNode }) {
  return (
    <article
      className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm hover:border-slate-300 transition"
      onClick={onOpen}
      role={onOpen ? 'button' : undefined}
      tabIndex={onOpen ? 0 : undefined}
      onKeyDown={(e) => {
        if (onOpen && (e.key === 'Enter' || e.key === ' ')) {
          e.preventDefault()
          onOpen()
        }
      }}
    >
      <header className="flex items-baseline justify-between mb-2">
        <h3 className="text-sm font-semibold text-slate-800">
          <span>{titleEn}</span>
          <span className="text-slate-500 mx-1.5">·</span>
          <span className="text-slate-500">{titleKo}</span>
        </h3>
        {status && status !== 'OK' ? <span className="text-xs text-amber-600">{status}</span> : null}
      </header>
      {children}
    </article>
  )
}
