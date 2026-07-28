'use client'

/**
 * MP2-SECTOR-CD S2 (D-SECTOR-MOM-LANE 변형2) — 국면 스트립 레인.
 *
 * 차트 하단 x축 공유 독립 컴포넌트. 전환일 사이 구간 = 지속 국면으로 렌더(run-length).
 * 데이터원 = regime detail의 regime_history_30d [{date, stage}](기서빙, 컨테이너가 이미 fetch —
 *   신규 저장·파생·fetch 0). 국면 색은 meaning.ts regimeTone 단일소스(신규 색 발명 0).
 * 정렬: 모멘텀 차트와 동일 날짜 창(dates)을 소비 → 동일 순서·비례폭. 카테고리 축 기준 개념적 공유.
 */
import { regimeTone } from '../meaning'
import { translate } from '@/lib/i18n/marketPulse'

interface StripSegment {
  stage: string
  count: number
  startDate: string
}

/** 날짜 창 + 날짜별 국면 → 연속 동일 국면 구간(run-length). 미매핑 날짜는 'unknown'. */
export function buildSegments(
  dates: string[],
  regimeByDate: Map<string, string>,
): StripSegment[] {
  const segments: StripSegment[] = []
  for (const d of dates) {
    const stage = regimeByDate.get(d) ?? 'unknown'
    const last = segments[segments.length - 1]
    if (last && last.stage === stage) {
      last.count += 1
    } else {
      segments.push({ stage, count: 1, startDate: d })
    }
  }
  return segments
}

export function RegimeStrip({
  dates,
  regimeHistory = [],
  labels,
}: {
  dates: string[]
  regimeHistory?: { date: string; stage: string }[]
  labels?: Record<string, string>
}) {
  if (dates.length === 0 || regimeHistory.length === 0) return null

  const regimeByDate = new Map(regimeHistory.map((h) => [h.date, h.stage]))
  const segments = buildSegments(dates, regimeByDate)

  return (
    <div data-testid="regime-strip" className="mt-1">
      <div className="flex h-4 w-full overflow-hidden rounded border border-slate-200">
        {segments.map((seg, i) => {
          const known = seg.stage !== 'unknown'
          const label = known ? translate(`regime.${seg.stage}`, labels, seg.stage) : ''
          return (
            <div
              key={`${seg.startDate}-${i}`}
              data-testid={`strip-seg-${seg.stage}`}
              className={`flex items-center justify-center overflow-hidden whitespace-nowrap text-[9px] leading-none ${
                known ? regimeTone(seg.stage) : 'bg-slate-50 text-slate-300 border-slate-100'
              }`}
              style={{ flexGrow: seg.count, flexBasis: 0 }}
              title={label || '국면 정보 없음'}
            >
              {seg.count >= 3 ? label : ''}
            </div>
          )
        })}
      </div>
      <p className="mt-0.5 text-[9px] text-slate-400">국면 레인 — 구간 = 지속 국면(전환일 경계)</p>
    </div>
  )
}
