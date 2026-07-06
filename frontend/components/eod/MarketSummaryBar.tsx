'use client';

import { TrendingUp, TrendingDown, Minus, AlertTriangle } from 'lucide-react';
import { VixChip } from './VixChip';
import { CHANGE_CHIP, STRENGTH_TEXT, STRENGTH_BAR_FILL } from './colorSemantics';
import type { MarketSummary } from '@/types/eod';

interface MarketSummaryBarProps {
  summary: MarketSummary;
}

function ChangeChip({ label, value }: { label: string; value: number }) {
  const isPositive = value > 0;
  const isNeutral = value === 0;

  // 한국축(D-COLOR-SYSTEM): 상승 rose / 하락 sky / 보합 gray. 아이콘·부호 병기(색 보조).
  const colorClass = isNeutral
    ? CHANGE_CHIP.neutral
    : isPositive
    ? CHANGE_CHIP.up
    : CHANGE_CHIP.down;

  const Icon = isNeutral ? Minus : isPositive ? TrendingUp : TrendingDown;

  return (
    <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-xs font-semibold ${colorClass}`}>
      <Icon className="w-3 h-3" />
      {label}
      <span>{value > 0 ? '+' : ''}{value.toFixed(2)}%</span>
    </span>
  );
}


function BullBearBar({ bullish, bearish }: { bullish: number; bearish: number }) {
  const total = bullish + bearish;
  if (total === 0) return null;
  const bullPct = Math.round((bullish / total) * 100);

  return (
    <div className="flex items-center gap-1.5">
      <span className={`text-xs ${STRENGTH_TEXT.positive} font-medium`}>{bullish}</span>
      <div className="w-24 h-2 rounded-full bg-gray-200 dark:bg-gray-600 overflow-hidden">
        <div
          className={`h-full ${STRENGTH_BAR_FILL} rounded-full`}
          style={{ width: `${bullPct}%` }}
        />
      </div>
      <span className={`text-xs ${STRENGTH_TEXT.negative} font-medium`}>{bearish}</span>
      <span className="text-[10px] text-gray-400 dark:text-gray-500 ml-0.5">({bullPct}%)</span>
    </div>
  );
}

export function MarketSummaryBar({ summary }: MarketSummaryBarProps) {
  const regimeLabel = summary.vix_regime === 'high_vol'
    ? '고변동성 구간'
    : summary.vix_regime === 'elevated'
    ? '변동성 주의'
    : null;

  const regimeBadgeClass = summary.vix_regime === 'high_vol'
    ? 'text-orange-600 dark:text-orange-400 bg-orange-50 dark:bg-orange-900/20 border-orange-200 dark:border-orange-700'
    : 'text-yellow-600 dark:text-yellow-400 bg-yellow-50 dark:bg-yellow-900/20 border-yellow-200 dark:border-yellow-700';

  return (
    <div className="mb-4 p-4 rounded-xl bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 shadow-sm">
      {/* 헤드라인 */}
      <div className="flex flex-wrap items-center gap-2 mb-3">
        <h2 className="text-xl font-bold text-gray-900 dark:text-white">
          {summary.stock_universe.toLocaleString()}종목에서{' '}
          <span className="text-blue-600 dark:text-blue-400 text-2xl font-extrabold">
            {summary.total_signals}개
          </span>{' '}
          시그널 감지
        </h2>
        {regimeLabel && (
          <span className={`inline-flex items-center gap-1 text-xs px-2 py-0.5 rounded-full border ${regimeBadgeClass}`}>
            <AlertTriangle className="w-3 h-3" />
            {regimeLabel}
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
