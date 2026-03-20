'use client';

import { formatDistanceToNow, parseISO } from 'date-fns';
import { ko } from 'date-fns/locale';
import { usePipelineHealth } from '@/hooks/useNewsPipeline';
import type { PhaseStatus } from '@/types/newsPipeline';

const STATUS_STYLES: Record<PhaseStatus, { badge: string; dot: string }> = {
  ok: {
    badge: 'bg-green-900/30 text-green-400 border-green-800',
    dot: 'bg-green-400',
  },
  warning: {
    badge: 'bg-yellow-900/30 text-yellow-400 border-yellow-800',
    dot: 'bg-yellow-400',
  },
  error: {
    badge: 'bg-red-900/30 text-red-400 border-red-800',
    dot: 'bg-red-400',
  },
  stale: {
    badge: 'bg-gray-800 text-gray-400 border-gray-700',
    dot: 'bg-gray-500',
  },
};

const STATUS_LABEL: Record<PhaseStatus, string> = {
  ok: 'OK',
  warning: '주의',
  error: '오류',
  stale: '지연',
};

function formatRelativeTime(isoString: string | null): string {
  if (!isoString) return '실행 없음';
  try {
    return formatDistanceToNow(parseISO(isoString), { addSuffix: true, locale: ko });
  } catch {
    return isoString;
  }
}

interface PipelineStatusBarProps {
  enabled?: boolean;
}

export function PipelineStatusBar({ enabled = true }: PipelineStatusBarProps) {
  const { data, isLoading, error } = usePipelineHealth(enabled);

  if (isLoading) {
    return (
      <div className="bg-gray-800 rounded-xl border border-gray-700 p-5">
        <h3 className="font-semibold text-gray-200 mb-4">파이프라인 Phase 상태</h3>
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
          {[...Array(6)].map((_, i) => (
            <div key={i} className="h-24 bg-gray-700 rounded-lg animate-pulse" />
          ))}
        </div>
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="bg-gray-800 rounded-xl border border-gray-700 p-5">
        <h3 className="font-semibold text-gray-200 mb-2">파이프라인 Phase 상태</h3>
        <p className="text-sm text-red-400">데이터 로드 실패</p>
      </div>
    );
  }

  const generatedAt = formatRelativeTime(data.generated_at);

  return (
    <div className="bg-gray-800 rounded-xl border border-gray-700 p-5">
      <div className="flex items-center justify-between mb-4">
        <h3 className="font-semibold text-gray-200">파이프라인 Phase 상태</h3>
        <span className="text-xs text-gray-500">업데이트: {generatedAt}</span>
      </div>

      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
        {data.phases.map((phase) => {
          const styles = STATUS_STYLES[phase.status];
          return (
            <div
              key={phase.phase}
              className="bg-gray-900 rounded-lg border border-gray-700 p-3 flex flex-col gap-2"
            >
              <div className="flex items-center justify-between">
                <span className="text-xs font-mono text-gray-500">Phase {phase.phase}</span>
                <span className={`inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-xs font-medium border ${styles.badge}`}>
                  <span className={`w-1.5 h-1.5 rounded-full ${styles.dot}`} />
                  {STATUS_LABEL[phase.status]}
                </span>
              </div>
              <p className="text-xs text-gray-300 leading-snug">{phase.name}</p>
              <p className="text-xs text-gray-500 mt-auto">
                {formatRelativeTime(phase.last_run)}
              </p>
            </div>
          );
        })}
      </div>

      {data.is_weekend_kst && (
        <p className="mt-3 text-xs text-gray-500">
          * 주말(KST) — Phase 2/3는 평일 전용 태스크로 주말 면제 적용됩니다.
        </p>
      )}
    </div>
  );
}
