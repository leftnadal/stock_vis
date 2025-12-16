'use client';

import { useState } from 'react';
import { Loader2 } from 'lucide-react';
import type { BasketAction } from '@/types/rag';
import { DATA_TYPE_INFO } from '@/types/rag';

interface BasketActionCardProps {
  action: BasketAction;
  remainingUnits: number;
  onAdd: (symbol: string, dataTypes: string[]) => Promise<void>;
  onContinueChat?: (message: string) => void;
}

export function BasketActionCard({
  action,
  remainingUnits,
  onAdd,
}: BasketActionCardProps) {
  const [selectedTypes, setSelectedTypes] = useState<string[]>(action.recommended);
  const [isLoading, setIsLoading] = useState(false);
  const [isExiting, setIsExiting] = useState(false);

  const toggleType = (type: string) => {
    setSelectedTypes(prev =>
      prev.includes(type)
        ? prev.filter(t => t !== type)
        : [...prev, type]
    );
  };

  const totalUnits = selectedTypes.reduce((sum, type) => {
    return sum + (DATA_TYPE_INFO[type]?.units || 5);
  }, 0);

  const canAdd = totalUnits <= remainingUnits && selectedTypes.length > 0;

  const handleAdd = async () => {
    if (!canAdd) return;
    setIsLoading(true);
    try {
      await onAdd(action.symbol, selectedTypes);
      setIsExiting(true);
    } finally {
      setIsLoading(false);
    }
  };

  if (isExiting) return null;

  return (
    <div className="bg-slate-800 border border-slate-700 rounded-lg p-3 my-2 text-sm">
      {/* 헤더 */}
      <div className="text-xs text-slate-400 mb-2">
        데이터 추가 제안: <span className="text-blue-400 font-medium">{action.symbol}</span>
        {action.name && <span className="text-slate-500 ml-1">({action.name})</span>}
      </div>

      {/* 데이터 목록 */}
      <div
        className="flex flex-wrap gap-1.5 mb-2 overflow-y-auto"
        style={{ maxHeight: '60px' }}
      >
        {action.available.map(type => {
          const info = DATA_TYPE_INFO[type];
          if (!info) return null;

          const isSelected = selectedTypes.includes(type);
          const wouldExceed = !isSelected && (totalUnits + info.units > remainingUnits);

          return (
            <button
              key={type}
              onClick={() => !wouldExceed && toggleType(type)}
              disabled={wouldExceed && !isSelected}
              className={`
                px-2 py-1 text-xs rounded border transition-colors
                ${isSelected
                  ? 'border-blue-500 bg-blue-500/20 text-blue-300'
                  : wouldExceed
                    ? 'border-slate-700 text-slate-600 cursor-not-allowed'
                    : 'border-slate-600 text-slate-400 hover:border-blue-500'
                }
              `}
            >
              {info.label} ({info.units}u)
            </button>
          );
        })}
      </div>

      {/* 푸터 */}
      <div className="flex items-center justify-between text-xs">
        <span className="text-slate-500">
          {selectedTypes.length}개 선택 · {totalUnits}u / {remainingUnits}u
        </span>
        <button
          onClick={handleAdd}
          disabled={!canAdd || isLoading}
          className={`
            px-3 py-1 rounded text-xs font-medium transition-colors
            ${canAdd && !isLoading
              ? 'bg-blue-600 hover:bg-blue-500 text-white'
              : 'bg-slate-700 text-slate-500 cursor-not-allowed'
            }
          `}
        >
          {isLoading ? (
            <Loader2 className="w-3 h-3 animate-spin" />
          ) : (
            '추가'
          )}
        </button>
      </div>
    </div>
  );
}
