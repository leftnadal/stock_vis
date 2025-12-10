'use client';

import React, { useEffect, useState, useCallback } from 'react';
import { RefreshCw, Activity, AlertCircle, Loader2, Clock, Database, CheckCircle } from 'lucide-react';
import FearGreedGauge from '@/components/macro/FearGreedGauge';
import YieldCurveChart from '@/components/macro/YieldCurveChart';
import EconomicIndicators from '@/components/macro/EconomicIndicators';
import GlobalMarketsCard from '@/components/macro/GlobalMarketsCard';
import { macroService } from '@/services/macroService';
import type { MarketPulseDashboard } from '@/types/macro';

// 데이터 비어있는지 확인하는 헬퍼 함수
function isDataEmpty(data: MarketPulseDashboard | null): boolean {
  if (!data) return true;

  // global_markets의 indices가 모두 null인지 확인
  const indices = data.global_markets?.indices;
  if (indices) {
    const hasIndexData = indices.sp500 || indices.nasdaq || indices.dow || indices.russell2000;
    if (!hasIndexData) return true;
  }

  return false;
}

export default function MarketPulsePage() {
  const [data, setData] = useState<MarketPulseDashboard | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // 동기화 상태
  const [syncStatus, setSyncStatus] = useState<'idle' | 'running' | 'completed' | 'error'>('idle');
  const [syncProgress, setSyncProgress] = useState({
    current_step: 'idle',
    steps_completed: 0,
    total_steps: 4,
    message: '대기 중',
  });
  const [syncTriggered, setSyncTriggered] = useState(false);

  const fetchData = useCallback(async (refresh = false) => {
    try {
      if (refresh) {
        setIsRefreshing(true);
      } else {
        setIsLoading(true);
      }
      setError(null);

      const result = await macroService.getMarketPulse();
      setData(result);

      // 데이터가 비어있으면 자동으로 동기화 시작
      if (isDataEmpty(result) && !syncTriggered && syncStatus !== 'running') {
        startDataSync();
      }
    } catch (err) {
      console.error('Failed to fetch market pulse:', err);
      setError('데이터를 불러오는데 실패했습니다. 잠시 후 다시 시도해주세요.');
    } finally {
      setIsLoading(false);
      setIsRefreshing(false);
    }
  }, [syncTriggered, syncStatus]);

  const startDataSync = async () => {
    try {
      setSyncTriggered(true);
      const response = await macroService.startDataSync();
      if (response.status === 'started' || response.status === 'already_running') {
        setSyncStatus('running');
        pollSyncStatus();
      }
    } catch (err) {
      console.error('Failed to start data sync:', err);
      setSyncStatus('error');
    }
  };

  const pollSyncStatus = async () => {
    try {
      const status = await macroService.getSyncStatus();
      setSyncStatus(status.status);
      setSyncProgress(status.progress);

      if (status.status === 'running') {
        // 2초 후 다시 폴링
        setTimeout(pollSyncStatus, 2000);
      } else if (status.status === 'completed') {
        // 완료되면 데이터 다시 로드
        setTimeout(() => {
          fetchData(true);
        }, 1000);
      }
    } catch (err) {
      console.error('Failed to poll sync status:', err);
    }
  };

  useEffect(() => {
    fetchData();

    // 1분마다 자동 새로고침
    const interval = setInterval(() => {
      if (syncStatus !== 'running') {
        fetchData(true);
      }
    }, 60000);

    return () => clearInterval(interval);
  }, []);

  const handleRefresh = () => {
    fetchData(true);
  };

  const handleManualSync = () => {
    startDataSync();
  };

  // 로딩 스켈레톤
  if (isLoading) {
    return (
      <div className="min-h-screen bg-gray-50 dark:bg-gray-900 p-6">
        <div className="max-w-7xl mx-auto">
          <div className="animate-pulse space-y-6">
            <div className="h-12 bg-gray-200 dark:bg-gray-700 rounded-lg w-64" />
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
              <div className="h-96 bg-gray-200 dark:bg-gray-700 rounded-xl" />
              <div className="lg:col-span-2 h-96 bg-gray-200 dark:bg-gray-700 rounded-xl" />
            </div>
            <div className="h-64 bg-gray-200 dark:bg-gray-700 rounded-xl" />
            <div className="h-96 bg-gray-200 dark:bg-gray-700 rounded-xl" />
          </div>
        </div>
      </div>
    );
  }

  // 에러 상태
  if (error) {
    return (
      <div className="min-h-screen bg-gray-50 dark:bg-gray-900 p-6 flex items-center justify-center">
        <div className="text-center">
          <AlertCircle className="w-16 h-16 text-red-500 mx-auto mb-4" />
          <h2 className="text-xl font-semibold text-gray-900 dark:text-white mb-2">
            오류가 발생했습니다
          </h2>
          <p className="text-gray-600 dark:text-gray-400 mb-4">{error}</p>
          <button
            onClick={() => fetchData()}
            className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
          >
            다시 시도
          </button>
        </div>
      </div>
    );
  }

  if (!data) return null;

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
      {/* Header */}
      <header className="bg-white dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700 sticky top-0 z-10">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-16">
            <div className="flex items-center gap-3">
              <Activity className="w-6 h-6 text-blue-600" />
              <div>
                <h1 className="text-xl font-bold text-gray-900 dark:text-white">
                  Market Pulse
                </h1>
                <p className="text-xs text-gray-500 dark:text-gray-400">
                  거시경제 대시보드
                </p>
              </div>
            </div>

            <div className="flex items-center gap-4">
              {/* Sync Status */}
              {syncStatus === 'running' && (
                <div className="flex items-center gap-2 px-3 py-1.5 bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300 rounded-lg text-sm">
                  <Loader2 className="w-4 h-4 animate-spin" />
                  <span>{syncProgress.message}</span>
                  <span className="text-xs opacity-75">
                    ({syncProgress.steps_completed}/{syncProgress.total_steps})
                  </span>
                </div>
              )}

              {syncStatus === 'completed' && (
                <div className="flex items-center gap-2 px-3 py-1.5 bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-300 rounded-lg text-sm">
                  <CheckCircle className="w-4 h-4" />
                  <span>업데이트 완료</span>
                </div>
              )}

              {/* Last Updated */}
              <div className="hidden sm:flex items-center gap-2 text-sm text-gray-500 dark:text-gray-400">
                <Clock className="w-4 h-4" />
                <span>
                  {new Date(data.last_updated).toLocaleTimeString('ko-KR', {
                    hour: '2-digit',
                    minute: '2-digit',
                  })}
                </span>
              </div>

              {/* Sync Button */}
              <button
                onClick={handleManualSync}
                disabled={syncStatus === 'running'}
                className="flex items-center gap-2 px-3 py-2 text-sm text-blue-600 hover:text-blue-700 dark:text-blue-400 dark:hover:text-blue-300 hover:bg-blue-50 dark:hover:bg-blue-900/20 rounded-lg transition-colors disabled:opacity-50"
                title="데이터 업데이트"
              >
                <Database className="w-4 h-4" />
                <span className="hidden sm:inline">데이터 업데이트</span>
              </button>

              {/* Refresh Button */}
              <button
                onClick={handleRefresh}
                disabled={isRefreshing || syncStatus === 'running'}
                className="flex items-center gap-2 px-4 py-2 text-sm text-gray-600 hover:text-gray-900 dark:text-gray-400 dark:hover:text-white hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition-colors disabled:opacity-50"
              >
                <RefreshCw className={`w-4 h-4 ${isRefreshing ? 'animate-spin' : ''}`} />
                새로고침
              </button>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6 space-y-6">
        {/* Section 1: Fear & Greed + Yield Curve */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Fear & Greed Gauge */}
          <div className="lg:col-span-1">
            <FearGreedGauge data={data.fear_greed} />
          </div>

          {/* Yield Curve Chart */}
          <div className="lg:col-span-2">
            <YieldCurveChart data={data.interest_rates} />
          </div>
        </div>

        {/* Section 2: Economic Indicators */}
        <EconomicIndicators data={data.economy} />

        {/* Section 3: Global Markets */}
        <GlobalMarketsCard data={data.global_markets} />

        {/* Section 4: Economic Calendar */}
        <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700 p-6">
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
            이번 주 주요 경제 일정
          </h3>

          {data.calendar.total_count === 0 ? (
            <p className="text-gray-500 dark:text-gray-400 text-center py-8">
              예정된 이벤트가 없습니다.
            </p>
          ) : (
            <div className="space-y-4">
              {Object.entries(data.calendar.events_by_date)
                .slice(0, 5)
                .map(([dateStr, events]) => (
                  <div key={dateStr}>
                    <h4 className="text-sm font-medium text-gray-500 dark:text-gray-400 mb-2">
                      {new Date(dateStr).toLocaleDateString('ko-KR', {
                        month: 'long',
                        day: 'numeric',
                        weekday: 'short',
                      })}
                    </h4>
                    <div className="space-y-2">
                      {events.map((event, idx) => (
                        <div
                          key={idx}
                          className={`flex items-center justify-between p-3 rounded-lg ${
                            event.impact === 'High'
                              ? 'bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800'
                              : 'bg-gray-50 dark:bg-gray-700'
                          }`}
                        >
                          <div className="flex items-center gap-3">
                            <span
                              className={`w-2 h-2 rounded-full ${
                                event.impact === 'High'
                                  ? 'bg-red-500'
                                  : event.impact === 'Medium'
                                  ? 'bg-amber-500'
                                  : 'bg-gray-400'
                              }`}
                            />
                            <div>
                              <span className="text-sm font-medium text-gray-900 dark:text-white">
                                {event.event}
                              </span>
                              <span className="text-xs text-gray-500 dark:text-gray-400 ml-2">
                                {event.time}
                              </span>
                            </div>
                          </div>
                          <div className="text-right text-sm">
                            {event.actual ? (
                              <span className="font-medium text-gray-900 dark:text-white">
                                {event.actual}
                              </span>
                            ) : event.estimate ? (
                              <span className="text-gray-500 dark:text-gray-400">
                                예상: {event.estimate}
                              </span>
                            ) : null}
                            {event.previous && (
                              <span className="text-xs text-gray-400 dark:text-gray-500 ml-2">
                                (이전: {event.previous})
                              </span>
                            )}
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                ))}
            </div>
          )}
        </div>

        {/* Disclaimer */}
        <div className="text-center text-xs text-gray-400 dark:text-gray-500 py-4">
          <p>
            본 데이터는 정보 제공 목적이며, 투자 권유가 아닙니다.
            투자 결정은 본인의 판단과 책임 하에 이루어져야 합니다.
          </p>
          <p className="mt-1">
            데이터 제공: FRED, FMP API | 최종 업데이트:{' '}
            {new Date(data.last_updated).toLocaleString('ko-KR')}
          </p>
        </div>
      </main>
    </div>
  );
}
