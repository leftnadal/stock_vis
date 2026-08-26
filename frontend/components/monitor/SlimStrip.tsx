// 상세 화면 슬림 스트립 헤더 (MON-DETAIL-P1 T1, D-MON-DETAIL-LAYOUT-B).
// 6토큰(상태·존·점수+Δ·손절여유·D-day·danger) + 타이틀 행(종목·scope·관제 일차)
// + 펼침 패널 2종(가격 사다리·신호). 전 데이터는 BE 단일 소스 소비 — FE 재계산 금지.
'use client'

import { useCallback, useSyncExternalStore } from 'react'

import { ChevronDown, ChevronRight } from 'lucide-react'

import { PriceLadder } from '@/components/monitor/PriceLadder'
import { STATE_TONE_CLASS, ddayLabel, stateMeta } from '@/lib/monitor/display'
import type { Claim, Monitor, MonitorIndicator, MonitorScope } from '@/types/monitor'
import { dirArrow, formatIndicator, formatPctRule, formatScore } from '@/utils/formatters'

const SCOPE_LABEL: Record<MonitorScope, string> = {
  market: '시장',
  sector: '섹터',
  theme: '테마',
  fund: '펀드',
  stock: '종목',
}

const TOGGLE_EVENT = 'mon-detail-toggle'

function readToggle(key: string): boolean {
  try {
    return window.localStorage.getItem(key) === '1'
  } catch {
    return false
  }
}

// 펼침 상태 localStorage 유지(재방문 복원). 외부 스토어(localStorage) 동기화는
// useSyncExternalStore로 — 하이드레이션 안전(server snapshot=접힘) + effect 내 setState 회피.
function usePersistedToggle(key: string): [boolean, () => void] {
  const subscribe = useCallback((cb: () => void) => {
    window.addEventListener('storage', cb)
    window.addEventListener(TOGGLE_EVENT, cb)
    return () => {
      window.removeEventListener('storage', cb)
      window.removeEventListener(TOGGLE_EVENT, cb)
    }
  }, [])
  const open = useSyncExternalStore(
    subscribe,
    () => readToggle(key),
    () => false // SSR·첫 렌더 = 접힘 기본(복원은 하이드레이션 후 재조정)
  )
  const toggle = useCallback(() => {
    try {
      window.localStorage.setItem(key, open ? '0' : '1')
    } catch {
      /* 프라이버시 모드 무시 */
    }
    window.dispatchEvent(new Event(TOGGLE_EVENT))
  }, [key, open])
  return [open, toggle]
}

function Token({
  label,
  value,
  tone = 'default',
  testid,
}: {
  label: string
  value: React.ReactNode
  tone?: 'default' | 'danger' | 'muted'
  testid?: string
}) {
  const valueTone =
    tone === 'danger'
      ? 'text-red-600 dark:text-red-400'
      : tone === 'muted'
        ? 'text-gray-400'
        : 'text-gray-900 dark:text-gray-100'
  return (
    <div className="flex flex-col" data-testid={testid}>
      <span className="text-[10px] uppercase tracking-wide text-gray-400">{label}</span>
      <span className={`text-sm font-semibold ${valueTone}`}>{value}</span>
    </div>
  )
}

// 관제 일차 = 생성일 이후 경과 일수(+1, 개시일=1일차).
function trackingDay(createdAt: string): number {
  const start = new Date(createdAt.slice(0, 10) + 'T00:00:00')
  const today = new Date()
  today.setHours(0, 0, 0, 0)
  return Math.max(1, Math.floor((today.getTime() - start.getTime()) / 86400000) + 1)
}

