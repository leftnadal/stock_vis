/**
 * Common Components - Usage Examples
 * @description 공통 컴포넌트 사용 예제 모음 (테스트/문서화 목적)
 */

'use client';

import { useState } from 'react';
import {
  DataLoadingState,
  DataSourceBadge,
  DataSourceBadgeCompact,
  DataSourceWithTooltip,
  CorporateActionBadge,
  CorporateActionBadgeCompact,
  CorporateActionIcon,
} from './index';
import type { DataStatus, DataError, ActionType } from './index';

export function DataLoadingStateExamples() {
  const [status, setStatus] = useState<DataStatus>('loading');

  const mockError: DataError = {
    code: 'RATE_LIMIT_EXCEEDED',
    message: '잠시 후 다시 시도해주세요. (약 1분 후)',
    canRetry: true,
    details: {
      symbol: 'AAPL',
      triedSources: ['FMP', 'Alpha Vantage'],
    },
  };

  return (
    <div className="space-y-8 p-6 bg-white dark:bg-gray-900">
      <h2 className="text-2xl font-bold mb-4 text-gray-900 dark:text-white">
        DataLoadingState Examples
      </h2>

      {/* Status Controls */}
      <div className="flex gap-2 flex-wrap">
        {(['loading', 'syncing', 'error', 'empty', 'success'] as DataStatus[]).map((s) => (
          <button
            key={s}
            onClick={() => setStatus(s)}
            className={`px-4 py-2 rounded-lg font-medium transition-colors ${
              status === s
                ? 'bg-blue-600 text-white'
                : 'bg-gray-200 dark:bg-gray-700 text-gray-700 dark:text-gray-300'
            }`}
          >
            {s}
          </button>
        ))}
      </div>

      {/* Component Display */}
      <div className="border border-gray-200 dark:border-gray-700 rounded-lg p-6">
        <DataLoadingState
          status={status}
          progress={
            status === 'syncing' || status === 'loading'
              ? { current: 3, total: 10, currentItem: 'AAPL' }
              : undefined
          }
          error={status === 'error' ? mockError : undefined}
          onRetry={() => alert('Retry clicked')}
          onSync={() => alert('Sync clicked')}
          loadingMessage="주식 데이터를 불러오는 중..."
          emptyMessage="표시할 데이터가 없습니다."
        >
          <div className="text-green-600 dark:text-green-400 font-semibold">
            Success! Data loaded successfully.
          </div>
        </DataLoadingState>
      </div>

      {/* All States Preview */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="border border-gray-200 dark:border-gray-700 rounded-lg p-4">
          <h3 className="font-semibold mb-2 text-gray-900 dark:text-white">Loading</h3>
          <DataLoadingState status="loading" />
        </div>
        <div className="border border-gray-200 dark:border-gray-700 rounded-lg p-4">
          <h3 className="font-semibold mb-2 text-gray-900 dark:text-white">Syncing</h3>
          <DataLoadingState
            status="syncing"
            progress={{ current: 5, total: 10, currentItem: 'MSFT' }}
          />
        </div>
        <div className="border border-gray-200 dark:border-gray-700 rounded-lg p-4">
          <h3 className="font-semibold mb-2 text-gray-900 dark:text-white">Error</h3>
          <DataLoadingState
            status="error"
            error={mockError}
            onRetry={() => {}}
          />
        </div>
        <div className="border border-gray-200 dark:border-gray-700 rounded-lg p-4">
          <h3 className="font-semibold mb-2 text-gray-900 dark:text-white">Empty</h3>
          <DataLoadingState status="empty" onSync={() => {}} />
        </div>
      </div>
    </div>
  );
}

export function DataSourceBadgeExamples() {
  return (
    <div className="space-y-8 p-6 bg-white dark:bg-gray-900">
      <h2 className="text-2xl font-bold mb-4 text-gray-900 dark:text-white">
        DataSourceBadge Examples
      </h2>

      {/* All Sources */}
      <div className="space-y-4">
        <h3 className="font-semibold text-gray-900 dark:text-white">All Data Sources</h3>
        <div className="flex flex-wrap gap-3">
          <DataSourceBadge source="db" syncedAt={new Date()} freshness="fresh" />
          <DataSourceBadge
            source="fmp"
            syncedAt={new Date(Date.now() - 1000 * 60 * 30)}
            freshness="fresh"
          />
          <DataSourceBadge
            source="fmp_realtime"
            syncedAt={new Date(Date.now() - 1000 * 60 * 60 * 2)}
            freshness="stale"
          />
          <DataSourceBadge
            source="alpha_vantage"
            syncedAt={new Date(Date.now() - 1000 * 60 * 60 * 24)}
            freshness="expired"
          />
          <DataSourceBadge source="yfinance" syncedAt={new Date()} freshness="fresh" />
          <DataSourceBadge source="unknown" />
        </div>
      </div>

      {/* Freshness States */}
      <div className="space-y-4">
        <h3 className="font-semibold text-gray-900 dark:text-white">Freshness States</h3>
        <div className="flex flex-wrap gap-3">
          <DataSourceBadge source="fmp" syncedAt={new Date()} freshness="fresh" />
          <DataSourceBadge
            source="fmp"
            syncedAt={new Date(Date.now() - 1000 * 60 * 60 * 2)}
            freshness="stale"
          />
          <DataSourceBadge
            source="fmp"
            syncedAt={new Date(Date.now() - 1000 * 60 * 60 * 24)}
            freshness="expired"
          />
        </div>
      </div>

      {/* Sizes */}
      <div className="space-y-4">
        <h3 className="font-semibold text-gray-900 dark:text-white">Sizes</h3>
        <div className="flex items-center flex-wrap gap-3">
          <DataSourceBadge source="fmp" syncedAt={new Date()} freshness="fresh" size="sm" />
          <DataSourceBadge source="fmp" syncedAt={new Date()} freshness="fresh" size="md" />
        </div>
      </div>

      {/* Compact Version */}
      <div className="space-y-4">
        <h3 className="font-semibold text-gray-900 dark:text-white">Compact Version</h3>
        <div className="flex flex-wrap gap-3">
          <DataSourceBadgeCompact source="fmp" freshness="fresh" />
          <DataSourceBadgeCompact source="db" freshness="stale" />
          <DataSourceBadgeCompact source="alpha_vantage" freshness="expired" />
        </div>
      </div>

      {/* With Tooltip */}
      <div className="space-y-4">
        <h3 className="font-semibold text-gray-900 dark:text-white">
          With Tooltip (hover to see)
        </h3>
        <div className="flex flex-wrap gap-3">
          <DataSourceWithTooltip
            source="fmp"
            syncedAt={new Date()}
            freshness="fresh"
            canSync={false}
          />
          <DataSourceWithTooltip
            source="alpha_vantage"
            syncedAt={new Date(Date.now() - 1000 * 60 * 60 * 24)}
            freshness="expired"
            canSync={true}
            onSync={() => alert('Sync triggered')}
          />
        </div>
      </div>
    </div>
  );
}

export function CorporateActionBadgeExamples() {
  const actionTypes: ActionType[] = ['reverse_split', 'split', 'spinoff', 'dividend'];
  const displays: Record<ActionType, string> = {
    reverse_split: '1:10',
    split: '2:1',
    spinoff: 'SpinCo',
    dividend: '$5.00',
  };

  return (
    <div className="space-y-8 p-6 bg-white dark:bg-gray-900">
      <h2 className="text-2xl font-bold mb-4 text-gray-900 dark:text-white">
        CorporateActionBadge Examples
      </h2>

      {/* All Action Types */}
      <div className="space-y-4">
        <h3 className="font-semibold text-gray-900 dark:text-white">All Action Types</h3>
        <div className="flex flex-wrap gap-3">
          {actionTypes.map((type) => (
            <CorporateActionBadge key={type} actionType={type} display={displays[type]} />
          ))}
        </div>
      </div>

      {/* Sizes */}
      <div className="space-y-4">
        <h3 className="font-semibold text-gray-900 dark:text-white">Sizes</h3>
        <div className="flex items-center flex-wrap gap-3">
          <CorporateActionBadge actionType="split" display="2:1" size="sm" />
          <CorporateActionBadge actionType="split" display="2:1" size="md" />
        </div>
      </div>

      {/* Without Tooltip */}
      <div className="space-y-4">
        <h3 className="font-semibold text-gray-900 dark:text-white">Without Tooltip</h3>
        <div className="flex flex-wrap gap-3">
          {actionTypes.map((type) => (
            <CorporateActionBadge
              key={type}
              actionType={type}
              display={displays[type]}
              showTooltip={false}
            />
          ))}
        </div>
      </div>

      {/* Compact Version */}
      <div className="space-y-4">
        <h3 className="font-semibold text-gray-900 dark:text-white">Compact Version</h3>
        <div className="flex flex-wrap gap-3">
          {actionTypes.map((type) => (
            <CorporateActionBadgeCompact key={type} actionType={type} />
          ))}
        </div>
      </div>

      {/* Icon Only */}
      <div className="space-y-4">
        <h3 className="font-semibold text-gray-900 dark:text-white">Icon Only</h3>
        <div className="flex items-center flex-wrap gap-3">
          {actionTypes.map((type) => (
            <CorporateActionIcon key={type} actionType={type} size="sm" />
          ))}
        </div>
        <div className="flex items-center flex-wrap gap-3">
          {actionTypes.map((type) => (
            <CorporateActionIcon key={type} actionType={type} size="md" />
          ))}
        </div>
      </div>

      {/* Real-world Example */}
      <div className="space-y-4">
        <h3 className="font-semibold text-gray-900 dark:text-white">Real-world Example</h3>
        <div className="border border-gray-200 dark:border-gray-700 rounded-lg p-4 space-y-3">
          <div className="flex items-center justify-between">
            <h4 className="text-lg font-semibold text-gray-900 dark:text-white">
              Apple Inc. (AAPL)
            </h4>
            <DataSourceBadge source="fmp" syncedAt={new Date()} freshness="fresh" />
          </div>
          <div className="flex items-center gap-2">
            <span className="text-sm text-gray-600 dark:text-gray-400">Recent Actions:</span>
            <CorporateActionBadge actionType="split" display="4:1" size="sm" />
            <CorporateActionBadge actionType="dividend" display="$0.24" size="sm" />
          </div>
          <p className="text-sm text-gray-500 dark:text-gray-400">
            주가 차트에서 가격 변동이 있을 수 있습니다. 배지 위에 마우스를 올려 상세 정보를 확인하세요.
          </p>
        </div>
      </div>
    </div>
  );
}

// Combined example page
export default function CommonComponentsExamples() {
  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-950">
      <div className="container mx-auto py-8 space-y-12">
        <div className="text-center space-y-2">
          <h1 className="text-4xl font-bold text-gray-900 dark:text-white">
            Common Components
          </h1>
          <p className="text-gray-600 dark:text-gray-400">
            Stock 데이터 로딩/에러 상태 및 Corporate Action 표시를 위한 공통 컴포넌트
          </p>
        </div>

        <div className="space-y-8">
          <DataLoadingStateExamples />
          <div className="border-t border-gray-300 dark:border-gray-700" />
          <DataSourceBadgeExamples />
          <div className="border-t border-gray-300 dark:border-gray-700" />
          <CorporateActionBadgeExamples />
        </div>
      </div>
    </div>
  );
}
