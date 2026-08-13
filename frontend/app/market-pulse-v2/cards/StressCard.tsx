/**
 * MPS-2 — StressCard 순수 뷰 (payload 구동, fetch 없음).
 *
 * 소속: market-pulse-v2/cards. hero(RegimeCardSummary) 직하 = DeltaCard 위(D-MPS-SURFACE 안 B).
 * 계약: 백엔드 state enum만 조합(카피=stressCopy, 색=stressAlert 단일소스 — 하드코딩 0).
 *   band_provisional은 파싱만 보존·화면 미표시. 금지 어휘는 stressCopy가 전수 스캔으로 고정.
 */
import { CardShell } from './CardShell'
import {
  buildStressCopy,
  type LevelBand,
  type StressState,
  type PriceState,
} from '../stressCopy'
import {
  divergenceBadgeClass,
  priceNeutralTextClass,
  stressBandBadgeClass,
  stressBandLabel,
  stressStateTextClass,
} from '../stressAlert'
import type { RegimeStressPayload } from '@/lib/api/marketPulseV2'

const STRESS_WORD: Record<StressState, string> = {
  worsening: '악화',
  easing: '완화',
  mixed: '혼조',
}
const PRICE_WORD: Record<PriceState, string> = {
  uptrend: '상승',
  downtrend: '하락',
  mixed: '혼조',
}
const VS_MA_WORD: Record<string, string> = {
  above: '상회',
  below: '하회',
  at: '근접',
}
const CATEGORY_LABEL: Record<string, string> = {
  volatility: '변동성',
  credit: '신용',
  curve: '금리곡선',
  financial_conditions: '금융환경',
  price: '가격',
}

function fmt(n: number | null | undefined, digits = 2): string {
  return n === null || n === undefined ? '—' : n.toFixed(digits)
}
function signArrow(d: number | null | undefined): string {
  if (d === null || d === undefined || d === 0) return '→'
  return d > 0 ? '▲' : '▼'
}

export function StressCard({ data }: { data: RegimeStressPayload }) {
  if (!data.available) {
    return (
      <CardShell titleEn="Market Stress" titleKo="시장 스트레스">
        <div data-testid="stress-unavailable" className="text-sm text-slate-400">
          아직 스트레스 지표를 계산할 수 없습니다.
        </div>
      </CardShell>
    )
  }

  const band = (data.level_band ?? 'stable') as LevelBand
  const sState = (data.direction?.stress.state ?? 'mixed') as StressState
  const pState = (data.direction?.price.state ?? 'mixed') as PriceState
  const copy = buildStressCopy({
    levelBand: band,
    percentileValue: data.percentile?.value ?? 0,
    stressState: sState,
    priceState: pState,
  })

  return (
    <CardShell titleEn="Market Stress" titleKo="시장 스트레스">
      <div data-testid="stress-card" className="flex flex-col gap-3">
        {/* ① 종합: 스코어 + 밴드 뱃지 */}
        <div className="flex items-baseline gap-2">
          <span className="text-2xl font-semibold text-slate-900">{fmt(data.score, 2)}</span>
          <span
            data-testid="stress-band-badge"
            className={`rounded border px-2 py-0.5 text-xs font-medium ${stressBandBadgeClass(band)}`}
          >
            {copy.level} · {stressBandLabel(band)}
          </span>
        </div>

        {/* ② 백분위 문구(F2 분기) */}
        <div className="text-sm text-slate-600">{copy.percentile}</div>

        {/* ③ 방향 2행 + 괴리 강조 */}
        <div className="flex flex-col gap-1 border-t border-slate-100 pt-2 text-sm">
          <div className={stressStateTextClass(sState)}>
            스트레스 {STRESS_WORD[sState]} · 5일 Δ {fmt(data.direction?.stress.d5)} · 20일 Δ{' '}
            {fmt(data.direction?.stress.d20)}
          </div>
          <div className={priceNeutralTextClass()}>
            가격 {PRICE_WORD[pState]} · MA20 {VS_MA_WORD[data.direction?.price.vs_ma20 ?? ''] ?? '—'} · MA60{' '}
            {VS_MA_WORD[data.direction?.price.vs_ma60 ?? ''] ?? '—'}
          </div>
          {copy.divergence && (
            <div
              data-testid="stress-divergence-badge"
              className={`mt-1 inline-flex w-fit items-center rounded border px-2 py-0.5 text-xs font-medium ${divergenceBadgeClass()}`}
            >
              ⚠ {copy.direction}
            </div>
          )}
          {copy.reverseDivergence && (
            <div className="mt-1 text-xs text-slate-500">{copy.direction}</div>
          )}
        </div>

        {/* ④ 카테고리 5종 서브스코어 */}
        <div className="flex flex-col gap-1 border-t border-slate-100 pt-2">
          {(data.categories ?? []).map((c) => (
            <div
              key={c.key}
              data-testid="stress-category-row"
              className="flex items-center justify-between text-xs text-slate-600"
            >
              <span>{CATEGORY_LABEL[c.key] ?? c.key}</span>
              <span className="tabular-nums">
                z {fmt(c.z)} <span className="text-slate-400">({signArrow(c.d5)} {fmt(c.d5)})</span>
              </span>
            </div>
          ))}
        </div>
      </div>
    </CardShell>
  )
}
