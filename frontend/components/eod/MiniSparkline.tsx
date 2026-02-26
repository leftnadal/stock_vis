'use client';

interface MiniSparklineProps {
  data: number[];
  width?: number;
  height?: number;
}

export function MiniSparkline({ data, width = 80, height = 24 }: MiniSparklineProps) {
  if (!data || data.length < 2) {
    return <div style={{ width, height }} className="bg-gray-100 dark:bg-gray-700 rounded" />;
  }

  const min = Math.min(...data);
  const max = Math.max(...data);
  const range = max - min || 1;

  const points = data.map((value, index) => {
    const x = (index / (data.length - 1)) * width;
    const y = height - ((value - min) / range) * (height - 2) - 1;
    return `${x.toFixed(1)},${y.toFixed(1)}`;
  });

  const polylinePoints = points.join(' ');
  const isPositive = data[data.length - 1] >= data[0];
  const strokeColor = isPositive ? '#3FB950' : '#F85149';

  // 채움 영역을 위한 path
  const firstPoint = points[0].split(',');
  const lastPoint = points[points.length - 1].split(',');
  const fillPath = `M ${firstPoint[0]},${height} L ${points.join(' L ')} L ${lastPoint[0]},${height} Z`;

  return (
    <svg
      width={width}
      height={height}
      viewBox={`0 0 ${width} ${height}`}
      className="overflow-visible"
    >
      {/* 채움 영역 */}
      <path
        d={fillPath}
        fill={isPositive ? 'rgba(63,185,80,0.1)' : 'rgba(248,81,73,0.1)'}
        stroke="none"
      />
      {/* 라인 */}
      <polyline
        points={polylinePoints}
        fill="none"
        stroke={strokeColor}
        strokeWidth="1.5"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      {/* 마지막 점 */}
      <circle
        cx={lastPoint[0]}
        cy={lastPoint[1]}
        r="1.5"
        fill={strokeColor}
      />
    </svg>
  );
}
