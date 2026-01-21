'use client';

import { useState } from 'react';
import { Filter } from 'lucide-react';
import type { ScreenerFilters as Filters } from '@/services/strategyService';

interface ScreenerFiltersProps {
  onFilterChange: (filters: Filters) => void;
}

const SECTORS = [
  { value: '', label: '전체' },
  { value: 'Technology', label: '기술' },
  { value: 'Healthcare', label: '헬스케어' },
  { value: 'Finance', label: '금융' },
  { value: 'Consumer', label: '소비재' },
  { value: 'Energy', label: '에너지' },
  { value: 'Industrial', label: '산업재' },
];

export function ScreenerFilters({ onFilterChange }: ScreenerFiltersProps) {
  const [filters, setFilters] = useState<Filters>({});

  const handleChange = (key: keyof Filters, value: string | number | undefined) => {
    const newFilters = {
      ...filters,
      [key]: value === '' ? undefined : value,
    };
    setFilters(newFilters);
    onFilterChange(newFilters);
  };

  const handleReset = () => {
    setFilters({});
    onFilterChange({});
  };

  return (
    <div className="rounded-lg border border-[#30363D] bg-[#0D1117] p-4">
      <div className="mb-3 flex items-center gap-2">
        <Filter className="h-4 w-4 text-[#58A6FF]" />
        <h3 className="text-sm font-semibold text-[#E6EDF3]">필터</h3>
      </div>

      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-4">
        {/* PER 최소값 */}
        <div>
          <label className="mb-1 block text-xs text-[#8B949E]">PER 최소</label>
          <input
            type="number"
            value={filters.per_min || ''}
            onChange={(e) => handleChange('per_min', e.target.value ? Number(e.target.value) : undefined)}
            placeholder="예: 0"
            className="w-full rounded border border-[#30363D] bg-[#161B22] px-3 py-2 text-sm text-[#E6EDF3] placeholder-[#8B949E] focus:border-[#58A6FF] focus:outline-none"
          />
        </div>

        {/* PER 최대값 */}
        <div>
          <label className="mb-1 block text-xs text-[#8B949E]">PER 최대</label>
          <input
            type="number"
            value={filters.per_max || ''}
            onChange={(e) => handleChange('per_max', e.target.value ? Number(e.target.value) : undefined)}
            placeholder="예: 30"
            className="w-full rounded border border-[#30363D] bg-[#161B22] px-3 py-2 text-sm text-[#E6EDF3] placeholder-[#8B949E] focus:border-[#58A6FF] focus:outline-none"
          />
        </div>

        {/* ROE 최소값 */}
        <div>
          <label className="mb-1 block text-xs text-[#8B949E]">ROE 최소 (%)</label>
          <input
            type="number"
            value={filters.roe_min || ''}
            onChange={(e) => handleChange('roe_min', e.target.value ? Number(e.target.value) : undefined)}
            placeholder="예: 15"
            className="w-full rounded border border-[#30363D] bg-[#161B22] px-3 py-2 text-sm text-[#E6EDF3] placeholder-[#8B949E] focus:border-[#58A6FF] focus:outline-none"
          />
        </div>

        {/* 섹터 */}
        <div>
          <label className="mb-1 block text-xs text-[#8B949E]">섹터</label>
          <select
            value={filters.sector || ''}
            onChange={(e) => handleChange('sector', e.target.value || undefined)}
            className="w-full rounded border border-[#30363D] bg-[#161B22] px-3 py-2 text-sm text-[#E6EDF3] focus:border-[#58A6FF] focus:outline-none"
          >
            {SECTORS.map((sector) => (
              <option key={sector.value} value={sector.value}>
                {sector.label}
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* 초기화 버튼 */}
      <div className="mt-3 flex justify-end">
        <button
          onClick={handleReset}
          className="rounded px-3 py-1.5 text-xs font-medium text-[#8B949E] transition-colors hover:bg-[#161B22] hover:text-[#E6EDF3]"
        >
          초기화
        </button>
      </div>
    </div>
  );
}
