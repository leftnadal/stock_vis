'use client';

/**
 * ETF Holdings 수집 패널
 *
 * Chain Sight Phase 3: ETF Holdings 수동 수집 및 상태 확인
 */
import React, { useState } from 'react';
import {
  RefreshCw,
  Database,
  CheckCircle2,
  AlertCircle,
  Clock,
  ChevronDown,
  ChevronUp,
  Zap,
  Wrench,
} from 'lucide-react';
import { useETFCollectionStatus, useETFSync, useRefreshThemeMatches, useResolveETFUrl } from '@/hooks/useETFCollection';
import { ETFProfile, ETFTier } from '@/types/etf';

interface ETFStatusRowProps {
  etf: ETFProfile;
  onSync: () => void;
  syncing: boolean;
}

function ETFStatusRow({ etf, onSync, syncing }: ETFStatusRowProps) {
  const statusConfig: Record<string, { icon: React.ReactNode; color: string; text: string }> = {
    synced: {
      icon: <CheckCircle2 className="h-4 w-4" />,
      color: 'text-green-500',
      text: `${etf.holdings_count}`,
    },
    pending: {
      icon: <Clock className="h-4 w-4" />,
      color: 'text-yellow-500',
      text: '-',
    },
    syncing: {
      icon: <RefreshCw className="h-4 w-4 animate-spin" />,
      color: 'text-blue-500',
      text: '...',
    },
    failed: {
      icon: <AlertCircle className="h-4 w-4" />,
      color: 'text-red-500',
      text: 'X',
    },
  };

  const status = syncing ? 'syncing' : etf.status;
  const config = statusConfig[status] || statusConfig.pending;

  const formatDate = (dateStr: string | null) => {
    if (!dateStr) return '-';
    const date = new Date(dateStr);
    return `${date.getMonth() + 1}/${date.getDate()}`;
  };

  return (
    <div className="flex items-center justify-between py-2 px-3 bg-gray-50 dark:bg-gray-800 rounded-lg mb-1 last:mb-0">
      <div className="flex items-center gap-3 flex-1 min-w-0">
        <span className="font-mono font-bold text-sm w-12">{etf.symbol}</span>
        <span className="text-xs text-gray-500 dark:text-gray-400 truncate flex-1">
          {etf.name}
        </span>
      </div>

      <div className="flex items-center gap-3">
        <div className={`flex items-center gap-1 ${config.color}`}>
          {config.icon}
          <span className="text-xs font-medium w-8 text-right">{config.text}</span>
        </div>

        <span className="text-xs text-gray-400 w-12 text-right">
          {formatDate(etf.last_updated)}
        </span>

        <button
          onClick={onSync}
          disabled={syncing || !etf.csv_url}
          className={`p-1.5 rounded transition-colors ${
            syncing || !etf.csv_url
              ? 'text-gray-300 cursor-not-allowed'
              : 'text-gray-500 hover:text-blue-500 hover:bg-blue-50 dark:hover:bg-blue-900/30'
          }`}
          title={!etf.csv_url ? 'CSV URL 미설정' : '동기화'}
        >
          <RefreshCw className={`h-3.5 w-3.5 ${syncing ? 'animate-spin' : ''}`} />
        </button>
      </div>
    </div>
  );
}

interface ETFTierSectionProps {
  title: string;
  tier: ETFTier;
  etfs: ETFProfile[];
  syncingEtf: string | null;
  onSync: (symbol: string) => void;
}

function ETFTierSection({ title, tier, etfs, syncingEtf, onSync }: ETFTierSectionProps) {
  const [expanded, setExpanded] = useState(tier === 'sector');

  const tierEtfs = etfs.filter((e) => e.tier === tier);
  const syncedCount = tierEtfs.filter((e) => e.status === 'synced').length;

  return (
    <div className="mb-3">
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-center justify-between p-2 bg-gray-100 dark:bg-gray-700 rounded-lg hover:bg-gray-200 dark:hover:bg-gray-600 transition-colors"
      >
        <div className="flex items-center gap-2">
          <span className="font-medium text-sm">{title}</span>
          <span className="text-xs text-gray-500 dark:text-gray-400">
            ({syncedCount}/{tierEtfs.length})
          </span>
        </div>
        {expanded ? (
          <ChevronUp className="h-4 w-4 text-gray-400" />
        ) : (
          <ChevronDown className="h-4 w-4 text-gray-400" />
        )}
      </button>

      {expanded && (
        <div className="mt-2 space-y-1">
          {tierEtfs.map((etf) => (
            <ETFStatusRow
              key={etf.symbol}
              etf={etf}
              onSync={() => onSync(etf.symbol)}
              syncing={syncingEtf === etf.symbol}
            />
          ))}
        </div>
      )}
    </div>
  );
}

