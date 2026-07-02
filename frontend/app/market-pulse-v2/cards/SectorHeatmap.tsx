'use client'

import { translate } from '@/lib/i18n/marketPulse'
import type { SectorDetail } from '@/lib/api/marketPulseV2'
import { useCardDetail } from '@/hooks/useMarketPulseV2'

/**
 * rel_strength → diverging 색 클래스 (한국 관례: 상승=빨강, 하락=파랑).
 * epsilon 안쪽은 neutral(slate).
 * 절대값 기준 2단계(mild: |rel|<=0.4, strong: |rel|>0.4).
 *
 * ⚠ rotation_index 절대 사용 금지 — 11섹터 동일값으로 전 타일 동색 버그.
 *   색은 오직 per-섹터 rel_strength.
 */
function heatTileClass(relStrength: number, epsilon = 0.1): string {
  if (relStrength > epsilon) {
    // 상승 = 빨강 (한국 관례)
    return relStrength > 0.4
      ? 'bg-rose-300 text-rose-900 border-rose-400'
      : 'bg-rose-100 text-rose-800 border-rose-200'
  }
  if (relStrength < -epsilon) {
    // 하락 = 파랑 (한국 관례)
    return relStrength < -0.4
      ? 'bg-sky-300 text-sky-900 border-sky-400'
      : 'bg-sky-100 text-sky-800 border-sky-200'
  }
  // 중립
  return 'bg-slate-100 text-slate-600 border-slate-200'
}

function formatRel(v: number): string {
  const sign = v > 0 ? '+' : ''
  return `${sign}${v.toFixed(2)}%`
}

interface SectorHeatmapProps {
  labels?: Record<string, string>
  onOpen?: () => void
}

/**
 * Sector 히트맵 — D-MP2-SURFACE 신규 full-width 컴포넌트.
 * useCardDetail<SectorDetail>('sector', true) 로 11섹터 fetch.
 * rank 오름차순 정렬 → 11 타일 렌더.
 * 색 = rel_strength diverging (상승=빨강, 하락=파랑, 한국 관례).
 * onOpen → sector 드로어 열림(항상 클릭 가능, 로딩/에러/빈 상태 포함).
 */
export function SectorHeatmap({ labels, onOpen }: SectorHeatmapProps) {
  const { data: envelope, isLoading, isError } = useCardDetail<SectorDetail>('sector', true)
  const detail = envelope?.data
  const sectors = !isLoading && !isError && detail
    ? [...(detail.sectors ?? [])].sort((a, b) => a.rank - b.rank)
    : []

  return (
    <section
      className="mt-4 rounded-lg border border-slate-200 bg-white p-4 shadow-sm cursor-pointer hover:border-slate-300 transition"
      onClick={onOpen}
      role={onOpen ? 'button' : undefined}
      tabIndex={onOpen ? 0 : undefined}
      onKeyDown={(e) => {
        if (onOpen && (e.key === 'Enter' || e.key === ' ')) {
          e.preventDefault()
          onOpen()
        }
      }}
      aria-label="Sector 히트맵 — 클릭 시 상세 보기"
    >
      <header className="flex items-baseline justify-between">
        <h3 className="text-sm font-semibold text-slate-800">
          <span>Sector Flow</span>
          <span className="text-slate-500 mx-1.5">·</span>
          <span className="text-slate-500">섹터 흐름</span>
        </h3>
      </header>

      {isLoading ? (
        <p className="text-sm text-slate-400 mt-2">섹터 데이터 불러오는 중…</p>
      ) : isError || !detail || sectors.length === 0 ? (
        <p className="text-sm text-slate-400 mt-2">섹터 데이터 미생성</p>
      ) : (
        <div className="mt-3 grid grid-cols-3 sm:grid-cols-4 md:grid-cols-6 gap-2">
          {sectors.map((s) => {
            const tileClass = heatTileClass(s.rel_strength)
            const label = translate(`sector.${s.symbol}`, labels, s.symbol)
            return (
              <div
                key={s.symbol}
                className={`rounded border px-2 py-2 text-center text-xs font-medium ${tileClass}`}
                data-testid={`sector-tile-${s.symbol}`}
                data-rel={s.rel_strength}
              >
                <div className="font-semibold truncate">{label}</div>
                <div className="mt-0.5 tabular-nums">{formatRel(s.rel_strength)}</div>
                <div className="text-[10px] opacity-70">#{s.rank}</div>
              </div>
            )
          })}
        </div>
      )}
    </section>
  )
}
