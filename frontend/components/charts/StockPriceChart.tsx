'use client'

import React, { useMemo } from 'react'
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  Area,
  AreaChart,
} from 'recharts'
import { format, parseISO } from 'date-fns'

interface ChartDataPoint {
  time: string
  open: number
  high: number
  low: number
  close: number
  volume: number
}

interface StockPriceChartProps {
  data: ChartDataPoint[]
  symbol: string
  period?: string
  chartType?: 'line' | 'area' | 'candlestick'
  height?: number
}

export default function StockPriceChart({
  data,
  symbol,
  period = '1M',
  chartType = 'line',
  height = 400,
}: StockPriceChartProps) {
  // 데이터 포맷팅
  const formattedData = useMemo(() => {
    return data.map((item) => ({
      ...item,
      date: format(parseISO(item.time), 'MM/dd'),
      fullDate: format(parseISO(item.time), 'yyyy-MM-dd'),
    }))
  }, [data])

  // 최소/최대값 계산
  const priceRange = useMemo(() => {
    const prices = data.flatMap((d) => [d.open, d.high, d.low, d.close])
    const min = Math.min(...prices)
    const max = Math.max(...prices)
    const padding = (max - min) * 0.1
    return {
      min: Math.floor(min - padding),
      max: Math.ceil(max + padding),
    }
  }, [data])

  // 커스텀 툴팁
  const CustomTooltip = ({ active, payload, label }: any) => {
    if (active && payload && payload.length) {
      const data = payload[0].payload
      return (
        <div className="bg-white p-3 border rounded-lg shadow-lg">
          <p className="text-sm font-semibold text-gray-900">{data.fullDate}</p>
          <div className="mt-1 space-y-1">
            <p className="text-xs">
              <span className="text-gray-600">Open:</span>{' '}
              <span className="font-medium">${data.open.toFixed(2)}</span>
            </p>
            <p className="text-xs">
              <span className="text-gray-600">Close:</span>{' '}
              <span className="font-medium">${data.close.toFixed(2)}</span>
            </p>
            <p className="text-xs">
              <span className="text-gray-600">High:</span>{' '}
              <span className="font-medium text-green-600">${data.high.toFixed(2)}</span>
            </p>
            <p className="text-xs">
              <span className="text-gray-600">Low:</span>{' '}
              <span className="font-medium text-red-600">${data.low.toFixed(2)}</span>
            </p>
            <p className="text-xs">
              <span className="text-gray-600">Volume:</span>{' '}
              <span className="font-medium">{(data.volume / 1000000).toFixed(2)}M</span>
            </p>
          </div>
        </div>
      )
    }
    return null
  }

  // 가격 포맷터
  const priceFormatter = (value: number) => `$${value.toFixed(0)}`

  // 차트 타입에 따른 렌더링
  const renderChart = () => {
    switch (chartType) {
      case 'area':
        return (
          <AreaChart data={formattedData}>
            <defs>
              <linearGradient id="colorClose" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#3B82F6" stopOpacity={0.3} />
                <stop offset="95%" stopColor="#3B82F6" stopOpacity={0} />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke="#E5E7EB" />
            <XAxis
              dataKey="date"
              stroke="#6B7280"
              fontSize={12}
              tickLine={false}
              axisLine={false}
            />
            <YAxis
              domain={[priceRange.min, priceRange.max]}
              stroke="#6B7280"
              fontSize={12}
              tickLine={false}
              axisLine={false}
              tickFormatter={priceFormatter}
            />
            <Tooltip content={<CustomTooltip />} />
            <Area
              type="monotone"
              dataKey="close"
              stroke="#3B82F6"
              strokeWidth={2}
              fillOpacity={1}
              fill="url(#colorClose)"
            />
          </AreaChart>
        )

      case 'candlestick':
        // 캔들스틱 차트는 Recharts에서 직접 지원하지 않으므로 커스텀 구현 필요
        // 여기서는 High-Low-Open-Close를 표시하는 라인 차트로 대체
        return (
          <LineChart data={formattedData}>
            <CartesianGrid strokeDasharray="3 3" stroke="#E5E7EB" />
            <XAxis
              dataKey="date"
              stroke="#6B7280"
              fontSize={12}
              tickLine={false}
              axisLine={false}
            />
            <YAxis
              domain={[priceRange.min, priceRange.max]}
              stroke="#6B7280"
              fontSize={12}
              tickLine={false}
              axisLine={false}
              tickFormatter={priceFormatter}
            />
            <Tooltip content={<CustomTooltip />} />
            <Legend />
            <Line
              type="monotone"
              dataKey="high"
              stroke="#10B981"
              strokeWidth={1}
              dot={false}
              name="High"
            />
            <Line
              type="monotone"
              dataKey="low"
              stroke="#EF4444"
              strokeWidth={1}
              dot={false}
              name="Low"
            />
            <Line
              type="monotone"
              dataKey="open"
              stroke="#6B7280"
              strokeWidth={1}
              dot={false}
              strokeDasharray="3 3"
              name="Open"
            />
            <Line
              type="monotone"
              dataKey="close"
              stroke="#3B82F6"
              strokeWidth={2}
              dot={false}
              name="Close"
            />
          </LineChart>
        )

      case 'line':
      default:
        return (
          <LineChart data={formattedData}>
            <CartesianGrid strokeDasharray="3 3" stroke="#E5E7EB" />
            <XAxis
              dataKey="date"
              stroke="#6B7280"
              fontSize={12}
              tickLine={false}
              axisLine={false}
            />
            <YAxis
              domain={[priceRange.min, priceRange.max]}
              stroke="#6B7280"
              fontSize={12}
              tickLine={false}
              axisLine={false}
              tickFormatter={priceFormatter}
            />
            <Tooltip content={<CustomTooltip />} />
            <Line
              type="monotone"
              dataKey="close"
              stroke="#3B82F6"
              strokeWidth={2}
              dot={false}
              activeDot={{ r: 4 }}
            />
          </LineChart>
        )
    }
  }

  return (
    <div className="w-full bg-white rounded-lg shadow-sm p-4">
      <div className="flex justify-between items-center mb-4">
        <div>
          <h3 className="text-lg font-semibold text-gray-900">{symbol} 주가 차트</h3>
          <p className="text-sm text-gray-500">기간: {period}</p>
        </div>
        <div className="flex gap-2">
          <button
            className={`px-3 py-1 text-sm rounded ${
              chartType === 'line'
                ? 'bg-blue-500 text-white'
                : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
            }`}
          >
            라인
          </button>
          <button
            className={`px-3 py-1 text-sm rounded ${
              chartType === 'area'
                ? 'bg-blue-500 text-white'
                : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
            }`}
          >
            영역
          </button>
          <button
            className={`px-3 py-1 text-sm rounded ${
              chartType === 'candlestick'
                ? 'bg-blue-500 text-white'
                : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
            }`}
          >
            캔들
          </button>
        </div>
      </div>

      <ResponsiveContainer width="100%" height={height}>
        {renderChart()}
      </ResponsiveContainer>

      <div className="mt-4 flex justify-between text-xs text-gray-500">
        <div>
          최고가: ${Math.max(...data.map((d) => d.high)).toFixed(2)}
        </div>
        <div>
          최저가: ${Math.min(...data.map((d) => d.low)).toFixed(2)}
        </div>
        <div>
          평균 거래량: {(data.reduce((sum, d) => sum + d.volume, 0) / data.length / 1000000).toFixed(2)}M
        </div>
      </div>
    </div>
  )
}