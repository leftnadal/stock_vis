'use client';

/**
 * Chain Trace 경로 표시
 */

import type { TraceResponse } from '@/types/chainsight';
import { getRelationStyle } from './graphStyles';

interface TracePathViewProps {
  trace: TraceResponse | null;
  isLoading: boolean;
  onClose: () => void;
}

export default function TracePathView({ trace, isLoading, onClose }: TracePathViewProps) {
  if (isLoading) {
    return (
      <div className="bg-gray-50 border border-gray-200 rounded-lg p-4 animate-pulse">
        <div className="h-4 bg-gray-200 rounded w-1/3 mb-2" />
        <div className="h-12 bg-gray-200 rounded" />
      </div>
    );
  }

  if (!trace) return null;

  if (!trace.found) {
    return (
      <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
        <div className="flex items-center justify-between mb-1">
          <span className="font-medium text-sm">{trace.from} → {trace.to}</span>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600 text-sm">✕</button>
        </div>
        <p className="text-xs text-yellow-700">
          두 종목 간 연결 경로를 찾을 수 없습니다.
        </p>
      </div>
    );
  }

  return (
    <div className="bg-white border border-blue-200 rounded-lg p-4">
      <div className="flex items-center justify-between mb-3">
        <span className="font-medium text-sm">
          {trace.from} → {trace.to} ({trace.path_length}단계)
        </span>
        <button onClick={onClose} className="text-gray-400 hover:text-gray-600 text-sm">✕</button>
      </div>

      {/* 경로 시각화 */}
      <div className="flex items-center gap-1 overflow-x-auto pb-2">
        {trace.path.map((step, i) => {
          const rel = step.next_relation;
          const relStyle = rel ? getRelationStyle(rel.type) : null;

          return (
            <div key={step.node.ticker} className="flex items-center shrink-0">
              {/* 노드 */}
              <div className="px-3 py-1.5 bg-gray-100 rounded-lg text-sm font-medium">
                {step.node.ticker}
              </div>
              {/* 화살표 + 관계 */}
              {rel && (
                <div className="flex flex-col items-center mx-1">
                  <span className="text-[10px] text-gray-500">{relStyle?.label || rel.type}</span>
                  <svg width="32" height="8">
                    <line
                      x1="0" y1="4" x2="28" y2="4"
                      stroke={relStyle?.color || '#6B7280'}
                      strokeWidth={1.5}
                    />
                    <polygon
                      points="28,1 32,4 28,7"
                      fill={relStyle?.color || '#6B7280'}
                    />
                  </svg>
                </div>
              )}
            </div>
          );
        })}
      </div>

      {/* 단계별 설명 */}
      <div className="mt-3 space-y-1.5">
        {trace.path.map((step, i) => {
          if (!step.next_relation) return null;
          const rel = step.next_relation;
          const style = getRelationStyle(rel.type);
          return (
            <div key={i} className="text-xs text-gray-600 flex items-start gap-2">
              <span className="font-medium text-gray-800 shrink-0">Step {i + 1}</span>
              <span>
                {rel.from} →{' '}
                <span style={{ color: style.color }}>{style.label}</span>
                {' → '}{rel.to}
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
}
