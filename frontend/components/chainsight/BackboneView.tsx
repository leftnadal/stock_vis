'use client';

/**
 * RC-C-1 backbone 뷰 (활성 해자 부분그래프).
 * 좌: 중심성 top-N 리스트(막대) · 우: 그래프(θ≥0.85 실선) · 하단: 엣지 선택 근거 바.
 * data-guide="chainsight.backbone" 루트 앵커(콘텐츠는 GUIDE 트랙 등재 — 3-3).
 */

import { useState } from 'react';
import { useBackbone } from '@/hooks/useBackbone';
import type { BackboneEdge } from '@/types/backbone';
import BackboneGraph, { edgeKey } from './BackboneGraph';

interface BackboneViewProps {
  // ForceGraph2D 주입(page 에서 dynamic ssr:false) — 테스트 용이(GraphCanvas 선례).
  ForceGraph2D: React.ComponentType<Record<string, unknown>>;
}

const TRUST_BADGE: Record<string, { label: string; cls: string }> = {
  confirmed: { label: '확정', cls: 'bg-green-500/15 text-green-400 border-green-500/30' },
  probable: { label: '유력', cls: 'bg-blue-500/15 text-blue-400 border-blue-500/30' },
};

export default function BackboneView({ ForceGraph2D }: BackboneViewProps) {
  const { data, isLoading, isError } = useBackbone(20);
  const [selectedEdge, setSelectedEdge] = useState<BackboneEdge | null>(null);

  if (isLoading) {
    return (
      <div className="flex h-[400px] items-center justify-center" data-guide="chainsight.backbone">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500" />
      </div>
    );
  }

  if (isError || !data) {
    return (
      <div className="p-6 text-sm text-red-400" data-guide="chainsight.backbone">
        백본 데이터를 불러오지 못했습니다.
      </div>
    );
  }

  const { top_symbols, edges, graph_size, theta } = data;
  const maxPr = Math.max(1e-9, ...top_symbols.map((s) => s.pagerank));
  const isEmpty = top_symbols.length === 0;

  return (
    <div className="p-6" data-guide="chainsight.backbone">
      <div className="mb-4">
        <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100">관계 백본</h1>
        <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
          활성 해자(확정·유력) 부분그래프의 중심성 — {graph_size.nodes}개 노드 / {graph_size.edges}개 엣지
        </p>
      </div>

      {isEmpty ? (
        <div className="py-16 text-center text-sm text-gray-400" data-testid="backbone-empty">
          활성 해자 관계가 없습니다.
        </div>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-[320px_1fr] gap-4">
          {/* 좌: 중심성 top-N 막대 리스트 */}
          <div data-testid="backbone-toplist" className="space-y-1.5">
            <div className="text-xs font-semibold text-gray-500 uppercase mb-2">중심성 상위</div>
            {top_symbols.map((s, i) => (
              <div key={s.symbol} className="flex items-center gap-2 text-sm">
                <span className="w-5 text-right text-gray-400 tabular-nums">{i + 1}</span>
                <span className="w-14 font-mono font-semibold text-gray-800 dark:text-gray-100">
                  {s.symbol}
                </span>
                <div className="flex-1 h-4 bg-gray-100 dark:bg-gray-800 rounded overflow-hidden">
                  <div
                    className="h-full bg-blue-500/70"
                    style={{ width: `${(s.pagerank / maxPr) * 100}%` }}
                  />
                </div>
                <span className="w-10 text-right text-xs text-gray-400 tabular-nums">
                  d{s.degree}
                </span>
              </div>
            ))}
          </div>

          {/* 우: 그래프 */}
          <div
            data-testid="backbone-graph"
            className="border border-gray-200 dark:border-gray-800 rounded-lg overflow-hidden bg-[#0D1117] min-h-[400px]"
          >
            <BackboneGraph
              topSymbols={top_symbols}
              edges={edges}
              theta={theta}
              width={720}
              height={420}
              selectedEdgeKey={selectedEdge ? edgeKey(selectedEdge) : null}
              onEdgeSelect={setSelectedEdge}
              ForceGraph2D={ForceGraph2D}
            />
          </div>
        </div>
      )}

      {/* 하단: 엣지 선택 근거 바 */}
      {selectedEdge && (
        <div
          data-testid="backbone-evidence-bar"
          className="mt-4 flex flex-wrap items-center gap-x-6 gap-y-2 rounded-lg border border-gray-200 dark:border-gray-800 bg-gray-50 dark:bg-gray-900 px-4 py-3 text-sm"
        >
          <span className="font-mono font-semibold text-gray-800 dark:text-gray-100">
            {selectedEdge.symbol_a} — {selectedEdge.symbol_b}
          </span>
          <span className="text-gray-500">
            점수 <span className="font-semibold text-gray-800 dark:text-gray-100">{selectedEdge.score.toFixed(2)}</span>
          </span>
          <span className="text-gray-500">유형 <span className="text-gray-800 dark:text-gray-100">{selectedEdge.category}</span></span>
          <span className="text-gray-500">근거 <span className="text-gray-800 dark:text-gray-100">{selectedEdge.evidence_count}</span></span>
          <span className="text-gray-500">재관측 <span className="text-gray-800 dark:text-gray-100">{selectedEdge.observed_count}</span></span>
          <span
            className={`px-2 py-0.5 rounded border text-xs ${
              TRUST_BADGE[selectedEdge.trust]?.cls ?? 'bg-gray-500/15 text-gray-400 border-gray-500/30'
            }`}
          >
            {TRUST_BADGE[selectedEdge.trust]?.label ?? selectedEdge.trust}
          </span>
        </div>
      )}
    </div>
  );
}
