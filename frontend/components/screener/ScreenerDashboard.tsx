'use client';

import React, { useState } from 'react';
import { useMarketBreadth } from '@/hooks/useMarketBreadth';
import { useSectorHeatmap } from '@/hooks/useSectorHeatmap';
import { useScreenerPresets, useDeletePreset } from '@/hooks/useScreenerPresets';
import MarketBreadthCard from './MarketBreadthCard';
import SectorHeatmap from './SectorHeatmap';
import PresetGallery from './PresetGallery';
import type { ScreenerPreset, ScreenerFilters } from '@/types/screener';

interface ScreenerDashboardProps {
  onFiltersApply?: (filters: ScreenerFilters, sector?: string) => void;
}

export default function ScreenerDashboard({ onFiltersApply }: ScreenerDashboardProps) {
  const [selectedDate, setSelectedDate] = useState<string>();

  // Market Breadth
  const {
    data: breadthData,
    isLoading: breadthLoading,
    error: breadthError,
  } = useMarketBreadth(selectedDate);

  // Sector Heatmap
  const {
    data: heatmapData,
    isLoading: heatmapLoading,
    error: heatmapError,
  } = useSectorHeatmap(selectedDate);

  // Screener Presets
  const {
    data: presetsData,
    isLoading: presetsLoading,
    error: presetsError,
  } = useScreenerPresets();

  const deletePresetMutation = useDeletePreset();

  // Handlers
  const handleSectorClick = (sector: string) => {
    if (onFiltersApply) {
      // 섹터 필터만 적용
      onFiltersApply({ sectors: [sector] }, sector);
    }
  };

  const handlePresetClick = (preset: ScreenerPreset) => {
    if (onFiltersApply) {
      // 프리셋 필터 적용
      onFiltersApply(preset.filters_json);
    }
  };

  const handleDeletePreset = async (presetId: number) => {
    if (confirm('이 프리셋을 삭제하시겠습니까?')) {
      try {
        await deletePresetMutation.mutateAsync(presetId);
      } catch (error) {
        console.error('프리셋 삭제 실패:', error);
        alert('프리셋 삭제에 실패했습니다.');
      }
    }
  };

  // 시스템 프리셋과 사용자 프리셋 분리
  const allPresets = presetsData?.data.presets || [];
  const systemPresets = allPresets.filter((p) => p.is_system);
  const userPresets = allPresets.filter((p) => !p.is_system);

  return (
    <div className="space-y-6">
      {/* Row 1: Market Breadth + Sector Heatmap */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <MarketBreadthCard
          data={breadthData?.data!}
          isLoading={breadthLoading}
          error={breadthError}
        />
        <div>
          <SectorHeatmap
            sectors={heatmapData?.data.sectors || []}
            date={heatmapData?.data.date}
            isLoading={heatmapLoading}
            error={heatmapError}
            onSectorClick={handleSectorClick}
          />
        </div>
      </div>

      {/* Row 2: Preset Gallery */}
      <PresetGallery
        presets={systemPresets}
        userPresets={userPresets}
        isLoading={presetsLoading}
        error={presetsError}
        onPresetClick={handlePresetClick}
        onDeletePreset={handleDeletePreset}
      />
    </div>
  );
}
