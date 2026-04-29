'use client'

import { ReactNode, useEffect } from 'react'

export function CardDrawer({
  open, onClose, title, children,
}: { open: boolean; onClose: () => void; title: string; children: ReactNode }) {
  useEffect(() => {
    if (!open) return
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose()
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [open, onClose])

  if (!open) return null
  return (
    <div className="fixed inset-0 z-50 flex items-end sm:items-center sm:justify-center" role="dialog" aria-modal="true">
      <div className="absolute inset-0 bg-slate-900/40" onClick={onClose} aria-hidden="true" />
      <div className="relative w-full sm:max-w-2xl rounded-t-2xl sm:rounded-2xl bg-white p-5 shadow-xl max-h-[85vh] overflow-y-auto">
        <header className="flex items-center justify-between mb-3">
          <h2 className="text-lg font-semibold text-slate-900">{title}</h2>
          <button type="button" onClick={onClose} className="text-sm text-slate-500 hover:text-slate-900 px-2 py-1">
            닫기
          </button>
        </header>
        <div>{children}</div>
      </div>
    </div>
  )
}
