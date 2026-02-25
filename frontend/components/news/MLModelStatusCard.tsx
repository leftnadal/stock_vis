'use client';

import React from 'react';
import {
  Brain,
  TrendingUp,
  Shield,
  Database,
  CheckCircle,
  XCircle,
  Clock,
  BarChart3,
} from 'lucide-react';
import { useMLStatus } from '@/hooks/useNews';

export default function MLModelStatusCard() {
  const { data, isLoading, error } = useMLStatus();

  if (isLoading) {
    return (
      <div className="bg-white dark:bg-gray-800 rounded-xl p-5 shadow-sm border border-gray-200 dark:border-gray-700">
        <div className="animate-pulse space-y-3">
          <div className="h-5 w-40 bg-gray-200 dark:bg-gray-700 rounded" />
          <div className="h-4 w-full bg-gray-200 dark:bg-gray-700 rounded" />
          <div className="h-4 w-3/4 bg-gray-200 dark:bg-gray-700 rounded" />
        </div>
      </div>
    );
  }

  if (error || !data) {
    return null;
  }

  const { latest_model, deployed_model, recent_history, labeled_data_count, min_required, ready_for_training } = data;

  return (
    <div className="bg-white dark:bg-gray-800 rounded-xl p-5 shadow-sm border border-gray-200 dark:border-gray-700">
      {/* Header */}
      <div className="flex items-center gap-2 mb-4">
        <Brain className="w-5 h-5 text-purple-500" />
        <h3 className="text-sm font-semibold text-gray-900 dark:text-gray-100">
          ML Model Status
        </h3>
        {deployed_model?.version ? (
          <span className="ml-auto text-xs px-2 py-0.5 rounded-full bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-400">
            Deployed
          </span>
        ) : latest_model?.status === 'shadow' ? (
          <span className="ml-auto text-xs px-2 py-0.5 rounded-full bg-yellow-100 dark:bg-yellow-900/30 text-yellow-700 dark:text-yellow-400">
            Shadow Mode
          </span>
        ) : (
          <span className="ml-auto text-xs px-2 py-0.5 rounded-full bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-400">
            Training
          </span>
        )}
      </div>

      {/* Data Readiness */}
      <div className="flex items-center gap-2 mb-3 p-2 rounded-lg bg-gray-50 dark:bg-gray-700/50">
        <Database className="w-4 h-4 text-gray-500" />
        <span className="text-xs text-gray-600 dark:text-gray-400">
          Labeled Data:
        </span>
        <span className="text-xs font-medium text-gray-900 dark:text-gray-200">
          {labeled_data_count.toLocaleString()} / {min_required}
        </span>
        {ready_for_training ? (
          <CheckCircle className="w-3.5 h-3.5 text-green-500 ml-auto" />
        ) : (
          <Clock className="w-3.5 h-3.5 text-yellow-500 ml-auto" />
        )}
      </div>

      {/* Latest Model Metrics */}
      {latest_model?.f1_score != null && (
        <div className="space-y-2 mb-3">
          <div className="flex items-center gap-2">
            <BarChart3 className="w-4 h-4 text-blue-500" />
            <span className="text-xs text-gray-600 dark:text-gray-400">
              Latest: {latest_model.version}
            </span>
          </div>

          <div className="grid grid-cols-2 gap-2">
            <MetricBadge label="F1" value={latest_model.f1_score} threshold={0.55} />
            <MetricBadge
              label="Gate"
              value={latest_model.safety_gate ? 1 : 0}
              threshold={0.5}
              format={(v) => v >= 0.5 ? 'Passed' : 'Failed'}
            />
          </div>
        </div>
      )}

      {/* Deployed Model Weights */}
      {deployed_model?.weights && (
        <div className="space-y-2 mb-3">
          <div className="flex items-center gap-2">
            <Shield className="w-4 h-4 text-green-500" />
            <span className="text-xs text-gray-600 dark:text-gray-400">
              Active Weights
            </span>
          </div>
          <div className="space-y-1">
            {Object.entries(deployed_model.weights).map(([key, value]) => (
              <WeightBar key={key} name={formatWeightName(key)} value={value} />
            ))}
          </div>
        </div>
      )}

      {/* Recent History */}
      {recent_history.length > 0 && (
        <div className="space-y-1">
          <div className="flex items-center gap-2 mb-1">
            <TrendingUp className="w-4 h-4 text-gray-500" />
            <span className="text-xs text-gray-600 dark:text-gray-400">
              Recent Training
            </span>
          </div>
          {recent_history.slice(0, 3).map((item) => (
            <div
              key={item.version}
              className="flex items-center gap-2 text-xs py-1"
            >
              {item.gate_passed ? (
                <CheckCircle className="w-3 h-3 text-green-500 flex-shrink-0" />
              ) : (
                <XCircle className="w-3 h-3 text-red-500 flex-shrink-0" />
              )}
              <span className="text-gray-600 dark:text-gray-400 truncate">
                {item.version}
              </span>
              <span className="ml-auto font-mono text-gray-900 dark:text-gray-200">
                F1: {item.f1.toFixed(2)}
              </span>
            </div>
          ))}
        </div>
      )}

      {/* No model yet */}
      {!latest_model && !deployed_model && (
        <p className="text-xs text-gray-500 dark:text-gray-400 text-center py-2">
          {ready_for_training
            ? 'Ready to train. Next run: Sunday 03:00 EST'
            : `Collecting data... ${labeled_data_count}/${min_required}`
          }
        </p>
      )}
    </div>
  );
}

// ── Sub Components ──

function MetricBadge({
  label,
  value,
  threshold,
  format,
}: {
  label: string;
  value: number;
  threshold: number;
  format?: (v: number) => string;
}) {
  const isGood = value >= threshold;
  const displayValue = format ? format(value) : value.toFixed(2);

  return (
    <div
      className={`px-2 py-1 rounded text-xs text-center ${
        isGood
          ? 'bg-green-50 dark:bg-green-900/20 text-green-700 dark:text-green-400'
          : 'bg-red-50 dark:bg-red-900/20 text-red-700 dark:text-red-400'
      }`}
    >
      <span className="text-gray-500 dark:text-gray-400">{label}: </span>
      <span className="font-medium">{displayValue}</span>
    </div>
  );
}

function WeightBar({ name, value }: { name: string; value: number }) {
  const pct = Math.round(value * 100);

  return (
    <div className="flex items-center gap-2">
      <span className="text-[10px] text-gray-500 dark:text-gray-400 w-20 truncate">
        {name}
      </span>
      <div className="flex-1 h-1.5 bg-gray-200 dark:bg-gray-600 rounded-full overflow-hidden">
        <div
          className="h-full bg-purple-500 dark:bg-purple-400 rounded-full"
          style={{ width: `${pct}%` }}
        />
      </div>
      <span className="text-[10px] font-mono text-gray-600 dark:text-gray-300 w-8 text-right">
        {pct}%
      </span>
    </div>
  );
}

function formatWeightName(key: string): string {
  const map: Record<string, string> = {
    source_credibility: 'Source',
    entity_count: 'Entities',
    sentiment_magnitude: 'Sentiment',
    recency: 'Recency',
    keyword_relevance: 'Keywords',
  };
  return map[key] || key;
}
