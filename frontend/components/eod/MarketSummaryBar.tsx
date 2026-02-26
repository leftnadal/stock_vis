'use client';

import { TrendingUp, TrendingDown, Minus, AlertTriangle } from 'lucide-react';
import type { MarketSummary } from '@/types/eod';

interface MarketSummaryBarProps {
  summary: MarketSummary;
}

function ChangeChip({ label, value }: { label: string; value: number }) {
  const isPositive = value > 0;
  const isNeutral = value === 0;

  const colorClass = isNeutral
    ? 'bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-300'
    : isPositive
    ? 'bg-green-50 dark:bg-green-900/20 text-green-700 dark:text-green-300'
    : 'bg-red-50 dark:bg-red-900/20 text-red-700 dark:text-red-300';

  const Icon = isNeutral ? Minus : isPositive ? TrendingUp : TrendingDown;

  return (
    <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-xs font-semibold ${colorClass}`}>
      <Icon className="w-3 h-3" />
      {label}
      <span>{value > 0 ? '+' : ''}{value.toFixed(2)}%</span>
    </span>
  );
}

function VixChip({ vix, regime }: { vix: number; regime: MarketSummary['vix_regime'] }) {
  const isHigh = regime === 'high_vol' || vix > 25;
  return (
    <span
      className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-xs font-semibold ${
        isHigh
          ? 'bg-orange-50 dark:bg-orange-900/20 text-orange-700 dark:text-orange-300'
          : 'bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-300'
      }`}
    >
      {isHigh && <AlertTriangle className="w-3 h-3" />}
      VIX {vix.toFixed(1)}
    </span>
  );
}

function BullBearBar({ bullish, bearish }: { bullish: number; bearish: number }) {
  const total = bullish + bearish;
  if (total === 0) return null;
  const bullPct = Math.round((bullish / total) * 100);

  return (
    <div className="flex items-center gap-1.5">
      <span className="text-xs text-green-600 dark:text-green-400 font-medium">{bullish}</span>
      <div className="w-16 h-1.5 rounded-full bg-gray-200 dark:bg-gray-600 overflow-hidden">
        <div
          className="h-full bg-green-500 rounded-full"
          style={{ width: `${bullPct}%` }}
        />
      </div>
      <span className="text-xs text-red-600 dark:text-red-400 font-medium">{bearish}</span>
    </div>
  );
}

export function MarketSummaryBar({ summary }: MarketSummaryBarProps) {
  const isVixHigh = summary.vix_regime === 'high_vol' || summary.vix > 25;

  return (
    <div className="mb-4 p-4 rounded-xl bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 shadow-sm">
      {/* 헤드라인 */}
      <div className="flex flex-wrap items-center gap-2 mb-3">
        <h2 className="text-base font-bold text-gray-900 dark:text-white">
          {summary.stock_universe.toLocaleString()}종목에서{' '}
          <span className="text-blue-600 dark:text-blue-400">
            {summary.total_signals}개
          </span>{' '}
          시그널 감지
        </h2>
        {isVixHigh && (
          <span className="inline-flex items-center gap-1 text-xs text-orange-600 dark:text-orange-400 bg-orange-50 dark:bg-orange-900/20 px-2 py-0.5 rounded-full border border-orange-200 dark:border-orange-700">
            <AlertTriangle className="w-3 h-3" />
            고변동성 구간
          </span>
        )}
      </div>

      {/* 지표 배지 */}
      <div className="flex flex-wrap items-center gap-2 mb-3">
        <ChangeChip label="S&P500" value={summary.sp500_change} />
        <ChangeChip label="QQQ" value={summary.qqq_change} />
        <VixChip vix={summary.vix} regime={summary.vix_regime} />
      </div>

      {/* 불/베어 비율 */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <span className="text-xs text-gray-500 dark:text-gray-400">강세/약세</span>
          <BullBearBar bullish={summary.bullish_count} bearish={summary.bearish_count} />
        </div>
        <span className="text-xs text-gray-400 dark:text-gray-500">
          {summary.stocks_with_signals}개 종목
        </span>
      </div>
    </div>
  );
}
