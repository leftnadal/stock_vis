'use client';

import { format, parseISO } from 'date-fns';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts';
import { useMLTrend } from '@/hooks/useNewsPipeline';

interface ChartDataPoint {
  date: string;
  f1: number | null;
  precision: number | null;
  recall: number | null;
  model_version: string;
}

interface CustomTooltipProps {
  active?: boolean;
  payload?: Array<{ name: string; value: number; color: string }>;
  label?: string;
}

function CustomTooltip({ active, payload, label }: CustomTooltipProps) {
  if (!active || !payload || payload.length === 0) return null;
  return (
    <div className="bg-gray-900 border border-gray-700 rounded-lg px-3 py-2 text-xs">
      <p className="text-gray-400 mb-1">{label}</p>
      {payload.map((item) => (
        <p key={item.name} style={{ color: item.color }}>
          {item.name}: {item.value?.toFixed(3) ?? '--'}
        </p>
      ))}
    </div>
  );
}

interface MLTrendChartProps {
  enabled?: boolean;
}

export function MLTrendChart({ enabled = true }: MLTrendChartProps) {
  const { data, isLoading, error } = useMLTrend(12, enabled);

  if (isLoading) {
    return (
      <div className="bg-gray-800 rounded-xl border border-gray-700 p-5">
        <h3 className="font-semibold text-gray-200 mb-4">ML 성능 추이 (12주)</h3>
        <div className="h-52 bg-gray-700 rounded-lg animate-pulse" />
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="bg-gray-800 rounded-xl border border-gray-700 p-5">
        <h3 className="font-semibold text-gray-200 mb-2">ML 성능 추이 (12주)</h3>
        <p className="text-sm text-red-400">데이터 로드 실패</p>
      </div>
    );
  }

  if (data.history.length === 0) {
    return (
      <div className="bg-gray-800 rounded-xl border border-gray-700 p-5">
        <h3 className="font-semibold text-gray-200 mb-2">ML 성능 추이 (12주)</h3>
        <p className="text-sm text-gray-500">학습 이력 없음</p>
      </div>
    );
  }

  const chartData: ChartDataPoint[] = data.history.map((entry) => ({
    date: format(parseISO(entry.trained_at), 'M/dd'),
    f1: entry.f1_score,
    precision: entry.precision,
    recall: entry.recall,
    model_version: entry.model_version,
  }));

  return (
    <div className="bg-gray-800 rounded-xl border border-gray-700 p-5">
      <h3 className="font-semibold text-gray-200 mb-4">ML 성능 추이 (12주)</h3>
      <div className="h-[200px]">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={chartData} margin={{ top: 4, right: 8, left: -16, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
            <XAxis
              dataKey="date"
              tick={{ fill: '#6B7280', fontSize: 11 }}
              tickLine={false}
              axisLine={{ stroke: '#374151' }}
            />
            <YAxis
              domain={[0, 1]}
              tick={{ fill: '#6B7280', fontSize: 11 }}
              tickLine={false}
              axisLine={{ stroke: '#374151' }}
              tickFormatter={(v: number) => v.toFixed(2)}
            />
            <Tooltip content={<CustomTooltip />} />
            <Legend
              wrapperStyle={{ fontSize: '12px', color: '#9CA3AF' }}
            />
            <Line
              type="monotone"
              dataKey="f1"
              name="F1"
              stroke="#34D399"
              strokeWidth={2}
              dot={{ fill: '#34D399', r: 3 }}
              activeDot={{ r: 5 }}
            />
            <Line
              type="monotone"
              dataKey="precision"
              name="Precision"
              stroke="#60A5FA"
              strokeWidth={2}
              dot={{ fill: '#60A5FA', r: 3 }}
              activeDot={{ r: 5 }}
            />
            <Line
              type="monotone"
              dataKey="recall"
              name="Recall"
              stroke="#F59E0B"
              strokeWidth={2}
              dot={{ fill: '#F59E0B', r: 3 }}
              activeDot={{ r: 5 }}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
