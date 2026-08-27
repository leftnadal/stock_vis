'use client';

import React from 'react';
import { TrendingUp, TrendingDown, Minus, Target, Users, DollarSign, BarChart3 } from 'lucide-react';
import type { InflationDashboard } from '@/types/macro';

interface EconomicIndicatorsProps {
  data: InflationDashboard;
}

export default function EconomicIndicators({ data }: EconomicIndicatorsProps) {
  const { inflation, employment, gdp } = data;

  // 연준 목표 대비 인플레이션 상태
  const getInflationStatus = (value: number | null, target: number) => {
    if (value === null) return { color: 'text-gray-500', icon: Minus, label: 'N/A' };
    if (value > target + 1) return { color: 'text-red-500', icon: TrendingUp, label: '목표 초과' };
    if (value > target) return { color: 'text-amber-500', icon: TrendingUp, label: '목표 상회' };
    if (value >= target - 0.5) return { color: 'text-green-500', icon: Target, label: '목표 근접' };
    return { color: 'text-blue-500', icon: TrendingDown, label: '목표 하회' };
  };

  const cpiStatus = getInflationStatus(inflation.cpi_yoy, inflation.fed_target);

  // 고용 상태
  const getEmploymentStatus = (rate: number | null) => {
    if (rate === null) return { color: 'text-gray-500', label: 'N/A' };
    if (rate < 4) return { color: 'text-green-500', label: '완전 고용' };
    if (rate < 5) return { color: 'text-emerald-500', label: '양호' };
    if (rate < 6) return { color: 'text-amber-500', label: '주의' };
    return { color: 'text-red-500', label: '우려' };
  };

  const employmentStatus = getEmploymentStatus(employment.unemployment_rate);

  return (
    <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700 p-6">
      <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-6">
        경제 지표 요약
      </h3>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* CPI */}
        <div className="bg-gray-50 dark:bg-gray-700 rounded-lg p-4">
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm text-gray-500 dark:text-gray-400">소비자물가 (CPI)</span>
            <DollarSign className={`w-4 h-4 ${cpiStatus.color}`} />
          </div>
          <div className="flex items-baseline gap-2">
            <span className={`text-2xl font-bold ${cpiStatus.color}`}>
              {inflation.cpi_yoy?.toFixed(1) ?? 'N/A'}%
            </span>
            <span className="text-xs text-gray-500 dark:text-gray-400">YoY</span>
          </div>
          <div className="mt-2 flex items-center gap-2">
            <div className="h-1 flex-1 bg-gray-200 dark:bg-gray-600 rounded-full overflow-hidden">
              <div
                className={`h-full ${
                  inflation.cpi_yoy && inflation.cpi_yoy > inflation.fed_target
                    ? 'bg-red-500'
                    : 'bg-green-500'
                }`}
                style={{
                  width: `${Math.min((inflation.cpi_yoy || 0) / 6 * 100, 100)}%`
                }}
              />
            </div>
            <span className="text-xs text-gray-500 dark:text-gray-400">
              목표 {inflation.fed_target}%
            </span>
          </div>
        </div>

        {/* Core CPI */}
        <div className="bg-gray-50 dark:bg-gray-700 rounded-lg p-4">
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm text-gray-500 dark:text-gray-400">근원물가 (Core CPI)</span>
            <BarChart3 className="w-4 h-4 text-blue-500" />
          </div>
          <div className="flex items-baseline gap-2">
            <span className="text-2xl font-bold text-gray-900 dark:text-white">
              {inflation.core_cpi_yoy?.toFixed(1) ?? 'N/A'}%
            </span>
            <span className="text-xs text-gray-500 dark:text-gray-400">YoY</span>
          </div>
          <p className="mt-2 text-xs text-gray-500 dark:text-gray-400">
            식품/에너지 제외
          </p>
        </div>

        {/* Unemployment */}
        <div className="bg-gray-50 dark:bg-gray-700 rounded-lg p-4">
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm text-gray-500 dark:text-gray-400">실업률</span>
            <Users className={`w-4 h-4 ${employmentStatus.color}`} />
          </div>
          <div className="flex items-baseline gap-2">
            <span className={`text-2xl font-bold ${employmentStatus.color}`}>
              {employment.unemployment_rate?.toFixed(1) ?? 'N/A'}%
            </span>
          </div>
          <div className="mt-2 flex items-center gap-1">
            <span
              className={`text-xs px-2 py-0.5 rounded-full ${
                employmentStatus.color === 'text-green-500'
                  ? 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400'
                  : employmentStatus.color === 'text-amber-500'
                  ? 'bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400'
                  : 'bg-gray-100 text-gray-700 dark:bg-gray-600 dark:text-gray-300'
              }`}
            >
              {employmentStatus.label}
            </span>
          </div>
        </div>

        {/* NFP */}
        <div className="bg-gray-50 dark:bg-gray-700 rounded-lg p-4">
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm text-gray-500 dark:text-gray-400">비농업 고용 (NFP)</span>
            {employment.nfp_change && employment.nfp_change > 0 ? (
              <TrendingUp className="w-4 h-4 text-green-500" />
            ) : (
              <TrendingDown className="w-4 h-4 text-red-500" />
            )}
          </div>
          <div className="flex items-baseline gap-2">
            <span
              className={`text-2xl font-bold ${
                employment.nfp_change && employment.nfp_change > 0
                  ? 'text-green-500'
                  : 'text-red-500'
              }`}
            >
              {employment.nfp_change
                ? `${employment.nfp_change > 0 ? '+' : ''}${(employment.nfp_change / 1000).toFixed(0)}K`
                : 'N/A'}
            </span>
          </div>
          <p className="mt-2 text-xs text-gray-500 dark:text-gray-400">
            전월 대비 변화
          </p>
        </div>
      </div>

      {/* GDP Section */}
      {gdp && (
        <div className="mt-6 pt-6 border-t border-gray-200 dark:border-gray-700">
          <div className="flex items-center justify-between">
            <div>
              <h4 className="text-sm font-medium text-gray-700 dark:text-gray-300">
                GDP 성장률 (연율화)
              </h4>
              <p className="text-xs text-gray-500 dark:text-gray-400">
                {gdp.date}
              </p>
            </div>
            <div className="text-right">
              <span
                className={`text-3xl font-bold ${
                  gdp.annualized_growth >= 0 ? 'text-green-500' : 'text-red-500'
                }`}
              >
                {gdp.annualized_growth > 0 ? '+' : ''}
                {gdp.annualized_growth.toFixed(1)}%
              </span>
              <p className="text-xs text-gray-500 dark:text-gray-400">
                QoQ: {gdp.qoq_growth > 0 ? '+' : ''}{gdp.qoq_growth.toFixed(2)}%
              </p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
