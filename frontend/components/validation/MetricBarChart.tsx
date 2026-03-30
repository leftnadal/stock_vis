'use client';

import {
  ComposedChart, Bar, XAxis, YAxis, CartesianGrid,
  Tooltip, Legend, Cell, ResponsiveContainer,
  Scatter, ErrorBar,
} from 'recharts';
import type { ChartDataPoint } from '@/types/validation';

function getSignalColor(companyValue: number | null, median: number | null, higherIsBetter: boolean): string {
  if (companyValue === null || median === null) return '#9CA3AF'; // gray
  const diff = higherIsBetter ? companyValue - median : median - companyValue;
  const ratio = median !== 0 ? diff / Math.abs(median) : 0;
  if (ratio > 0.15) return '#10B981'; // green
  if (ratio > -0.15) return '#F59E0B'; // yellow
  return '#EF4444'; // red
}

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

export default function MetricBarChart({ history, unit, higherIsBetter }: Props) {
  if (history.length === 0) return null;

  const chartData = history.map((h) => ({
    year: h.fiscal_year,
    company: h.company_value,
    median: h.peer_median,
    p25: h.peer_p25,
    p75: h.peer_p75,
    // ErrorBar용: p25~p75 범위
    errorLow: h.peer_median !== null && h.peer_p25 !== null ? h.peer_median - h.peer_p25 : 0,
    errorHigh: h.peer_median !== null && h.peer_p75 !== null ? h.peer_p75 - h.peer_median : 0,
  }));

  return (
    <div className="w-full h-48">
      <ResponsiveContainer width="100%" height="100%">
        <ComposedChart data={chartData} margin={{ top: 5, right: 10, left: 0, bottom: 5 }}>
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
              };
              return labels[value] || value;
            }}
          />

          {/* 이 기업 Bar (연도별 색상) */}
          <Bar dataKey="company" name="company" barSize={24} radius={[2, 2, 0, 0]}>
            {chartData.map((d, idx) => (
              <Cell key={idx} fill={getSignalColor(d.company, d.median, higherIsBetter)} />
            ))}
          </Bar>

          {/* Peer 중앙값 Scatter (dash 마커) */}
          <Scatter
            dataKey="median"
            name="median"
            fill="#6B7280"
            shape={(props: any) => {
              const { cx, cy } = props;
              if (!cx || !cy) return <rect width={0} height={0} />;
              return (
                <line x1={cx - 12} y1={cy} x2={cx + 12} y2={cy} stroke="#6B7280" strokeWidth={2} />
              );
            }}
          >
            <ErrorBar
              dataKey="errorHigh"
              direction="y"
              width={8}
              stroke="#9CA3AF"
              strokeWidth={1}
            />
          </Scatter>
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  );
}
