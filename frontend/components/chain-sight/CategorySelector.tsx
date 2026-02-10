'use client';

import { ChainSightCategory } from '@/types/chainSight';

interface CategorySelectorProps {
  categories: ChainSightCategory[];
  selectedId: string | null;
  onSelect: (categoryId: string | null) => void;
  isLoading?: boolean;
}

/**
 * 카테고리 선택 컴포넌트
 *
 * 카테고리 칩/버튼을 표시하고 선택 상태를 관리합니다.
 */
export default function CategorySelector({
  categories,
  selectedId,
  onSelect,
  isLoading = false,
}: CategorySelectorProps) {
  if (isLoading) {
    return (
      <div className="flex flex-wrap gap-2 p-4">
        {[1, 2, 3].map((i) => (
          <div
            key={i}
            className="h-10 w-28 animate-pulse rounded-full bg-gray-200 dark:bg-gray-700"
          />
        ))}
      </div>
    );
  }

  if (categories.length === 0) {
    return (
      <div className="p-4 text-center text-sm text-gray-500 dark:text-gray-400">
        카테고리를 찾을 수 없습니다. 잠시 후 다시 시도해 주세요.
      </div>
    );
  }

  return (
    <div className="flex flex-wrap gap-2 p-4">
      {categories.map((category) => {
        const isSelected = selectedId === category.id;
        const count = category.count === '?' ? '' : `(${category.count})`;

        return (
          <button
            key={category.id}
            onClick={() => onSelect(isSelected ? null : category.id)}
            className={`
              group flex items-center gap-2 rounded-full px-4 py-2 text-sm font-medium
              transition-all duration-200
              ${
                isSelected
                  ? 'bg-blue-600 text-white shadow-md'
                  : 'bg-gray-100 text-gray-700 hover:bg-gray-200 dark:bg-gray-700 dark:text-gray-200 dark:hover:bg-gray-600'
              }
            `}
            title={category.description}
          >
            <span className="text-base">{category.icon}</span>
            <span>{category.name}</span>
            {count && (
              <span
                className={`
                  text-xs
                  ${isSelected ? 'text-blue-100' : 'text-gray-500 dark:text-gray-400'}
                `}
              >
                {count}
              </span>
            )}
            {category.is_dynamic && !isSelected && (
              <span className="text-xs text-blue-500">AI</span>
            )}
          </button>
        );
      })}
    </div>
  );
}
