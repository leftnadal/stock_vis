'use client';

import { useState } from 'react';
import { ChevronDown, ChevronUp, CheckCircle2 } from 'lucide-react';
import { format, parseISO } from 'date-fns';
import { useCollectionLogs } from '@/hooks/useNewsPipeline';
import type { CollectionLogEntry } from '@/types/newsPipeline';

const MAX_DISPLAY = 10;

interface ErrorItemProps {
  entry: CollectionLogEntry;
}

function ErrorItem({ entry }: ErrorItemProps) {
  const [expanded, setExpanded] = useState(false);
  const executedAt = format(parseISO(entry.executed_at), 'MM/dd HH:mm');

  return (
    <div className="rounded-lg border border-red-900/50 bg-red-900/10 overflow-hidden">
      <div
        role="button"
        tabIndex={0}
        onClick={() => setExpanded(!expanded)}
        onKeyDown={(e) => {
          if (e.key === 'Enter' || e.key === ' ') {
            e.preventDefault();
            setExpanded(!expanded);
          }
        }}
        className="flex items-center gap-3 p-3 text-left cursor-pointer hover:bg-red-900/20 transition-colors"
      >
        <span className="font-mono text-xs px-1.5 py-0.5 bg-gray-700 text-gray-300 rounded uppercase">
          {entry.provider}
        </span>
        <span className="flex-1 text-sm text-gray-300 truncate">{entry.task_name}</span>
        <span className="text-xs text-gray-500 whitespace-nowrap">{executedAt}</span>
        <span className="text-xs font-medium text-red-400 whitespace-nowrap">
          errors: {entry.errors}
        </span>
        {expanded ? (
          <ChevronUp className="h-4 w-4 text-gray-500 flex-shrink-0" />
        ) : (
          <ChevronDown className="h-4 w-4 text-gray-500 flex-shrink-0" />
        )}
      </div>

      {expanded && (
        <div className="px-3 pb-3 pt-0 text-xs text-gray-400 space-y-1">
          <p>
            <span className="text-gray-500">심볼 처리: </span>
            {entry.symbols_tried}개
          </p>
          <p>
            <span className="text-gray-500">신규: </span>
            {entry.articles_new}건 /
            <span className="text-gray-500"> 중복: </span>
            {entry.articles_dup}건
          </p>
          <p>
            <span className="text-gray-500">소요 시간: </span>
            {entry.duration_sec.toFixed(1)}s
          </p>
        </div>
      )}
    </div>
  );
}

interface RecentErrorsListProps {
  enabled?: boolean;
}

export function RecentErrorsList({ enabled = true }: RecentErrorsListProps) {
  const { data, isLoading, error } = useCollectionLogs(3, enabled);

  if (isLoading) {
    return (
      <div className="bg-gray-800 rounded-xl border border-gray-700 p-5">
        <h3 className="font-semibold text-gray-200 mb-4">최근 에러 목록 (3일)</h3>
        <div className="h-24 bg-gray-700 rounded-lg animate-pulse" />
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="bg-gray-800 rounded-xl border border-gray-700 p-5">
        <h3 className="font-semibold text-gray-200 mb-2">최근 에러 목록 (3일)</h3>
        <p className="text-sm text-red-400">데이터 로드 실패</p>
      </div>
    );
  }

  const errorLogs = data.logs
    .filter((log: CollectionLogEntry) => log.errors > 0)
    .slice(0, MAX_DISPLAY);

  return (
    <div className="bg-gray-800 rounded-xl border border-gray-700 p-5">
      <div className="flex items-center justify-between mb-4">
        <h3 className="font-semibold text-gray-200">최근 에러 목록 (3일)</h3>
        {errorLogs.length > 0 && (
          <span className="text-xs px-2 py-0.5 bg-red-900/30 text-red-400 rounded-full border border-red-900">
            {errorLogs.length}건
          </span>
        )}
      </div>

      {errorLogs.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-6 text-gray-500">
          <CheckCircle2 className="h-8 w-8 mb-2 text-green-500/50" />
          <p className="text-sm">최근 3일간 에러 없음</p>
        </div>
      ) : (
        <div className="space-y-2">
          {errorLogs.map((entry: CollectionLogEntry) => (
            <ErrorItem key={entry.id} entry={entry} />
          ))}
        </div>
      )}
    </div>
  );
}
