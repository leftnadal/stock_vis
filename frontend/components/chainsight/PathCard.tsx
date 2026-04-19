'use client';

import { useRouter } from 'next/navigation';
import { RefreshCw, Maximize2, MoreHorizontal, Archive, CheckCircle } from 'lucide-react';
import { useState } from 'react';
import type { SavedPathListItem } from '@/types/pathWatchlist';
import { PATH_STATUS_BADGE, formatRelativeTime } from '@/lib/utils/pathStatus';
import { useRecheckPath, useArchivePath, useResolvePath } from '@/hooks/usePathWatchlist';

interface PathCardProps {
  path: SavedPathListItem;
}

export default function PathCard({ path }: PathCardProps) {
  const router = useRouter();
  const [menuOpen, setMenuOpen] = useState(false);
  const recheckMutation = useRecheckPath();
  const archiveMutation = useArchivePath();
  const resolveMutation = useResolvePath();

  const badge = PATH_STATUS_BADGE[path.status];
  const summaryNodes = path.summary_path || [];
  const extraCount = path.path_length - summaryNodes.length;

  const handleCardClick = () => {
    router.push(`/chainsight/watchlist/${path.id}`);
  };

  return (
    <div
      className="border border-gray-200 dark:border-gray-700 rounded-lg p-4 hover:border-blue-300 dark:hover:border-blue-600 transition-colors cursor-pointer bg-white dark:bg-gray-800"
      onClick={handleCardClick}
    >
      {/* 경로 체인 */}
      <div className="flex items-center gap-1 text-sm font-medium text-gray-900 dark:text-gray-100 mb-2">
        {summaryNodes.map((ticker, i) => (
          <span key={ticker} className="flex items-center gap-1">
            {i > 0 && <span className="text-gray-400">&rarr;</span>}
            <span>{ticker}</span>
          </span>
        ))}
        {extraCount > 0 && (
          <span className="text-gray-400 text-xs ml-1">(+{extraCount})</span>
        )}
      </div>

      {/* path_signature 태그 */}
      {path.path_signature && (
        <div className="text-xs text-gray-500 dark:text-gray-400 mb-2">
          {path.path_signature}
        </div>
      )}

      {/* status 뱃지 + 시간 */}
      <div className="flex items-center gap-2 mb-3">
        <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium ${badge.bg} ${badge.color}`}>
          <span className="w-1.5 h-1.5 rounded-full bg-current" />
          {badge.label}
        </span>
        <span className="text-xs text-gray-400">
          {formatRelativeTime(path.updated_at)}
        </span>
        {path.recheck_count > 0 && (
          <span className="text-xs text-gray-400">
            · Recheck {path.recheck_count}회
          </span>
        )}
      </div>

      {/* headline */}
      {path.latest_headline && (
        <p className="text-xs text-gray-500 dark:text-gray-400 mb-3 line-clamp-1">
          {path.latest_headline}
        </p>
      )}

      {/* Quick actions */}
      <div className="flex items-center gap-2" onClick={(e) => e.stopPropagation()}>
        <button
          onClick={() => recheckMutation.mutate(path.id)}
          disabled={recheckMutation.isPending || path.status === 'archived' || path.status === 'resolved'}
          className="flex items-center gap-1 px-2.5 py-1 rounded text-xs font-medium bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-300 hover:bg-blue-50 dark:hover:bg-blue-900/20 hover:text-blue-600 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
        >
          <RefreshCw className={`w-3 h-3 ${recheckMutation.isPending ? 'animate-spin' : ''}`} />
          Recheck
        </button>

        <button
          onClick={() => router.push(`/chainsight/watchlist/${path.id}`)}
          className="flex items-center gap-1 px-2.5 py-1 rounded text-xs font-medium bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-300 hover:bg-blue-50 dark:hover:bg-blue-900/20 hover:text-blue-600 transition-colors"
        >
          <Maximize2 className="w-3 h-3" />
          열기
        </button>

        <div className="ml-auto relative">
          <button
            onClick={() => setMenuOpen(!menuOpen)}
            className="p-1 rounded hover:bg-gray-100 dark:hover:bg-gray-700 text-gray-400"
          >
            <MoreHorizontal className="w-4 h-4" />
          </button>

          {menuOpen && (
            <div className="absolute right-0 top-8 w-36 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg shadow-lg z-10 py-1">
              <button
                onClick={() => { archiveMutation.mutate(path.id); setMenuOpen(false); }}
                disabled={path.status === 'archived'}
                className="w-full flex items-center gap-2 px-3 py-2 text-xs text-gray-600 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700 disabled:opacity-40"
              >
                <Archive className="w-3.5 h-3.5" /> Archive
              </button>
              <button
                onClick={() => { resolveMutation.mutate(path.id); setMenuOpen(false); }}
                disabled={path.status === 'resolved'}
                className="w-full flex items-center gap-2 px-3 py-2 text-xs text-gray-600 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700 disabled:opacity-40"
              >
                <CheckCircle className="w-3.5 h-3.5" /> Resolve
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
