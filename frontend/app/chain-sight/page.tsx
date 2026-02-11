'use client';

/**
 * Chain Sight 관리 페이지
 *
 * ETF Holdings 수집 및 테마 관리를 위한 전용 페이지
 */
import { useState } from 'react';
import {
  Compass,
  Database,
  RefreshCw,
  Zap,
  CheckCircle2,
  AlertCircle,
  Clock,
  ChevronDown,
  ChevronUp,
  Wrench,
  Upload,
  Mail,
  Calendar,
} from 'lucide-react';
import { useETFCollectionStatus, useETFSync, useRefreshThemeMatches, useResolveETFUrl } from '@/hooks/useETFCollection';
import { ETFProfile, ETFTier } from '@/types/etf';

interface ETFStatusRowProps {
  etf: ETFProfile;
  onSync: () => void;
  syncing: boolean;
}

function ETFStatusRow({ etf, onSync, syncing }: ETFStatusRowProps) {
  const statusConfig: Record<string, { icon: React.ReactNode; color: string; bgColor: string }> = {
    synced: {
      icon: <CheckCircle2 className="h-4 w-4" />,
      color: 'text-green-600 dark:text-green-400',
      bgColor: 'bg-green-50 dark:bg-green-900/20',
    },
    pending: {
      icon: <Clock className="h-4 w-4" />,
      color: 'text-yellow-600 dark:text-yellow-400',
      bgColor: 'bg-yellow-50 dark:bg-yellow-900/20',
    },
    syncing: {
      icon: <RefreshCw className="h-4 w-4 animate-spin" />,
      color: 'text-blue-600 dark:text-blue-400',
      bgColor: 'bg-blue-50 dark:bg-blue-900/20',
    },
    failed: {
      icon: <AlertCircle className="h-4 w-4" />,
      color: 'text-red-600 dark:text-red-400',
      bgColor: 'bg-red-50 dark:bg-red-900/20',
    },
  };

  const status = syncing ? 'syncing' : etf.status;
  const config = statusConfig[status] || statusConfig.pending;

  const formatDate = (dateStr: string | null) => {
    if (!dateStr) return '미수집';
    const date = new Date(dateStr);
    return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')}`;
  };

  return (
    <div className={`flex items-center justify-between p-4 rounded-lg border ${config.bgColor} border-gray-200 dark:border-gray-700`}>
      <div className="flex items-center gap-4">
        <div className={`flex items-center justify-center w-10 h-10 rounded-full ${config.bgColor}`}>
          <span className={config.color}>{config.icon}</span>
        </div>
        <div>
          <div className="flex items-center gap-2">
            <span className="font-mono font-bold text-lg">{etf.symbol}</span>
            {etf.holdings_count > 0 && (
              <span className="px-2 py-0.5 text-xs font-medium bg-gray-100 dark:bg-gray-700 rounded-full">
                {etf.holdings_count}개 종목
              </span>
            )}
          </div>
          <span className="text-sm text-gray-500 dark:text-gray-400">{etf.name}</span>
        </div>
      </div>

      <div className="flex items-center gap-4">
        <div className="text-right">
          <div className="text-sm text-gray-500 dark:text-gray-400">마지막 수집</div>
          <div className="text-sm font-medium">{formatDate(etf.last_updated)}</div>
        </div>

        <button
          onClick={onSync}
          disabled={syncing || !etf.csv_url}
          className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
            syncing || !etf.csv_url
              ? 'bg-gray-100 text-gray-400 cursor-not-allowed dark:bg-gray-800'
              : 'bg-blue-500 text-white hover:bg-blue-600'
          }`}
          title={!etf.csv_url ? 'CSV URL 미설정 (수동 업로드 필요)' : '개별 수집'}
        >
          {syncing ? (
            <RefreshCw className="h-4 w-4 animate-spin" />
          ) : !etf.csv_url ? (
            <Upload className="h-4 w-4" />
          ) : (
            <RefreshCw className="h-4 w-4" />
          )}
          {syncing ? '수집 중...' : !etf.csv_url ? '수동 필요' : '수집'}
        </button>
      </div>
    </div>
  );
}

interface ETFTierSectionProps {
  title: string;
  description: string;
  tier: ETFTier;
  etfs: ETFProfile[];
  syncingEtf: string | null;
  onSync: (symbol: string) => void;
}

function ETFTierSection({ title, description, tier, etfs, syncingEtf, onSync }: ETFTierSectionProps) {
  const [expanded, setExpanded] = useState(true);

  const tierEtfs = etfs.filter((e) => e.tier === tier);
  const syncedCount = tierEtfs.filter((e) => e.status === 'synced').length;
  const failedCount = tierEtfs.filter((e) => e.status === 'failed').length;

  return (
    <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 overflow-hidden">
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-center justify-between p-4 hover:bg-gray-50 dark:hover:bg-gray-700/50 transition-colors"
      >
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2">
            <span className="text-lg font-semibold">{title}</span>
            <div className="flex items-center gap-1">
              <span className="px-2 py-0.5 text-xs font-medium bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400 rounded-full">
                {syncedCount} 완료
              </span>
              {failedCount > 0 && (
                <span className="px-2 py-0.5 text-xs font-medium bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400 rounded-full">
                  {failedCount} 실패
                </span>
              )}
            </div>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-sm text-gray-500">{tierEtfs.length}개 ETF</span>
          {expanded ? (
            <ChevronUp className="h-5 w-5 text-gray-400" />
          ) : (
            <ChevronDown className="h-5 w-5 text-gray-400" />
          )}
        </div>
      </button>

      {expanded && (
        <div className="p-4 pt-0 space-y-3">
          <p className="text-sm text-gray-500 dark:text-gray-400 mb-4">{description}</p>
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

export default function ChainSightPage() {
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
      refetch();
    } finally {
      setSyncingEtf(null);
    }
  };

  const handleSyncAll = async () => {
    setSyncingAll(true);
    try {
      await syncMutation.mutateAsync(undefined);
      await refreshThemesMutation.mutateAsync();
      refetch();
    } finally {
      setSyncingAll(false);
    }
  };

  const handleResolveUrls = async () => {
    setResolvingUrls(true);
    try {
      const result = await resolveUrlMutation.mutateAsync(undefined);
      if (result.data.summary.resolved > 0) {
        await syncMutation.mutateAsync(undefined);
      }
      refetch();
    } finally {
      setResolvingUrls(false);
    }
  };

  const etfs = statusData?.data.etfs || [];
  const summary = statusData?.data.summary;
  const failedCount = etfs.filter(
    (e) => e.status === 'failed' || (e.last_error && e.last_error.includes('다운로드'))
  ).length;

  return (
    <div className="container mx-auto px-4 py-8 max-w-5xl">
      {/* 헤더 */}
      <div className="mb-8">
        <div className="flex items-center gap-3 mb-2">
          <div className="flex items-center justify-center w-12 h-12 rounded-xl bg-gradient-to-br from-blue-500 to-purple-600">
            <Compass className="h-6 w-6 text-white" />
          </div>
          <div>
            <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
              Chain Sight
            </h1>
            <p className="text-gray-500 dark:text-gray-400">
              ETF Holdings 기반 테마 관계 수집
            </p>
          </div>
        </div>
      </div>

      {/* 액션 카드 */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-8">
        {/* 전체 수집 */}
        <button
          onClick={handleSyncAll}
          disabled={syncingAll || syncingEtf !== null || resolvingUrls || isLoading}
          className={`p-6 rounded-xl border-2 text-left transition-all ${
            syncingAll || syncingEtf !== null || resolvingUrls || isLoading
              ? 'border-gray-200 bg-gray-50 cursor-not-allowed dark:border-gray-700 dark:bg-gray-800/50'
              : 'border-blue-200 bg-blue-50 hover:border-blue-400 hover:shadow-lg dark:border-blue-800 dark:bg-blue-900/20 dark:hover:border-blue-600'
          }`}
        >
          <div className="flex items-center gap-3 mb-3">
            {syncingAll ? (
              <RefreshCw className="h-8 w-8 text-blue-500 animate-spin" />
            ) : (
              <Zap className="h-8 w-8 text-blue-500" />
            )}
            <span className="text-lg font-semibold text-gray-900 dark:text-white">
              {syncingAll ? '수집 중...' : '전체 수집'}
            </span>
          </div>
          <p className="text-sm text-gray-600 dark:text-gray-400">
            모든 ETF Holdings를 한 번에 수집합니다. 자동화된 ETF만 수집됩니다.
          </p>
        </button>

        {/* URL 복구 */}
        <button
          onClick={handleResolveUrls}
          disabled={resolvingUrls || syncingAll || syncingEtf !== null || failedCount === 0 || isLoading}
          className={`p-6 rounded-xl border-2 text-left transition-all ${
            resolvingUrls || syncingAll || syncingEtf !== null || failedCount === 0 || isLoading
              ? 'border-gray-200 bg-gray-50 cursor-not-allowed dark:border-gray-700 dark:bg-gray-800/50'
              : 'border-orange-200 bg-orange-50 hover:border-orange-400 hover:shadow-lg dark:border-orange-800 dark:bg-orange-900/20 dark:hover:border-orange-600'
          }`}
        >
          <div className="flex items-center gap-3 mb-3">
            {resolvingUrls ? (
              <Wrench className="h-8 w-8 text-orange-500 animate-spin" />
            ) : (
              <Wrench className="h-8 w-8 text-orange-500" />
            )}
            <span className="text-lg font-semibold text-gray-900 dark:text-white">
              {resolvingUrls ? '복구 중...' : `URL 복구 (${failedCount})`}
            </span>
          </div>
          <p className="text-sm text-gray-600 dark:text-gray-400">
            404 에러가 발생한 ETF의 CSV URL을 자동으로 복구합니다.
          </p>
        </button>

        {/* 스케줄 정보 */}
        <div className="p-6 rounded-xl border-2 border-gray-200 bg-gray-50 dark:border-gray-700 dark:bg-gray-800/50">
          <div className="flex items-center gap-3 mb-3">
            <Calendar className="h-8 w-8 text-gray-500" />
            <span className="text-lg font-semibold text-gray-900 dark:text-white">
              자동 스케줄
            </span>
          </div>
          <p className="text-sm text-gray-600 dark:text-gray-400 mb-2">
            매주 월요일 오전 6시 (EST) 자동 수집
          </p>
          <div className="flex items-center gap-2 text-xs text-gray-500">
            <Mail className="h-3.5 w-3.5" />
            <span>실패 시 이메일 알림</span>
          </div>
        </div>
      </div>

      {/* 요약 통계 */}
      {summary && (
        <div className="grid grid-cols-4 gap-4 mb-8">
          <div className="p-4 bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 text-center">
            <div className="text-3xl font-bold text-blue-500">{summary.total}</div>
            <div className="text-sm text-gray-500 dark:text-gray-400">전체 ETF</div>
          </div>
          <div className="p-4 bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 text-center">
            <div className="text-3xl font-bold text-green-500">{summary.synced}</div>
            <div className="text-sm text-gray-500 dark:text-gray-400">수집 완료</div>
          </div>
          <div className="p-4 bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 text-center">
            <div className="text-3xl font-bold text-yellow-500">{summary.pending}</div>
            <div className="text-sm text-gray-500 dark:text-gray-400">대기 중</div>
          </div>
          <div className="p-4 bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 text-center">
            <div className="text-3xl font-bold text-red-500">{failedCount}</div>
            <div className="text-sm text-gray-500 dark:text-gray-400">수동 필요</div>
          </div>
        </div>
      )}

      {/* 로딩 상태 */}
      {isLoading && (
        <div className="flex items-center justify-center py-12">
          <RefreshCw className="h-8 w-8 text-blue-500 animate-spin" />
          <span className="ml-3 text-gray-500">ETF 상태 조회 중...</span>
        </div>
      )}

      {/* ETF 목록 */}
      {!isLoading && (
        <div className="space-y-6">
          <ETFTierSection
            title="Tier 1: 섹터 ETF"
            description="S&P 500 전 종목의 섹터별 테마 확보. 대형주 중심의 시장 뼈대를 구성합니다."
            tier="sector"
            etfs={etfs}
            syncingEtf={syncingEtf}
            onSync={handleSyncSingle}
          />

          <ETFTierSection
            title="Tier 2: 테마 ETF"
            description="반도체, AI, 클린에너지 등 특화 테마. 50~100위권 중소형 '숨겨진 보석' 발견의 핵심입니다."
            tier="theme"
            etfs={etfs}
            syncingEtf={syncingEtf}
            onSync={handleSyncSingle}
          />
        </div>
      )}

      {/* 수동 수집 안내 */}
      <div className="mt-8 p-6 bg-amber-50 dark:bg-amber-900/20 rounded-xl border border-amber-200 dark:border-amber-800">
        <h3 className="font-semibold text-amber-800 dark:text-amber-300 mb-2">
          수동 수집이 필요한 ETF
        </h3>
        <p className="text-sm text-amber-700 dark:text-amber-400 mb-4">
          일부 ETF (ARKK, ARKG, TAN, KWEB 등)는 운용사 보안 정책으로 자동 수집이 불가능합니다.
          아래 명령으로 수동 업로드하세요:
        </p>
        <div className="bg-gray-900 text-gray-100 rounded-lg p-4 font-mono text-sm overflow-x-auto">
          <code>python manage.py import_etf_csv ARKK /path/to/ARKK_holdings.csv</code>
        </div>
        <div className="mt-4 text-xs text-amber-600 dark:text-amber-500">
          <strong>운용사 다운로드 링크:</strong>
          <ul className="mt-1 space-y-1">
            <li>• ARK Invest: <a href="https://ark-funds.com/funds/arkk/" target="_blank" rel="noopener noreferrer" className="underline hover:no-underline">ark-funds.com</a></li>
            <li>• Invesco (TAN, KWEB): <a href="https://www.invesco.com/us/financial-products/etfs/" target="_blank" rel="noopener noreferrer" className="underline hover:no-underline">invesco.com</a></li>
          </ul>
        </div>
      </div>
    </div>
  );
}
