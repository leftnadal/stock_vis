'use client';

import { PipelineStatusBar } from './PipelineStatusBar';
import { CollectionStatsTable } from './CollectionStatsTable';
import { MLModelCard } from './MLModelCard';
import { MLTrendChart } from './MLTrendChart';
import { RecentErrorsList } from './RecentErrorsList';
import { LLMUsageSummary } from './LLMUsageSummary';

interface NewsPipelineSubTabProps {
  enabled?: boolean;
}

export function NewsPipelineSubTab({ enabled = true }: NewsPipelineSubTabProps) {
  return (
    <div className="space-y-6">
      <PipelineStatusBar enabled={enabled} />
      <CollectionStatsTable enabled={enabled} />
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <MLModelCard enabled={enabled} />
        <LLMUsageSummary enabled={enabled} />
      </div>
      <MLTrendChart enabled={enabled} />
      <RecentErrorsList enabled={enabled} />
    </div>
  );
}
