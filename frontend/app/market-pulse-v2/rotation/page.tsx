'use client'

/**
 * MP2-SECTOR-CD Slice 3 — RRG 회전 맵 서브스크린 (D-SECTOR-NAV 옵션 B).
 *
 * chainsight 서브스크린 동형(useSearchParams + Suspense). 진입 파라미터 `from` = 출발 섹터.
 * 데이터 = 판단 카드와 동일 sector 카드 fetch(useCardDetail — TanStack 캐시 공유, 신규 fetch 0).
 * 뒤로가기 = 판단 화면(/market-pulse-v2) 복귀.
 */
import { Suspense } from 'react'
import Link from 'next/link'
import { useRouter, useSearchParams } from 'next/navigation'

import { useCardDetail } from '@/hooks/useMarketPulseV2'
import { useMarketPulseI18n } from '@/lib/i18n/marketPulse'
import type { SectorDetail } from '@/lib/api/marketPulseV2'
import { RRGChart } from '../details/RRGChart'
import { CD_STATE_ORDER, cdStateDotFill, cdStateLabel } from '../sectorColor'

function RotationInner() {
  // ⚠ 변수명 searchParams 금지(Turbopack 충돌) — params 사용.
  const params = useSearchParams()
  const router = useRouter()
  const fromSymbol = params.get('from')?.toUpperCase() || undefined

  // CD-READ 변형 H: 점 탭 → 포커스 전환 = URL from 동기화(현행 구조). scroll 유지.
  const handleFocusChange = (symbol: string) => {
    router.replace(`/market-pulse-v2/rotation?from=${symbol}`, { scroll: false })
  }

  const { data, isLoading, isError } = useCardDetail<SectorDetail>('sector', true)
  const { data: i18n } = useMarketPulseI18n()
  const labels = i18n?.labels
  const payload = data?.data

  return (
    <div className="mx-auto max-w-2xl px-4 py-6">
      <header className="mb-4 flex items-center justify-between gap-2">
        <div>
          <h1 className="text-lg font-bold text-slate-900">섹터 회전 맵</h1>
          <p className="text-xs text-slate-500">상대강도(x) × 5일 모멘텀(y) — 돈이 어디로 회전하나</p>
        </div>
        <Link
          href="/market-pulse-v2"
          data-testid="rrg-back"
          className="shrink-0 rounded border border-slate-200 px-2 py-1 text-xs text-slate-600 hover:bg-slate-50"
        >
          ← 판단 화면
        </Link>
      </header>

      {isLoading ? (
        <p className="text-sm text-slate-400">불러오는 중…</p>
      ) : isError || !payload?.available ? (
        <p data-testid="rrg-unavailable" className="text-sm text-slate-500">회전 맵 데이터가 아직 준비되지 않았습니다.</p>
      ) : (
        <>
          <RRGChart payload={payload} labels={labels} fromSymbol={fromSymbol} onFocusChange={handleFocusChange} />
          <ul data-testid="rrg-legend" className="mt-3 flex flex-wrap gap-x-3 gap-y-1 text-[10px] text-slate-500">
            {CD_STATE_ORDER.map((state) => (
              <li key={state} className="flex items-center gap-1">
                <span className="inline-block h-2 w-2 rounded-full" style={{ background: cdStateDotFill(state) }} />
                {cdStateLabel(state)}
              </li>
            ))}
          </ul>
          <p className="mt-2 text-[10px] text-slate-400">
            점을 탭하면 그 섹터로 포커스(꼬리·라벨)가 이동합니다. 꼬리 = 최근 {5}거래일 궤적(현재 상태색) —
            포커스 섹터만 표시, "전체 꼬리"로 전 섹터 궤적을 켤 수 있습니다. 배경·점 색은 서빙된 판정(cd_state) 기준.
          </p>
        </>
      )}
    </div>
  )
}

export default function RotationPage() {
  return (
    <Suspense fallback={<div className="mx-auto max-w-2xl px-4 py-6 text-sm text-slate-400">불러오는 중…</div>}>
      <RotationInner />
    </Suspense>
  )
}
