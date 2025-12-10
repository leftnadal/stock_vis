'use client';

import React from 'react';
import { TrendingUp, TrendingDown, Globe, DollarSign, Droplets, Gem } from 'lucide-react';
import type { GlobalMarketsDashboard, IndexData } from '@/types/macro';

interface GlobalMarketsCardProps {
  data: GlobalMarketsDashboard;
}

export default function GlobalMarketsCard({ data }: GlobalMarketsCardProps) {
  const { indices, global_indices, sectors, forex, commodities, dxy, vix } = data;

  const formatChange = (change: number | null | undefined) => {
    if (change === null || change === undefined) return 'N/A';
    const sign = change >= 0 ? '+' : '';
    return `${sign}${change.toFixed(2)}%`;
  };

  const getChangeColor = (change: number | null | undefined) => {
    if (change === null || change === undefined) return 'text-gray-500';
    return change >= 0 ? 'text-green-500' : 'text-red-500';
  };

  const IndexRow = ({ name, data: indexData }: { name: string; data: IndexData | null }) => {
    if (!indexData) return null;

    return (
      <div className="flex items-center justify-between py-2 border-b border-gray-100 dark:border-gray-700 last:border-0">
        <div>
          <span className="text-sm font-medium text-gray-900 dark:text-white">{name}</span>
          <p className="text-xs text-gray-500 dark:text-gray-400">
            {indexData.price?.toLocaleString()}
          </p>
        </div>
        <div className="flex items-center gap-1">
          {indexData.change_percent && indexData.change_percent >= 0 ? (
            <TrendingUp className="w-4 h-4 text-green-500" />
          ) : (
            <TrendingDown className="w-4 h-4 text-red-500" />
          )}
          <span className={`text-sm font-medium ${getChangeColor(indexData.change_percent)}`}>
            {formatChange(indexData.change_percent)}
          </span>
        </div>
      </div>
    );
  };

  return (
    <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700 p-6">
      <div className="flex items-center gap-2 mb-6">
        <Globe className="w-5 h-5 text-blue-500" />
        <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
          글로벌 시장 현황
        </h3>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        {/* US Indices */}
        <div>
          <h4 className="text-sm font-medium text-gray-500 dark:text-gray-400 mb-3 flex items-center gap-2">
            <span className="text-lg">🇺🇸</span> 미국 지수
          </h4>
          <div className="space-y-1">
            <IndexRow name="S&P 500" data={indices.sp500} />
            <IndexRow name="NASDAQ" data={indices.nasdaq} />
            <IndexRow name="Dow Jones" data={indices.dow} />
            <IndexRow name="Russell 2000" data={indices.russell2000} />
          </div>
        </div>

        {/* Global Indices */}
        <div>
          <h4 className="text-sm font-medium text-gray-500 dark:text-gray-400 mb-3 flex items-center gap-2">
            <Globe className="w-4 h-4" /> 글로벌 지수
          </h4>
          <div className="space-y-1">
            <IndexRow name="FTSE 100" data={global_indices.ftse} />
            <IndexRow name="DAX" data={global_indices.dax} />
            <IndexRow name="Nikkei 225" data={global_indices.nikkei} />
            <IndexRow name="Hang Seng" data={global_indices.hangseng} />
          </div>
        </div>

        {/* Forex & DXY */}
        <div>
          <h4 className="text-sm font-medium text-gray-500 dark:text-gray-400 mb-3 flex items-center gap-2">
            <DollarSign className="w-4 h-4" /> 환율
          </h4>
          <div className="space-y-1">
            {/* DXY */}
            {dxy && (
              <div className="flex items-center justify-between py-2 border-b border-gray-100 dark:border-gray-700 bg-blue-50 dark:bg-blue-900/20 rounded px-2 -mx-2">
                <div>
                  <span className="text-sm font-medium text-blue-700 dark:text-blue-300">
                    달러인덱스 (DXY)
                  </span>
                  <p className="text-xs text-blue-600 dark:text-blue-400">
                    {dxy.value?.toFixed(2)}
                  </p>
                </div>
                <span className={`text-sm font-medium ${getChangeColor(dxy.change_percent)}`}>
                  {formatChange(dxy.change_percent)}
                </span>
              </div>
            )}

            {/* Major Forex */}
            {Object.entries(forex).slice(0, 3).map(([symbol, forexData]) => (
              <div key={symbol} className="flex items-center justify-between py-2 border-b border-gray-100 dark:border-gray-700 last:border-0">
                <div>
                  <span className="text-sm font-medium text-gray-900 dark:text-white">
                    {forexData.name}
                  </span>
                  <p className="text-xs text-gray-500 dark:text-gray-400">
                    {forexData.price?.toFixed(4)}
                  </p>
                </div>
                <span className={`text-sm font-medium ${getChangeColor(forexData.change_percent)}`}>
                  {formatChange(forexData.change_percent)}
                </span>
              </div>
            ))}
          </div>
        </div>

        {/* Commodities & VIX */}
        <div>
          <h4 className="text-sm font-medium text-gray-500 dark:text-gray-400 mb-3 flex items-center gap-2">
            <Gem className="w-4 h-4" /> 상품 & VIX
          </h4>
          <div className="space-y-1">
            {/* VIX */}
            {vix && (
              <div className={`flex items-center justify-between py-2 border-b border-gray-100 dark:border-gray-700 rounded px-2 -mx-2 ${
                vix.level === 'extreme_high' || vix.level === 'high'
                  ? 'bg-red-50 dark:bg-red-900/20'
                  : vix.level === 'low'
                  ? 'bg-blue-50 dark:bg-blue-900/20'
                  : 'bg-green-50 dark:bg-green-900/20'
              }`}>
                <div>
                  <span className="text-sm font-medium text-gray-900 dark:text-white">
                    VIX (변동성)
                  </span>
                  <p className={`text-xs ${
                    vix.level === 'extreme_high' || vix.level === 'high'
                      ? 'text-red-600 dark:text-red-400'
                      : 'text-gray-500 dark:text-gray-400'
                  }`}>
                    {vix.level === 'extreme_high' ? '극단적 공포' :
                     vix.level === 'high' ? '높은 변동성' :
                     vix.level === 'low' ? '낮은 변동성' : '정상'}
                  </p>
                </div>
                <span className={`text-lg font-bold ${
                  vix.level === 'extreme_high' || vix.level === 'high'
                    ? 'text-red-500'
                    : vix.level === 'low'
                    ? 'text-blue-500'
                    : 'text-green-500'
                }`}>
                  {vix.value?.toFixed(1)}
                </span>
              </div>
            )}

            {/* Commodities */}
            {Object.entries(commodities).slice(0, 3).map(([symbol, commodity]) => (
              <div key={symbol} className="flex items-center justify-between py-2 border-b border-gray-100 dark:border-gray-700 last:border-0">
                <div>
                  <span className="text-sm font-medium text-gray-900 dark:text-white">
                    {commodity.name}
                  </span>
                  <p className="text-xs text-gray-500 dark:text-gray-400">
                    ${commodity.price?.toFixed(2)}
                  </p>
                </div>
                <span className={`text-sm font-medium ${getChangeColor(commodity.change_percent)}`}>
                  {formatChange(commodity.change_percent)}
                </span>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Sector Performance */}
      {sectors.sectors && Object.keys(sectors.sectors).length > 0 && (
        <div className="mt-6 pt-6 border-t border-gray-200 dark:border-gray-700">
          <h4 className="text-sm font-medium text-gray-500 dark:text-gray-400 mb-3">
            섹터 성과 (오늘)
          </h4>
          <div className="flex flex-wrap gap-2">
            {Object.entries(sectors.sectors)
              .sort(([, a], [, b]) => (b.change_percent || 0) - (a.change_percent || 0))
              .map(([symbol, sector]) => (
                <div
                  key={symbol}
                  className={`px-3 py-1.5 rounded-full text-xs font-medium ${
                    sector.change_percent && sector.change_percent >= 0
                      ? 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400'
                      : 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400'
                  }`}
                >
                  {sector.name} {formatChange(sector.change_percent)}
                </div>
              ))}
          </div>
        </div>
      )}
    </div>
  );
}
