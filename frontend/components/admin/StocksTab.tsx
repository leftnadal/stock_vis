'use client';

import { useState } from 'react';
import { Database, ChevronDown, ChevronUp, AlertTriangle } from 'lucide-react';
import { useAdminStocks } from '@/hooks/useAdminDashboard';
import StatusBadge from './shared/StatusBadge';
import ActionButton from './shared/ActionButton';

function freshness(isFresh: boolean, latestDate: string | null): 'ok' | 'warning' | 'error' {
  if (!latestDate) return 'error';
  return isFresh ? 'ok' : 'error';
}

function staleLabel(latestDate: string | null, lastTradingDay: string): string | null {
  if (!latestDate) return '데이터 없음';
  if (latestDate !== lastTradingDay) {
    return `최신 데이터: ${latestDate} (기준일: ${lastTradingDay})`;
  }
  return null;
}

export default function StocksTab() {
  const { data, isLoading, error } = useAdminStocks();

  if (isLoading) {
    return (
      <div className="space-y-4">
        {[...Array(6)].map((_, i) => (
          <div key={i} className="h-20 bg-gray-100 dark:bg-gray-800 rounded-xl animate-pulse" />
        ))}
      </div>
    );
  }

  if (error || !data) {
    return <div className="text-center py-12 text-red-500">데이터 로드 실패</div>;
  }

  const lastTD = data.last_trading_day;

  // DailyPrice 상태: is_fresh + missing_count 종합
  const dailyStatus = !data.daily_price.is_fresh
    ? 'error'
    : data.daily_price.missing_count <= 5
      ? 'ok'
      : data.daily_price.missing_count <= 15
        ? 'warning'
        : 'error';

  return (
    <div className="space-y-4">
      {/* 기준일 안내 */}
      <div className="text-sm text-gray-500 dark:text-gray-400 px-1">
        기준 거래일: <span className="font-mono font-medium text-gray-700 dark:text-gray-300">{lastTD}</span>
      </div>

      {/* SP500 */}
      <DataCard
        title="SP500 동기화"
        items={[
          { label: '활성 종목', value: `${data.sp500.active_count}개` },
          { label: '마지막 동기화', value: data.sp500.latest_update ? new Date(data.sp500.latest_update).toLocaleDateString('ko-KR') : '없음' },
        ]}
        status={data.sp500.active_count > 0 ? 'ok' : 'error'}
      />

      {/* DailyPrice */}
      <DataCard
        title="DailyPrice"
        items={[
          { label: '최신 날짜', value: data.daily_price.latest_date || '없음' },
          { label: '커버리지', value: `${data.daily_price.coverage}/${data.sp500.active_count}` },
          { label: '총 레코드', value: data.daily_price.total_records.toLocaleString() },
        ]}
        status={dailyStatus}
        staleMessage={staleLabel(data.daily_price.latest_date, lastTD)}
        action={(!data.daily_price.is_fresh || data.daily_price.missing_count > 0) ? <ActionButton action="sync_eod_prices" label="EOD 동기화" /> : undefined}
        expandContent={
          data.daily_price.missing_count > 0 ? (
            <div>
              <p className="text-sm text-gray-500 dark:text-gray-400 mb-2">
                누락 종목 ({data.daily_price.missing_count}개):
              </p>
              <div className="flex flex-wrap gap-1">
                {data.daily_price.missing_symbols.map((s) => (
                  <span key={s} className="px-2 py-0.5 text-xs font-mono bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-300 rounded">
                    {s}
                  </span>
                ))}
              </div>
            </div>
          ) : undefined
        }
      />

      {/* WeeklyPrice */}
      <DataCard
        title="WeeklyPrice"
        items={[
          { label: '최신 날짜', value: data.weekly_price.latest_date || '없음' },
          { label: '총 레코드', value: data.weekly_price.total_records.toLocaleString() },
        ]}
        status={freshness(data.weekly_price.is_fresh, data.weekly_price.latest_date)}
        staleMessage={!data.weekly_price.is_fresh && data.weekly_price.latest_date ? `최신 데이터가 7일 이상 오래됨 (${data.weekly_price.latest_date})` : (!data.weekly_price.latest_date ? '데이터 없음' : null)}
        action={!data.weekly_price.is_fresh ? <ActionButton action="aggregate_weekly" label="주간 집계" /> : undefined}
      />

      {/* Financial Statements */}
      <DataCard
        title="BalanceSheet"
        items={[
          { label: '최신 날짜', value: data.balance_sheet.latest_date || '없음' },
          { label: '총 레코드', value: data.balance_sheet.total_records.toLocaleString() },
          { label: '종목 수', value: `${data.balance_sheet.distinct_stocks}개` },
        ]}
        status={freshness(data.balance_sheet.is_fresh, data.balance_sheet.latest_date)}
        staleMessage={!data.balance_sheet.is_fresh && data.balance_sheet.latest_date ? `90일 이상 미갱신 (${data.balance_sheet.latest_date})` : (!data.balance_sheet.latest_date ? '데이터 없음' : null)}
        action={!data.balance_sheet.is_fresh ? <ActionButton action="sync_financials_batch" label="배치 동기화" /> : undefined}
      />

      <DataCard
        title="IncomeStatement"
        items={[
          { label: '최신 날짜', value: data.income_statement.latest_date || '없음' },
          { label: '총 레코드', value: data.income_statement.total_records.toLocaleString() },
          { label: '종목 수', value: `${data.income_statement.distinct_stocks}개` },
        ]}
        status={freshness(data.income_statement.is_fresh, data.income_statement.latest_date)}
        staleMessage={!data.income_statement.is_fresh && data.income_statement.latest_date ? `90일 이상 미갱신 (${data.income_statement.latest_date})` : (!data.income_statement.latest_date ? '데이터 없음' : null)}
        action={!data.income_statement.is_fresh ? <ActionButton action="sync_financials_batch" label="배치 동기화" /> : undefined}
      />

      <DataCard
        title="CashFlowStatement"
        items={[
          { label: '최신 날짜', value: data.cash_flow.latest_date || '없음' },
          { label: '총 레코드', value: data.cash_flow.total_records.toLocaleString() },
          { label: '종목 수', value: `${data.cash_flow.distinct_stocks}개` },
        ]}
        status={freshness(data.cash_flow.is_fresh, data.cash_flow.latest_date)}
        staleMessage={!data.cash_flow.is_fresh && data.cash_flow.latest_date ? `90일 이상 미갱신 (${data.cash_flow.latest_date})` : (!data.cash_flow.latest_date ? '데이터 없음' : null)}
        action={!data.cash_flow.is_fresh ? <ActionButton action="sync_financials_batch" label="배치 동기화" /> : undefined}
      />
    </div>
  );
}

