'use client';

/**
 * AI 가이드 패널 (좌측)
 * 카테고리 카드 + Chain Trace 입력
 */

import type { SuggestionCategory } from '@/types/chainsight';

interface AIGuidePanelProps {
  categories: SuggestionCategory[];
  isLoading: boolean;
  /**
   * ⑳-3 S2: 카테고리(suggestions) 기능이 아직 PG로 복구되지 않아 "준비 중" 상태로
   * 정직 표시. true이면 에러/빈 배열을 "카테고리 없음"으로 오표시하지 않고 준비 중 안내.
   */
  preparing?: boolean;
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
  preparing = false,
  activeCategory,
  onCategorySelect,
}: AIGuidePanelProps) {
  // ⑳-3 S2 D-1: Chain Trace(레거시 Neo4j /trace/) 미호출 — centerSymbol·onTrace 미사용.
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
        ) : preparing ? (
          // ⑳-3 S2: (b) 준비 중 상태 — suggestions PG 재설계 전까지 정직 표시(오류≠무데이터)
          <div className="py-6 text-center space-y-1">
            <p className="text-xs text-gray-500">탐색 카테고리는 준비 중입니다</p>
            <p className="text-[11px] text-gray-400">
              관계 그래프는 아래 지도에서 바로 탐색할 수 있어요
            </p>
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

        {!isLoading && !preparing && categories.length === 0 && (
          <p className="text-xs text-gray-400 py-4 text-center">
            탐색 가능한 카테고리가 없습니다.
          </p>
        )}
      </div>

      {/* 경로 탐색 섹션 — ⑳-3 S2 D-1: 레거시 Neo4j trace 미호출(500→"경로 없음" 오번역 제거).
          준비 중으로 정직 표시(TRACE-PG-REDESIGN, 백본 트랙 연계 후보). */}
      <div className="border-t border-gray-200 p-3">
        <h4 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-2">
          경로 탐색
        </h4>
        <p className="text-xs text-gray-400 py-2">경로 탐색은 준비 중입니다</p>
      </div>
    </div>
  );
}
