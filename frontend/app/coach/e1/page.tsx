'use client'

/**
 * E1 GARP 진단 페이지 — Slice 15 Part 2 파일럿 화면.
 *
 * 데이터 레이어(`useE1Coach`)는 그대로 소비, UI만 책임.
 * 3-상태(빈/로딩/에러/성공)를 명시 처리.
 */

import { useState } from 'react'
import { AlertCircle, Loader2, Plus, Sparkles, Trash2 } from 'lucide-react'

import { AuthGuard } from '@/components/auth/AuthGuard'
import CommentaryCard from '@/components/coach/CommentaryCard'
import { useE1Coach } from '@/lib/coach/hooks'
import type { E1Request } from '@/lib/coach/types'

const PRESETS: { value: E1Request['preset']; label: string }[] = [
  { value: 'garp', label: 'GARP (성장 + 가치)' },
  { value: 'focused', label: 'Focused (집중)' },
  { value: 'income', label: 'Income (소득)' },
  { value: 'growth', label: 'Growth (성장)' },
  { value: 'factor', label: 'Factor (팩터)' },
]

interface HoldingRow {
  ticker: string
  weight: string
  epsGrowth: string
  pe: string
  peg: string
}

const EMPTY_ROW: HoldingRow = {
  ticker: '',
  weight: '',
  epsGrowth: '',
  pe: '',
  peg: '',
}

