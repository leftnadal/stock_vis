// Sentiment chart component using Recharts

'use client';

import React from 'react';
import {
  ComposedChart,
  Line,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ReferenceLine,
  ResponsiveContainer,
} from 'recharts';
import { format, parseISO } from 'date-fns';
import { ko } from 'date-fns/locale';
import { AlertCircle, TrendingUp } from 'lucide-react';
import { useStockSentiment } from '@/hooks/useNews';
import { StockSentiment } from '@/types/news';

export interface SentimentChartProps {
  symbol: string;
  days?: number;
}

export default function SentimentChart({ symbol, days = 7 }: SentimentChartProps) {
  const { data, isLoading, error } = useStockSentiment(symbol, days);

  // Loading State
  if (isLoading) {
    return (
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 p-6">
        <div className="animate-pulse space-y-4">
          <div className="h-6 bg-gray-200 dark:bg-gray-700 rounded w-48"></div>
          <div className="h-64 bg-gray-200 dark:bg-gray-700 rounded"></div>
        </div>
      </div>
    );
  }

  // Error State
  if (error) {
    return (
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 p-6">
        <div className="text-center">
          <AlertCircle className="w-12 h-12 text-red-500 mx-auto mb-3" />
          <p className="text-red-600 dark:text-red-400">감성 분석 데이터를 불러올 수 없습니다</p>
        </div>
      </div>
    );
  }

  // No Data State
  if (!data || data.history.length === 0) {
    return (
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 p-6">
        <div className="text-center py-8">
          <TrendingUp className="w-12 h-12 text-gray-400 mx-auto mb-3" />
          <p className="text-gray-600 dark:text-gray-400">감성 분석 데이터가 없습니다</p>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 p-6">
      {/* Header: Summary Stats */}
      <div className="mb-6">
        <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
          감성 분석
        </h3>
        <SentimentSummary sentiment={data} />
      </div>

      {/* Chart */}
      <div className="w-full h-80">
        <ResponsiveContainer width="100%" height="100%">
          <ComposedChart
            data={data.history}
            margin={{ top: 20, right: 30, left: 20, bottom: 20 }}
          >
            <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />

            {/* X Axis: Date */}
            <XAxis
              dataKey="date"
              tickFormatter={(date) => format(parseISO(date), 'MM.dd', { locale: ko })}
              stroke="#6b7280"
              style={{ fontSize: '12px' }}
            />

            {/* Y Axis (Left): Sentiment Score */}
            <YAxis
              yAxisId="left"
              domain={[-100, 100]}
              stroke="#6b7280"
              style={{ fontSize: '12px' }}
              label={{
                value: '감성 점수',
                angle: -90,
                position: 'insideLeft',
                style: { fontSize: '12px', fill: '#6b7280' },
              }}
            />

            {/* Y Axis (Right): News Count */}
            <YAxis
              yAxisId="right"
              orientation="right"
              stroke="#6b7280"
              style={{ fontSize: '12px' }}
              label={{
                value: '뉴스 수',
                angle: 90,
                position: 'insideRight',
                style: { fontSize: '12px', fill: '#6b7280' },
              }}
            />

            {/* Tooltip */}
            <Tooltip content={<CustomTooltip />} />

            {/* Legend */}
            <Legend />

            {/* Reference Line at 0 */}
            <ReferenceLine
              yAxisId="left"
              y={0}
              stroke="#9ca3af"
              strokeDasharray="3 3"
              strokeWidth={1}
            />

            {/* Bar: News Count */}
            <Bar
              yAxisId="right"
              dataKey="news_count"
              fill="#3b82f6"
              opacity={0.3}
              name="뉴스 수"
              radius={[4, 4, 0, 0]}
            />

            {/* Line: Sentiment Score */}
            <Line
              yAxisId="left"
              type="monotone"
              dataKey="avg_sentiment"
              stroke="#10b981"
              strokeWidth={2}
              dot={{ r: 4 }}
              name="감성 점수"
            />
          </ComposedChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}

// Sentiment Summary Component
function SentimentSummary({ sentiment }: { sentiment: StockSentiment }) {
  const getSentimentColor = (score: number | null) => {
    if (score === null) return 'text-gray-600 dark:text-gray-400';
    if (score >= 0.1) return 'text-green-600 dark:text-green-400';
    if (score <= -0.1) return 'text-red-600 dark:text-red-400';
    return 'text-gray-600 dark:text-gray-400';
  };

  return (
    <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
      <div className="bg-gray-50 dark:bg-gray-700/50 rounded-lg p-3">
        <p className="text-xs text-gray-500 dark:text-gray-400 mb-1">평균 감성</p>
        <p className={`text-lg font-bold ${getSentimentColor(sentiment.avg_sentiment)}`}>
          {sentiment.avg_sentiment !== null
            ? (sentiment.avg_sentiment * 100).toFixed(1)
            : '-'}
        </p>
      </div>

      <div className="bg-gray-50 dark:bg-gray-700/50 rounded-lg p-3">
        <p className="text-xs text-gray-500 dark:text-gray-400 mb-1">긍정</p>
        <p className="text-lg font-bold text-green-600 dark:text-green-400">
          {(sentiment.positive_ratio * 100).toFixed(0)}%
        </p>
      </div>

      <div className="bg-gray-50 dark:bg-gray-700/50 rounded-lg p-3">
        <p className="text-xs text-gray-500 dark:text-gray-400 mb-1">부정</p>
        <p className="text-lg font-bold text-red-600 dark:text-red-400">
          {(sentiment.negative_ratio * 100).toFixed(0)}%
        </p>
      </div>

      <div className="bg-gray-50 dark:bg-gray-700/50 rounded-lg p-3">
        <p className="text-xs text-gray-500 dark:text-gray-400 mb-1">총 뉴스</p>
        <p className="text-lg font-bold text-gray-900 dark:text-white">
          {sentiment.total_articles}
        </p>
      </div>
    </div>
  );
}

// Custom Tooltip Component
function CustomTooltip({ active, payload }: any) {
  if (!active || !payload || payload.length === 0) return null;

  const data = payload[0].payload;

  return (
    <div className="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg shadow-lg p-3">
      <p className="text-sm font-semibold text-gray-900 dark:text-white mb-2">
        {format(parseISO(data.date), 'yyyy년 MM월 dd일', { locale: ko })}
      </p>

      <div className="space-y-1 text-sm">
        <div className="flex justify-between gap-4">
          <span className="text-gray-600 dark:text-gray-400">감성 점수:</span>
          <span className="font-medium text-green-600 dark:text-green-400">
            {data.avg_sentiment !== null ? data.avg_sentiment.toFixed(2) : '-'}
          </span>
        </div>

        <div className="flex justify-between gap-4">
          <span className="text-gray-600 dark:text-gray-400">뉴스 수:</span>
          <span className="font-medium text-blue-600 dark:text-blue-400">
            {data.news_count}
          </span>
        </div>

        <div className="border-t border-gray-200 dark:border-gray-700 my-2"></div>

        <div className="flex justify-between gap-4 text-xs">
          <span className="text-green-600 dark:text-green-400">긍정: {data.positive_count}</span>
          <span className="text-gray-600 dark:text-gray-400">중립: {data.neutral_count}</span>
          <span className="text-red-600 dark:text-red-400">부정: {data.negative_count}</span>
        </div>
      </div>
    </div>
  );
}
