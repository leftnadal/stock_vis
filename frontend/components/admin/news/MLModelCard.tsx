'use client';

import { formatDistanceToNow, parseISO } from 'date-fns';
import { ko } from 'date-fns/locale';
import { useMLTrend } from '@/hooks/useNewsPipeline';
import type { MLModelEntry } from '@/types/newsPipeline';

const DEPLOYMENT_STYLES: Record<string, { badge: string; label: string }> = {
  deployed: {
    badge: 'bg-green-900/30 text-green-400 border border-green-800',
    label: 'Deployed',
  },
  shadow: {
    badge: 'bg-yellow-900/30 text-yellow-400 border border-yellow-800',
    label: 'Shadow',
  },
  rolled_back: {
    badge: 'bg-red-900/30 text-red-400 border border-red-800',
    label: 'Rolled Back',
  },
  archived: {
    badge: 'bg-gray-800 text-gray-400 border border-gray-700',
    label: 'Archived',
  },
};

function DeploymentBadge({ status }: { status: string }) {
  const styles = DEPLOYMENT_STYLES[status] ?? DEPLOYMENT_STYLES.archived;
  return (
    <span className={`inline-block px-2 py-0.5 rounded text-xs font-medium ${styles.badge}`}>
      {styles.label}
    </span>
  );
}

function MetricItem({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex flex-col">
      <span className="text-xs text-gray-500">{label}</span>
      <span className="text-sm font-semibold text-gray-200">{value}</span>
    </div>
  );
}

interface MLModelCardProps {
  enabled?: boolean;
}

export function MLModelCard({ enabled = true }: MLModelCardProps) {
  const { data, isLoading, error } = useMLTrend(12, enabled);

  if (isLoading) {
    return (
      <div className="bg-gray-800 rounded-xl border border-gray-700 p-5">
        <h3 className="font-semibold text-gray-200 mb-4">현재 배포 ML 모델</h3>
        <div className="h-36 bg-gray-700 rounded-lg animate-pulse" />
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="bg-gray-800 rounded-xl border border-gray-700 p-5">
        <h3 className="font-semibold text-gray-200 mb-2">현재 배포 ML 모델</h3>
        <p className="text-sm text-red-400">데이터 로드 실패</p>
      </div>
    );
  }

  const deployed = data.history.find((m: MLModelEntry) => m.deployment_status === 'deployed');
  const latest = data.history[data.history.length - 1];
  const model = deployed ?? latest;

  if (!model) {
    return (
      <div className="bg-gray-800 rounded-xl border border-gray-700 p-5">
        <h3 className="font-semibold text-gray-200 mb-2">현재 배포 ML 모델</h3>
        <p className="text-sm text-gray-500">모델 이력 없음</p>
      </div>
    );
  }

  const deployedAt = model.trained_at
    ? formatDistanceToNow(parseISO(model.trained_at), { addSuffix: true, locale: ko })
    : '알 수 없음';

  const { trend_summary } = data;
  const trendColor =
    trend_summary.f1_direction === 'improving'
      ? 'text-green-400'
      : trend_summary.f1_direction === 'declining'
      ? 'text-red-400'
      : 'text-gray-400';
  const trendLabel =
    trend_summary.f1_direction === 'improving'
      ? '개선 중'
      : trend_summary.f1_direction === 'declining'
      ? '하락 중'
      : '안정';

  return (
    <div className="bg-gray-800 rounded-xl border border-gray-700 p-5">
      <div className="flex items-center justify-between mb-4">
        <h3 className="font-semibold text-gray-200">현재 배포 ML 모델</h3>
        <DeploymentBadge status={model.deployment_status} />
      </div>

      <p className="text-xs font-mono text-gray-400 mb-4 truncate">{model.model_version}</p>

      <div className="grid grid-cols-3 gap-3 mb-4">
        <MetricItem label="F1 Score" value={model.f1_score.toFixed(3)} />
        <MetricItem label="Precision" value={model.precision.toFixed(3)} />
        <MetricItem label="Recall" value={model.recall.toFixed(3)} />
      </div>

      <div className="grid grid-cols-2 gap-3 border-t border-gray-700 pt-3">
        <MetricItem
          label="학습 샘플"
          value={model.training_samples.toLocaleString()}
        />
        <MetricItem label="알고리즘" value={model.algorithm} />
      </div>

      <div className="mt-3 border-t border-gray-700 pt-3 flex items-center justify-between">
        <span className="text-xs text-gray-500">학습: {deployedAt}</span>
        <span className={`text-xs font-medium ${trendColor}`}>
          {trendLabel} ({trend_summary.f1_change_total >= 0 ? '+' : ''}
          {trend_summary.f1_change_total.toFixed(3)})
        </span>
      </div>
    </div>
  );
}
