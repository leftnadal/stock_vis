'use client'

import { useState, useEffect } from 'react'
import {
  Activity,
  DollarSign,
  Zap,
  Database,
  TrendingUp,
  Clock,
  RefreshCw,
  ChevronDown,
  ChevronUp,
  X
} from 'lucide-react'
import {
  monitoringService,
  type CostSummary,
  type CacheStats,
  type UsageStats,
} from '@/services/ragService'

interface MonitoringDashboardProps {
  isOpen: boolean
  onClose: () => void
}

export function MonitoringDashboard({ isOpen, onClose }: MonitoringDashboardProps) {
  const [costSummary, setCostSummary] = useState<CostSummary | null>(null)
  const [cacheStats, setCacheStats] = useState<CacheStats | null>(null)
  const [usageStats, setUsageStats] = useState<UsageStats | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [isExpanded, setIsExpanded] = useState(false)

  const fetchData = async () => {
    setIsLoading(true)
    setError(null)

    try {
      const [cost, cache, usage] = await Promise.all([
        monitoringService.getCostSummary(),
        monitoringService.getCacheStats(),
        monitoringService.getUsageStats(24),
      ])

      setCostSummary(cost)
      setCacheStats(cache)
      setUsageStats(usage)
    } catch (err) {
      console.error('Failed to fetch monitoring data:', err)
      setError('모니터링 데이터를 불러올 수 없습니다.')
    } finally {
      setIsLoading(false)
    }
  }

  useEffect(() => {
    if (isOpen) {
      fetchData()
    }
  }, [isOpen])

  if (!isOpen) return null

  // 원화 환산 (1400원/달러)
  const toKRW = (usd: number) => Math.round(usd * 1400)

  // 진행률 바 색상
  const getProgressColor = (percent: number) => {
    if (percent >= 90) return 'bg-red-500'
    if (percent >= 70) return 'bg-amber-500'
    return 'bg-emerald-500'
  }

  return (
    <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 rounded-xl shadow-lg overflow-hidden">
      {/* 헤더 */}
      <div className="flex items-center justify-between px-4 py-3 bg-slate-50 dark:bg-slate-800/50 border-b border-slate-200 dark:border-slate-700">
        <div className="flex items-center gap-2">
          <Activity className="w-4 h-4 text-blue-500" />
          <h3 className="text-sm font-semibold text-slate-900 dark:text-white">
            사용량 모니터링
          </h3>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={fetchData}
            disabled={isLoading}
            className="p-1.5 rounded-lg hover:bg-slate-200 dark:hover:bg-slate-700 transition-colors disabled:opacity-50"
            title="새로고침"
          >
            <RefreshCw className={`w-4 h-4 text-slate-500 ${isLoading ? 'animate-spin' : ''}`} />
          </button>
          <button
            onClick={() => setIsExpanded(!isExpanded)}
            className="p-1.5 rounded-lg hover:bg-slate-200 dark:hover:bg-slate-700 transition-colors"
          >
            {isExpanded ? (
              <ChevronUp className="w-4 h-4 text-slate-500" />
            ) : (
              <ChevronDown className="w-4 h-4 text-slate-500" />
            )}
          </button>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg hover:bg-slate-200 dark:hover:bg-slate-700 transition-colors"
          >
            <X className="w-4 h-4 text-slate-500" />
          </button>
        </div>
      </div>

      {/* 로딩/에러 상태 */}
      {isLoading && (
        <div className="p-8 flex items-center justify-center">
          <RefreshCw className="w-6 h-6 text-blue-500 animate-spin" />
        </div>
      )}

      {error && (
        <div className="p-4 text-center text-red-500 text-sm">
          {error}
        </div>
      )}

      {/* 메인 컨텐츠 */}
      {!isLoading && !error && costSummary && (
        <div className="p-4 space-y-4">
          {/* 비용 요약 (간략) */}
          <div className="grid grid-cols-3 gap-3">
            {/* 일일 비용 */}
            <div className="bg-gradient-to-br from-blue-50 to-blue-100 dark:from-blue-900/30 dark:to-blue-800/30 rounded-lg p-3">
              <div className="flex items-center gap-1.5 mb-1">
                <DollarSign className="w-3.5 h-3.5 text-blue-600 dark:text-blue-400" />
                <span className="text-xs text-blue-600 dark:text-blue-400 font-medium">오늘</span>
              </div>
              <div className="text-lg font-bold text-blue-700 dark:text-blue-300 font-mono">
                ${costSummary.daily.cost_usd.toFixed(4)}
              </div>
              <div className="text-xs text-blue-500 dark:text-blue-400">
                ≈ ₩{toKRW(costSummary.daily.cost_usd).toLocaleString()}
              </div>
              {/* 진행률 바 */}
              <div className="mt-2 h-1.5 bg-blue-200 dark:bg-blue-900 rounded-full overflow-hidden">
                <div
                  className={`h-full ${getProgressColor(costSummary.daily.usage_percent)} transition-all`}
                  style={{ width: `${Math.min(costSummary.daily.usage_percent, 100)}%` }}
                />
              </div>
              <div className="text-xs text-blue-500 dark:text-blue-400 mt-1">
                {costSummary.daily.usage_percent.toFixed(1)}% / ${costSummary.daily.limit_usd}
              </div>
            </div>

            {/* 월간 비용 */}
            <div className="bg-gradient-to-br from-emerald-50 to-emerald-100 dark:from-emerald-900/30 dark:to-emerald-800/30 rounded-lg p-3">
              <div className="flex items-center gap-1.5 mb-1">
                <TrendingUp className="w-3.5 h-3.5 text-emerald-600 dark:text-emerald-400" />
                <span className="text-xs text-emerald-600 dark:text-emerald-400 font-medium">
                  {costSummary.monthly.month}월
                </span>
              </div>
              <div className="text-lg font-bold text-emerald-700 dark:text-emerald-300 font-mono">
                ${costSummary.monthly.cost_usd.toFixed(4)}
              </div>
              <div className="text-xs text-emerald-500 dark:text-emerald-400">
                ≈ ₩{toKRW(costSummary.monthly.cost_usd).toLocaleString()}
              </div>
              {/* 진행률 바 */}
              <div className="mt-2 h-1.5 bg-emerald-200 dark:bg-emerald-900 rounded-full overflow-hidden">
                <div
                  className={`h-full ${getProgressColor(costSummary.monthly.usage_percent)} transition-all`}
                  style={{ width: `${Math.min(costSummary.monthly.usage_percent, 100)}%` }}
                />
              </div>
              <div className="text-xs text-emerald-500 dark:text-emerald-400 mt-1">
                {costSummary.monthly.usage_percent.toFixed(1)}% / ${costSummary.monthly.limit_usd}
              </div>
            </div>

            {/* 캐시 히트율 */}
            <div className="bg-gradient-to-br from-amber-50 to-amber-100 dark:from-amber-900/30 dark:to-amber-800/30 rounded-lg p-3">
              <div className="flex items-center gap-1.5 mb-1">
                <Zap className="w-3.5 h-3.5 text-amber-600 dark:text-amber-400" />
                <span className="text-xs text-amber-600 dark:text-amber-400 font-medium">캐시</span>
              </div>
              <div className="text-lg font-bold text-amber-700 dark:text-amber-300 font-mono">
                {costSummary.cache.hit_rate_percent.toFixed(1)}%
              </div>
              <div className="text-xs text-amber-500 dark:text-amber-400">
                24시간 히트율
              </div>
              {/* 캐시 히트율 바 */}
              <div className="mt-2 h-1.5 bg-amber-200 dark:bg-amber-900 rounded-full overflow-hidden">
                <div
                  className="h-full bg-amber-500 transition-all"
                  style={{ width: `${costSummary.cache.hit_rate_percent}%` }}
                />
              </div>
              <div className="text-xs text-amber-500 dark:text-amber-400 mt-1">
                절감 효과
              </div>
            </div>
          </div>

          {/* 확장된 상세 정보 */}
          {isExpanded && usageStats && cacheStats && (
            <div className="space-y-4 pt-2 border-t border-slate-200 dark:border-slate-700">
              {/* 24시간 사용량 통계 */}
              <div>
                <h4 className="text-xs font-medium text-slate-500 dark:text-slate-400 uppercase tracking-wide mb-2">
                  24시간 사용량
                </h4>
                <div className="grid grid-cols-2 gap-2">
                  <StatItem
                    icon={<Activity className="w-3.5 h-3.5" />}
                    label="총 요청"
                    value={usageStats.total_requests.toString()}
                    color="blue"
                  />
                  <StatItem
                    icon={<Zap className="w-3.5 h-3.5" />}
                    label="캐시 히트"
                    value={usageStats.cache_hits.toString()}
                    color="amber"
                  />
                  <StatItem
                    icon={<Database className="w-3.5 h-3.5" />}
                    label="입력 토큰"
                    value={usageStats.total_input_tokens.toLocaleString()}
                    color="emerald"
                  />
                  <StatItem
                    icon={<Database className="w-3.5 h-3.5" />}
                    label="출력 토큰"
                    value={usageStats.total_output_tokens.toLocaleString()}
                    color="purple"
                  />
                  <StatItem
                    icon={<Clock className="w-3.5 h-3.5" />}
                    label="평균 지연"
                    value={`${Math.round(usageStats.avg_latency_ms)}ms`}
                    color="slate"
                  />
                  <StatItem
                    icon={<DollarSign className="w-3.5 h-3.5" />}
                    label="총 비용"
                    value={`$${usageStats.total_cost_usd.toFixed(4)}`}
                    color="rose"
                  />
                </div>
              </div>

              {/* 시맨틱 캐시 통계 */}
              {cacheStats.status === 'available' && (
                <div>
                  <h4 className="text-xs font-medium text-slate-500 dark:text-slate-400 uppercase tracking-wide mb-2">
                    시맨틱 캐시
                  </h4>
                  <div className="grid grid-cols-3 gap-2">
                    <StatItem
                      icon={<Database className="w-3.5 h-3.5" />}
                      label="총 항목"
                      value={(cacheStats.total_entries || 0).toString()}
                      color="blue"
                    />
                    <StatItem
                      icon={<Zap className="w-3.5 h-3.5" />}
                      label="활성"
                      value={(cacheStats.active_entries || 0).toString()}
                      color="emerald"
                    />
                    <StatItem
                      icon={<Clock className="w-3.5 h-3.5" />}
                      label="평균 히트"
                      value={(cacheStats.avg_hit_count || 0).toFixed(1)}
                      color="amber"
                    />
                  </div>
                </div>
              )}

              {cacheStats.status === 'unavailable' && (
                <div className="text-center py-2 text-sm text-slate-500 dark:text-slate-400">
                  시맨틱 캐시 서비스를 사용할 수 없습니다.
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  )
}

// 통계 아이템 컴포넌트
function StatItem({
  icon,
  label,
  value,
  color,
}: {
  icon: React.ReactNode
  label: string
  value: string
  color: 'blue' | 'emerald' | 'amber' | 'purple' | 'slate' | 'rose'
}) {
  const colorClasses = {
    blue: 'text-blue-600 dark:text-blue-400 bg-blue-50 dark:bg-blue-900/30',
    emerald: 'text-emerald-600 dark:text-emerald-400 bg-emerald-50 dark:bg-emerald-900/30',
    amber: 'text-amber-600 dark:text-amber-400 bg-amber-50 dark:bg-amber-900/30',
    purple: 'text-purple-600 dark:text-purple-400 bg-purple-50 dark:bg-purple-900/30',
    slate: 'text-slate-600 dark:text-slate-400 bg-slate-50 dark:bg-slate-800/50',
    rose: 'text-rose-600 dark:text-rose-400 bg-rose-50 dark:bg-rose-900/30',
  }

  return (
    <div className={`rounded-lg p-2 ${colorClasses[color]}`}>
      <div className="flex items-center gap-1 mb-0.5">
        {icon}
        <span className="text-xs opacity-80">{label}</span>
      </div>
      <div className="text-sm font-semibold font-mono">{value}</div>
    </div>
  )
}

// 간단한 모니터링 버튼 (토글용)
export function MonitoringButton({
  onClick,
  isActive,
}: {
  onClick: () => void
  isActive: boolean
}) {
  return (
    <button
      onClick={onClick}
      className={`
        flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm font-medium
        transition-colors
        ${isActive
          ? 'bg-blue-100 text-blue-700 dark:bg-blue-900/50 dark:text-blue-300'
          : 'bg-slate-100 text-slate-600 hover:bg-slate-200 dark:bg-slate-800 dark:text-slate-400 dark:hover:bg-slate-700'
        }
      `}
    >
      <Activity className="w-4 h-4" />
      <span>모니터링</span>
    </button>
  )
}
