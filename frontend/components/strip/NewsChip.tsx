// 뉴스 스트립 칩 1장 — 방향점·헤드라인·relevance_line·"+n건"·관계망 배지. [D-NEWSAXIS-CONTRACT]
import { DIRECTION_HEX_SIGNED } from '@/components/common/colorSemantics';
import type { NewsStripItem, StripDirection } from '@/services/stripService';

// 방향점 색 = 공용 토큰만 소비(로컬 색 사전 금지, D-COLOR-TOKEN). 중립은 방향 없음=회색.
function dotColor(direction: StripDirection): string {
  if (direction === 'up') return DIRECTION_HEX_SIGNED.positive;
  if (direction === 'down') return DIRECTION_HEX_SIGNED.negative;
  return '#9ca3af'; // gray-400 (중립 = 방향색 아님)
}

export function NewsChip({ item }: { item: NewsStripItem }) {
  return (
    <a
      href={item.article_url}
      target="_blank"
      rel="noopener noreferrer"
      role="listitem"
      className="flex-shrink-0 w-64 snap-start rounded-lg border border-gray-200 bg-white p-3 shadow-sm hover:shadow-md transition-shadow dark:border-gray-700 dark:bg-gray-800"
    >
      <div className="flex items-center gap-2">
        <span
          data-testid="direction-dot"
          className="inline-block h-2 w-2 rounded-full"
          style={{ backgroundColor: dotColor(item.direction) }}
        />
        <span className="text-xs text-gray-500 dark:text-gray-400">
          {item.relevance_line}
        </span>
        {item.collapsed_count > 0 && (
          <span className="ml-auto text-xs text-gray-400">
            +{item.collapsed_count}건
          </span>
        )}
      </div>

      <p className="mt-1 line-clamp-2 text-sm font-medium text-gray-900 dark:text-gray-100">
        {item.headline}
      </p>

      {item.badge && (
        <div className="mt-2">
          <span className="inline-flex items-center rounded-full bg-indigo-50 px-2 py-0.5 text-xs text-indigo-700 dark:bg-indigo-900/40 dark:text-indigo-300">
            🔗 {item.badge.pair}
          </span>
        </div>
      )}
    </a>
  );
}
