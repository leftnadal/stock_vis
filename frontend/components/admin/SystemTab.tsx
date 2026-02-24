'use client';

import { useState } from 'react';
import { Server, Database, Wifi, Gauge, Clock, ListChecks, ChevronDown, ChevronUp } from 'lucide-react';
import { useAdminSystem, useHealthCheck, useProviderStatus } from '@/hooks/useAdminDashboard';
import type { LatestTaskRun } from '@/types/admin';
import StatusBadge from './shared/StatusBadge';
import TaskLogViewer from './shared/TaskLogViewer';
import ActionButton from './shared/ActionButton';

export default function SystemTab() {
  const { data: systemData, isLoading: systemLoading } = useAdminSystem();
  const { data: healthData, isLoading: healthLoading } = useHealthCheck();
  const { data: providerData, isLoading: providerLoading } = useProviderStatus();

  return (
    <div className="space-y-6">
      {/* Infrastructure Health */}
      <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-5">
        <h3 className="font-semibold text-gray-800 dark:text-gray-200 mb-4 flex items-center gap-2">
          <Server className="h-4 w-4" />
          Infrastructure
        </h3>
        {healthLoading ? (
          <div className="h-12 bg-gray-100 dark:bg-gray-700 rounded animate-pulse" />
        ) : healthData ? (
          <div className="flex flex-wrap gap-4">
            {Object.entries(healthData.components).map(([name, comp]) => (
              <div key={name} className="flex items-center gap-2">
                <StatusBadge
                  status={comp.status === 'healthy' ? 'ok' : 'error'}
                  label={name}
                />
                {comp.type && (
                  <span className="text-xs text-gray-400">{comp.type}</span>
                )}
                {comp.active && (
                  <span className="text-xs text-gray-400">{comp.active}</span>
                )}
              </div>
            ))}
          </div>
        ) : (
          <p className="text-sm text-red-500">Health check 실패</p>
        )}
      </div>

      {/* Latest Task Runs — 태스크별 최근 실행 현황 */}
      <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-5">
        <h3 className="font-semibold text-gray-800 dark:text-gray-200 mb-4 flex items-center gap-2">
          <ListChecks className="h-4 w-4" />
          최근 태스크 실행 현황
        </h3>
        {systemLoading ? (
          <div className="h-24 bg-gray-100 dark:bg-gray-700 rounded animate-pulse" />
        ) : systemData?.latest_task_runs && systemData.latest_task_runs.length > 0 ? (
          <LatestTaskRunsTable runs={systemData.latest_task_runs} />
        ) : (
          <p className="text-sm text-gray-400">실행 기록 없음</p>
        )}
      </div>

      {/* API Providers */}
      <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-5">
        <h3 className="font-semibold text-gray-800 dark:text-gray-200 mb-4 flex items-center gap-2">
          <Wifi className="h-4 w-4" />
          API Providers
        </h3>
        {providerLoading ? (
          <div className="h-24 bg-gray-100 dark:bg-gray-700 rounded animate-pulse" />
        ) : providerData ? (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-gray-200 dark:border-gray-700">
                  <th className="text-left py-2 px-2 text-gray-500 dark:text-gray-400 font-medium">Endpoint</th>
                  <th className="text-left py-2 px-2 text-gray-500 dark:text-gray-400 font-medium">Provider</th>
                  <th className="text-left py-2 px-2 text-gray-500 dark:text-gray-400 font-medium">Status</th>
                </tr>
              </thead>
              <tbody>
                {Object.entries(providerData.providers).map(([endpoint, info]) => (
                  <tr key={endpoint} className="border-b border-gray-100 dark:border-gray-800">
                    <td className="py-1.5 px-2 text-gray-700 dark:text-gray-300 font-mono text-xs">{endpoint}</td>
                    <td className="py-1.5 px-2 text-gray-600 dark:text-gray-400">{info.provider || '-'}</td>
                    <td className="py-1.5 px-2">
                      {info.error ? (
                        <StatusBadge status="error" label="Error" />
                      ) : (
                        <StatusBadge status={info.available ? 'ok' : 'warning'} label={info.available ? 'Available' : 'Unavailable'} />
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <p className="text-sm text-gray-400">Provider 상태 조회 불가</p>
        )}
      </div>

      {/* Rate Limits */}
      {systemData?.rate_limits && Object.keys(systemData.rate_limits).length > 0 && (
        <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-5">
          <h3 className="font-semibold text-gray-800 dark:text-gray-200 mb-4 flex items-center gap-2">
            <Gauge className="h-4 w-4" />
            Rate Limits
          </h3>
          <div className="space-y-3">
            {Object.entries(systemData.rate_limits).map(([provider, limits]: [string, any]) => (
              <div key={provider} className="border border-gray-100 dark:border-gray-700 rounded-lg p-3">
                <p className="font-medium text-sm text-gray-700 dark:text-gray-300 mb-2">{provider}</p>
                <div className="flex flex-wrap gap-4 text-xs">
                  {limits.limits && Object.entries(limits.limits).map(([period, info]: [string, any]) => (
                    <div key={period} className="text-gray-500 dark:text-gray-400">
                      <span className="font-medium">{period}:</span>{' '}
                      {info.current}/{info.limit} (남은: {info.remaining})
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Celery Task Logs */}
      <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-5">
        <h3 className="font-semibold text-gray-800 dark:text-gray-200 mb-4 flex items-center gap-2">
          <Clock className="h-4 w-4" />
          Celery 태스크 로그
        </h3>
        <TaskLogViewer />
      </div>

      {/* DB Table Sizes */}
      {systemData?.db_table_sizes && systemData.db_table_sizes.length > 0 && (
        <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-5">
          <h3 className="font-semibold text-gray-800 dark:text-gray-200 mb-4 flex items-center gap-2">
            <Database className="h-4 w-4" />
            DB 테이블 크기
          </h3>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-gray-200 dark:border-gray-700">
                  <th className="text-left py-2 px-2 text-gray-500 dark:text-gray-400 font-medium">Table</th>
                  <th className="text-right py-2 px-2 text-gray-500 dark:text-gray-400 font-medium">Rows</th>
                  <th className="text-left py-2 px-2 text-gray-500 dark:text-gray-400 font-medium w-1/3">Bar</th>
                </tr>
              </thead>
              <tbody>
                {systemData.db_table_sizes.slice(0, 15).map((t) => {
                  const maxRows = systemData.db_table_sizes[0]?.row_count || 1;
                  const pct = (t.row_count / maxRows) * 100;
                  return (
                    <tr key={t.table} className="border-b border-gray-100 dark:border-gray-800">
                      <td className="py-1.5 px-2 text-gray-700 dark:text-gray-300 font-mono text-xs">{t.table}</td>
                      <td className="py-1.5 px-2 text-right text-gray-600 dark:text-gray-400">{t.row_count.toLocaleString()}</td>
                      <td className="py-1.5 px-2">
                        <div className="w-full bg-gray-100 dark:bg-gray-700 rounded-full h-2">
                          <div
                            className="bg-indigo-500 h-2 rounded-full"
                            style={{ width: `${pct}%` }}
                          />
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}

// ========================================
// 최근 태스크 실행 현황 테이블
// ========================================

const TASK_ACTION_MAP: Record<string, string> = {
  'stocks.tasks.sync_sp500_eod_prices': 'sync_eod_prices',
  'stocks.tasks.aggregate_weekly_prices': 'aggregate_weekly',
  'stocks.tasks.sync_sp500_financials': 'sync_financials_batch',
  'stocks.tasks.sync_sp500_constituents': 'sync_sp500_constituents',
  'serverless.tasks.sync_daily_market_movers': 'sync_movers',
  'serverless.tasks.keyword_generation_pipeline': 'generate_keywords',
  'serverless.tasks.calculate_daily_market_breadth': 'sync_breadth',
  'serverless.tasks.calculate_daily_sector_heatmap': 'sync_heatmap',
  'serverless.tasks.sync_etf_holdings': 'sync_etf_holdings',
  'news.tasks.collect_daily_news': 'collect_news',
  'news.tasks.extract_daily_news_keywords': 'extract_news_keywords',
};

function LatestTaskRunsTable({ runs }: { runs: LatestTaskRun[] }) {
  const [expandedTask, setExpandedTask] = useState<string | null>(null);

  const taskStatusBadge = (status: string) => {
    switch (status) {
      case 'SUCCESS': return <StatusBadge status="ok" label="SUCCESS" />;
      case 'FAILURE': return <StatusBadge status="error" label="FAILURE" />;
      case 'PENDING': return <StatusBadge status="info" label="PENDING" />;
      case 'STARTED': return <StatusBadge status="info" label="STARTED" />;
      default: return <StatusBadge status="warning" label={status} />;
    }
  };

  const formatTime = (iso: string | null) => {
    if (!iso) return '-';
    const d = new Date(iso);
    const now = new Date();
    const diffMs = now.getTime() - d.getTime();
    const diffH = Math.floor(diffMs / (1000 * 60 * 60));
    const diffM = Math.floor(diffMs / (1000 * 60));

    const timeStr = d.toLocaleString('ko-KR', {
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
    });

    let ago: string;
    if (diffM < 60) {
      ago = `${diffM}분 전`;
    } else if (diffH < 24) {
      ago = `${diffH}시간 전`;
    } else {
      ago = `${Math.floor(diffH / 24)}일 전`;
    }
    return `${timeStr} (${ago})`;
  };

  const shortName = (taskName: string) => taskName.split('.').pop() || taskName;

  const formatResult = (result: string): string => {
    if (!result) return '';
    try {
      const jsonStr = result
        .replace(/'/g, '"')
        .replace(/None/g, 'null')
        .replace(/True/g, 'true')
        .replace(/False/g, 'false');
      const parsed = JSON.parse(jsonStr);
      return JSON.stringify(parsed, null, 2);
    } catch {
      return result;
    }
  };

  const resultPreview = (result: string): string => {
    if (!result) return '-';
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
    } catch { /* not JSON */ }
    return result.length > 50 ? result.slice(0, 50) + '...' : result;
  };

  // 통계
  const successCount = runs.filter((r) => r.status === 'SUCCESS').length;
  const failureCount = runs.filter((r) => r.status === 'FAILURE').length;

  return (
    <div>
      {/* 요약 */}
      <div className="flex items-center gap-4 mb-3 text-sm text-gray-500 dark:text-gray-400">
        <span>등록 태스크 <span className="font-semibold text-gray-700 dark:text-gray-200">{runs.length}</span>개</span>
        <span className="text-green-600 dark:text-green-400">{successCount} 정상</span>
        {failureCount > 0 && (
          <span className="text-red-600 dark:text-red-400">{failureCount} 실패</span>
        )}
      </div>

      {/* 테이블 */}
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-gray-200 dark:border-gray-700">
              <th className="text-left py-2 px-3 text-gray-500 dark:text-gray-400 font-medium">태스크</th>
              <th className="text-left py-2 px-3 text-gray-500 dark:text-gray-400 font-medium">상태</th>
              <th className="text-left py-2 px-3 text-gray-500 dark:text-gray-400 font-medium">마지막 실행</th>
              <th className="text-left py-2 px-3 text-gray-500 dark:text-gray-400 font-medium">결과</th>
              <th className="text-left py-2 px-3 text-gray-500 dark:text-gray-400 font-medium">액션</th>
              <th className="w-8"></th>
            </tr>
          </thead>
          <tbody>
            {runs.map((run) => {
              const isExpanded = expandedTask === run.task_name;
              const hasResult = !!run.result;
              return (
                <LatestTaskRow
                  key={run.task_name}
                  run={run}
                  expanded={isExpanded}
                  onToggle={() => setExpandedTask(isExpanded ? null : run.task_name)}
                  shortName={shortName}
                  formatTime={formatTime}
                  formatResult={formatResult}
                  resultPreview={resultPreview}
                  taskStatusBadge={taskStatusBadge}
                  hasResult={hasResult}
                />
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function LatestTaskRow({
  run,
  expanded,
  onToggle,
  shortName,
  formatTime,
  formatResult,
  resultPreview,
  taskStatusBadge,
  hasResult,
}: {
  run: LatestTaskRun;
  expanded: boolean;
  onToggle: () => void;
  shortName: (n: string) => string;
  formatTime: (iso: string | null) => string;
  formatResult: (r: string) => string;
  resultPreview: (r: string) => string;
  taskStatusBadge: (s: string) => React.ReactNode;
  hasResult: boolean;
}) {
  return (
    <>
      <tr
        className={`border-b border-gray-100 dark:border-gray-800 ${hasResult ? 'cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-800/50' : ''}`}
        onClick={hasResult ? onToggle : undefined}
      >
        <td className="py-2 px-3 font-mono text-xs" title={run.task_name}>
          {shortName(run.task_name)}
        </td>
        <td className="py-2 px-3">
          {taskStatusBadge(run.status)}
        </td>
        <td className="py-2 px-3 text-gray-500 dark:text-gray-400 text-xs whitespace-nowrap">
          {formatTime(run.date_done)}
        </td>
        <td className="py-2 px-3 text-gray-500 dark:text-gray-400 text-xs max-w-[240px] truncate" title={run.result}>
          {run.status === 'FAILURE' ? (
            <span className="text-red-500 dark:text-red-400">Error</span>
          ) : (
            resultPreview(run.result)
          )}
        </td>
        <td className="py-2 px-3" onClick={(e) => e.stopPropagation()}>
          {run.status === 'FAILURE' && TASK_ACTION_MAP[run.task_name] && (
            <ActionButton action={TASK_ACTION_MAP[run.task_name]} label="재실행" size="sm" variant="secondary" />
          )}
        </td>
        <td className="py-2 px-3">
          {hasResult && (
            expanded
              ? <ChevronUp className="h-4 w-4 text-gray-400" />
              : <ChevronDown className="h-4 w-4 text-gray-400" />
          )}
        </td>
      </tr>
      {expanded && hasResult && (
        <tr>
          <td colSpan={6} className="px-3 py-2 bg-gray-50 dark:bg-gray-800/50">
            <pre className="text-xs text-gray-700 dark:text-gray-300 whitespace-pre-wrap font-mono bg-white dark:bg-gray-900/50 rounded p-2 border border-gray-200 dark:border-gray-700 max-h-40 overflow-y-auto">
              {formatResult(run.result)}
            </pre>
          </td>
        </tr>
      )}
    </>
  );
}
