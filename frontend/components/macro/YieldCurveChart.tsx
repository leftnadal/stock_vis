'use client';

import React from 'react';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  ReferenceLine,
} from 'recharts';
import { Info, AlertOctagon, CheckCircle, Minus, TrendingUp } from 'lucide-react';
import type { InterestRatesDashboard, YieldCurveDataPoint } from '@/types/macro';
import { EDUCATIONAL_CONTENT } from '@/constants/education';

interface YieldCurveChartProps {
  data: InterestRatesDashboard;
  showEducation?: boolean;
}

export default function YieldCurveChart({ data, showEducation = true }: YieldCurveChartProps) {
  const { yield_curve_data, yield_curve_status, yield_spread, fed_funds_rate } = data;

  // 상태별 아이콘 및 색상
  const getStatusIcon = () => {
    switch (yield_spread.status) {
      case 'inverted':
        return <AlertOctagon className="w-5 h-5 text-red-500" />;
      case 'flattening':
        return <Minus className="w-5 h-5 text-amber-500" />;
      case 'normal':
        return <CheckCircle className="w-5 h-5 text-green-500" />;
      case 'steep':
        return <TrendingUp className="w-5 h-5 text-blue-500" />;
      default:
        return <Info className="w-5 h-5 text-gray-500" />;
    }
  };

  const statusColors: Record<string, { line: string; bg: string }> = {
    inverted: { line: '#DC2626', bg: 'bg-red-50 dark:bg-red-900/20' },
    flattening: { line: '#F59E0B', bg: 'bg-amber-50 dark:bg-amber-900/20' },
    normal: { line: '#16A34A', bg: 'bg-green-50 dark:bg-green-900/20' },
    steep: { line: '#2563EB', bg: 'bg-blue-50 dark:bg-blue-900/20' },
  };

  const currentColors = statusColors[yield_spread.status] || statusColors.normal;

  return (
    <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700 p-6">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <div>
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
            수익률 곡선
          </h3>
          <p className="text-sm text-gray-500 dark:text-gray-400">
            미국 국채 만기별 금리
          </p>
        </div>
        {showEducation && (
          <button
            className="p-2 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700"
            title="자세히 알아보기"
          >
            <Info className="w-5 h-5" />
          </button>
        )}
      </div>

      {/* Status Banner */}
      <div className={`${currentColors.bg} rounded-lg p-4 mb-4`}>
        <div className="flex items-center gap-3">
          {getStatusIcon()}
          <div>
            <span className="font-semibold text-gray-900 dark:text-white">
              {yield_curve_status.label}
            </span>
            <span className="text-gray-600 dark:text-gray-400 ml-2">
              (스프레드: {yield_spread.spread?.toFixed(2) ?? 'N/A'}%p)
            </span>
          </div>
        </div>
        <p className="mt-2 text-sm text-gray-600 dark:text-gray-400">
          {yield_curve_status.message}
        </p>
      </div>

      {/* Chart */}
      <div className="h-64 mt-4">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart
            data={yield_curve_data}
            margin={{ top: 10, right: 30, left: 0, bottom: 0 }}
          >
            <CartesianGrid strokeDasharray="3 3" stroke="#374151" opacity={0.2} />
            <XAxis
              dataKey="maturity"
              tick={{ fill: '#9CA3AF', fontSize: 12 }}
              axisLine={{ stroke: '#4B5563' }}
            />
            <YAxis
              tickFormatter={(value) => `${value}%`}
              tick={{ fill: '#9CA3AF', fontSize: 12 }}
              axisLine={{ stroke: '#4B5563' }}
              domain={['auto', 'auto']}
            />
            <Tooltip
              contentStyle={{
                backgroundColor: '#1F2937',
                border: 'none',
                borderRadius: '8px',
                color: '#F9FAFB',
              }}
              formatter={(value: number) => [`${value.toFixed(2)}%`, '금리']}
              labelFormatter={(label) => `만기: ${label}`}
            />
            {/* Fed Funds Rate reference line */}
            {fed_funds_rate && (
              <ReferenceLine
                y={fed_funds_rate}
                stroke="#9333EA"
                strokeDasharray="5 5"
                label={{
                  value: `기준금리 ${fed_funds_rate}%`,
                  position: 'right',
                  fill: '#9333EA',
                  fontSize: 10,
                }}
              />
            )}
            <Line
              type="monotone"
              dataKey="rate"
              stroke={currentColors.line}
              strokeWidth={3}
              dot={{ fill: currentColors.line, strokeWidth: 2, r: 4 }}
              activeDot={{ r: 6, fill: currentColors.line }}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>

      {/* Key Rates Summary */}
      <div className="grid grid-cols-3 gap-4 mt-4 pt-4 border-t border-gray-200 dark:border-gray-700">
        <div className="text-center">
          <p className="text-xs text-gray-500 dark:text-gray-400">기준금리</p>
          <p className="text-lg font-semibold text-purple-600">
            {fed_funds_rate?.toFixed(2) ?? 'N/A'}%
          </p>
        </div>
        <div className="text-center">
          <p className="text-xs text-gray-500 dark:text-gray-400">2년물</p>
          <p className="text-lg font-semibold text-gray-900 dark:text-white">
            {data.treasury_2y?.toFixed(2) ?? 'N/A'}%
          </p>
        </div>
        <div className="text-center">
          <p className="text-xs text-gray-500 dark:text-gray-400">10년물</p>
          <p className="text-lg font-semibold text-gray-900 dark:text-white">
            {data.treasury_10y?.toFixed(2) ?? 'N/A'}%
          </p>
        </div>
      </div>

      {/* Historical Note */}
      {yield_curve_status.historical_note && (
        <div className="mt-4 p-3 bg-gray-50 dark:bg-gray-700 rounded-lg">
          <p className="text-xs text-gray-500 dark:text-gray-400">
            <span className="font-medium">역사적 관점:</span>{' '}
            {yield_curve_status.historical_note}
          </p>
        </div>
      )}

      {/* Education Section */}
      {showEducation && (
        <div className="mt-4 pt-4 border-t border-gray-200 dark:border-gray-700">
          <details className="group">
            <summary className="flex items-center justify-between cursor-pointer text-sm text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white">
              <span className="font-medium">수익률 곡선이란?</span>
              <span className="ml-2 transform group-open:rotate-180 transition-transform">
                ▼
              </span>
            </summary>
            <div className="mt-3 text-sm text-gray-600 dark:text-gray-400">
              <p>{EDUCATIONAL_CONTENT.yieldCurve.levels.beginner}</p>
            </div>
          </details>
        </div>
      )}
    </div>
  );
}
