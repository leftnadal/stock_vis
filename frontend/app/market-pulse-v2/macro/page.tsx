'use client'

/**
 * MP2-SUBPAGES S1 — 거시 근거 허브 (D-SUBPAGES-LAYOUT 가·D-SUBPAGES-DATA i).
 *
 * Phase 2 "왜 움직였나"의 근거 화면. v1 pulse API(`/api/v1/macro/pulse/`)를 그대로 소비
 * (useMarketPulse 재사용·신규 훅 0·pulse 계약 FREEZE 준수)하고, v1 props형 위젯 4종을
 * 원위치 import 재사용(이동 0). 탭 앵커(?tab=)로 딥링크 흡수, 라우트 1개.
 * rotation 서브스크린 동형(useSearchParams + Suspense). 무버스는 S2(준비 중).
 */
import { Suspense, useEffect, useState } from 'react'
import Link from 'next/link'
import { useSearchParams } from 'next/navigation'

import { useMarketPulse } from '@/hooks/useMarketPulse'
import FearGreedGauge from '@/components/macro/FearGreedGauge'
import YieldCurveChart from '@/components/macro/YieldCurveChart'
import EconomicIndicators from '@/components/macro/EconomicIndicators'
import GlobalMarketsCard from '@/components/macro/GlobalMarketsCard'

// 거시 집계는 장외(KST)엔 콜드 캐시라 라이브 집계가 느릴 수 있어 허브만 타임아웃을 건다.
// (BE는 SWR로 stale 즉시 응답 — D-SUBPAGES-SWR. FE는 그 대기가 길어질 때의 안전판.)
const HUB_TIMEOUT_MS = 20000
const STALE_BADGE_MIN = 5  // last_updated 나이가 이 값(분)을 넘으면 "N분 전 데이터" 배지 노출

/** last_updated(ISO)와 현재시각(ms)으로 경과 '분'. 파싱 실패·미래 시각이면 null. */
export function staleMinutes(lastUpdated: string | undefined, nowMs: number): number | null {
  if (!lastUpdated) return null
  const t = Date.parse(lastUpdated)
  if (Number.isNaN(t)) return null
  const min = Math.floor((nowMs - t) / 60000)
  return min >= 0 ? min : null
}

type TabKey = 'all' | 'rates' | 'sentiment' | 'global' | 'movers'

const TABS: { key: TabKey; label: string; disabled?: boolean }[] = [
  { key: 'all', label: '전체' },
  { key: 'rates', label: '금리' },
  { key: 'sentiment', label: '심리' },
  { key: 'global', label: '글로벌' },
  { key: 'movers', label: '무버스', disabled: true },
]
const VALID_TABS = new Set<string>(['all', 'rates', 'sentiment', 'global', 'movers'])

// 위젯 → 노출 탭. economy는 '금리·지표'로 rates 탭에 동승(CTA ② "금리·지표 →").
const show = (section: 'sentiment' | 'rates' | 'economy' | 'global', tab: TabKey) => {
  if (tab === 'all') return true
  if (section === 'economy') return tab === 'rates'
  return tab === section
}

