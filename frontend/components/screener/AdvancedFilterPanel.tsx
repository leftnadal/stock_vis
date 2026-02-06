'use client';

import React, { useState, useMemo, useCallback } from 'react';
import { Search, ChevronDown, ChevronUp, X, Filter, Star, SlidersHorizontal } from 'lucide-react';
import type { FilterCategory, FilterDefinition, ScreenerFilters } from '@/types/screener';
import { FILTER_CATEGORIES, ADVANCED_FILTERS } from '@/types/screener';

interface AdvancedFilterPanelProps {
  filters: ScreenerFilters;
  onFilterChange: (key: keyof ScreenerFilters, value: string | number | undefined) => void;
  onReset: () => void;
  activePresetIds?: number[];
  className?: string;
}

export default function AdvancedFilterPanel({
  filters,
  onFilterChange,
  onReset,
  activePresetIds = [],
  className = '',
}: AdvancedFilterPanelProps) {
  const hasActivePresets = activePresetIds.length > 0;
  const [isExpanded, setIsExpanded] = useState(false);
  const [activeCategory, setActiveCategory] = useState<FilterCategory | 'popular'>('popular');
  const [searchQuery, setSearchQuery] = useState('');

  // Filter filters based on search query and category
  const displayedFilters = useMemo(() => {
    let result = ADVANCED_FILTERS;

    // Search filter
    if (searchQuery.trim()) {
      const query = searchQuery.toLowerCase();
      result = result.filter(
        (f) =>
          f.label.toLowerCase().includes(query) ||
          f.labelKo.includes(query) ||
          (f.descriptionKo && f.descriptionKo.includes(query))
      );
    }

    // Category filter
    if (activeCategory === 'popular') {
      result = result.filter((f) => f.isPopular);
    } else {
      result = result.filter((f) => f.category === activeCategory);
    }

    return result;
  }, [searchQuery, activeCategory]);

  // Count active filters per category
  const categoryFilterCounts = useMemo(() => {
    const counts: Record<string, number> = { popular: 0 };

    FILTER_CATEGORIES.forEach((cat) => {
      counts[cat.id] = 0;
    });

    Object.keys(filters).forEach((key) => {
      const value = filters[key as keyof ScreenerFilters];
      if (value !== undefined && value !== '') {
        const filter = ADVANCED_FILTERS.find((f) => f.id === key);
        if (filter) {
          counts[filter.category]++;
          if (filter.isPopular) {
            counts['popular']++;
          }
        }
      }
    });

    return counts;
  }, [filters]);

  // Total active filters count
  const totalActiveFilters = Object.values(filters).filter(
    (v) => v !== undefined && v !== ''
  ).length;

  // Handle range filter change
  const handleRangeChange = useCallback(
    (filterId: string, value: string) => {
      const numValue = value === '' ? undefined : Number(value);
      onFilterChange(filterId as keyof ScreenerFilters, numValue);
    },
    [onFilterChange]
  );

  // Handle select filter change
  const handleSelectChange = useCallback(
    (filterId: string, value: string) => {
      onFilterChange(filterId as keyof ScreenerFilters, value || undefined);
    },
    [onFilterChange]
  );

  // Get current value for a filter (excludes array values for simplicity)
  const getFilterValue = (filterId: string): string | number | undefined => {
    const value = filters[filterId as keyof ScreenerFilters];
    // Skip array values (sectors[], exchanges[])
    if (Array.isArray(value)) {
      return undefined;
    }
    return value;
  };

  // Render a single filter input
  const renderFilterInput = (filter: FilterDefinition) => {
    const value = getFilterValue(filter.id);

    if (filter.type === 'range') {
      return (
        <div className="flex flex-col gap-1">
          <label className="text-xs text-[#8B949E]">
            {filter.labelKo}
            {filter.unit && <span className="text-[#6E7681]"> ({filter.unit})</span>}
          </label>
          <div className="flex items-center gap-2">
            <input
              type="number"
              value={value ?? ''}
              onChange={(e) => handleRangeChange(filter.id, e.target.value)}
              placeholder={filter.minValue !== undefined ? String(filter.minValue) : ''}
              min={filter.minValue}
              max={filter.maxValue}
              step={filter.step}
              className="w-full rounded border border-[#30363D] bg-[#0D1117] px-3 py-1.5 text-sm text-[#E6EDF3] placeholder-[#6E7681] focus:border-[#58A6FF] focus:outline-none"
            />
            {value !== undefined && value !== '' && (
              <button
                onClick={() => handleRangeChange(filter.id, '')}
                className="p-1 text-[#8B949E] hover:text-[#F85149]"
                title="삭제"
              >
                <X className="h-3.5 w-3.5" />
              </button>
            )}
          </div>
          {filter.descriptionKo && (
            <p className="text-[10px] text-[#6E7681]">{filter.descriptionKo}</p>
          )}
        </div>
      );
    }

    if (filter.type === 'select') {
      return (
        <div className="flex flex-col gap-1">
          <label className="text-xs text-[#8B949E]">{filter.labelKo}</label>
          <select
            value={(value as string) ?? ''}
            onChange={(e) => handleSelectChange(filter.id, e.target.value)}
            className="w-full rounded border border-[#30363D] bg-[#0D1117] px-3 py-1.5 text-sm text-[#E6EDF3] focus:border-[#58A6FF] focus:outline-none"
          >
            <option value="">전체</option>
            {filter.options?.map((opt) => (
              <option key={opt.value} value={opt.value}>
                {opt.label}
              </option>
            ))}
          </select>
        </div>
      );
    }

    return null;
  };

  return (
    <div className={`rounded-lg border border-[#30363D] bg-[#161B22] ${className}`}>
      {/* Header */}
      <div
        className="flex cursor-pointer items-center justify-between px-4 py-3"
        onClick={() => setIsExpanded(!isExpanded)}
      >
        <div className="flex items-center gap-2">
          <SlidersHorizontal className="h-4 w-4 text-[#58A6FF]" />
          <h3 className="text-sm font-semibold text-[#E6EDF3]">고급 필터</h3>
          {totalActiveFilters > 0 && (
            <span className="rounded-full bg-[#238636] px-2 py-0.5 text-xs font-medium text-white">
              {totalActiveFilters}
            </span>
          )}
        </div>
        <div className="flex items-center gap-2">
          {totalActiveFilters > 0 && (
            <button
              onClick={(e) => {
                e.stopPropagation();
                onReset();
              }}
              className="text-xs text-[#F85149] hover:underline"
              title={hasActivePresets ? '추가 필터만 초기화 (프리셋 유지)' : '모든 필터 초기화'}
            >
              {hasActivePresets ? '추가 필터 초기화' : '초기화'}
            </button>
          )}
          {isExpanded ? (
            <ChevronUp className="h-4 w-4 text-[#8B949E]" />
          ) : (
            <ChevronDown className="h-4 w-4 text-[#8B949E]" />
          )}
        </div>
      </div>

      {/* Expanded content */}
      {isExpanded && (
        <div className="border-t border-[#30363D] px-4 py-4">
          {/* Search */}
          <div className="mb-4">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-[#8B949E]" />
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="필터 검색..."
                className="w-full rounded border border-[#30363D] bg-[#0D1117] py-2 pl-9 pr-3 text-sm text-[#E6EDF3] placeholder-[#8B949E] focus:border-[#58A6FF] focus:outline-none"
              />
              {searchQuery && (
                <button
                  onClick={() => setSearchQuery('')}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-[#8B949E] hover:text-[#E6EDF3]"
                >
                  <X className="h-4 w-4" />
                </button>
              )}
            </div>
          </div>

          {/* Category tabs */}
          <div className="mb-4 flex flex-wrap gap-2">
            {/* Popular tab */}
            <button
              onClick={() => setActiveCategory('popular')}
              className={`flex items-center gap-1 rounded-full px-3 py-1.5 text-xs font-medium transition-colors ${
                activeCategory === 'popular'
                  ? 'bg-[#238636] text-white'
                  : 'bg-[#21262D] text-[#8B949E] hover:bg-[#30363D] hover:text-[#E6EDF3]'
              }`}
            >
              <Star className="h-3 w-3" />
              인기
              {categoryFilterCounts['popular'] > 0 && (
                <span className="ml-1 rounded-full bg-white/20 px-1.5 text-[10px]">
                  {categoryFilterCounts['popular']}
                </span>
              )}
            </button>

            {/* Category tabs */}
            {FILTER_CATEGORIES.map((cat) => (
              <button
                key={cat.id}
                onClick={() => setActiveCategory(cat.id)}
                className={`rounded-full px-3 py-1.5 text-xs font-medium transition-colors ${
                  activeCategory === cat.id
                    ? 'bg-[#58A6FF] text-white'
                    : 'bg-[#21262D] text-[#8B949E] hover:bg-[#30363D] hover:text-[#E6EDF3]'
                }`}
              >
                {cat.labelKo}
                {categoryFilterCounts[cat.id] > 0 && (
                  <span className="ml-1 rounded-full bg-white/20 px-1.5 text-[10px]">
                    {categoryFilterCounts[cat.id]}
                  </span>
                )}
              </button>
            ))}
          </div>

          {/* Filter grid */}
          {displayedFilters.length > 0 ? (
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
              {displayedFilters.map((filter) => (
                <div key={filter.id}>{renderFilterInput(filter)}</div>
              ))}
            </div>
          ) : (
            <div className="flex flex-col items-center justify-center py-8 text-[#8B949E]">
              <Filter className="mb-2 h-8 w-8 opacity-50" />
              <p className="text-sm">검색 결과가 없습니다</p>
              <p className="text-xs">다른 키워드로 검색해보세요</p>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
