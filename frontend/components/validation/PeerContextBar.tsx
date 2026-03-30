'use client';

import { useState } from 'react';
import { ChevronDown, ChevronUp, Info } from 'lucide-react';
import type { PeerInfo } from '@/types/validation';

const CONFIDENCE_BADGE = {
  high: { label: '높음', color: 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400' },
  medium: { label: '보통', color: 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400' },
  low: { label: '낮음', color: 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400' },
  limited: { label: '제한적', color: 'bg-gray-100 text-gray-700 dark:bg-gray-700 dark:text-gray-300' },
} as const;

const SIZE_LABELS: Record<string, string> = {
  mega: 'Mega Cap',
  large: 'Large Cap',
  mid: 'Mid Cap',
  small: 'Small Cap',
};

interface Props {
  peerInfo: PeerInfo;
  fiscalYear: number;
}

export default function PeerContextBar({ peerInfo, fiscalYear }: Props) {
  const [expanded, setExpanded] = useState(false);

  const confidenceKey = peerInfo.confidence as keyof typeof CONFIDENCE_BADGE;
  const badge = CONFIDENCE_BADGE[confidenceKey] || CONFIDENCE_BADGE.low;

  return (
    <div className="bg-blue-50 dark:bg-blue-900/20 rounded-lg p-4">
      {/* 메인 라인 */}
      <div className="flex flex-wrap items-center gap-x-4 gap-y-2 text-sm">
        <span className="font-medium text-gray-900 dark:text-white">
          📊 비교 기준: {peerInfo.basis_description} {peerInfo.peer_count}개
        </span>
        <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${badge.color}`}>
          비교 신뢰도: {badge.label}
        </span>
        <span className="text-gray-500 dark:text-gray-400">
          {SIZE_LABELS[peerInfo.size_bucket] || peerInfo.size_bucket}
        </span>
        <span className="text-gray-500 dark:text-gray-400">
          데이터 기준: {fiscalYear} FY
        </span>
      </div>

      {/* 안내문 */}
      <div className="flex items-center gap-1.5 mt-2 text-xs text-gray-500 dark:text-gray-400">
        <Info className="w-3.5 h-3.5 flex-shrink-0" />
        <span>과거 연도 차트도 현재 peer 기준으로 계산됩니다</span>
      </div>

      {/* Peer 목록 접기/펼치기 */}
      {peerInfo.top_peers.length > 0 && (
        <div className="mt-3">
          <button
            onClick={() => setExpanded(!expanded)}
            className="flex items-center gap-1 text-xs text-blue-600 dark:text-blue-400 hover:underline"
          >
            peer 목록 {expanded ? '접기' : '보기'}
            {expanded ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
          </button>
          {expanded && (
            <div className="mt-2 flex flex-wrap gap-1.5">
              {peerInfo.top_peers.map((sym) => (
                <span
                  key={sym}
                  className="inline-flex px-2 py-0.5 bg-white dark:bg-gray-700 rounded text-xs text-gray-700 dark:text-gray-300 border border-gray-200 dark:border-gray-600"
                >
                  {sym}
                </span>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