function DataCard({
  title,
  items,
  status,
  staleMessage,
  expandContent,
  action,
}: {
  title: string;
  items: Array<{ label: string; value: string }>;
  status: 'ok' | 'warning' | 'error';
  staleMessage?: string | null;
  expandContent?: React.ReactNode;
  action?: React.ReactNode;
}) {
  const [expanded, setExpanded] = useState(false);

  return (
    <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Database className="h-5 w-5 text-gray-400" />
          <span className="font-medium text-gray-800 dark:text-gray-200">{title}</span>
          <StatusBadge status={status} />
          {action && <div onClick={(e) => e.stopPropagation()}>{action}</div>}
        </div>
        {expandContent && (
          <button onClick={() => setExpanded(!expanded)} className="text-gray-400 hover:text-gray-600">
            {expanded ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
          </button>
        )}
      </div>
      {staleMessage && (
        <div className="mt-1.5 ml-8 flex items-center gap-1.5 text-xs text-red-500 dark:text-red-400">
          <AlertTriangle className="h-3.5 w-3.5 flex-shrink-0" />
          <span>{staleMessage}</span>
        </div>
      )}
      <div className="mt-2 flex flex-wrap gap-x-6 gap-y-1 ml-8">
        {items.map((item) => (
          <div key={item.label} className="text-sm">
            <span className="text-gray-500 dark:text-gray-400">{item.label}: </span>
            <span className="font-medium text-gray-700 dark:text-gray-300">{item.value}</span>
          </div>
        ))}
      </div>
      {expanded && expandContent && (
        <div className="mt-3 ml-8 pt-3 border-t border-gray-100 dark:border-gray-700">
          {expandContent}
        </div>
      )}
    </div>
  );
}
