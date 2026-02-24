'use client';

import { CheckCircle2, AlertTriangle, XCircle, Info } from 'lucide-react';

type BadgeStatus = 'ok' | 'warning' | 'error' | 'info' | 'loading';

interface StatusBadgeProps {
  status: BadgeStatus;
  label?: string;
}

const config: Record<BadgeStatus, { icon: React.ReactNode; color: string; bg: string }> = {
  ok: {
    icon: <CheckCircle2 className="h-3.5 w-3.5" />,
    color: 'text-green-600 dark:text-green-400',
    bg: 'bg-green-100 dark:bg-green-900/30',
  },
  warning: {
    icon: <AlertTriangle className="h-3.5 w-3.5" />,
    color: 'text-yellow-600 dark:text-yellow-400',
    bg: 'bg-yellow-100 dark:bg-yellow-900/30',
  },
  error: {
    icon: <XCircle className="h-3.5 w-3.5" />,
    color: 'text-red-600 dark:text-red-400',
    bg: 'bg-red-100 dark:bg-red-900/30',
  },
  info: {
    icon: <Info className="h-3.5 w-3.5" />,
    color: 'text-blue-600 dark:text-blue-400',
    bg: 'bg-blue-100 dark:bg-blue-900/30',
  },
  loading: {
    icon: <div className="h-3.5 w-3.5 rounded-full border-2 border-gray-300 border-t-blue-500 animate-spin" />,
    color: 'text-gray-500',
    bg: 'bg-gray-100 dark:bg-gray-800',
  },
};

export default function StatusBadge({ status, label }: StatusBadgeProps) {
  const c = config[status];
  return (
    <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium ${c.color} ${c.bg}`}>
      {c.icon}
      {label && <span>{label}</span>}
    </span>
  );
}
