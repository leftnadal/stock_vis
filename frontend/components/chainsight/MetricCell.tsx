interface MetricCellProps {
  value: number | null;
  domain: 'center' | 'baseline'; // 'center' = center-origin signed, 'baseline' = 0-baseline
  domainMax: number;             // positive half for 'center', max for 'baseline'
  signed?: boolean;              // if true, use teal for positive, coral for negative
}

export default function MetricCell({ value, domain, domainMax, signed = false }: MetricCellProps) {
  if (value === null) {
    return (
      <div className="w-20 text-right">
        <div className="text-sm text-gray-400 dark:text-gray-500">—</div>
        <div className="w-full h-1 bg-gray-100 dark:bg-gray-700 rounded overflow-hidden mt-1" />
      </div>
    );
  }

  const isPositive = value >= 0;

  // Determine text color
  let textColorClass = 'text-gray-700 dark:text-gray-300';
  if (signed) {
    textColorClass = isPositive ? 'text-teal-600' : 'text-red-400';
  }

  // Determine bar color
  let barColorClass = 'bg-blue-400';
  if (signed) {
    barColorClass = isPositive ? 'bg-teal-500' : 'bg-red-400';
  }

  // Compute bar width and position
  let barStyle: React.CSSProperties;

  if (domain === 'center') {
    // Center-origin: bar fills from center (50%) outward
    const ratio = Math.min(Math.abs(value) / domainMax, 1);
    const halfWidthPct = ratio * 50;
    if (isPositive) {
      barStyle = { left: '50%', width: `${halfWidthPct}%` };
    } else {
      barStyle = { right: '50%', width: `${halfWidthPct}%` };
    }
  } else {
    // 0-baseline: bar fills from left
    const ratio = Math.min(value / domainMax, 1);
    barStyle = { left: 0, width: `${Math.max(ratio, 0) * 100}%` };
  }

  return (
    <div className="w-20 text-right">
      <div className={`text-sm font-medium ${textColorClass}`}>{value.toFixed(2)}</div>
      <div className="w-full h-1 bg-gray-100 dark:bg-gray-700 rounded overflow-hidden relative mt-1">
        <div
          className={`absolute top-0 h-full ${barColorClass} rounded`}
          style={barStyle}
        />
      </div>
    </div>
  );
}
