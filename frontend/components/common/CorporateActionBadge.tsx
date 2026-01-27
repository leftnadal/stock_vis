'use client';

import { memo, useState } from 'react';
import { AlertTriangle, TrendingUp, TrendingDown, Gift } from 'lucide-react';

export type ActionType = 'reverse_split' | 'split' | 'spinoff' | 'dividend';

export interface CorporateActionBadgeProps {
  actionType: ActionType;
  display: string;
  size?: 'sm' | 'md';
  showTooltip?: boolean;
  className?: string;
}

// Action type configurations
const ACTION_CONFIG: Record<
  ActionType,
  {
    label: string;
    icon: typeof TrendingUp;
    bgColor: string;
    textColor: string;
    darkBgColor: string;
    darkTextColor: string;
    tooltip: string;
  }
> = {
  reverse_split: {
    label: '역분할',
    icon: TrendingUp,
    bgColor: 'bg-amber-100',
    textColor: 'text-amber-700',
    darkBgColor: 'dark:bg-amber-900/30',
    darkTextColor: 'dark:text-amber-400',
    tooltip: '역주식분할로 인한 가격 변동입니다. 실제 시가총액 변화 없음.',
  },
  split: {
    label: '분할',
    icon: TrendingDown,
    bgColor: 'bg-blue-100',
    textColor: 'text-blue-700',
    darkBgColor: 'dark:bg-blue-900/30',
    darkTextColor: 'dark:text-blue-400',
    tooltip: '주식분할로 인한 가격 변동입니다. 실제 시가총액 변화 없음.',
  },
  spinoff: {
    label: '분사',
    icon: AlertTriangle,
    bgColor: 'bg-purple-100',
    textColor: 'text-purple-700',
    darkBgColor: 'dark:bg-purple-900/30',
    darkTextColor: 'dark:text-purple-400',
    tooltip: '기업 분사(Spin-off)로 인한 가격 조정입니다.',
  },
  dividend: {
    label: '배당',
    icon: Gift,
    bgColor: 'bg-green-100',
    textColor: 'text-green-700',
    darkBgColor: 'dark:bg-green-900/30',
    darkTextColor: 'dark:text-green-400',
    tooltip: '특별 배당으로 인한 배당락 가격 조정입니다.',
  },
};

export const CorporateActionBadge = memo(function CorporateActionBadge({
  actionType,
  display,
  size = 'sm',
  showTooltip = true,
  className = '',
}: CorporateActionBadgeProps) {
  const [isHovered, setIsHovered] = useState(false);

  const config = ACTION_CONFIG[actionType];
  const Icon = config.icon;

  const sizeClasses = {
    sm: 'px-2 py-0.5 text-xs gap-1',
    md: 'px-2.5 py-1 text-sm gap-1.5',
  };

  const iconSize = {
    sm: 'h-3 w-3',
    md: 'h-4 w-4',
  };

  return (
    <div
      className={`relative inline-flex group/action ${className}`}
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
    >
      <span
        className={`
          inline-flex items-center rounded-full font-medium transition-all duration-200
          ${config.bgColor} ${config.textColor}
          ${config.darkBgColor} ${config.darkTextColor}
          ${sizeClasses[size]}
          border border-current/20
        `}
      >
        <Icon className={iconSize[size]} />
        <span>{display}</span>
      </span>

      {/* Hover tooltip */}
      {showTooltip && isHovered && (
        <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 z-50 w-56 pointer-events-none">
          <div className="bg-gray-900 dark:bg-gray-700 text-white rounded-lg shadow-lg p-3">
            <div className="space-y-1.5">
              <div className="flex items-center gap-2">
                <Icon className="h-4 w-4" />
                <span className="font-semibold text-sm">{config.label}</span>
              </div>
              <p className="text-xs leading-relaxed text-gray-300 dark:text-gray-200">
                {config.tooltip}
              </p>
              <div className="pt-1.5 border-t border-gray-700 dark:border-gray-600">
                <span className="text-xs text-gray-400 dark:text-gray-300">
                  표시: {display}
                </span>
              </div>
            </div>
            {/* Arrow */}
            <div className="absolute top-full left-1/2 -translate-x-1/2 -mt-px">
              <div className="w-2 h-2 bg-gray-900 dark:bg-gray-700 rotate-45" />
            </div>
          </div>
        </div>
      )}
    </div>
  );
});

// Compact version for tight spaces
export const CorporateActionBadgeCompact = memo(function CorporateActionBadgeCompact({
  actionType,
  className = '',
}: Pick<CorporateActionBadgeProps, 'actionType' | 'className'>) {
  const config = ACTION_CONFIG[actionType];
  const Icon = config.icon;

  return (
    <div
      className={`inline-flex items-center gap-1 ${className}`}
      title={config.tooltip}
    >
      <Icon className={`h-3 w-3 ${config.textColor} ${config.darkTextColor}`} />
      <span className={`text-xs ${config.textColor} ${config.darkTextColor}`}>
        {config.label}
      </span>
    </div>
  );
});

// Icon only version
export const CorporateActionIcon = memo(function CorporateActionIcon({
  actionType,
  size = 'sm',
  className = '',
}: Pick<CorporateActionBadgeProps, 'actionType' | 'size' | 'className'>) {
  const config = ACTION_CONFIG[actionType];
  const Icon = config.icon;

  const iconSize = {
    sm: 'h-4 w-4',
    md: 'h-5 w-5',
  };

  return (
    <div
      className={`inline-flex items-center justify-center rounded-full p-1 ${config.bgColor} ${config.darkBgColor} ${className}`}
      title={config.tooltip}
    >
      <Icon className={`${iconSize[size]} ${config.textColor} ${config.darkTextColor}`} />
    </div>
  );
});

// Export config for external use
export { ACTION_CONFIG };
