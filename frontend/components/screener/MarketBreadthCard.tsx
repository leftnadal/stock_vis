'use client';

import React, { useState } from 'react';
import { TrendingUp, TrendingDown, Minus, AlertCircle, ChevronDown, ChevronUp, Info } from 'lucide-react';
import type { MarketBreadthData } from '@/types/screener';

interface MarketBreadthCardProps {
  data: MarketBreadthData;
  isLoading?: boolean;
  error?: Error | null;
}

export default function MarketBreadthCard({ data, isLoading, error }: MarketBreadthCardProps) {
  const [showMethodology, setShowMethodology] = useState(false);

  if (isLoading) {
    return (
      <div className="rounded-xl border border-[#30363D] bg-[#161B22] p-6">
        <div className="animate-pulse">
          <div className="h-6 bg-[#21262D] rounded w-1/3 mb-6"></div>
          <div className="h-32 bg-[#21262D] rounded mb-4"></div>
          <div className="h-4 bg-[#21262D] rounded w-full"></div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="rounded-xl border border-[#30363D] bg-[#161B22] p-6">
        <div className="flex items-center gap-2 text-[#F85149]">
          <AlertCircle className="w-5 h-5" />
          <span className="text-sm">시장 폭 데이터를 불러올 수 없습니다</span>
        </div>
      </div>
    );
  }

  const {
    advancing_count,
    declining_count,
    advance_decline_ratio,
    breadth_signal,
    signal_interpretation,
    indices,
    methodology,
  } = data;

  // 게이지 각도 계산 (0-100 기준)
  const total = advancing_count + declining_count;
  const advancingPercent = total > 0 ? (advancing_count / total) * 100 : 50;
  const angle = (advancingPercent / 100) * 180 - 90;

  // 아이콘 선택
  const getIcon = () => {
    switch (breadth_signal) {
      case 'strong_bullish':
      case 'bullish':
        return <TrendingUp className="w-5 h-5" />;
      case 'strong_bearish':
      case 'bearish':
        return <TrendingDown className="w-5 h-5" />;
      default:
        return <Minus className="w-5 h-5" />;
    }
  };

  const color = signal_interpretation.color;
  const emoji = signal_interpretation.emoji;

  // 지수 색상
  const getChangeColor = (change: number | null) => {
    if (change === null) return 'text-[#8B949E]';
    if (change > 0) return 'text-[#3FB950]';
    if (change < 0) return 'text-[#F85149]';
    return 'text-[#8B949E]';
  };

  const formatChange = (change: number | null) => {
    if (change === null) return '-';
    return `${change > 0 ? '+' : ''}${change.toFixed(2)}%`;
  };

  return (
    <div className="rounded-xl border border-[#30363D] bg-[#161B22] p-6">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-semibold text-[#E6EDF3]">
          시장 폭 지표
        </h3>
        <div className="flex items-center gap-2">
          <span className="text-xs text-[#8B949E]">
            {data.date}
          </span>
          <button
            onClick={() => setShowMethodology(!showMethodology)}
            className="p-1 rounded hover:bg-[#21262D] text-[#8B949E] hover:text-[#E6EDF3] transition-colors"
            title="계산 방식 보기"
          >
            <Info className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* 주요 지수 표시 */}
      {indices && (
        <div className="grid grid-cols-3 gap-2 mb-4 p-3 bg-[#0D1117] rounded-lg">
          {Object.entries(indices).map(([key, index]) => (
            <div key={key} className="text-center">
              <div className="text-xs text-[#8B949E]">{index.name}</div>
              <div className={`text-sm font-semibold ${getChangeColor(index.change_pct)}`}>
                {formatChange(index.change_pct)}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Gauge */}
      <div className="flex flex-col items-center">
        {/* Semi-circle Gauge */}
        <div className="relative w-48 h-24 mb-4">
          <svg viewBox="0 0 200 100" className="w-full h-full">
            {/* Gradient background */}
            <defs>
              <linearGradient id="breadthGradient" x1="0%" y1="0%" x2="100%" y2="0%">
                <stop offset="0%" stopColor="#DC2626" />
                <stop offset="25%" stopColor="#F59E0B" />
                <stop offset="50%" stopColor="#6B7280" />
                <stop offset="75%" stopColor="#10B981" />
                <stop offset="100%" stopColor="#059669" />
              </linearGradient>
            </defs>

            {/* Background arc */}
            <path
              d="M 10 100 A 90 90 0 0 1 190 100"
              fill="none"
              stroke="url(#breadthGradient)"
              strokeWidth="16"
              strokeLinecap="round"
            />

            {/* Needle */}
            <g transform={`rotate(${angle}, 100, 100)`}>
              <line
                x1="100"
                y1="100"
                x2="100"
                y2="25"
                stroke={color}
                strokeWidth="4"
                strokeLinecap="round"
              />
              <circle cx="100" cy="100" r="8" fill={color} />
            </g>
          </svg>

          {/* Value display */}
          <div className="absolute bottom-0 left-1/2 transform -translate-x-1/2 text-center">
            <span className="text-3xl font-bold" style={{ color }}>
              {advancingPercent.toFixed(0)}%
            </span>
          </div>
        </div>

        {/* Labels */}
        <div className="flex justify-between w-full px-4 text-xs text-[#8B949E] mb-4">
          <span>약세</span>
          <span>강세</span>
        </div>

        {/* Counts */}
        <div className="flex items-center gap-4 mb-4">
          <div className="text-center">
            <div className="text-sm text-[#8B949E]">상승</div>
            <div className="text-2xl font-bold text-[#3FB950]">
              {advancing_count.toLocaleString()}
            </div>
          </div>
          <div className="text-[#30363D]">vs</div>
          <div className="text-center">
            <div className="text-sm text-[#8B949E]">하락</div>
            <div className="text-2xl font-bold text-[#F85149]">
              {declining_count.toLocaleString()}
            </div>
          </div>
        </div>

        {/* Ratio */}
        <div className="mb-4">
          <span className="text-xs text-[#8B949E]">A/D 비율: </span>
          <span className="text-sm font-semibold text-[#E6EDF3]">
            {Number(advance_decline_ratio).toFixed(2)}
          </span>
        </div>

        {/* Status Badge */}
        <div
          className="inline-flex items-center gap-2 px-4 py-2 rounded-full text-sm font-medium"
          style={{ backgroundColor: `${color}20`, color }}
        >
          {getIcon()}
          <span>{emoji}</span>
          <span>{signal_interpretation.title}</span>
        </div>

        {/* Message */}
        <p className="text-center text-[#8B949E] mt-4 text-sm leading-relaxed px-2">
          {signal_interpretation.description}
        </p>
      </div>

      {/* Methodology Section (Collapsible) */}
      {methodology && (
        <div className="mt-6 border-t border-[#30363D] pt-4">
          <button
            onClick={() => setShowMethodology(!showMethodology)}
            className="flex items-center justify-between w-full text-left text-sm text-[#8B949E] hover:text-[#E6EDF3] transition-colors"
          >
            <span className="flex items-center gap-2">
              <Info className="w-4 h-4" />
              계산 방식 및 해석 가이드
            </span>
            {showMethodology ? (
              <ChevronUp className="w-4 h-4" />
            ) : (
              <ChevronDown className="w-4 h-4" />
            )}
          </button>

          {showMethodology && (
            <div className="mt-4 space-y-4 text-sm">
              {/* 데이터 소스 */}
              <div className="p-3 bg-[#0D1117] rounded-lg">
                <div className="font-medium text-[#E6EDF3] mb-2">데이터 소스</div>
                <div className="text-[#8B949E] space-y-1">
                  <div>샘플 크기: {methodology.sample_size}개 / {methodology.total_market.toLocaleString()}개 ({methodology.sample_rate})</div>
                  <div>데이터: {methodology.data_source}</div>
                </div>
              </div>

              {/* 정확도 */}
              <div className="p-3 bg-[#0D1117] rounded-lg">
                <div className="font-medium text-[#E6EDF3] mb-2">정확도</div>
                <div className="text-[#8B949E] space-y-1">
                  <div className="flex justify-between">
                    <span>방향성 판단:</span>
                    <span className="text-[#3FB950]">{methodology.accuracy.direction}</span>
                  </div>
                  <div className="flex justify-between">
                    <span>정확한 종목 수:</span>
                    <span className="text-[#F59E0B]">{methodology.accuracy.exact_count}</span>
                  </div>
                  <div className="flex justify-between">
                    <span>거래량:</span>
                    <span className="text-[#F85149]">{methodology.accuracy.volume}</span>
                  </div>
                </div>
              </div>

              {/* A/D 비율 해석 */}
              <div className="p-3 bg-[#0D1117] rounded-lg">
                <div className="font-medium text-[#E6EDF3] mb-2">A/D 비율 해석</div>
                <div className="text-[#8B949E] space-y-1 text-xs">
                  <div className="flex items-center gap-2">
                    <span className="w-3 h-3 rounded-full bg-[#22c55e]"></span>
                    <span><strong>2.0+</strong>: 강한 상승세</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="w-3 h-3 rounded-full bg-[#84cc16]"></span>
                    <span><strong>1.5~2.0</strong>: 상승세</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="w-3 h-3 rounded-full bg-[#eab308]"></span>
                    <span><strong>0.67~1.5</strong>: 중립</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="w-3 h-3 rounded-full bg-[#f97316]"></span>
                    <span><strong>0.5~0.67</strong>: 하락세</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="w-3 h-3 rounded-full bg-[#ef4444]"></span>
                    <span><strong>0.5 미만</strong>: 강한 하락세</span>
                  </div>
                </div>
              </div>

              {/* 한계점 */}
              <div className="p-3 bg-[#0D1117] rounded-lg border border-[#F59E0B30]">
                <div className="font-medium text-[#F59E0B] mb-2">주의사항</div>
                <ul className="text-[#8B949E] space-y-1 text-xs list-disc list-inside">
                  {methodology.limitations.map((limitation, index) => (
                    <li key={index}>{limitation}</li>
                  ))}
                </ul>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
