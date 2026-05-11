'use client';

import { formatDistanceToNow, parseISO } from 'date-fns';
import { ko } from 'date-fns/locale';
import { Database } from 'lucide-react';
import { useNeo4jStatus } from '@/hooks/useNewsPipeline';

function formatRelativeTime(isoString: string | null): string {
  if (!isoString) return '없음';
  try {
    return formatDistanceToNow(parseISO(isoString), { addSuffix: true, locale: ko });
  } catch {
    return isoString;
  }
}

interface StatRowProps {
  label: string;
  value: string | number;
  valueClass?: string;
}

function StatRow({ label, value, valueClass = 'text-gray-200' }: StatRowProps) {
  return (
    <div className="flex items-center justify-between py-1.5 border-b border-gray-700 last:border-0">
      <span className="text-xs text-gray-500">{label}</span>
      <span className={`text-sm font-semibold ${valueClass}`}>{value}</span>
    </div>
  );
}

interface Neo4jStatusCardProps {
  enabled?: boolean;
}

export function Neo4jStatusCard({ enabled = true }: Neo4jStatusCardProps) {
  const { data, isLoading, error } = useNeo4jStatus(enabled);

  if (isLoading) {
    return (
      <div className="bg-gray-800 rounded-xl border border-gray-700 p-5">
        <h3 className="font-semibold text-gray-200 mb-4">Neo4j 상태</h3>
        <div className="h-32 bg-gray-700 rounded-lg animate-pulse" />
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="bg-gray-800 rounded-xl border border-gray-700 p-5">
        <h3 className="font-semibold text-gray-200 mb-2">Neo4j 상태</h3>
        <p className="text-sm text-red-400">데이터 로드 실패</p>
      </div>
    );
  }

  const connectionBadge = data.available
    ? 'bg-green-900/30 text-green-400 border border-green-800'
    : 'bg-red-900/30 text-red-400 border border-red-800';
  const connectionLabel = data.available ? '연결됨' : '연결 안 됨';

  return (
    <div className="bg-gray-800 rounded-xl border border-gray-700 p-5">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <Database className="h-4 w-4 text-gray-400" />
          <h3 className="font-semibold text-gray-200">Neo4j 상태</h3>
        </div>
        <span className={`inline-block px-2 py-0.5 rounded text-xs font-medium ${connectionBadge}`}>
          {connectionLabel}
        </span>
      </div>

      <div className="space-y-0">
        <StatRow
          label="마지막 동기화"
          value={formatRelativeTime(data.last_sync)}
        />
        <StatRow
          label="오늘 동기화"
          value={`${data.synced_today.toLocaleString()}건`}
          valueClass={data.synced_today > 0 ? 'text-green-400' : 'text-gray-400'}
        />
        <StatRow
          label="동기화 대기"
          value={`${data.pending_sync.toLocaleString()}건`}
          valueClass={data.pending_sync > 0 ? 'text-yellow-400' : 'text-gray-200'}
        />
        <StatRow
          label="마지막 클린업"
          value={formatRelativeTime(data.cleanup_last_run)}
        />
      </div>
    </div>
  );
}