export default function ETFCollectionPanel() {
  const [syncingEtf, setSyncingEtf] = useState<string | null>(null);
  const [syncingAll, setSyncingAll] = useState(false);
  const [resolvingUrls, setResolvingUrls] = useState(false);

  const { data: statusData, isLoading, refetch } = useETFCollectionStatus();
  const syncMutation = useETFSync();
  const refreshThemesMutation = useRefreshThemeMatches();
  const resolveUrlMutation = useResolveETFUrl();

  const handleSyncSingle = async (symbol: string) => {
    setSyncingEtf(symbol);
    try {
      await syncMutation.mutateAsync(symbol);
    } finally {
      setSyncingEtf(null);
    }
  };

  const handleSyncAll = async () => {
    setSyncingAll(true);
    try {
      await syncMutation.mutateAsync(undefined);
      // 전체 동기화 후 테마 매치 갱신
      await refreshThemesMutation.mutateAsync();
    } finally {
      setSyncingAll(false);
    }
  };

  const handleResolveUrls = async () => {
    setResolvingUrls(true);
    try {
      const result = await resolveUrlMutation.mutateAsync(undefined);
      if (result.data.summary.resolved > 0) {
        // URL이 복구되면 다시 동기화 시도
        await syncMutation.mutateAsync(undefined);
      }
    } finally {
      setResolvingUrls(false);
    }
  };

  // 실패한 ETF 개수
  const failedCount = statusData?.data.etfs.filter(
    (e) => e.status === 'failed' || (e.last_error && e.last_error.includes('다운로드'))
  ).length || 0;

  if (isLoading) {
    return (
      <div className="p-4 bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-700">
        <div className="animate-pulse space-y-3">
          <div className="h-6 bg-gray-200 dark:bg-gray-700 rounded w-1/3" />
          <div className="h-24 bg-gray-100 dark:bg-gray-800 rounded" />
          <div className="h-24 bg-gray-100 dark:bg-gray-800 rounded" />
        </div>
      </div>
    );
  }

  const etfs = statusData?.data.etfs || [];
  const summary = statusData?.data.summary;

  return (
    <div className="p-4 bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-700">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <Database className="h-5 w-5 text-blue-500" />
          <h3 className="font-semibold text-gray-900 dark:text-white">
            ETF Holdings
          </h3>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={() => refetch()}
            disabled={isLoading}
            className="p-1.5 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 transition-colors"
            title="새로고침"
          >
            <RefreshCw className={`h-4 w-4 ${isLoading ? 'animate-spin' : ''}`} />
          </button>

          {/* URL 복구 버튼 (실패한 ETF가 있을 때만) */}
          {failedCount > 0 && (
            <button
              onClick={handleResolveUrls}
              disabled={resolvingUrls || syncingAll || syncingEtf !== null}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm font-medium transition-colors ${
                resolvingUrls || syncingAll || syncingEtf !== null
                  ? 'bg-gray-100 text-gray-400 cursor-not-allowed dark:bg-gray-800'
                  : 'bg-orange-500 text-white hover:bg-orange-600'
              }`}
              title="404 에러 ETF의 CSV URL을 자동으로 복구합니다"
            >
              {resolvingUrls ? (
                <>
                  <Wrench className="h-3.5 w-3.5 animate-spin" />
                  <span>복구 중...</span>
                </>
              ) : (
                <>
                  <Wrench className="h-3.5 w-3.5" />
                  <span>URL 복구 ({failedCount})</span>
                </>
              )}
            </button>
          )}

          <button
            onClick={handleSyncAll}
            disabled={syncingAll || syncingEtf !== null || resolvingUrls}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm font-medium transition-colors ${
              syncingAll || syncingEtf !== null || resolvingUrls
                ? 'bg-gray-100 text-gray-400 cursor-not-allowed dark:bg-gray-800'
                : 'bg-blue-500 text-white hover:bg-blue-600'
            }`}
          >
            {syncingAll ? (
              <>
                <RefreshCw className="h-3.5 w-3.5 animate-spin" />
                <span>수집 중...</span>
              </>
            ) : (
              <>
                <Zap className="h-3.5 w-3.5" />
                <span>전체 수집</span>
              </>
            )}
          </button>
        </div>
      </div>

      {/* Summary */}
      {summary && (
        <div className="grid grid-cols-3 gap-2 mb-4">
          <div className="text-center p-2 bg-gray-50 dark:bg-gray-800 rounded-lg">
            <div className="text-lg font-bold text-green-500">{summary.synced}</div>
            <div className="text-xs text-gray-500">수집 완료</div>
          </div>
          <div className="text-center p-2 bg-gray-50 dark:bg-gray-800 rounded-lg">
            <div className="text-lg font-bold text-yellow-500">{summary.pending}</div>
            <div className="text-xs text-gray-500">대기 중</div>
          </div>
          <div className="text-center p-2 bg-gray-50 dark:bg-gray-800 rounded-lg">
            <div className="text-lg font-bold text-blue-500">{summary.total}</div>
            <div className="text-xs text-gray-500">전체</div>
          </div>
        </div>
      )}

      {/* ETF Lists */}
      <ETFTierSection
        title="Tier 1: 섹터 ETF"
        tier="sector"
        etfs={etfs}
        syncingEtf={syncingEtf}
        onSync={handleSyncSingle}
      />

      <ETFTierSection
        title="Tier 2: 테마 ETF"
        tier="theme"
        etfs={etfs}
        syncingEtf={syncingEtf}
        onSync={handleSyncSingle}
      />

      {/* Info */}
      <div className="mt-4 p-2 bg-blue-50 dark:bg-blue-900/20 rounded-lg">
        <p className="text-xs text-blue-600 dark:text-blue-400">
          운용사 공식 CSV에서 Holdings 데이터를 수집합니다.
          전체 수집 후 테마 매칭이 자동으로 갱신됩니다.
        </p>
      </div>
    </div>
  );
}
