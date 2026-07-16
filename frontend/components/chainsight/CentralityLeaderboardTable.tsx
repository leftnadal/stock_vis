'use client';

/**
 * 중심성 리더보드 테이블 (⑳-1) — presentational.
 * 데이터 주입형(items). rank_delta 3상태(▲상승·▼하락·— 무변화/null) + ego 링크.
 */

import Link from 'next/link';
import { CHANGE_TEXT } from '@/components/common/colorSemantics';
import type { CentralityLeaderboardItem } from '@/types/chainsight';
import {
  LEADERBOARD_COLUMNS,
  egoUrlForSymbol,
  metricByKey,
} from './leaderboardConfig';

function RankDelta({ delta }: { delta: number | null }) {
  // 상승(순위 개선)=양수 → 한국축 강세색(rose). 하락=음수 → 약세색(sky). 0/null → 중립.
  if (delta === null || delta === undefined || delta === 0) {
    return (
      <span data-testid="rank-delta" data-state="flat" className="text-gray-400">
        —
      </span>
    );
  }
  if (delta > 0) {
    return (
      <span data-testid="rank-delta" data-state="up" className={CHANGE_TEXT.up}>
        ▲ {delta}
      </span>
    );
  }
  return (
    <span data-testid="rank-delta" data-state="down" className={CHANGE_TEXT.down}>
      ▼ {Math.abs(delta)}
    </span>
  );
}

export interface CentralityLeaderboardTableProps {
  items: CentralityLeaderboardItem[];
  metricKey: string;
}

export default function CentralityLeaderboardTable({
  items,
  metricKey,
}: CentralityLeaderboardTableProps) {
  const metric = metricByKey(metricKey);

  if (items.length === 0) {
    return (
      <p className="py-8 text-center text-sm text-gray-500">
        표시할 중심성 데이터가 없습니다.
      </p>
    );
  }

  const alignClass = (a: string) =>
    a === 'right' ? 'text-right' : a === 'center' ? 'text-center' : 'text-left';

  return (
    <table className="w-full text-sm" data-testid="centrality-leaderboard-table">
      <thead>
        <tr className="border-b border-slate-200 text-xs text-slate-500">
          {LEADERBOARD_COLUMNS.map((c) => (
            <th key={c.key} className={`px-3 py-2 font-medium ${alignClass(c.align)}`}>
              {c.key === 'value' ? metric.label : c.label}
            </th>
          ))}
        </tr>
      </thead>
      <tbody>
        {items.map((item) => (
          <tr
            key={item.symbol}
            className="border-b border-slate-100 hover:bg-slate-50"
            data-testid={`row-${item.symbol}`}
          >
            <td className="px-3 py-2 text-right tabular-nums text-slate-500">
              {item.rank}
            </td>
            <td className="px-3 py-2">
              <Link
                href={egoUrlForSymbol(item.symbol)}
                className="font-medium text-slate-800 hover:text-rose-600"
              >
                {item.symbol}
              </Link>
              {item.name ? (
                <span className="ml-2 text-xs text-slate-400">{item.name}</span>
              ) : null}
            </td>
            <td className="px-3 py-2 text-right tabular-nums text-slate-700">
              {metric.format(item)}
            </td>
            <td className="px-3 py-2 text-center tabular-nums">
              <RankDelta delta={item.rank_delta} />
            </td>
            <td className="px-3 py-2 text-center">
              <Link
                href={egoUrlForSymbol(item.symbol)}
                className="text-xs text-sky-600 hover:underline"
                aria-label={`${item.symbol} 관계망 보기`}
              >
                관계망 →
              </Link>
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