export function E1CoachContent() {
  const [portfolioId, setPortfolioId] = useState('demo-portfolio')
  const [preset, setPreset] = useState<E1Request['preset']>('garp')
  const [rows, setRows] = useState<HoldingRow[]>([
    { ticker: 'AAPL', weight: '0.4', epsGrowth: '0.12', pe: '18', peg: '1.5' },
    { ticker: 'MSFT', weight: '0.6', epsGrowth: '0.15', pe: '22', peg: '1.4' },
  ])

  const mutation = useE1Coach()

  const updateRow = (idx: number, patch: Partial<HoldingRow>) => {
    setRows((cur) => cur.map((row, i) => (i === idx ? { ...row, ...patch } : row)))
  }
  const addRow = () => setRows((cur) => [...cur, { ...EMPTY_ROW }])
  const removeRow = (idx: number) =>
    setRows((cur) => (cur.length > 1 ? cur.filter((_, i) => i !== idx) : cur))

  // 가벼운 클라이언트 검증 — 본격 검증은 백엔드 serializer가 한다.
  const validRows = rows.filter((r) => r.ticker.trim() && r.weight.trim())
  const canSubmit = portfolioId.trim().length > 0 && validRows.length > 0 && !mutation.isPending

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!canSubmit) return

    const request: E1Request = {
      portfolio_id: portfolioId.trim(),
      fetched_at: new Date().toISOString(),
      preset,
      entry_point: 'e1',
      holdings: validRows.map((r) => ({
        ticker: r.ticker.trim().toUpperCase(),
        weight: Number(r.weight),
        sector: null,
        asset_class: null,
        name: null,
      })),
      garp_metrics: Object.fromEntries(
        validRows.map((r) => [
          r.ticker.trim().toUpperCase(),
          {
            eps_growth_rate: r.epsGrowth ? Number(r.epsGrowth) : null,
            pe_ratio: r.pe ? Number(r.pe) : null,
            peg_ratio: r.peg ? Number(r.peg) : null,
          },
        ]),
      ),
    }
    mutation.mutate(request)
  }

  return (
    <div className="mx-auto max-w-4xl px-4 py-8">
      <header className="mb-6">
        <div className="mb-2 flex items-center gap-2">
          <Sparkles className="h-6 w-6 text-blue-600" />
          <h1 className="text-2xl font-bold text-slate-900">E1 GARP 진단</h1>
        </div>
        <p className="text-sm text-slate-600">
          포트폴리오 보유 종목과 GARP 지표를 입력하면 AI 코치가 성장-가치 균형 관점에서 진단해 드립니다.
        </p>
      </header>

      {/* ── 입력 폼 ── */}
      <form
        onSubmit={handleSubmit}
        className="mb-6 rounded-2xl border border-slate-200 bg-white p-6 shadow-sm"
        aria-label="E1 GARP 진단 입력 폼"
      >
        <div className="mb-4 grid grid-cols-1 gap-4 md:grid-cols-2">
          <label className="text-sm">
            <span className="mb-1 block font-medium text-slate-700">포트폴리오 ID</span>
            <input
              type="text"
              value={portfolioId}
              onChange={(e) => setPortfolioId(e.target.value)}
              className="w-full rounded-lg border border-slate-300 px-3 py-2 text-slate-900 focus:border-blue-500 focus:outline-none"
              required
            />
          </label>
          <label className="text-sm">
            <span className="mb-1 block font-medium text-slate-700">투자 스타일 (Preset)</span>
            <select
              value={preset}
              onChange={(e) => setPreset(e.target.value as E1Request['preset'])}
              className="w-full rounded-lg border border-slate-300 px-3 py-2 text-slate-900 focus:border-blue-500 focus:outline-none"
            >
              {PRESETS.map((p) => (
                <option key={p.value} value={p.value}>
                  {p.label}
                </option>
              ))}
            </select>
          </label>
        </div>

        <div className="mb-2 flex items-center justify-between">
          <h2 className="text-sm font-semibold text-slate-700">보유 종목 & GARP 지표</h2>
          <button
            type="button"
            onClick={addRow}
            className="inline-flex items-center gap-1 rounded-md border border-slate-300 bg-white px-2 py-1 text-xs font-medium text-slate-700 hover:bg-slate-50"
          >
            <Plus className="h-3.5 w-3.5" /> 종목 추가
          </button>
        </div>
        <div className="space-y-2">
          {rows.map((row, idx) => (
            <div key={idx} className="grid grid-cols-12 items-center gap-2">
              <input
                aria-label={`종목 ${idx + 1} ticker`}
                type="text"
                placeholder="AAPL"
                value={row.ticker}
                onChange={(e) => updateRow(idx, { ticker: e.target.value })}
                className="col-span-3 rounded-lg border border-slate-300 px-2 py-1.5 text-sm uppercase"
              />
              <input
                aria-label={`종목 ${idx + 1} 비중`}
                type="number"
                step="0.01"
                placeholder="0.4"
                value={row.weight}
                onChange={(e) => updateRow(idx, { weight: e.target.value })}
                className="col-span-2 rounded-lg border border-slate-300 px-2 py-1.5 text-sm"
              />
              <input
                aria-label={`종목 ${idx + 1} EPS 성장률`}
                type="number"
                step="0.01"
                placeholder="EPS 성장"
                value={row.epsGrowth}
                onChange={(e) => updateRow(idx, { epsGrowth: e.target.value })}
                className="col-span-2 rounded-lg border border-slate-300 px-2 py-1.5 text-sm"
              />
              <input
                aria-label={`종목 ${idx + 1} PE`}
                type="number"
                step="0.1"
                placeholder="PE"
                value={row.pe}
                onChange={(e) => updateRow(idx, { pe: e.target.value })}
                className="col-span-2 rounded-lg border border-slate-300 px-2 py-1.5 text-sm"
              />
              <input
                aria-label={`종목 ${idx + 1} PEG`}
                type="number"
                step="0.1"
                placeholder="PEG"
                value={row.peg}
                onChange={(e) => updateRow(idx, { peg: e.target.value })}
                className="col-span-2 rounded-lg border border-slate-300 px-2 py-1.5 text-sm"
              />
              <button
                type="button"
                onClick={() => removeRow(idx)}
                disabled={rows.length === 1}
                aria-label={`종목 ${idx + 1} 삭제`}
                className="col-span-1 inline-flex justify-center rounded-md p-1.5 text-slate-400 hover:text-red-600 disabled:opacity-30"
              >
                <Trash2 className="h-4 w-4" />
              </button>
            </div>
          ))}
        </div>

        <div className="mt-6 flex justify-end">
          <button
            type="submit"
            disabled={!canSubmit}
            className="inline-flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2 text-sm font-semibold text-white hover:bg-blue-700 disabled:cursor-not-allowed disabled:bg-slate-300"
          >
            {mutation.isPending ? (
              <>
                <Loader2 className="h-4 w-4 animate-spin" />
                진단 중...
              </>
            ) : (
              <>
                <Sparkles className="h-4 w-4" />
                진단 실행
              </>
            )}
          </button>
        </div>
      </form>

      {/* ── 결과 영역 (3-상태) ── */}
      <section aria-live="polite" aria-busy={mutation.isPending}>
        {mutation.isIdle && (
          <div
            data-testid="empty-state"
            className="rounded-2xl border border-dashed border-slate-300 bg-slate-50 p-8 text-center text-sm text-slate-500"
          >
            포트폴리오를 입력하고 <span className="font-medium">진단 실행</span> 버튼을 눌러주세요.
          </div>
        )}
        {mutation.isPending && (
          <div
            data-testid="loading-state"
            className="flex flex-col items-center gap-3 rounded-2xl border border-slate-200 bg-white p-10 text-slate-600"
          >
            <Loader2 className="h-8 w-8 animate-spin text-blue-500" />
            <p className="text-sm">AI 코치가 진단을 작성하고 있습니다...</p>
          </div>
        )}
        {mutation.isError && (
          <div
            role="alert"
            data-testid="error-state"
            className="flex items-start gap-3 rounded-2xl border border-red-200 bg-red-50 p-5 text-sm text-red-800"
          >
            <AlertCircle className="mt-0.5 h-5 w-5 shrink-0" />
            <div>
              <p className="font-medium">진단 생성에 실패했습니다.</p>
              <p className="mt-1 text-red-700">
                잠시 후 다시 시도해 주세요. 문제가 계속되면 관리자에게 문의해 주세요.
              </p>
            </div>
          </div>
        )}
        {mutation.isSuccess && mutation.data && <CommentaryCard output={mutation.data.output} />}
      </section>
    </div>
  )
}

export default function E1CoachPage() {
  return (
    <AuthGuard>
      <E1CoachContent />
    </AuthGuard>
  )
}
