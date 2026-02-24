'use client';

import { useState } from 'react';
import { ChevronDown, ChevronUp, RefreshCw, CheckCircle2, XCircle, Clock } from 'lucide-react';
import { useAdminTaskLogs } from '@/hooks/useAdminDashboard';
import type { TaskLogEntry } from '@/types/admin';
import StatusBadge from './StatusBadge';

export default function TaskLogViewer() {
  const [taskNameFilter, setTaskNameFilter] = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  const [hoursFilter, setHoursFilter] = useState(24);
  const [expandedId, setExpandedId] = useState<string | null>(null);

  const { data: logs, isLoading, refetch } = useAdminTaskLogs({
    task_name: taskNameFilter || undefined,
    status: statusFilter || undefined,
    hours: hoursFilter,
    limit: 50,
  });

  // 요약 통계
  const summary = logs
    ? {
        total: logs.length,
        success: logs.filter((l) => l.status === 'SUCCESS').length,
        failure: logs.filter((l) => l.status === 'FAILURE').length,
        other: logs.filter((l) => l.status !== 'SUCCESS' && l.status !== 'FAILURE').length,
      }
    : null;

  const formatTime = (iso: string | null) => {
    if (!iso) return '-';
    const d = new Date(iso);
    return d.toLocaleString('ko-KR', {
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
    });
  };

  const taskStatusBadge = (status: string) => {
    switch (status) {
      case 'SUCCESS': return <StatusBadge status="ok" label="SUCCESS" />;
      case 'FAILURE': return <StatusBadge status="error" label="FAILURE" />;
      case 'PENDING': return <StatusBadge status="info" label="PENDING" />;
      case 'STARTED': return <StatusBadge status="info" label="STARTED" />;
      default: return <StatusBadge status="warning" label={status} />;
    }
  };

  return (
    <div>
      {/* 요약 바 */}
      {summary && summary.total > 0 && (
        <div className="flex items-center gap-4 mb-4 px-1 text-sm">
          <span className="text-gray-500 dark:text-gray-400">
            총 <span className="font-semibold text-gray-700 dark:text-gray-200">{summary.total}</span>건
          </span>
          <span className="flex items-center gap-1 text-green-600 dark:text-green-400">
            <CheckCircle2 className="h-3.5 w-3.5" />
            {summary.success}
          </span>
          <span className="flex items-center gap-1 text-red-600 dark:text-red-400">
            <XCircle className="h-3.5 w-3.5" />
            {summary.failure}
          </span>
          {summary.other > 0 && (
            <span className="flex items-center gap-1 text-blue-600 dark:text-blue-400">
              <Clock className="h-3.5 w-3.5" />
              {summary.other}
            </span>
          )}
          {summary.total > 0 && (
            <span className="text-gray-400 dark:text-gray-500 text-xs">
              성공률 {summary.total > 0 ? Math.round((summary.success / summary.total) * 100) : 0}%
            </span>
          )}
        </div>
      )}

      {/* Filters */}
      <div className="flex flex-wrap gap-3 mb-4">
        <input
          type="text"
          placeholder="태스크명 검색..."
          value={taskNameFilter}
          onChange={(e) => setTaskNameFilter(e.target.value)}
          className="px-3 py-1.5 text-sm border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-1 focus:ring-blue-500"
        />
        <select
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
          className="px-3 py-1.5 text-sm border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-1 focus:ring-blue-500"
        >
          <option value="">All Status</option>
          <option value="SUCCESS">SUCCESS</option>
          <option value="FAILURE">FAILURE</option>
          <option value="PENDING">PENDING</option>
          <option value="STARTED">STARTED</option>
        </select>
        <select
          value={hoursFilter}
          onChange={(e) => setHoursFilter(Number(e.target.value))}
          className="px-3 py-1.5 text-sm border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-1 focus:ring-blue-500"
        >
          <option value={6}>6시간</option>
          <option value={24}>24시간</option>
          <option value={48}>48시간</option>
          <option value={168}>7일</option>
        </select>
        <button
          onClick={() => refetch()}
          className="px-3 py-1.5 text-sm bg-gray-100 dark:bg-gray-700 rounded-lg hover:bg-gray-200 dark:hover:bg-gray-600 transition-colors"
        >
          <RefreshCw className={`h-4 w-4 ${isLoading ? 'animate-spin' : ''}`} />
        </button>
      </div>

      {/* Table */}
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-gray-200 dark:border-gray-700">
              <th className="text-left py-2 px-3 text-gray-500 dark:text-gray-400 font-medium">Task Name</th>
              <th className="text-left py-2 px-3 text-gray-500 dark:text-gray-400 font-medium">Status</th>
              <th className="text-left py-2 px-3 text-gray-500 dark:text-gray-400 font-medium">Time</th>
              <th className="text-left py-2 px-3 text-gray-500 dark:text-gray-400 font-medium">Result</th>
              <th className="w-8"></th>
            </tr>
          </thead>
          <tbody>
            {isLoading ? (
              <tr>
                <td colSpan={5} className="text-center py-8 text-gray-400">
                  <RefreshCw className="h-5 w-5 animate-spin mx-auto mb-2" />
                  로딩 중...
                </td>
              </tr>
            ) : !logs || logs.length === 0 ? (
              <tr>
                <td colSpan={5} className="text-center py-8 text-gray-400">
                  로그 없음
                </td>
              </tr>
            ) : (
              logs.map((log: TaskLogEntry) => (
                <TaskLogRow
                  key={log.id}
                  log={log}
                  expanded={expandedId === log.id}
                  onToggle={() => setExpandedId(expandedId === log.id ? null : log.id)}
                  formatTime={formatTime}
                  taskStatusBadge={taskStatusBadge}
                />
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}

/** result 문자열에서 핵심 숫자만 추출하여 짧게 표시 */
function resultPreview(result: string): string {
  if (!result) return '-';
  // JSON-like result인 경우 짧게 요약
  try {
    const parsed = JSON.parse(result.replace(/'/g, '"'));
    if (typeof parsed === 'object' && parsed !== null) {
      const parts: string[] = [];
      for (const [k, v] of Object.entries(parsed)) {
        if (typeof v === 'number' || typeof v === 'string') {
          parts.push(`${k}: ${v}`);
        }
      }
      if (parts.length > 0) return parts.slice(0, 3).join(', ') + (parts.length > 3 ? ' ...' : '');
    }
  } catch {
    // not JSON
  }
  // 길면 잘라서 반환
  return result.length > 60 ? result.slice(0, 60) + '...' : result;
}

function TaskLogRow({
  log,
  expanded,
  onToggle,
  formatTime,
  taskStatusBadge,
}: {
  log: TaskLogEntry;
  expanded: boolean;
  onToggle: () => void;
  formatTime: (iso: string | null) => string;
  taskStatusBadge: (status: string) => React.ReactNode;
}) {
  const shortName = log.task_name.split('.').pop() || log.task_name;
  const hasDetail = !!(log.result || log.traceback);

  return (
    <>
      <tr
        className={`border-b border-gray-100 dark:border-gray-800 ${hasDetail ? 'cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-800/50' : ''}`}
        onClick={hasDetail ? onToggle : undefined}
      >
        <td className="py-2 px-3 font-mono text-xs" title={log.task_name}>
          {shortName}
        </td>
        <td className="py-2 px-3">{taskStatusBadge(log.status)}</td>
        <td className="py-2 px-3 text-gray-500 dark:text-gray-400 text-xs whitespace-nowrap">
          {formatTime(log.date_done)}
        </td>
        <td className="py-2 px-3 text-gray-500 dark:text-gray-400 text-xs max-w-[260px] truncate" title={log.result}>
          {log.status === 'FAILURE' ? (
            <span className="text-red-500 dark:text-red-400">Error (click to expand)</span>
          ) : (
            resultPreview(log.result)
          )}
        </td>
        <td className="py-2 px-3">
          {hasDetail && (
            expanded ? <ChevronUp className="h-4 w-4 text-gray-400" /> : <ChevronDown className="h-4 w-4 text-gray-400" />
          )}
        </td>
      </tr>
      {expanded && hasDetail && (
        <tr>
          <td colSpan={5} className={`px-3 py-3 ${log.status === 'FAILURE' ? 'bg-red-50 dark:bg-red-900/10' : 'bg-gray-50 dark:bg-gray-800/50'}`}>
            {log.result && (
              <div className="mb-2">
                <span className="text-xs font-medium text-gray-500 dark:text-gray-400">Result:</span>
                <pre className="mt-1 text-xs text-gray-700 dark:text-gray-300 whitespace-pre-wrap font-mono bg-white dark:bg-gray-900/50 rounded p-2 border border-gray-200 dark:border-gray-700">
                  {formatResult(log.result)}
                </pre>
              </div>
            )}
            {log.traceback && (
              <div>
                <span className="text-xs font-medium text-red-500 dark:text-red-400">Traceback:</span>
                <pre className="mt-1 text-xs text-red-700 dark:text-red-300 whitespace-pre-wrap max-h-48 overflow-y-auto font-mono bg-white dark:bg-gray-900/50 rounded p-2 border border-red-200 dark:border-red-800">
                  {log.traceback}
                </pre>
              </div>
            )}
            {log.worker && (
              <div className="mt-2 text-xs text-gray-400">
                Worker: {log.worker} | Task ID: {log.task_id}
              </div>
            )}
          </td>
        </tr>
      )}
    </>
  );
}

/** result를 보기 좋게 포맷 */
function formatResult(result: string): string {
  if (!result) return '';
  try {
    // Python dict style → JSON 변환 시도
    const jsonStr = result.replace(/'/g, '"').replace(/None/g, 'null').replace(/True/g, 'true').replace(/False/g, 'false');
    const parsed = JSON.parse(jsonStr);
    return JSON.stringify(parsed, null, 2);
  } catch {
    return result;
  }
}
