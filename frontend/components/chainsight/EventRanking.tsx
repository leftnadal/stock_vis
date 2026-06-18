'use client';

import { useQuery } from '@tanstack/react-query';
import { useRouter } from 'next/navigation';
import { ArrowLeft } from 'lucide-react';
import Link from 'next/link';
import { fetchEventStocks } from '@/services/chainsightService';
import { getLabelForTheme, METRIC_INFO } from '@/constants/eventThemes';
import type { EventRankingItem } from '@/types/chainsight';
import LowLiquidityPanel from '@/components/chainsight/LowLiquidityPanel';
import MetricInfoPopover from '@/components/chainsight/MetricInfoPopover';

interface Props {
  theme: string;
}

function LowLiquidityBadge() {
  return (
    <span className="inline-flex items-center rounded-full bg-amber-100 dark:bg-amber-900 text-amber-800 dark:text-amber-200 text-xs font-medium px-2 py-0.5">
      저유동성
    </span>
  );
}

const PRIMARY_METRICS = [
  'trend_quality',
  'theme_beta',
  'capture_spread',
] as const;

function RankingHeader() {
  return (
    <div
      className="flex items-center gap-4 px-4 py-2 bg-gray-50 dark:bg-gray-800/60 border-b border-gray-200 dark:border-gray-700"
      aria-label="지표 컬럼 헤더"
    >
      {/* rank placeholder */}
      <span className="w-6 shrink-0" />
      {/* symbol/name placeholder */}
      <div className="flex-1 min-w-0" />
      {/* return/score placeholder */}
      <div className="w-20 shrink-0" />
      {/* 3 primary metric columns */}
      <div className="flex gap-3">
        {PRIMARY_METRICS.map((key) => (
          <div
            key={key}
            className="w-20 flex items-center justify-end gap-1 text-xs font-medium text-gray-500 dark:text-gray-400"
          >
            <span>{METRIC_INFO[key].label}</span>
            <MetricInfoPopover metricKey={key} />
          </div>
        ))}
      </div>
    </div>
  );
}

function RankingRow({ item, rank }: { item: EventRankingItem; rank: number }) {
  const isPositive = item.raw_return >= 0;

  return (
    <div className="border-b border-gray-100 dark:border-gray-700">
      <Link
        href={`/chainsight/${item.symbol}`}
        className="flex items-center gap-4 py-3 px-4 hover:bg-gray-50 dark:hover:bg-gray-800/50 cursor-pointer"
      >
        <span className="w-6 text-sm font-bold text-gray-400 text-right">{rank}</span>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <span className="font-semibold text-sm text-gray-900 dark:text-gray-100">{item.symbol}</span>
            {item.is_low_liquidity && <LowLiquidityBadge />}
          </div>
          <span className="text-xs text-gray-500 dark:text-gray-400 truncate block">{item.name}</span>
        </div>
        <div className="w-20 shrink-0 text-right">
          <div className={`text-sm font-medium ${isPositive ? 'text-green-600' : 'text-red-500'}`}>
            {isPositive ? '▲' : '▼'} {Math.abs(item.raw_return * 100).toFixed(2)}%
          </div>
          <div className="text-xs text-gray-500 dark:text-gray-400">관심도 {item.score.toFixed(1)}</div>
        </div>
        {/* 3 primary metric value columns — placeholder for Slice 2 */}
        <div className="flex gap-3">
          {PRIMARY_METRICS.map((key) => (
            <div key={key} className="w-20 text-right text-sm text-gray-400 dark:text-gray-500">
              —
            </div>
          ))}
        </div>
      </Link>
      {item.is_low_liquidity && (
        <div className="px-4 pb-3">
          <LowLiquidityPanel item={item} />
        </div>
      )}
    </div>
  );
}

export default function EventRanking({ theme }: Props) {
  const router = useRouter();
  const label = getLabelForTheme(theme);

  const { data, isLoading, isError } = useQuery({
    queryKey: ['chainsight', 'events', theme, 'stocks'],
    queryFn: () => fetchEventStocks(theme),
    staleTime: 1000 * 60 * 5,
  });

  return (
    <div className="p-6">
      <div className="mb-6">
        <button
          onClick={() => router.back()}
          className="flex items-center gap-1 text-sm text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200 mb-4"
        >
          <ArrowLeft size={16} />
          이벤트 보드
        </button>
        <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100">
          {label.ko} — 관련 종목 그룹
        </h1>
      </div>

      {isLoading && (
        <div className="p-8 text-center text-gray-500">로딩 중...</div>
      )}

      {isError && (
        <div className="p-8 text-center text-red-500">데이터를 불러올 수 없습니다</div>
      )}

      {data && data.length === 0 && (
        <div className="p-8 text-center text-gray-500">종목 데이터가 없습니다</div>
      )}

      {data && data.length > 0 && (
        <div className="rounded-xl border border-gray-200 dark:border-gray-700 overflow-hidden">
          <RankingHeader />
          {[...data]
            .sort((a, b) => b.score - a.score)
            .map((item, index) => (
              <RankingRow key={item.symbol} item={item} rank={index + 1} />
            ))}
        </div>
      )}
    </div>
  );
}
