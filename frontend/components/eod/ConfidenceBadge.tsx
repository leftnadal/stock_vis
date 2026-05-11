'use client';

interface ConfidenceBadgeProps {
  score: number;
}

export function ConfidenceBadge({ score }: ConfidenceBadgeProps) {
  const getDotConfig = (score: number): { dots: number; color: string; label: string } => {
    if (score > 0.6) return { dots: 5, color: 'bg-green-500', label: '강력 매수' };
    if (score > 0.3) return { dots: 4, color: 'bg-green-400', label: '매수' };
    if (score > 0) return { dots: 3, color: 'bg-gray-400', label: '중립' };
    if (score > -0.3) return { dots: 2, color: 'bg-orange-400', label: '약세' };
    return { dots: 1, color: 'bg-red-500', label: '강한 약세' };
  };

  const { dots, color, label } = getDotConfig(score);

  return (
    <div className="flex items-center gap-1" title={`종합점수: ${score.toFixed(2)} (${label})`}>
      {Array.from({ length: 5 }).map((_, i) => (
        <span
          key={i}
          className={`inline-block w-2 h-2 rounded-full ${
            i < dots ? color : 'bg-gray-200 dark:bg-gray-600'
          }`}
        />
      ))}
      <span className="text-[10px] text-gray-400 dark:text-gray-500 ml-0.5">{label}</span>
    </div>
  );
}
