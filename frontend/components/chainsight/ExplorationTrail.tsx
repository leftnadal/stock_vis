'use client';

import { useRef, useEffect } from 'react';
import { useExplorationStore } from '@/lib/stores/explorationStore';

const REL_LABELS: Record<string, string> = {
  SUPPLIES_TO: 'supply',
  CUSTOMER_OF: 'customer',
  COMPETES_WITH: 'compete',
  PEER_OF: 'peer',
  CO_MENTIONED: 'co-mention',
  PRICE_CORRELATED: 'corr',
};

export default function ExplorationTrail() {
  const { trail, undoToTrailNode } = useExplorationStore();
  const scrollRef = useRef<HTMLDivElement>(null);

  // 새 노드 추가 시 오른쪽 끝 자동 스크롤
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTo({
        left: scrollRef.current.scrollWidth,
        behavior: 'smooth',
      });
    }
  }, [trail.length]);

  if (trail.length === 0) return null;

  return (
    <div
      ref={scrollRef}
      className="flex items-center gap-1 overflow-x-auto py-3 px-2 scrollbar-thin h-[60px]"
    >
      {trail.map((node, i) => {
        const isCurrent = i === trail.length - 1;
        const r = isCurrent ? 18 : 12;

        return (
          <div key={`${node.symbol}-${i}`} className="flex items-center gap-1 flex-shrink-0">
            {/* 엣지 라벨 (첫 노드 이후) */}
            {i > 0 && node.relation_from_prev && (
              <span className="text-[10px] text-gray-400 dark:text-gray-500 px-1">
                ──{REL_LABELS[node.relation_from_prev] || node.relation_from_prev}──
              </span>
            )}
            {i > 0 && !node.relation_from_prev && (
              <span className="text-gray-300 dark:text-gray-600 px-1">──</span>
            )}

            {/* 노드 */}
            <button
              onClick={() => undoToTrailNode(i)}
              className={`
                flex items-center justify-center rounded-full
                text-xs font-medium transition-all duration-200
                ${isCurrent
                  ? 'bg-blue-500 text-white shadow-md'
                  : 'bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-600'
                }
              `}
              style={{ width: r * 2, height: r * 2, minWidth: r * 2 }}
              title={node.symbol}
            >
              {node.type === 'sector'
                ? node.symbol.slice(0, 4)
                : node.symbol.slice(0, 5)}
            </button>
          </div>
        );
      })}
    </div>
  );
}
