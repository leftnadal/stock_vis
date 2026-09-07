'use client'

// 후보 선택 — 전 종목 검색(shared.stocks.Stock)으로 후보 심볼을 지정한다(SWAP-P1).
// BE 계약(SwapHoldLog.candidate_ref = 심볼)에 FE를 정합시킨다 — 감시 미등록 종목도 후보 가능.
// 검색 API = stockService.searchStocks(/stocks/api/search/?q=), 디바운스/외부클릭 UX는 AddStockModal 선례.
import { useEffect, useRef, useState } from 'react'

import { stockService } from '@/services/stock'
import type { Monitor } from '@/types/monitor'

interface SearchResultItem {
  symbol: string
  name: string
  price: string | null
}

interface CandidatePickerProps {
  monitors: Monitor[] // 검색 결과에 "감시중" 배지 표시용
  excludeSymbol: string // 현재 모니터 심볼(결과에서 제외)
  value: string // 지정된 후보 심볼(대문자)
  onChange: (symbol: string, priceHint?: string | null) => void
  watchlistItems?: { symbol: string; name: string; price?: string | null }[]
}

export function CandidatePicker({
  monitors,
  excludeSymbol,
  value,
  onChange,
  watchlistItems = [],
}: CandidatePickerProps) {
  const [query, setQuery] = useState('')
  const [results, setResults] = useState<SearchResultItem[]>([])
  const [open, setOpen] = useState(false)
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const boxRef = useRef<HTMLDivElement>(null)

  const registered = new Set(
    monitors.filter((m) => m.scope === 'stock').map((m) => m.target_ref.toUpperCase())
  )
  const exclude = excludeSymbol.toUpperCase()

  // 외부 클릭 시 결과 닫기
  useEffect(() => {
    const onOutside = (e: MouseEvent) => {
      if (boxRef.current && !boxRef.current.contains(e.target as Node)) setOpen(false)
    }
    document.addEventListener('mousedown', onOutside)
    return () => document.removeEventListener('mousedown', onOutside)
  }, [])

  // 언마운트 시 디바운스 타이머 정리
  useEffect(() => () => { if (timerRef.current) clearTimeout(timerRef.current) }, [])

  function runSearch(q: string) {
    const term = q.trim()
    if (term.length < 2) {
      setResults([])
      setOpen(false)
      return
    }
    stockService
      .searchStocks(term)
      .then((rows: unknown[]) => {
        const mapped = ((rows ?? []) as Record<string, unknown>[])
          .map((r) => ({
            symbol: String(r.symbol ?? '').toUpperCase(),
            name: (r.stock_name as string) ?? String(r.symbol ?? ''),
            price: r.real_time_price != null ? String(r.real_time_price) : null,
          }))
          .filter((r) => r.symbol && r.symbol !== exclude)
        setResults(mapped)
        setOpen(true)
      })
      .catch(() => {
        setResults([])
      })
  }

  function onInput(v: string) {
    setQuery(v)
    if (timerRef.current) clearTimeout(timerRef.current)
    timerRef.current = setTimeout(() => runSearch(v), 300)
  }

  function pick(symbol: string, price: string | null) {
    onChange(symbol, price)
    setQuery(symbol)
    setOpen(false)
    setResults([])
  }

  return (
    <div ref={boxRef} className="flex flex-col gap-1 text-sm text-gray-600 dark:text-gray-300">
      <label className="flex flex-col gap-1">
        교체 후보
        <div className="relative">
          <input
            value={query}
            onChange={(e) => onInput(e.target.value)}
            onFocus={() => { if (results.length > 0) setOpen(true) }}
            placeholder="종목명 또는 티커로 검색"
            data-testid="candidate-picker"
            className="w-full rounded-lg border border-gray-300 px-3 py-2 dark:border-gray-700 dark:bg-gray-900"
          />
          {open && results.length > 0 && (
            <ul
              data-testid="candidate-search-results"
              className="absolute z-10 mt-1 max-h-60 w-full overflow-auto rounded-lg border border-gray-200 bg-white shadow dark:border-gray-700 dark:bg-gray-900"
            >
              {results.map((r) => (
                <li key={r.symbol}>
                  <button
                    type="button"
                    onClick={() => pick(r.symbol, r.price)}
                    data-testid={`candidate-option-${r.symbol}`}
                    className="flex w-full items-center justify-between gap-2 px-3 py-2 text-left hover:bg-gray-50 dark:hover:bg-gray-800"
                  >
                    <span>
                      <span className="font-medium">{r.symbol}</span> · {r.name}
                    </span>
                    {registered.has(r.symbol) && (
                      <span className="flex-shrink-0 rounded bg-blue-100 px-1 py-0.5 text-[10px] font-medium text-blue-700 dark:bg-blue-900/30 dark:text-blue-300">
                        감시중
                      </span>
                    )}
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>
      </label>

      {value && <span className="text-xs text-gray-500">지정된 후보: {value}</span>}

      {watchlistItems.length > 0 && (
        <div className="mt-1 flex flex-wrap items-center gap-1">
          <span className="text-xs text-gray-400">관심종목:</span>
          {watchlistItems
            .filter((w) => w.symbol.toUpperCase() !== exclude)
            .map((w) => (
              <button
                key={w.symbol}
                type="button"
                onClick={() => pick(w.symbol.toUpperCase(), w.price ?? null)}
                data-testid={`candidate-watchlist-chip-${w.symbol.toUpperCase()}`}
                className="rounded-full border border-gray-300 px-2 py-0.5 text-xs hover:bg-gray-100 dark:border-gray-700 dark:hover:bg-gray-800"
              >
                {w.symbol}
              </button>
            ))}
        </div>
      )}

      {!value && (
        <span className="text-xs text-gray-400">종목명이나 티커로 검색해 후보를 지정하세요.</span>
      )}
    </div>
  )
}
