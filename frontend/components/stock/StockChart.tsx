'use client';

import { useState, useEffect } from 'react';
import {
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Area,
  AreaChart,
} from 'recharts';
import { stockService, ChartData } from '@/services/stock';
import { TrendingUp, TrendingDown } from 'lucide-react';
import { formatCurrency, formatVolume } from '@/utils/formatters';
import { isProfit, getProfitSign } from '@/utils/styling';

interface StockChartProps {
  symbol: string;
}

// 기간별 옵션 설정 (표시할 데이터 범위)
const PERIOD_OPTIONS = [
  { value: '5d', label: '5일', period: 'days', days: 7, chartType: 'daily' },      // 최근 7일 데이터
  { value: '1m', label: '1개월', period: '1m', days: 30, chartType: 'daily' },     // 최근 1개월
  { value: '3m', label: '3개월', period: '3m', days: 90, chartType: 'daily' },     // 최근 3개월
  { value: '1y', label: '1년', period: '1y', days: 365, chartType: 'daily' },      // 최근 1년
];

export default function StockChart({ symbol }: StockChartProps) {
  const [chartData, setChartData] = useState<ChartData[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedPeriod, setSelectedPeriod] = useState('1m'); // 기본값 1개월

  const currentOption = PERIOD_OPTIONS.find(opt => opt.value === selectedPeriod) || PERIOD_OPTIONS[1];

  useEffect(() => {
    loadChartData();
  }, [symbol, selectedPeriod]);

  const loadChartData = async () => {
    try {
      setLoading(true);
      setError(null);

      // days를 사용하는 경우와 period를 사용하는 경우 구분
      const periodParam = currentOption.period === 'days'
        ? `days=${currentOption.days}`
        : currentOption.period;

      const response = await stockService.getChartData(
        symbol.toUpperCase(),
        currentOption.chartType as 'daily' | 'weekly',
        periodParam
      );

      // Transform and sort data (과거 날짜부터 최신 날짜 순으로 정렬)
      const transformedData = response.data
        .map((item: any) => ({
          date: new Date(item.time).toLocaleDateString('ko-KR', {
            month: 'short',
            day: 'numeric'
          }),
          timestamp: new Date(item.time).getTime(),
          open_price: item.open,
          high_price: item.high,
          low_price: item.low,
          close_price: item.close,
          volume: item.volume,
        }))
        .sort((a, b) => a.timestamp - b.timestamp); // 오래된 날짜부터 정렬

      setChartData(transformedData);
    } catch (err) {
      console.error('Failed to load chart data:', err);
      setError('차트 데이터를 불러오는 중 오류가 발생했습니다.');
    } finally {
      setLoading(false);
    }
  };

  const CustomTooltip = ({ active, payload, label }: any) => {
    if (active && payload && payload[0]) {
      const data = payload[0].payload;
      return (
        <div className="bg-white dark:bg-gray-800 p-3 rounded-lg shadow-lg border border-gray-200 dark:border-gray-700">
          <p className="text-sm font-medium text-gray-900 dark:text-white mb-2">{label}</p>
          <div className="space-y-1 text-xs">
            <div className="flex justify-between gap-4">
              <span className="text-gray-500">시가:</span>
              <span className="font-medium">{formatCurrency(data.open_price)}</span>
            </div>
            <div className="flex justify-between gap-4">
              <span className="text-gray-500">고가:</span>
              <span className="font-medium">{formatCurrency(data.high_price)}</span>
            </div>
            <div className="flex justify-between gap-4">
              <span className="text-gray-500">저가:</span>
              <span className="font-medium">{formatCurrency(data.low_price)}</span>
            </div>
            <div className="flex justify-between gap-4">
              <span className="text-gray-500">종가:</span>
              <span className="font-medium text-blue-600">{formatCurrency(data.close_price)}</span>
            </div>
            <div className="flex justify-between gap-4">
              <span className="text-gray-500">거래량:</span>
              <span className="font-medium">{formatVolume(data.volume)}</span>
            </div>
          </div>
        </div>
      );
    }
    return null;
  };

  if (loading) {
    return (
      <div className="bg-white dark:bg-gray-800 rounded-lg p-6">
        <div className="animate-pulse">
          <div className="h-8 bg-gray-200 dark:bg-gray-700 rounded w-1/4 mb-4"></div>
          <div className="h-64 bg-gray-200 dark:bg-gray-700 rounded"></div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-white dark:bg-gray-800 rounded-lg p-6">
        <div className="text-center text-red-600 dark:text-red-400">
          <p>{error}</p>
          <button
            onClick={loadChartData}
            className="mt-4 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
          >
            다시 시도
          </button>
        </div>
      </div>
    );
  }

  // Calculate price change
  const firstPrice = chartData.length > 0 ? chartData[0].close_price : 0;
  const lastPrice = chartData.length > 0 ? chartData[chartData.length - 1].close_price : 0;
  const priceChange = lastPrice - firstPrice;
  const priceChangePercent = firstPrice > 0 ? (priceChange / firstPrice) * 100 : 0;
  const isPositive = isProfit(priceChange);

  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg p-6">
      {/* Chart Header */}
      <div className="flex justify-between items-start mb-4">
        <div>
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white">주가 차트</h3>
          <div className="flex items-center mt-2 space-x-4">
            <span className="text-2xl font-bold text-gray-900 dark:text-white">
              {formatCurrency(lastPrice)}
            </span>
            <div className={`flex items-center ${isPositive ? 'text-green-600' : 'text-red-600'}`}>
              {isPositive ? <TrendingUp className="h-4 w-4 mr-1" /> : <TrendingDown className="h-4 w-4 mr-1" />}
              <span className="font-medium">
                {getProfitSign(priceChange)}{formatCurrency(priceChange)} ({priceChangePercent.toFixed(2)}%)
              </span>
            </div>
          </div>
        </div>

        {/* Period Selector */}
        <div className="flex space-x-1">
          {PERIOD_OPTIONS.map((option) => (
            <button
              key={option.value}
              onClick={() => setSelectedPeriod(option.value)}
              className={`px-3 py-1 text-xs rounded transition-colors ${
                selectedPeriod === option.value
                  ? 'bg-blue-100 text-blue-700 dark:bg-blue-900 dark:text-blue-300'
                  : 'bg-gray-100 text-gray-700 hover:bg-gray-200 dark:bg-gray-700 dark:text-gray-300 dark:hover:bg-gray-600'
              }`}
            >
              {option.label}
            </button>
          ))}
        </div>
      </div>

      {/* Chart */}
      <ResponsiveContainer width="100%" height={400}>
        <AreaChart data={chartData} margin={{ top: 10, right: 60, left: 10, bottom: 0 }}>
          <defs>
            <linearGradient id="colorPrice" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor={isPositive ? '#10B981' : '#EF4444'} stopOpacity={0.3} />
              <stop offset="95%" stopColor={isPositive ? '#10B981' : '#EF4444'} stopOpacity={0} />
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="3 3" stroke="#E5E7EB" />
          <XAxis
            dataKey="date"
            tick={{ fontSize: 12 }}
            stroke="#9CA3AF"
          />
          <YAxis
            orientation="right"
            domain={['dataMin - 5', 'dataMax + 5']}
            tick={{ fontSize: 12 }}
            stroke="#9CA3AF"
            tickFormatter={(value) => `$${value}`}
          />
          <Tooltip content={<CustomTooltip />} />
          <Area
            type="monotone"
            dataKey="close_price"
            stroke={isPositive ? '#10B981' : '#EF4444'}
            strokeWidth={2}
            fill="url(#colorPrice)"
          />
        </AreaChart>
      </ResponsiveContainer>

      {/* Volume Bar (Optional) */}
      <div className="mt-4 pt-4 border-t border-gray-200 dark:border-gray-700">
        <p className="text-sm text-gray-500 dark:text-gray-400 mb-2">거래량</p>
        <ResponsiveContainer width="100%" height={100}>
          <AreaChart data={chartData} margin={{ top: 0, right: 60, left: 10, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#E5E7EB" />
            <XAxis dataKey="date" hide />
            <YAxis orientation="right" hide />
            <Tooltip
              content={({ active, payload }: any) => {
                if (active && payload && payload[0]) {
                  return (
                    <div className="bg-white dark:bg-gray-800 p-2 rounded shadow-lg border border-gray-200 dark:border-gray-700">
                      <p className="text-xs">
                        거래량: {formatVolume(payload[0].value)}
                      </p>
                    </div>
                  );
                }
                return null;
              }}
            />
            <Area
              type="monotone"
              dataKey="volume"
              stroke="#3B82F6"
              fill="#3B82F6"
              fillOpacity={0.3}
            />
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}