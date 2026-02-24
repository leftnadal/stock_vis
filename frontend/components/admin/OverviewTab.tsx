'use client';

import { BarChart3, Cog, Newspaper, AlertTriangle, CheckCircle2, XCircle } from 'lucide-react';
import { useAdminOverview } from '@/hooks/useAdminDashboard';
import SummaryCard from './shared/SummaryCard';
import IssueList from './shared/IssueList';
import StatusBadge from './shared/StatusBadge';

export default function OverviewTab() {
  const { data, isLoading, error } = useAdminOverview();

  if (isLoading) {
    return <LoadingSkeleton />;
  }

  if (error || !data) {
    return (
      <div className="text-center py-12 text-red-500">
        데이터를 불러오는 중 오류가 발생했습니다.
      </div>
    );
  }

  const { summary, issues } = data;
  const { stocks, tasks_24h, data_freshness, news } = summary;

  const errorCount = issues.filter((i) => i.severity === 'error').length;
  const warningCount = issues.filter((i) => i.severity === 'warning').length;

  return (
    <div className="space-y-6">
      {/* Summary Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <SummaryCard
          title="SP500 가격 커버리지"
          value={`${stocks.with_todays_price}/${stocks.sp500_active}`}
          subtitle={`${stocks.coverage_pct}% 커버리지`}
          icon={<BarChart3 className="h-6 w-6" />}
          status={stocks.coverage_pct >= 95 ? 'ok' : stocks.coverage_pct >= 80 ? 'warning' : 'error'}
        />
        <SummaryCard
          title="Celery 태스크 (24h)"
          value={`${tasks_24h.success_rate}%`}
          subtitle={`성공 ${tasks_24h.success} / 실패 ${tasks_24h.failure} / 전체 ${tasks_24h.total}`}
          icon={<Cog className="h-6 w-6" />}
          status={tasks_24h.failure === 0 ? 'ok' : tasks_24h.success_rate >= 90 ? 'warning' : 'error'}
        />
        <SummaryCard
          title="뉴스 기사 (24h)"
          value={news.articles_24h}
          subtitle="최근 24시간 수집"
          icon={<Newspaper className="h-6 w-6" />}
          status={news.articles_24h > 0 ? 'ok' : 'warning'}
        />
        <SummaryCard
          title="감지된 문제"
          value={issues.length}
          subtitle={errorCount > 0 ? `${errorCount} error, ${warningCount} warning` : '이상 없음'}
          icon={<AlertTriangle className="h-6 w-6" />}
          status={errorCount > 0 ? 'error' : warningCount > 0 ? 'warning' : 'ok'}
        />
      </div>

      {/* Data Freshness */}
      <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-5">
        <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-3">
          데이터 신선도 — {data_freshness.last_trading_day}
          {data_freshness.is_today_trading_day && (
            <span className="ml-2 text-xs text-blue-500">(오늘 거래일)</span>
          )}
        </h3>
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          <FreshnessItem label="Market Movers" ok={data_freshness.movers} />
          <FreshnessItem label="AI Keywords" ok={data_freshness.keywords} />
          <FreshnessItem label="Market Breadth" ok={data_freshness.breadth} />
          <FreshnessItem label="News Keywords" ok={data_freshness.news_keywords} />
        </div>
      </div>

      {/* Issues */}
      <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-5">
        <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-3">
          감지된 문제 ({issues.length}건)
        </h3>
        <IssueList issues={issues} />
      </div>

      {/* Task Quick Stats */}
      <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-5">
        <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-3">
          최근 태스크 요약
        </h3>
        <div className="flex items-center gap-6 text-sm">
          <div className="flex items-center gap-2">
            <StatusBadge status="ok" />
            <span className="text-gray-600 dark:text-gray-400">성공: {tasks_24h.success}</span>
          </div>
          <div className="flex items-center gap-2">
            <StatusBadge status="error" />
            <span className="text-gray-600 dark:text-gray-400">실패: {tasks_24h.failure}</span>
          </div>
          <div className="text-gray-400 dark:text-gray-500">
            성공률: {tasks_24h.success_rate}%
          </div>
        </div>
      </div>
    </div>
  );
}

function FreshnessItem({ label, ok }: { label: string; ok: boolean }) {
  return (
    <div className="flex items-center gap-2">
      {ok ? (
        <CheckCircle2 className="h-4 w-4 text-green-500" />
      ) : (
        <XCircle className="h-4 w-4 text-red-500" />
      )}
      <span className="text-sm text-gray-600 dark:text-gray-400">{label}</span>
    </div>
  );
}

function LoadingSkeleton() {
  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {[...Array(4)].map((_, i) => (
          <div key={i} className="h-28 bg-gray-100 dark:bg-gray-800 rounded-xl animate-pulse" />
        ))}
      </div>
      <div className="h-32 bg-gray-100 dark:bg-gray-800 rounded-xl animate-pulse" />
      <div className="h-48 bg-gray-100 dark:bg-gray-800 rounded-xl animate-pulse" />
    </div>
  );
}
