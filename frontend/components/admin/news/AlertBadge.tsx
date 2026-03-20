'use client';

import { Bell } from 'lucide-react';
import { useAlerts } from '@/hooks/useNewsPipeline';

interface AlertBadgeProps {
  onNavigate?: () => void;
}

export function AlertBadge({ onNavigate }: AlertBadgeProps) {
  const { data, isLoading } = useAlerts({ resolved: false, limit: 1 });

  const unresolvedCount = data?.unresolved_count ?? 0;
  const hasAlerts = unresolvedCount > 0;

  return (
    <button
      onClick={onNavigate}
      disabled={isLoading}
      title={hasAlerts ? `미해결 알림 ${unresolvedCount}건` : '알림 없음'}
      className={`relative flex items-center justify-center w-9 h-9 rounded-lg transition-colors ${
        hasAlerts
          ? 'text-red-400 hover:bg-red-900/20'
          : 'text-gray-500 hover:bg-gray-700'
      }`}
    >
      <Bell className="h-5 w-5" />
      {hasAlerts && (
        <span className="absolute -top-1 -right-1 flex items-center justify-center min-w-[18px] h-[18px] px-1 rounded-full bg-red-500 text-white text-[10px] font-bold leading-none">
          {unresolvedCount > 99 ? '99+' : unresolvedCount}
        </span>
      )}
    </button>
  );
}
