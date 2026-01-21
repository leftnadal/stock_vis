'use client';

import { ArrowUp, ArrowDown } from 'lucide-react';
import type { MajorIndex } from '@/services/strategyService';

interface QuoteCardProps {
  quote: MajorIndex;
}

export function QuoteCard({ quote }: QuoteCardProps) {
  const isPositive = quote.change >= 0;

  // 간단한 스파크라인 (있으면 표시)
  const renderSparkline = () => {
    if (!quote.sparkline || quote.sparkline.length === 0) return null;

    const min = Math.min(...quote.sparkline);
    const max = Math.max(...quote.sparkline);
    const range = max - min || 1;

    const points = quote.sparkline
      .map((value, index) => {
        const x = (index / (quote.sparkline!.length - 1)) * 100;
        const y = 100 - ((value - min) / range) * 100;
        return `${x},${y}`;
      })
      .join(' ');

    return (
      <svg
        className="absolute bottom-0 right-0 w-24 h-12 opacity-20"
        viewBox="0 0 100 100"
        preserveAspectRatio="none"
      >
        <polyline
          points={points}
          fill="none"
          stroke={isPositive ? '#3FB950' : '#F85149'}
          strokeWidth="2"
        />
      </svg>
    );
  };

  return (
    <div className="relative overflow-hidden rounded-lg border border-[#30363D] bg-[#161B22] p-4 transition-all hover:border-[#58A6FF]/50 hover:shadow-lg">
      {/* 스파크라인 배경 */}
      {renderSparkline()}

      {/* 컨텐츠 */}
      <div className="relative z-10">
        <div className="mb-2 text-xs font-medium text-[#8B949E]">{quote.name}</div>
        <div className="mb-1 text-2xl font-bold text-[#E6EDF3]">
          {quote.price.toLocaleString('en-US', {
            minimumFractionDigits: 2,
            maximumFractionDigits: 2,
          })}
        </div>
        <div className="flex items-center gap-1">
          {isPositive ? (
            <ArrowUp className="h-4 w-4 text-[#3FB950]" />
          ) : (
            <ArrowDown className="h-4 w-4 text-[#F85149]" />
          )}
          <span className={`text-sm font-medium ${isPositive ? 'text-[#3FB950]' : 'text-[#F85149]'}`}>
            {isPositive ? '+' : ''}
            {quote.change.toFixed(2)} ({quote.change_percent})
          </span>
        </div>
      </div>
    </div>
  );
}