function MacroHubInner() {
  // ⚠ 변수명 searchParams 금지(Turbopack 충돌) — params 사용.
  const params = useSearchParams()
  const rawTab = params.get('tab') ?? 'all'
  const activeTab: TabKey = (VALID_TABS.has(rawTab) ? rawTab : 'all') as TabKey

  const { data, isLoading, isError, refetch } = useMarketPulse({ timeoutMs: HUB_TIMEOUT_MS })

  // 나이 배지용 현재시각 — mount 후에만 설정(SSR/CSR Date.now() 불일치 회피, common-bugs #24).
  const [nowMs, setNowMs] = useState<number | null>(null)
  useEffect(() => {
    setNowMs(Date.now())
    const id = setInterval(() => setNowMs(Date.now()), 60000)
    return () => clearInterval(id)
  }, [])
  const ageMin = nowMs != null ? staleMinutes(data?.last_updated, nowMs) : null
  const isStale = ageMin != null && ageMin > STALE_BADGE_MIN

  const header = (
    <header className="px-2 pt-4">
      <Link href="/market-pulse-v2" className="text-xs text-slate-500 hover:text-slate-800">
        ← Market Pulse
      </Link>
      <div className="mt-1 flex items-center gap-2">
        <h1 className="text-2xl font-bold text-slate-900">거시 근거</h1>
        {isStale && (
          <span
            className="rounded-full border border-amber-200 bg-amber-50 px-2 py-0.5 text-[11px] font-medium text-amber-700"
            title="자동 갱신 중 — 마지막 성공 데이터를 표시합니다"
          >
            {ageMin}분 전 데이터
          </span>
        )}
      </div>
      <p className="text-xs text-slate-500 mt-1">
        오늘 국면의 배경 — 금리·심리·글로벌{data?.last_updated ? ` · ${data.last_updated}` : ''}
      </p>
    </header>
  )

  const tabBar = (
    <nav className="mt-3 flex gap-1 overflow-x-auto px-2 pb-1" aria-label="거시 탭">
      {TABS.map((t) =>
        t.disabled ? (
          <span
            key={t.key}
            className="shrink-0 rounded-full border border-slate-200 px-3 py-1 text-xs text-slate-400"
            title="S2에서 제공 예정"
          >
            {t.label} <span className="text-[10px]">준비 중</span>
          </span>
        ) : (
          <Link
            key={t.key}
            href={t.key === 'all' ? '/market-pulse-v2/macro' : `/market-pulse-v2/macro?tab=${t.key}`}
            scroll={false}
            className={`shrink-0 rounded-full border px-3 py-1 text-xs transition-colors ${
              activeTab === t.key
                ? 'border-slate-800 bg-slate-800 text-white'
                : 'border-slate-200 text-slate-600 hover:border-slate-400'
            }`}
          >
            {t.label}
          </Link>
        ),
      )}
    </nav>
  )

  return (
    <main className="max-w-4xl mx-auto pb-16">
      {header}
      {tabBar}
      <div className="px-2 py-3">
        {isLoading ? (
          <p className="text-slate-500">불러오는 중…</p>
        ) : isError || !data ? (
          <div
            className="rounded-md border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800"
            role="status"
          >
            <p>거시 데이터를 준비 중입니다 — 잠시 후 자동으로 다시 시도합니다.</p>
            <button
              type="button"
              onClick={() => refetch()}
              className="mt-2 rounded border border-amber-300 bg-white px-3 py-1 text-xs font-medium text-amber-800 hover:bg-amber-100"
            >
              다시 시도
            </button>
          </div>
        ) : (
          <div className="space-y-4">
            {/* 심리 + 금리(2열) */}
            {(show('sentiment', activeTab) || show('rates', activeTab)) && (
              <section className="grid gap-4 md:grid-cols-2">
                {show('sentiment', activeTab) && (
                  <div data-guide="marketPulse.macro.sentiment">
                    <FearGreedGauge data={data.fear_greed} />
                  </div>
                )}
                {show('rates', activeTab) && (
                  <div data-guide="marketPulse.macro.rates">
                    <YieldCurveChart data={data.interest_rates} />
                  </div>
                )}
              </section>
            )}
            {/* 경제지표(전폭) */}
            {show('economy', activeTab) && (
              <section data-guide="marketPulse.macro.economy">
                <EconomicIndicators data={data.economy} />
              </section>
            )}
            {/* 글로벌(전폭) */}
            {show('global', activeTab) && (
              <section data-guide="marketPulse.macro.global">
                <GlobalMarketsCard data={data.global_markets} />
              </section>
            )}
          </div>
        )}
      </div>
    </main>
  )
}

export default function MacroHubPage() {
  return (
    <Suspense fallback={<main className="max-w-4xl mx-auto px-2 py-6 text-slate-500">불러오는 중…</main>}>
      <MacroHubInner />
    </Suspense>
  )
}
