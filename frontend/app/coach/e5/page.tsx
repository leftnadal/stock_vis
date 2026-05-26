'use client'

/**
 * E5 추출 + 시계열 컨텍스트 페이지 — Slice 16 Part 4. ⚠ 특수 케이스.
 *
 * 폼 = extraction_targets (콤마 분리 다중 키, min_length=1 강제) +
 *      time_series_context (안 C: 토글 + 4칸 + 예시 채우기 버튼).
 *
 * Decimal 직렬화: current/window_* 모두 string으로 전달 (codegen number|string
 * union의 string 분기, fixture portfolio_a2.json 패턴 정합, 백엔드 정밀도 안전).
 *
 * delta_4q_pct는 서버가 자동 계산 — UI에 입력 필드 없음.
 */

import { useMemo, useState } from 'react'
import { AlertCircle, Loader2, Plus, Sparkles, Trash2 } from 'lucide-react'

import { AuthGuard } from '@/components/auth/AuthGuard'
import CommentaryCard from '@/components/coach/CommentaryCard'
import { useE5Coach } from '@/lib/coach/hooks'
import type { E5Request, E5TimeSeriesContext } from '@/lib/coach/types'

const PRESETS: { value: E5Request['preset']; label: string }[] = [
  { value: 'garp', label: 'GARP (성장 + 가치)' },
  { value: 'focused', label: 'Focused (집중)' },
  { value: 'income', label: 'Income (소득)' },
  { value: 'growth', label: 'Growth (성장)' },
  { value: 'factor', label: 'Factor (팩터)' },
]

interface HoldingRow {
  ticker: string
  weight: string
  sector: string
}

const EMPTY_ROW: HoldingRow = { ticker: '', weight: '', sector: '' }

interface TimeSeriesForm {
  current: string
  window_1q: string
  window_4q: string
  window_12q: string
}

const EMPTY_TS: TimeSeriesForm = { current: '', window_1q: '', window_4q: '', window_12q: '' }

/**
 * 예시 값 — `portfolio/tests/fixtures/coach/portfolio_a2.json:93~101` E5 샘플의
 * dividend_yield TimeSeriesContext. 프론트 상수로 박아둠 (런타임에 fixture 로딩 X —
 * 백엔드 테스트 자산을 프론트가 의존하지 않기 위함).
 */
const FIXTURE_TS_EXAMPLE: TimeSeriesForm = {
  current: '3.45',
  window_1q: '3.40',
  window_4q: '3.30',
  window_12q: '3.15',
}

function parseExtractionTargets(raw: string): string[] {
  return raw
    .split(',')
    .map((s) => s.trim())
    .filter((s) => s.length > 0)
}

function toTimeSeriesPayload(ts: TimeSeriesForm): E5TimeSeriesContext {
  // codegen union(number|string|null). string으로 통일 전달 — Pydantic Decimal이
  // string 입력을 안전하게 수용 (fixture와 동일 직렬화 패턴).
  return {
    current: ts.current,
    window_1q: ts.window_1q ? ts.window_1q : null,
    window_4q: ts.window_4q ? ts.window_4q : null,
    window_12q: ts.window_12q ? ts.window_12q : null,
  }
}

