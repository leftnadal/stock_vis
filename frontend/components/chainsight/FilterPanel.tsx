'use client';

/**
 * 프로 투자자용 필터 패널
 * 관계 타입, Depth, 섹터 필터링
 */

import { useState } from 'react';
import { RELATION_STYLES } from './graphStyles';

export interface FilterState {
  relTypes: Set<string>;
  depth: number;
}

interface FilterPanelProps {
  filters: FilterState;
  onFiltersChange: (filters: FilterState) => void;
  onClose: () => void;
}

const REL_TYPE_OPTIONS = [
  { key: 'PEER_OF', label: '경쟁사' },
  { key: 'SUPPLIES_TO', label: '공급' },
  { key: 'CUSTOMER_OF', label: '고객' },
  { key: 'COMPETES_WITH', label: '경쟁' },
  { key: 'CO_MENTIONED', label: '뉴스 동시출현' },
  { key: 'HAS_THEME', label: '테마' },
  { key: 'BELONGS_TO_SECTOR', label: '섹터' },
  { key: 'BELONGS_TO_INDUSTRY', label: '산업' },
  { key: 'RELATED_TO', label: '관련' },
];

export default function FilterPanel({ filters, onFiltersChange, onClose }: FilterPanelProps) {
  const [local, setLocal] = useState<FilterState>({
    relTypes: new Set(filters.relTypes),
    depth: filters.depth,
  });

  const toggleRelType = (key: string) => {
    const next = new Set(local.relTypes);
    if (next.has(key)) next.delete(key);
    else next.add(key);
    setLocal({ ...local, relTypes: next });
  };

  const selectAll = () => {
    setLocal({ ...local, relTypes: new Set(REL_TYPE_OPTIONS.map(o => o.key)) });
  };

  const clearAll = () => {
    setLocal({ ...local, relTypes: new Set() });
  };

  const apply = () => {
    onFiltersChange(local);
    onClose();
  };

  const reset = () => {
    const defaults: FilterState = {
      relTypes: new Set(REL_TYPE_OPTIONS.map(o => o.key)),
      depth: 1,
    };
    setLocal(defaults);
    onFiltersChange(defaults);
    onClose();
  };

  return (
    <div className="absolute top-12 right-4 z-50 w-72 bg-white border border-gray-200 rounded-xl shadow-lg p-4 space-y-4">
      <div className="flex items-center justify-between">
        <h4 className="text-sm font-semibold">필터</h4>
        <button onClick={onClose} className="text-gray-400 hover:text-gray-600 text-sm">✕</button>
      </div>

      {/* 관계 타입 */}
      <div>
        <div className="flex items-center justify-between mb-2">
          <span className="text-xs text-gray-500 font-medium">관계 타입</span>
          <div className="flex gap-2 text-xs">
            <button onClick={selectAll} className="text-blue-500 hover:underline">전체</button>
            <button onClick={clearAll} className="text-gray-400 hover:underline">해제</button>
          </div>
        </div>
        <div className="space-y-1.5">
          {REL_TYPE_OPTIONS.map(opt => {
            const style = RELATION_STYLES[opt.key];
            return (
              <label key={opt.key} className="flex items-center gap-2 cursor-pointer text-sm">
                <input
                  type="checkbox"
                  checked={local.relTypes.has(opt.key)}
                  onChange={() => toggleRelType(opt.key)}
                  className="rounded border-gray-300"
                />
                {style && (
                  <span
                    className="inline-block w-3 h-3 rounded-full"
                    style={{ backgroundColor: style.color }}
                  />
                )}
                <span>{opt.label}</span>
              </label>
            );
          })}
        </div>
      </div>

      {/* Depth */}
      <div>
        <span className="text-xs text-gray-500 font-medium">Depth</span>
        <div className="flex gap-2 mt-1">
          {[1, 2, 3].map(d => (
            <button
              key={d}
              onClick={() => setLocal({ ...local, depth: d })}
              className={`flex-1 py-1.5 text-sm rounded-lg border ${
                local.depth === d
                  ? 'border-gray-800 bg-gray-800 text-white'
                  : 'border-gray-200 text-gray-600 hover:bg-gray-50'
              }`}
            >
              {d}
            </button>
          ))}
        </div>
      </div>

      {/* 액션 */}
      <div className="flex gap-2 pt-2 border-t border-gray-100">
        <button
          onClick={reset}
          className="flex-1 py-2 text-sm rounded-lg border border-gray-200 text-gray-600 hover:bg-gray-50"
        >
          초기화
        </button>
        <button
          onClick={apply}
          className="flex-1 py-2 text-sm rounded-lg bg-gray-800 text-white hover:bg-gray-700"
        >
          적용
        </button>
      </div>
    </div>
  );
}
