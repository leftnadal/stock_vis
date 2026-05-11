'use client';

import { useState, useRef } from 'react';
import Link from 'next/link';
import { HelpCircle, ChevronRight, TrendingUp, AlertTriangle, Network } from 'lucide-react';
import { MiniSparkline } from './MiniSparkline';
import { NewsContextBadge } from './NewsContextBadge';
import { SIGNAL_CATEGORY_COLORS, SIGNAL_CATEGORY_LABELS } from '@/types/eod';
import type { SignalCard as SignalCardType } from '@/types/eod';

interface SignalCardProps {
  card: SignalCardType;
  onCardClick: (card: SignalCardType) => void;
}

export function SignalCard({ card, onCardClick }: SignalCardProps) {
  const [showTip, setShowTip] = useState(false);
  const categoryColor = SIGNAL_CATEGORY_COLORS[card.category] ?? card.color;
  const categoryLabel = SIGNAL_CATEGORY_LABELS[card.category];

  // 모바일 터치/스크롤 충돌 방지
  const touchStartRef = useRef<{ x: number; y: number } | null>(null);
  const isInteractionBlockedRef = useRef(false);

  const handleTouchStart = (e: React.TouchEvent) => {
    const touch = e.touches[0];
    touchStartRef.current = { x: touch.clientX, y: touch.clientY };
    isInteractionBlockedRef.current = false;
  };

  const handleTouchMove = (e: React.TouchEvent) => {
    if (!touchStartRef.current || isInteractionBlockedRef.current) return;
    const touch = e.touches[0];
    const dx = Math.abs(touch.clientX - touchStartRef.current.x);
    const dy = Math.abs(touch.clientY - touchStartRef.current.y);
    if (dx > 10 || dy > 10) {
      isInteractionBlockedRef.current = true;
    }
  };

  const handleTouchEnd = () => {
    touchStartRef.current = null;
  };

  const handleTouchCancel = () => {
    touchStartRef.current = null;
    isInteractionBlockedRef.current = true;
  };

  const handleClick = () => {
    if (isInteractionBlockedRef.current) {
      isInteractionBlockedRef.current = false;
      return;
    }
    onCardClick(card);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault();
      onCardClick(card);
    }
  };

  const handleTipToggle = (e: React.MouseEvent) => {
    e.stopPropagation();
    setShowTip((prev) => !prev);
  };

  return (
    <div
      role="button"
      tabIndex={0}
      onTouchStart={handleTouchStart}
      onTouchMove={handleTouchMove}
      onTouchEnd={handleTouchEnd}
      onTouchCancel={handleTouchCancel}
      onClick={handleClick}
      onKeyDown={handleKeyDown}
      className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 shadow-sm hover:shadow-md transition-all duration-200 overflow-hidden flex flex-col cursor-pointer outline-none focus-visible:ring-2 focus-visible:ring-blue-500"
      style={{ borderLeft: `4px solid ${categoryColor}` }}
    >
      {/* 카드 헤더 */}
      <div className="px-4 pt-4 pb-3">
        <div className="flex items-start justify-between gap-2 mb-1">
          <div className="flex items-center gap-2 min-w-0">
            <span
              className="inline-block w-2 h-2 rounded-full flex-shrink-0"
              style={{ backgroundColor: categoryColor }}
            />
            <span className="text-[11px] font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wide">
              {categoryLabel}
            </span>
          </div>
          <div className="flex items-center gap-1.5 flex-shrink-0">
            <span
              className="inline-flex items-center justify-center px-2 py-0.5 rounded-full text-xs font-bold text-white"
              style={{ backgroundColor: categoryColor }}
            >
              {card.count}
            </span>
            <button
              onClick={handleTipToggle}
              className={`
                p-1 rounded-full transition-colors
                ${showTip
                  ? 'bg-gray-200 dark:bg-gray-600 text-gray-700 dark:text-gray-200'
                  : 'text-gray-400 dark:text-gray-500 hover:text-gray-600 dark:hover:text-gray-300'
                }
              `}
              aria-label="교육 팁 보기"
            >
              <HelpCircle className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>

        <h3 className="text-base font-bold text-gray-900 dark:text-white leading-tight mb-1">
          {card.title}
        </h3>
        <p className="text-xs text-gray-500 dark:text-gray-400 leading-relaxed">
          {card.description_ko}
        </p>
      </div>

      {/* 교육 팁 (토글) */}
      {showTip && (
        <div
          className="mx-4 mb-3 rounded-lg bg-blue-50 dark:bg-blue-900/20 border border-blue-100 dark:border-blue-800 p-3 space-y-2"
          onClick={(e) => e.stopPropagation()}
        >
          <div className="flex items-start gap-2">
            <TrendingUp className="w-3.5 h-3.5 text-blue-600 dark:text-blue-400 mt-0.5 flex-shrink-0" />
            <p className="text-xs text-blue-800 dark:text-blue-200 leading-relaxed">
              {card.education_tip}
            </p>
          </div>
          {card.education_risk && (
            <div className="flex items-start gap-2">
              <AlertTriangle className="w-3.5 h-3.5 text-amber-500 dark:text-amber-400 mt-0.5 flex-shrink-0" />
              <p className="text-xs text-amber-700 dark:text-amber-300 leading-relaxed">
                {card.education_risk}
              </p>
            </div>
          )}
        </div>
      )}

      {/* 프리뷰 종목 목록 */}
      <div className="flex-1 px-4 space-y-2.5 pb-3">
        {card.preview_stocks.slice(0, 3).map((stock) => {
          const isPositive = stock.change_percent >= 0;
          const showChainSight = stock.chain_sight_cta || process.env.NEXT_PUBLIC_FORCE_CHAIN_SIGHT === 'true';
          return (
            <div
              key={stock.symbol}
              className="flex items-start gap-2"
            >
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-1 mb-0.5">
                  <Link
                    href={`/stocks/${stock.symbol}`}
                    className="text-xs font-bold text-gray-900 dark:text-white hover:text-blue-600 dark:hover:text-blue-400 transition-colors"
                    onClick={(e) => e.stopPropagation()}
                  >
                    {stock.symbol}
                  </Link>
                  {showChainSight && (
                    <Link
                      href={`/stocks/${stock.symbol}?tab=chain-sight`}
                      onClick={(e) => e.stopPropagation()}
                      className="text-purple-400 hover:text-purple-600 transition-colors"
                      title="Chain Sight 연계 분석"
                    >
                      <Network className="w-2.5 h-2.5" />
                    </Link>
                  )}
                  <span className="text-[10px] text-gray-400 dark:text-gray-500 truncate">
                    {stock.signal_label}
                  </span>
                </div>
                {stock.news_context?.headline && (
                  <NewsContextBadge news={stock.news_context} />
                )}
              </div>

              <div className="flex-shrink-0 flex flex-col items-end gap-0.5">
                <MiniSparkline data={stock.mini_chart_20d} width={52} height={20} />
                <span
                  className={`text-[11px] font-semibold ${
                    isPositive
                      ? 'text-green-600 dark:text-green-400'
                      : 'text-red-600 dark:text-red-400'
                  }`}
                >
                  {isPositive ? '+' : ''}{stock.change_percent.toFixed(2)}%
                </span>
              </div>
            </div>
          );
        })}
      </div>

      {/* CTA 버튼 */}
      <div className="px-4 pb-4">
        <button
          onClick={(e) => { e.stopPropagation(); onCardClick(card); }}
          className="w-full flex items-center justify-center gap-1.5 py-2 rounded-lg text-xs font-semibold transition-all duration-150 border"
          style={{
            borderColor: categoryColor,
            color: categoryColor,
            backgroundColor: categoryColor + '1A',
          }}
          onMouseEnter={(e) => {
            (e.currentTarget as HTMLButtonElement).style.backgroundColor = categoryColor + '26';
          }}
          onMouseLeave={(e) => {
            (e.currentTarget as HTMLButtonElement).style.backgroundColor = categoryColor + '1A';
          }}
        >
          {card.more_count > 0 ? (
            <>
              +{card.more_count}종목 더 보기
              <ChevronRight className="w-3.5 h-3.5" />
            </>
          ) : (
            <>
              전체 보기
              <ChevronRight className="w-3.5 h-3.5" />
            </>
          )}
        </button>
      </div>
    </div>
  );
}
