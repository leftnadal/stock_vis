'use client';

import { useState } from 'react';
import { XCircle, AlertTriangle, Info, ChevronDown, ChevronUp } from 'lucide-react';
import type { AdminIssue } from '@/types/admin';
import ActionButton from './ActionButton';

interface IssueListProps {
  issues: AdminIssue[];
}

const severityConfig = {
  error: {
    icon: <XCircle className="h-5 w-5 text-red-500" />,
    border: 'border-red-200 dark:border-red-800',
    bg: 'bg-red-50 dark:bg-red-900/10',
  },
  warning: {
    icon: <AlertTriangle className="h-5 w-5 text-yellow-500" />,
    border: 'border-yellow-200 dark:border-yellow-800',
    bg: 'bg-yellow-50 dark:bg-yellow-900/10',
  },
  info: {
    icon: <Info className="h-5 w-5 text-blue-500" />,
    border: 'border-blue-200 dark:border-blue-800',
    bg: 'bg-blue-50 dark:bg-blue-900/10',
  },
};

function IssueItem({ issue }: { issue: AdminIssue }) {
  const [expanded, setExpanded] = useState(false);
  const config = severityConfig[issue.severity];

  return (
    <div className={`rounded-lg border ${config.border} ${config.bg} overflow-hidden`}>
      <div
        role="button"
        tabIndex={0}
        onClick={() => setExpanded(!expanded)}
        onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); setExpanded(!expanded); } }}
        className="w-full flex items-center gap-3 p-3 text-left hover:opacity-80 transition-opacity cursor-pointer"
      >
        {config.icon}
        <span className="flex-1 text-sm font-medium text-gray-800 dark:text-gray-200">
          {issue.title}
        </span>
        <span className="text-xs text-gray-400 px-2 py-0.5 bg-gray-100 dark:bg-gray-800 rounded">
          {issue.category}
        </span>
        {issue.suggested_action && (
          <div onClick={(e) => e.stopPropagation()}>
            <ActionButton action={issue.suggested_action} label="Fix" size="sm" variant="secondary" />
          </div>
        )}
        {expanded ? (
          <ChevronUp className="h-4 w-4 text-gray-400" />
        ) : (
          <ChevronDown className="h-4 w-4 text-gray-400" />
        )}
      </div>

      {expanded && (
        <div className="px-3 pb-3 pt-0 ml-8">
          <p className="text-sm text-gray-600 dark:text-gray-400">{issue.detail}</p>
          {issue.symbols && issue.symbols.length > 0 && (
            <div className="mt-2 flex flex-wrap gap-1">
              {issue.symbols.map((s) => (
                <span
                  key={s}
                  className="px-2 py-0.5 text-xs font-mono bg-gray-200 dark:bg-gray-700 rounded"
                >
                  {s}
                </span>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export default function IssueList({ issues }: IssueListProps) {
  if (issues.length === 0) {
    return (
      <div className="text-center py-6 text-gray-400 dark:text-gray-500">
        <Info className="h-8 w-8 mx-auto mb-2 opacity-50" />
        <p className="text-sm">감지된 문제 없음</p>
      </div>
    );
  }

  return (
    <div className="space-y-2">
      {issues.map((issue, i) => (
        <IssueItem key={`${issue.category}-${issue.title}-${i}`} issue={issue} />
      ))}
    </div>
  );
}
