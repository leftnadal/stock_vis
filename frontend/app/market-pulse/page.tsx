'use client';

import React, { useEffect, useState } from 'react';
import { RefreshCw, Activity, AlertCircle, Loader2, Clock, Database, CheckCircle, Minus } from 'lucide-react';
import { AuthGuard } from '@/components/auth/AuthGuard';
import FearGreedGauge from '@/components/macro/FearGreedGauge';
import YieldCurveChart from '@/components/macro/YieldCurveChart';
import EconomicIndicators from '@/components/macro/EconomicIndicators';
import GlobalMarketsCard from '@/components/macro/GlobalMarketsCard';
import { MarketMoversSection } from '@/components/market-pulse/MarketMoversSection';
import { useMarketPulse, isMarketPulseDataEmpty, useSyncStatus, useStartDataSync, useRefreshOnSyncComplete } from '@/hooks/useMarketPulse';

// 섹션별 스켈레톤 컴포넌트
function SectionSkeleton({ title, subtitle }: { title: string; subtitle?: string }) {
  return (
    <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-100 dark:border-gray-700">
      <div className="px-6 py-4 border-b border-gray-100 dark:border-gray-700">
        <div className="text-sm font-semibold text-gray-900 dark:text-white">{title}</div>
        {subtitle && <div className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">{subtitle}</div>}
      </div>
      <div className="p-6">
        <div className="flex items-center justify-center py-12">
          <div className="text-center">
            <Loader2 className="w-5 h-5 animate-spin text-gray-300 dark:text-gray-600 mx-auto mb-2" />
            <p className="text-xs text-gray-400 dark:text-gray-500">데이터 로딩 중</p>
          </div>
        </div>
      </div>
    </div>
  );
}

// 스탈 데이터 표시 배지
function StaleIndicator({ updatedAt, isValidating }: { updatedAt: string; isValidating: boolean }) {
  const minutes = Math.floor((Date.now() - new Date(updatedAt).getTime()) / 60000);

  if (isValidating) {
    return (
      <span className="flex items-center gap-1.5 text-xs text-blue-600 dark:text-blue-400">
        <Loader2 className="w-3 h-3 animate-spin" />
        업데이트 중
      </span>
    );
  }

  if (minutes < 1) {
    return <span className="text-xs text-emerald-600 dark:text-emerald-400">방금 업데이트</span>;
  }

  if (minutes < 5) {
    return <span className="text-xs text-gray-500 dark:text-gray-400">{minutes}분 전</span>;
  }

  return <span className="text-xs text-amber-600 dark:text-amber-400">{minutes}분 전</span>;
}

function MarketPulseContent() {
  // TanStack Query 훅 사용
  const { data, isLoading, isFetching, error, refetch } = useMarketPulse();

  // 동기화 상태 관리
  const [syncEnabled, setSyncEnabled] = useState(false);
  const { data: syncStatusData } = useSyncStatus(syncEnabled);
  const startSyncMutation = useStartDataSync();
  const { invalidateMarketPulse } = useRefreshOnSyncComplete();

  // 데이터가 비어있으면 자동 동기화 트리거
  useEffect(() => {
    if (!isLoading && isMarketPulseDataEmpty(data) && !syncEnabled) {
      handleStartSync();
    }
  }, [isLoading, data, syncEnabled]);

  // 동기화 완료 시 데이터 리페치
  useEffect(() => {
    if (syncStatusData?.status === 'completed') {
      invalidateMarketPulse();
      setTimeout(() => setSyncEnabled(false), 3000);
    }
  }, [syncStatusData?.status, invalidateMarketPulse]);

  const handleStartSync = async () => {
    setSyncEnabled(true);
    startSyncMutation.mutate();
  };

  const handleRefresh = () => {
    refetch();
  };

  const syncStatus = syncStatusData?.status || 'idle';
  const syncProgress = syncStatusData?.progress || { message: '', steps_completed: 0, total_steps: 4 };

  // 데이터 유무와 관계없이 페이지 구조는 즉시 렌더링
  // 각 섹션이 독립적으로 로딩 상태를 표시
  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
      {/* Header */}
      <header className="bg-white dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700 sticky top-0 z-10">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-14">
            <div className="flex items-center gap-3">
              <div className="w-8 h-8 bg-gradient-to-br from-blue-500 to-indigo-600 rounded-lg flex items-center justify-center">
                <Activity className="w-4 h-4 text-white" />
              </div>
              <h1 className="text-base font-semibold text-gray-900 dark:text-white">
                Market Pulse
              </h1>
            </div>

            <div className="flex items-center gap-3">
              {/* Sync Status */}
              {syncStatus === 'running' && (
                <div className="flex items-center gap-2 px-3 py-1.5 bg-blue-50 dark:bg-blue-900/20 rounded-lg">
                  <Loader2 className="w-3.5 h-3.5 text-blue-600 dark:text-blue-400 animate-spin" />
                  <span className="text-xs font-medium text-blue-700 dark:text-blue-300">
                    {syncProgress.message}
                  </span>
                </div>
              )}

              {syncStatus === 'completed' && (
                <div className="flex items-center gap-1.5 px-3 py-1.5 bg-emerald-50 dark:bg-emerald-900/20 rounded-lg">
                  <CheckCircle className="w-3.5 h-3.5 text-emerald-600 dark:text-emerald-400" />
                  <span className="text-xs font-medium text-emerald-700 dark:text-emerald-300">완료</span>
                </div>
              )}

              {/* Last Updated */}
              {data && (
                <div className="hidden sm:flex items-center gap-1.5 text-gray-500 dark:text-gray-400">
                  <Clock className="w-3.5 h-3.5" />
                  <StaleIndicator updatedAt={data.last_updated} isValidating={isFetching && !isLoading} />
                </div>
              )}

              <div className="h-4 w-px bg-gray-200 dark:bg-gray-700 hidden sm:block" />

              <button
                onClick={handleStartSync}
                disabled={syncStatus === 'running'}
                className="flex items-center gap-1.5 px-2.5 py-1.5 text-xs font-medium text-gray-600 hover:text-gray-900 dark:text-gray-400 dark:hover:text-white hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition-colors disabled:opacity-50"
              >
                <Database className="w-3.5 h-3.5" />
                <span className="hidden sm:inline">동기화</span>
              </button>

              <button
                onClick={handleRefresh}
                disabled={isFetching || syncStatus === 'running'}
                className="flex items-center gap-1.5 px-2.5 py-1.5 text-xs font-medium text-gray-600 hover:text-gray-900 dark:text-gray-400 dark:hover:text-white hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition-colors disabled:opacity-50"
              >
                <RefreshCw className={`w-3.5 h-3.5 ${isFetching ? 'animate-spin' : ''}`} />
                <span className="hidden sm:inline">새로고침</span>
              </button>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content - 각 섹션 독립적으로 렌더링 */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6 space-y-6">
        {/* Section 0: Market Movers - 가장 빠르게 로드됨 (독립 훅 사용) */}
        <MarketMoversSection />

        {/* Section 1: Fear & Greed + Yield Curve */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="lg:col-span-1">
            {data?.fear_greed ? (
              <FearGreedGauge data={data.fear_greed} />
            ) : (
              <SectionSkeleton title="Fear & Greed Index" subtitle="시장 심리 지표" />
            )}
          </div>
          <div className="lg:col-span-2">
            {data?.interest_rates ? (
              <YieldCurveChart data={data.interest_rates} />
            ) : (
              <SectionSkeleton title="Yield Curve" subtitle="국채 수익률 곡선" />
            )}
          </div>
        </div>

        {/* Section 2: Economic Indicators */}
        {data?.economy ? (
          <EconomicIndicators data={data.economy} />
        ) : (
          <SectionSkeleton title="Economic Indicators" subtitle="주요 경제 지표" />
        )}

        {/* Section 3: Global Markets */}
        {data?.global_markets ? (
          <GlobalMarketsCard data={data.global_markets} />
        ) : (
          <SectionSkeleton title="Global Markets" subtitle="글로벌 시장 현황" />
        )}

        {/* Section 4: Economic Calendar */}
        {data?.calendar ? (
          <section className="bg-white dark:bg-gray-800 rounded-xl border border-gray-100 dark:border-gray-700">
            <div className="px-6 py-4 border-b border-gray-100 dark:border-gray-700">
              <h3 className="text-sm font-semibold text-gray-900 dark:text-white">Economic Calendar</h3>
              <p className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">이번 주 주요 경제 일정</p>
            </div>
            <div className="p-6">
              {data.calendar.total_count === 0 ? (
                <div className="text-center py-8">
                  <div className="w-12 h-12 bg-gray-100 dark:bg-gray-700 rounded-full flex items-center justify-center mx-auto mb-3">
                    <Minus className="w-5 h-5 text-gray-400" />
                  </div>
                  <p className="text-sm text-gray-500 dark:text-gray-400">예정된 이벤트가 없습니다</p>
                </div>
              ) : (
                <div className="space-y-6">
                  {Object.entries(data.calendar.events_by_date).slice(0, 5).map(([dateStr, events]) => (
                    <div key={dateStr}>
                      <div className="flex items-center gap-2 mb-3">
                        <span className="text-xs font-medium text-gray-900 dark:text-white">
                          {new Date(dateStr).toLocaleDateString('ko-KR', { month: 'short', day: 'numeric' })}
                        </span>
                        <span className="text-xs text-gray-400 dark:text-gray-500">
                          {new Date(dateStr).toLocaleDateString('ko-KR', { weekday: 'short' })}
                        </span>
                      </div>
                      <div className="space-y-2">
                        {events.map((event, idx) => (
                          <div
                            key={idx}
                            className={`flex items-center justify-between p-3 rounded-lg transition-colors ${
                              event.impact === 'High'
                                ? 'bg-red-50/50 dark:bg-red-900/10'
                                : 'bg-gray-50/50 dark:bg-gray-700/30'
                            }`}
                          >
                            <div className="flex items-center gap-3">
                              <div className={`w-1.5 h-1.5 rounded-full flex-shrink-0 ${
                                event.impact === 'High' ? 'bg-red-500'
                                  : event.impact === 'Medium' ? 'bg-amber-500' : 'bg-gray-300'
                              }`} />
                              <div>
                                <span className="text-sm text-gray-900 dark:text-white">{event.event}</span>
                                <span className="text-xs text-gray-400 ml-2">{event.time}</span>
                              </div>
                            </div>
                            <div className="text-right">
                              {event.actual ? (
                                <span className="text-sm font-medium text-gray-900 dark:text-white">{event.actual}</span>
                              ) : event.estimate ? (
                                <span className="text-sm text-gray-500">Est. {event.estimate}</span>
                              ) : null}
                              {event.previous && (
                                <span className="text-xs text-gray-400 ml-2">(Prev. {event.previous})</span>
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
          </section>
        ) : (
          <SectionSkeleton title="Economic Calendar" subtitle="이번 주 주요 경제 일정" />
        )}

        {/* Disclaimer */}
        {data && (
          <footer className="text-center text-xs text-gray-400 dark:text-gray-500 py-4 space-y-1">
            <p>본 데이터는 정보 제공 목적이며, 투자 권유가 아닙니다.</p>
            <p>
              Data: FRED, FMP · Updated: {new Date(data.last_updated).toLocaleString('ko-KR', {
                month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit',
              })}
            </p>
          </footer>
        )}
      </main>
    </div>
  );
}

export default function MarketPulsePage() {
  return (
    <AuthGuard>
      <MarketPulseContent />
    </AuthGuard>
  );
}