export function SlimStrip({
  monitor,
  zoneClaim,
  scoreDelta,
  indicators,
  latestValueById,
  sufficientById,
}: {
  monitor: Monitor
  zoneClaim?: Claim | null
  scoreDelta?: number | null
  indicators: MonitorIndicator[]
  latestValueById: Map<string, number | null>
  sufficientById?: Map<string, boolean> // MON-P2A T3: 지표별 충분성(신호 배지)
}) {
  const [priceOpen, togglePrice] = usePersistedToggle('monitor-detail:panel:price')
  const [signalsOpen, toggleSignals] = usePersistedToggle('monitor-detail:panel:signals')

  const meta = stateMeta(monitor.current_state)
  const zd = zoneClaim?.zone_display ?? null
  const score = monitor.latest_score
  const cov = monitor.indicator_coverage // MON-P2A T3: {sufficient, total}
  const dday = ddayLabel(monitor.next_deadline)
  const currencyCode = monitor.currency_code ?? 'USD' // PART B-FE 숫자 표시 규약 '가'

  // 위험 강조 = 기존 신호만 소비(신규 임계 창설 금지, T1): danger_streak·close_suggested·이탈 존.
  const dangerActive =
    monitor.danger_streak > 0 || monitor.close_suggested || zd?.zone === 'exited'
  const stopPct = zd?.stop_distance_pct

  return (
    <div className="mb-4">
      {/* 타이틀 행 */}
      <div className="mb-3 flex items-center gap-2">
        <span className="rounded bg-gray-100 px-1.5 py-0.5 text-[11px] text-gray-500 dark:bg-gray-700 dark:text-gray-400">
          {SCOPE_LABEL[monitor.scope]}
        </span>
        <h1 className="truncate font-semibold text-gray-900 dark:text-gray-100">{monitor.name}</h1>
        <span className="ml-auto flex-shrink-0 text-[11px] text-gray-400" data-testid="tracking-day">
          관제 {trackingDay(monitor.created_at)}일차
        </span>
      </div>

      {/* 6토큰 스트립 */}
      <div
        className="grid grid-cols-3 gap-x-3 gap-y-3 rounded-xl border border-gray-200 p-3 sm:grid-cols-6 dark:border-gray-700"
        data-testid="slim-strip"
      >
        <Token
          label="상태"
          testid="token-state"
          value={
            <span className={`rounded px-1.5 py-0.5 text-xs ${STATE_TONE_CLASS[meta.tone]}`}>
              {meta.label}
            </span>
          }
        />
        <Token
          label="존"
          testid="token-zone"
          value={zd?.label ?? '—'}
          tone={zd?.label ? 'default' : 'muted'}
        />
        <Token
          label="점수"
          testid="token-score"
          value={
            <span className="inline-flex items-baseline gap-1">
              {score != null ? formatScore(score) : '—'}
              {scoreDelta != null && (
                <span
                  data-testid="token-score-delta"
                  className={`text-[10px] ${
                    scoreDelta > 0
                      ? 'text-green-600 dark:text-green-400'
                      : scoreDelta < 0
                        ? 'text-red-600 dark:text-red-400'
                        : 'text-gray-400'
                  }`}
                >
                  {dirArrow(scoreDelta, 3) || '·'}
                  {formatScore(scoreDelta, { signed: true })}
                </span>
              )}
              {/* MON-P2A T3: 커버리지 접미(유효/전체). 유효<전체면 경고톤(부분 데이터). */}
              {cov && (
                <span
                  data-testid="token-score-coverage"
                  className={`text-[10px] ${cov.sufficient < cov.total ? 'text-amber-600 dark:text-amber-400' : 'text-gray-400'}`}
                >
                  · {cov.sufficient}/{cov.total}
                </span>
              )}
            </span>
          }
          tone={score != null ? 'default' : 'muted'}
        />
        <Token
          label="손절여유"
          testid="token-stop-distance"
          value={typeof stopPct === 'number' ? formatPctRule(stopPct) : '—'}
          tone={typeof stopPct === 'number' ? (dangerActive ? 'danger' : 'default') : 'muted'}
        />
        <Token
          label="기한"
          testid="token-dday"
          value={dday ?? '—'}
          tone={dday ? 'default' : 'muted'}
        />
        <Token
          label="위험"
          testid="token-danger"
          value={
            monitor.close_suggested
              ? '마감 제안'
              : monitor.danger_streak > 0
                ? `${monitor.danger_streak}회`
                : '이상 없음'
          }
          tone={dangerActive ? 'danger' : 'muted'}
        />
      </div>

      {/* 펼침 패널 2종 (접힘 기본, localStorage 복원) */}
      <div className="mt-3 space-y-2">
        {zd && (
          <div className="rounded-xl border border-gray-100 dark:border-gray-800">
            <button
              type="button"
              onClick={togglePrice}
              data-testid="panel-toggle-price"
              aria-expanded={priceOpen}
              className="flex w-full items-center gap-1.5 px-4 py-2.5 text-sm font-medium text-gray-700 dark:text-gray-300"
            >
              {priceOpen ? <ChevronDown size={16} /> : <ChevronRight size={16} />}
              가격 사다리
            </button>
            {priceOpen && (
              <div className="border-t border-gray-100 px-4 py-3 dark:border-gray-800" data-testid="panel-price">
                <PriceLadder zoneDisplay={zd} currencyCode={currencyCode} />
                <p className="mt-3 text-[11px] text-gray-400">일봉 기준 · 스윙 타이밍</p>
              </div>
            )}
          </div>
        )}

        <div className="rounded-xl border border-gray-100 dark:border-gray-800">
          <button
            type="button"
            onClick={toggleSignals}
            data-testid="panel-toggle-signals"
            aria-expanded={signalsOpen}
            className="flex w-full items-center gap-1.5 px-4 py-2.5 text-sm font-medium text-gray-700 dark:text-gray-300"
          >
            {signalsOpen ? <ChevronDown size={16} /> : <ChevronRight size={16} />}
            신호 {indicators.length > 0 && <span className="text-gray-400">({indicators.length})</span>}
          </button>
          {signalsOpen && (
            <div className="border-t border-gray-100 px-4 py-1 dark:border-gray-800" data-testid="panel-signals">
              {indicators.length === 0 ? (
                <p className="py-2 text-sm text-gray-400">등록된 지표가 없어요.</p>
              ) : (
                indicators.map((ind) => {
                  const v = latestValueById.get(ind.id)
                  // MON-P2A T3: 지표별 충분성 배지. false만 표기(부족 = 점수 제외됨).
                  const suff = sufficientById?.get(ind.id)
                  return (
                    <div
                      key={ind.id}
                      className="flex items-center justify-between gap-2 border-b border-gray-100 py-2 text-sm last:border-0 dark:border-gray-800"
                    >
                      <span className="flex min-w-0 flex-1 items-center gap-1.5">
                        <span className="min-w-0 truncate text-gray-600 dark:text-gray-300">
                          {ind.name}
                        </span>
                        {suff === false && (
                          <span
                            data-testid="signal-insufficient-badge"
                            className="flex-shrink-0 rounded bg-gray-100 px-1 py-0.5 text-[10px] text-gray-400 dark:bg-gray-800"
                            title="관측 이력 부족 — 점수 집계에서 제외됨"
                          >
                            부족
                          </span>
                        )}
                      </span>
                      <span className="flex-shrink-0 text-gray-400">
                        {typeof v === 'number' ? formatIndicator(v) : '—'}
                      </span>
                    </div>
                  )
                })
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
