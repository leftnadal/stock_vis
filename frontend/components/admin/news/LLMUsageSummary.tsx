'use client';

import { AlertTriangle } from 'lucide-react';
import { useLLMUsage } from '@/hooks/useNewsPipeline';

interface LLMUsageSummaryProps {
  enabled?: boolean;
}

export function LLMUsageSummary({ enabled = true }: LLMUsageSummaryProps) {
  const { data, isLoading, error } = useLLMUsage(7, enabled);

  if (isLoading) {
    return (
      <div className="bg-gray-800 rounded-xl border border-gray-700 p-5">
        <h3 className="font-semibold text-gray-200 mb-4">LLM 사용량 요약</h3>
        <div className="h-36 bg-gray-700 rounded-lg animate-pulse" />
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="bg-gray-800 rounded-xl border border-gray-700 p-5">
        <h3 className="font-semibold text-gray-200 mb-2">LLM 사용량 요약</h3>
        <p className="text-sm text-red-400">데이터 로드 실패</p>
      </div>
    );
  }

  const { keyword_extraction, deep_analysis } = data;
  const { totals } = keyword_extraction;

  return (
    <div className="bg-gray-800 rounded-xl border border-gray-700 p-5">
      <h3 className="font-semibold text-gray-200 mb-3">LLM 사용량 요약</h3>

      {/* 경고 배너 */}
      <div className="flex items-start gap-2 rounded-lg bg-yellow-900/30 border border-yellow-800/50 px-3 py-2 mb-4">
        <AlertTriangle className="h-4 w-4 text-yellow-400 mt-0.5 flex-shrink-0" />
        <p className="text-xs text-yellow-400 leading-snug">
          키워드 추출 비용만 반영됩니다. Phase 3 심층 분석 비용(전체의 대부분)은 미포함입니다.
        </p>
      </div>

      {/* 키워드 추출 통계 */}
      <div className="mb-4">
        <p className="text-xs text-gray-500 font-medium uppercase tracking-wide mb-2">
          키워드 추출 (7일)
        </p>
        <div className="grid grid-cols-2 gap-2">
          <div className="bg-gray-900 rounded-lg p-2.5">
            <p className="text-xs text-gray-500">총 토큰</p>
            <p className="text-sm font-semibold text-gray-200">
              {totals.total_tokens.toLocaleString()}
            </p>
            <p className="text-xs text-gray-600 mt-0.5">
              P: {totals.prompt_tokens.toLocaleString()} / C: {totals.completion_tokens.toLocaleString()}
            </p>
          </div>
          <div className="bg-gray-900 rounded-lg p-2.5">
            <p className="text-xs text-gray-500">성공/실패</p>
            <p className="text-sm font-semibold text-gray-200">
              {totals.success_days}
              <span className="text-gray-500 font-normal"> / </span>
              <span className={totals.failed_days > 0 ? 'text-red-400' : ''}>
                {totals.failed_days}
              </span>
            </p>
            <p className="text-xs text-gray-600 mt-0.5">
              평균 {totals.avg_generation_time_ms.toLocaleString()}ms
            </p>
          </div>
        </div>
      </div>

      {/* LLM 심층 분석 건수 */}
      <div>
        <p className="text-xs text-gray-500 font-medium uppercase tracking-wide mb-2">
          LLM 심층 분석 — 건수만 표시, 토큰 미추적
        </p>
        <div className="grid grid-cols-2 gap-2 mb-2">
          <div className="bg-gray-900 rounded-lg p-2.5">
            <p className="text-xs text-gray-500">분석 완료 (오늘)</p>
            <p className="text-sm font-semibold text-gray-200">
              {deep_analysis.today_analyzed}건
            </p>
          </div>
          <div className="bg-gray-900 rounded-lg p-2.5">
            <p className="text-xs text-gray-500">대기 중</p>
            <p className={`text-sm font-semibold ${deep_analysis.pending_today > 0 ? 'text-yellow-400' : 'text-gray-200'}`}>
              {deep_analysis.pending_today}건
            </p>
          </div>
        </div>
        <div className="flex gap-2 text-xs">
          <span className="px-2 py-1 bg-gray-900 rounded text-gray-400">
            Tier A: {deep_analysis.tier_breakdown.A}
          </span>
          <span className="px-2 py-1 bg-gray-900 rounded text-gray-400">
            Tier B: {deep_analysis.tier_breakdown.B}
          </span>
          <span className="px-2 py-1 bg-gray-900 rounded text-gray-400">
            Tier C: {deep_analysis.tier_breakdown.C}
          </span>
        </div>
      </div>
    </div>
  );
}
