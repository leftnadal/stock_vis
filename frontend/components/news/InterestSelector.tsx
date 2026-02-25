'use client';

import React, { useState } from 'react';
import { Check, Loader2 } from 'lucide-react';
import { useInterestOptions } from '@/hooks/useNews';
import { userInterestService } from '@/services/userInterestService';
import { InterestOption } from '@/types/news';

interface InterestSelectorProps {
  onComplete: () => void;
}

export default function InterestSelector({ onComplete }: InterestSelectorProps) {
  const { data, isLoading } = useInterestOptions();
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [saving, setSaving] = useState(false);

  const toggleOption = (option: InterestOption) => {
    const key = `${option.interest_type}:${option.value}`;
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(key)) {
        next.delete(key);
      } else {
        next.add(key);
      }
      return next;
    });
  };

  const handleSave = async () => {
    if (selected.size === 0) return;
    setSaving(true);
    try {
      const allOptions = [...(data?.themes || []), ...(data?.sectors || [])];
      const interests = Array.from(selected).map((key) => {
        const colonIndex = key.indexOf(':');
        const interest_type = key.substring(0, colonIndex);
        const value = key.substring(colonIndex + 1);
        const option = allOptions.find(
          (o) => o.interest_type === interest_type && o.value === value
        );
        return {
          interest_type,
          value,
          display_name: option?.display_name || value,
        };
      });
      await userInterestService.saveInterests(interests);
      onComplete();
    } catch (error) {
      console.error('Failed to save interests:', error);
    } finally {
      setSaving(false);
    }
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-8">
        <Loader2 className="w-5 h-5 animate-spin text-gray-400" />
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Themes */}
      {data?.themes && data.themes.length > 0 && (
        <div>
          <h4 className="text-xs font-medium text-gray-500 dark:text-gray-400 mb-2 uppercase tracking-wider">
            투자 테마
          </h4>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
            {data.themes.map((theme) => {
              const key = `${theme.interest_type}:${theme.value}`;
              const isSelected = selected.has(key);
              return (
                <button
                  key={key}
                  onClick={() => toggleOption(theme)}
                  className={`relative p-3 rounded-lg border text-left transition-all ${
                    isSelected
                      ? 'border-purple-500 bg-purple-50 dark:bg-purple-900/20 ring-1 ring-purple-500'
                      : 'border-gray-200 dark:border-gray-700 hover:border-gray-300 dark:hover:border-gray-600'
                  }`}
                >
                  {isSelected && (
                    <div className="absolute top-1.5 right-1.5">
                      <Check className="w-3.5 h-3.5 text-purple-500" />
                    </div>
                  )}
                  <div className="text-sm font-medium text-gray-900 dark:text-white mb-1">
                    {theme.display_name}
                  </div>
                  <div className="text-[10px] text-gray-400 dark:text-gray-500">
                    {theme.sample_symbols.join(', ')}
                  </div>
                </button>
              );
            })}
          </div>
        </div>
      )}

      {/* Sectors */}
      {data?.sectors && data.sectors.length > 0 && (
        <div>
          <h4 className="text-xs font-medium text-gray-500 dark:text-gray-400 mb-2 uppercase tracking-wider">
            섹터
          </h4>
          <div className="flex flex-wrap gap-2">
            {data.sectors.map((sector) => {
              const key = `${sector.interest_type}:${sector.value}`;
              const isSelected = selected.has(key);
              return (
                <button
                  key={key}
                  onClick={() => toggleOption(sector)}
                  className={`px-3 py-1.5 rounded-full text-xs font-medium transition-all ${
                    isSelected
                      ? 'bg-purple-500 text-white'
                      : 'bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-600'
                  }`}
                >
                  {sector.display_name}
                </button>
              );
            })}
          </div>
        </div>
      )}

      {/* Save / Skip */}
      <div className="flex items-center justify-between pt-2">
        <span className="text-xs text-gray-400">{selected.size}개 선택</span>
        <div className="flex gap-2">
          <button
            onClick={onComplete}
            className="px-4 py-1.5 text-xs text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200"
          >
            건너뛰기
          </button>
          <button
            onClick={handleSave}
            disabled={selected.size === 0 || saving}
            className="px-4 py-1.5 text-xs font-medium bg-purple-600 text-white rounded-lg hover:bg-purple-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex items-center gap-1.5"
          >
            {saving && <Loader2 className="w-3 h-3 animate-spin" />}
            저장하기
          </button>
        </div>
      </div>
    </div>
  );
}
