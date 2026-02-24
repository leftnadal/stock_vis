'use client';

import { TrendingUp, Key, Gauge, DollarSign, BarChart3, Globe, Calendar } from 'lucide-react';
import { useAdminMarketPulse } from '@/hooks/useAdminDashboard';
import StatusBadge from './shared/StatusBadge';
import ActionButton from './shared/ActionButton';

export default function MarketPulseTab() {
  const { data, isLoading, error } = useAdminMarketPulse();

  if (isLoading) {
    return (
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {[...Array(5)].map((_, i) => (
          <div key={i} className="h-36 bg-gray-100 dark:bg-gray-800 rounded-xl animate-pulse" />
        ))}
      </div>
    );
  }

  if (error || !data) {
    return <div className="text-center py-12 text-red-500">데이터 로드 실패</div>;
  }

  const { movers, keywords, cache, economic_indicators } = data;

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
      {/* Market Movers */}
      <PulseCard
        icon={<TrendingUp className="h-5 w-5 text-blue-500" />}
        title="Market Movers"
        date={movers.date}
        status={movers.total > 0 ? 'ok' : 'error'}
        action={movers.total === 0 ? <ActionButton action="sync_movers" label="Movers 동기화" /> : undefined}
      >
        <div className="space-y-1 text-sm">
          <DataRow label="Gainers" value={movers.by_type.gainers ?? 0} />
          <DataRow label="Losers" value={movers.by_type.losers ?? 0} />
          <DataRow label="Actives" value={movers.by_type.actives ?? 0} />
          <DataRow label="Total" value={movers.total} bold />
        </div>
      </PulseCard>

      {/* AI Keywords */}
      <PulseCard
        icon={<Key className="h-5 w-5 text-purple-500" />}
        title="AI Keywords"
        date={keywords.date}
        status={(keywords.by_status.completed ?? 0) > 0 ? 'ok' : 'warning'}
        action={(keywords.by_status.failed ?? 0) > 0 ? <ActionButton action="generate_keywords" label="키워드 재생성" /> : undefined}
      >
        <div className="space-y-1 text-sm">
          <DataRow label="Completed" value={keywords.by_status.completed ?? 0} />
          <DataRow label="Pending" value={keywords.by_status.pending ?? 0} />
          <DataRow label="Failed" value={keywords.by_status.failed ?? 0} />
        </div>
      </PulseCard>

      {/* Fear & Greed Cache */}
      <PulseCard
        icon={<Gauge className="h-5 w-5 text-orange-500" />}
        title="Fear & Greed"
        status={cache.fear_greed ? 'ok' : 'warning'}
      >
        <div className="text-sm">
          <span className="text-gray-500 dark:text-gray-400">Redis Cache: </span>
          <StatusBadge status={cache.fear_greed ? 'ok' : 'warning'} label={cache.fear_greed ? '존재' : '없음'} />
        </div>
      </PulseCard>

      {/* Market Pulse Cache */}
      <PulseCard
        icon={<DollarSign className="h-5 w-5 text-green-500" />}
        title="Market Pulse"
        status={cache.market_pulse ? 'ok' : 'warning'}
      >
        <div className="text-sm">
          <span className="text-gray-500 dark:text-gray-400">Redis Cache: </span>
          <StatusBadge status={cache.market_pulse ? 'ok' : 'warning'} label={cache.market_pulse ? '존재' : '없음'} />
        </div>
      </PulseCard>

      {/* Economic Indicators */}
      <PulseCard
        icon={<BarChart3 className="h-5 w-5 text-cyan-500" />}
        title="Economic Indicators"
        status={economic_indicators.total > 0 ? 'ok' : 'warning'}
      >
        <div className="text-sm">
          <DataRow label="총 지표" value={economic_indicators.total} />
        </div>
      </PulseCard>
    </div>
  );
}

function PulseCard({
  icon,
  title,
  date,
  status,
  action,
  children,
}: {
  icon: React.ReactNode;
  title: string;
  date?: string;
  status: 'ok' | 'warning' | 'error';
  action?: React.ReactNode;
  children: React.ReactNode;
}) {
  return (
    <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-5">
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          {icon}
          <span className="font-semibold text-gray-800 dark:text-gray-200">{title}</span>
          {action && <div onClick={(e) => e.stopPropagation()}>{action}</div>}
        </div>
        <StatusBadge status={status} />
      </div>
      {date && (
        <p className="text-xs text-gray-400 dark:text-gray-500 mb-2">Date: {date}</p>
      )}
      {children}
    </div>
  );
}

function DataRow({ label, value, bold }: { label: string; value: number | string; bold?: boolean }) {
  return (
    <div className="flex justify-between">
      <span className="text-gray-500 dark:text-gray-400">{label}</span>
      <span className={`text-gray-700 dark:text-gray-300 ${bold ? 'font-bold' : 'font-medium'}`}>{value}</span>
    </div>
  );
}
