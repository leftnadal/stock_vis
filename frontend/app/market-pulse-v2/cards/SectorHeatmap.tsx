'use client'

import { translate } from '@/lib/i18n/marketPulse'
import type { SectorDetail } from '@/lib/api/marketPulseV2'
import { useCardDetail } from '@/hooks/useMarketPulseV2'
import { sectorTileClass } from '../sectorColor'
import { SenseNote } from './SenseNote'

function formatRel(v: number): string {
  const sign = v > 0 ? '+' : ''
  return `${sign}${v.toFixed(2)}%`
}

interface SectorHeatmapProps {
  labels?: Record<string, string>
  onOpen?: () => void
  sense?: string | null
}

/**
 * Sector 히트맵 — D-MP2-SURFACE 신규 full-width 컴포넌트.
 * useCardDetail<SectorDetail>('sector', true) 로 11섹터 fetch.
 * rank 오름차순 정렬 → 11 타일 렌더.
 * 색 = sectorTileClass (상승=rose, 하락=sky, 한국 관례, sectorColor.ts 단일소스).
 * sense prop → 히트맵 아래 SenseNote 렌더(null이면 미렌더).
 * onOpen → sector 드로어 열림(항상 클릭 가능, 로딩/에러/빈 상태 포함).
 */
export function SectorHeatmap({ labels, onOpen, sense }: SectorHeatmapProps) {
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
            const tileClass = sectorTileClass(s.rel_strength)
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

      {/* sense 한 줄 복원: 히트맵 아래 상시 — null이면 SenseNote가 미렌더 */}
      <SenseNote sense={sense} />
    </section>
  )
}
