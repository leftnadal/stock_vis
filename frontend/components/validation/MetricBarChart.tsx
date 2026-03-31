'use client';

import {
  ComposedChart, Line, Area, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer, Label,
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

/** 마지막 dot에 라벨 표시하는 커스텀 dot */
function LastPointLabel({ cx, cy, index, data, label, color }: any) {
  if (index !== data.length - 1) return null;
  return (
    <text x={cx + 6} y={cy + 3} fontSize={9} fill={color} fontWeight={label === '이 기업' ? 600 : 400}>
      {label}
    </text>
  );
}

interface Props {
  history: ChartDataPoint[];
  unit: string;
  higherIsBetter: boolean;
  rank?: number | null;
  total?: number | null;
}

export default function MetricBarChart({ history, unit, rank, total }: Props) {
  if (history.length === 0) return null;

  const chartData = history.map((h) => ({
    year: h.fiscal_year,
    company: h.company_value,
    median: h.peer_median,
    p25: h.peer_p25,
    p75: h.peer_p75,
  }));

  return (
    <div className="w-full h-48 relative">
      {rank && total && (
        <div className="absolute top-0 right-0 z-10 text-[10px] font-medium text-gray-500 dark:text-gray-400 bg-white/80 dark:bg-gray-800/80 px-1.5 py-0.5 rounded">
          {rank}위/{total}
        </div>
      )}
      <ResponsiveContainer width="100%" height="100%">
        <ComposedChart data={chartData} margin={{ top: 5, right: 50, left: 0, bottom: 5 }}>
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

          {/* 1) P75 Area — 하늘색으로 0~p75 전체 채움 */}
          <Area
            dataKey="p75"
            stroke="#93C5FD"
            strokeWidth={0.5}
            strokeDasharray="3 3"
            fill="#DBEAFE"
            fillOpacity={0.5}
            isAnimationActive={false}
            dot={false}
            activeDot={false}
            connectNulls
            legendType="none"
          />
          {/* 2) P25 Area — 흰색으로 0~p25 덮어씌움 → p25~p75만 하늘색 */}
          <Area
            dataKey="p25"
            stroke="#93C5FD"
            strokeWidth={0.5}
            strokeDasharray="3 3"
            fill="#FFFFFF"
            fillOpacity={1}
            isAnimationActive={false}
            dot={false}
            activeDot={false}
            connectNulls
            legendType="none"
          />

          {/* Peer 중앙값 (실선) + 끝 라벨 */}
          <Line
            dataKey="median"
            stroke="#6B7280"
            strokeWidth={1.5}
            dot={(props: any) => {
              const { key, ...rest } = props;
              return (
                <g key={key ?? rest.index}>
                  <circle cx={rest.cx} cy={rest.cy} r={2.5} fill="#6B7280" />
                  <LastPointLabel {...rest} data={chartData} label="Median" color="#6B7280" />
                </g>
              );
            }}
            activeDot={false}
            connectNulls
            legendType="none"
          />

          {/* 이 기업 (실선, 파란색) + 끝 라벨 */}
          <Line
            dataKey="company"
            stroke="#3B82F6"
            strokeWidth={2}
            dot={(props: any) => {
              const { key, ...rest } = props;
              return (
                <g key={key ?? rest.index}>
                  <circle cx={rest.cx} cy={rest.cy} r={4} fill="#3B82F6" stroke="#fff" strokeWidth={2} />
                  <LastPointLabel {...rest} data={chartData} label="이 기업" color="#3B82F6" />
                </g>
              );
            }}
            activeDot={{ r: 6 }}
            connectNulls
            legendType="none"
          />
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  );
}
