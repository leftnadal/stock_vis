'use client';

import { useExplorationStore } from '@/lib/stores/explorationStore';
import type { SectorSummary } from '@/types/chainsight';

interface SectorBarProps {
  sectors: SectorSummary[];
}

export default function SectorBar({ sectors }: SectorBarProps) {
  const { selectedSector, selectSector, reset } = useExplorationStore();

  const handleClick = (sector: string) => {
    if (selectedSector === sector) {
      reset();
    } else {
      selectSector(sector);
    }
  };

  if (!sectors.length) return null;

  return (
    <div className="flex gap-2 overflow-x-auto py-3 px-1 scrollbar-thin">
      {sectors.map((s) => {
        const isSelected = selectedSector === s.sector;
        const isUp = s.pct_change >= 0;
        return (
          <button
            key={s.sector}
            onClick={() => handleClick(s.sector)}
            className={`
              flex-shrink-0 px-4 py-2 rounded-lg text-sm font-medium
              transition-all duration-200 border
              ${isSelected
                ? 'bg-blue-50 dark:bg-blue-900/30 border-blue-400 dark:border-blue-600 text-blue-700 dark:text-blue-300'
                : 'bg-white dark:bg-gray-800 border-gray-200 dark:border-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-750'
              }
            `}
          >
            <span className="block text-xs font-semibold truncate max-w-[120px]">
              {s.sector_display}
            </span>
            <span
              className={`block text-xs mt-0.5 ${
                isUp ? 'text-[#A32D2D]' : 'text-[#185FA5]'
              }`}
            >
              {isUp ? '+' : ''}{s.pct_change}%
            </span>
          </button>
        );
      })}
    </div>
  );
}
