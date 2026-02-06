// Market data badge component

'use client';

import React from 'react';
import { TrendingUp, TrendingDown, Minus, Target, Activity } from 'lucide-react';
import { MarketData, PricePosition, Valuation, AnalystRatings } from '@/types/news';

interface MarketDataBadgeProps {
  data: MarketData;
  compact?: boolean;
}

// Format percentage with sign
function formatPercent(value: number | undefined | null): string {
  if (value === undefined || value === null) return '-';
  const sign = value >= 0 ? '+' : '';
  return `${sign}${value.toFixed(1)}%`;
}

// Format price
function formatPrice(value: number | undefined | null): string {
  if (value === undefined || value === null) return '-';
  return `$${value.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

// Color based on percentage value
function getPercentColor(value: number | undefined | null): string {
  if (value === undefined || value === null) return 'text-gray-500';
  if (value > 0) return 'text-green-600 dark:text-green-400';
  if (value < 0) return 'text-red-600 dark:text-red-400';
  return 'text-gray-500 dark:text-gray-400';
}

// Price position section
function PricePositionSection({ position }: { position: PricePosition }) {
  const highDistance = position.distance_from_52w_high;
  const lowDistance = position.distance_from_52w_low;

  // Calculate bar position (0 = at low, 100 = at high)
  let barPosition = 50;
  if (position.week_52_high && position.week_52_low && position.current_price) {
    const range = position.week_52_high - position.week_52_low;
    if (range > 0) {
      barPosition = ((position.current_price - position.week_52_low) / range) * 100;
    }
  }

  return (
    <div className="space-y-2">
      {/* 52-week range bar */}
      {position.week_52_low && position.week_52_high && (
        <div className="space-y-1">
          <div className="flex justify-between text-xs text-gray-500 dark:text-gray-400">
            <span>{formatPrice(position.week_52_low)}</span>
            <span>52주 범위</span>
            <span>{formatPrice(position.week_52_high)}</span>
          </div>
          <div className="relative h-2 bg-gray-200 dark:bg-gray-700 rounded-full">
            <div
              className="absolute top-0 w-3 h-2 bg-blue-500 dark:bg-blue-400 rounded-full transform -translate-x-1/2"
              style={{ left: `${Math.min(Math.max(barPosition, 5), 95)}%` }}
            />
          </div>
        </div>
      )}

      {/* Distance badges */}
      <div className="flex flex-wrap gap-2 text-xs">
        {highDistance !== undefined && (
          <span className={`px-2 py-0.5 rounded bg-gray-100 dark:bg-gray-800 ${getPercentColor(highDistance)}`}>
            고가 대비 {formatPercent(highDistance)}
          </span>
        )}
        {lowDistance !== undefined && (
          <span className={`px-2 py-0.5 rounded bg-gray-100 dark:bg-gray-800 ${getPercentColor(lowDistance)}`}>
            저가 대비 {formatPercent(lowDistance)}
          </span>
        )}
      </div>

      {/* Moving averages */}
      {(position.vs_ma_50 !== undefined || position.vs_ma_200 !== undefined) && (
        <div className="flex flex-wrap gap-2 text-xs">
          {position.vs_ma_50 !== undefined && (
            <span className={`flex items-center gap-1 px-2 py-0.5 rounded bg-gray-100 dark:bg-gray-800 ${getPercentColor(position.vs_ma_50)}`}>
              <Activity className="w-3 h-3" />
              50일 MA {formatPercent(position.vs_ma_50)}
            </span>
          )}
          {position.vs_ma_200 !== undefined && (
            <span className={`flex items-center gap-1 px-2 py-0.5 rounded bg-gray-100 dark:bg-gray-800 ${getPercentColor(position.vs_ma_200)}`}>
              <Activity className="w-3 h-3" />
              200일 MA {formatPercent(position.vs_ma_200)}
            </span>
          )}
        </div>
      )}
    </div>
  );
}

// Valuation section
function ValuationSection({ valuation }: { valuation: Valuation }) {
  return (
    <div className="flex flex-wrap gap-2 text-xs">
      {valuation.pe_ratio !== undefined && valuation.pe_ratio !== null && (
        <span className="px-2 py-0.5 rounded bg-gray-100 dark:bg-gray-800 text-gray-700 dark:text-gray-300">
          PER {valuation.pe_ratio.toFixed(1)}x
        </span>
      )}
      {valuation.roe !== undefined && valuation.roe !== null && (
        <span className="px-2 py-0.5 rounded bg-gray-100 dark:bg-gray-800 text-gray-700 dark:text-gray-300">
          ROE {valuation.roe.toFixed(1)}%
        </span>
      )}
      {valuation.beta !== undefined && valuation.beta !== null && (
        <span className="px-2 py-0.5 rounded bg-gray-100 dark:bg-gray-800 text-gray-700 dark:text-gray-300">
          Beta {valuation.beta.toFixed(2)}
        </span>
      )}
      {valuation.analyst_upside !== undefined && valuation.analyst_upside !== null && (
        <span className={`flex items-center gap-1 px-2 py-0.5 rounded bg-gray-100 dark:bg-gray-800 ${getPercentColor(valuation.analyst_upside)}`}>
          <Target className="w-3 h-3" />
          목표가 {formatPercent(valuation.analyst_upside)}
        </span>
      )}
    </div>
  );
}

// Analyst ratings section
function AnalystRatingsSection({ ratings }: { ratings: AnalystRatings }) {
  const total = ratings.buy + ratings.hold + ratings.sell;
  if (total === 0) return null;

  const buyPercent = (ratings.buy / total) * 100;
  const holdPercent = (ratings.hold / total) * 100;
  const sellPercent = (ratings.sell / total) * 100;

  return (
    <div className="space-y-1">
      <div className="flex h-2 rounded-full overflow-hidden bg-gray-100 dark:bg-gray-700">
        {buyPercent > 0 && (
          <div className="bg-green-500" style={{ width: `${buyPercent}%` }} />
        )}
        {holdPercent > 0 && (
          <div className="bg-yellow-500" style={{ width: `${holdPercent}%` }} />
        )}
        {sellPercent > 0 && (
          <div className="bg-red-500" style={{ width: `${sellPercent}%` }} />
        )}
      </div>
      <div className="flex justify-between text-xs text-gray-500 dark:text-gray-400">
        <span className="text-green-600 dark:text-green-400">Buy {ratings.buy}</span>
        <span className="text-yellow-600 dark:text-yellow-400">Hold {ratings.hold}</span>
        <span className="text-red-600 dark:text-red-400">Sell {ratings.sell}</span>
      </div>
    </div>
  );
}

export default function MarketDataBadge({ data, compact = false }: MarketDataBadgeProps) {
  const hasData = data.price_position || data.valuation || data.analyst_ratings;

  if (!hasData) {
    return null;
  }

  if (compact) {
    // Compact view: just key metrics inline
    return (
      <div className="flex flex-wrap gap-2 text-xs">
        {data.price_position?.distance_from_52w_high !== undefined && (
          <span className={`px-2 py-0.5 rounded bg-gray-100 dark:bg-gray-800 ${getPercentColor(data.price_position.distance_from_52w_high)}`}>
            52주고가 {formatPercent(data.price_position.distance_from_52w_high)}
          </span>
        )}
        {data.valuation?.pe_ratio !== undefined && data.valuation?.pe_ratio !== null && (
          <span className="px-2 py-0.5 rounded bg-gray-100 dark:bg-gray-800 text-gray-700 dark:text-gray-300">
            PER {data.valuation.pe_ratio.toFixed(1)}x
          </span>
        )}
        {data.valuation?.analyst_upside !== undefined && data.valuation?.analyst_upside !== null && (
          <span className={`px-2 py-0.5 rounded bg-gray-100 dark:bg-gray-800 ${getPercentColor(data.valuation.analyst_upside)}`}>
            목표가 {formatPercent(data.valuation.analyst_upside)}
          </span>
        )}
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {/* Price Position */}
      {data.price_position && (
        <PricePositionSection position={data.price_position} />
      )}

      {/* Valuation */}
      {data.valuation && (
        <ValuationSection valuation={data.valuation} />
      )}

      {/* Analyst Ratings */}
      {data.analyst_ratings && (
        <AnalystRatingsSection ratings={data.analyst_ratings} />
      )}
    </div>
  );
}
