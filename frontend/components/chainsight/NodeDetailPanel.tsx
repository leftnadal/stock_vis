'use client';

/**
 * 선택된 노드 상세 패널 (우측)
 * CTA: 가설 생성, Watchlist, Validation, 여기서 탐색, 경로 찾기
 */

import Link from 'next/link';
import type { GraphNode } from '@/types/chainsight';

interface NodeDetailPanelProps {
  node: GraphNode | null;
  centerSymbol: string;
  relationLabel?: string;
  onExploreHere: (ticker: string) => void;
  onStartTrace: (to: string) => void;
}

export default function NodeDetailPanel({
  node,
  centerSymbol,
  relationLabel,
  onExploreHere,
  onStartTrace,
}: NodeDetailPanelProps) {
  if (!node) {
    return (
      <div className="p-4 text-sm text-gray-400">
        노드를 클릭하면 상세 정보가 표시됩니다.
      </div>
    );
  }

  const isCenter = node.ticker === centerSymbol;

  return (
    <div className="p-4 space-y-4">
      {/* 종목 정보 */}
      <div>
        <div className="flex items-center justify-between">
          <h3 className="text-lg font-bold">{node.ticker}</h3>
          <Link
            href={`/stocks/${node.ticker}`}
            className="text-xs text-blue-500 hover:underline"
          >
            종목 상세 ↗
          </Link>
        </div>
        <p className="text-sm text-gray-600 mt-0.5">{node.name}</p>
        {relationLabel && !isCenter && (
          <span className="inline-block mt-1 px-2 py-0.5 text-xs rounded-full bg-gray-100 text-gray-700">
            {relationLabel}
          </span>
        )}
      </div>

      {/* 프로파일 요약 */}
      <div className="text-xs space-y-1 text-gray-600">
        {node.sector && (
          <div className="flex justify-between">
            <span>섹터</span>
            <span className="font-medium text-gray-800">{node.sector}</span>
          </div>
        )}
        {node.industry && (
          <div className="flex justify-between">
            <span>산업</span>
            <span className="font-medium text-gray-800">{node.industry}</span>
          </div>
        )}
        {node.growth_stage && (
          <div className="flex justify-between">
            <span>GrowthStage</span>
            <span className="font-medium text-gray-800">{node.growth_stage}</span>
          </div>
        )}
        {node.capital_dna && (
          <div className="flex justify-between">
            <span>CapitalDNA</span>
            <span className="font-medium text-gray-800">{node.capital_dna}</span>
          </div>
        )}
      </div>

      {/* CTA 버튼 */}
      {!isCenter && (
        <div className="space-y-2 pt-2 border-t border-gray-100">
          <Link
            href={`/thesis/new?symbol=${node.ticker}&from=${centerSymbol}`}
            className="block w-full text-center text-sm py-2 px-3 rounded-lg bg-blue-600 text-white hover:bg-blue-700 transition"
          >
            가설 생성
          </Link>
          <Link
            href={`/stocks/${node.ticker}?tab=validation`}
            className="block w-full text-center text-sm py-2 px-3 rounded-lg bg-gray-100 text-gray-700 hover:bg-gray-200 transition"
          >
            Validation 보기
          </Link>
          <button
            onClick={() => onExploreHere(node.ticker)}
            className="w-full text-sm py-2 px-3 rounded-lg bg-gray-100 text-gray-700 hover:bg-gray-200 transition"
          >
            여기서 탐색 시작
          </button>
          <button
            onClick={() => onStartTrace(node.ticker)}
            className="w-full text-sm py-2 px-3 rounded-lg bg-gray-100 text-gray-700 hover:bg-gray-200 transition"
          >
            {centerSymbol} → {node.ticker} 경로 찾기
          </button>
        </div>
      )}
    </div>
  );
}
