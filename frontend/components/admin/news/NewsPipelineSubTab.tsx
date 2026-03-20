'use client';

import { PipelineStatusBar } from './PipelineStatusBar';
import { CollectionStatsTable } from './CollectionStatsTable';
import { MLModelCard } from './MLModelCard';
import { MLTrendChart } from './MLTrendChart';
import { RecentErrorsList } from './RecentErrorsList';
import { LLMUsageSummary } from './LLMUsageSummary';
import { TaskTimelineChart } from './TaskTimelineChart';
import { Neo4jStatusCard } from './Neo4jStatusCard';
import { MLCompareView } from './MLCompareView';

interface NewsPipelineSubTabProps {
  enabled?: boolean;
}

export function NewsPipelineSubTab({ enabled = true }: NewsPipelineSubTabProps) {
  return (
    <div className="space-y-6">
      <PipelineStatusBar enabled={enabled} />
      {/* Phase B: 24시간 태스크 타임라인 */}
      <TaskTimelineChart hours={24} enabled={enabled} />
      <CollectionStatsTable enabled={enabled} />
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <MLModelCard enabled={enabled} />
        <LLMUsageSummary enabled={enabled} />
      </div>
      {/* Phase B: ML 모델 비교/롤백 + Neo4j 상태 */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <MLCompareView enabled={enabled} />
        <Neo4jStatusCard enabled={enabled} />
      </div>
      <MLTrendChart enabled={enabled} />
      <RecentErrorsList enabled={enabled} />
    </div>
  );
}
