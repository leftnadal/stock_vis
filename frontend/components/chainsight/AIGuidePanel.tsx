'use client';

/**
 * AI 가이드 패널 (좌측)
 * 카테고리 카드 + Chain Trace 입력
 */

import { useState } from 'react';
import type { SuggestionCategory } from '@/types/chainsight';

interface AIGuidePanelProps {
  categories: SuggestionCategory[];
  isLoading: boolean;
  activeCategory: string | null;
  centerSymbol: string;
  onCategorySelect: (categoryId: string | null) => void;
  onTrace: (from: string, to: string) => void;
}

const STRENGTH_LABELS: Record<string, string> = {
  strong: '강함',
  moderate: '보통',
  signal: '시그널',
  weak: '약함',
};

export default function AIGuidePanel({
  categories,
  isLoading,
  activeCategory,
  centerSymbol,
  onCategorySelect,
  onTrace,
}: AIGuidePanelProps) {
  const [traceTo, setTraceTo] = useState('');

  return (
    <div className="flex flex-col h-full">
      {/* 카테고리 섹션 */}
      <div className="flex-1 overflow-y-auto p-3 space-y-2">
        <h4 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-2">
          탐색 카테고리
        </h4>

        {isLoading ? (
          <div className="space-y-2">
            {[1, 2, 3].map(i => (
              <div key={i} className="h-16 bg-gray-100 rounded-lg animate-pulse" />
            ))}
          </div>
        ) : (
          categories.map(cat => {
            const isActive = activeCategory === cat.id;
            return (
              <button
                key={cat.id}
                onClick={() => onCategorySelect(isActive ? null : cat.id)}
                className={`w-full text-left p-3 rounded-lg border transition text-sm ${
                  isActive
                    ? 'border-blue-500 bg-blue-50'
                    : 'border-gray-200 bg-white hover:border-gray-300'
                }`}
              >
                <div className="flex items-center justify-between">
                  <span className="font-medium">{cat.label}</span>
                  <span className="text-xs text-gray-500">{cat.count}</span>
                </div>
                {cat.top_tickers.length > 0 && (
                  <div className="mt-1 text-xs text-gray-500">
                    {cat.top_tickers.slice(0, 3).join(', ')}
                    {cat.count > 3 && ` +${cat.count - 3}`}
                  </div>
                )}
                <div className="mt-1 text-xs text-gray-400">
                  {STRENGTH_LABELS[cat.strength] || cat.strength}
                </div>
              </button>
            );
          })
        )}

        {!isLoading && categories.length === 0 && (
          <p className="text-xs text-gray-400 py-4 text-center">
            탐색 가능한 카테고리가 없습니다.
          </p>
        )}
      </div>

      {/* Chain Trace 섹션 */}
      <div className="border-t border-gray-200 p-3">
        <h4 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-2">
          Chain Trace
        </h4>
        <div className="space-y-2">
          <div className="text-xs">
            <span className="text-gray-500">From:</span>{' '}
            <span className="font-medium">{centerSymbol}</span>
          </div>
          <input
            type="text"
            placeholder="To: 종목 심볼 입력"
            value={traceTo}
            onChange={e => setTraceTo(e.target.value.toUpperCase())}
            onKeyDown={e => {
              if (e.key === 'Enter' && traceTo) {
                onTrace(centerSymbol, traceTo);
              }
            }}
            className="w-full px-3 py-2 text-sm border border-gray-200 rounded-lg focus:outline-none focus:border-blue-500"
          />
          <button
            onClick={() => traceTo && onTrace(centerSymbol, traceTo)}
            disabled={!traceTo}
            className="w-full text-sm py-2 rounded-lg bg-gray-800 text-white disabled:opacity-40 hover:bg-gray-700 transition"
          >
            경로 찾기
          </button>
        </div>
      </div>
    </div>
  );
}
