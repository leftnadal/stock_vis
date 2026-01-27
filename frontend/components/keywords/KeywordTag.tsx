'use client';

import { memo, useState } from 'react';
import type { Keyword } from '@/types/keyword';
import { KEYWORD_CATEGORY_COLORS, KEYWORD_CATEGORY_LABELS } from '@/types/keyword';
import { Info } from 'lucide-react';

interface KeywordTagProps {
  keyword: Keyword;
  onClick?: (keyword: Keyword) => void;
  showTooltip?: boolean;
  showConfidence?: boolean;
  size?: 'sm' | 'md';
}

// 기본 색상 (카테고리가 없거나 매칭되지 않을 때)
const DEFAULT_COLORS = {
  bg: 'bg-gray-50',
  text: 'text-gray-700',
  border: 'border-gray-200',
  darkBg: 'dark:bg-gray-800/50',
  darkText: 'dark:text-gray-300',
  darkBorder: 'dark:border-gray-600',
};

const DEFAULT_LABEL = { en: 'Keyword', ko: '키워드' };

export const KeywordTag = memo(function KeywordTag({
  keyword,
  onClick,
  showTooltip = true,
  showConfidence = false,
  size = 'sm',
}: KeywordTagProps) {
  const [isHovered, setIsHovered] = useState(false);

  // 카테고리가 없거나 매칭되지 않으면 기본값 사용
  const colors = (keyword.category && KEYWORD_CATEGORY_COLORS[keyword.category]) || DEFAULT_COLORS;
  const categoryLabel = (keyword.category && KEYWORD_CATEGORY_LABELS[keyword.category]) || DEFAULT_LABEL;

  const sizeClasses = {
    sm: 'px-2 py-0.5 text-[10px]',
    md: 'px-2.5 py-1 text-xs',
  };

  const confidenceColor = (conf: number) => {
    if (conf >= 0.8) return 'text-emerald-600 dark:text-emerald-400';
    if (conf >= 0.6) return 'text-amber-600 dark:text-amber-400';
    return 'text-gray-500 dark:text-gray-400';
  };

  return (
    <div
      className="relative inline-flex items-center gap-1 group/keyword"
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
    >
      <span
        onClick={() => onClick?.(keyword)}
        className={`
          inline-flex items-center gap-1 rounded-md font-medium transition-all duration-200
          ${colors.bg} ${colors.text} ${colors.darkBg} ${colors.darkText}
          border ${colors.border} ${colors.darkBorder}
          ${sizeClasses[size]}
          ${onClick ? 'cursor-pointer hover:scale-105 hover:shadow-sm' : ''}
        `}
      >
        {/* 카테고리 라벨 (선택 사항) */}
        {/* <span className="opacity-60 text-[9px] uppercase">{categoryLabel.ko}</span> */}
        {/* <span className="text-gray-300 dark:text-gray-600">·</span> */}

        {/* 키워드 텍스트 */}
        <span>{keyword.text}</span>

        {/* 신뢰도 표시 (선택) */}
        {showConfidence && keyword.confidence !== undefined && (
          <span className={`text-[9px] ${confidenceColor(keyword.confidence)}`}>
            {Math.round(keyword.confidence * 100)}%
          </span>
        )}

        {/* 툴팁 아이콘 */}
        {showTooltip && keyword.description && (
          <Info className="w-2.5 h-2.5 opacity-50 group-hover/keyword:opacity-100 transition-opacity" />
        )}
      </span>

      {/* 호버 툴팁 */}
      {showTooltip && keyword.description && isHovered && (
        <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-1 z-20 w-48 p-2 bg-gray-900 dark:bg-gray-700 text-white text-[10px] leading-relaxed rounded shadow-lg pointer-events-none">
          <div className="space-y-1">
            <div className="flex items-center justify-between">
              <span className="font-semibold text-[11px]">{keyword.text}</span>
              <span className="text-gray-400 text-[9px] uppercase">{categoryLabel.ko}</span>
            </div>
            <p className="text-gray-300">{keyword.description}</p>
            {showConfidence && keyword.confidence !== undefined && (
              <div className="pt-1 border-t border-gray-600">
                <span className="text-gray-400">신뢰도: </span>
                <span className={confidenceColor(keyword.confidence)}>
                  {Math.round(keyword.confidence * 100)}%
                </span>
              </div>
            )}
          </div>
          {/* 화살표 */}
          <div className="absolute top-full left-1/2 -translate-x-1/2 -mt-px">
            <div className="w-2 h-2 bg-gray-900 dark:bg-gray-700 rotate-45" />
          </div>
        </div>
      )}
    </div>
  );
});
