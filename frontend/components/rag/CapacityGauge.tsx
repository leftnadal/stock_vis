'use client';

interface CapacityGaugeProps {
  currentUnits: number;
  maxUnits: number;
  className?: string;
}

export function CapacityGauge({
  currentUnits,
  maxUnits,
  className = ''
}: CapacityGaugeProps) {
  const percentage = Math.min((currentUnits / maxUnits) * 100, 100);
  const remaining = maxUnits - currentUnits;

  // 색상: 초록 → 노랑 → 빨강
  const getColor = () => {
    if (percentage < 60) return 'bg-green-500';
    if (percentage < 85) return 'bg-yellow-500';
    return 'bg-red-500';
  };

  const getTextColor = () => {
    if (percentage < 60) return 'text-green-600 dark:text-green-400';
    if (percentage < 85) return 'text-yellow-600 dark:text-yellow-400';
    return 'text-red-600 dark:text-red-400';
  };

  return (
    <div className={className}>
      <div className="flex justify-between text-sm text-slate-600 dark:text-slate-400 mb-1">
        <span className="font-medium">용량</span>
        <span className={`font-semibold ${getTextColor()}`}>
          {currentUnits} / {maxUnits} units
        </span>
      </div>
      <div className="h-2 bg-slate-200 dark:bg-slate-700 rounded-full overflow-hidden">
        <div
          className={`h-full ${getColor()} transition-all duration-300`}
          style={{ width: `${percentage}%` }}
        />
      </div>
      <div className="text-xs text-slate-500 dark:text-slate-400 mt-1 flex justify-between">
        <span>남은 용량: {remaining} units</span>
        <span>{percentage.toFixed(0)}%</span>
      </div>
    </div>
  );
}
