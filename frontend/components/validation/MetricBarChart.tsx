'use client';

import {
  LineChart, Line, Area, XAxis, YAxis, CartesianGrid,
  Tooltip, Legend, ResponsiveContainer,
} from 'recharts';
import type { ChartDataPoint } from '@/types/validation';

function formatAxisValue(value: number, unit: string): string {
  switch (unit) {
    case 'ratio':
    case 'pct':
      return `${(value * 100).toFixed(0)}%`;
    case 'multiple':
      return `${value.toFixed(1)}x`;
    case 'days':
      return `${value.toFixed(0)}d`;
    case 'years':
      return `${value.toFixed(1)}y`;
    default:
      return value.toFixed(1);
  }
}

function formatTooltipValue(value: number | null, unit: string): string {
  if (value === null) return '-';
  switch (unit) {
    case 'ratio':
    case 'pct':
      return `${(value * 100).toFixed(2)}%`;
    case 'multiple':
      return `${value.toFixed(2)}x`;
    case 'days':
      return `${value.toFixed(0)}일`;
    case 'years':
      return `${value.toFixed(1)}년`;
    default:
      return value.toFixed(3);
  }
}

interface Props {
  history: ChartDataPoint[];
  unit: string;
  higherIsBetter: boolean;
}

export default function MetricBarChart({ history, unit }: Props) {
  if (history.length === 0) return null;

  const chartData = history.map((h) => ({
    year: h.fiscal_year,
    company: h.company_value,
    median: h.peer_median,
    p25: h.peer_p25,
    p75: h.peer_p75,
  }));

  return (
    <div className="w-full h-48">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={chartData} margin={{ top: 5, right: 10, left: 0, bottom: 5 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#E5E7EB" />
          <XAxis
            dataKey="year"
            tick={{ fontSize: 11, fill: '#6B7280' }}
            axisLine={{ stroke: '#D1D5DB' }}
          />
          <YAxis
            tick={{ fontSize: 11, fill: '#6B7280' }}
            tickFormatter={(v) => formatAxisValue(v, unit)}
            axisLine={{ stroke: '#D1D5DB' }}
            width={50}
          />
          <Tooltip
            content={({ active, payload }) => {
              if (!active || !payload?.length) return null;
              const d = payload[0]?.payload;
              return (
                <div className="bg-white dark:bg-gray-800 shadow-lg rounded-lg p-3 border border-gray-200 dark:border-gray-700 text-xs">
                  <p className="font-semibold text-gray-900 dark:text-white mb-1">{d.year} FY</p>
                  <p className="text-blue-600">이 기업: {formatTooltipValue(d.company, unit)}</p>
                  <p className="text-gray-500">Median: {formatTooltipValue(d.median, unit)}</p>
                  <p className="text-gray-400">P25: {formatTooltipValue(d.p25, unit)}</p>
                  <p className="text-gray-400">P75: {formatTooltipValue(d.p75, unit)}</p>
                </div>
              );
            }}
          />
          <Legend
            wrapperStyle={{ fontSize: 11 }}
            formatter={(value: string) => {
              const labels: Record<string, string> = {
                company: '이 기업',
                median: 'Peer 중앙값',
                p75: 'Peer P25~P75',
              };
              return labels[value] || value;
            }}
          />

          {/* Peer p25~p75 밴드 (Area) */}
          <Area
            dataKey="p75"
            name="p75"
            stroke="none"
            fill="#E5E7EB"
            fillOpacity={0.5}
            connectNulls
          />
          <Area
            dataKey="p25"
            stroke="none"
            fill="#FFFFFF"
            fillOpacity={1}
            legendType="none"
            connectNulls
          />

          {/* Peer 중앙값 (점선) */}
          <Line
            dataKey="median"
            name="median"
            stroke="#9CA3AF"
            strokeWidth={1.5}
            strokeDasharray="4 4"
            dot={{ r: 3, fill: '#9CA3AF' }}
            connectNulls
          />

          {/* 이 기업 (실선, 파란색) */}
          <Line
            dataKey="company"
            name="company"
            stroke="#3B82F6"
            strokeWidth={2}
            dot={{ r: 4, fill: '#3B82F6', strokeWidth: 2, stroke: '#fff' }}
            activeDot={{ r: 6 }}
            connectNulls
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
