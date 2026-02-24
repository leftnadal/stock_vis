'use client';

import type { ReactNode } from 'react';

interface SummaryCardProps {
  title: string;
  value: string | number;
  subtitle?: string;
  icon: ReactNode;
  status?: 'ok' | 'warning' | 'error' | 'neutral';
}

const statusColors: Record<string, string> = {
  ok: 'border-l-green-500',
  warning: 'border-l-yellow-500',
  error: 'border-l-red-500',
  neutral: 'border-l-blue-500',
};

export default function SummaryCard({ title, value, subtitle, icon, status = 'neutral' }: SummaryCardProps) {
  return (
    <div className={`bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 border-l-4 ${statusColors[status]} p-5`}>
      <div className="flex items-start justify-between">
        <div>
          <p className="text-sm text-gray-500 dark:text-gray-400">{title}</p>
          <p className="mt-1 text-2xl font-bold text-gray-900 dark:text-white">{value}</p>
          {subtitle && (
            <p className="mt-1 text-xs text-gray-400 dark:text-gray-500">{subtitle}</p>
          )}
        </div>
        <div className="text-gray-400 dark:text-gray-500">
          {icon}
        </div>
      </div>
    </div>
  );
}
