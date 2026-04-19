'use client';

import { useState } from 'react';
import Link from 'next/link';
import {
  ArrowLeft, RefreshCw, Archive, CheckCircle,
  ChevronRight, ArrowUpRight, ArrowDownRight, Minus,
} from 'lucide-react';
import type {
  SavedPathDetail, RecheckResponse, ExpandCandidate, AlternativesResponse,
} from '@/types/pathWatchlist';
import {
  useRecheckPath, useExpandPath, useAlternatives,
  useArchivePath, useResolvePath,
} from '@/hooks/usePathWatchlist';
import { PATH_STATUS_BADGE } from '@/lib/utils/pathStatus';

const REL_LABELS: Record<string, string> = {
  SUPPLIES_TO: 'supply',
  CUSTOMER_OF: 'customer',
  COMPETES_WITH: 'compete',
  PEER_OF: 'peer',
  CO_MENTIONED: 'co-mention',
  PRICE_CORRELATED: 'corr',
  HAS_THEME: 'theme',
};

interface FullPathViewProps {
  path: SavedPathDetail;
}

export default function FullPathView({ path: initialPath }: FullPathViewProps) {
  const [recheckResult, setRecheckResult] = useState<RecheckResponse | null>(null);
  const [expandCandidates, setExpandCandidates] = useState<ExpandCandidate[] | null>(null);
  const [altResult, setAltResult] = useState<AlternativesResponse | null>(null);
  const [selectedNode, setSelectedNode] = useState<string | null>(null);
  const [currentStatus, setCurrentStatus] = useState(initialPath.status);
  const [recheckCount, setRecheckCount] = useState(initialPath.recheck_count);

  const recheckMutation = useRecheckPath();
  const expandMutation = useExpandPath();
  const altMutation = useAlternatives();
  const archiveMutation = useArchivePath();
  const resolveMutation = useResolvePath();

  const badge = PATH_STATUS_BADGE[currentStatus];
  const isTerminal = currentStatus === 'archived' || currentStatus === 'resolved';

  const headline = recheckResult?.headline
    ?? initialPath.why_now_snapshot?.headline
    ?? '';

  const handleRecheck = () => {
    recheckMutation.mutate(initialPath.id, {
      onSuccess: (data) => {
        setRecheckResult(data);
        setCurrentStatus(data.status as typeof currentStatus);
        setRecheckCount(data.recheck_count);
      },
    });
  };

  const handleExpand = () => {
    expandMutation.mutate(
      { id: initialPath.id },
      { onSuccess: (data) => setExpandCandidates(data.candidates) },
    );
  };

  const handleNodeClick = (ticker: string) => {
    if (isTerminal) return;
    setSelectedNode(ticker === selectedNode ? null : ticker);
    setAltResult(null);
  };

  const handleAlternatives = (ticker: string) => {
    altMutation.mutate(
      { id: initialPath.id, targetTicker: ticker },
      { onSuccess: (data) => setAltResult(data) },
    );
  };

  const handleArchive = () => {
    archiveMutation.mutate(initialPath.id, {
      onSuccess: () => setCurrentStatus('archived'),
    });
  };

  const handleResolve = () => {
    resolveMutation.mutate(initialPath.id, {
      onSuccess: () => setCurrentStatus('resolved'),
    });
  };

  return (
    <div className="max-w-3xl mx-auto px-4 py-6 space-y-6">
      {/* Header */}
      <div className="flex items-center gap-3">
        <Link
          href="/chainsight/watchlist"
          className="p-1.5 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800 text-gray-500"
        >
          <ArrowLeft className="w-5 h-5" />
        </Link>
        <div>
          <h1 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
            경로 상세
          </h1>
          {initialPath.path_signature && (
            <p className="text-xs text-gray-500 dark:text-gray-400">
              {initialPath.path_signature}
            </p>
          )}
        </div>
        <span className={`ml-auto inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-medium ${badge.bg} ${badge.color}`}>
          <span className="w-1.5 h-1.5 rounded-full bg-current" />
          {badge.label}
        </span>
      </div>

      {/* Recheck Result Section */}
      {headline && (
        <div className="bg-gray-50 dark:bg-gray-800/50 rounded-lg p-4 space-y-3">
          <div className="flex items-center gap-2">
            <span className="text-sm font-medium text-gray-700 dark:text-gray-300">
              Recheck 결과
            </span>
            <span className="text-xs text-gray-400">
              Recheck {recheckCount}회
            </span>
          </div>

          <p className="text-sm text-gray-800 dark:text-gray-200 font-medium">
            {headline}
          </p>

          {recheckResult && (
            <div className="space-y-1">
              {recheckResult.strengthened.map((e, i) => (
                <div key={`s-${i}`} className="flex items-center gap-2 text-xs text-green-600 dark:text-green-400">
                  <ArrowUpRight className="w-3.5 h-3.5" />
                  <span>{e.from} &rarr; {e.to}: {e.old_score ?? '?'} &rarr; {e.new_score ?? '?'} (strengthened)</span>
                </div>
              ))}
              {recheckResult.weakened.map((e, i) => (
                <div key={`w-${i}`} className="flex items-center gap-2 text-xs text-red-500 dark:text-red-400">
                  <ArrowDownRight className="w-3.5 h-3.5" />
                  <span>{e.from} &rarr; {e.to}: {e.old_score ?? '?'} &rarr; {e.new_score ?? '?'} (weakened)</span>
                </div>
              ))}
              {recheckResult.broken_edges.map((e, i) => (
                <div key={`b-${i}`} className="flex items-center gap-2 text-xs text-gray-500">
                  <Minus className="w-3.5 h-3.5" />
                  <span>{e.from} &rarr; {e.to}: broken</span>
                </div>
              ))}

              {recheckResult.suggested_action !== 'none' && (
                <div className="mt-2 p-2 bg-blue-50 dark:bg-blue-900/20 rounded text-xs text-blue-700 dark:text-blue-300">
                  추천: <strong>{recheckResult.suggested_action}</strong> &mdash; {recheckResult.suggested_reason}
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {/* Path Node Chain */}
      <div>
        <h2 className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-3">
          경로 노드
        </h2>
        <div className="flex items-center gap-1 overflow-x-auto py-2 scrollbar-thin">
          {initialPath.path_nodes.map((ticker, i) => {
            const edge = initialPath.edge_snapshot?.[i] ?? null;
            const isSelected = selectedNode === ticker;

            return (
              <div key={`${ticker}-${i}`} className="flex items-center gap-1 flex-shrink-0">
                {/* Edge label */}
                {i > 0 && edge && (
                  <span className="text-[10px] text-gray-400 dark:text-gray-500 px-0.5 whitespace-nowrap">
                    &mdash;{REL_LABELS[edge.type ?? ''] || edge.type || ''}&mdash;
                  </span>
                )}
                {i > 0 && !edge && (
                  <span className="text-gray-300 dark:text-gray-600 px-0.5">&mdash;&mdash;</span>
                )}

                {/* Node */}
                <button
                  onClick={() => handleNodeClick(ticker)}
                  className={`
                    px-3 py-1.5 rounded-full text-xs font-medium transition-all
                    ${isSelected
                      ? 'bg-blue-500 text-white shadow-md ring-2 ring-blue-300'
                      : 'bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-600'
                    }
                  `}
                >
                  {ticker}
                </button>
              </div>
            );
          })}
        </div>

        {/* Selected node -> Alternatives */}
        {selectedNode && !isTerminal && (
          <div className="mt-3 p-3 bg-gray-50 dark:bg-gray-800/50 rounded-lg">
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs font-medium text-gray-600 dark:text-gray-400">
                {selectedNode} 대신 다른 노드는?
              </span>
              <button
                onClick={() => handleAlternatives(selectedNode)}
                disabled={altMutation.isPending}
                className="text-xs px-2.5 py-1 rounded bg-blue-500 text-white hover:bg-blue-600 disabled:opacity-50"
              >
                {altMutation.isPending ? '탐색 중...' : 'Alternatives 찾기'}
              </button>
            </div>

            {altResult && altResult.target_ticker === selectedNode && (
              <div className="space-y-2 mt-2">
                {altResult.alternatives.length === 0 ? (
                  <p className="text-xs text-gray-400">조건에 맞는 대안이 없습니다.</p>
                ) : (
                  altResult.alternatives.map((alt) => (
                    <div
                      key={alt.ticker}
                      className="flex items-center justify-between p-2 bg-white dark:bg-gray-800 rounded border border-gray-200 dark:border-gray-700"
                    >
                      <div>
                        <span className="text-sm font-medium text-gray-800 dark:text-gray-200">
                          {alt.ticker}
                        </span>
                        <span className="text-xs text-gray-500 ml-2">{alt.name}</span>
                        <p className="text-xs text-gray-400 mt-0.5">{alt.why_summary}</p>
                      </div>
                      <span className="text-xs text-blue-500 font-medium">
                        overlap {alt.overlap_count}
                      </span>
                    </div>
                  ))
                )}
              </div>
            )}
          </div>
        )}
      </div>

      {/* Expand Candidates */}
      <div>
        <div className="flex items-center justify-between mb-3">
          <h2 className="text-sm font-medium text-gray-700 dark:text-gray-300">
            Expand 후보
          </h2>
          {!isTerminal && (
            <button
              onClick={handleExpand}
              disabled={expandMutation.isPending}
              className="text-xs px-2.5 py-1 rounded bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-300 hover:bg-blue-50 hover:text-blue-600 disabled:opacity-50"
            >
              {expandMutation.isPending ? '탐색 중...' : '후보 찾기'}
            </button>
          )}
        </div>

        {expandCandidates && (
          <div className="space-y-2">
            {expandCandidates.length === 0 ? (
              <p className="text-xs text-gray-400">확장 가능한 후보가 없습니다.</p>
            ) : (
              expandCandidates.slice(0, 5).map((cand) => (
                <div
                  key={cand.ticker}
                  className="flex items-center justify-between p-3 bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700"
                >
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="text-sm font-medium text-gray-800 dark:text-gray-200">
                        {cand.ticker}
                      </span>
                      <span className="text-xs text-gray-500">{cand.name}</span>
                      {cand.relation_type && (
                        <span className="text-[10px] px-1.5 py-0.5 bg-gray-100 dark:bg-gray-700 rounded text-gray-500">
                          {cand.relation_type}
                        </span>
                      )}
                    </div>
                    <p className="text-xs text-gray-400 mt-0.5">{cand.why_summary}</p>
                  </div>
                  <div className="text-right">
                    {cand.truth_score != null && (
                      <span className="text-sm font-semibold text-blue-500">
                        {cand.truth_score}점
                      </span>
                    )}
                  </div>
                </div>
              ))
            )}
          </div>
        )}
      </div>

      {/* Action Button Bar */}
      <div className="flex items-center gap-2 pt-4 border-t border-gray-200 dark:border-gray-700">
        <button
          onClick={handleRecheck}
          disabled={recheckMutation.isPending || isTerminal}
          className="flex items-center gap-1.5 px-4 py-2 rounded-lg text-sm font-medium bg-blue-500 text-white hover:bg-blue-600 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
        >
          <RefreshCw className={`w-4 h-4 ${recheckMutation.isPending ? 'animate-spin' : ''}`} />
          Recheck
        </button>

        <button
          onClick={handleExpand}
          disabled={expandMutation.isPending || isTerminal}
          className="flex items-center gap-1.5 px-4 py-2 rounded-lg text-sm font-medium bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-600 disabled:opacity-40 transition-colors"
        >
          <ChevronRight className="w-4 h-4" />
          Expand
        </button>

        <div className="ml-auto flex items-center gap-2">
          <button
            onClick={handleArchive}
            disabled={archiveMutation.isPending || currentStatus === 'archived'}
            className="flex items-center gap-1.5 px-3 py-2 rounded-lg text-sm text-gray-500 hover:bg-gray-100 dark:hover:bg-gray-800 disabled:opacity-40 transition-colors"
          >
            <Archive className="w-4 h-4" />
            Archive
          </button>
          <button
            onClick={handleResolve}
            disabled={resolveMutation.isPending || currentStatus === 'resolved'}
            className="flex items-center gap-1.5 px-3 py-2 rounded-lg text-sm text-gray-500 hover:bg-gray-100 dark:hover:bg-gray-800 disabled:opacity-40 transition-colors"
          >
            <CheckCircle className="w-4 h-4" />
            Resolve
          </button>
        </div>
      </div>
    </div>
  );
}
