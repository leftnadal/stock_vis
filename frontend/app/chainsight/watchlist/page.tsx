'use client';

import { useState } from 'react';
import Link from 'next/link';
import { ArrowLeft } from 'lucide-react';
import { useWatchlist } from '@/hooks/usePathWatchlist';
import PathCard from '@/components/chainsight/PathCard';

const STATUS_OPTIONS = [
  { value: '', label: '전체' },
  { value: 'watching', label: 'Watching' },
  { value: 'active', label: 'Active' },
  { value: 'archived', label: 'Archived' },
  { value: 'resolved', label: 'Resolved' },
];

export default function WatchlistPage() {
  const [statusFilter, setStatusFilter] = useState('');
  const { data: paths, isLoading } = useWatchlist(statusFilter || undefined);

  return (
    <div className="max-w-3xl mx-auto px-4 py-6">
      {/* 헤더 */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-3">
          <Link
            href="/chainsight"
            className="p-1.5 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800 text-gray-500"
          >
            <ArrowLeft className="w-5 h-5" />
          </Link>
          <h1 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
            Path Watchlist
          </h1>
        </div>

        {/* 필터 */}
        <select
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
          className="text-sm border border-gray-300 dark:border-gray-600 rounded-lg px-3 py-1.5 bg-white dark:bg-gray-800 text-gray-700 dark:text-gray-300"
        >
          {STATUS_OPTIONS.map((opt) => (
            <option key={opt.value} value={opt.value}>
              {opt.label}
            </option>
          ))}
        </select>
      </div>

      {/* 리스트 */}
      {isLoading ? (
        <div className="flex items-center justify-center h-40">
          <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-blue-500" />
        </div>
      ) : !paths || paths.length === 0 ? (
        <div className="text-center py-16">
          <p className="text-gray-500 dark:text-gray-400 mb-2">
            아직 저장한 경로가 없어요.
          </p>
          <p className="text-sm text-gray-400 dark:text-gray-500">
            Chain Sight에서 탐색하며 Watch 버튼을 눌러보세요
          </p>
          <Link
            href="/chainsight"
            className="inline-block mt-4 px-4 py-2 rounded-lg bg-blue-500 text-white text-sm hover:bg-blue-600 transition-colors"
          >
            Chain Sight 열기
          </Link>
        </div>
      ) : (
        <div className="space-y-3">
          {paths.map((path) => (
            <PathCard key={path.id} path={path} />
          ))}
        </div>
      )}
    </div>
  );
}
