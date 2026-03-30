'use client';

import type { IndustryRank } from '@/types/validation';

interface Props {
  ranks: IndustryRank[];
}

export default function IndustryPosition({ ranks }: Props) {
  if (ranks.length === 0) return null;

  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg p-5 border border-gray-200 dark:border-gray-700">
      <h3 className="text-base font-semibold text-gray-900 dark:text-white mb-4">산업 내 경쟁력 요약</h3>

      <div className="space-y-3">
        {ranks.map((r) => {
          const pct = r.total > 0 ? ((r.total - r.rank + 1) / r.total) * 100 : 0;
          const barColor = pct >= 70 ? 'bg-green-500' : pct >= 40 ? 'bg-yellow-400' : 'bg-red-400';

          return (
            <div key={r.metric} className="flex items-center gap-3">
              <span className="text-sm text-gray-700 dark:text-gray-300 w-28 flex-shrink-0 truncate">
                {r.display_name}
              </span>
              <div className="flex-1 h-5 bg-gray-100 dark:bg-gray-700 rounded-full overflow-hidden relative">
                <div
                  className={`h-full ${barColor} rounded-full transition-all`}
                  style={{ width: `${Math.max(pct, 5)}%` }}
                />
              </div>
              <span className="text-xs text-gray-500 dark:text-gray-400 w-16 text-right flex-shrink-0">
                {r.rank}위/{r.total}
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
}
