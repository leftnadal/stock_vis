'use client';

/**
 * 중심성 리더보드 (⑳-1) — container. 지표 드롭다운 + TanStack Query + 테이블.
 * 관계망 안에서 중심(허브·매개) 종목을 순위로 조망한다.
 */

import { useState } from 'react';
import { useCentralityTop } from '@/hooks/useMarketView';
import CentralityLeaderboardTable from './CentralityLeaderboardTable';
import { LEADERBOARD_LIMIT, LEADERBOARD_METRICS } from './leaderboardConfig';

export default function CentralityLeaderboard() {
  const [metric, setMetric] = useState(LEADERBOARD_METRICS[0].key);
  const { data, isLoading, isError } = useCentralityTop(metric, LEADERBOARD_LIMIT);

  return (
    <section className="mx-auto max-w-3xl px-4 py-6">
      <header className="mb-4">
        <h1 className="text-lg font-semibold text-slate-900">중심성 리더보드</h1>
        <p className="mt-1 text-sm text-slate-500">
          관계망에서 중심에 있는 종목 — 허브(영향력)와 매개(연결 다리)를 순위로.
        </p>
      </header>

      <div className="mb-3 flex items-center justify-between">
        <label className="text-sm text-slate-600">
          지표{' '}
          <select
            value={metric}
            onChange={(e) => setMetric(e.target.value)}
            className="ml-1 rounded border border-slate-300 px-2 py-1 text-sm"
            aria-label="중심성 지표 선택"
          >
            {LEADERBOARD_METRICS.map((m) => (
              <option key={m.key} value={m.key}>
                {m.label}
              </option>
            ))}
          </select>
        </label>
        {data?.as_of ? (
          <span className="text-xs text-slate-400">기준일 {data.as_of}</span>
        ) : null}
      </div>

      {isLoading ? (
        <p className="py-8 text-center text-sm text-slate-500">불러오는 중…</p>
      ) : isError ? (
        <p className="py-8 text-center text-sm text-rose-600">
          중심성 데이터를 불러오지 못했습니다.
        </p>
      ) : (
        <CentralityLeaderboardTable items={data?.results ?? []} metricKey={metric} />
      )}
    </section>
  );
}
