'use client';

import { AlertTriangle, Activity } from 'lucide-react';
import type { MarketSummary } from '@/types/eod';

interface VixChipProps {
  vix: number;
  regime: MarketSummary['vix_regime'];
}

const REGIME_STYLES: Record<
  MarketSummary['vix_regime'],
  { bg: string; text: string; icon: typeof AlertTriangle | null; label: string }
> = {
  normal: {
    bg: 'bg-gray-100 dark:bg-gray-700',
    text: 'text-gray-600 dark:text-gray-300',
    icon: null,
    label: '',
  },
  elevated: {
    bg: 'bg-yellow-50 dark:bg-yellow-900/20',
    text: 'text-yellow-700 dark:text-yellow-300',
    icon: Activity,
    label: '',
  },
  high_vol: {
    bg: 'bg-orange-50 dark:bg-orange-900/20',
    text: 'text-orange-700 dark:text-orange-300',
    icon: AlertTriangle,
    label: '',
  },
};

export function VixChip({ vix, regime }: VixChipProps) {
  const style = REGIME_STYLES[regime] ?? REGIME_STYLES.normal;
  const IconComponent = style.icon;

  return (
    <span
      className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-xs font-semibold ${style.bg} ${style.text}`}
    >
      {IconComponent && <IconComponent className="w-3 h-3" />}
      VIX {vix.toFixed(1)}
    </span>
  );
}
