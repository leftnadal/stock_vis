'use client';

import { Newspaper, BarChart3, Hash, Heart, FolderOpen } from 'lucide-react';
import { useAdminNews } from '@/hooks/useAdminDashboard';
import SummaryCard from './shared/SummaryCard';
import NewsCategoryManager from './NewsCategoryManager';

export default function NewsTab() {
  const { data, isLoading, error } = useAdminNews();

  if (isLoading) {
    return (
      <div className="space-y-4">
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
          {[...Array(4)].map((_, i) => (
            <div key={i} className="h-28 bg-gray-100 dark:bg-gray-800 rounded-xl animate-pulse" />
          ))}
        </div>
        {[...Array(2)].map((_, i) => (
          <div key={i} className="h-48 bg-gray-100 dark:bg-gray-800 rounded-xl animate-pulse" />
        ))}
      </div>
    );
  }

  if (error || !data) {
    return <div className="text-center py-12 text-red-500">데이터 로드 실패</div>;
  }

  const { articles, source_distribution, keyword_history, sentiment, categories } = data;

  return (
    <div className="space-y-6">
      {/* Article Stats */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <SummaryCard
          title="전체 기사"
          value={articles.total.toLocaleString()}
          icon={<Newspaper className="h-6 w-6" />}
          status="neutral"
        />
        <SummaryCard
          title="24시간 수집"
          value={articles.last_24h}
          icon={<BarChart3 className="h-6 w-6" />}
          status={articles.last_24h > 0 ? 'ok' : 'warning'}
        />
        <SummaryCard
          title="7일 수집"
          value={articles.last_7d}
          icon={<BarChart3 className="h-6 w-6" />}
          status="neutral"
        />
        <SummaryCard
          title="수집 카테고리"
          value={categories ? `${categories.active}/${categories.total}` : '0'}
          subtitle={categories?.latest_collection
            ? `최근: ${categories.latest_collection.name}`
            : undefined}
          icon={<FolderOpen className="h-6 w-6" />}
          status={categories && categories.active > 0 ? 'ok' : 'neutral'}
        />
      </div>

      {/* Source Distribution */}
      <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-5">
        <h3 className="font-semibold text-gray-800 dark:text-gray-200 mb-3">소스 분포 (7일)</h3>
        {source_distribution.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-gray-200 dark:border-gray-700">
                  <th className="text-left py-2 px-2 text-gray-500 dark:text-gray-400 font-medium">Source</th>
                  <th className="text-right py-2 px-2 text-gray-500 dark:text-gray-400 font-medium">Count</th>
                  <th className="text-left py-2 px-2 text-gray-500 dark:text-gray-400 font-medium w-1/2">Bar</th>
                </tr>
              </thead>
              <tbody>
                {source_distribution.map((s) => {
                  const maxCount = source_distribution[0]?.count || 1;
                  const pct = (s.count / maxCount) * 100;
                  return (
                    <tr key={s.source} className="border-b border-gray-100 dark:border-gray-800">
                      <td className="py-1.5 px-2 text-gray-700 dark:text-gray-300 font-mono text-xs">{s.source}</td>
                      <td className="py-1.5 px-2 text-right text-gray-600 dark:text-gray-400">{s.count}</td>
                      <td className="py-1.5 px-2">
                        <div className="w-full bg-gray-100 dark:bg-gray-700 rounded-full h-2">
                          <div
                            className="bg-blue-500 h-2 rounded-full"
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
        ) : (
          <p className="text-sm text-gray-400">데이터 없음</p>
        )}
      </div>

      {/* Keyword History */}
      <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-5">
        <h3 className="font-semibold text-gray-800 dark:text-gray-200 mb-3 flex items-center gap-2">
          <Hash className="h-4 w-4" />
          키워드 이력 (7일)
        </h3>
        {keyword_history.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-gray-200 dark:border-gray-700">
                  <th className="text-left py-2 px-2 text-gray-500 dark:text-gray-400 font-medium">Date</th>
                  <th className="text-left py-2 px-2 text-gray-500 dark:text-gray-400 font-medium">Status</th>
                  <th className="text-right py-2 px-2 text-gray-500 dark:text-gray-400 font-medium">News Count</th>
                </tr>
              </thead>
              <tbody>
                {keyword_history.map((k) => (
                  <tr key={k.date} className="border-b border-gray-100 dark:border-gray-800">
                    <td className="py-1.5 px-2 text-gray-700 dark:text-gray-300">{k.date}</td>
                    <td className="py-1.5 px-2">
                      <span className={`text-xs font-medium ${
                        k.status === 'completed' ? 'text-green-600' : k.status === 'failed' ? 'text-red-600' : 'text-yellow-600'
                      }`}>
                        {k.status}
                      </span>
                    </td>
                    <td className="py-1.5 px-2 text-right text-gray-600 dark:text-gray-400">{k.total_news_count}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <p className="text-sm text-gray-400">데이터 없음</p>
        )}
      </div>

      {/* Sentiment */}
      <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-5">
        <h3 className="font-semibold text-gray-800 dark:text-gray-200 mb-3 flex items-center gap-2">
          <Heart className="h-4 w-4" />
          감성 분석
        </h3>
        <div className="flex gap-6 text-sm">
          <div>
            <span className="text-gray-500 dark:text-gray-400">7일 평균: </span>
            <span className="font-medium text-gray-700 dark:text-gray-300">
              {sentiment.avg_7d ? Number(sentiment.avg_7d).toFixed(3) : 'N/A'}
            </span>
          </div>
          <div>
            <span className="text-gray-500 dark:text-gray-400">커버리지: </span>
            <span className="font-medium text-gray-700 dark:text-gray-300">
              {sentiment.coverage_symbols}개 종목
            </span>
          </div>
        </div>
      </div>

      {/* News Collection Categories */}
      <NewsCategoryManager />
    </div>
  );
}