export function E5CoachContent() {
  const [portfolioId, setPortfolioId] = useState('demo-portfolio')
  const [preset, setPreset] = useState<E5Request['preset']>('garp')
  const [rows, setRows] = useState<HoldingRow[]>([
    { ticker: 'AAPL', weight: '0.5', sector: 'Tech' },
    { ticker: 'JNJ', weight: '0.5', sector: 'Healthcare' },
  ])
  const [extractionTargetsRaw, setExtractionTargetsRaw] = useState(
    'dividend_yield, sector_diversification, beta, expense_ratio',
  )
  const [tsEnabled, setTsEnabled] = useState(false)
  const [ts, setTs] = useState<TimeSeriesForm>(EMPTY_TS)

  const mutation = useE5Coach()

  const updateRow = (idx: number, patch: Partial<HoldingRow>) => {
    setRows((cur) => cur.map((row, i) => (i === idx ? { ...row, ...patch } : row)))
  }
  const addRow = () => setRows((cur) => [...cur, { ...EMPTY_ROW }])
  const removeRow = (idx: number) =>
    setRows((cur) => (cur.length > 1 ? cur.filter((_, i) => i !== idx) : cur))

  const validRows = useMemo(
    () => rows.filter((r) => r.ticker.trim() && r.weight.trim()),
    [rows],
  )
  const extractionTargets = useMemo(
    () => parseExtractionTargets(extractionTargetsRaw),
    [extractionTargetsRaw],
  )

  const tsCurrentInvalid = tsEnabled && ts.current.trim() === ''

  const canSubmit =
    portfolioId.trim().length > 0 &&
    validRows.length > 0 &&
    extractionTargets.length > 0 &&
    !tsCurrentInvalid &&
    !mutation.isPending

  const handleFillExample = () => {
    setTs({ ...FIXTURE_TS_EXAMPLE })
  }

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!canSubmit) return

    const request: E5Request = {
      portfolio_id: portfolioId.trim(),
      fetched_at: new Date().toISOString(),
      preset,
      entry_point: 'e5',
      holdings: validRows.map((r) => ({
        ticker: r.ticker.trim().toUpperCase(),
        weight: Number(r.weight),
        sector: r.sector.trim() || null,
        asset_class: null,
        name: null,
      })),
      extraction_targets: extractionTargets,
      time_series_context: tsEnabled ? toTimeSeriesPayload(ts) : null,
    }
    mutation.mutate(request)
  }

  return (
    <div className="mx-auto max-w-4xl px-4 py-8">
      <header className="mb-6">
        <div className="mb-2 flex items-center gap-2">
          <Sparkles className="h-6 w-6 text-blue-600" />
          <h1 className="text-2xl font-bold text-slate-900">E5 추출 + 시계열 분석</h1>
        </div>
        <p className="text-sm text-slate-600">
          추출 대상 키와 (선택) 시계열 컨텍스트를 입력하면 AI 코치가 추출값 + 추세까지 종합 해석합니다.
        </p>
      </header>

      <form
        onSubmit={handleSubmit}
        className="mb-6 rounded-2xl border border-slate-200 bg-white p-6 shadow-sm"
        aria-label="E5 추출 + 시계열 입력 폼"
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
              onChange={(e) => setPreset(e.target.value as E5Request['preset'])}
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

        {/* ── 보유 종목 ── */}
        <div className="mb-2 flex items-center justify-between">
          <h2 className="text-sm font-semibold text-slate-700">보유 종목</h2>
          <button
            type="button"
            onClick={addRow}
            className="inline-flex items-center gap-1 rounded-md border border-slate-300 bg-white px-2 py-1 text-xs font-medium text-slate-700 hover:bg-slate-50"
          >
            <Plus className="h-3.5 w-3.5" /> 종목 추가
          </button>
        </div>
        <div className="mb-4 space-y-2">
          {rows.map((row, idx) => (
            <div key={idx} className="grid grid-cols-12 items-center gap-2">
              <input
                aria-label={`종목 ${idx + 1} ticker`}
                type="text"
                placeholder="AAPL"
                value={row.ticker}
                onChange={(e) => updateRow(idx, { ticker: e.target.value })}
                className="col-span-4 rounded-lg border border-slate-300 px-2 py-1.5 text-sm uppercase"
              />
              <input
                aria-label={`종목 ${idx + 1} 비중`}
                type="number"
                step="0.01"
                placeholder="0.5"
                value={row.weight}
                onChange={(e) => updateRow(idx, { weight: e.target.value })}
                className="col-span-3 rounded-lg border border-slate-300 px-2 py-1.5 text-sm"
              />
              <input
                aria-label={`종목 ${idx + 1} 섹터`}
                type="text"
                placeholder="Tech"
                value={row.sector}
                onChange={(e) => updateRow(idx, { sector: e.target.value })}
                className="col-span-4 rounded-lg border border-slate-300 px-2 py-1.5 text-sm"
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

        {/* ── extraction_targets ── */}
        <label className="mb-4 block text-sm">
          <span className="mb-1 block font-medium text-slate-700">
            추출 대상 (콤마로 구분)
          </span>
          <input
            type="text"
            value={extractionTargetsRaw}
            onChange={(e) => setExtractionTargetsRaw(e.target.value)}
            placeholder="dividend_yield, beta, expense_ratio"
            aria-describedby="extraction-targets-hint"
            className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm text-slate-900 focus:border-blue-500 focus:outline-none"
          />
          <p id="extraction-targets-hint" className="mt-1 text-xs text-slate-500">
            현재 {extractionTargets.length}개 키 입력됨{' '}
            {extractionTargets.length > 0 && `→ ${extractionTargets.join(', ')}`}
          </p>
        </label>

        {/* ── time_series_context (안 C) ── */}
        <fieldset className="mb-4 rounded-lg border border-slate-200 p-4">
          <div className="mb-2 flex items-center justify-between gap-3">
            <label className="flex items-center gap-2 text-sm font-medium text-slate-700">
              <input
                type="checkbox"
                checked={tsEnabled}
                onChange={(e) => setTsEnabled(e.target.checked)}
                aria-label="시계열 컨텍스트 포함"
                className="h-4 w-4 rounded border-slate-300 text-blue-600 focus:ring-blue-500"
              />
              시계열 컨텍스트 포함 (선택)
            </label>
            {tsEnabled && (
              <button
                type="button"
                onClick={handleFillExample}
                className="rounded-md border border-slate-300 bg-white px-2 py-1 text-xs font-medium text-slate-700 hover:bg-slate-50"
              >
                예시 값 채우기
              </button>
            )}
          </div>

          {tsEnabled && (
            <>
              <p className="mb-3 text-xs text-amber-700">
                예시 데이터입니다 — <span className="font-medium">실제 값으로 교체</span>하세요.
                값은 문자열로 전달됩니다 (정밀도 보호).
              </p>
              <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
                <label className="text-xs">
                  <span className="mb-0.5 block font-medium text-slate-700">current *</span>
                  <input
                    aria-label="시계열 current"
                    type="text"
                    value={ts.current}
                    onChange={(e) => setTs((cur) => ({ ...cur, current: e.target.value }))}
                    placeholder="3.45"
                    className={`w-full rounded-md border px-2 py-1.5 text-sm ${
                      tsCurrentInvalid ? 'border-red-400' : 'border-slate-300'
                    }`}
                  />
                </label>
                <label className="text-xs">
                  <span className="mb-0.5 block font-medium text-slate-700">window_1q</span>
                  <input
                    aria-label="시계열 window_1q"
                    type="text"
                    value={ts.window_1q}
                    onChange={(e) => setTs((cur) => ({ ...cur, window_1q: e.target.value }))}
                    placeholder="3.40"
                    className="w-full rounded-md border border-slate-300 px-2 py-1.5 text-sm"
                  />
                </label>
                <label className="text-xs">
                  <span className="mb-0.5 block font-medium text-slate-700">window_4q</span>
                  <input
                    aria-label="시계열 window_4q"
                    type="text"
                    value={ts.window_4q}
                    onChange={(e) => setTs((cur) => ({ ...cur, window_4q: e.target.value }))}
                    placeholder="3.30"
                    className="w-full rounded-md border border-slate-300 px-2 py-1.5 text-sm"
                  />
                </label>
                <label className="text-xs">
                  <span className="mb-0.5 block font-medium text-slate-700">window_12q</span>
                  <input
                    aria-label="시계열 window_12q"
                    type="text"
                    value={ts.window_12q}
                    onChange={(e) => setTs((cur) => ({ ...cur, window_12q: e.target.value }))}
                    placeholder="3.15"
                    className="w-full rounded-md border border-slate-300 px-2 py-1.5 text-sm"
                  />
                </label>
              </div>
              {tsCurrentInvalid && (
                <p role="alert" className="mt-2 text-xs text-red-600">
                  시계열 컨텍스트를 포함하려면 <span className="font-medium">current</span> 값을
                  입력해야 합니다.
                </p>
              )}
              <p className="mt-2 text-[11px] text-slate-500">
                * delta_4q_pct는 서버가 자동 계산합니다 (current + window_4q 기준).
              </p>
            </>
          )}
        </fieldset>

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

      <section aria-live="polite" aria-busy={mutation.isPending}>
        {mutation.isIdle && (
          <div
            data-testid="empty-state"
            className="rounded-2xl border border-dashed border-slate-300 bg-slate-50 p-8 text-center text-sm text-slate-500"
          >
            추출 대상을 입력하고 <span className="font-medium">진단 실행</span> 버튼을 눌러주세요.
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

export default function E5CoachPage() {
  return (
    <AuthGuard>
      <E5CoachContent />
    </AuthGuard>
  )
}
