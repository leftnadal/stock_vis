'use client';

import { useState } from 'react';
import { Filter, RotateCcw } from 'lucide-react';
import type { ScreenerFilters as Filters } from '@/services/strategyService';

interface ScreenerFiltersProps {
  onFilterChange: (filters: Filters) => void;
}

const EXCHANGES = [
  { value: '', label: '전체' },
  { value: 'NYSE', label: 'NYSE' },
  { value: 'NASDAQ', label: 'NASDAQ' },
  { value: 'AMEX', label: 'AMEX' },
  { value: 'EURONEXT', label: 'EURONEXT' },
  { value: 'TSX', label: 'TSX (토론토)' },
  { value: 'LSE', label: 'LSE (런던)' },
];

const SECTORS = [
  { value: '', label: '전체' },
  { value: 'Technology', label: '기술 (Technology)' },
  { value: 'Healthcare', label: '헬스케어 (Healthcare)' },
  { value: 'Financial Services', label: '금융 (Financial Services)' },
  { value: 'Consumer Cyclical', label: '경기소비재 (Consumer Cyclical)' },
  { value: 'Consumer Defensive', label: '필수소비재 (Consumer Defensive)' },
  { value: 'Energy', label: '에너지 (Energy)' },
  { value: 'Industrials', label: '산업재 (Industrials)' },
  { value: 'Basic Materials', label: '소재 (Basic Materials)' },
  { value: 'Communication Services', label: '통신서비스 (Communication Services)' },
  { value: 'Utilities', label: '유틸리티 (Utilities)' },
  { value: 'Real Estate', label: '부동산 (Real Estate)' },
];

const LIMIT_OPTIONS = [
  { value: 20, label: '20개' },
  { value: 50, label: '50개' },
  { value: 100, label: '100개' },
  { value: 200, label: '200개' },
  { value: 500, label: '500개' },
];

export function ScreenerFilters({ onFilterChange }: ScreenerFiltersProps) {
  const [filters, setFilters] = useState<Filters>({ limit: 100 });

  const handleChange = (key: keyof Filters, value: string | number | undefined) => {
    const newFilters = {
      ...filters,
      [key]: value === '' ? undefined : value,
    };
    setFilters(newFilters);
    onFilterChange(newFilters);
  };

  const handleReset = () => {
    const defaultFilters = { limit: 100 };
    setFilters(defaultFilters);
    onFilterChange(defaultFilters);
  };

  return (
    <div className="rounded-lg border border-[#30363D] bg-[#0D1117] p-4">
      <div className="mb-4 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Filter className="h-4 w-4 text-[#58A6FF]" />
          <h3 className="text-sm font-semibold text-[#E6EDF3]">필터</h3>
        </div>
        <button
          onClick={handleReset}
          className="flex items-center gap-1 rounded px-2 py-1 text-xs font-medium text-[#8B949E] transition-colors hover:bg-[#161B22] hover:text-[#E6EDF3]"
        >
          <RotateCcw className="h-3 w-3" />
          초기화
        </button>
      </div>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
        {/* 최대 개수 */}
        <div>
          <label className="mb-1.5 block text-xs font-medium text-[#8B949E]">최대 개수</label>
          <select
            value={filters.limit || 100}
            onChange={(e) => handleChange('limit', Number(e.target.value))}
            className="w-full rounded border border-[#30363D] bg-[#161B22] px-3 py-2 text-sm text-[#E6EDF3] focus:border-[#58A6FF] focus:outline-none"
          >
            {LIMIT_OPTIONS.map((opt) => (
              <option key={opt.value} value={opt.value}>
                {opt.label}
              </option>
            ))}
          </select>
        </div>

        {/* 거래소 */}
        <div>
          <label className="mb-1.5 block text-xs font-medium text-[#8B949E]">거래소</label>
          <select
            value={filters.exchange || ''}
            onChange={(e) => handleChange('exchange', e.target.value || undefined)}
            className="w-full rounded border border-[#30363D] bg-[#161B22] px-3 py-2 text-sm text-[#E6EDF3] focus:border-[#58A6FF] focus:outline-none"
          >
            {EXCHANGES.map((ex) => (
              <option key={ex.value} value={ex.value}>
                {ex.label}
              </option>
            ))}
          </select>
        </div>

        {/* 섹터 */}
        <div>
          <label className="mb-1.5 block text-xs font-medium text-[#8B949E]">섹터</label>
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

        {/* 시가총액 최소 */}
        <div>
          <label className="mb-1.5 block text-xs font-medium text-[#8B949E]">시가총액 최소 ($B)</label>
          <input
            type="number"
            value={filters.market_cap_more_than ? filters.market_cap_more_than / 1_000_000_000 : ''}
            onChange={(e) => handleChange('market_cap_more_than', e.target.value ? Number(e.target.value) * 1_000_000_000 : undefined)}
            placeholder="예: 10 (= $10B)"
            className="w-full rounded border border-[#30363D] bg-[#161B22] px-3 py-2 text-sm text-[#E6EDF3] placeholder-[#8B949E] focus:border-[#58A6FF] focus:outline-none"
          />
        </div>

        {/* 가격 범위 */}
        <div>
          <label className="mb-1.5 block text-xs font-medium text-[#8B949E]">최소 가격 ($)</label>
          <input
            type="number"
            value={filters.price_more_than || ''}
            onChange={(e) => handleChange('price_more_than', e.target.value ? Number(e.target.value) : undefined)}
            placeholder="예: 10"
            className="w-full rounded border border-[#30363D] bg-[#161B22] px-3 py-2 text-sm text-[#E6EDF3] placeholder-[#8B949E] focus:border-[#58A6FF] focus:outline-none"
          />
        </div>

        <div>
          <label className="mb-1.5 block text-xs font-medium text-[#8B949E]">최대 가격 ($)</label>
          <input
            type="number"
            value={filters.price_lower_than || ''}
            onChange={(e) => handleChange('price_lower_than', e.target.value ? Number(e.target.value) : undefined)}
            placeholder="예: 500"
            className="w-full rounded border border-[#30363D] bg-[#161B22] px-3 py-2 text-sm text-[#E6EDF3] placeholder-[#8B949E] focus:border-[#58A6FF] focus:outline-none"
          />
        </div>

        {/* 배당률 최소 */}
        <div>
          <label className="mb-1.5 block text-xs font-medium text-[#8B949E]">배당률 최소 (%)</label>
          <input
            type="number"
            step="0.1"
            value={filters.dividend_more_than || ''}
            onChange={(e) => handleChange('dividend_more_than', e.target.value ? Number(e.target.value) : undefined)}
            placeholder="예: 2.0"
            className="w-full rounded border border-[#30363D] bg-[#161B22] px-3 py-2 text-sm text-[#E6EDF3] placeholder-[#8B949E] focus:border-[#58A6FF] focus:outline-none"
          />
        </div>

        {/* 거래량 최소 */}
        <div>
          <label className="mb-1.5 block text-xs font-medium text-[#8B949E]">거래량 최소</label>
          <input
            type="number"
            value={filters.volume_more_than || ''}
            onChange={(e) => handleChange('volume_more_than', e.target.value ? Number(e.target.value) : undefined)}
            placeholder="예: 1000000"
            className="w-full rounded border border-[#30363D] bg-[#161B22] px-3 py-2 text-sm text-[#E6EDF3] placeholder-[#8B949E] focus:border-[#58A6FF] focus:outline-none"
          />
        </div>
      </div>
    </div>
  );
}
