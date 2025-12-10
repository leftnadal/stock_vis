'use client';

import React from 'react';
import { Info, TrendingDown, TrendingUp, Minus, AlertTriangle } from 'lucide-react';
import type { FearGreedIndex } from '@/types/macro';
import { EDUCATIONAL_CONTENT } from '@/constants/education';

interface FearGreedGaugeProps {
  data: FearGreedIndex;
  showEducation?: boolean;
}

export default function FearGreedGauge({ data, showEducation = true }: FearGreedGaugeProps) {
  const { value, label, color, message, action_hint, rule_key } = data;

  // 게이지 각도 계산 (0-100 -> -90도 ~ 90도)
  const angle = (value / 100) * 180 - 90;

  // 아이콘 선택
  const getIcon = () => {
    switch (rule_key) {
      case 'extreme_fear':
      case 'fear':
        return <TrendingDown className="w-5 h-5" />;
      case 'extreme_greed':
        return <AlertTriangle className="w-5 h-5" />;
      case 'greed':
        return <TrendingUp className="w-5 h-5" />;
      default:
        return <Minus className="w-5 h-5" />;
    }
  };

  return (
    <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700 p-6">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
          공포/탐욕 지수
        </h3>
        {showEducation && (
          <button
            className="p-2 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700"
            title="자세히 알아보기"
          >
            <Info className="w-5 h-5" />
          </button>
        )}
      </div>

      {/* Gauge */}
      <div className="flex flex-col items-center">
        {/* Semi-circle Gauge */}
        <div className="relative w-48 h-24 mb-4">
          {/* Background arc */}
          <svg viewBox="0 0 200 100" className="w-full h-full">
            {/* Gradient background */}
            <defs>
              <linearGradient id="gaugeGradient" x1="0%" y1="0%" x2="100%" y2="0%">
                <stop offset="0%" stopColor="#DC2626" />
                <stop offset="25%" stopColor="#EA580C" />
                <stop offset="50%" stopColor="#6B7280" />
                <stop offset="75%" stopColor="#16A34A" />
                <stop offset="100%" stopColor="#059669" />
              </linearGradient>
            </defs>

            {/* Background arc */}
            <path
              d="M 10 100 A 90 90 0 0 1 190 100"
              fill="none"
              stroke="url(#gaugeGradient)"
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
            <span
              className="text-4xl font-bold"
              style={{ color }}
            >
              {value}
            </span>
          </div>
        </div>

        {/* Labels */}
        <div className="flex justify-between w-full px-4 text-sm text-gray-500 dark:text-gray-400 mb-4">
          <span>극단적 공포</span>
          <span>극단적 탐욕</span>
        </div>

        {/* Status Badge */}
        <div
          className="inline-flex items-center gap-2 px-4 py-2 rounded-full text-sm font-medium"
          style={{ backgroundColor: `${color}20`, color }}
        >
          {getIcon()}
          {label}
        </div>

        {/* Message */}
        <p className="text-center text-gray-600 dark:text-gray-400 mt-4 text-sm leading-relaxed">
          {message}
        </p>

        {/* Action Hint */}
        {action_hint && (
          <div className="mt-4 px-4 py-2 bg-gray-50 dark:bg-gray-700 rounded-lg text-center">
            <span className="text-xs text-gray-500 dark:text-gray-400">투자자 힌트:</span>
            <p className="text-sm font-medium text-gray-700 dark:text-gray-300">
              {action_hint}
            </p>
          </div>
        )}
      </div>

      {/* Education Section */}
      {showEducation && (
        <div className="mt-6 pt-6 border-t border-gray-200 dark:border-gray-700">
          <details className="group">
            <summary className="flex items-center justify-between cursor-pointer text-sm text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white">
              <span className="font-medium">이 지표는 어떻게 해석하나요?</span>
              <span className="ml-2 transform group-open:rotate-180 transition-transform">
                ▼
              </span>
            </summary>
            <div className="mt-3 text-sm text-gray-600 dark:text-gray-400 space-y-2">
              <p>{EDUCATIONAL_CONTENT.fearGreed.levels.beginner}</p>
              <ul className="list-disc list-inside space-y-1 mt-2">
                {EDUCATIONAL_CONTENT.fearGreed.keyPoints.slice(0, 3).map((point, i) => (
                  <li key={i}>{point}</li>
                ))}
              </ul>
            </div>
          </details>
        </div>
      )}
    </div>
  );
}
